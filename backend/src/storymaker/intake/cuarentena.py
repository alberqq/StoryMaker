"""spec: §4.1 · arq: §4, §15

La cuarentena del texto libre.

Si el comprador pega una anécdota o una carta, el texto entra aquí y **no sale de aquí**.
Solo avanza convertido en filas tipadas por un extractor cuya salida está restringida por
esquema, y esas filas llevan `origen = 'texto_libre_no_confiable'`.

**La defensa contra *prompt injection* es estructural, no una instrucción.** No se le pide
a ningún modelo que «ignore las órdenes embebidas»: se le pide que extraiga personas,
lugares, fechas, objetos y anécdotas. Una inyección tiene que sobrevivir a convertirse en
una de esas cinco filas para hacer daño, y no sobrevive: lo que llega al escritor es
`{"tipo": "objeto", "valor": "un reloj de bolsillo"}`, no la frase que lo rodeaba.
"""

from __future__ import annotations

import json

import aiosqlite

from storymaker.commons.db.repos import intake as repo
from storymaker.intake.esquemas import DatoExtraido, ElementoPersonalizacion

ORIGEN_CUARENTENA = "texto_libre_no_confiable"
ORIGEN_ENTREVISTA = "entrevista"


async def guardar_en_cuarentena(db: aiosqlite.Connection, texto: str) -> int:
    """Mete el texto pegado y devuelve su identificador. Nadie más lo lee."""
    return await repo.guardar_texto_crudo(db, texto)


async def volcar_extraidos(
    db: aiosqlite.Connection, texto_crudo_id: int, datos: list[DatoExtraido]
) -> list[int]:
    """Escribe las filas tipadas que salieron de la cuarentena, con su procedencia."""
    identificadores = []
    for dato in datos:
        identificadores.append(
            await repo.insertar_dato(
                db,
                tipo=dato.tipo.value,
                valor_json=json.dumps({"valor": dato.valor}, ensure_ascii=False),
                origen=ORIGEN_CUARENTENA,
                obligatorio=dato.obligatorio,
                texto_crudo_id=texto_crudo_id,
            )
        )
    return identificadores


async def volcar_dictados(
    db: aiosqlite.Connection, elementos: list[ElementoPersonalizacion]
) -> list[int]:
    """Los que el comprador dictó en la entrevista. No tienen texto de procedencia.

    Por eso `texto_crudo_id` admite nulo: solo lo extraído de la cuarentena tiene de dónde
    venir, y el `CHECK` del esquema exige que lo demás lo declare.
    """
    identificadores = []
    for elemento in elementos:
        valor_json = json.dumps({"valor": elemento.valor}, ensure_ascii=False)
        if await repo.existe_dato(
            db, tipo=elemento.tipo.value, valor_json=valor_json, origen=ORIGEN_ENTREVISTA
        ):
            # Una vuelta más de la entrevista repite los datos ya dictados: no se duplican.
            continue
        identificadores.append(
            await repo.insertar_dato(
                db,
                tipo=elemento.tipo.value,
                valor_json=valor_json,
                origen=ORIGEN_ENTREVISTA,
                obligatorio=elemento.obligatorio,
            )
        )
    return identificadores


async def textos_en_cuarentena(db: aiosqlite.Connection) -> list[str]:
    """Todo lo que hay en cuarentena, para las aserciones que comprueban que no sale.

    Existe para la suite adversaria: se ensambla un prompt y se comprueba que ninguna
    cadena de aquí aparece en él.
    """
    async with db.execute("SELECT texto FROM intake_texto_crudo ORDER BY id") as cursor:
        return [str(fila["texto"]) for fila in await cursor.fetchall()]


async def marcar_procesado(db: aiosqlite.Connection, texto_crudo_id: int) -> None:
    await db.execute(
        "UPDATE intake_texto_crudo SET procesado_en = datetime('now') WHERE id = ?",
        (texto_crudo_id,),
    )
