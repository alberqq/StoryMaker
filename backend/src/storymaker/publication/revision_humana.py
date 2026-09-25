"""spec: §4.5 · arq: §11b

`revision_humana`: **la misma rúbrica que el juez, puntuada por una persona**.

El módulo no juzga nada: prepara la hoja en la que la persona puntúa, valida lo que
devuelve, lo registra como *score* al lado del juez y compone el acta que compara las dos
notas criterio a criterio. Leer la novela y puntuarla es trabajo de la persona, y ningún
código lo sustituye.

**La hoja no copia las preguntas.** Nombra los criterios y remite a `rubrica.yaml`, que es
el fichero del que se puntúa (ver `docs/revision-humana.md` §1): una hoja con las preguntas
copiadas dejaría de decir lo mismo que el juez el día que el fichero cambiara.

**La hoja no lleva las notas del juez.** Puntuar viéndolas contamina la nota; el acta las
pone al lado solo cuando la persona ya ha registrado las suyas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import aiosqlite
import yaml

from storymaker.commons.errores import ErrorDeStoryMaker
from storymaker.commons.obs.scores import registrar
from storymaker.commons.obs.trazas import Observador

RUBRICA = Path(__file__).with_name("rubrica.yaml")
VALIDADOR = "revision_humana"

#: A partir de cuántos puntos de diferencia una divergencia se anota en el acta.
DIVERGENCIA = 2


class HojaInvalida(ErrorDeStoryMaker):
    """La hoja rellena no se puede registrar: le falta un criterio, una nota o su porqué."""


@cache
def criterios() -> tuple[str, ...]:
    datos = yaml.safe_load(RUBRICA.read_text(encoding="utf-8"))
    return tuple(str(c["nombre"]) for c in datos.get("criterios", []))


@cache
def _escala() -> tuple[int, int, float]:
    escala = yaml.safe_load(RUBRICA.read_text(encoding="utf-8")).get("escala", {})
    return int(escala["minimo"]), int(escala["maximo"]), float(escala["umbral_de_publicacion"])


def hoja(novela: str, version: int) -> str:
    """La hoja en blanco, en YAML, para una versión publicada."""
    minimo, maximo, _ = _escala()
    lineas = [
        f"# Revision humana de {novela}, version {version}.",
        f"# Las preguntas de cada criterio estan en {RUBRICA.name}: puntua desde ese fichero.",
        f"# Cada criterio lleva una nota entera de {minimo} a {maximo} y su justificacion.",
        "# No mires las notas del juez hasta haber registrado las tuyas.",
        f"novela: {novela}",
        f"version: {version}",
        "revisor: ''",
        "duracion_de_la_lectura: ''",
        "criterios:",
    ]
    for nombre in criterios():
        lineas += [f"  {nombre}:", "    valor:", "    justificacion: ''"]
    lineas.append("notas_al_margen: ''")
    return "\n".join(lineas) + "\n"


@dataclass(frozen=True)
class Fila:
    criterio: str
    persona: int
    juez: int | None
    justificacion: str

    @property
    def diferencia(self) -> int | None:
        return None if self.juez is None else self.persona - self.juez


@dataclass(frozen=True)
class Acta:
    novela: str
    version: int
    revisor: str
    duracion: str
    filas: tuple[Fila, ...]

    @property
    def media_persona(self) -> float:
        return sum(f.persona for f in self.filas) / len(self.filas)

    @property
    def media_juez(self) -> float | None:
        notas = [f.juez for f in self.filas if f.juez is not None]
        return sum(notas) / len(notas) if notas else None

    @property
    def divergencias(self) -> tuple[Fila, ...]:
        return tuple(
            f for f in self.filas if f.diferencia is not None and abs(f.diferencia) > DIVERGENCIA
        )

    def como_markdown(self) -> str:
        """El acta con la forma de la plantilla de `docs/revision-humana.md` §5."""
        juez = self.media_juez
        lineas = [
            f"### {date.today().isoformat()} · {self.novela} · versión {self.version}",
            "",
            f"**Revisor:** {self.revisor or '—'} · **Duración de la lectura:** "
            f"{self.duracion or '—'}",
            "",
            "| Criterio | Persona | Juez | Justificación de la persona |",
            "|---|---|---|---|",
        ]
        for f in self.filas:
            nota_juez = "—" if f.juez is None else str(f.juez)
            lineas.append(
                f"| {f.criterio} | {f.persona} | {nota_juez} | "
                f"{f.justificacion.replace('|', '/')} |"
            )
        lineas.append(
            f"| **Media** | {self.media_persona:.2f} | "
            f"{'—' if juez is None else f'{juez:.2f}'} | |"
        )
        lineas += ["", f"**Divergencias por encima de {DIVERGENCIA} puntos:**", ""]
        if self.divergencias:
            lineas += [
                f"- {f.criterio}: persona {f.persona}, juez {f.juez} ({f.diferencia:+d})"
                for f in self.divergencias
            ]
        else:
            lineas.append("Ninguna.")
        lineas += ["", "**Qué se hace con ellas:**", "", "**Sesión de red-teaming asociada:**", ""]
        return "\n".join(lineas)


def leer_hoja(texto: str) -> dict[str, Any]:
    """Valida la hoja rellena. Todo criterio de la rúbrica, con nota en escala y porqué."""
    try:
        datos = yaml.safe_load(texto) or {}
    except yaml.YAMLError as error:
        raise HojaInvalida(f"La hoja no es YAML valido: {error}") from error
    minimo, maximo, _ = _escala()
    puntuados = datos.get("criterios") or {}
    faltan = [c for c in criterios() if c not in puntuados]
    if faltan:
        raise HojaInvalida(f"Faltan criterios en la hoja: {', '.join(faltan)}.")
    sobran = [c for c in puntuados if c not in criterios()]
    if sobran:
        raise HojaInvalida(
            f"La hoja puntua criterios que la rubrica no tiene: {', '.join(sobran)}."
        )
    for nombre in criterios():
        entrada = puntuados[nombre] or {}
        valor = entrada.get("valor")
        if not isinstance(valor, int) or not minimo <= valor <= maximo:
            raise HojaInvalida(f"{nombre}: la nota tiene que ser un entero de {minimo} a {maximo}.")
        if len(str(entrada.get("justificacion") or "").strip()) < 10:
            raise HojaInvalida(f"{nombre}: falta la justificacion, o es demasiado corta.")
    return datos


async def notas_del_juez(db: aiosqlite.Connection) -> dict[str, int]:
    """Las notas por criterio del último juicio, o vacío si el juez no ha juzgado."""
    async with db.execute(
        "SELECT detalle_json FROM score WHERE validador = 'juez_rubrica' ORDER BY id DESC LIMIT 1"
    ) as cursor:
        fila = await cursor.fetchone()
    if fila is None or not fila["detalle_json"]:
        return {}
    detalle = json.loads(str(fila["detalle_json"]))
    return {c: int(detalle[c]) for c in criterios() if isinstance(detalle.get(c), int)}


async def registrar_revision(
    db: aiosqlite.Connection, observador: Observador, texto_hoja: str
) -> Acta:
    """Registra la hoja como *score* `revision_humana` y devuelve el acta comparada.

    El *score* va a la tabla `score`, al lado del del juez, y a la sesión de Langfuse de la
    novela, con el mismo nombre en los dos sitios.
    """
    datos = leer_hoja(texto_hoja)
    version = int(datos.get("version") or 0)
    async with db.execute("SELECT 1 FROM version_novela WHERE numero = ?", (version,)) as cursor:
        if await cursor.fetchone() is None:
            raise HojaInvalida(f"La novela no tiene publicada la version {version}.")

    puntuados = datos["criterios"]
    juez = await notas_del_juez(db)
    filas = tuple(
        Fila(
            criterio=nombre,
            persona=int(puntuados[nombre]["valor"]),
            juez=juez.get(nombre),
            justificacion=str(puntuados[nombre]["justificacion"]).strip(),
        )
        for nombre in criterios()
    )
    acta = Acta(
        novela=str(datos.get("novela") or ""),
        version=version,
        revisor=str(datos.get("revisor") or ""),
        duracion=str(datos.get("duracion_de_la_lectura") or ""),
        filas=filas,
    )
    await registrar(
        db,
        observador,
        validador=VALIDADOR,
        valor=acta.media_persona,
        objeto_tipo="novela",
        objeto_id=version,
        detalle={
            **{f.criterio: f.persona for f in filas},
            "justificaciones": {f.criterio: f.justificacion for f in filas},
            "revisor": acta.revisor,
        },
    )
    return acta
