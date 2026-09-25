"""spec: §6 · arq: §16.4

La CLI de Typer: **el punto de entrada del Autor y de las ejecuciones de evaluación**.

Los ocho comandos llaman a la misma función de invocación. **`decidir` es la única entrada
de una decisión de gate**: Telegram solo avisa (arq. §10), y el Autor decide en su PC. Un
tercer punto de entrada —una cola de trabajos con su worker— añadiría un segundo lugar
donde el estado puede vivir, que es justo lo que §7 evita al meter checkpoint y dominio
en la misma transacción.

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
from storymaker.commons.db.apertura import abrir_novela, crear_novela, ruta_de_novela
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
    return ruta_de_novela(nombre, settings.directorio_proyectos)


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
    investigacion: str = typer.Option(
        "",
        "--investigacion",
        help="estandar (una sesion, tres paginas) o exhaustiva (ocho sesiones dirigidas)",
    ),
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
    if investigacion:
        if investigacion not in ("estandar", "exhaustiva"):
            salida.error("--investigacion admite «estandar» o «exhaustiva».")
            raise typer.Exit(code=1)
        settings = settings.model_copy(update={"investigacion": investigacion})

    async def correr() -> None:
        await crear_novela(ruta)
        salida.aviso(f"Novela creada en {ruta}")
        salida.aviso(
            f"{encargo.n_capitulos} capitulos"
            + (" · modo batch, sin gates" if batch else " · con gates")
            + f" · investigacion {settings.investigacion}"
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
    ruta = _ruta(nombre, settings)

    async def gate_que_espera() -> int | None:
        from storymaker.commons.db.repos import arnes

        async with abrir_novela(ruta) as db:
            pendiente = await arnes.gate_pendiente(db)
        return int(pendiente["id"]) if pendiente is not None else None

    # Reanudar un gate pendiente sin decisión lo aprobaría en silencio: se decide aparte.
    if (gate := _ejecutar(gate_que_espera())) is not None:
        salida.error(f"La novela espera tu decision en el gate #{gate}.")
        salida.aviso(f"Decide con: storymaker decidir {nombre} aprobar|rehacer|editar|abortar")
        raise typer.Exit(code=1)
    resultado = _ejecutar(reanudar(ruta, settings=settings))
    salida.resultado(resultado)


@app.command()
def decidir(
    nombre: str,
    decision: str = typer.Argument(..., help="aprobar, rehacer, editar o abortar"),
    comentario: str = typer.Option("", help="lo que hay que cambiar, para «rehacer»"),
) -> None:
    """Decide el gate que espera y reanuda **en este mismo proceso**.

    La decisión se escribe antes de reanudar, así que si el proceso cae a mitad no se pierde:
    `continuar` retoma por el camino de siempre. Un gate ya decidido no está pendiente, y
    decidir dos veces no reanuda dos veces.
    """
    settings = _ajustes()
    ruta = _ruta(nombre, settings)

    async def escribir() -> tuple[str, str | None]:
        from storymaker.commons.obs.trazas import construir as construir_observador
        from storymaker.gates.decisiones import aplicar

        async with abrir_novela(ruta) as db:
            observador = construir_observador(settings, novela=ruta.stem)
            tomada = await aplicar(db, observador, decision, comentario)
            await db.commit()
            observador.cerrar()
        return tomada.decision.value, tomada.fase

    valor, fase = _ejecutar(escribir())
    if fase == "regeneration":
        # El gate de Regeneración lo abrió la API, no un `interrupt()`: no hay nada que
        # reanudar, y aprobar es entrar en la Fase 6 desde `Idle`.
        from storymaker.commons.graph.run import regenerar

        salida.aviso(f"Decision registrada: {valor}. Entrando en la Regeneracion...")
        salida.resultado(
            _ejecutar(regenerar(ruta, settings=settings, aprobada=valor == "aprobar"))
        )
        return
    salida.aviso(f"Decision registrada: {valor}. Reanudando...")
    resultado = _ejecutar(
        reanudar(ruta, settings=settings, decision=valor, comentario=comentario or None)
    )
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
def reintentar(nombre: str) -> None:
    """Reabre el capítulo que agotó sus reintentos y reanuda desde él.

    Tras un `Fail` de capítulo el grafo ha terminado y `continuar` no tiene nada que retomar.
    Se niega sin tocar nada si la novela no se detuvo así.
    """
    settings = _ajustes()
    ruta = _ruta(nombre, settings)
    from storymaker.commons.graph.run import reintentar as reintentar_capitulo

    salida.aviso("Reabriendo el capitulo que agoto sus reintentos...")
    salida.resultado(_ejecutar(reintentar_capitulo(ruta, settings=settings)))

revision = typer.Typer(help="La revision humana de una novela con la rubrica del juez.")
app.add_typer(revision, name="revision")


@revision.command("hoja")
def revision_hoja(
    nombre: str,
    version: int = typer.Option(0, help="version publicada; por defecto, la ultima"),
    destino: Path = typer.Option(Path(""), help="donde escribir la hoja; por defecto, al lado"),
) -> None:
    """Escribe la hoja en blanco para puntuar una versión publicada."""
    settings = _ajustes()
    ruta = _ruta(nombre, settings)
    from storymaker.publication import revision_humana

    async def ultima() -> int:
        async with abrir_novela(ruta) as db:
            async with db.execute("SELECT COALESCE(MAX(numero), 0) AS n FROM version_novela") as c:
                fila = await c.fetchone()
        return int(fila["n"]) if fila is not None else 0

    numero = version or _ejecutar(ultima())
    if not numero:
        salida.error("La novela no tiene ninguna version publicada que revisar.")
        raise typer.Exit(code=1)
    fichero = destino if str(destino) not in ("", ".") else ruta.with_suffix(
        f".v{numero}.revision.yaml"
    )
    fichero.write_text(revision_humana.hoja(ruta.stem, numero), encoding="utf-8")
    salida.aviso(
        f"Hoja escrita en {fichero}. Lee la novela entera, puntua desde "
        f"{revision_humana.RUBRICA.name} y registrala con `storymaker revision registrar`."
    )


@revision.command("registrar")
def revision_registrar(
    nombre: str,
    hoja: Path = typer.Argument(..., help="la hoja rellena"),
    acta: Path = typer.Option(Path(""), help="donde escribir el acta en Markdown"),
) -> None:
    """Registra la hoja rellena como score y escribe el acta comparada con el juez."""
    settings = _ajustes()
    ruta = _ruta(nombre, settings)
    from storymaker.commons.obs.trazas import construir as construir_observador
    from storymaker.publication import revision_humana

    async def registrar() -> revision_humana.Acta:
        async with abrir_novela(ruta) as db:
            observador = construir_observador(settings, novela=ruta.stem)
            resultado = await revision_humana.registrar_revision(
                db, observador, hoja.read_text(encoding="utf-8")
            )
            await db.commit()
            observador.cerrar()
        return resultado

    comparada = _ejecutar(registrar())
    texto = comparada.como_markdown()
    if str(acta) not in ("", "."):
        acta.write_text(texto, encoding="utf-8")
        salida.aviso(f"Acta escrita en {acta}. Anadela a docs/revision-humana.md §5.")
    else:
        print(texto)


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
            ruta = ruta_de_novela(f"eval-{fichero.stem}", settings.directorio_proyectos)
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
