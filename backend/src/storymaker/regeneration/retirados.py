"""spec: §4.6 · arq: §2, §4

Detalla `specs/escritura/spec.md` §9.

**El valor retirado**: lo que un cambio de nombre deja de ser, y los tres sitios donde hay que
perseguirlo para que el cambio llegue al texto.

Cambiar la fila del canon no basta. La primera regeneración real lo demostró: el nombre
nuevo iba una vez en el paquete del escritor —la ficha del personaje— y el viejo entre tres
y seis, repetido en los beats de la escaleta y en la prosa del capítulo anterior. El
escritor siguió a la mayoría, ningún validador miraba el nombre retirado, y la versión 2
salió con el nombre de siempre. De ahí las tres piezas de este módulo:

- **`propagar`** reescribe el valor en la escaleta y en el canon, que son plan y no prosa
  publicada, para que el paquete deje de contradecir a la ficha;
- **`capitulos_que_lo_nombran`** amplía el alcance a los capítulos cuyo texto aprobado lo
  contiene, aunque ninguna tabla de uso lo registre;
- **`incidencias`** hace bloqueante que un capítulo regenerado lo conserve, de modo que el
  editor lo repara o el capítulo no se aprueba.
"""

from __future__ import annotations

import re

import aiosqlite

from storymaker.commons.db.repos import arnes
from storymaker.commons.validation.modelos import Incidencia, Severidad
from storymaker.regeneration.esquemas import ObjetoDelCambio

VALIDADOR = "valor_retirado"

#: Qué campos son un nombre que la prosa repite tal cual.
_NOMBRES = {(ObjetoDelCambio.PERSONAJE, "nombre"), (ObjetoDelCambio.GLOSARIO, "termino")}

Pares = list[tuple[str, str]]


def pares(objeto: ObjetoDelCambio, campo: str, antes: str, despues: str) -> Pares:
    """Qué hay que dejar de decir y qué decir en su lugar.

    El nombre entero y, si el viejo y el nuevo tienen las mismas palabras, cada palabra que
    cambia: el texto dice «Pérez» a secas mucho más que «Juan Pérez». Las palabras cortas no
    entran, porque sustituir «de» o «la» destrozaría la escaleta.
    """
    viejo, nuevo = antes.strip(), despues.strip()
    if (objeto, campo) not in _NOMBRES or not viejo or viejo == nuevo:
        return []
    resultado = [(viejo, nuevo)]
    palabras_viejas, palabras_nuevas = viejo.split(), nuevo.split()
    if len(palabras_viejas) == len(palabras_nuevas) > 1:
        for a, b in zip(palabras_viejas, palabras_nuevas, strict=True):
            if a != b and len(a) >= 3 and (a, b) not in resultado:
                resultado.append((a, b))
    return resultado


def _patron(valor: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(valor)}(?!\w)")


def aparece(texto: str, pares_: Pares) -> list[str]:
    """Los valores retirados que el texto todavía contiene, como palabra entera.

    Lo ya encontrado se aparta antes de buscar el siguiente: «Emeterio» dentro de «Don
    Emeterio» es la misma mención, no dos.
    """
    encontrados = []
    for viejo, _ in pares_:
        patron = _patron(viejo)
        if patron.search(texto):
            encontrados.append(viejo)
            texto = patron.sub(" ", texto)
    return encontrados


def sustituir(texto: str, pares_: Pares) -> str:
    """El texto con cada valor retirado cambiado por el nuevo, el nombre entero primero."""
    for viejo, nuevo in pares_:
        texto = _patron(viejo).sub(nuevo, texto)
    return texto


def incidencias(texto: str, pares_: Pares) -> list[Incidencia]:
    """Una incidencia bloqueante por cada valor retirado que sigue en el capítulo."""
    nuevos = dict(pares_)
    return [
        Incidencia(
            validador=VALIDADOR,
            severidad=Severidad.BLOQUEANTE,
            mensaje=f"El capitulo todavia dice «{viejo}», que ahora es «{nuevos[viejo]}».",
            propuesta=f"Sustituye cada «{viejo}» por «{nuevos[viejo]}».",
        )
        for viejo in aparece(texto, pares_)
    ]


async def propagar(db: aiosqlite.Connection, pares_: Pares) -> int:
    """Reescribe el valor en la escaleta y el canon. Devuelve cuántas celdas cambió.

    Recorre las columnas de texto de `plan_*` y `canon_*` —los beats, los objetivos, los
    hitos, las relaciones— porque el nombre se copió en prosa al planificar y ninguna clave
    foránea lo recuerda. No toca `mundo_*`, que está sellado, ni el texto de los capítulos,
    que es inmutable: eso lo reescribe la regeneración.
    """
    if not pares_:
        return 0
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
        " AND (name LIKE 'plan\\_%' ESCAPE '\\' OR name LIKE 'canon\\_%' ESCAPE '\\')"
    ) as cursor:
        tablas = [str(f[0]) for f in await cursor.fetchall()]

    cambiadas = 0
    for tabla in tablas:
        async with db.execute(f"PRAGMA table_info({tabla})") as cursor:
            columnas = [
                str(f["name"]) for f in await cursor.fetchall() if str(f["type"]).upper() == "TEXT"
            ]
        for columna in columnas:
            filtro = " OR ".join(f"{columna} LIKE ?" for _ in pares_)
            async with db.execute(
                f"SELECT rowid AS fila, {columna} AS valor FROM {tabla} WHERE {filtro}",  # noqa: S608
                [f"%{viejo}%" for viejo, _ in pares_],
            ) as cursor:
                filas = list(await cursor.fetchall())
            for fila in filas:
                antes = str(fila["valor"])
                despues = sustituir(antes, pares_)
                if despues != antes:
                    await db.execute(
                        f"UPDATE {tabla} SET {columna} = ? WHERE rowid = ?",  # noqa: S608
                        (despues, fila["fila"]),
                    )
                    cambiadas += 1

    if cambiadas:
        await arnes.registrar_audit(
            db,
            actor="arnes",
            accion="propagar:valor_retirado",
            objeto="plan_*,canon_*",
            antes={"valores": [v for v, _ in pares_]},
            despues={"valores": [n for _, n in pares_], "celdas": cambiadas},
        )
    return cambiadas


async def capitulos_que_lo_nombran(db: aiosqlite.Connection, pares_: Pares) -> list[int]:
    """Los capítulos cuya última versión aprobada contiene algún valor retirado."""
    if not pares_:
        return []
    async with db.execute(
        """
        SELECT pc.numero, cv.texto
          FROM capitulo_version cv
          JOIN plan_capitulo pc ON pc.id = cv.capitulo_id
         WHERE cv.id = (SELECT MAX(id) FROM capitulo_version
                         WHERE capitulo_id = cv.capitulo_id AND estado = 'aprobado')
         ORDER BY pc.numero
        """
    ) as cursor:
        filas = list(await cursor.fetchall())
    return [int(f["numero"]) for f in filas if aparece(str(f["texto"]), pares_)]
