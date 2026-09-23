"""spec: §7.1 nº 21 · arq: §11e

`inventario_del_plan`: coteja lo que el plan nombra con lo que hay en el árbol, **en las
dos direcciones**, e **informa en dos cubos**.

Las dos direcciones detectan cosas distintas. «Declarado y ausente» es un ítem del plan que
todavía no existe: durante el desarrollo es el estado normal —la mayoría de los ítems están
por escribir— y se mira al cerrar cada hito. «Presente y no declarado» es código que nadie
especificó, y esa es la deriva que contradice el método de este proyecto, así que se mira
siempre.

No bloquea. Convertirlo en puerta dejaría G1 en rojo durante meses por el estado normal del
plan, que es justo lo que §11e dice que no hay que hacer.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
PLANES = sorted((RAIZ / "specs").glob("*/plan.md"))
FUENTE = RAIZ / "backend" / "src" / "storymaker"

#: Rutas dentro de una celda de la columna «Ficheros y símbolos»: algo con barra o con
#: extensión conocida, entre acentos graves.
_RUTA = re.compile(r"`([^`]+)`")
_PARECE_RUTA = re.compile(r"[/\\]|\.(py|sql|toml|yaml|yml|lean|tla|cfg|json|lock|md)\b")


def _expandir_llaves(ruta: str) -> list[str]:
    """`commons/validation/{chapter_validator,policy_checker}.py` son dos ficheros.

    El plan usa esa forma para nombrar un par que se lee junto, y tomarla literalmente haria
    que el inventario informara de dos derivas que no existen.
    """
    apertura = ruta.find("{")
    cierre = ruta.find("}", apertura)
    if apertura == -1 or cierre == -1:
        return [ruta]
    antes, dentro, despues = ruta[:apertura], ruta[apertura + 1 : cierre], ruta[cierre + 1 :]
    return [
        pieza
        for opcion in dentro.split(",")
        for pieza in _expandir_llaves(antes + opcion.strip() + despues)
    ]


def _rutas_declaradas() -> set[str]:
    declaradas: set[str] = set()
    for plan in PLANES:
        for linea in plan.read_text(encoding="utf-8").splitlines():
            if not linea.startswith("| **P-"):
                continue
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if len(celdas) < 3:
                continue
            for trozo in _RUTA.findall(celdas[2]):
                candidato = trozo.split("::")[0].strip()
                if _PARECE_RUTA.search(candidato):
                    declaradas.update(_expandir_llaves(candidato))
    return declaradas


def _modulos_en_el_arbol() -> set[str]:
    return {
        str(p.relative_to(RAIZ / "backend" / "src")).replace("\\", "/")
        for p in FUENTE.rglob("*.py")
        if p.name != "__init__.py"
    }


def _esta_declarado(modulo: str, declaradas: set[str]) -> bool:
    """Una ruta del plan cubre un módulo si lo nombra o nombra su carpeta con comodín."""
    sin_prefijo = modulo.removeprefix("storymaker/")
    for declarada in declaradas:
        normalizada = declarada.replace("\\", "/").removeprefix("backend/src/")
        if normalizada.endswith(("/", "/*", "/**")):
            if sin_prefijo.startswith(normalizada.rstrip("*/")):
                return True
        if "*" in normalizada:
            patron = normalizada.replace("**", "*").replace("*", "[^/]*")
            if re.fullmatch(patron, sin_prefijo) or re.fullmatch(patron, modulo):
                return True
        if normalizada in (modulo, sin_prefijo):
            return True
    return False


def cubos() -> tuple[list[str], list[str]]:
    """Devuelve («declarado y ausente», «presente y no declarado»)."""
    declaradas = _rutas_declaradas()
    ausentes = sorted(
        ruta
        for ruta in declaradas
        if ruta.endswith((".py", ".sql"))
        and "*" not in ruta
        and not (RAIZ / "backend" / "src" / ruta.removeprefix("backend/src/")).exists()
        and not (RAIZ / ruta).exists()
        and not (RAIZ / "backend" / "src" / "storymaker" / ruta).exists()
        # Las rutas de prueba se escriben en el plan relativas a `backend/` —`tests/unit/…`—,
        # y sin este intento el cubo «declarado y ausente» se llenaba de ficheros que sí
        # existen. Un informe con falsos ausentes es el camino más corto a que nadie lo mire.
        and not (RAIZ / "backend" / ruta).exists()
    )
    no_declarados = sorted(m for m in _modulos_en_el_arbol() if not _esta_declarado(m, declaradas))
    return ausentes, no_declarados


def test_el_plan_se_puede_leer() -> None:
    """Un parser roto informaria de cero derivas y pareceria una buena noticia."""
    assert PLANES, "no se encontro ningun plan de implementacion"
    assert len(_rutas_declaradas()) > 40, "el plan declara menos rutas de las que deberia"


def test_informe_en_dos_cubos() -> None:
    """Informa: imprime los dos cubos y no detiene nada.

    El cubo que importa durante el desarrollo es el segundo. El primero esta lleno por
    definicion mientras quedan hitos por cerrar.
    """
    ausentes, no_declarados = cubos()
    print(f"\n[inventario] declarado y ausente: {len(ausentes)}")
    for ruta in ausentes[:20]:
        print(f"  - {ruta}")
    print(f"[inventario] presente y no declarado: {len(no_declarados)}")
    for ruta in no_declarados[:20]:
        print(f"  + {ruta}")
    assert isinstance(ausentes, list) and isinstance(no_declarados, list)
