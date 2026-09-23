"""spec: §7.1 · arq: §11e

`matrices_de_trazabilidad`: comprueba las matrices que afirman que cada decisión de la
arquitectura tiene ítem de plan y cada ítem de plan tiene decisión detrás.

Existe porque esas matrices se escriben a mano y afirman en verde. Mientras nadie las
mire, el modo normal de que se corrompan no es que alguien mienta: es que alguien edite un
plan, renumere un ítem o borre una fila, y la matriz siga diciendo lo de ayer.

**Qué bloquea y qué informa**, con el criterio de `verification.md`: bloquea lo que sostiene
una puerta, informa lo que describe la forma del repositorio.

- Bloquean los defectos del propio documento, que son baratos de arreglar y hacen mentir a
  cualquier lectura posterior: una fila mal formada, un identificador repetido, un estado
  fuera del enumerado, un ítem citado que no existe en ningún plan, un huérfano sin
  resolución, y que el inventario **encoja**. Lo último es la regla que impide cerrar
  huecos borrando la exigencia.
- Informa el recuento de filas en `GAP`, que durante el desarrollo es un estado legítimo:
  una decisión recién fijada puede pasar un rato sin ítem que la realice.

Una fila mal formada bloquea por experiencia propia: un parche dejó tres filas de la matriz
de la raíz sin el separador entre estado y nota, y el `grep` con el que se comprobaba las
seguía contando. Una comprobación mecánica que miente es peor que no tener ninguna.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]

#: Identificadores de ítem declarados por cada plan, por prefijo de cita.
PLANES = {
    "BE": RAIZ / "specs" / "backend" / "plan.md",
    "FE": RAIZ / "specs" / "frontend" / "plan.md",
}

#: Cada matriz con el suelo de su inventario. El suelo no se baja **nunca**: si un requisito
#: desaparece de la arquitectura, su fila se queda con nota en lugar de dejar hueco a otro.
MATRICES = {
    "raíz": (RAIZ / "trace-matrix.md", "ARQ", 136),
    "frontend": (RAIZ / "specs" / "frontend" / "trace-matrix.md", "ARQ", 36),
    "backend": (RAIZ / "specs" / "backend" / "trace-matrix.md", "A", 116),
}

ESTADOS = {"CUBIERTO", "GAP"}
RESOLUCIONES = {"ENLAZADO", "ELIMINADO", "JUSTIFICADO"}

_ITEM = re.compile(r"\b(?:BE:|FE:)?((?:P|IMP)-\d+)\b")


def _items_declarados() -> set[str]:
    """Los identificadores que los planes definen, tal como abren su fila: `**P-01**`."""
    declarados: set[str] = set()
    for plan in PLANES.values():
        texto = plan.read_text(encoding="utf-8")
        declarados |= set(re.findall(r"^\|\s*\*\*((?:P|IMP)-\d+)\*\*", texto, re.M))
    return declarados


def _filas(ruta: Path, prefijo: str) -> list[list[str]]:
    """Las filas de inventario de una matriz, partidas en celdas."""
    filas = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not re.match(rf"^\|\s*{prefijo}-\d+\s*\|", linea):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        filas.append(celdas)
    return filas


def test_las_filas_estan_bien_formadas() -> None:
    """Cinco celdas en las de esquema `ARQ`, cuatro en la del backend. Bloquea."""
    for nombre, (ruta, prefijo, _) in MATRICES.items():
        esperadas = 4 if nombre == "backend" else 5
        for celdas in _filas(ruta, prefijo):
            assert len(celdas) == esperadas, (
                f"[{nombre}] la fila {celdas[0]} tiene {len(celdas)} celdas y no {esperadas}: "
                f"un separador perdido hace que la fila se cuente y no se lea."
            )


def test_los_identificadores_no_se_repiten() -> None:
    """Un identificador repetido parte la trazabilidad en dos sin avisar. Bloquea."""
    for nombre, (ruta, prefijo, _) in MATRICES.items():
        ids = [celdas[0] for celdas in _filas(ruta, prefijo)]
        repetidos = sorted({i for i in ids if ids.count(i) > 1})
        assert not repetidos, f"[{nombre}] identificadores repetidos: {repetidos}"


def test_el_inventario_no_encoge() -> None:
    """El suelo de cada matriz. Bloquea: es lo que impide cerrar huecos borrando filas."""
    for nombre, (ruta, prefijo, suelo) in MATRICES.items():
        filas = _filas(ruta, prefijo)
        assert len(filas) >= suelo, (
            f"[{nombre}] el inventario tiene {len(filas)} filas y su suelo es {suelo}. "
            f"Un requisito que desaparece deja su fila con nota; no se borra."
        )


def test_el_estado_esta_en_el_enumerado() -> None:
    """Solo en las matrices de esquema `ARQ`; la del backend usa prosa. Bloquea."""
    for nombre, (ruta, prefijo, _) in MATRICES.items():
        if nombre == "backend":
            continue
        for celdas in _filas(ruta, prefijo):
            assert celdas[3] in ESTADOS, (
                f"[{nombre}] {celdas[0]} declara el estado «{celdas[3]}», "
                f"que no es {' ni '.join(sorted(ESTADOS))}."
            )


def test_no_se_cita_ningun_item_inexistente() -> None:
    """Un ítem fantasma es una cobertura que nadie va a implementar. Bloquea."""
    declarados = _items_declarados()
    for nombre, (ruta, prefijo, _) in MATRICES.items():
        for celdas in _filas(ruta, prefijo):
            citados = set(_ITEM.findall(celdas[2]))
            fantasmas = sorted(citados - declarados)
            assert not fantasmas, (
                f"[{nombre}] {celdas[0]} cita {fantasmas}, que ningún plan declara."
            )


def test_todo_item_del_plan_tiene_fila_o_resolucion() -> None:
    """El recorrido inverso: trabajo que nadie acordó. Bloquea si no está resuelto."""
    for nombre, (ruta, _prefijo, _) in MATRICES.items():
        if nombre != "frontend":
            continue  # la matriz del frontend es la que cubre un plan entero y solo uno
        texto = ruta.read_text(encoding="utf-8")
        citados = set(_ITEM.findall(texto))
        declarados = set(
            re.findall(r"^\|\s*\*\*(IMP-\d+)\*\*", PLANES["FE"].read_text(encoding="utf-8"), re.M)
        )
        sin_ancla = sorted(declarados - citados, key=lambda s: int(s.split("-")[1]))
        assert not sin_ancla, (
            f"[{nombre}] estos ítems del plan no aparecen en la matriz ni como fila ni como "
            f"huérfano: {sin_ancla}"
        )


def test_los_huerfanos_declaran_resolucion() -> None:
    """Un huérfano sin resolución es una pregunta abierta disfrazada de tabla. Bloquea."""
    for nombre, (ruta, _, _) in MATRICES.items():
        texto = ruta.read_text(encoding="utf-8")
        if "Huérfanos del plan" not in texto:
            continue
        bloque = texto.split("Huérfanos del plan")[1].split("\n## ")[0]
        for linea in bloque.splitlines():
            if not re.match(r"^\|\s*(?:BE:|FE:)?(?:P|IMP)-\d+\s*\|", linea):
                continue
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            assert any(r in celdas[-1] for r in RESOLUCIONES), (
                f"[{nombre}] el huérfano {celdas[0]} no declara "
                f"{' / '.join(sorted(RESOLUCIONES))}."
            )


def test_informe_de_huecos() -> None:
    """Informa, no bloquea: un requisito recién fijado puede pasar un rato sin ítem."""
    for nombre, (ruta, prefijo, _) in MATRICES.items():
        if nombre == "backend":
            continue
        huecos = [c[0] for c in _filas(ruta, prefijo) if c[3] == "GAP"]
        print(f"\n[matrices] {nombre}: {len(huecos)} en GAP")
        for identificador in huecos:
            print(f"  - {identificador}")
