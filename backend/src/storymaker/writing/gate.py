"""spec: §4.4 · arq: §10, §11a

El gate de Writing: el manuscrito terminado, delante del Autor.

Es el último gate humano antes de publicar, y por eso lleva las tres cosas que solo se
pueden decidir con la novela entera escrita: **la cobertura de personalización**, que es la
red de seguridad de las tres comprobaciones de cobertura; **los avisos de ejecución**
acumulados, con los del último capítulo destacados porque no tuvieron adónde viajar; y el
consumo, que es lo que el Autor mira antes de autorizar la fase que cuesta el juez.

`cobertura_personalizacion` se queda aquí como red de seguridad porque **anclar no es
escribir, y escribir el capítulo N no garantiza que ningún otro se quedara sin su parte**.
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import intake, plan, texto
from storymaker.commons.validation.escaleta import cobertura_personalizacion
from storymaker.commons.validation.modelos import Incidencia
from storymaker.writing import avisos
from storymaker.writing.avisos import AvisoDestacado


@dataclass(frozen=True)
class InformeDeWriting:
    capitulos_aprobados: int
    capitulos_totales: int
    avisos: tuple[tuple[int, str], ...] = ()
    avisos_del_ultimo: tuple[AvisoDestacado, ...] = ()
    incidencias: tuple[Incidencia, ...] = ()

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

    return InformeDeWriting(
        capitulos_aprobados=aprobados,
        capitulos_totales=total,
        avisos=tuple(await avisos.todos_los_avisos(db)),
        avisos_del_ultimo=tuple(await avisos.del_ultimo_capitulo(db)),
        incidencias=tuple(cobertura_personalizacion(obligatorios, usados)),
    )
