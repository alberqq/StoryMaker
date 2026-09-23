"""spec: §7.1 · arq: §11e

`requisitos_declarados`: comprueba las tablas de requisitos de las dos specs —§10 en el
backend, §12 en el frontend— contra los planes que dicen realizarlas y contra los apartados
de los que dicen salir.

Es el cuarto miembro de la familia de §11e, y mira lo que los otros tres no miran. El
inventario compara **ítems contra árbol**; las anclas, **módulos contra apartados**; las
matrices, **arquitectura contra ítems**. Esta tabla es el eslabón que faltaba: el contrato
de la spec en su forma comprobable, fila a fila, y lo que aquí se corrompe no se nota en
ninguno de los otros tres.

**Informa y no bloquea, los tres hallazgos.** No es descuido: durante el desarrollo los tres
son estados legítimos. Un requisito recién escrito puede pasar días con un guion en la
columna de ítems mientras el plan alcanza a la spec —es justamente para eso para lo que esa
columna admite el guion—; un apartado recién abierto puede no tener todavía fila que lo
enuncie; y un identificador repetido, aunque sea un defecto claro, aparece casi siempre a
mitad de una renumeración que el Autor está haciendo a mano y que bloquear dejaría a medias.
Lo que sostiene las puertas ya lo bloquean `registro_de_validadores` y
`matrices_de_trazabilidad`; esto describe la forma de los documentos, que es lo que §11e
manda informar.

La salida va por `print`, que `pytest -s` o el informe de CI enseñan. Un hallazgo que nadie
lee es exactamente lo mismo que no tenerlo, así que conviene mirarlo al cerrar cada hito —
que es cuando el plan y la spec han terminado de moverse.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]

#: Cada spec con el prefijo de sus requisitos, su plan y el plan del otro lado, porque una
#: fila puede citar ítems de los dos con el prefijo `BE:` o `FE:`.
SPECS = {
    "backend": (RAIZ / "specs" / "backend" / "spec.md", "REQ-BE"),
    "frontend": (RAIZ / "specs" / "frontend" / "spec.md", "REQ-FE"),
}

PLANES = {
    "BE": RAIZ / "specs" / "backend" / "plan.md",
    "FE": RAIZ / "specs" / "frontend" / "plan.md",
}

#: Los apartados que la tabla tiene que cubrir. §3 y §4 son el contrato de verdad —lo que
#: cada módulo y cada fase hace—, y son los únicos de los que se exige que ninguno se quede
#: sin fila. Los demás apartados aportan requisitos, pero no todos tienen por qué.
APARTADOS_EXIGIDOS = ("3", "4")

_ITEM = re.compile(r"\b(?:BE:|FE:)?((?:P|IMP)-\d+)\b")
_APARTADO = re.compile(r"§(\d+(?:\.\d+)?)")


def _items_declarados() -> set[str]:
    """Los identificadores que los planes definen, tal como abren su fila: `**P-01**`."""
    declarados: set[str] = set()
    for plan in PLANES.values():
        texto = plan.read_text(encoding="utf-8")
        declarados |= set(re.findall(r"^\|\s*\*\*((?:P|IMP)-\d+)\*\*", texto, re.M))
    return declarados


def _filas(ruta: Path, prefijo: str) -> list[list[str]]:
    """Las filas de requisito de una spec, partidas en celdas.

    Se reconocen por cómo abren —`| REQ-BE-07 |`— y no por el apartado en el que están, de
    modo que partir §10 en más subapartados no deja filas fuera del recuento.
    """
    filas = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not re.match(rf"^\|\s*{prefijo}-\d+\s*\|", linea):
            continue
        filas.append([c.strip() for c in linea.strip().strip("|").split("|")])
    return filas


def _subapartados(ruta: Path) -> set[str]:
    """Los apartados de §3 y §4 que la spec abre, con su numeración completa.

    Se recogen tanto los encabezados de segundo nivel —`## 3. …`, cuando el apartado no está
    partido— como los de tercero, porque las dos specs no tienen la misma profundidad: el
    mapa de rutas del frontend es un apartado entero sin subapartados.
    """
    encontrados: set[str] = set()
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        encabezado = re.match(r"^#{2,3}\s+(\d+(?:\.\d+)?)[.\s]", linea)
        if encabezado is None:
            continue
        numero = encabezado.group(1)
        if numero.split(".")[0] in APARTADOS_EXIGIDOS:
            encontrados.add(numero)
    return encontrados


def _apartados_citados(filas: list[list[str]]) -> set[str]:
    """Los apartados que las filas citan, con sus padres.

    Una fila que cita `§3.6` cubre también `§3`: el apartado padre no necesita fila propia
    si alguno de sus hijos la tiene. Sin esto, `## 4. Las seis fases` saldría siempre como
    huérfano por el mero hecho de tener subapartados.
    """
    citados: set[str] = set()
    for celdas in filas:
        for numero in _APARTADO.findall(celdas[2] if len(celdas) > 2 else ""):
            citados.add(numero)
            citados.add(numero.split(".")[0])
    return citados


def test_informe_de_items_fantasma() -> None:
    """Un ítem citado que ningún plan declara. Informa.

    Es la avería más silenciosa de las tres: la fila afirma que alguien va a construir eso,
    y nadie lo va a construir porque el ítem no existe. Aparece al renumerar un plan.
    """
    declarados = _items_declarados()
    for nombre, (ruta, prefijo) in SPECS.items():
        fantasmas: dict[str, list[str]] = {}
        for celdas in _filas(ruta, prefijo):
            citados = set(_ITEM.findall(celdas[3] if len(celdas) > 3 else ""))
            sobran = sorted(citados - declarados)
            if sobran:
                fantasmas[celdas[0]] = sobran
        print(f"\n[requisitos] {nombre}: {len(fantasmas)} filas citan items inexistentes")
        for identificador, sobran in fantasmas.items():
            print(f"  - {identificador} cita {sobran}")


def test_informe_de_apartados_sin_requisito() -> None:
    """Un apartado de §3 o §4 al que ningún requisito apunta. Informa.

    Significa que una parte del contrato está escrita en prosa y no tiene forma comprobable,
    que es precisamente lo que esta tabla existe para evitar.
    """
    for nombre, (ruta, prefijo) in SPECS.items():
        abiertos = _subapartados(ruta)
        citados = _apartados_citados(_filas(ruta, prefijo))
        huerfanos = sorted(abiertos - citados, key=lambda s: [int(p) for p in s.split(".")])
        print(f"\n[requisitos] {nombre}: {len(huerfanos)} apartados sin requisito que apunte")
        for apartado in huerfanos:
            print(f"  - §{apartado}")


def test_informe_de_identificadores_repetidos() -> None:
    """Un `REQ-BE-nn` o `REQ-FE-nn` repetido. Informa.

    Un identificador que aparece dos veces parte la trazabilidad en dos sin avisar: quien
    cite ese número creerá haber cubierto uno de los dos requisitos y no sabrá cuál.
    """
    for nombre, (ruta, prefijo) in SPECS.items():
        ids = [celdas[0] for celdas in _filas(ruta, prefijo)]
        repetidos = sorted({i for i in ids if ids.count(i) > 1})
        print(f"\n[requisitos] {nombre}: {len(ids)} requisitos, {len(repetidos)} repetidos")
        for identificador in repetidos:
            print(f"  - {identificador}")


def test_las_dos_tablas_existen_y_tienen_filas() -> None:
    """Lo único que sí bloquea: que haya tabla.

    No es una comprobación del contenido sino del propio validador. Un cambio de formato que
    dejara el parser sin reconocer ninguna fila haría que los tres informes de arriba
    saliesen en cero, que es exactamente como se leen cuando todo está bien — y esa es la
    forma en que una comprobación mecánica pasa de decir la verdad a mentir sin que nadie
    lo note.
    """
    for nombre, (ruta, prefijo) in SPECS.items():
        filas = _filas(ruta, prefijo)
        assert filas, (
            f"[{nombre}] no se ha reconocido ninguna fila de requisito con el prefijo "
            f"{prefijo}. O la tabla ha desaparecido, o ha cambiado de formato y este "
            f"validador lleva informando de cero desde entonces."
        )
        assert all(len(celdas) == 4 for celdas in filas), (
            f"[{nombre}] hay filas con un numero de celdas distinto de cuatro: "
            f"un separador perdido hace que la fila se cuente y no se lea."
        )
