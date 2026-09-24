"""spec: §7.1 n.o 22 · arq: §13, verif. §4.2

Corre los cinco briefs de evaluacion en modo batch y escribe la tabla de resultados.

Es G2 y no G1: necesita **modelo real**, asi que no puede correr en cada push. Lo que mide
no es si el codigo funciona —eso lo dicen las pruebas de G1— sino **como se comporta el
sistema con un modelo de verdad delante**: cero incidencias criticas en la version
publicada, 5 de 5 briefs que completan, y al menos el 70 % de los capitulos aprobados al
primer intento.

Los gates van desactivados. Es imprescindible y no un lujo: si cada brief pidiera cinco
aprobaciones, la tabla no se terminaria nunca.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResultadoDeBrief:
    """Lo que se mide de cada ejecucion. Sin nada que no se vaya a mirar."""

    brief: str
    completo: bool
    capitulos: int
    al_primer_intento: int
    incidencias_criticas: int
    coste_usd: float
    error: str | None = None

    @property
    def tasa_primer_intento(self) -> float:
        return self.al_primer_intento / self.capitulos if self.capitulos else 0.0


@dataclass(frozen=True)
class Tabla:
    resultados: tuple[ResultadoDeBrief, ...]

    @property
    def completan(self) -> int:
        return sum(1 for r in self.resultados if r.completo)

    @property
    def criticas(self) -> int:
        return sum(r.incidencias_criticas for r in self.resultados)

    @property
    def tasa_media(self) -> float:
        if not self.resultados:
            return 0.0
        return sum(r.tasa_primer_intento for r in self.resultados) / len(self.resultados)

    @property
    def coste(self) -> float:
        return sum(r.coste_usd for r in self.resultados)

    def pasa(self) -> bool:
        """Los tres umbrales de verif. §4.2, juntos."""
        return (
            self.criticas == 0
            and self.completan == len(self.resultados)
            and self.tasa_media >= 0.70
        )

    def como_texto(self) -> str:
        lineas = [
            "| brief | completo | capitulos | 1.er intento | criticas | coste |",
            "|---|---|---|---|---|---|",
        ]
        for r in self.resultados:
            lineas.append(
                f"| {r.brief} | {'si' if r.completo else 'NO'} | {r.capitulos} | "
                f"{r.tasa_primer_intento:.0%} | {r.incidencias_criticas} | {r.coste_usd:.2f} $ |"
            )
        lineas.append("")
        lineas.append(
            f"{self.completan}/{len(self.resultados)} completan · "
            f"{self.criticas} incidencia(s) critica(s) · "
            f"{self.tasa_media:.0%} al primer intento · "
            f"{self.coste:.2f} $ estimados en cliente, no facturacion."
        )
        lineas.append("PASA" if self.pasa() else "NO PASA")
        return "\n".join(lineas)


async def medir(db: Any) -> dict[str, int]:
    """Los tres numeros de verif. §4.2, leidos de la novela ya escrita.

    Se leen de la base y no del estado devuelto a proposito: el estado dice por donde paso
    la invocacion, y lo que mide un eval es **lo que quedo escrito**. Una ejecucion que
    termina limpia y deja cero capitulos aprobados no es un exito, y contandola desde el
    estado lo pareceria.
    """
    async def uno(consulta: str) -> int:
        async with db.execute(consulta) as cursor:
            fila = await cursor.fetchone()
        return int(fila[0]) if fila is not None else 0

    return {
        "capitulos": await uno(
            "SELECT COUNT(*) FROM capitulo_version WHERE estado = 'aprobado'"
        ),
        "al_primer_intento": await uno(
            "SELECT COUNT(*) FROM capitulo_version WHERE estado = 'aprobado' AND intento = 1"
        ),
        "criticas": await uno(
            "SELECT COUNT(*) FROM incidencia WHERE severidad = 'bloqueante'"
        ),
    }


async def correr_uno(brief: Path) -> ResultadoDeBrief:
    """Un brief de principio a fin, en modo batch.

    Devuelve el error dentro del resultado en lugar de propagarlo: que un brief reviente no
    puede impedir que se midan los otros cuatro, y un eval que se detiene en el primer fallo
    no es una tabla, es una anecdota.
    """
    from storymaker.commons.config import Settings
    from storymaker.commons.db.apertura import abrir_novela, crear_novela, ruta_de_novela
    from storymaker.commons.graph.run import Arranque, invocar
    from storymaker.intake.encargo import leer

    settings = Settings().en_modo_batch()
    ruta = ruta_de_novela(f"eval-{brief.stem}", settings.directorio_proyectos)

    try:
        encargo = leer(brief)
        if not ruta.exists():
            await crear_novela(ruta)
        resultado = await invocar(
            ruta,
            Arranque(
                n_capitulos=encargo.n_capitulos,
                premisa=encargo.premisa,
                texto_pegado=encargo.texto_pegado,
            ),
            settings=settings,
        )
        async with abrir_novela(ruta) as db:
            medidas = await medir(db)
        return ResultadoDeBrief(
            brief=brief.stem,
            completo=resultado.error is None,
            capitulos=medidas["capitulos"],
            al_primer_intento=medidas["al_primer_intento"],
            incidencias_criticas=medidas["criticas"],
            coste_usd=resultado.consumo.coste_usd,
            error=resultado.error,
        )
    except Exception as fallo:
        return ResultadoDeBrief(
            brief=brief.stem,
            completo=False,
            capitulos=0,
            al_primer_intento=0,
            incidencias_criticas=0,
            coste_usd=0.0,
            error=str(fallo),
        )


async def correr(directorio: Path) -> Tabla:
    briefs = sorted(directorio.glob("*.yaml")) + sorted(directorio.glob("*.json"))
    return Tabla(tuple([await correr_uno(b) for b in briefs]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Corre los cinco briefs de evaluacion")
    parser.add_argument("--briefs", type=Path, default=Path("evals/briefs"))
    parser.add_argument("--salida", type=Path, default=Path("evals/resultados.json"))
    argumentos = parser.parse_args()

    tabla = asyncio.run(correr(argumentos.briefs))
    argumentos.salida.write_text(
        json.dumps([asdict(r) for r in tabla.resultados], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(tabla.como_texto())
    return 0 if tabla.pasa() else 1


if __name__ == "__main__":
    raise SystemExit(main())
