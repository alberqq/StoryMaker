"""spec: §4.6 · arq: §4

La elección del Autor en el gate de Regeneration y el alcance de un cambio de personaje.

Lo que se comprueba es lo que impidió quitar el apellido a un protagonista: que la fila
tocada es **la que el Autor eligió** y no la que devuelva una segunda búsqueda, que una
petición sin valor nuevo **no escribe nada**, y que cambiar un personaje regenera **todos
los capítulos donde aparece**, no solo los de su arco.
"""

from __future__ import annotations

import aiosqlite
from dobles.fabrica import NovelaDePrueba, poblar
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.db.repos import texto
from storymaker.regeneration import cambio, nodos
from storymaker.regeneration.esquemas import ObjetoDelCambio


async def test_la_eleccion_del_autor_apunta_a_su_fila(db: aiosqlite.Connection) -> None:
    novela: NovelaDePrueba = await poblar(db)
    resuelto = await cambio.resolver(
        db, VectorizadorFalso(), f"personaje:{novela.homenajeado} nombre=Manuel"
    )
    assert resuelto is not None
    assert resuelto.objeto is ObjetoDelCambio.PERSONAJE
    assert resuelto.fila_id == novela.homenajeado
    assert resuelto.campo == "nombre"
    assert (resuelto.antes, resuelto.despues) == ("Manuel Ferrer", "Manuel")


async def test_una_peticion_sin_valor_nuevo_no_toca_nada(db: aiosqlite.Connection) -> None:
    """Antes, la frase entera se escribía como valor en la fila más parecida."""
    await poblar(db)
    assert await cambio.resolver(
        db, VectorizadorFalso(), "quiero que no aparezca el apellido"
    ) is None


async def test_una_fila_o_un_campo_que_no_existen_no_se_aplican(db: aiosqlite.Connection) -> None:
    novela = await poblar(db)
    assert await cambio.resolver_eleccion(db, "personaje:9999 nombre=X") is None
    assert await cambio.resolver_eleccion(
        db, f"personaje:{novela.homenajeado} inventado=X"
    ) is None


async def test_un_personaje_se_regenera_donde_aparece_y_no_solo_en_su_arco(
    db: aiosqlite.Connection, fase_run: int
) -> None:
    novela = await poblar(db)
    version = await texto.insertar_capitulo_version(
        db, capitulo_id=novela.capitulo_2, fase_run_id=novela.fase_run, texto="Manuel llega."
    )
    await texto.aprobar_capitulo(db, version)
    await texto.insertar_continuidad(
        db, capitulo_version_id=version, personaje_id=novela.homenajeado
    )
    alcance = await nodos.calcular_alcance(
        db, objeto=ObjetoDelCambio.PERSONAJE, fila_id=novela.homenajeado
    )
    assert 2 in alcance.a_regenerar
