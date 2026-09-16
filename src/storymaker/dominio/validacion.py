"""E7 - Validacion de la novela y bucle externo (RF-059 a RF-069).

El validador no relee la novela. Valida contra estructuras: el libro de hechos
para la continuidad, el plan de revelaciones para lo que se puede saber, las
Restricciones de epoca para los anacronismos. Es lo que RF-028 existe para
alimentar, y es la unica forma de que validar el capitulo 38 cueste lo mismo que
validar el 4.

La puerta mas facil de saltarse sin darse cuenta es RF-067: un capitulo rechazado
no puede aprobarse si su texto no ha cambiado. Sin ella, el bucle externo se cierra
declarando que ahora si, sin que nadie haya tocado nada.
"""

from __future__ import annotations

from typing import Any, Iterable

from storymaker import SCHEMA_VERSION
from storymaker.dominio import novela as dominio_novela
from storymaker.errores import ErrorStoryMaker
from storymaker.hallazgos import (
    BLOQUEANTE,
    Hallazgo,
    abiertos,
    enrutar,
    severidad_canonica,
)
from storymaker.ids import normalizar, sha256_texto
from storymaker.proyecto import Proyecto
from storymaker.sobre import ahora


def hash_capitulo(proyecto: Proyecto, id_capitulo: str, rama: str = "principal") -> str:
    """Huella del texto completo del capitulo, que es lo que RF-067 compara."""
    return sha256_texto(texto_capitulo(proyecto, id_capitulo, rama))


def texto_capitulo(proyecto: Proyecto, id_capitulo: str, rama: str = "principal") -> str:
    plan = proyecto.exigir_canon_aprobado()
    capitulo = _exigir_capitulo(plan, id_capitulo)
    ramas = proyecto.ramas().get(rama) or {}
    partes = []
    for escena in sorted(capitulo.get("escenas", []), key=lambda e: e.get("orden", 0)):
        vigente = ramas.get(escena["id"])
        if vigente is None:
            continue
        texto = proyecto.almacen.leer_texto(
            proyecto.almacen.texto_escena(escena["id"], vigente), ""
        )
        partes.append(texto or "")
    return "\n\n".join(partes)


def preparar_para_validar(
    proyecto: Proyecto, id_capitulo: str, rama: str = "principal"
) -> dict[str, Any]:
    """CT-10: el capitulo con todas sus escenas cerradas internamente.

    Un capitulo con escenas abiertas no se valida. No es rigor formal: validar un
    capitulo a medias produce hallazgos sobre texto que va a cambiar, y eso es
    presupuesto tirado.
    """
    plan = proyecto.exigir_canon_aprobado()
    capitulo = _exigir_capitulo(plan, id_capitulo)
    ramas = proyecto.ramas().get(rama) or {}

    abiertas, cerradas, palabras = [], [], 0
    for escena in sorted(capitulo.get("escenas", []), key=lambda e: e.get("orden", 0)):
        vigente = ramas.get(escena["id"])
        if vigente is None:
            abiertas.append(escena["id"])
            continue
        meta = proyecto.almacen.leer_json(
            proyecto.almacen.meta_escena(escena["id"], vigente), {}
        ) or {}
        if not meta.get("modo_cierre"):
            abiertas.append(escena["id"])
            continue
        cerradas.append(meta)
        palabras += meta.get("palabras", 0)

    if abiertas:
        raise ErrorStoryMaker(
            "ERR-701",
            f"El capitulo {id_capitulo} tiene escenas sin cerrar internamente: {abiertas}",
            capitulo=id_capitulo,
            escenas_abiertas=abiertas,
        )

    return {
        "capitulo": id_capitulo,
        "escenas_cerradas": [m["id"] for m in cerradas],
        "extension_real": palabras,
        "presupuesto": sum(
            e.get("presupuesto_palabras", 0) for e in capitulo.get("escenas", [])
        ),
        "hash_texto": hash_capitulo(proyecto, id_capitulo, rama),
        "fichas_escenas": capitulo.get("escenas", []),
    }


# ==========================================================================
# Comprobaciones deterministas
# ==========================================================================
#
# Seccion 9.1: el arnes distingue entre lo que se comprueba y lo que se juzga, y
# no las mezcla. Una Restriccion lexica se comprueba: o el termino aparece o no.
# La solidez de un arco se juzga. Lo de aqui abajo es lo comprobable; lo juzgable
# lo hace el subagente con su rubrica.


