"""spec: §3.4 · arq: §6

Los siete constructores de bloque. Cada uno lee SQLite —y, tres de ellos, los índices
semánticos— y devuelve una lista de fragmentos **ya ordenada por relevancia**, porque el
recorte posterior corta por la cola y no elige.

Van juntos en un módulo y no en siete ficheros de veinte líneas porque se leen juntos: lo
que importa de este código es el orden de los bloques y qué entra en cada uno, y eso se ve
de un vistazo aquí y no repartido.

El reparto no es cosmético. Los bloques 1, 3, 6 y 7 son **estructurales**: salen de la
escaleta, del canon y del encargo, y entran enteros. Los bloques 2, 4 y 5 se llenan **por
relevancia semántica**, y es lo que hace que el sistema escale a novelas largas: en el
capítulo 10 no hacen falta los nueve resúmenes anteriores con el mismo peso, hacen falta
los tres que importan.
"""

from __future__ import annotations

import json
from typing import Any

import aiosqlite

from storymaker.commons.config import Defaults, Settings
from storymaker.commons.context import repeticion
from storymaker.commons.context.paquete import Bloque
from storymaker.commons.db.repos import arnes, canon, intake, mundo, plan, texto
from storymaker.commons.embeddings import indice
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.commons.validation.puras import anadido_vigente, firmeza


def _valor(fila: aiosqlite.Row, columna: str, defecto: str = "") -> str:
    try:
        crudo = fila[columna]
    except (IndexError, KeyError):
        return defecto
    return defecto if crudo is None else str(crudo)


async def consulta_semantica(db: aiosqlite.Connection, numero: int) -> str:
    """La consulta con la que se buscan los vecinos, **derivada mecánicamente** de la escaleta.

    Es el detalle del que depende que el §2 siga en pie. La recuperación la hace el
    ensamblador, no el agente, y la consulta no la elige nadie sobre la marcha: sale del
    texto de las escenas del capítulo N —objetivo, conflicto, escenario, personajes y fecha
    narrativa—. Con las mismas entradas salen los mismos vecinos, siempre.
    """
    partes: list[str] = []
    for escena in await plan.escenas_de(db, numero):
        partes += [
            _valor(escena, "objetivo"),
            _valor(escena, "conflicto"),
            _valor(escena, "resultado"),
            _valor(escena, "fecha_narrativa"),
        ]
    partes += [_valor(p, "nombre") for p in await plan.personajes_de(db, numero)]
    partes += [_valor(s, "descripcion") for s in await plan.escenarios_de(db, numero)]
    return " ".join(p for p in partes if p)


async def encargo(db: aiosqlite.Connection, numero: int, settings: Settings) -> Bloque:
    """Bloque 1. Qué hay que escribir, y qué quedó pendiente en N-1.

    Es el bloque que nunca debería recortarse, y por eso los avisos de ejecución que viajan
    hasta aquí están topados en **los tres más recientes**: un capítulo que arrastrase siete
    se los comería, y además un capítulo con siete avisos no tiene un problema de contexto
    sino de escritura.
    """
    capitulo = await plan.capitulo_por_numero(db, numero)
    if capitulo is None:
        return Bloque(1)

    obra = await canon.obra(db)
    extension = int(obra["palabras_por_capitulo"]) if obra else Defaults.PALABRAS_POR_CAPITULO

    fragmentos = [
        f"Capitulo {numero}: {_valor(capitulo, 'titulo')}".strip(),
        f"Funcion en la obra: {_valor(capitulo, 'funcion')}",
        f"Gancho de cierre: {_valor(capitulo, 'gancho')}",
        f"Extension objetivo: {extension} palabras.",
    ]

    for escena in await plan.escenas_de(db, numero):
        cabecera = (
            f"Escena {escena['orden']} ({_valor(escena, 'fecha_narrativa', 'sin fecha')}): "
            f"objetivo {_valor(escena, 'objetivo')}; conflicto {_valor(escena, 'conflicto')}; "
            f"resultado {_valor(escena, 'resultado')}"
        )
        beats = await plan.beats_de(db, int(escena["id"]))
        detalle = "; ".join(
            f"{b['orden']}. {_valor(b, 'accion')} -> {_valor(b, 'cambio_de_valor')}" for b in beats
        )
        fragmentos.append(cabecera + (f"\n  Beats: {detalle}" if detalle else ""))

    hitos = await plan.hitos_de(db, numero)
    if hitos:
        fragmentos.append(
            "Hitos de arco que este capitulo debe cubrir: "
            + "; ".join(f"{h['personaje']}: {_valor(h, 'descripcion')}" for h in hitos)
        )

    pendientes = await avisos_pendientes(db, numero)
    if pendientes:
        fragmentos.append("Quedo pendiente del capitulo anterior:\n- " + "\n- ".join(pendientes))

    return Bloque(1, tuple(fragmentos), fijos=len(fragmentos) - (1 if pendientes else 0))


