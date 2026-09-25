"""spec: §3.6 · arq: §11a, §19

Los dos validadores del gate de Plotting, más la red de seguridad del gate de Writing.

**La cobertura se comprueba tres veces, y cada una cuesta menos que la siguiente.**
`cobertura_anclada` verifica aquí que cada elemento obligatorio está anclado a alguna
escena, y convierte un fallo de diez capítulos escritos y pagados en un fallo de escaleta;
`cobertura_capitulo` —que vive con los de capítulo— convierte un fallo de novela en un
reintento; y `cobertura_personalizacion` se queda al cerrar Writing como red de seguridad,
porque anclar no es escribir y escribir el capítulo N no garantiza que ningún otro se
quedara sin su parte.
"""

from __future__ import annotations

from storymaker.commons.config import Defaults
from storymaker.commons.validation.modelos import (
    ArcoEnRevision,
    EscaletaEnRevision,
    Incidencia,
    Severidad,
)


def cobertura_anclada(escaleta: EscaletaEnRevision) -> list[Incidencia]:
    """Cada elemento obligatorio del brief está anclado a ≥1 escena de la escaleta."""
    faltan = [d for d in escaleta.obligatorios if d not in escaleta.obligatorios_anclados]
    if not faltan:
        return []
    return [
        Incidencia(
            validador="cobertura_anclada",
            severidad=Severidad.BLOQUEANTE,
            mensaje=(
                f"{len(faltan)} elemento(s) obligatorio(s) del encargo no estan anclados a "
                f"ninguna escena: {faltan}. Corregir la escaleta cuesta un parrafo; "
                f"descubrirlo con la novela escrita cuesta diez capitulos."
            ),
        )
    ]


def arco_anclado(escaleta: EscaletaEnRevision) -> list[Incidencia]:
    """Todo personaje recurrente tiene arco, y el del homenajeado cierra en el tercio final.

    **Cuenta apariciones, no importancia, y es deliberado.** «Personaje principal» no es
    algo que el modelo de datos sepa responder —`tipo` distingue procedencia, no peso en la
    trama—, pero contar sobre `plan_escena_personaje` sí es computable y dice lo que
    interesa: de todo personaje que vuelve, el arquitecto tiene que haber decidido qué hace
    a lo largo de la obra.

    Lo que evita que esa exigencia se convierta en una puerta atascada es que **el arco
    plano cuenta**. Al tabernero que sale en cuatro escenas no se le pide una
    transformación —pedírsela sería mala literatura impuesta por un validador—, se le pide
    que alguien haya decidido que no la tiene.
    """
    incidencias: list[Incidencia] = []
    arcos_por_personaje = {a.personaje_id: a for a in escaleta.arcos}

    for personaje_id, apariciones in escaleta.apariciones_por_personaje.items():
        if apariciones < Defaults.ESCENAS_PARA_EXIGIR_ARCO:
            continue
        nombre = escaleta.nombres_por_personaje.get(personaje_id, str(personaje_id))
        arco = arcos_por_personaje.get(personaje_id)
        if arco is None:
            incidencias.append(
                Incidencia(
                    validador="arco_anclado",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje=(
                        f"«{nombre}» aparece en {apariciones} escenas y no tiene arco. Declarar "
                        f"que no se transforma —arco plano— tambien es una decision valida."
                    ),
                    ubicacion=nombre,
                )
            )
            continue
        incidencias.extend(_revisar_arco(arco, escaleta.n_capitulos))

    return incidencias


def _revisar_arco(arco: ArcoEnRevision, n_capitulos: int) -> list[Incidencia]:
    incidencias: list[Incidencia] = []

    if arco.es_homenajeado and arco.tipo == "plano":
        incidencias.append(
            Incidencia(
                validador="arco_anclado",
                severidad=Severidad.BLOQUEANTE,
                mensaje=(
                    f"El arco de «{arco.personaje}» no puede ser plano: la novela es para el."
                ),
                ubicacion=arco.personaje,
            )
        )

    if arco.tipo == "plano":
        return incidencias

    hitos = arco.hitos_por_capitulo
    if len(hitos) < Defaults.HITOS_MINIMOS_ARCO_CON_TRANSFORMACION:
        incidencias.append(
            Incidencia(
                validador="arco_anclado",
                severidad=Severidad.BLOQUEANTE,
                mensaje=(
                    f"El arco {arco.tipo} de «{arco.personaje}» tiene {len(hitos)} hito(s) "
                    f"anclado(s) y necesita al menos "
                    f"{Defaults.HITOS_MINIMOS_ARCO_CON_TRANSFORMACION}."
                ),
                ubicacion=arco.personaje,
            )
        )
    elif list(hitos) != sorted(hitos):
        # No decrecientes, no estrictamente crecientes: dos hitos en el mismo capítulo no
        # van hacia atrás, y en una novela corta exigir uno por capítulo era imponer la
        # forma de la escaleta con un validador (trama-rehacible §3.6).
        incidencias.append(
            Incidencia(
                validador="arco_anclado",
                severidad=Severidad.BLOQUEANTE,
                mensaje=(
                    f"Los hitos de «{arco.personaje}» retroceden de capitulo: {list(hitos)}. "
                    f"Una transformacion no ocurre hacia atras."
                ),
                ubicacion=arco.personaje,
            )
        )

    if arco.es_homenajeado and hitos and n_capitulos:
        if hitos[-1] <= (n_capitulos * 2) // 3:
            incidencias.append(
                Incidencia(
                    validador="arco_anclado",
                    severidad=Severidad.BLOQUEANTE,
                    mensaje=(
                        f"El ultimo hito de «{arco.personaje}» cae en el capitulo {hitos[-1]} "
                        f"de {n_capitulos}: su arco tiene que cerrar en el tercio final."
                    ),
                    ubicacion=arco.personaje,
                )
            )

    return incidencias


def cobertura_personalizacion(
    obligatorios: tuple[int, ...], usados_en_algun_capitulo: frozenset[int]
) -> list[Incidencia]:
    """Cada elemento obligatorio aparece en al menos un capítulo. La red de seguridad."""
    faltan = [d for d in obligatorios if d not in usados_en_algun_capitulo]
    if not faltan:
        return []
    return [
        Incidencia(
            validador="cobertura_personalizacion",
            severidad=Severidad.BLOQUEANTE,
            mensaje=(
                f"{len(faltan)} elemento(s) obligatorio(s) no aparecen en ningun capitulo "
                f"aprobado: {faltan}."
            ),
        )
    ]
