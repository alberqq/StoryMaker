"""spec: §3.6 · arq: §3, §15

El ejecutable que la skill y el hook de `.claude/` invocan. No tiene logica propia: lee el
fichero, llama al Core Domain e imprime el informe. Toda la decision vive en
`entrada_manual`, que es el mismo codigo que ejecuta el grafo.
"""

from __future__ import annotations

import sys
from pathlib import Path

from storymaker.commons.validation.entrada_manual import revisar_fichero


def main(argumentos: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argumentos is None else argumentos
    if not argv:
        print("uso: python -m storymaker.commons.validation.cli_hook <capitulo.md>")
        return 2

    ruta = Path(argv[0])
    if not ruta.exists():
        print(f"No existe el fichero {ruta}")
        return 2

    informe = revisar_fichero(ruta)
    print(informe.como_texto())
    # El hook bloquea con codigo 2, que es lo que Claude Code lee como "no sigas".
    return 2 if informe.bloquea else 0


if __name__ == "__main__":
    raise SystemExit(main())