def barrer_anacronismos_lexicos(
    proyecto: Proyecto, id_capitulo: str, rama: str = "principal"
) -> list[Hallazgo]:
    """RF-063 y RNF-005, en su parte determinista.

    Solo las Restricciones lexicas se barren asi. Las de mentalidad no tienen
    termino que buscar: las juzga el validador con rubrica, y por eso no aparecen
    aqui.
    """
    texto = normalizar(texto_capitulo(proyecto, id_capitulo, rama))
    encontrados: list[Hallazgo] = []
    for restriccion in proyecto.almacen.leer_jsonl(proyecto.almacen.restricciones):
        if restriccion.get("categoria") != "lexica" or restriccion.get("estado") == "revocada":
            continue
        for termino in restriccion.get("terminos_prohibidos", []):
            if f" {normalizar(termino)} " in f" {texto} ":
                encontrados.append(Hallazgo(
                    unidad=id_capitulo,
                    categoria="anacronismo",
                    elemento_senalado=termino,
                    severidad=BLOQUEANTE,
                    causa_raiz="redaccion",
                    descripcion=(
                        f"Aparece '{termino}', que la Restriccion {restriccion['id']} "
                        f"prohibe: {restriccion.get('enunciado')}"
                    ),
                    accion_exigida=f"Sustituir '{termino}' por un equivalente de epoca",
                    evidencia=restriccion.get("afirmacion_id", ""),
                    etapa_destino=enrutar("redaccion"),
                ))
    return encontrados


def comprobar_revelaciones_anticipadas(
    proyecto: Proyecto, id_capitulo: str, rama: str = "principal"
) -> list[Hallazgo]:
    """RF-061 e INV-2, en su parte comprobable.

    Se comprueba lo que el arnes sabe con certeza: que una escena declare portar
    una revelacion que el plan situa despues. Que el texto insinue algo sin
    declararlo es juicio del validador, no comprobacion.
    """
    plan = proyecto.exigir_canon_aprobado()
    capitulo = _exigir_capitulo(plan, id_capitulo)
    orden = _orden_absoluto(plan)
    por_revelacion = {r["id"]: r for r in plan.get("revelaciones", [])}
    ramas = proyecto.ramas().get(rama) or {}

    hallazgos: list[Hallazgo] = []
    for escena in capitulo.get("escenas", []):
        vigente = ramas.get(escena["id"])
        if vigente is None:
            continue
        meta = proyecto.almacen.leer_json(
            proyecto.almacen.meta_escena(escena["id"], vigente), {}
        ) or {}
        for id_revelacion in meta.get("revelaciones_portadas", []):
            revelacion = por_revelacion.get(id_revelacion)
            if revelacion is None:
                continue
            escena_prevista = revelacion.get("escena")
            if escena_prevista in orden and orden.get(escena["id"], 0) < orden[escena_prevista]:
                hallazgos.append(Hallazgo(
                    unidad=id_capitulo,
                    categoria="revelacion_anticipada",
                    elemento_senalado=id_revelacion,
                    severidad=BLOQUEANTE,
                    causa_raiz="redaccion",
                    descripcion=(
                        f"{escena['id']} porta la revelacion {id_revelacion}, que el plan "
                        f"situa en {escena_prevista}, posterior."
                    ),
                    accion_exigida="Retirar la revelacion de esta escena",
                    localizacion={"escena": escena["id"]},
                ))
    return hallazgos


def comprobar_ritmo(
    proyecto: Proyecto, id_capitulo: str, umbral: float = 0.20, rama: str = "principal"
) -> Hallazgo | None:
    """RF-069: extension acumulada e hilos resueltos frente a lo planificado."""
    preparado = preparar_para_validar(proyecto, id_capitulo, rama)
    presupuesto = preparado["presupuesto"]
    if not presupuesto:
        return None
    desviacion = (preparado["extension_real"] - presupuesto) / presupuesto
    if abs(desviacion) <= umbral:
        return None
    return Hallazgo(
        unidad=id_capitulo,
        categoria="extension_fuera_de_tolerancia",
        elemento_senalado=id_capitulo,
        severidad="mayor",
        causa_raiz="redaccion",
        descripcion=(
            f"El capitulo suma {preparado['extension_real']:,} palabras frente a las "
            f"{presupuesto:,} planificadas ({desviacion:+.1%})."
        ),
        accion_exigida="Ajustar la extension del capitulo hacia su presupuesto",
    )


