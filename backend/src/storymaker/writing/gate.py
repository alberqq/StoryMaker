"""spec: §4.4 · arq: §10, §11a

El gate de Writing: el manuscrito terminado, delante del Autor.

Es el último gate humano antes de publicar, y por eso lleva las tres cosas que solo se
pueden decidir con la novela entera escrita: **la cobertura de personalización**, que es la
red de seguridad de las tres comprobaciones de cobertura; **los avisos de ejecución**
acumulados, con los del último capítulo destacados porque no tuvieron adónde viajar; y el
consumo, que es lo que el Autor mira antes de autorizar la fase que cuesta el juez.

`cobertura_personalizacion` se queda aquí como red de seguridad porque **anclar no es
escribir, y escribir el capítulo N no garantiza que ningún otro se quedara sin su parte**.
Corre cada vez que la novela llega al gate, también en batch, y deja incidencia y *score*.

**El gate es también adonde vuelve un rechazo.** Si el juez no pasa el umbral o la
publicación rechaza la versión —Lean sobre la cronología completa, `render_visual` en el
navegador—, la novela llega aquí con incidencias que citan capítulos. Rehacer reescribe
esos capítulos, y cada escritor recibe en su encargo el motivo que cita el suyo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import arnes, intake, plan, texto
from storymaker.commons.obs import scores
from storymaker.commons.obs.trazas import Observador
from storymaker.commons.validation.escaleta import cobertura_personalizacion
from storymaker.commons.validation.modelos import Incidencia
from storymaker.writing import avisos
from storymaker.writing.avisos import AvisoDestacado

RECHAZOS_DE_PUBLICACION = ("cronologia_publicacion", "render_visual")

_CITA = re.compile(r"cap(\d+)")


@dataclass(frozen=True)
class InformeDeWriting:
    capitulos_aprobados: int
    capitulos_totales: int
    avisos: tuple[tuple[int, str], ...] = ()
    avisos_del_ultimo: tuple[AvisoDestacado, ...] = ()
    incidencias: tuple[Incidencia, ...] = ()
    #: Lo que el juez listó en su último juicio. Aviso: si está aquí es porque la nota no
    #: pasó el umbral y la novela volvió al gate, o porque el Autor rehízo tras leerla.
    contradicciones: tuple[str, ...] = ()
    #: Por qué la publicación rechazó la última candidata, si lo hizo: `(validador, mensaje)`.
    rechazos: tuple[tuple[str, str], ...] = ()

    @property
    def completo(self) -> bool:
        return self.capitulos_aprobados == self.capitulos_totales

    @property
    def puede_publicar(self) -> bool:
        return self.completo and not any(i.bloquea for i in self.incidencias)

    def como_texto(self) -> str:
        lineas = [
            f"Manuscrito: {self.capitulos_aprobados} de {self.capitulos_totales} capitulos "
            f"aprobados."
        ]
        if not self.completo:
            lineas.append(
                "Faltan capitulos por aprobar: la novela no esta lista para el juez."
            )

        if self.incidencias:
            lineas.append("\nValidadores del gate:")
            for incidencia in self.incidencias:
                lineas.append(f"  [BLOQUEA] {incidencia.validador}: {incidencia.mensaje}")

        if self.avisos_del_ultimo:
            lineas.append(
                "\nAvisos del ultimo capitulo, que no tienen capitulo siguiente al que viajar."
                " Aqui es donde cierra el arco del homenajeado, asi que conviene mirarlos:"
            )
            for aviso in self.avisos_del_ultimo:
                lineas.append(f"  ! {aviso.validador}: {aviso.mensaje}")

        otros = [(n, m) for n, m in self.avisos if not any(
            a.mensaje == m for a in self.avisos_del_ultimo
        )]
        if otros:
            lineas.append(f"\n{len(otros)} aviso(s) de ejecucion en capitulos anteriores:")
            for numero, mensaje in otros:
                lineas.append(f"  - capitulo {numero}: {mensaje}")

        if self.rechazos:
            lineas.append(
                f"\nLa publicacion rechazo la version candidata ({len(self.rechazos)} motivo(s))."
                " Si rehaces, se reescriben los capitulos que citan:"
            )
            lineas += [f"  [BLOQUEA] {v}: {m}" for v, m in self.rechazos]

        if self.contradicciones:
            lineas.append(f"\nEl juez encontro {len(self.contradicciones)} contradiccion(es):")
            lineas += [f"  - {c}" for c in self.contradicciones]

        if self.puede_publicar:
            lineas.append("\nEl manuscrito esta completo y la cobertura en verde.")
        return "\n".join(lineas)


async def construir(db: aiosqlite.Connection) -> InformeDeWriting:
    total = await plan.total_de_capitulos(db)
    aprobados = 0
    for numero in range(1, total + 1):
        capitulo = await plan.capitulo_por_numero(db, numero)
        if capitulo is not None and await texto.capitulo_aprobado(db, int(capitulo["id"])):
            aprobados += 1

    obligatorios = tuple(int(d["id"]) for d in await intake.obligatorios(db))
    sin_usar = {int(d["id"]) for d in await intake.obligatorios_sin_usar(db)}
    usados = frozenset(d for d in obligatorios if d not in sin_usar)
    rechazos = [
        (validador, mensaje)
        for validador in RECHAZOS_DE_PUBLICACION
        for mensaje in await arnes.incidencias_sin_capitulo(db, validador)
    ]

    return InformeDeWriting(
        capitulos_aprobados=aprobados,
        capitulos_totales=total,
        avisos=tuple(await avisos.todos_los_avisos(db)),
        avisos_del_ultimo=tuple(await avisos.del_ultimo_capitulo(db)),
        incidencias=tuple(cobertura_personalizacion(obligatorios, usados)),
        contradicciones=tuple(await arnes.incidencias_sin_capitulo(db, "juez_contradiccion")),
        rechazos=tuple(rechazos),
    )


async def revisar(db: aiosqlite.Connection, observador: Observador) -> InformeDeWriting:
    """Construye el informe y deja la cobertura de personalización como incidencia y *score*.

    Cada llegada al gate sustituye las incidencias de la anterior: lo que ya se cubrió al
    rehacer no debe seguir bloqueando en el informe.
    """
    informe = await construir(db)
    await arnes.retirar_incidencias_sin_capitulo(db, "cobertura_personalizacion")
    for incidencia in informe.incidencias:
        await arnes.registrar_incidencia(
            db,
            validador=incidencia.validador,
            severidad=str(incidencia.severidad),
            mensaje=incidencia.mensaje,
            ubicacion=incidencia.ubicacion,
            propuesta=incidencia.propuesta,
        )
    await scores.registrar_veredicto(
        db,
        observador,
        validador="cobertura_personalizacion",
        incidencias=list(informe.incidencias),
        objeto_tipo="novela",
        objeto_id=1,
    )
    return informe


async def _citadas(db: aiosqlite.Connection) -> list[tuple[str, set[int]]]:
    """Las incidencias de la novela que devuelven capítulos, con los capítulos que citan."""
    return [
        (mensaje, {int(n) for n in _CITA.findall(ubicacion)})
        for mensaje, ubicacion in await arnes.incidencias_que_devuelven_capitulos(db)
    ]


async def capitulos_a_rehacer(db: aiosqlite.Connection, n_capitulos: int) -> list[int]:
    """Qué capítulos reescribe «rehacer» en este gate: los que citan las incidencias.

    Las contradicciones del juez y los rechazos de la publicación nombran capítulos; se
    rehacen esos, en orden. Si ninguna cita ninguno —el Autor rehace por su cuenta, con su
    comentario—, se rehace el último, que es donde cierra el arco del homenajeado.
    """
    citados = {c for _, capitulos in await _citadas(db) for c in capitulos}
    validos = sorted(c for c in citados if 1 <= c <= n_capitulos)
    return validos or [n_capitulos]


async def motivos_para(db: aiosqlite.Connection, numero: int) -> list[str]:
    """Lo que las incidencias de la novela le reprochan al capítulo `numero`.

    Viaja al encargo del escritor cuando se rehace ese capítulo desde este gate: es el
    camino por el que un rechazo de la publicación llega a quien puede corregirlo.
    """
    return [mensaje for mensaje, capitulos in await _citadas(db) if numero in capitulos]
