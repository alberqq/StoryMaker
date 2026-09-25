"""spec: §4.6 · arq: §2, §4

Detalla `specs/escritura/spec.md` §9.

El valor retirado de un cambio de nombre: qué pares salen, dónde se encuentran y cómo se
sustituyen. Son funciones puras salvo `propagar`, que se prueba sobre una novela sembrada.
"""

from __future__ import annotations

import aiosqlite
from dobles.fabrica import poblar

from storymaker.commons.validation.modelos import Severidad
from storymaker.regeneration import retirados
from storymaker.regeneration.esquemas import ObjetoDelCambio

PERSONAJE = ObjetoDelCambio.PERSONAJE


class TestPares:
    def test_un_nombre_de_una_palabra_da_un_par(self) -> None:
        assert retirados.pares(PERSONAJE, "nombre", "Cayo", "Amaro") == [("Cayo", "Amaro")]

    def test_con_las_mismas_palabras_entra_cada_una_que_cambia(self) -> None:
        pares = retirados.pares(PERSONAJE, "nombre", "Don Emeterio", "Don Anselmo")
        assert pares == [("Don Emeterio", "Don Anselmo"), ("Emeterio", "Anselmo")]

    def test_las_palabras_cortas_no_entran(self) -> None:
        pares = retirados.pares(PERSONAJE, "nombre", "Ana de Luz", "Ana la Luz")
        assert pares == [("Ana de Luz", "Ana la Luz")]

    def test_lo_que_no_es_un_nombre_no_da_pares(self) -> None:
        assert retirados.pares(ObjetoDelCambio.ESCENARIO, "descripcion", "Aula", "Taller") == []
        assert retirados.pares(PERSONAJE, "objetivo", "vivir", "morir") == []

    def test_sin_cambio_no_hay_pares(self) -> None:
        assert retirados.pares(PERSONAJE, "nombre", "Cayo", " Cayo ") == []


class TestEnElTexto:
    def test_se_busca_como_palabra_entera(self) -> None:
        pares = [("Cayo", "Amaro")]
        assert retirados.aparece("Llego Cayo al alba.", pares) == ["Cayo"]
        assert retirados.aparece("Cayetano llego.", pares) == []

    def test_sustituir_empieza_por_el_nombre_entero(self) -> None:
        pares = retirados.pares(PERSONAJE, "nombre", "Don Emeterio", "Don Anselmo")
        assert retirados.sustituir("Don Emeterio y Emeterio.", pares) == "Don Anselmo y Anselmo."

    def test_cada_valor_que_sigue_es_una_incidencia_bloqueante(self) -> None:
        pares = retirados.pares(PERSONAJE, "nombre", "Don Emeterio", "Don Anselmo")
        incidencias = retirados.incidencias("Emeterio entro.", pares)
        assert [i.validador for i in incidencias] == [retirados.VALIDADOR]
        assert incidencias[0].severidad is Severidad.BLOQUEANTE
        assert "Anselmo" in (incidencias[0].propuesta or "")


class TestPropagar:
    async def test_reescribe_la_escaleta_y_no_toca_el_corpus(
        self, db: aiosqlite.Connection
    ) -> None:
        await poblar(db)
        await db.execute("UPDATE plan_beat SET accion = 'Cayo abre la puerta'")
        async with db.execute("SELECT enunciado FROM mundo_hecho ORDER BY id") as cursor:
            corpus = [f[0] for f in await cursor.fetchall()]

        cambiadas = await retirados.propagar(db, [("Cayo", "Amaro")])

        async with db.execute("SELECT DISTINCT accion FROM plan_beat") as cursor:
            assert [f[0] for f in await cursor.fetchall()] == ["Amaro abre la puerta"]
        async with db.execute("SELECT enunciado FROM mundo_hecho ORDER BY id") as cursor:
            assert [f[0] for f in await cursor.fetchall()] == corpus
        assert cambiadas >= 1
