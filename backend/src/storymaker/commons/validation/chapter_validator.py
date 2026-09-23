"""spec: §3.6 · arq: §11a, §15

Los validadores deterministas que actúan sobre un capítulo. **Python puro, agnóstico a
quién los llama**: reciben datos y devuelven incidencias tipadas, no escriben en la base,
no llaman a un modelo y no salen a la red. La regla Semgrep `core-domain-puro` lo impone.

Tienen dos consumidores y una sola implementación. En producción los ejecuta el grafo como
nodos; en edición manual, `.claude/` los expone como *skill* y como *hook*, de modo que
cuando una persona edita un capítulo a mano la misma validación comprueba que no ha roto
los guardrails ni la continuidad. Si divergieran, el producto y el editor humano dejarían
de estar de acuerdo sobre qué es válido — y por eso la prueba de contrato más valiosa del
proyecto ejecuta el mismo capítulo por ambos caminos y exige el mismo veredicto.

Ninguno de estos es una herramienta que un agente pueda decidir llamar. Todos corren
siempre, y lo que el editor recibe es el informe ya producido.
"""

from __future__ import annotations

import re

from storymaker.commons.validation.modelos import (
    CapituloEnRevision,
    Incidencia,
    Severidad,
)
from storymaker.commons.validation.puras import es_anacronico, normalizar


def nombres_exactos(capitulo: CapituloEnRevision) -> list[Incidencia]:
    """El homenajeado y los personajes, escritos exactamente como en el canon.

    Es el validador más humilde del sistema y el que más importa para el producto: la
    novela es un regalo, y un nombre mal escrito la estropea entera por muy buena que sea
    la prosa.
    """
    incidencias = []
    normalizado = normalizar(capitulo.texto)
    for nombre in capitulo.nombres_canonicos:
        if nombre in capitulo.texto:
            continue
        if normalizar(nombre) in normalizado:
            incidencias.append(
                Incidencia(
                    validador="nombres_exactos",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje=(
                        f"El nombre «{nombre}» aparece con otra grafia. Se escribe "
                        f"exactamente asi, como en el canon."
                    ),
                    propuesta=nombre,
                )
            )
    return incidencias


def longitud_capitulo(capitulo: CapituloEnRevision) -> list[Incidencia]:
    """Palabras dentro del rango del brief.

    El recuento lo calcula la capa de persistencia al escribir la fila, no lo declara quien
    redacta: si lo declarase el escritor, este validador estaría comprobando la aritmética
    del modelo en lugar de la longitud del texto.
    """
    minimo, maximo = capitulo.rango_palabras
    if capitulo.palabras < minimo:
        return [
            Incidencia(
                validador="longitud_capitulo",
                severidad=Severidad.BLOQUEANTE,
                mensaje=f"El capitulo tiene {capitulo.palabras} palabras y el minimo es {minimo}.",
            )
        ]
    if capitulo.palabras > maximo:
        return [
            Incidencia(
                validador="longitud_capitulo",
                severidad=Severidad.BLOQUEANTE,
                mensaje=f"El capitulo tiene {capitulo.palabras} palabras y el maximo es {maximo}.",
            )
        ]
    return []


def anacronismo_fechado(capitulo: CapituloEnRevision) -> list[Incidencia]:
    """Ningún objeto, término o concepto posterior a la fecha narrativa de la escena.

    Existe solo porque el dominio es histórico, y es uno de los dos que llevan el sistema
    por encima del mínimo exigido. Compara contra `fecha_inicio`, que es un dato del corpus:
    no juzga verosimilitud, comprueba aritmética.
    """
    incidencias = []
    normalizado = normalizar(capitulo.texto)
    for entidad in capitulo.entidades_fechadas:
        if normalizar(entidad.nombre) not in normalizado:
            continue
        if es_anacronico(entidad.fecha_inicio, capitulo.fecha_narrativa):
            incidencias.append(
                Incidencia(
                    validador="anacronismo_fechado",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje=(
                        f"«{entidad.nombre}» aparece en {capitulo.fecha_narrativa} y no existe "
                        f"hasta {entidad.fecha_inicio}."
                    ),
                    ubicacion=entidad.nombre,
                )
            )
    return incidencias


def anclaje_valido(capitulo: CapituloEnRevision) -> list[Incidencia]:
    """Todo anclaje apunta a un hecho del corpus sellado o a una Licencia declarada.

    Es lo que obliga a que un detalle inventado por el arquitecto sea **una fila del
    corpus** y no prosa suelta: un dato que viviera solo en su cabeza tumbaría este
    validador en cuanto el escritor lo usara.
    """
    incidencias = []
    for anclaje in capitulo.anclajes:
        if anclaje.hecho_id is None:
            continue
        if anclaje.hecho_id in capitulo.hechos_sellados:
            continue
        if anclaje.hecho_id in capitulo.licencias_declaradas:
            continue
        incidencias.append(
            Incidencia(
                validador="anclaje_valido",
                severidad=Severidad.BLOQUEANTE,
                mensaje=(
                    f"La escena {anclaje.escena_id} ancla al hecho {anclaje.hecho_id}, que no "
                    f"esta en el corpus sellado ni declarado como Licencia."
                ),
                ubicacion=f"escena {anclaje.escena_id}",
            )
        )
    return incidencias


def cobertura_capitulo(capitulo: CapituloEnRevision) -> list[Incidencia]:
    """Lo que la escaleta encomendó a este capítulo aparece en él.

    Corre sobre la salida del extractor, no sobre el texto: quien dice qué elementos se
    usaron es un agente independiente, porque si lo declarase el escritor la cobertura se
    mediría sobre el testimonio de quien tiene interés en decir que lo cubrió todo.

    Convierte un fallo de novela en un reintento de capítulo, que es la segunda de las tres
    comprobaciones de cobertura y la del medio en coste.
    """
    faltan = [
        dato
        for dato in capitulo.personalizacion_encomendada
        if dato not in capitulo.personalizacion_usada
    ]
    if not faltan:
        return []
    return [
        Incidencia(
            validador="cobertura_capitulo",
            severidad=Severidad.BLOQUEANTE,
            mensaje=(
                f"La escaleta encomendo a este capitulo {len(faltan)} elemento(s) de "
                f"personalizacion que no aparecen: {faltan}."
            ),
        )
    ]


#: Los validadores deterministas que actúan sobre el capítulo, en orden de coste creciente.
DE_CAPITULO = (longitud_capitulo, nombres_exactos, anacronismo_fechado, anclaje_valido)


def validar_capitulo(capitulo: CapituloEnRevision) -> list[Incidencia]:
    """La pasada determinista completa, de coste cero: solo texto contra filas ya escritas."""
    incidencias: list[Incidencia] = []
    for validador in DE_CAPITULO:
        incidencias.extend(validador(capitulo))
    return incidencias


def cuenta_palabras(texto: str) -> int:
    """El recuento canónico. Vive aquí para que el hook y el grafo cuenten igual."""
    return len(re.findall(r"\b[\w'-]+\b", texto, re.UNICODE))