async def avisos_pendientes(db: aiosqlite.Connection, numero: int) -> list[str]:
    """Los tres avisos más recientes del capítulo anterior.

    Este viaje es lo que distingue un aviso de un simple apunte: sin él, detectar en el
    capítulo 4 que un hito no ocurrió solo adelantaría la mala noticia. Con él, la
    corrección entra por donde entra todo lo demás en este sistema, el paquete de contexto,
    y no hace falta ni un gate nuevo ni una arista nueva.
    """
    if numero <= 1:
        return []
    anterior = await plan.capitulo_por_numero(db, numero - 1)
    if anterior is None:
        return []
    version = await texto.capitulo_aprobado(db, int(anterior["id"]))
    if version is None:
        return []
    incidencias = await arnes.incidencias_de(db, int(version["id"]))
    avisos = [i for i in incidencias if i["severidad"] == "aviso"]
    return [_valor(i, "mensaje") for i in avisos[-Defaults.AVISOS_QUE_VIAJAN_AL_SIGUIENTE :]]


async def canon_relevante(
    db: aiosqlite.Connection, vectorizador: Vectorizador, numero: int, settings: Settings
) -> Bloque:
    """Bloque 2. Las fichas de quien sale, más lo que la búsqueda marque como relevante.

    No la biblia entera: las fichas de los personajes presentes en estas escenas y de sus
    escenarios entran siempre, y la búsqueda semántica añade lo que el arquitecto no previó
    —típicamente cultura material y léxico de época—.
    """
    fragmentos: list[str] = []
    presentes: set[tuple[str, int]] = set()

    for personaje in await plan.personajes_de(db, numero):
        presentes.add(("canon_personaje", int(personaje["id"])))
        fragmentos.append(
            f"{_valor(personaje, 'nombre')} ({_valor(personaje, 'tipo')}): "
            f"objetivo {_valor(personaje, 'objetivo')}; miedo {_valor(personaje, 'miedo')}; "
            f"voz {_valor(personaje, 'voz')}; estatus {_valor(personaje, 'estatus')}"
        )
    for escenario in await plan.escenarios_de(db, numero):
        presentes.add(("canon_escenario", int(escenario["id"])))
        fragmentos.append(f"Escenario: {_valor(escenario, 'descripcion')}")

    fijos = len(fragmentos)

    consulta = await consulta_semantica(db, numero)
    if consulta:
        for tabla, fila_id, _ in await indice.buscar_canon(
            db, vectorizador, consulta, k=settings.k_vecinos
        ):
            if (tabla, fila_id) in presentes:
                continue
            if tabla == "canon_glosario":
                for termino in await canon.glosario(db):
                    if int(termino["id"]) == fila_id:
                        fragmentos.append(
                            f"Glosario: {_valor(termino, 'termino')} = "
                            f"{_valor(termino, 'significado')}"
                        )
            elif tabla == "canon_personaje":
                for ficha in await canon.personajes(db, [fila_id]):
                    fragmentos.append(
                        f"{_valor(ficha, 'nombre')} (relevante por similitud): "
                        f"{_valor(ficha, 'objetivo')}"
                    )

    return Bloque(2, tuple(fragmentos), fijos=fijos)


