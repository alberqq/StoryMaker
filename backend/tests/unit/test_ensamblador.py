"""spec: §3.4 · arq: §6

Pruebas del ensamblador. Las tres primeras son las propiedades que §3.4 declara y que
CrossHair verifica después sobre las funciones puras; las demás comprueban que cada bloque
lleva lo que §6 dice que lleva.

Lo que se comprueba aquí no es que el contexto sea «bueno» —eso lo miden los evals—, sino
que es **acotado, ordenado y reproducible**: que nunca se pasa del techo, que se recorta
por la cola, que la continuidad es lo último que se toca y que los anclajes explícitos
entran siempre.
"""

from __future__ import annotations

import aiosqlite
import pytest
from dobles.fabrica import NovelaDePrueba, poblar
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.config import Settings
from storymaker.commons.context.ensamblador import ensamblar, persistir
from storymaker.commons.context.paquete import TECHO_TOTAL, Bloque
from storymaker.commons.context.truncado import ajustar_al_total, truncar_por_prioridad
from storymaker.commons.db.repos import arnes
from storymaker.commons.embeddings import indice
from storymaker.commons.errores import EscaletaAusente


@pytest.fixture
def vectorizador() -> VectorizadorFalso:
    return VectorizadorFalso()


@pytest.fixture
def ajustes() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture
async def novela(db: aiosqlite.Connection) -> NovelaDePrueba:
    return await poblar(db)


class TestFuncionesPuras:
    """`truncar_por_prioridad` es una de las cinco que CrossHair verifica en G2."""

    def test_corta_por_la_cola(self) -> None:
        fragmentos = ["a" * 100, "b" * 100, "c" * 100]
        conservados = truncar_por_prioridad(fragmentos, techo_tokens=60)
        assert conservados == fragmentos[:2], "se sueltan los ultimos, no los del medio"

    def test_los_fijos_no_se_sueltan_nunca(self) -> None:
        """Un anclaje que el arquitecto puso y que no cabe es una senal, no un sobrante."""
        fragmentos = ["x" * 5_000, "vecino semantico"]
        conservados = truncar_por_prioridad(fragmentos, techo_tokens=10, fijos=1)
        assert conservados == ["x" * 5_000]

    def test_la_continuidad_es_lo_ultimo_que_se_toca(self) -> None:
        bloques = [
            Bloque(1, ("encargo",)),
            Bloque(3, tuple(f"continuidad {i}" for i in range(5))),
            Bloque(4, tuple("memoria " * 400 for _ in range(6))),
        ]
        ajustados = {b.numero: b for b in ajustar_al_total(bloques, techo_total=500)}
        assert len(ajustados[3].fragmentos) == 5, "la continuidad sigue entera"
        assert len(ajustados[4].fragmentos) < 6, "la memoria es la que cede"


