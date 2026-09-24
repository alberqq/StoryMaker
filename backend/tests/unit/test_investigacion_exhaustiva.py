"""spec: §4.2 · arq: §4, §15

Pruebas del modo exhaustivo de la investigación.

Lo que se comprueba es lo que el modo promete y lo que no puede romper: que corre una
sesión por dimensión más las dos dirigidas por el brief, que una sesión que falla se salta
sin tumbar a las demás, que **ningún dato personal sale por la puerta a internet** aunque
el comprador lo haya escrito donde no tocaba, y que el modo viaja con la novela.
"""

from __future__ import annotations

import json
from typing import Any

import aiosqlite
import pytest
from dobles import guion
from dobles.agente_falso import TransporteFalso
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.agents.techos import TECHOS, Perfil
from storymaker.commons.config import Settings
from storymaker.commons.db.repos import arnes, intake
from storymaker.commons.graph.dependencias import Dependencias, usando
from storymaker.commons.graph.estado import estado_inicial
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.investigation import informe, nodos

PERIODO, LUGAR = "Siglo de Oro (1572-1576)", "Salamanca"


def brief(**cambios: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "nombre_homenajeado": "Tomas Aldecoa Villarreal",
        "fecha_nacimiento": "1961-11-09",
        "rol_epoca": "impresor y encuadernador",
        "elementos_personalizacion": [{"tipo": "anecdota", "valor": "lee en voz alta"}],
        "personajes_historicos": [{"nombre": "fray Luis de Leon", "debe_aparecer": True}],
        "evento_ancla": "el regreso de fray Luis a su catedra",
    }
    base.update(cambios)
    return base


async def guardar(db: aiosqlite.Connection, fase_run: int, datos: dict[str, Any]) -> None:
    await intake.guardar_brief(
        db, fase_run_id=fase_run, json_brief=json.dumps(datos), hash_brief="h"
    )
    await db.commit()


def dependencias(db: aiosqlite.Connection, transporte: TransporteFalso) -> Dependencias:
    return Dependencias(
        db=db,
        settings=Settings(_env_file=None),
        transporte=transporte,
        vectorizador=VectorizadorFalso(),
        observador=ObservadorNulo(),
    )


class TestPerfil:
    def test_una_busqueda_y_una_pagina_con_un_techo_menor_que_la_sesion_unica(self) -> None:
        """Ninguna sesión dirigida lleva más de una página: el peor caso no sube."""
        dirigido = TECHOS[Perfil.INVESTIGADOR_DIRIGIDO]
        assert dict(dirigido.cuota_de_herramientas) == {"WebSearch": 1, "WebFetch": 1}
        assert dirigido.total < TECHOS[Perfil.INVESTIGADOR_INICIAL].total

    def test_el_modo_viaja_en_el_estado_y_por_defecto_es_el_estandar(self) -> None:
        comun: dict[str, Any] = {
            "novela": "n.db", "fase_run_id": 1, "n_capitulos": 10,
            "max_intentos": 2, "huecos": 5, "gates_enabled": False,
        }
        assert estado_inicial(**comun)["investigacion"] == "estandar"
        assert estado_inicial(**comun, investigacion="exhaustiva")["investigacion"] == "exhaustiva"
        assert Settings(_env_file=None).investigacion == "estandar"


