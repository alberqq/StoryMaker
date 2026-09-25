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
import tempfile
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


class AveriaDeLean(ErrorDeEntorno):
    """`verificar` salió con fallo sin nombrar ningún invariante: no juzgó la cronología.

    Es lo que se ve cuando el fichero generado no compila o el sistema no deja ejecutar el
    binario —en Windows, Smart App Control lo bloquea a veces con el error 4551—. No es un
    veredicto negativo, y tratarlo como tal tumbaba novelas coherentes en la publicación.
    Viaja como error de entorno para que `verificar_cronologia` caiga a la evaluación en
    Python (arq. §11c), que juzga los mismos invariantes con la misma severidad.
    """


def interpretar(codigo: int, salida: str) -> Veredicto:
    """Traduce el código de salida y la prosa de `verificar` a incidencias.

    El código manda: con un valor distinto de cero, nada se da por bueno. Las etiquetas
    `I1`…`I4` dicen **cuál** cae y con qué eventos. Si no se reconoce ninguna, Lean no llegó
    a juzgar —no compiló o no se pudo ejecutar— y eso es una avería, que se lanza como
    `AveriaDeLean` en lugar de disfrazarse de invariante violado.
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
        raise AveriaDeLean(
            f"Lean salio con codigo {codigo} sin nombrar ningun invariante: no ha juzgado la "
            f"cronologia. Salida: {salida[-400:]}"
        )
    return Veredicto(correcto=False, incidencias=tuple(incidencias), salida=salida)


def escribir_generado(novela: NovelaLean, *, proyecto: Path = PROYECTO_POR_DEFECTO) -> Path:
    """Vuelca los datos de la novela. Devuelve la ruta escrita."""
    destino = proyecto / FICHERO_GENERADO
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(generar(novela), encoding="utf-8")
    return destino


async def verificar(novela: NovelaLean, *, proyecto: Path | None = None) -> Veredicto:
    """Genera, compila y ejecuta. No cuesta un token: es aritmética.

    Por eso Lean es uno de los dos validadores de coste cero que la Fase 6 corre sobre los
    capítulos invalidados, y por eso puede correr en tres sitios sin que nadie mire el
    presupuesto de contexto.

    **Sin `proyecto`, trabaja sobre una copia temporal de `formal/lean`**, con su `.lake`
    ya compilado: el generador escribe `Generado.lean`, y hacerlo sobre el del repositorio
    pisaría el caso de ejemplo versionado en cada capítulo y haría chocar dos novelas que
    verificaran a la vez. La copia solo recompila `Generado` y el ejecutable.
    """
    if proyecto is None:
        with tempfile.TemporaryDirectory(prefix="storymaker-lean-") as carpeta:
            copia = Path(carpeta) / "lean"
            if (PROYECTO_POR_DEFECTO / "lakefile.toml").exists():
                shutil.copytree(PROYECTO_POR_DEFECTO, copia)
            return await _ejecutar(novela, copia)
    return await _ejecutar(novela, proyecto)


async def _ejecutar(novela: NovelaLean, proyecto: Path) -> Veredicto:
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
