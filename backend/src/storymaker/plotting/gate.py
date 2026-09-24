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
import shutil
from dataclasses import dataclass

import aiosqlite

from storymaker.commons.config import Defaults
from storymaker.commons.db.repos import arnes, canon, intake, plan
from storymaker.commons.embeddings.modelo import Vectorizador
from storymaker.commons.formal import evaluacion
from storymaker.commons.formal.generador import (
    Evento,
    NovelaLean,
    Persona,
    a_momento,
)
from storymaker.commons.validation.escaleta import arco_anclado, cobertura_anclada
from storymaker.commons.validation.modelos import (
    ArcoEnRevision,
    EscaletaEnRevision,
    Incidencia,
    Severidad,
)


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
                    nacimiento=_nacimiento(fila["fecha_nacimiento"]),
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
        momento = a_momento(fila["fecha_narrativa"])
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
                lugar=int(fila["escenario_id"] or 0),
                participantes=participantes,
                objetos=(),
                origen="narrativo",
            )
        )

    return NovelaLean(personas=tuple(personas), objetos=(), eventos=tuple(eventos))


#: El nacimiento de quien no tiene fecha: tan atrás que ninguna escena cae antes. Con `0`
#: —el 1 de enero de 1800— toda escena del siglo XVI ponía a sus personajes antes de nacer.
NACIMIENTO_DESCONOCIDO = -(10**7)


def _nacimiento(fecha: object) -> int:
    momento = a_momento(str(fecha)) if fecha else None
    return NACIMIENTO_DESCONOCIDO if momento is None else momento


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
    evaluacion.VALIDADOR,
    "lean_cronologia",
)


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
    """
    sueltos = await intake.obligatorios_sin_anclar(db)
    escenas = await plan.escenas_con_texto(db)
    if not sueltos or not escenas:
        return []

    textos_de_escena = [str(e["texto"]).strip() or f"escena {e['orden']}" for e in escenas]
    vectores_de_escena = vectorizador.vectorizar(textos_de_escena)
    avisos: list[Incidencia] = []
    for dato in sueltos:
        valor = _valor(dato["valor_json"])
        (vector,) = vectorizador.vectorizar([valor])
        indice = max(range(len(escenas)), key=lambda i: _coseno(vector, vectores_de_escena[i]))
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
    arranca— tampoco detiene nada: se cae a la evaluación en Python, que mira lo mismo.
    """
    novela = await cronologia_de_la_escaleta(db)
    if not novela.eventos:
        return []
    if shutil.which("lake") is not None:
        from storymaker.commons.formal import runner

        try:
            veredicto = await runner.verificar(novela)
        except Exception:  # cualquier avería de Lean cae a la evaluación en Python
            veredicto = None
        if veredicto is not None:
            return [
                Incidencia(
                    validador=i.validador,
                    severidad=Severidad.AVISO,
                    mensaje=i.mensaje,
                    ubicacion=i.ubicacion,
                    propuesta=i.propuesta,
                )
                for i in veredicto.incidencias
            ]
    return list(evaluacion.evaluar(novela).incidencias)


async def revisar(db: aiosqlite.Connection, vectorizador: Vectorizador) -> PuertaDePlotting:
    """Repara la cobertura, comprueba lo demás y **guarda** lo que encuentre.

    Guardarlo es lo que permite que lo lean tres sitios distintos sin volver a calcularlo:
    el aviso del gate, la pantalla del gate y el prompt del arquitecto si el Autor rehace.
    `anclaje_resuelto` no se retira aquí porque lo escribe el volcado, justo antes.
    """
    for validador in VALIDADORES_DE_LA_TRAMA:
        if validador != "anclaje_resuelto":
            await arnes.retirar_incidencias_sin_capitulo(db, validador)

    reparadas = await reparar_cobertura(db, vectorizador)
    puerta = await comprobar(db)
    cronologia = await comprobar_cronologia(db)
    nuevas = [
        *reparadas,
        *(i for i in puerta.incidencias if i.validador != "anclaje_resuelto"),
        *cronologia,
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
    return PuertaDePlotting((*puerta.incidencias, *reparadas, *cronologia))


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
