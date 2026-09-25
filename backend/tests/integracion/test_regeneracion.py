"""spec: §4.6 · arq: §4, §9 · verif. G1, G3, G5

Detalla `specs/escritura/spec.md` §9.

**La Fase 6 de extremo a extremo: un cambio en una novela publicada llega a una versión nueva.**

Se publica una novela de dos capítulos en batch, se siembra que el inspector sale en el
capítulo 1, y se aprueba en el gate de Regeneración el cambio de su nombre. Lo que se mira es
la base:

- el capítulo donde sale se **regenera** —fila nueva en `capitulo_version`—;
- el posterior que no lo usa pasa por los validadores de coste cero y **se reutiliza**, sin
  una llamada al escritor;
- si el posterior no pasa la cronología, **se reescribe él también**, y solo él;
- la versión 2 comparte con la 1 lo no tocado, y **la 1 sigue entera**.

Antes de esta prueba, aprobar el gate reanudaba un grafo ya terminado y no pasaba nada: la
invocación se cerraba como completada sin haber cambiado una fila.
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest
from dobles import guion
from dobles.agente_falso import TransporteFalso
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.agents.techos import Perfil
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela, crear_novela
from storymaker.commons.db.repos import arnes
from storymaker.commons.graph.run import Arranque, invocar, regenerar
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.gates.decisiones import aplicar
from storymaker.writing.esquemas import SalidaEscritor

CAPITULOS = 2
NUEVO = "Las aulas rurales se calentaban con brasero de picon."
#: El inspector del guion: no sale en ninguna escena hasta que la prueba lo siembra.
INSPECTOR = 2
RENOMBRADO = "Don Anselmo"
CAMBIO = f"personaje:{INSPECTOR} nombre={RENOMBRADO}"


@pytest.fixture
def ajustes(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        directorio_proyectos=tmp_path / "proyectos",
        gates_enabled=False,
        reintentos_por_capitulo=2,
    )


#: El nombre del inspector en el guion, antes del cambio.
INSPECTOR_ANTES = "Don Emeterio"


def _nombrando(numero: int, nombre: str) -> SalidaEscritor:
    """Un capítulo del guion que nombra a alguien, con la misma longitud que los demás."""
    base = guion.capitulo(numero, palabras=guion.PALABRAS_POR_CAPITULO - 3)
    return SalidaEscritor(texto=f"{base.texto} {nombre} llego tarde.")


def _transporte_inicial(*, nombra_en_2: bool = False) -> TransporteFalso:
    """El guion completo; con `nombra_en_2`, el capítulo 2 menciona al inspector."""
    segundo = _nombrando(2, INSPECTOR_ANTES) if nombra_en_2 else guion.capitulo(2)
    falso = TransporteFalso()
    falso.preparar(Perfil.ENTREVISTADOR, guion.entrevista(CAPITULOS))
    falso.preparar(Perfil.INVESTIGADOR_INICIAL, guion.investigacion())
    falso.preparar(Perfil.VERIFICADOR, guion.verificacion())
    falso.preparar(Perfil.ARQUITECTO, guion.arquitectura(CAPITULOS))
    falso.preparar(Perfil.INVESTIGADOR_MICRO, *[guion.hueco_resuelto() for _ in range(5)])
    # Las colas se sirven en orden: si sobra un capítulo 1, el 2 se lo lleva.
    falso.preparar(Perfil.ESCRITOR, guion.capitulo(1), *[segundo] * 5)
    falso.preparar(Perfil.EDITOR, *[segundo] * 4)
    falso.preparar(Perfil.EXTRACTOR_CAPITULO, *[guion.extraccion(n) for n in (1, 1, 1, 2, 2, 2)])
    falso.preparar(Perfil.JUEZ, guion.juicio(), guion.juicio())
    return falso


def _transporte_de_regeneracion(*capitulos: int) -> TransporteFalso:
    """Solo lo que la regeneración puede pedir: escritor, editor, extractor y juez."""
    falso = TransporteFalso()
    falso.preparar(Perfil.ESCRITOR, *[guion.capitulo(n) for n in capitulos for _ in range(3)])
    falso.preparar(Perfil.EDITOR, *[guion.capitulo(n) for n in capitulos for _ in range(2)])
    falso.preparar(
        Perfil.EXTRACTOR_CAPITULO, *[guion.extraccion(n) for n in capitulos for _ in range(3)]
    )
    falso.preparar(Perfil.JUEZ, guion.juicio(), guion.juicio())
    return falso


async def _uno(db: aiosqlite.Connection, consulta: str, *args: object) -> object:
    async with db.execute(consulta, args) as cursor:
        fila = await cursor.fetchone()
    return fila[0] if fila is not None else None


async def _aprobada(db: aiosqlite.Connection, numero: int) -> int:
    valor = await _uno(
        db,
        """
        SELECT MAX(cv.id) FROM capitulo_version cv
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE pc.numero = ? AND cv.estado = 'aprobado'
        """,
        numero,
    )
    assert valor is not None, f"el capitulo {numero} no tiene version aprobada"
    return int(str(valor))


async def _manifiesto(db: aiosqlite.Connection, numero: int) -> list[int]:
    async with db.execute(
        """
        SELECT vc.capitulo_version_id
          FROM version_capitulo vc
          JOIN version_novela v ON v.id = vc.version_id
          JOIN capitulo_version cv ON cv.id = vc.capitulo_version_id
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE v.numero = ?
         ORDER BY pc.numero
        """,
        (numero,),
    ) as cursor:
        return [int(f[0]) for f in await cursor.fetchall()]


async def _publicada(ruta: Path, ajustes: Settings, *, nombra_en_2: bool = False) -> None:
    await crear_novela(ruta)
    resultado = await invocar(
        ruta,
        Arranque(n_capitulos=CAPITULOS),
        settings=ajustes,
        transporte=_transporte_inicial(nombra_en_2=nombra_en_2),
        vectorizador=VectorizadorFalso(),
        observador=ObservadorNulo(),
    )
    assert resultado.nodo_final == "Idle", resultado.error


async def _sembrar_aparicion(db: aiosqlite.Connection, personaje_id: int, numero: int) -> None:
    """El personaje sale en la escena del capítulo `numero`, según la escaleta."""
    escena = await _uno(
        db,
        """
        SELECT e.id FROM plan_escena e JOIN plan_capitulo c ON c.id = e.capitulo_id
         WHERE c.numero = ? ORDER BY e.orden LIMIT 1
        """,
        numero,
    )
    await db.execute(
        "INSERT INTO plan_escena_personaje (escena_id, personaje_id) VALUES (?, ?)",
        (escena, personaje_id),
    )


async def _sembrar_evento_imposible(db: aiosqlite.Connection, numero: int) -> None:
    """Un evento del capítulo con la homenajeada antes de nacer: Lean lo tumba."""
    version = await _aprobada(db, numero)
    cursor = await db.execute(
        "INSERT INTO cronologia_evento (clave, descripcion, momento, origen, capitulo_version_id)"
        " VALUES (?, 'La maestra ya da clase', '1900-09-15', 'narrativo', ?)",
        (f"cap{numero}-v{version}-imposible", version),
    )
    homenajeada = await _uno(db, "SELECT MIN(id) FROM canon_personaje")
    await db.execute(
        "INSERT INTO cronologia_participante (evento_id, personaje_id) VALUES (?, ?)",
        (cursor.lastrowid, homenajeada),
    )


async def _pedir_y_decidir(ruta: Path, decision: str, comentario: str) -> None:
    """Lo que hacen `POST /cambios` y `storymaker decidir`: abrir el gate y decidirlo."""
    async with abrir_novela(ruta) as db:
        fase_run = await arnes.abrir_fase_run(db, "regeneration")
        await arnes.abrir_gate(db, fase_run)
        await aplicar(db, ObservadorNulo(), decision, comentario)
        await db.commit()


async def _regenerar(
    ruta: Path, ajustes: Settings, transporte: TransporteFalso, *, aprobada: bool = True
):  # type: ignore[no-untyped-def]
    return await regenerar(
        ruta,
        settings=ajustes,
        aprobada=aprobada,
        transporte=transporte,
        vectorizador=VectorizadorFalso(),
        observador=ObservadorNulo(),
    )


class TestCambioDeUnPersonaje:
    async def test_regenera_el_que_lo_usa_y_reutiliza_el_posterior(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "hecho.db"
        await _publicada(ruta, ajustes)
        async with abrir_novela(ruta) as db:
            await _sembrar_aparicion(db, INSPECTOR, 1)
            await db.commit()
            v1 = await _manifiesto(db, 1)
        await _pedir_y_decidir(ruta, "aprobar", CAMBIO)

        transporte = _transporte_de_regeneracion(1)
        resultado = await _regenerar(ruta, ajustes, transporte)

        assert resultado.nodo_final == "Idle", resultado.error
        async with abrir_novela(ruta) as db:
            nombre = await _uno(db, "SELECT nombre FROM canon_personaje WHERE id = ?", INSPECTOR)
            assert nombre == RENOMBRADO
            v2 = await _manifiesto(db, 2)
            assert await _manifiesto(db, 1) == v1, "la version 1 tiene que seguir entera"
            assert v2[0] != v1[0], "el capitulo 1 usa el hecho y se regenera"
            assert v2[1] == v1[1], "el capitulo 2 pasa el coste cero y se reutiliza"
            estado = await _uno(db, "SELECT estado FROM capitulo_version WHERE id = ?", v1[1])
            assert estado == "aprobado"
        assert transporte.veces(Perfil.ESCRITOR) == 1, "solo se escribe el capitulo 1"

    async def test_el_posterior_que_no_pasa_lean_se_reescribe(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "lean.db"
        await _publicada(ruta, ajustes)
        async with abrir_novela(ruta) as db:
            await _sembrar_aparicion(db, INSPECTOR, 1)
            await _sembrar_evento_imposible(db, 2)
            await db.commit()
            v1 = await _manifiesto(db, 1)
        await _pedir_y_decidir(ruta, "aprobar", CAMBIO)

        transporte = _transporte_de_regeneracion(1, 2)
        resultado = await _regenerar(ruta, ajustes, transporte)

        assert resultado.nodo_final == "Idle", resultado.error
        async with abrir_novela(ruta) as db:
            v2 = await _manifiesto(db, 2)
            assert v2[0] != v1[0] and v2[1] != v1[1]
            estado = await _uno(db, "SELECT estado FROM capitulo_version WHERE id = ?", v1[1])
            assert estado == "invalidado", "el que Lean tumba no vuelve a aprobado"
            assert await _manifiesto(db, 1) == v1
        assert transporte.veces(Perfil.ESCRITOR) == 2


class TestElNombreLlegaAlTexto:
    """Lo que la primera regeneración real no hizo: que el nombre nuevo acabe en la prosa."""

    async def test_el_texto_que_nombra_entra_en_el_alcance_y_se_repara(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "nombre.db"
        await _publicada(ruta, ajustes, nombra_en_2=True)
        async with abrir_novela(ruta) as db:
            await db.execute("UPDATE plan_beat SET accion = ?", (f"{INSPECTOR_ANTES} entra",))
            await db.commit()
            v1 = await _manifiesto(db, 1)
        await _pedir_y_decidir(ruta, "aprobar", CAMBIO)

        # El escritor sigue diciendo el nombre viejo; el editor lo corrige.
        transporte = TransporteFalso()
        transporte.preparar(Perfil.ESCRITOR, _nombrando(2, INSPECTOR_ANTES))
        transporte.preparar(Perfil.EDITOR, _nombrando(2, RENOMBRADO))
        transporte.preparar(Perfil.EXTRACTOR_CAPITULO, *[guion.extraccion(2)] * 2)
        transporte.preparar(Perfil.JUEZ, guion.juicio())
        resultado = await _regenerar(ruta, ajustes, transporte)

        assert resultado.nodo_final == "Idle", resultado.error
        assert resultado.nota is None, resultado.nota
        async with abrir_novela(ruta) as db:
            v2 = await _manifiesto(db, 2)
            assert v2[0] == v1[0], "el capitulo 1 no lo nombra y se reutiliza"
            assert v2[1] != v1[1], "el capitulo 2 lo nombra en el texto y se regenera"
            nuevo = str(await _uno(db, "SELECT texto FROM capitulo_version WHERE id = ?", v2[1]))
            assert "Emeterio" not in nuevo and RENOMBRADO in nuevo
            beats = await _uno(db, "SELECT COUNT(*) FROM plan_beat WHERE accion LIKE '%Emeterio%'")
            assert beats == 0, "la escaleta ya no dice el nombre viejo"
            retirado = await _uno(
                db, "SELECT COUNT(*) FROM incidencia WHERE validador = 'valor_retirado'"
            )
            assert retirado == 1
        assert transporte.veces(Perfil.EDITOR) == 1


class TestSinNadaQueRegenerar:
    async def test_una_fila_que_nadie_usa_se_cambia_sin_version_nueva(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "nadie.db"
        await _publicada(ruta, ajustes)
        await _pedir_y_decidir(ruta, "aprobar", CAMBIO)

        transporte = _transporte_de_regeneracion()
        resultado = await _regenerar(ruta, ajustes, transporte)

        assert resultado.nota and "Ningun capitulo" in resultado.nota
        async with abrir_novela(ruta) as db:
            nombre = await _uno(db, "SELECT nombre FROM canon_personaje WHERE id = ?", INSPECTOR)
            assert nombre == RENOMBRADO
            assert await _uno(db, "SELECT COUNT(*) FROM version_novela") == 1
        assert transporte.veces(Perfil.ESCRITOR) == 0

    async def test_un_hecho_del_corpus_sellado_no_se_cambia(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "sellado.db"
        await _publicada(ruta, ajustes)
        await _pedir_y_decidir(ruta, "aprobar", f"hecho:1 enunciado={NUEVO}")

        resultado = await _regenerar(ruta, ajustes, _transporte_de_regeneracion())

        assert resultado.nota and "sellado" in resultado.nota
        async with abrir_novela(ruta) as db:
            assert await _uno(db, "SELECT enunciado FROM mundo_hecho WHERE id = 1") != NUEVO

    async def test_sin_fila_ni_valor_no_se_toca_nada(
        self, tmp_path: Path, ajustes: Settings
    ) -> None:
        ruta = tmp_path / "proyectos" / "vaga.db"
        await _publicada(ruta, ajustes)
        async with abrir_novela(ruta) as db:
            antes = await _uno(db, "SELECT enunciado FROM mundo_hecho WHERE id = 1")
        await _pedir_y_decidir(ruta, "aprobar", "que no salga la estufa")

        resultado = await _regenerar(ruta, ajustes, _transporte_de_regeneracion())

        assert resultado.nota and "no se ha cambiado nada" in resultado.nota
        async with abrir_novela(ruta) as db:
            assert await _uno(db, "SELECT enunciado FROM mundo_hecho WHERE id = 1") == antes
            assert await _uno(db, "SELECT COUNT(*) FROM version_novela") == 1

    async def test_rehacer_descarta_la_peticion(self, tmp_path: Path, ajustes: Settings) -> None:
        ruta = tmp_path / "proyectos" / "descartada.db"
        await _publicada(ruta, ajustes)
        async with abrir_novela(ruta) as db:
            await _sembrar_aparicion(db, INSPECTOR, 1)
            await db.commit()
        await _pedir_y_decidir(ruta, "rehacer", CAMBIO)

        resultado = await _regenerar(ruta, ajustes, _transporte_de_regeneracion(), aprobada=False)

        assert resultado.nota and "descartada" in resultado.nota
        async with abrir_novela(ruta) as db:
            nombre = await _uno(db, "SELECT nombre FROM canon_personaje WHERE id = ?", INSPECTOR)
            assert nombre != RENOMBRADO
            assert await _uno(db, "SELECT COUNT(*) FROM version_novela") == 1
            assert await _uno(db, "SELECT estado FROM fase_run ORDER BY id DESC LIMIT 1") == (
                "abortada"
            )
