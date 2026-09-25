"""spec: §4.3, §7.2 · arq: §11a, §11c

La revisión que guarda, repara y no cierra la fija `specs/trama-rehacible/spec.md` §3.

La revisión de la escaleta: **lo que se comprueba antes de abrir el gate de Plotting**.

Aquí corren los dos validadores más rentables del sistema, y lo son por la misma razón: se
ejecutan cuando todavía no se ha escrito una línea, y arreglarlos cuesta un párrafo de
escaleta en lugar de diez capítulos escritos y pagados.

`cobertura_anclada` comprueba que cada elemento obligatorio del encargo está anclado a
alguna escena. `arco_anclado` comprueba que todo personaje recurrente tiene arco — y admite
el plano, que es lo que evita que la exigencia se convierta en una puerta atascada. Y corre
**la cronología deducida de la escaleta**, que es el más barato de sus tres puntos de
ejecución: la escaleta ya declara qué día ocurre cada escena y quién está en ella.

**Nada de esto cierra el gate**: el Autor puede aprobar con avisos, como pide el criterio de
producto. Lo que la revisión hace es servir para algo en los dos caminos. Un elemento
obligatorio sin anclar **se ancla solo** a la escena que más se le parece, y queda dicho;
lo demás se guarda como incidencia, lo enseña el gate y **llega al arquitecto si el Autor
rehace**, de modo que rehacer sin comentario ya es un reintento dirigido.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

import aiosqlite

from storymaker.commons.config import Defaults
from storymaker.commons.db.repos import arnes, canon, intake, plan
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.commons.formal import evaluacion
from storymaker.commons.formal.cronologia import verificar_cronologia
from storymaker.commons.formal.generador import (
    DIA,
    Evento,
    NovelaLean,
    Persona,
    a_momento,
    leer_fecha,
    nacimiento_de,
)
from storymaker.commons.formal.generador import (
    NACIMIENTO_DESCONOCIDO as NACIMIENTO_DESCONOCIDO,
)
from storymaker.commons.validation.escaleta import arco_anclado, cobertura_anclada
from storymaker.commons.validation.modelos import (
    ArcoEnRevision,
    EscaletaEnRevision,
    Incidencia,
    Severidad,
)
from storymaker.commons.validation.puras import normalizar


async def construir_revision(db: aiosqlite.Connection) -> EscaletaEnRevision:
    """Traduce la base a los tipos del Core Domain. El validador no ve SQLite."""
    obra = await canon.obra(db)
    homenajeado = await canon.homenajeado(db)
    homenajeado_id = int(homenajeado["id"]) if homenajeado is not None else None

    apariciones = await plan.apariciones_por_personaje(db)
    nombres: dict[int, str] = {}
    arcos: list[ArcoEnRevision] = []

    for fila in await canon.arcos(db):
        personaje_id = int(fila["personaje_id"])
        nombres[personaje_id] = str(fila["personaje"])
        hitos = await canon.hitos_de_arco(db, int(fila["id"]))
        capitulos = tuple(
            int(h["capitulo_numero"]) for h in hitos if h["capitulo_numero"] is not None
        )
        arcos.append(
            ArcoEnRevision(
                personaje_id=personaje_id,
                personaje=str(fila["personaje"]),
                tipo=str(fila["tipo"]),
                hitos_por_capitulo=capitulos,
                es_homenajeado=personaje_id == homenajeado_id,
            )
        )

    for personaje_id in apariciones:
        if personaje_id not in nombres:
            fichas = await canon.personajes(db, [personaje_id])
            nombres[personaje_id] = str(fichas[0]["nombre"]) if fichas else str(personaje_id)

    obligatorios = await intake.obligatorios(db)
    sin_anclar = {int(f["id"]) for f in await intake.obligatorios_sin_anclar(db)}
    todos = tuple(int(f["id"]) for f in obligatorios)

    return EscaletaEnRevision(
        n_capitulos=(
            int(obra["n_capitulos"]) if obra is not None else await plan.total_de_capitulos(db)
        ),
        apariciones_por_personaje=apariciones,
        nombres_por_personaje=nombres,
        arcos=tuple(arcos),
        obligatorios=todos,
        obligatorios_anclados=frozenset(d for d in todos if d not in sin_anclar),
    )


async def cronologia_de_la_escaleta(db: aiosqlite.Connection) -> NovelaLean:
    """La cronología que se deduce de la escaleta, sin haber redactado nada.

    Cada escena es un evento con su fecha y sus personajes; cada personaje, una persona con
    sus fechas vitales. Con eso, los cuatro invariantes ya tienen material: si el arquitecto
    puso a alguien en una escena posterior a su muerte documentada, cae aquí.
    """
    personas: list[Persona] = []
    async with db.execute(
        "SELECT id, nombre, fecha_nacimiento, fecha_muerte FROM canon_personaje ORDER BY id"
    ) as cursor:
        for fila in await cursor.fetchall():
            personas.append(
                Persona(
                    id=int(fila["id"]),
                    nombre=str(fila["nombre"]),
                    nacimiento=nacimiento_de(fila["fecha_nacimiento"]),
                    muerte=a_momento(fila["fecha_muerte"]),
                )
            )

    eventos: list[Evento] = []
    async with db.execute(
        """
        SELECT e.id, e.orden, e.fecha_narrativa, e.escenario_id, c.numero
          FROM plan_escena e
          JOIN plan_capitulo c ON c.id = e.capitulo_id
         ORDER BY c.numero, e.orden
        """
    ) as cursor:
        escenas = list(await cursor.fetchall())

    for fila in escenas:
        fecha = leer_fecha(fila["fecha_narrativa"])
        momento = fecha.momento
        if momento is None:
            # Una escena sin fecha no se puede juzgar temporalmente, y no tenerla no es un
            # error: el arquitecto puede dejarla al aire. Lean no opina sobre lo que no sabe.
            continue
        async with db.execute(
            "SELECT personaje_id FROM plan_escena_personaje WHERE escena_id = ?",
            (fila["id"],),
        ) as cursor2:
            participantes = tuple(int(p["personaje_id"]) for p in await cursor2.fetchall())
        eventos.append(
            Evento(
                id=int(fila["id"]),
                clave=f"cap{fila['numero']}-esc{fila['orden']}",
                momento=momento,
                # Solo lo fechado al día puede estar «en otro sitio el mismo día»: una
                # escena de «1856» no ocurre el 1 de enero. Sin día, el escenario pasa a
                # desconocido, que I3 no cuenta.
                lugar=int(fila["escenario_id"] or 0) if fecha.precision == DIA else 0,
                participantes=participantes,
                objetos=(),
                origen="narrativo",
            )
        )

    return NovelaLean(personas=tuple(personas), objetos=(), eventos=tuple(eventos))


@dataclass(frozen=True)
class PuertaDePlotting:
    incidencias: tuple[Incidencia, ...]

    @property
    def abierta(self) -> bool:
        return not any(i.bloquea for i in self.incidencias)


async def comprobar(db: aiosqlite.Connection) -> PuertaDePlotting:
    """Los dos validadores del gate. Lean corre aparte, porque necesita el subproceso."""
    revision = await construir_revision(db)
    # Los anclajes que el volcado no pudo resolver (ER §7.2). Avisan y no bloquean: la
    # escena existe igual, y lo que falte de cobertura ya lo bloquea `cobertura_anclada`.
    sin_resolver = [
        Incidencia(validador="anclaje_resuelto", severidad=Severidad.AVISO, mensaje=mensaje)
        for mensaje in await arnes.incidencias_sin_capitulo(db, "anclaje_resuelto")
    ]
    fuera_de_rango = await escenas_fuera_de_rango(db)
    return PuertaDePlotting(
        tuple(
            [*cobertura_anclada(revision), *arco_anclado(revision), *sin_resolver, *fuera_de_rango]
        )
    )


async def escenas_fuera_de_rango(db: aiosqlite.Connection) -> list[Incidencia]:
    """Un aviso por capítulo con menos o más escenas que el rango de §19. No bloquea."""
    minimo, maximo = Defaults.RANGO_ESCENAS_POR_CAPITULO
    return [
        Incidencia(
            validador="escenas_por_capitulo",
            severidad=Severidad.AVISO,
            mensaje=(
                f"El capitulo {numero} tiene {escenas} escena(s); "
                f"la escaleta pide entre {minimo} y {maximo}."
            ),
        )
        for numero, escenas in await plan.escenas_por_capitulo(db)
        if not minimo <= escenas <= maximo
    ]


#: Los validadores de la revisión que dejan incidencia guardada. `anclaje_resuelto` lo
#: escribe el volcado; los demás, `revisar`.
VALIDADORES_DE_LA_TRAMA = (
    "cobertura_anclada",
    "cobertura_reparada",
    "arco_anclado",
    "escenas_por_capitulo",
    "anclaje_resuelto",
    "anclaje_por_parecido",
    "invencion_sobre_historico",
    evaluacion.VALIDADOR,
    "lean_cronologia",
)

#: Los que escribe el volcado de la escaleta y no la revisión, que por eso no los retira.
ESCRITOS_POR_EL_VOLCADO = ("anclaje_resuelto", "anclaje_por_parecido")


def _coseno(a: list[float], b: list[float]) -> float:
    norma = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=False)) / norma if norma else 0.0


async def reparar_cobertura(
    db: aiosqlite.Connection, vectorizador: Vectorizador
) -> list[Incidencia]:
    """Ancla cada elemento obligatorio suelto a la escena que más se le parece.

    Es lo que convierte `cobertura_anclada` en algo más que un aviso: el elemento llega al
    paquete del escritor con su escena, que es donde el escritor mira qué tiene que usar.
    Que la escena sea la acertada lo decide un parecido de embeddings y no el arquitecto,
    así que se dice —cuál y dónde— para que el Autor lo mueva si no le convence.

    **Antes del parecido, la fecha** (trama-rehacible §3.2). Si el elemento lleva fecha —el
    evento ancla lleva la del encargo—, solo compiten las escenas de su año, y de ellas las
    de su mes si las hay. El parecido de embeddings no sabe de tiempo: dejaba la
    inauguración de octubre de 1919 en una escena de 1917 porque hablaba del Metro.
    """
    sueltos = await intake.obligatorios_sin_anclar(db)
    escenas = await plan.escenas_con_texto(db)
    if not sueltos or not escenas:
        return []

    textos_de_escena = [str(e["texto"]).strip() or f"escena {e['orden']}" for e in escenas]
    vectores_de_escena = vectorizador.vectorizar(textos_de_escena)
    evento_ancla = await _evento_ancla_con_fecha(db)
    avisos: list[Incidencia] = []
    for dato in sueltos:
        valor = _valor(dato["valor_json"])
        referencia = evento_ancla if normalizar(valor).startswith("evento ancla") else valor
        candidatas = escenas_de_su_fecha(referencia, [e["fecha_narrativa"] for e in escenas])
        (vector,) = vectorizador.vectorizar([valor])
        indice = max(candidatas, key=lambda i: _coseno(vector, vectores_de_escena[i]))
        escena = escenas[indice]
        await plan.anclar_dato(db, int(escena["id"]), int(dato["id"]))
        avisos.append(
            Incidencia(
                validador="cobertura_reparada",
                severidad=Severidad.AVISO,
                mensaje=(
                    f"«{valor}» es obligatorio y el arquitecto no lo anclo a ninguna escena: "
                    f"se ha anclado al capitulo {escena['capitulo']}, escena {escena['orden']}."
                ),
                ubicacion=f"cap{escena['capitulo']}-esc{escena['orden']}",
            )
        )
    return avisos


_ANIO = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
_MES_ISO = re.compile(r"\b\d{4}-(\d{2})\b")
_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip


def _anios_y_meses(texto: str | None) -> tuple[set[int], set[int]]:
    """Los años y los meses que nombra un texto, en cifra o en castellano."""
    if not texto:
        return set(), set()
    anios = {int(a) for a in _ANIO.findall(texto)}
    palabras = set(normalizar(texto).split())
    meses = {i + 1 for i, mes in enumerate(_MESES) if mes in palabras}
    meses |= {int(m) for m in _MES_ISO.findall(texto) if 1 <= int(m) <= 12}
    return anios, meses


def escenas_de_su_fecha(referencia: str, fechas: list[object]) -> list[int]:
    """Los índices de las escenas que casan con la fecha de la referencia.

    Sin fecha en la referencia, o sin ninguna escena de su año, compiten todas: la fecha
    estrecha la búsqueda, nunca la deja sin candidatas.
    """
    anios, meses = _anios_y_meses(referencia)
    todas = list(range(len(fechas)))
    if not anios:
        return todas

    def sintonia(i: int) -> int:
        suyos, sus_meses = _anios_y_meses(str(fechas[i] or ""))
        if not anios & suyos:
            return 0
        return 2 + (1 if meses & sus_meses else 0)

    mejor = max(sintonia(i) for i in todas)
    return [i for i in todas if sintonia(i) == mejor] if mejor else todas


async def _brief_guardado(db: aiosqlite.Connection) -> dict[str, object]:
    """La fotografía del encargo, como diccionario. Vacía si no hay o no se lee."""
    async with db.execute("SELECT json FROM intake_brief ORDER BY id DESC LIMIT 1") as cursor:
        fila = await cursor.fetchone()
    if fila is None:
        return {}
    try:
        cargado = json.loads(str(fila["json"]))
    except json.JSONDecodeError:
        return {}
    return cargado if isinstance(cargado, dict) else {}


async def _evento_ancla_con_fecha(db: aiosqlite.Connection) -> str:
    """El evento ancla del encargo con su fecha, que es contra lo que se busca su escena."""
    brief = await _brief_guardado(db)
    return " ".join(str(brief.get(c) or "") for c in ("evento_ancla", "fecha_evento_ancla"))


async def invenciones_sobre_historicos(
    db: aiosqlite.Connection, hecho_ids: Iterable[int] | None = None
) -> list[Incidencia]:
    """Un aviso por hecho inventado que nombra a un personaje histórico (trama-rehacible §4.4).

    La invención autorizada no tiene cita que verificar, y por eso nadie la comprobaba. Pero
    lo que se inventa para un hueco es ambiente, no biografía: un hecho que convierte a un
    ingeniero real en jefe de una oficina donde nunca trabajó llegaba al canon sin que nada
    lo parase. Se detecta por el nombre —completo o por su último apellido— y **avisa**: el
    Autor lo corrige con la edición directa del hecho, o rehace. No hace falta un modelo
    para saber que una frase sin fuente habla de alguien real.
    """
    historicos = await _nombres_historicos(db)
    if not historicos:
        return []
    async with db.execute(
        "SELECT id, enunciado FROM mundo_hecho WHERE origen = 'invencion_autorizada' ORDER BY id"
    ) as cursor:
        filas = list(await cursor.fetchall())
    elegidos = None if hecho_ids is None else set(hecho_ids)
    avisos: list[Incidencia] = []
    for fila in filas:
        if elegidos is not None and int(fila["id"]) not in elegidos:
            continue
        enunciado = str(fila["enunciado"])
        for nombre in historicos:
            if not nombra_a(enunciado, nombre):
                continue
            avisos.append(
                Incidencia(
                    validador="invencion_sobre_historico",
                    severidad=Severidad.AVISO,
                    mensaje=(
                        f"El hecho inventado #{fila['id']} dice algo de «{nombre}», que es un "
                        f"personaje historico, sin fuente que lo respalde: «{enunciado}». "
                        f"Si no es cierto, corrigelo antes de sellar."
                    ),
                    ubicacion=f"hecho #{fila['id']}",
                )
            )
    return avisos


async def recalcular_invenciones(db: aiosqlite.Connection) -> None:
    """Vuelve a mirar lo inventado tras una edición directa del Autor en el gate.

    La revisión no se repite al editar, y sin esto el aviso de un hecho ya corregido —o de
    un personaje al que el Autor le cambió el nombre— seguiría en la pantalla diciendo lo
    que ya no es verdad.
    """
    await arnes.retirar_incidencias_sin_capitulo(db, "invencion_sobre_historico")
    for aviso in await invenciones_sobre_historicos(db):
        await arnes.registrar_incidencia(
            db,
            validador=aviso.validador,
            severidad=aviso.severidad.value,
            mensaje=aviso.mensaje,
            ubicacion=aviso.ubicacion,
        )


#: Palabras que, delante de un nombre, lo convierten en el de un lugar o una institución:
#: el Canal de Isabel II no es la reina, ni la calle de Gravina el almirante.
DELANTE_DE_UN_LUGAR = frozenset(
    {
        "avenida", "barrio", "cafe", "calle", "canal", "colegio", "compania", "convento",
        "estacion", "fuente", "fundacion", "glorieta", "hospital", "hotel", "iglesia",
        "instituto", "museo", "palacio", "parque", "paseo", "plaza", "premio", "puente",
        "puerta", "puerto", "ronda", "teatro", "universidad",
    }
)  # fmt: skip
_ENLACES = frozenset({"de", "del", "la", "las", "el", "los"})
_PALABRA = re.compile(r"\w+")


def nombra_a(texto: str, nombre: str) -> bool:
    """Si el texto nombra a esa persona, y no a un sitio que lleva su nombre.

    Cuenta el nombre entero, o su último apellido si tiene cinco letras o más **y va con
    mayúscula**: «Valle dirigió la obra» nombra a Lucio del Valle; «el valle del Lozoya», no.
    Y ninguna de las dos formas cuenta detrás de una palabra de lugar —«Canal», «calle»,
    «plaza»…—, saltándose los «de», «del» y artículos de en medio.
    """
    originales = _PALABRA.findall(texto)
    palabras = [normalizar(p) for p in originales]
    buscado = normalizar(nombre).split()
    if not buscado:
        return False
    ultimo = buscado[-1]
    for i in range(len(palabras)):
        entero = palabras[i : i + len(buscado)] == buscado
        apellido = (
            len(buscado) > 1
            and len(ultimo) >= 5
            and palabras[i] == ultimo
            and originales[i][:1].isupper()
        )
        if (entero or apellido) and not _detras_de_un_lugar(palabras, i):
            return True
    return False


def _detras_de_un_lugar(palabras: list[str], i: int) -> bool:
    j = i - 1
    while j >= 0 and palabras[j] in _ENLACES:
        j -= 1
    return j >= 0 and palabras[j] in DELANTE_DE_UN_LUGAR


async def _nombres_historicos(db: aiosqlite.Connection) -> list[str]:
    """Los personajes históricos del canon y del encargo, sin el homenajeado."""
    homenajeado = await canon.homenajeado(db)
    excluido = str(homenajeado["nombre"]) if homenajeado is not None else None
    async with db.execute(
        "SELECT nombre FROM canon_personaje WHERE tipo LIKE 'historico%' ORDER BY id"
    ) as cursor:
        nombres = [str(f["nombre"]) for f in await cursor.fetchall()]
    personajes = (await _brief_guardado(db)).get("personajes_historicos") or []
    if isinstance(personajes, list):
        nombres += [str(p["nombre"]) for p in personajes if isinstance(p, dict) and p.get("nombre")]
    vistos: list[str] = []
    for nombre in nombres:
        if nombre != excluido and nombre not in vistos:
            vistos.append(nombre)
    return vistos


def _valor(valor_json: object) -> str:
    try:
        cargado = json.loads(str(valor_json))
    except json.JSONDecodeError:
        return str(valor_json)
    if isinstance(cargado, dict):
        return str(cargado.get("valor", "")) or json.dumps(cargado, ensure_ascii=False)
    return str(cargado)


async def comprobar_cronologia(db: aiosqlite.Connection) -> list[Incidencia]:
    """La cronología de la escaleta, con Lean si está instalado y en Python si no.

    Con Lean, sus incidencias bajan a aviso: aquí no hay capítulo que devolver al editor,
    solo una escaleta que el Autor decide si rehacer. Un fallo de Lean —no compila, no
    arranca— tampoco detiene nada: se cae a la evaluación en Python, que mira lo mismo. Es
    el mismo cálculo que el de Writing y el de la publicación; solo cambia la severidad.
    """
    return await verificar_cronologia(
        await cronologia_de_la_escaleta(db), bloquea=False, validador=evaluacion.VALIDADOR
    )


#: Los validadores de la revisión que puntúan en Langfuse. Uno por nombre de §11a y §11c.
PUNTUADOS_EN_LA_TRAMA = ("cobertura_anclada", "arco_anclado", evaluacion.VALIDADOR)


async def puntuar(db: aiosqlite.Connection, incidencias: Iterable[Incidencia]) -> None:
    """Un *score* por validador de la revisión, también cuando pasa (ver `registrar_veredicto`).

    Fuera de una invocación —la interfaz recalcula la revisión tras una edición— no hay
    observador, y el *score* se queda solo en la base.
    """
    from storymaker.commons.graph.dependencias import SinDependencias, actuales
    from storymaker.commons.obs.scores import registrar_veredicto
    from storymaker.commons.obs.trazas import ObservadorNulo

    try:
        observador = actuales().observador
    except SinDependencias:
        observador = ObservadorNulo()
    lista = list(incidencias)
    for validador in PUNTUADOS_EN_LA_TRAMA:
        await registrar_veredicto(
            db,
            observador,
            validador=validador,
            incidencias=[i for i in lista if i.validador == validador],
            objeto_tipo="escaleta",
            objeto_id=1,
        )


async def revisar(db: aiosqlite.Connection, vectorizador: Vectorizador) -> PuertaDePlotting:
    """Repara la cobertura, comprueba lo demás y **guarda** lo que encuentre.

    Guardarlo es lo que permite que lo lean tres sitios distintos sin volver a calcularlo:
    el aviso del gate, la pantalla del gate y el prompt del arquitecto si el Autor rehace.
    `anclaje_resuelto` y `anclaje_por_parecido` no se retiran aquí porque los escribe el
    volcado, justo antes.
    """
    for validador in VALIDADORES_DE_LA_TRAMA:
        if validador not in ESCRITOS_POR_EL_VOLCADO:
            await arnes.retirar_incidencias_sin_capitulo(db, validador)

    reparadas = await reparar_cobertura(db, vectorizador)
    puerta = await comprobar(db)
    cronologia = await comprobar_cronologia(db)
    inventadas = await invenciones_sobre_historicos(db)
    nuevas = [
        *reparadas,
        *(i for i in puerta.incidencias if i.validador not in ESCRITOS_POR_EL_VOLCADO),
        *cronologia,
        *inventadas,
    ]
    for incidencia in nuevas:
        await arnes.registrar_incidencia(
            db,
            validador=incidencia.validador,
            severidad=incidencia.severidad.value,
            mensaje=incidencia.mensaje,
            ubicacion=incidencia.ubicacion,
            propuesta=incidencia.propuesta,
        )
    await puntuar(db, (*puerta.incidencias, *cronologia))
    return PuertaDePlotting((*puerta.incidencias, *reparadas, *cronologia, *inventadas))


async def incidencias_guardadas(db: aiosqlite.Connection) -> list[Incidencia]:
    """Lo que la última revisión dejó escrito, en el orden en que lo encontró."""
    marcas = ",".join("?" for _ in VALIDADORES_DE_LA_TRAMA)
    async with db.execute(
        f"""
        SELECT validador, severidad, mensaje, ubicacion, propuesta FROM incidencia
         WHERE capitulo_version_id IS NULL AND validador IN ({marcas})
         ORDER BY id
        """,  # noqa: S608 - solo marcadores
        VALIDADORES_DE_LA_TRAMA,
    ) as cursor:
        return [
            Incidencia(
                validador=str(f["validador"]),
                severidad=Severidad(str(f["severidad"])),
                mensaje=str(f["mensaje"]),
                ubicacion=f["ubicacion"],
                propuesta=f["propuesta"],
            )
            for f in await cursor.fetchall()
        ]


async def retirar_incidencias(db: aiosqlite.Connection) -> None:
    for validador in VALIDADORES_DE_LA_TRAMA:
        await arnes.retirar_incidencias_sin_capitulo(db, validador)
