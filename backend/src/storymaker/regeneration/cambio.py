"""spec: §4.6 · arq: §2 principio 4, §8, §16.2

Resolver la petición a una fila y **modificar la fila, nunca el texto**.

«El canon manda sobre el texto» es uno de los seis principios, y esta es su implementación:
un cambio se aplica al hecho en la base y el texto se regenera como consecuencia. Nunca al
revés — un `buscar-y-reemplazar` sobre la prosa deja mintiendo a la biblia, y el siguiente
capítulo se escribiría contra un canon que ya no describe la novela.

Toda modificación queda en `audit_log` y, si viene de una persona, también en
`edicion_humana`. La intervención del Autor se traza igual que la de un agente.
"""

from __future__ import annotations

import re

import aiosqlite

from storymaker.commons.db.repos import arnes, mundo
from storymaker.commons.embeddings import indice
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.regeneration.esquemas import CambioResuelto, Candidato, ObjetoDelCambio


async def buscar_candidatos(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    peticion: str,
    *,
    k: int = 5,
) -> list[Candidato]:
    """Los candidatos a ser la fila que hay que tocar, ordenados por proximidad.

    Se busca en el corpus y en el canon, porque una petición del lector puede referirse a
    cualquiera de los dos: «el perro se llama Nala» es canon; «el bloqueo fue en abril» es
    corpus.
    """
    candidatos: list[Candidato] = []

    for vecino in await indice.buscar_hechos(db, vectorizador, peticion, k=k):
        fila = await mundo.hecho_por_id(db, vecino.id)
        if fila is not None:
            candidatos.append(
                Candidato(
                    objeto=ObjetoDelCambio.HECHO,
                    fila_id=vecino.id,
                    descripcion=str(fila["enunciado"]),
                    distancia=vecino.distancia,
                )
            )

    for tabla, fila_id, distancia in await indice.buscar_canon(db, vectorizador, peticion, k=k):
        objeto = {
            "canon_personaje": ObjetoDelCambio.PERSONAJE,
            "canon_escenario": ObjetoDelCambio.ESCENARIO,
            "canon_glosario": ObjetoDelCambio.GLOSARIO,
        }.get(tabla)
        if objeto is None:
            continue
        descripcion = await _describir(db, tabla, fila_id)
        candidatos.append(
            Candidato(
                objeto=objeto, fila_id=fila_id, descripcion=descripcion, distancia=distancia
            )
        )

    return sorted(candidatos, key=lambda c: c.distancia)


async def _describir(db: aiosqlite.Connection, tabla: str, fila_id: int) -> str:
    columna = {
        "canon_personaje": "nombre",
        "canon_escenario": "descripcion",
        "canon_glosario": "termino",
    }
    campo = columna.get(tabla, "id")
    async with db.execute(
        f"SELECT {campo} AS valor FROM {tabla} WHERE id = ?",  # noqa: S608
        (fila_id,),
    ) as cursor:
        fila = await cursor.fetchone()
    return str(fila["valor"]) if fila is not None else ""


TABLA_DE = {
    ObjetoDelCambio.HECHO: "mundo_hecho",
    ObjetoDelCambio.PERSONAJE: "canon_personaje",
    ObjetoDelCambio.ESCENARIO: "canon_escenario",
    ObjetoDelCambio.GLOSARIO: "canon_glosario",
}


#: El campo que se toca cuando la petición no nombra ninguno. Es el que `_describir` enseña
#: en el gate, de modo que el Autor confirma exactamente lo que va a cambiar.
CAMPO_POR_DEFECTO = {
    ObjetoDelCambio.HECHO: "enunciado",
    ObjetoDelCambio.PERSONAJE: "nombre",
    ObjetoDelCambio.ESCENARIO: "descripcion",
    ObjetoDelCambio.GLOSARIO: "termino",
}


#: La decisión del Autor en el gate: qué fila eligió de entre los candidatos y qué valor le
#: da. «personaje:1 nombre=Manuel». Es lo que convierte «el Autor confirma» en un dato.
_ELECCION = re.compile(
    r"^\s*(hecho|personaje|escenario|glosario)\s*[:#]\s*(\d+)\s+(\w+)\s*=\s*(.+?)\s*$",
    re.DOTALL,
)


async def _valor_actual(
    db: aiosqlite.Connection, objeto: ObjetoDelCambio, fila_id: int, campo: str
) -> str | None:
    """El valor de ese campo en esa fila, o `None` si la fila o el campo no existen."""
    tabla = TABLA_DE[objeto]
    async with db.execute(f"PRAGMA table_info({tabla})") as cursor:
        columnas = {str(f["name"]) for f in await cursor.fetchall()}
    if campo not in columnas:
        return None
    async with db.execute(
        f"SELECT {campo} FROM {tabla} WHERE id = ?", (fila_id,)  # noqa: S608
    ) as cursor:
        fila = await cursor.fetchone()
    return None if fila is None else str(fila[campo] or "")