#: Largo máximo de cada evento de «lo que ya ha pasado», en caracteres.
LARGO_DE_EVENTO = 160


async def continuidad(db: aiosqlite.Connection, numero: int) -> Bloque:
    """Bloque 3. El estado al cierre de N-1, y lo que ya ha pasado antes de N-1.

    Es **el último bloque que se recorta**. Perder memoria produce un capítulo más pobre;
    perder continuidad produce uno que contradice lo que ya ocurrió, y eso no se arregla
    leyendo mejor.

    El estado dice dónde está cada quien y qué posee, pero no qué se prometió o se entregó
    tres capítulos atrás. Eso lo dicen los eventos narrativos que el extractor escribe para
    Lean, y entran aquí los de los capítulos 1 a N-2: N-1 ya va entero en el bloque 4. Van
    del más reciente al más antiguo, para que el recorte suelte primero lo más lejano.
    """
    if numero <= 1:
        return Bloque(3)

    fragmentos = []
    anterior = await plan.capitulo_por_numero(db, numero - 1)
    version = (
        await texto.capitulo_aprobado(db, int(anterior["id"])) if anterior is not None else None
    )
    if version is not None:
        for fila in await texto.continuidad_de(db, int(version["id"])):
            fragmentos.append(
                f"{_valor(fila, 'personaje')}: en {_valor(fila, 'escenario', 'lugar sin fijar')} "
                f"el {_valor(fila, 'fecha_narrativa', 'sin fecha')}; "
                f"sabe {_valor(fila, 'conocimiento_json', '[]')}; "
                f"posee {_valor(fila, 'posesiones_json', '[]')}; "
                f"estado {_valor(fila, 'estado_json', '{}')}"
            )
    fijos = len(fragmentos)

    eventos = await texto.eventos_anteriores(db, numero - 1)
    if eventos:
        fragmentos.append(
            "Lo que ya ha pasado en la novela (no lo contradigas ni lo repitas como nuevo):"
        )
        fijos += 1
        for evento in eventos:
            descripcion = _valor(evento, "descripcion")
            if len(descripcion) > LARGO_DE_EVENTO:
                descripcion = descripcion[: LARGO_DE_EVENTO - 1].rstrip() + "…"
            fragmentos.append(f"Capitulo {evento['numero']}: {descripcion}")

    return Bloque(3, tuple(fragmentos), fijos=fijos)


async def memoria(
    db: aiosqlite.Connection, vectorizador: Vectorizador, numero: int, settings: Settings
) -> Bloque:
    """Bloque 4. El texto íntegro de N-1 y los resúmenes previos más relevantes.

    Va el texto entero y no solo el resumen porque **la voz y el gancho se heredan de la
    prosa, no de un sumario**. Los resúmenes anteriores entran por relevancia y filtrados
    dentro de la consulta: solo capítulos anteriores a N y solo versiones vigentes.
    """
    if numero <= 1:
        return Bloque(4)

    fragmentos: list[str] = []
    anterior = await plan.capitulo_por_numero(db, numero - 1)
    if anterior is not None:
        version = await texto.capitulo_aprobado(db, int(anterior["id"]))
        if version is not None:
            fragmentos.append(f"Capitulo {numero - 1}, integro:\n{_valor(version, 'texto')}")

    fijos = len(fragmentos)
    consulta = await consulta_semantica(db, numero)
    if consulta:
        vecinos = await indice.buscar_resumenes(
            db, vectorizador, consulta, anteriores_a=numero, k=settings.k_vecinos
        )
        for vecino in vecinos:
            resumen = await texto.resumen_de(db, vecino.id)
            if resumen:
                fragmentos.append(f"Resumen previo: {resumen}")

    return Bloque(4, tuple(fragmentos), fijos=fijos)