class TestEncargos:
    async def test_seis_por_dimension_y_dos_dirigidas_por_el_brief(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        await guardar(db, fase_run, brief())
        encargos = await nodos.encargos_dirigidos(db, PERIODO, LUGAR, "")
        nombres = [e.nombre for e in encargos]
        assert len(nombres) == 8
        assert nombres[-2:] == ["personajes y evento ancla", "oficio"]
        assert "fray Luis de Leon" in encargos[-2].prompt
        assert "impresor y encuadernador" in encargos[-1].prompt

    async def test_sin_personajes_ni_evento_ni_oficio_quedan_las_seis(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        await guardar(
            db, fase_run, brief(personajes_historicos=[], evento_ancla=None, rol_epoca="")
        )
        assert len(await nodos.encargos_dirigidos(db, PERIODO, LUGAR, "")) == 6

    async def test_el_comentario_del_autor_llega_a_todas(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        await guardar(db, fase_run, brief())
        encargos = await nodos.encargos_dirigidos(db, PERIODO, LUGAR, "- mas sobre la imprenta")
        assert all("mas sobre la imprenta" in e.prompt for e in encargos)


class TestSesiones:
    async def test_corren_las_ocho_y_el_informe_da_una_linea_por_sesion(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        await guardar(db, fase_run, brief())
        falso = TransporteFalso().preparar(
            Perfil.INVESTIGADOR_DIRIGIDO, *[guion.investigacion() for _ in range(8)]
        )
        with usando(dependencias(db, falso)):
            escritos = await nodos.investigar_exhaustiva(PERIODO, LUGAR, fase_run_id=fase_run)

        assert falso.veces(Perfil.INVESTIGADOR_DIRIGIDO) == 8
        assert falso.veces(Perfil.INVESTIGADOR_INICIAL) == 0
        assert len(escritos) == 8 * 6
        resultado = await informe.construir(db, fase_run)
        assert len(resultado.sesiones_dirigidas) == 8
        assert "Investigacion exhaustiva" in resultado.como_texto()

    async def test_una_sesion_invalida_se_salta_y_las_demas_siguen(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """Que falle una búsqueda no justifica perder las otras siete."""
        await guardar(db, fase_run, brief())
        falso = TransporteFalso().preparar(
            Perfil.INVESTIGADOR_DIRIGIDO,
            "esto no es json",
            "tampoco esto",
            *[guion.investigacion() for _ in range(7)],
        )
        with usando(dependencias(db, falso)):
            escritos = await nodos.investigar_exhaustiva(PERIODO, LUGAR, fase_run_id=fase_run)

        assert len(escritos) == 7 * 6
        lineas = await arnes.incidencias_sin_capitulo(db, "investigacion_dirigida")
        assert sum("saltada" in linea for linea in lineas) == 1

    async def test_un_dato_personal_en_el_brief_no_sale_a_internet(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        """El comprador escribió el nombre del homenajeado dentro del oficio."""
        await guardar(
            db, fase_run, brief(rol_epoca="impresor, como Tomas Aldecoa Villarreal")
        )
        falso = TransporteFalso().preparar(
            Perfil.INVESTIGADOR_DIRIGIDO, *[guion.investigacion() for _ in range(8)]
        )
        with usando(dependencias(db, falso)):
            await nodos.investigar_exhaustiva(PERIODO, LUGAR, fase_run_id=fase_run)

        assert falso.veces(Perfil.INVESTIGADOR_DIRIGIDO) == 7
        lineas = await arnes.incidencias_sin_capitulo(db, "investigacion_dirigida")
        assert any("oficio: saltada" in linea and "dato personal" in linea for linea in lineas)


@pytest.mark.parametrize("modo", ["estandar", "exhaustiva"])
async def test_el_nodo_research_elige_la_sesion_segun_el_modo(
    db: aiosqlite.Connection, fase_run: int, modo: str
) -> None:
    await guardar(db, fase_run, brief())
    falso = TransporteFalso()
    falso.preparar(Perfil.INVESTIGADOR_INICIAL, guion.investigacion())
    falso.preparar(Perfil.INVESTIGADOR_DIRIGIDO, *[guion.investigacion() for _ in range(8)])
    estado = estado_inicial(
        novela="n.db", fase_run_id=fase_run, n_capitulos=10, max_intentos=2, huecos=5,
        gates_enabled=False, investigacion=modo,
    )
    with usando(dependencias(db, falso)):
        await nodos.research(estado)

    esperado = Perfil.INVESTIGADOR_DIRIGIDO if modo == "exhaustiva" else Perfil.INVESTIGADOR_INICIAL
    assert set(falso.pedidos) == {esperado}


class TestSinResultado:
    """La tercera novela del día —siglo II, Cáceres— se detuvo aquí sin un solo hecho."""

    def test_la_denegacion_le_dice_que_entregue_ya(self) -> None:
        from storymaker.commons.agents.hooks import CuotaDeHerramientas

        cuota = CuotaDeHerramientas.para(Perfil.INVESTIGADOR_INICIAL)
        for _ in range(3):
            cuota.decidir("WebSearch")
        denegada = cuota.decidir("WebSearch")
        assert denegada["permissionDecision"] == "deny"
        assert "entrega ahora" in denegada["permissionDecisionReason"]

    async def test_la_sesion_unica_sin_json_no_detiene_la_fase(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        await guardar(db, fase_run, brief())
        falso = TransporteFalso().preparar(
            Perfil.INVESTIGADOR_INICIAL, "voy a buscar mas", "sigo buscando"
        )
        with usando(dependencias(db, falso)):
            escritos = await nodos.investigar(PERIODO, LUGAR, fase_run_id=fase_run)

        assert escritos == []
        lineas = await arnes.incidencias_sin_capitulo(db, "investigacion_dirigida")
        assert any("sesion unica: sin resultado" in linea for linea in lineas)