class TestPaquete:
    async def test_tiene_los_siete_bloques_en_orden(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        paquete = await ensamblar(db, vectorizador, 2, settings=ajustes)
        assert [b.numero for b in paquete.bloques] == [1, 2, 3, 4, 5, 6, 7]

    async def test_nunca_excede_el_techo_total(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        """La primera de las tres propiedades del ensamblador."""
        paquete = await ensamblar(db, vectorizador, 2, settings=ajustes)
        assert paquete.tokens() <= TECHO_TOTAL

    async def test_un_capitulo_sin_escaleta_aborta(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        """Un bloque vacio no es un error; un capitulo sin encargo si."""
        with pytest.raises(EscaletaAusente):
            await ensamblar(db, vectorizador, 99, settings=ajustes)

    async def test_el_paquete_se_persiste_entero(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        paquete = await ensamblar(db, vectorizador, 2, settings=ajustes)
        identificador = await persistir(
            db, paquete, trace_span="capitulo_02 · escritor · intento_1"
        )
        async with db.execute(
            "SELECT * FROM paquete_contexto WHERE id = ?", (identificador,)
        ) as cursor:
            fila = await cursor.fetchone()
        assert fila is not None
        assert fila["capitulo_numero"] == 2
        assert fila["texto"] == paquete.texto()


class TestBloques:
    async def test_el_encargo_lleva_escenas_beats_y_hitos(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        texto_bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(1).texto()
        assert "conseguir roble americano" in texto_bloque
        assert "confianza -> duda" in texto_bloque, "los beats van en el encargo"
        assert "pide ayuda por primera vez" in texto_bloque, "el hito de arco tambien"
        assert "1200 palabras" in texto_bloque

    async def test_la_memoria_lleva_el_texto_integro_del_anterior(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        """La voz y el gancho se heredan de la prosa, no de un sumario."""
        bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(4)
        assert "La niebla subia del agua" in bloque.texto()

    async def test_la_continuidad_sale_del_cierre_del_anterior(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(3)
        assert "Manuel Ferrer" in bloque.texto()
        assert "el reloj del abuelo" in bloque.texto()

    async def test_los_anclajes_explicitos_entran_siempre(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        """Lo que el arquitecto decidio no compite con lo que la busqueda encontro."""
        bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(5)
        assert "roble americano llegaba a Cadiz" in bloque.texto()
        assert bloque.fijos >= 1

    async def test_el_anclaje_viaja_con_su_estado_epistemico(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        """El escritor tiene que saber si lo que usa es verificado o inferido."""
        bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(5)
        assert "[verificado]" in bloque.texto()

    async def test_las_reglas_llevan_los_diales_de_la_frontera(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        """Sin declararlos, esa politica la pondria el modelo."""
        texto_bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(6).texto()
        assert "grado_licencia" in texto_bloque
        assert "arcaismo" in texto_bloque
        assert "Beatriz" in texto_bloque, "las prohibidas llegan a quien escribe"

    async def test_la_personalizacion_lleva_lo_obligatorio_de_este_capitulo(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        texto_bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(7).texto()
        assert "OBLIGATORIO" in texto_bloque
        assert "reloj de bolsillo" in texto_bloque

    async def test_el_capitulo_1_no_tiene_memoria_ni_continuidad(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        paquete = await ensamblar(db, vectorizador, 1, settings=ajustes)
        assert paquete.bloque(3).fragmentos == ()
        assert paquete.bloque(4).fragmentos == ()
        assert paquete.bloque(1).fragmentos != (), "pero el encargo esta"


class TestAvisosQueViajan:
    async def test_los_tres_mas_recientes_llegan_al_encargo(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        """Sin este viaje, detectar en el capitulo 4 que un hito no ocurrio solo
        adelantaria la mala noticia."""
        for i in range(5):
            await arnes.registrar_incidencia(
                db,
                capitulo_version_id=novela.version_capitulo_1,
                validador="ejecucion_escaleta",
                severidad="aviso",
                mensaje=f"El beat {i} no llego a ocurrir",
            )
        texto_bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(1).texto()
        assert "El beat 4 no llego a ocurrir" in texto_bloque
        assert "El beat 0 no llego a ocurrir" not in texto_bloque, "solo los tres ultimos"

    async def test_lo_bloqueante_no_viaja(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        """Una incidencia bloqueante volvio al editor en su momento; no es un pendiente."""
        await arnes.registrar_incidencia(
            db,
            capitulo_version_id=novela.version_capitulo_1,
            validador="guardrail_prohibidas",
            severidad="bloqueante",
            mensaje="aparecio un termino prohibido",
        )
        texto_bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(1).texto()
        assert "termino prohibido" not in texto_bloque


class TestRecuperacionDeterminista:
    async def test_dos_ensamblados_identicos_dan_el_mismo_paquete(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        """Con las mismas entradas salen los mismos vecinos, siempre."""
        primero = await ensamblar(db, vectorizador, 2, settings=ajustes)
        segundo = await ensamblar(db, vectorizador, 2, settings=ajustes)
        assert primero.texto() == segundo.texto()

    async def test_la_busqueda_anade_lo_que_la_escaleta_no_previo(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba,
        vectorizador: VectorizadorFalso, ajustes: Settings,
    ) -> None:
        await indice.indexar_hecho(
            db,
            vectorizador,
            hecho_id=novela.hecho_suelto,
            enunciado="Las tabernas del muelle abrian antes del amanecer",
            estado="inferido",
            dimension="mentalidad",
        )
        bloque = (await ensamblar(db, vectorizador, 2, settings=ajustes)).bloque(5)
        assert "tabernas del muelle" in bloque.texto()