def comprobar_licencia_de_figura(
    proyecto: Proyecto,
    id_figura: str,
    accion_atribuida: str,
    id_capitulo: str,
) -> Hallazgo | None:
    """RF-059 y RNF-021: toda accion de una figura real, respaldada o con licencia.

    El orden de comprobacion es el de la especificacion: ficha documental, luego
    Licencia de alcance vigente dentro de sus limites, luego Licencia puntual. Si
    ninguna ampara la accion, es bloqueante.
    """
    ficha = proyecto.almacen.leer_json(proyecto.almacen.figura_real(id_figura))
    if ficha and any(
        normalizar(accion_atribuida) in normalizar(hecho)
        for hecho in ficha.get("hechos_documentados", [])
    ):
        return None

    plan = proyecto.plan_canon() or {}
    for licencia in plan.get("licencias_alcance", []):
        if licencia.get("figura_o_hecho") != id_figura:
            continue
        if licencia.get("estado") != "autorizada":
            continue
        dentro = any(
            normalizar(limite) in normalizar(accion_atribuida)
            or normalizar(accion_atribuida) in normalizar(limite)
            for limite in licencia.get("limites", [])
        )
        if dentro:
            return None

    return Hallazgo(
        unidad=id_capitulo,
        categoria="afirmacion_sin_respaldo",
        elemento_senalado=f"{id_figura}:{accion_atribuida}",
        severidad=BLOQUEANTE,
        causa_raiz="redaccion",
        descripcion=(
            f"Se atribuye a la figura real {id_figura} una accion sin respaldo documental, "
            "sin Licencia de alcance vigente que la ampare y sin Licencia puntual registrada."
        ),
        accion_exigida="Respaldar con fuente, registrar Licencia literaria, o retirar la accion",
    )


# ==========================================================================
# Veredicto del capitulo
# ==========================================================================


def registrar_hallazgos(proyecto: Proyecto, lote: Iterable[Hallazgo]) -> list[dict[str, Any]]:
    """Anexa un lote de hallazgos imponiendo la escala canonica de severidad."""
    registrados = []
    for hallazgo in lote:
        hallazgo.severidad = severidad_canonica(hallazgo.categoria, hallazgo.severidad)
        hallazgo.etapa_destino = enrutar(hallazgo.causa_raiz)
        registro = hallazgo.como_dict()
        proyecto.almacen.anexar(proyecto.almacen.hallazgos, registro)
        registrados.append(registro)
    return registrados


def transicionar_hallazgo(
    proyecto: Proyecto, identificador: str, nuevo_estado: str, motivo: str
) -> dict[str, Any]:
    """Un hallazgo cambia de estado anexando, nunca sobrescribiendo."""
    actual = next(
        (h for h in reversed(proyecto.almacen.leer_jsonl(proyecto.almacen.hallazgos))
         if h.get("id") == identificador),
        None,
    )
    if actual is None:
        raise ErrorStoryMaker("ERR-304", f"No existe el hallazgo {identificador}")
    if nuevo_estado == "descartado" and not motivo.strip():
        raise ErrorStoryMaker(
            "ERR-302", "Descartar un hallazgo exige justificacion registrada"
        )
    transicionado = dict(actual)
    transicionado.update({
        "estado": nuevo_estado,
        "motivo_transicion": motivo,
        "transicionado_en": ahora(),
    })
    proyecto.almacen.anexar(proyecto.almacen.hallazgos, transicionado)
    return transicionado


def validar(
    proyecto: Proyecto,
    id_capitulo: str,
    *,
    hallazgos_del_agente: Iterable[Hallazgo] = (),
    umbral_mayores: int = 2,
    rama: str = "principal",
) -> dict[str, Any]:
    """RF-060 a RF-067: emite el veredicto del capitulo.

    Combina lo comprobable -- que corre aqui, deterministamente -- con lo que el
    subagente juzgo. Y aplica RF-067 antes que nada: si este capitulo fue rechazado
    y su texto no ha cambiado, no hay veredicto que dar.
    """
    preparado = preparar_para_validar(proyecto, id_capitulo, rama)
    hash_actual = preparado["hash_texto"]

    rechazo_previo = _ultimo_rechazo(proyecto, id_capitulo)
    if rechazo_previo and rechazo_previo.get("hash_texto") == hash_actual:
        raise ErrorStoryMaker(
            "ERR-704",
            f"El capitulo {id_capitulo} fue rechazado y su texto no ha cambiado desde "
            "entonces. No se aprueba un capitulo que nadie ha tocado (RF-067).",
            capitulo=id_capitulo,
            hash_texto=hash_actual,
            rechazado_en=rechazo_previo.get("momento"),
        )

    lote: list[Hallazgo] = list(hallazgos_del_agente)
    lote.extend(barrer_anacronismos_lexicos(proyecto, id_capitulo, rama))
    lote.extend(comprobar_revelaciones_anticipadas(proyecto, id_capitulo, rama))
    ritmo = comprobar_ritmo(proyecto, id_capitulo, rama=rama)
    if ritmo is not None:
        lote.append(ritmo)

    registrados = registrar_hallazgos(proyecto, lote)
    bloqueantes = [h for h in abiertos(lote) if h.severidad == BLOQUEANTE]
    mayores = [h for h in abiertos(lote) if h.severidad == "mayor"]
    aprobado = not bloqueantes and len(mayores) <= umbral_mayores

    veredicto = {
        "schema_version": SCHEMA_VERSION,
        "capitulo": id_capitulo,
        "aprobado": aprobado,
        "hash_texto": hash_actual,
        "momento": ahora(),
        "extension_real": preparado["extension_real"],
        "presupuesto": preparado["presupuesto"],
        "recuento": {
            "bloqueante": len(bloqueantes),
            "mayor": len(mayores),
            "menor": len(abiertos(lote, "menor")),
        },
        "hallazgos": [h["id"] for h in registrados],
        "enrutado": {h["id"]: h["etapa_destino"] for h in registrados},
    }
    _registrar_veredicto(proyecto, veredicto)
    return veredicto