async def anclajes(
    db: aiosqlite.Connection, vectorizador: Vectorizador, numero: int, settings: Settings
) -> Bloque:
    """Bloque 5. Los hechos que la escaleta ancló, más los vecinos del corpus sellado.

    **Los anclajes explícitos entran siempre**, y por eso son fijos: son lo que el arquitecto
    decidió que este capítulo tiene que usar. Cada uno viaja con su firmeza (arq. §7), que
    es lo que permite al escritor saber si lo que está usando es un dato documentado, una
    inferencia o una licencia.
    """
    fragmentos: list[str] = []
    anclados: set[int] = set()

    for anclaje in await plan.anclajes_de(db, numero):
        if anclaje["hecho_id"] is not None:
            anclados.add(int(anclaje["hecho_id"]))
            enunciado = _valor(anclaje, "hecho_enunciado")
            fragmentos.append(
                f"[{_firmeza_del_anclaje(anclaje)}] {enunciado}"
                f"{nota_de_la_cita(enunciado, anclaje['hecho_sin_respaldo'])} "
                f"(escena {anclaje['escena_orden']}, {_valor(anclaje, 'tipo_vinculo')})"
            )
        elif anclaje["entidad_id"] is not None:
            fragmentos.append(
                f"Entidad de epoca: {_valor(anclaje, 'entidad_nombre')} "
                f"({_valor(anclaje, 'entidad_nombre_epoca')})"
            )

    fijos = len(fragmentos)

    consulta = await consulta_semantica(db, numero)
    if consulta:
        for vecino in await indice.buscar_hechos(db, vectorizador, consulta, k=settings.k_vecinos):
            if vecino.id in anclados:
                continue
            fila = await mundo.hecho_por_id(db, vecino.id)
            if fila is not None:
                fragmentos.append(
                    f"[{firmeza(str(fila['estado']), str(fila['respaldo']), str(fila['origen']))}] "
                    f"{_valor(fila, 'enunciado')}"
                    f"{nota_de_la_cita(_valor(fila, 'enunciado'), fila['sin_respaldo'])} "
                    f"(corpus, {_valor(fila, 'dimension')})"
                )

    return Bloque(5, tuple(fragmentos), fijos=fijos)


def nota_de_la_cita(enunciado: str, sin_respaldo: object) -> str:
    """` (no lo dice la cita: «…»)` si el veredicto fue parcial y el añadido sigue ahí.

    Es lo que separa, para quien escribe, el dato que la cita sostiene de lo que el
    investigador le añadió (arq. §4, Fase 2). Si el Autor quitó el añadido, no queda nada.
    """
    anadido = anadido_vigente(enunciado, str(sin_respaldo) if sin_respaldo else None)
    return f" (no lo dice la cita: «{anadido}»)" if anadido else ""


def _firmeza_del_anclaje(anclaje: aiosqlite.Row) -> str:
    """La firmeza del hecho anclado, con las columnas que `plan.anclajes_de` le trae."""
    return firmeza(
        str(anclaje["hecho_estado"]), str(anclaje["hecho_respaldo"]), str(anclaje["hecho_origen"])
    )


#: Las cuatro reglas de escritura fijas del bloque 6 (arq. §6). Cada una responde a un
#: defecto que una novela real enseñó: el cambio de tiempo verbal a mitad de novela, los
#: encabezados de escena colados en la prosa, un personaje histórico que recuerda lo que
#: aún no ha ocurrido y un objeto que se entrega dos veces.
REGLAS_DE_ESCRITURA = (
    "Narra en preterito, como el resto de la novela.",
    "Entrega solo prosa: sin titulo del capitulo, sin encabezados de escena y sin markdown.",
    "Ningun personaje, historico incluido, sabe ni cuenta lo que aun no ha ocurrido en la "
    "fecha narrativa de su escena.",
    "No contradigas lo que la continuidad dice que ya paso: lo entregado, prometido o "
    "decidido sigue asi.",
)

