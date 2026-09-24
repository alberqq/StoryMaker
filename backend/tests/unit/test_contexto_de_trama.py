"""spec: §3.4 · arq: §6

Lo que el escritor recibe para no contradecir ni repetir la novela que ya está escrita, y
lo que el juez hace con las contradicciones que aun así encuentre.

Nacen de la lectura de la cuarta novela real: la firma del mapa contradicha en cinco
capítulos, la navaja entregada dos veces, «precisión» sesenta y tres veces, dos capítulos
con el mismo párrafo de cierre y un 8 del juez en continuidad.
"""

from __future__ import annotations

import aiosqlite
import pytest
from dobles.fabrica import NovelaDePrueba, poblar

from storymaker.commons.context import bloques, repeticion
from storymaker.commons.context.paquete import TECHO_TOTAL, TECHOS_DE_BLOQUE
from storymaker.commons.db.repos import texto
from storymaker.publication.esquemas import Criterio, Puntuacion, SalidaJuez
from storymaker.publication.nodos import topar_continuidad


@pytest.fixture
async def novela(db: aiosqlite.Connection) -> NovelaDePrueba:
    return await poblar(db)


async def _tercer_capitulo(db: aiosqlite.Connection) -> None:
    await db.execute(
        "INSERT INTO plan_capitulo (numero, titulo, funcion, gancho) "
        "VALUES (3, 'El zarpe', 'cierre', 'la flota sale')"
    )


async def _evento(db: aiosqlite.Connection, clave: str, descripcion: str, version: int) -> None:
    await db.execute(
        "INSERT INTO cronologia_evento (clave, descripcion, momento, origen, capitulo_version_id)"
        " VALUES (?, ?, '1805-04-02', 'narrativo', ?)",
        (clave, descripcion, version),
    )


class TestRepeticion:
    def test_cuenta_palabras_y_expresiones_y_deja_fuera_los_nombres(self) -> None:
        textos = [
            "La precision de Manuel. Treinta años de precision. Treinta años de verdad.",
            "Precision y precision. Treinta años. Manuel, Manuel, Manuel, Manuel, Manuel.",
            "Otra precision, treinta años despues.",
        ]
        palabras, expresiones = repeticion.mas_repetidas(textos, excluir=["Manuel Ferrer"])
        assert ("precision", 5) in palabras
        assert all(p != "manuel" for p, _ in palabras), "el nombre no es una repeticion"
        assert ("treinta años", 4) in expresiones

    def test_lo_que_aparece_poco_no_entra(self) -> None:
        palabras, _ = repeticion.mas_repetidas(["Una ventana y otra ventana."])
        assert palabras == []

    def test_la_ultima_frase(self) -> None:
        assert repeticion.ultima_frase("Primera. Y por fin descansa.") == "Y por fin descansa."
        assert repeticion.ultima_frase("") == ""


class TestLoQueYaHaPasado:
    async def test_el_bloque_3_lleva_los_eventos_anteriores_a_n_menos_1(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """El capitulo 3 ve lo que paso en el 1; el 2 ya le llega entero en la memoria."""
        await _tercer_capitulo(db)
        await _evento(
            db, "cap1-navaja", "Manuel entrega la navaja a su aprendiz", novela.version_capitulo_1
        )
        bloque = await bloques.continuidad(db, 3)
        assert "Lo que ya ha pasado en la novela" in bloque.texto()
        assert "Capitulo 1: Manuel entrega la navaja a su aprendiz" in bloque.texto()

    async def test_los_eventos_de_un_intento_descartado_no_cuentan(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await _tercer_capitulo(db)
        descartado = await texto.insertar_capitulo_version(
            db,
            capitulo_id=novela.capitulo_1,
            fase_run_id=novela.fase_run,
            texto="Un intento que nadie aprobo.",
            intento=2,
        )
        await _evento(db, "cap1-fantasma", "Algo que no esta en la novela", descartado)
        assert "Algo que no esta en la novela" not in (await bloques.continuidad(db, 3)).texto()

    async def test_el_capitulo_2_no_repite_lo_que_ya_lleva_la_memoria(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await _evento(db, "cap1-niebla", "La niebla sube del agua", novela.version_capitulo_1)
        assert "La niebla sube del agua" not in (await bloques.continuidad(db, 2)).texto()

    def test_los_techos_siguen_sumando_el_total(self) -> None:
        assert TECHOS_DE_BLOQUE[3] == 2_500
        assert TECHOS_DE_BLOQUE[4] == 3_000
        assert sum(TECHOS_DE_BLOQUE.values()) == TECHO_TOTAL


class TestReglas:
    async def test_las_reglas_de_escritura_son_fijas(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        bloque = await bloques.reglas(db, 2)
        assert "Narra en preterito" in bloque.texto()
        assert "sin encabezados de escena" in bloque.texto()
        assert bloque.fijos >= 2, "voz y reglas no se recortan antes que lo ya gastado"

    async def test_lleva_la_frase_con_la_que_cerro_el_anterior(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        bloque = await bloques.reglas(db, 2)
        assert "antes de que el sol tocara la jarcia." in bloque.texto()

    async def test_el_capitulo_1_no_tiene_nada_gastado(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        assert "Frases con las que ya cerraron" not in (await bloques.reglas(db, 1)).texto()


def _notas(continuidad: int, contradicciones: list[str]) -> SalidaJuez:
    return SalidaJuez(
        puntuaciones=[
            Puntuacion(
                criterio=c,
                valor=continuidad if c is Criterio.CONTINUIDAD else 7,
                justificacion="justificacion suficiente",
            )
            for c in Criterio
        ],
        contradicciones=contradicciones,
    )


class TestToparContinuidad:
    def test_cada_contradiccion_baja_el_techo_dos_puntos(self) -> None:
        notas = topar_continuidad(_notas(8, ["a", "b", "c"]))
        assert notas.por_criterio()["continuidad"] == 4
        assert notas.por_criterio()["prosa"] == 7, "los demas criterios no se tocan"

    def test_sin_contradicciones_la_nota_no_cambia(self) -> None:
        assert topar_continuidad(_notas(8, [])).por_criterio()["continuidad"] == 8

    def test_nunca_baja_de_uno(self) -> None:
        notas = topar_continuidad(_notas(9, [str(i) for i in range(8)]))
        assert notas.por_criterio()["continuidad"] == 1