async def resolver_eleccion(db: aiosqlite.Connection, decision: str) -> CambioResuelto | None:
    """La fila y el valor que el Autor eligió en el gate, sin buscar nada.

    Es el camino de la spec (§4.6): los candidatos se enseñan y **el Autor confirma**. Volver
    a buscar al aprobar hacía que la fila tocada dependiera del texto del comentario y no de
    lo que el Autor había elegido, y así se llegó a apuntar a un personaje que no era.
    """
    encontrada = _ELECCION.match(decision)
    if encontrada is None:
        return None
    objeto = ObjetoDelCambio(encontrada.group(1))
    fila_id, campo, valor = int(encontrada.group(2)), encontrada.group(3), encontrada.group(4)
    antes = await _valor_actual(db, objeto, fila_id, campo)
    if antes is None:
        return None
    return CambioResuelto(
        objeto=objeto, fila_id=fila_id, campo=campo, antes=antes, despues=valor, motivo=decision
    )


async def resolver(
    db: aiosqlite.Connection, vectorizador: Vectorizador, peticion: str
) -> CambioResuelto | None:
    """Convierte la petición en lenguaje natural en el cambio concreto que se va a aplicar.

    La resolución la hace el arnés y la confirma el Autor, que es lo que permite al lector
    escribir «el perro se llama Nala» sin conocer ningún identificador. Se admite la forma
    `campo=valor` para cuando el Autor quiere ser explícito; sin ella se toca el campo que el
    gate ya le enseñó. **Ningún modelo participa en esto**: es búsqueda por similitud más una
    partición de cadena, y por eso la Fase 6 no tiene techo de contexto propio.

    Devuelve `None` si la búsqueda no encuentra a qué fila se refiere la petición. El nodo lo
    trata como alcance vacío y el gate lo enseña: es preferible una regeneración que no
    cambia nada a una que cambia la fila equivocada.
    """
    elegido_por_el_autor = await resolver_eleccion(db, peticion)
    if elegido_por_el_autor is not None:
        return elegido_por_el_autor

    campo, separador, valor = peticion.partition("=")
    if not separador:
        # Sin «campo=valor» no hay valor nuevo que escribir: tomar la frase entera como tal
        # escribiría «quiero que no aparezca el apellido» en el canon. Mejor no tocar nada.
        return None
    campo, valor = campo.strip(), valor.strip()
    consulta = valor or peticion

    candidatos = await buscar_candidatos(db, vectorizador, consulta, k=3)
    if not candidatos:
        return None

    elegido = candidatos[0]
    if not campo:
        campo = CAMPO_POR_DEFECTO[elegido.objeto]
    elif campo not in CAMPO_POR_DEFECTO.values():
        campo = CAMPO_POR_DEFECTO[elegido.objeto]

    return CambioResuelto(
        objeto=elegido.objeto,
        fila_id=elegido.fila_id,
        campo=campo,
        antes=elegido.descripcion,
        despues=valor,
        motivo=peticion,
    )


async def aplicar(
    db: aiosqlite.Connection,
    vectorizador: Vectorizador,
    cambio: CambioResuelto,
    *,
    actor: str = "autor",
    fase_run_id: int | None = None,
) -> None:
    """Modifica la fila, la reindexa y lo deja escrito en el audit log.

    El reembedding va aquí y no más tarde: si la fila cambiara y su vector no, la búsqueda
    semántica seguiría devolviendo el texto anterior a la corrección, que es justo lo
    contrario de lo que promete el gate.
    """
    tabla = TABLA_DE[cambio.objeto]
    await db.execute(
        f"UPDATE {tabla} SET {cambio.campo} = ? WHERE id = ?",  # noqa: S608
        (cambio.despues, cambio.fila_id),
    )

    await arnes.registrar_audit(
        db,
        actor=actor,
        accion=f"cambio:{cambio.objeto.value}",
        objeto=f"{tabla}:{cambio.fila_id}",
        antes={cambio.campo: cambio.antes},
        despues={cambio.campo: cambio.despues},
    )

    if actor != "arnes":
        await db.execute(
            """
            INSERT INTO edicion_humana (fase_run_id, tabla, fila_id, campo, antes, despues, motivo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fase_run_id, tabla, cambio.fila_id, cambio.campo, cambio.antes, cambio.despues,
             cambio.motivo),
        )

    await _reindexar(db, vectorizador, cambio)


async def _reindexar(
    db: aiosqlite.Connection, vectorizador: Vectorizador, cambio: CambioResuelto
) -> None:
    if cambio.objeto is ObjetoDelCambio.HECHO:
        fila = await mundo.hecho_por_id(db, cambio.fila_id)
        if fila is not None:
            await indice.indexar_hecho(
                db,
                vectorizador,
                hecho_id=cambio.fila_id,
                enunciado=str(fila["enunciado"]),
                estado=str(fila["estado"]),
                dimension=str(fila["dimension"]),
            )
        return

    tabla = TABLA_DE[cambio.objeto]
    familia = {"canon_personaje": "personaje", "canon_escenario": "escenario",
               "canon_glosario": "glosario"}[tabla]
    await indice.indexar_canon(
        db,
        vectorizador,
        tabla=tabla,
        fila_id=cambio.fila_id,
        texto=await _describir(db, tabla, cambio.fila_id),
        familia=familia,
    )
