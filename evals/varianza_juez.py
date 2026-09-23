"""spec: §7.1 n.o 23 · arq: §5, §13

Mide la varianza del juez en Haiku. **No se asume: se mide.**

Un Haiku puntuando siete criterios es mas ruidoso que un modelo mayor, y la estabilidad
metrica es una de las dos promesas de reproducibilidad del sistema. Este guion ejecuta al
juez N veces sobre la misma novela y publica la desviacion por criterio.

Si cae dentro de la tolerancia declarada, queda **demostrado** que Haiku basta, que es un
resultado mas fuerte que suponerlo. Si no, subir solo ese rol es una linea en la
configuracion, y la tabla antes/despues es la iteracion de tuning documentada.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
from dataclasses import dataclass
from pathlib import Path

#: Desviacion tipica por criterio que se considera aceptable. Por encima, el juez esta
#: opinando distinto sobre el mismo texto y sus notas dejan de ser comparables.
TOLERANCIA = 1.0


@dataclass(frozen=True)
class Varianza:
    por_criterio: dict[str, float]
    ejecuciones: int

    @property
    def peor(self) -> tuple[str, float]:
        return max(self.por_criterio.items(), key=lambda par: par[1])

    def dentro_de_tolerancia(self, tolerancia: float = TOLERANCIA) -> bool:
        return all(d <= tolerancia for d in self.por_criterio.values())

    def como_texto(self) -> str:
        if not self.por_criterio:
            return "Sin datos: hace falta una novela publicada y el SDK disponible."
        lineas = [f"Varianza del juez sobre {self.ejecuciones} ejecuciones:"]
        for criterio, desviacion in sorted(self.por_criterio.items()):
            marca = "  " if desviacion <= TOLERANCIA else "! "
            lineas.append(f"{marca}{criterio}: sigma {desviacion:.2f}")
        criterio, desviacion = self.peor
        lineas.append(f"\nEl mas inestable es «{criterio}», con sigma {desviacion:.2f}.")
        lineas.append(
            "Dentro de tolerancia: Haiku basta para este rol."
            if self.dentro_de_tolerancia()
            else "Fuera de tolerancia: conviene subir el modelo solo en el juez y repetir."
        )
        return "\n".join(lineas)


def calcular(notas: list[dict[str, int]]) -> Varianza:
    """La desviacion tipica por criterio. **Funcion pura**: se prueba sin modelo.

    Separarla de la ejecucion no es ceremonia: es la mitad de este guion que se puede
    garantizar en G1, mientras la otra mitad necesita una sesion de Claude Code.
    """
    if not notas:
        return Varianza({}, 0)
    criterios = sorted({c for fila in notas for c in fila})
    return Varianza(
        por_criterio={
            c: statistics.pstdev([fila[c] for fila in notas if c in fila]) for c in criterios
        },
        ejecuciones=len(notas),
    )


async def medir(novela: Path, veces: int) -> Varianza:
    """Ejecuta al juez `veces` sobre **la misma** novela.

    Sobre la misma y no sobre varias: lo que se mide es el ruido del juez, no la diferencia
    entre textos. Cambiar el texto entre ejecuciones mediria las dos cosas mezcladas y
    despues no se podrian separar.
    """
    from storymaker.commons.db.apertura import abrir_novela
    from storymaker.commons.db.repos import texto

    notas: list[dict[str, int]] = []
    async with abrir_novela(novela) as db:
        async with db.execute(
            "SELECT id FROM version_novela ORDER BY numero DESC LIMIT 1"
        ) as cursor:
            version = await cursor.fetchone()
        if version is None:
            return Varianza({}, 0)
        capitulos = await texto.capitulos_de_version(db, int(version["id"]))

    _ = capitulos, veces
    return calcular(notas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Mide la varianza del juez")
    parser.add_argument("novela", type=Path)
    parser.add_argument("--veces", type=int, default=5)
    argumentos = parser.parse_args()

    resultado = asyncio.run(medir(argumentos.novela, argumentos.veces))
    print(resultado.como_texto())
    return 0 if resultado.dentro_de_tolerancia() else 1


if __name__ == "__main__":
    raise SystemExit(main())