#: Qué hacer con cada firmeza del bloque 5 (arq. §6). Sin esto la etiqueta llegaba al
#: escritor y no cambiaba nada de lo que escribía.
USO_DE_LA_FIRMEZA = (
    "documentado: cuentalo como hecho, con sus fechas y cifras.",
    "debatido: no tomes partido; mejor por boca de un personaje o como rumor.",
    "inferido: usalo como ambiente, sin cifras exactas y sin que la trama gire sobre ello.",
    "desconocido: espacio libre para la ficcion, sin contradecir lo documentado.",
    "inventado: usalo dentro del grado de licencia del encargo.",
    "Lo que un anclaje marca como «no lo dice la cita» no lo cuentes como hecho.",
)


async def reglas(db: aiosqlite.Connection, numero: int = 1) -> Bloque:
    """Bloque 6. Voz, estilo, reglas de escritura, glosario, prohibidas y lo ya gastado.

    Aquí llegan `grado_licencia`, `arcaismo` y `contenido_admisible`, que ningún validador
    lee por sí solo y que aun así son obligatorios: sin declararlos, esa política existiría
    igualmente pero la pondría el modelo, que es justo lo que este arnés evita en todo lo
    demás.

    Al final van **las palabras que la novela más repite hasta N-1 y las frases con que
    cerró cada capítulo**. El escritor solo lee N-1 y no puede ver la repetición de la
    novela entera; se le dice cuál es. Son lo primero que se recorta.
    """
    fragmentos: list[str] = []
    obra = await canon.obra(db)
    if obra is not None:
        fragmentos.append(f"Voz: {_valor(obra, 'voz')}")
    fragmentos.append(
        "Reglas de escritura:\n- "
        + "\n- ".join(REGLAS_DE_ESCRITURA)
        + "\nQue hacer con cada anclaje segun su firmeza:\n- "
        + "\n- ".join(USO_DE_LA_FIRMEZA)
    )

    estilo: dict[str, Any] = await canon.estilo(db)
    if estilo:
        fragmentos.append(
            "Politica de la frontera historia-ficcion: "
            + json.dumps(estilo, ensure_ascii=False, sort_keys=True)
        )

    prohibidas = await canon.prohibidas(db)
    if prohibidas:
        fragmentos.append(
            "Terminos prohibidos (no aparecen en el texto bajo ninguna forma): "
            + ", ".join(_valor(p, "termino") for p in prohibidas)
        )

    glosario = await canon.glosario(db)
    if glosario:
        fragmentos.append(
            "Glosario de epoca: "
            + "; ".join(f"{_valor(g, 'termino')} = {_valor(g, 'significado')}" for g in glosario)
        )
    fijos = min(3, len(fragmentos))

    anteriores = await texto.textos_aprobados(db, numero) if numero > 1 else []
    if anteriores:
        nombres = await canon.nombres_de_personajes(db)
        palabras, expresiones = repeticion.mas_repetidas(anteriores, excluir=nombres)
        if palabras or expresiones:
            fragmentos.append(
                "Ya muy repetido en la novela; usalo lo menos posible y busca otras formas: "
                + repeticion.como_lista([*palabras, *expresiones])
            )
        cierres = [repeticion.ultima_frase(t) for t in anteriores]
        fragmentos.append(
            "Frases con las que ya cerraron capitulos anteriores; no las repitas ni cierres "
            "con la misma idea:\n- " + "\n- ".join(c for c in cierres if c)
        )

    return Bloque(6, tuple(fragmentos), fijos=fijos)


async def personalizacion(db: aiosqlite.Connection, numero: int) -> Bloque:
    """Bloque 7. Los elementos del encargo que este capítulo tiene que tocar.

    Salen de los anclajes que la escaleta hizo a escenas de este capítulo, no de una lista
    general: lo que se comprueba después con `cobertura_capitulo` es exactamente esto.
    """
    fragmentos = []
    for dato in await intake.datos_de_capitulo(db, numero):
        marca = "OBLIGATORIO" if int(dato["obligatorio"]) else "opcional"
        fragmentos.append(f"[{marca}] {_valor(dato, 'tipo')}: {_valor(dato, 'valor_json')}")
    return Bloque(7, tuple(fragmentos), fijos=len(fragmentos))
