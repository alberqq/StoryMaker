"""spec: §6 · arq: §16.4

La CLI de Typer: **el punto de entrada del Autor y de las ejecuciones de evaluación**.

Los siete comandos llaman a la misma función de invocación que la API. Un tercer punto de
entrada —una cola de trabajos con su worker— añadiría un segundo lugar donde el estado puede
vivir, que es justo lo que §7 evita al meter checkpoint y dominio en la misma transacción.

`ramificar` es literalmente copiar el fichero, y `desbloquear` rompe un cerrojo huérfano: es
la operación de mantenimiento que el Autor hará una vez cada muchas, y vive aquí y no en un
reintento automático porque **un cerrojo que se rompe solo deja de ser un cerrojo**.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import typer

from storymaker.cli import salida
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela, crear_novela
from storymaker.commons.errores import ErrorDeStoryMaker
from storymaker.commons.graph import cerrojo
from storymaker.commons.graph.branch import ramificar as copiar_novela
from storymaker.commons.graph.run import Arranque, invocar, reanudar
from storymaker.intake.encargo import leer as leer_encargo

app = typer.Typer(
    help="StoryMaker — arnes multiagente para novelas historicas personalizadas",
    no_args_is_help=True,
)


def _ajustes() -> Settings:
    return Settings()


def _ruta(nombre: str, settings: Settings) -> Path:
    limpio = Path(nombre).name
    if not limpio.endswith(".db"):
        limpio = f"{limpio}.db"
    return settings.directorio_proyectos / limpio


def _ejecutar(corrutina: Any) -> Any:
    """Corre la corrutina y traduce los errores del arnés a salida legible.

    La CLI no enseña trazas: un `NovelaOcupada` es una frase que dice qué hacer, no un
    volcado de pila. Las trazas se miran en la traza.
    """
    try:
        return asyncio.run(corrutina)
    except ErrorDeStoryMaker as error:
        salida.error(str(error))
        raise typer.Exit(code=1) from error


@app.command()
def nueva(
    brief: Path = typer.Argument(..., help="fichero YAML o JSON con el encargo"),
    nombre: str = typer.Option("", help="nombre de la novela; por defecto, el del homenajeado"),
    batch: bool = typer.Option(False, "--batch", help="sin gates: no se detiene a preguntar"),
) -> None:
    """Crea el fichero de la novela en `proyectos/` y arranca la invocación.

    El encargo se **lee aquí** y entra en el grafo como premisa. Antes no se abría, y el
    entrevistador arrancaba con la premisa vacía: la novela salía adelante preguntándolo
    todo, y el fichero que el comprador había rellenado no lo miraba nadie.
    """
    settings = _ajustes()
    encargo = leer_encargo(brief)
    ruta = _ruta(nombre or encargo.nombre, settings)
    if ruta.exists():
        salida.error(f"Ya existe una novela en {ruta}. Elige otro nombre.")
        raise typer.Exit(code=1)

    if batch:
        settings = settings.en_modo_batch()

    async def correr() -> None:
        await crear_novela(ruta)
        salida.aviso(f"Novela creada en {ruta}")
        salida.aviso(
            f"{encargo.n_capitulos} capitulos"
            + (" · modo batch, sin gates" if batch else " · con gates")
        )
        resultado = await invocar(
            ruta,
            Arranque(
                n_capitulos=encargo.n_capitulos,
                premisa=encargo.premisa,
                texto_pegado=encargo.texto_pegado,
            ),
            settings=settings,
        )
        salida.resultado(resultado)

    _ejecutar(correr())


@app.command()
def continuar(nombre: str) -> None:
    """Reanuda desde el último checkpoint, **sea tras un fallo o tras un gate**.

    Es el mismo camino de código en los dos casos, que es exactamente lo que §10 promete.
    """
    settings = _ajustes()
    resultado = _ejecutar(reanudar(_ruta(nombre, settings), settings=settings))
    salida.resultado(resultado)


@app.command()
def estado(nombre: str) -> None:
    """Fase, gate abierto, capítulos aprobados y consumo acumulado."""
    settings = _ajustes()
    ruta = _ruta(nombre, settings)

    async def leer() -> dict[str, Any]:
        from storymaker.api.novelas import ficha

        datos = await ficha(ruta)
        async with abrir_novela(ruta) as db:
            async with db.execute(
                "SELECT COUNT(*) AS n FROM capitulo_version WHERE estado = 'aprobado'"
            ) as cursor:
                fila = await cursor.fetchone()
            aprobados = int(fila["n"]) if fila is not None else 0
            async with db.execute(
                "SELECT COALESCE(SUM(coste_usd), 0) AS c, COALESCE(SUM(tokens_in), 0) AS i,"
                " COALESCE(SUM(tokens_out), 0) AS o FROM fase_run"
            ) as cursor:
                consumo = await cursor.fetchone()
            gasto = float(consumo["c"]) if consumo is not None else 0.0
            entrada = int(consumo["i"]) if consumo is not None else 0
            salida_tokens = int(consumo["o"]) if consumo is not None else 0
        return {
            "titulo": datos.titulo,
            "fase": datos.fase,
            "gate": datos.gate_abierto,
            "ocupada": datos.ocupada,
            "aprobados": aprobados,
            "coste": gasto,
            "tokens_in": entrada,
            "tokens_out": salida_tokens,
        }

    salida.estado(_ejecutar(leer()))


@app.command()
def ramificar(nombre: str, destino: str) -> None:
    """**Copia el fichero** y escribe la fila de `procedencia`."""
    settings = _ajustes()
    ruta = _ejecutar(
        copiar_novela(_ruta(nombre, settings), _ruta(destino, settings))
    )
    salida.aviso(f"Rama creada en {ruta}. Una novela es un fichero: descargarla es copiarlo.")


@app.command()
def cambiar(nombre: str, peticion: str) -> None:
    """Entra en la Fase 6 por la puerta del Autor. **No cambia nada hasta el gate.**"""
    settings = _ajustes()
    ruta = _ruta(nombre, settings)

    async def proponer() -> list[Any]:
        from storymaker.commons.embeddings.modelo import FastEmbedVectorizador
        from storymaker.regeneration.cambio import buscar_candidatos

        async with abrir_novela(ruta) as db:
            return await buscar_candidatos(db, FastEmbedVectorizador(), peticion)

    salida.candidatos(_ejecutar(proponer()))


@app.command()
def desbloquear(nombre: str) -> None:
    """Rompe un cerrojo huérfano dejado por un proceso muerto."""
    settings = _ajustes()
    ruta = _ruta(nombre, settings)
    if cerrojo.romper(ruta):
        salida.aviso(f"Cerrojo roto. Comprueba que ningun proceso siga escribiendo en {nombre}.")
    else:
        salida.aviso("No habia ningun cerrojo que romper.")


@app.command()
def evaluar(
    briefs: Path = typer.Option(Path("evals/briefs"), help="directorio con los briefs"),
) -> None:
    """Corre los cinco briefs en modo batch, con `gates_enabled = false`.

    Es imprescindible que los gates se puedan apagar: si cada brief pidiera cinco
    aprobaciones, la tabla de resultados no se terminaría nunca.
    """
    settings = _ajustes().en_modo_batch()
    ficheros = sorted(briefs.glob("*.yaml")) + sorted(briefs.glob("*.json"))
    if not ficheros:
        salida.error(f"No hay briefs en {briefs}")
        raise typer.Exit(code=1)

    salida.aviso(f"{len(ficheros)} brief(s) en modo batch, con los gates desactivados.")

    async def correr() -> None:
        for fichero in ficheros:
            encargo = leer_encargo(fichero)
            ruta = settings.directorio_proyectos / f"eval-{fichero.stem}.db"
            salida.aviso(f"  - {fichero.stem} -> {ruta.name}")
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
            salida.resultado(resultado)

    _ejecutar(correr())