def cerrar_capitulo(
    proyecto: Proyecto,
    id_capitulo: str,
    sinopsis: str,
    *,
    con_reservas: bool = False,
    hallazgos_en_deuda: Iterable[str] = (),
) -> dict[str, Any]:
    """Cierra el capitulo y congela su sinopsis.

    El cierre con reservas existe para RF-074 en modo autonomo: se cierra, se
    registra la Deuda, y la novela deja de poder declararse *finalizada*. No es un
    atajo: es la unica forma de que una ejecucion desatendida no se quede colgada
    para siempre, y se paga declarandolo en la entrega.
    """
    pendientes = list(hallazgos_en_deuda)
    if pendientes and not con_reservas:
        raise ErrorStoryMaker(
            "ERR-701",
            "No se cierra un capitulo con bloqueantes abiertos salvo cierre con reservas "
            "y Deuda de calidad emitida (INV-5)",
            capitulo=id_capitulo,
            hallazgos=pendientes,
        )

    dominio_novela.escribir_sinopsis(proyecto, id_capitulo, sinopsis)
    if con_reservas:
        proyecto.limitar_a_reservas(
            f"Capitulo {id_capitulo} cerrado con reservas y {len(pendientes)} hallazgos en deuda"
        )
    return {
        "capitulo": id_capitulo,
        "con_reservas": con_reservas,
        "hallazgos_en_deuda": pendientes,
        "sinopsis_congelada": True,
    }


def capitulos_validados(proyecto: Proyecto) -> list[str]:
    validados = []
    for veredicto in _veredictos(proyecto):
        if veredicto.get("aprobado"):
            validados.append(veredicto["capitulo"])
        elif veredicto["capitulo"] in validados:
            validados.remove(veredicto["capitulo"])
    return sorted(set(validados))


# -- interno ---------------------------------------------------------------


def _ruta_veredictos(proyecto: Proyecto):
    return proyecto.almacen.raiz / "novela" / "veredictos.jsonl"


def _registrar_veredicto(proyecto: Proyecto, veredicto: dict[str, Any]) -> None:
    proyecto.almacen.anexar(_ruta_veredictos(proyecto), veredicto)


def _veredictos(proyecto: Proyecto) -> list[dict[str, Any]]:
    return proyecto.almacen.leer_jsonl(_ruta_veredictos(proyecto))


def _ultimo_rechazo(proyecto: Proyecto, id_capitulo: str) -> dict[str, Any] | None:
    for veredicto in reversed(_veredictos(proyecto)):
        if veredicto.get("capitulo") != id_capitulo:
            continue
        return veredicto if not veredicto.get("aprobado") else None
    return None


def _exigir_capitulo(plan: dict[str, Any], id_capitulo: str) -> dict[str, Any]:
    for capitulo in plan.get("capitulos", []):
        if capitulo.get("id") == id_capitulo:
            return capitulo
    raise ErrorStoryMaker(
        "ERR-304", f"El capitulo {id_capitulo} no existe en el Canon vigente"
    )


def _orden_absoluto(plan: dict[str, Any]) -> dict[str, int]:
    orden: dict[str, int] = {}
    posicion = 0
    for capitulo in sorted(plan.get("capitulos", []), key=lambda c: c.get("orden", 0)):
        for escena in sorted(capitulo.get("escenas", []), key=lambda e: e.get("orden", 0)):
            orden[escena["id"]] = posicion
            posicion += 1
    return orden
