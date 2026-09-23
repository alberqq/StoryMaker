"""spec: §3.7, §8 · arq: §11c

Escribe el fichero generado, invoca el ejecutable de Lean y traduce su veredicto.

**El código de salida es el contrato**, y no la salida de texto: `verificar` sale con 0 si
la cronología cumple los cuatro invariantes y con 1 si no, imprimiendo los eventos
culpables agrupados por invariante. El nodo del grafo lee un entero y decide la arista; si
tuviera que parsear prosa, un cambio de redacción en Lean rompería la validación en Python
sin que nada se quejara. La prosa se usa solo para decirle al editor qué arreglar.

**Lo que este módulo distingue es más importante que lo que ejecuta.** Un invariante
violado es una *incidencia*: el capítulo vuelve al editor y el bucle sigue. Que `lake` no
esté instalado es un *error de entorno*: detiene la invocación y **no aprueba nada**.
Confundirlos aprobaría capítulos por avería — un fichero que no compila porque falta el
compilador diría exactamente lo mismo que uno que compila sin problemas.

Corre en **tres sitios**: el gate de Plotting sobre la cronología deducida de la escaleta,
la pasada del extractor de cada capítulo sobre la acumulada, y antes de publicar sobre la
novela entera. En el primero vuelve al arquitecto, en el segundo al editor y en el tercero
la versión **no se publica**.
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from storymaker.commons.errores import ErrorDeEntorno
from storymaker.commons.formal.generador import INVARIANTES, NovelaLean, generar
from storymaker.commons.validation.modelos import Incidencia, Severidad

#: El proyecto Lake vive fuera del backend: es un artefacto de verificación con vida
#: propia, y el arnés solo lo invoca.
PROYECTO_POR_DEFECTO: Final = Path(__file__).resolve().parents[5] / "formal" / "lean"

#: Dónde escribe el generador. `Cronologia.Basico` no se toca nunca.
FICHERO_GENERADO: Final = Path("Cronologia") / "Generado.lean"


@dataclass(frozen=True)
class Veredicto:
    """El resultado de una comprobación formal.

    Nunca contiene un error de entorno: eso viaja como excepción, precisamente para que no
    pueda confundirse con un veredicto favorable por descuido de quien lo lea.
    """

    correcto: bool
    incidencias: tuple[Incidencia, ...] = ()
    salida: str = ""


def interpretar(codigo: int, salida: str) -> Veredicto:
    """Traduce el código de salida y la prosa de `verificar` a incidencias.

    El código manda: cualquier valor distinto de cero es un fallo, aunque la salida no se
    reconozca. Las etiquetas `I1`…`I4` solo sirven para decir **cuál** y con qué eventos, y
    si no se reconoce ninguna se abre una incidencia genérica con la salida entera dentro —
    perder el detalle es aceptable; dar por bueno lo que fallo, no.
    """
    if codigo == 0:
        return Veredicto(correcto=True, salida=salida)

    incidencias = []
    for etiqueta, mensaje in INVARIANTES.items():
        if f"{etiqueta} ·" in salida or f"{etiqueta} " in salida:
            culpables = [
                linea.strip()
                for linea in salida.splitlines()
                if linea.startswith("    evento")
            ]
            incidencias.append(
                Incidencia(
                    validador="lean_cronologia",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje=mensaje,
                    ubicacion=etiqueta,
                    propuesta="\n".join(culpables[:5]) or None,
                )
            )

    if not incidencias:
        incidencias.append(
            Incidencia(
                validador="lean_cronologia",
                severidad=Severidad.BLOQUEANTE,
                mensaje=(
                    "La cronologia no supera la verificacion formal y la salida no nombra "
                    "ningun invariante conocido."
                ),
                propuesta=salida[:400] or None,
            )
        )
    return Veredicto(correcto=False, incidencias=tuple(incidencias), salida=salida)


def escribir_generado(novela: NovelaLean, *, proyecto: Path = PROYECTO_POR_DEFECTO) -> Path:
    """Vuelca los datos de la novela. Devuelve la ruta escrita."""
    destino = proyecto / FICHERO_GENERADO
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(generar(novela), encoding="utf-8")
    return destino


async def verificar(
    novela: NovelaLean, *, proyecto: Path = PROYECTO_POR_DEFECTO
) -> Veredicto:
    """Genera, compila y ejecuta. No cuesta un token: es aritmética.

    Por eso Lean es uno de los dos validadores de coste cero que la Fase 6 corre sobre los
    capítulos invalidados, y por eso puede correr en tres sitios sin que nadie mire el
    presupuesto de contexto.
    """
    if shutil.which("lake") is None:
        raise ErrorDeEntorno(
            "No se encuentra `lake` en el PATH. Sin el, la cronologia no se puede verificar, "
            "y un capitulo sin verificar no es un capitulo correcto: la invocacion se detiene "
            "en lugar de aprobarlo."
        )
    if not (proyecto / "lakefile.toml").exists():
        raise ErrorDeEntorno(
            f"No hay proyecto Lake en {proyecto}. El arnes invoca el proyecto de formal/lean, "
            f"no lo construye."
        )

    escribir_generado(novela, proyecto=proyecto)

    proceso = await asyncio.create_subprocess_exec(
        "lake",
        "exe",
        "verificar",
        cwd=str(proyecto),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    bruto, _ = await proceso.communicate()
    salida = bruto.decode("utf-8", errors="replace")
    codigo = proceso.returncode if proceso.returncode is not None else 1
    return interpretar(codigo, salida)
