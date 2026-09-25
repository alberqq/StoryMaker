"""spec: §4.3 · arq: §4, §7

Vuelca la escaleta: capítulos, escenas, beats, quién está en cada escena y a qué se ancla.

La escena es la **unidad de planificación y de traza**; el capítulo, la de redacción. Esa
separación es la que permite que el escritor redacte el capítulo entero de una vez —coser
escenas generadas por separado es la forma más fiable de producir prosa mecánica— sin
perder la granularidad que necesitan `uso_hecho`, `uso_hito` y la cronología.

Aquí está también lo que hace posible detectar una cronología imposible **antes de redactar
una línea**: cada escena lleva su `fecha_narrativa` y sus personajes, así que un personaje
en dos sitios el mismo día, o vivo tres años después de su muerte documentada, es visible
en el gate de Plotting, donde corregirlo cuesta un párrafo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import id_insertado
from storymaker.commons.validation.puras import normalizar
from storymaker.plotting.esquemas import SalidaArquitecto

_CLAVE = re.compile(r"#\s*(\d+)")


def mapa_de_claves(filas: dict[int, str]) -> dict[str, int]:
    """Identificador → texto, convertido en todo lo que el arquitecto puede escribir.

    El contexto le enseña cada hecho y cada elemento como `#id`, y así es como se le pide
    que ancle (ER §7.2). Se acepta también el texto, normalizado, porque un anclaje que
    copia el enunciado en vez de la clave apunta a lo mismo y descartarlo sería castigar la
    forma y no el contenido.
    """
    mapa: dict[str, int] = {}
    for identificador, texto_fila in filas.items():
        mapa[f"#{identificador}"] = identificador
        mapa[str(identificador)] = identificador
        if texto_fila:
            mapa[normalizar(texto_fila)] = identificador
    return mapa


def resolver_clave(mapa: dict[str, int], propuesta: str | None) -> int | None:
    """La clave que escribió el arquitecto, o `None` si no apunta a nada conocido."""
    if not propuesta:
        return None
    if (marca := _CLAVE.search(propuesta)) is not None:
        return mapa.get(f"#{marca.group(1)}")
    limpia = propuesta.strip()
    return mapa.get(limpia) if limpia in mapa else mapa.get(normalizar(limpia))


#: Lo mínimo que tienen que compartir un anclaje escrito como frase y el texto al que se
#: resuelve por parecido: dos palabras con contenido y seis de cada diez de las suyas.
PALABRAS_COMUNES_MINIMAS = 2
PROPORCION_MINIMA = 0.6


def _palabras(texto: str) -> set[str]:
    """Las palabras con contenido: cuatro letras o más, o un año."""
    return {p for p in normalizar(texto).split() if len(p) >= 4}


def por_parecido(textos: dict[int, str], propuesta: str | None) -> int | None:
    """El texto que más palabras comparte con la propuesta, si comparte bastantes.

    Es la última forma de resolver un anclaje que el arquitecto escribió como frase —«los
    telegrafistas trabajaban en turnos de ocho horas…» en lugar de `#13`—, y es léxica a
    propósito: determinista, sin umbrales de coseno que dependan del modelo de embeddings,
    y fácil de explicar en el aviso que deja. Un empate no se decide a ciegas: gana el
    texto que menos palabras le sobran.
    """
    if not propuesta or (buscadas := _palabras(propuesta)) == set():
        return None
    mejor: tuple[float, int, float] | None = None
    elegido: int | None = None
    for identificador, texto in textos.items():
        suyas = _palabras(texto)
        comunes = len(buscadas & suyas)
        proporcion = comunes / len(buscadas)
        if comunes < PALABRAS_COMUNES_MINIMAS or proporcion < PROPORCION_MINIMA:
            continue
        clave = (proporcion, comunes, comunes / len(buscadas | suyas))
        if mejor is None or clave > mejor:
            mejor, elegido = clave, identificador
    return elegido


@dataclass(frozen=True)
class AnclajeResuelto:
    """A qué apunta un anclaje propuesto, y si hubo que adivinarlo por parecido."""

    hecho_id: int | None = None
    dato_id: int | None = None
    por_parecido: bool = False


def resolver_anclaje(
    hecho: str | None,
    dato: str | None,
    *,
    hechos: dict[str, int],
    datos: dict[str, int],
    textos_de_hecho: dict[int, str],
    textos_de_dato: dict[int, str],
) -> AnclajeResuelto | None:
    """Resuelve un anclaje en tres pasos, del más fiable al menos (trama-rehacible §3.5).

    1. **La clave o el texto exacto, en su campo**: `hecho` contra el corpus, `dato` contra
       el encargo.
    2. **Lo mismo, en el campo cruzado.** El arquitecto escribía a menudo un elemento del
       encargo en `hecho`; apunta a lo mismo, y descartarlo castigaba la forma.
    3. **Por parecido léxico**, primero contra el encargo —que es lo que la cobertura
       exige— y después contra el corpus.
    """
    if (h := resolver_clave(hechos, hecho)) is not None:
        return AnclajeResuelto(hecho_id=h)
    if (d := resolver_clave(datos, dato)) is not None:
        return AnclajeResuelto(dato_id=d)
    if (d := resolver_clave(datos, hecho)) is not None:
        return AnclajeResuelto(dato_id=d)
    if (h := resolver_clave(hechos, dato)) is not None:
        return AnclajeResuelto(hecho_id=h)
    for texto in (dato, hecho):
        if (d := por_parecido(textos_de_dato, texto)) is not None:
            return AnclajeResuelto(dato_id=d, por_parecido=True)
    for texto in (hecho, dato):
        if (h := por_parecido(textos_de_hecho, texto)) is not None:
            return AnclajeResuelto(hecho_id=h, por_parecido=True)
    return None


def resolver_escenario(
    nombre: str,
    claves: dict[str, int],
    *,
    clave_de_escena: str,
    sin_resolver: list[str] | None = None,
    resueltos_por_parecido: list[str] | None = None,
) -> int | None:
    """El escenario de una escena: la clave exacta, la normalizada o la única que la contiene.

    Antes solo se aceptaba la clave exacta, y lo que el arquitecto escribiera con otra
    grafía dejaba la escena sin escenario sin avisar a nadie. En `metro` ninguna de las
    once escenas quedó enlazada, y la ficha de lugares de la lectura decía de los cinco que
    no aparecían en ningún capítulo: lo encontró la inspección en el navegador. Lo adivinado
    se dice y lo que no se resuelve se enseña en el gate de la Trama.
    """
    if not nombre:
        return None
    exacta = claves.get(f"escenario:{nombre}")
    if exacta is not None:
        return exacta
    escenarios = {
        normalizar(clave.removeprefix("escenario:")): valor
        for clave, valor in claves.items()
        if clave.startswith("escenario:")
    }
    buscado = normalizar(nombre)
    candidato = escenarios.get(buscado)
    if candidato is None:
        parecidos = {v for k, v in escenarios.items() if k and (k in buscado or buscado in k)}
        candidato = parecidos.pop() if len(parecidos) == 1 else None
    if candidato is not None:
        if resueltos_por_parecido is not None:
            resueltos_por_parecido.append(f"escena {clave_de_escena}: escenario «{nombre}»")
        return candidato
    if sin_resolver is not None:
        sin_resolver.append(f"escena {clave_de_escena}: escenario «{nombre}»")
    return None


async def volcar_escaleta(
    db: aiosqlite.Connection,
    salida: SalidaArquitecto,
    *,
    personajes: dict[str, int],
    hechos: dict[str, int] | None = None,
    datos: dict[str, int] | None = None,
    textos_de_hecho: dict[int, str] | None = None,
    textos_de_dato: dict[int, str] | None = None,
    sin_resolver: list[str] | None = None,
    resueltos_por_parecido: list[str] | None = None,
) -> dict[str, int]:
    """Escribe la escaleta entera. Devuelve clave de escena → identificador.

    Ese diccionario es lo que después permite anclar los hitos de arco a sus escenas, y por
    eso se devuelve en lugar de quedarse dentro: el arquitecto nombra las escenas con claves
    y la base con identificadores, y alguien tiene que traducir.

    Los anclajes que no apuntan a nada conocido se añaden a `sin_resolver`, para que el
    gate de Plotting los enseñe en lugar de perderlos en silencio; los que se resolvieron
    por parecido, a `resueltos_por_parecido`, porque lo adivinado se dice.
    """
    hechos = hechos or {}
    datos = datos or {}
    textos_de_hecho = textos_de_hecho or {}
    textos_de_dato = textos_de_dato or {}
    escenas_por_clave: dict[str, int] = {}

    for capitulo in sorted(salida.capitulos, key=lambda c: c.numero):
        cursor = await db.execute(
            "INSERT INTO plan_capitulo (numero, titulo, funcion, gancho) VALUES (?, ?, ?, ?)",
            (capitulo.numero, capitulo.titulo, capitulo.funcion, capitulo.gancho),
        )
        capitulo_id = id_insertado(cursor)

        for escena in sorted(capitulo.escenas, key=lambda e: e.orden):
            cursor = await db.execute(
                """
                INSERT INTO plan_escena
                    (capitulo_id, orden, escenario_id, fecha_narrativa, pdv_personaje_id,
                     objetivo, conflicto, resultado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    capitulo_id,
                    escena.orden,
                    resolver_escenario(
                        escena.escenario,
                        personajes,
                        clave_de_escena=escena.clave,
                        sin_resolver=sin_resolver,
                        resueltos_por_parecido=resueltos_por_parecido,
                    ),
                    escena.fecha_narrativa or None,
                    personajes.get(escena.pdv),
                    escena.objetivo,
                    escena.conflicto,
                    escena.resultado,
                ),
            )
            escena_id = id_insertado(cursor)
            escenas_por_clave[escena.clave] = escena_id

            for beat in sorted(escena.beats, key=lambda b: b.orden):
                await db.execute(
                    """
                    INSERT INTO plan_beat (escena_id, orden, accion, cambio_de_valor)
                    VALUES (?, ?, ?, ?)
                    """,
                    (escena_id, beat.orden, beat.accion, beat.cambio_de_valor),
                )

            for nombre in escena.personajes:
                personaje_id = personajes.get(nombre)
                if personaje_id is not None:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO plan_escena_personaje (escena_id, personaje_id)
                        VALUES (?, ?)
                        """,
                        (escena_id, personaje_id),
                    )

            for anclaje in escena.anclajes:
                resuelto = resolver_anclaje(
                    anclaje.hecho,
                    anclaje.dato,
                    hechos=hechos,
                    datos=datos,
                    textos_de_hecho=textos_de_hecho,
                    textos_de_dato=textos_de_dato,
                )
                if resuelto is None:
                    if sin_resolver is not None and (anclaje.hecho or anclaje.dato):
                        sin_resolver.append(
                            f"escena {escena.clave}: {anclaje.hecho or anclaje.dato}"
                        )
                    # Un anclaje que no apunta a nada no se escribe: el `CHECK` exige
                    # exactamente uno de los tres, y escribirlo abortaría la transacción
                    # entera por un despiste del modelo.
                    continue
                await db.execute(
                    """
                    INSERT INTO plan_anclaje (escena_id, hecho_id, dato_id, tipo_vinculo)
                    VALUES (?, ?, ?, ?)
                    """,
                    (escena_id, resuelto.hecho_id, resuelto.dato_id, anclaje.tipo_vinculo),
                )
                if resuelto.por_parecido and resueltos_por_parecido is not None:
                    destino = (
                        f"#{resuelto.dato_id} «{textos_de_dato.get(resuelto.dato_id or 0, '')}»"
                        if resuelto.dato_id is not None
                        else f"#{resuelto.hecho_id} "
                        f"«{textos_de_hecho.get(resuelto.hecho_id or 0, '')}»"
                    )
                    resueltos_por_parecido.append(
                        f"escena {escena.clave}: «{anclaje.hecho or anclaje.dato}» → {destino}"
                    )

    return escenas_por_clave
