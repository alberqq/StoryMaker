"""Orquestacion: Ejecucion, unidades de trabajo y puntos de control (seccion 7).

Todo lo que el arnes hace ocurre dentro de una **unidad de trabajo**: un despacho
de subagente con su manifiesto de contexto, su presupuesto admitido de antemano y
su registro en el ledger. Es la pieza que hace que una Ejecucion sea reanudable,
contabilizable y reintentable.

Su ciclo es siempre el mismo. El nucleo calcula el manifiesto, estima el coste y
pide admision al presupuesto; si se admite, registra el inicio con una clave de
idempotencia y despacha el subagente; el subagente trabaja contra su memoria
efimera y propone un resultado; el nucleo valida contra esquema e invariantes,
persiste en el orden canonico y registra el cierre con su modo de terminacion.

Si algo falla en medio, **la unidad se rehace entera desde el manifiesto**. No se
continua una unidad a medias, porque una unidad a medias no tiene estado propio
que continuar: su estado o esta persistido o no existe.
"""

from __future__ import annotations

from typing import Any

from storymaker import SCHEMA_VERSION, __version__
from storymaker.errores import ErrorStoryMaker
from storymaker.ids import (
    clave_idempotencia,
    hash_corto,
    id_ejecucion,
    id_secuencial,
    id_unidad_trabajo,
)
from storymaker.ledger import Ledger
from storymaker.manifiesto import Manifiesto
from storymaker.presupuesto import (
    AMBITO_ESCENA,
    Consumo,
    Contabilidad,
    Estimacion,
    Presupuesto,
    en_ultimo_tercio,
)
from storymaker.proyecto import MODO_ASISTIDO, MODOS, Proyecto
from storymaker.sobre import ahora

# Estados de la maquina de la seccion 7.2.
TRANSICIONES: dict[str, set[str]] = {
    "Encargo": {"Investigacion"},
    "Investigacion": {"Refutacion"},
    "Refutacion": {"Investigacion", "Diseno"},       # B11 devuelve si se refuta
    "Diseno": {"ValidacionCanon"},
    "ValidacionCanon": {"Diseno", "Piloto"},          # B5
    "Piloto": {"Encargo", "Diseno", "Produccion"},    # B9
    "Produccion": {"Produccion", "Diseno", "PasadaGlobal", "Detenida"},
    "PasadaGlobal": {"Produccion", "Entrega"},        # B10
    "Detenida": {"Produccion"},
    "Entrega": set(),
}

# Puntos de control de la Funcional 12.1.
PUNTOS_CONTROL = {
    "PC-1": ("Durante la captura del encargo", "humano", False),
    "PC-2": ("Cierre del Encargo", "humano", False),
    "PC-3": ("Tras el diseno narrativo, antes de redactar", "agente", True),
    "PC-4": ("Replanificacion del Canon durante la produccion", "el_mismo_que_aprobo", False),
    "PC-5": ("Escalado por bloqueo irresoluble", "humano", False),
    "PC-6": ("Agotamiento del bucle externo con bloqueantes", "humano", True),
    "PC-8": ("Escena piloto, antes de producir en serie", "humano", True),
}

DECISIONES = (
    "aprobar", "rechazar", "editar", "regenerar", "ramificar", "aportar_fuente",
    "autorizar_licencia", "modificar_encargo", "ampliar_presupuesto", "ajustar_estilo",
    "volver_al_canon", "abandonar",
)


# ==========================================================================
# Ejecucion
# ==========================================================================


def iniciar(
    proyecto: Proyecto,
    presupuesto: Presupuesto,
    *,
    modo: str = MODO_ASISTIDO,
    versiones_agentes: dict[str, str] | None = None,
    versiones_rubricas: dict[str, str] | None = None,
    catalogo_modelos: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """RF-080 y RF-083: arranca una Ejecucion con su configuracion congelada.

    Congelar la configuracion al inicio es lo que hace RNF-013 comprobable: meses
    despues se puede saber con que version de cada prompt y de cada rubrica se
    produjo cada pasaje, porque no se lee del disco actual sino del ledger.
    """
    if modo not in MODOS:
        raise ErrorStoryMaker("ERR-105", f"Modo de operacion desconocido: {modo!r}", campo="modo")

    identificador = id_ejecucion()
    configuracion = {
        "schema_version": SCHEMA_VERSION,
        "id": identificador,
        "proyecto": proyecto.estado.id,
        "modo": modo,
        "estado": "en_curso",
        "etapa": proyecto.estado.etapa,
        "iniciada_en": ahora(),
        "version_nucleo": __version__,
        "presupuesto": presupuesto.como_dict(),
        "versiones_agentes": versiones_agentes or {},
        "versiones_rubricas": versiones_rubricas or {},
        "catalogo_modelos": catalogo_modelos or {},
        "encargo_version": proyecto.estado.encargo_version_vigente,
        "contexto_version": proyecto.estado.contexto_version_vigente,
        "canon_version": proyecto.estado.canon_version_vigente,
    }

    proyecto.almacen.escribir_json(
        proyecto.almacen.fichero_ejecucion(identificador), configuracion
    )
    ledger = Ledger(proyecto.almacen, identificador)
    ledger.anexar("ejecucion_iniciada", configuracion=configuracion)
    proyecto.guardar(ejecucion_activa=identificador, modo=modo)
    return configuracion


def estado(proyecto: Proyecto, id_ejecucion_: str | None = None) -> dict[str, Any]:
    """RF-086: lo que el Autor puede saber en cualquier momento, sin interrumpir nada."""
    identificador = id_ejecucion_ or proyecto.estado.ejecucion_activa
    if identificador is None:
        return {"ejecucion": None, "proyecto": proyecto.estado.como_dict()}

    configuracion = proyecto.almacen.leer_json(
        proyecto.almacen.fichero_ejecucion(identificador), {}
    ) or {}
    ledger = Ledger(proyecto.almacen, identificador)
    contabilidad = reconstruir_contabilidad(proyecto, identificador)

    unidades = ledger.eventos("unidad_iniciada")
    cierres = ledger.eventos("unidad_cerrada")
    en_curso = unidades[-1]["carga"] if len(unidades) > len(cierres) else None

    from storymaker.indices import GestorIndices

    gestor = GestorIndices(proyecto.almacen)
    abiertos = gestor.leer("idx_hallazgos_abiertos") or {}
    recuento = {"bloqueante": 0, "mayor": 0, "menor": 0}
    for lote in abiertos.values():
        for hallazgo in lote:
            severidad = hallazgo.get("severidad")
            if severidad in recuento:
                recuento[severidad] += 1

    avance = _avance(proyecto)
    return {
        "proyecto": proyecto.estado.como_dict(),
        "ejecucion": identificador,
        "modo": configuracion.get("modo"),
        "etapa": proyecto.estado.etapa,
        "unidad_en_proceso": en_curso,
        "iteracion": (en_curso or {}).get("intento"),
        "hallazgos_abiertos_por_severidad": recuento,
        "consumo": contabilidad.global_.como_dict(),
        "remanente": contabilidad.remanente(),
        "proyeccion": contabilidad.proyeccion(avance),
        "avance": round(avance, 4),
        "puntos_control_pendientes": listar_puntos_control(proyecto, identificador, "pendiente"),
        "lineas_descartadas": ledger.lineas_descartadas(),
    }


def pausar(proyecto: Proyecto, motivo: str) -> dict[str, Any]:
    """RNF-020: una Ejecucion detenida no consume presupuesto mientras espera."""
    identificador = _exigir_ejecucion(proyecto)
    Ledger(proyecto.almacen, identificador).anexar(
        "punto_control_abierto", tipo="pausa_manual", motivo=motivo
    )
    proyecto.guardar(etapa="Detenida")
    return {"ejecucion": identificador, "etapa": "Detenida", "motivo": motivo}


def reanudar(proyecto: Proyecto, id_ejecucion_: str | None = None) -> dict[str, Any]:
    """RF-084: reanuda desde la ultima unidad cerrada, sin rehacer trabajo valido.

    Reanudar es leer el ultimo estado consistente y continuar desde la siguiente
    unidad, conservando el consumo ya gastado. El estado de la Ejecucion vive en
    `ejecucion.json` y en el ledger, nunca en la conversacion.
    """
    identificador = id_ejecucion_ or _exigir_ejecucion(proyecto)
    ledger = Ledger(proyecto.almacen, identificador)
    configuracion = proyecto.almacen.leer_json(
        proyecto.almacen.fichero_ejecucion(identificador), {}
    ) or {}

    # ADR-06 regla 5: si el esquema del registro es anterior, se promueve en
    # lectura y se deja constancia de que se cruzo una frontera.
    if configuracion.get("schema_version") != SCHEMA_VERSION:
        ledger.anexar(
            "frontera_esquema_cruzada",
            desde=configuracion.get("schema_version"),
            hasta=SCHEMA_VERSION,
            entidad="ejecucion",
        )

    cierres = ledger.eventos("unidad_cerrada")
    ultima = cierres[-1]["carga"] if cierres else None
    contabilidad = reconstruir_contabilidad(proyecto, identificador)

    proyecto.guardar(ejecucion_activa=identificador)
    return {
        "ejecucion": identificador,
        "ultima_unidad_cerrada": ultima,
        "consumo_conservado": contabilidad.global_.como_dict(),
        "remanente": contabilidad.remanente(),
        "etapa": proyecto.estado.etapa,
        "claves_ya_cerradas": len(cierres),
    }


def finalizar(
    proyecto: Proyecto,
    estado_final: str,
    modos_terminacion: dict[str, int],
    coste_generacion_bruta: float = 0.0,
) -> dict[str, Any]:
    """RF-079: cierra la Ejecucion emitiendo el informe de calibracion."""
    identificador = _exigir_ejecucion(proyecto)
    contabilidad = reconstruir_contabilidad(proyecto, identificador)
    informe = contabilidad.informe_calibracion(modos_terminacion, coste_generacion_bruta)

    ledger = Ledger(proyecto.almacen, identificador)
    ledger.anexar(
        "ejecucion_finalizada",
        estado=estado_final,
        consumo_total=contabilidad.global_.como_dict(),
        informe_calibracion=informe,
    )

    configuracion = proyecto.almacen.leer_json(
        proyecto.almacen.fichero_ejecucion(identificador), {}
    ) or {}
    configuracion.update({"estado": estado_final, "finalizada_en": ahora()})
    proyecto.almacen.escribir_json(
        proyecto.almacen.fichero_ejecucion(identificador), configuracion
    )
    proyecto.almacen.escribir_json(
        proyecto.almacen.entrega / "informe_calibracion.json", informe
    )
    return {"ejecucion": identificador, "estado": estado_final, "informe_calibracion": informe}


def transicionar(proyecto: Proyecto, etapa_destino: str) -> dict[str, Any]:
    """Aplica la maquina de estados de la seccion 7.2, rechazando saltos invalidos."""
    origen = proyecto.estado.etapa
    permitidas = TRANSICIONES.get(origen, set())
    if etapa_destino not in permitidas:
        raise ErrorStoryMaker(
            "ERR-302",
            f"Transicion no admitida: {origen} -> {etapa_destino}. "
            f"Desde {origen} solo se puede ir a {sorted(permitidas)}.",
            origen=origen,
            destino=etapa_destino,
        )
    proyecto.guardar(etapa=etapa_destino)
    return {"etapa_anterior": origen, "etapa": etapa_destino}


# ==========================================================================
# Unidades de trabajo
# ==========================================================================


def admitir_unidad(
    proyecto: Proyecto,
    etapa: str,
    unidad: str,
    manifiesto: Manifiesto,
    estimacion: Estimacion,
    *,
    intento: int = 1,
    ambito: str = AMBITO_ESCENA,
    tramo_solicitado: str | None = None,
    capitulo_actual: int = 0,
    capitulos_totales: int = 0,
) -> dict[str, Any]:
    """Puerta de admision previa mas registro de inicio (secciones 7.1 y 8.1).

    Si la clave de idempotencia ya tiene un cierre registrado, no se vuelve a
    gastar: se devuelve el resultado anterior. Es lo que permite reanudar una
    Ejecucion caida sin pagar dos veces, y lo que hace segura `etapa reejecutar`.
    """
    identificador = _exigir_ejecucion(proyecto)
    ledger = Ledger(proyecto.almacen, identificador)

    clave = clave_idempotencia(etapa, unidad, intento, manifiesto.hash())
    cierre_previo = ledger.cierre_de_clave(clave)
    if cierre_previo is not None:
        return {
            "admitida": True,
            "ya_ejecutada": True,
            "clave_idempotencia": clave,
            "resultado_anterior": cierre_previo.get("carga"),
            "motivo": "Esta clave ya tiene un cierre registrado. No se vuelve a gastar.",
        }

    contabilidad = reconstruir_contabilidad(proyecto, identificador)
    veredicto = contabilidad.admitir(
        unidad,
        estimacion,
        ambito=ambito,
        tramo_solicitado=tramo_solicitado,
        en_ultimo_tercio=en_ultimo_tercio(capitulo_actual, capitulos_totales),
    )

    if not veredicto.admitida:
        ledger.anexar(
            "presupuesto_denegado",
            ambito=ambito,
            unidad=unidad,
            estimacion=estimacion.__dict__,
            remanente=veredicto.remanente,
            motivo=veredicto.motivo,
            codigo_error=veredicto.codigo_error,
            tramo=veredicto.tramo,
        )
        return {
            "admitida": False,
            "ya_ejecutada": False,
            "clave_idempotencia": clave,
            **veredicto.como_dict(),
        }

    ledger.anexar(
        "presupuesto_admitido",
        ambito=ambito,
        unidad=unidad,
        estimacion=estimacion.__dict__,
        remanente=veredicto.remanente,
        tramo=veredicto.tramo,
    )
    id_unidad = id_unidad_trabajo(etapa, unidad, intento)
    ledger.anexar(
        "unidad_iniciada",
        id_unidad=id_unidad,
        etapa=etapa,
        unidad=unidad,
        intento=intento,
        clave_idempotencia=clave,
        manifiesto=manifiesto.como_dict(),
    )
    proyecto.almacen.anexar(
        proyecto.almacen.unidades(identificador),
        {
            "schema_version": SCHEMA_VERSION,
            "id": id_unidad,
            "etapa": etapa,
            "unidad": unidad,
            "intento": intento,
            "clave_idempotencia": clave,
            "estado": "en_curso",
            "iniciada_en": ahora(),
        },
    )
    proyecto.almacen.preparar_tmp(id_unidad)

    return {
        "admitida": True,
        "ya_ejecutada": False,
        "id_unidad": id_unidad,
        "clave_idempotencia": clave,
        "tramo": veredicto.tramo,
        "remanente": veredicto.remanente,
        "tmp": str(proyecto.almacen.tmp(id_unidad)),
    }


def registrar_llamada(
    proyecto: Proyecto,
    id_unidad: str,
    *,
    prompt_renderizado: str,
    salida_cruda: str,
    tokens_entrada: int,
    tokens_salida: int,
    coste: float,
    segundos: float,
    modelo_solicitado: str,
    modelo_servido: str,
) -> dict[str, Any]:
    """Contabiliza una llamada al modelo y conserva sus blobs.

    El prompt y la salida van al almacen por contenido, no al ledger: el ledger
    guarda sus huellas para seguir siendo legible, y los blobs guardan el texto
    para que la trazabilidad sea completa.
    """
    identificador = _exigir_ejecucion(proyecto)
    ledger = Ledger(proyecto.almacen, identificador)

    # Orden canonico: blob primero.
    hash_prompt = proyecto.almacen.guardar_blob(prompt_renderizado)
    hash_salida = proyecto.almacen.guardar_blob(salida_cruda)

    ledger.anexar(
        "llamada_modelo",
        id_unidad=id_unidad,
        blob_prompt=hash_prompt,
        blob_salida=hash_salida,
        tokens_entrada=tokens_entrada,
        tokens_salida=tokens_salida,
        coste=coste,
        segundos=segundos,
        modelo_solicitado=modelo_solicitado,
        modelo_servido=modelo_servido,
    )
    registro = {
        "schema_version": SCHEMA_VERSION,
        "id_unidad": id_unidad,
        "momento": ahora(),
        "iteraciones": 0,
        "tokens_entrada": tokens_entrada,
        "tokens_salida": tokens_salida,
        "coste": coste,
        "segundos": segundos,
    }
    proyecto.almacen.anexar(proyecto.almacen.consumo(identificador), registro)
    return registro


def cerrar_unidad(
    proyecto: Proyecto,
    id_unidad: str,
    unidad: str,
    modo_cierre: str,
    *,
    clave_idempotencia_: str,
    version_vigente: str | None = None,
    deuda: dict[str, Any] | None = None,
    iteraciones_consumidas: int = 1,
    tramo: str | None = None,
    borrar_efimera: bool = True,
) -> dict[str, Any]:
    """RF-055: cierra la unidad, registra el modo y libera la memoria efimera.

    La memoria efimera se borra porque su contenido no se lee jamas fuera de la
    unidad que lo creo. Si algo de lo que hay ahi importaba, tenia que haberse
    persistido a traves del nucleo.
    """
    identificador = _exigir_ejecucion(proyecto)
    ledger = Ledger(proyecto.almacen, identificador)

    ledger.anexar(
        "unidad_cerrada",
        id_unidad=id_unidad,
        unidad=unidad,
        clave_idempotencia=clave_idempotencia_,
        modo_cierre=modo_cierre,
        version_vigente=version_vigente,
        deuda=deuda,
        iteraciones_consumidas=iteraciones_consumidas,
        tramo=tramo,
    )
    proyecto.almacen.anexar(
        proyecto.almacen.consumo(identificador),
        {
            "schema_version": SCHEMA_VERSION,
            "id_unidad": id_unidad,
            "unidad": unidad,
            "momento": ahora(),
            "iteraciones": iteraciones_consumidas,
            "tramo": tramo,
            "tokens_entrada": 0, "tokens_salida": 0, "coste": 0.0, "segundos": 0.0,
        },
    )
    if deuda:
        proyecto.almacen.anexar(proyecto.almacen.deudas, deuda)
    if borrar_efimera:
        proyecto.almacen.borrar_tmp(id_unidad)

    return {"id_unidad": id_unidad, "modo_cierre": modo_cierre, "deuda": deuda}


def reejecutar_etapa(
    proyecto: Proyecto, etapa: str, unidad: str
) -> dict[str, Any]:
    """RF-085: reejecuta una etapa aislada e inventaria lo que queda invalidado.

    E1 queda exceptuada (RNF-014): es un dialogo con una persona, y su reejecucion
    consiste en reproducir la conversacion registrada, no en repetirla.
    """
    if etapa in ("E1", "sm-entrada"):
        identificador = _exigir_ejecucion(proyecto)
        return {
            "reejecutable": False,
            "motivo": (
                "E1 es un dialogo con una persona. Su reejecucion consiste en reproducir "
                "la conversacion registrada, no en repetirla (RNF-014)."
            ),
            "conversacion_registrada": Ledger(proyecto.almacen, identificador).eventos(
                "punto_control_resuelto"
            ),
        }

    invalidados = _artefactos_invalidados(proyecto, etapa, unidad)
    return {
        "reejecutable": True,
        "etapa": etapa,
        "unidad": unidad,
        "artefactos_invalidados": invalidados,
        "aviso": (
            "La reejecucion parte del manifiesto registrado. Una unidad no se continua "
            "a medias: se rehace entera."
        ),
    }


def _artefactos_invalidados(proyecto: Proyecto, etapa: str, unidad: str) -> list[str]:
    """Que deja de ser valido si se reejecuta una etapa aguas arriba."""
    cascada = {
        "E2": ["contexto_historico", "restricciones", "canon", "novela_completa"],
        "sm-investigacion": ["contexto_historico", "restricciones", "canon", "novela_completa"],
        "E3": ["canon", "novela_completa"],
        "sm-diseno": ["canon", "novela_completa"],
        "E4": ["aprobacion_canon"],
        "sm-validador-canon": ["aprobacion_canon"],
        "E5": [f"versiones_posteriores_de:{unidad}", "validacion_del_capitulo"],
        "sm-redactor": [f"versiones_posteriores_de:{unidad}", "validacion_del_capitulo"],
        "E6": [f"refinados_posteriores_de:{unidad}"],
        "E7": [f"veredicto_de:{unidad}", "pasada_global"],
        "E8": ["pasada_global", "entrega"],
    }
    return cascada.get(etapa, [])


# ==========================================================================
# Puntos de control
# ==========================================================================


def abrir_punto_control(
    proyecto: Proyecto,
    tipo: str,
    presentado: dict[str, Any],
    *,
    modo_requerido: str | None = None,
) -> dict[str, Any]:
    """Abre un punto de control y detiene lo que haya que detener.

    En modo autonomo, PC-8 no detiene nada pero el piloto se registra igualmente
    como referencia de voz de la Ejecucion: su valor como linea base de estilo no
    depende de que alguien lo lea.
    """
    if tipo not in PUNTOS_CONTROL:
        raise ErrorStoryMaker("ERR-302", f"Punto de control desconocido: {tipo}")

    identificador = _exigir_ejecucion(proyecto)
    descripcion, modo_por_defecto, configurable = PUNTOS_CONTROL[tipo]
    modo_efectivo = modo_requerido or modo_por_defecto

    detiene = True
    if proyecto.estado.modo == "autonomo" and tipo in ("PC-3", "PC-8", "PC-6"):
        detiene = False

    numero = len(listar_puntos_control(proyecto, identificador)) + 1
    registro = {
        "schema_version": SCHEMA_VERSION,
        "id": id_secuencial("pct", numero),
        "tipo": tipo,
        "descripcion": descripcion,
        "modo": modo_efectivo,
        "configurable": configurable,
        "estado": "pendiente",
        "detiene_ejecucion": detiene,
        "presentado": presentado,
        "abierto_en": ahora(),
        "ejecucion": identificador,
    }
    proyecto.almacen.escribir_json(
        proyecto.almacen.punto_control(identificador, registro["id"]), registro
    )
    Ledger(proyecto.almacen, identificador).anexar(
        "punto_control_abierto", tipo=tipo, presentado=presentado, modo=modo_efectivo
    )
    if detiene:
        proyecto.guardar(etapa="Detenida")
    return registro


def resolver_punto_control(
    proyecto: Proyecto,
    id_punto: str,
    decision: str,
    quien: str,
    *,
    motivo: str = "",
    elemento_afectado: str | None = None,
) -> dict[str, Any]:
    """Recoge la decision del Autor sobre un punto de control pendiente.

    Aprobar con bloqueantes abiertos solo se admite en PC-3, solo en modo humano y
    exigiendo motivo, y deja el Proyecto limitado a *finalizado con reservas*.
    """
    if decision not in DECISIONES:
        raise ErrorStoryMaker(
            "ERR-302",
            f"Decision desconocida: {decision!r}. Las admitidas son {DECISIONES}.",
        )

    identificador = _exigir_ejecucion(proyecto)
    ruta = proyecto.almacen.punto_control(identificador, id_punto)
    registro = proyecto.almacen.leer_json(ruta)
    if registro is None:
        raise ErrorStoryMaker("ERR-304", f"No existe el punto de control {id_punto}")
    if registro.get("estado") != "pendiente":
        raise ErrorStoryMaker(
            "ERR-302",
            f"El punto de control {id_punto} ya esta {registro.get('estado')}",
        )

    bloqueantes = registro.get("presentado", {}).get("bloqueantes_abiertos", [])
    if decision == "aprobar" and bloqueantes:
        if registro["tipo"] != "PC-3":
            raise ErrorStoryMaker(
                "ERR-701",
                f"No se aprueba con bloqueantes abiertos en {registro['tipo']}. "
                "Solo PC-3 lo admite, y solo en modo humano.",
                punto=id_punto,
            )
        if registro.get("modo") != "humano":
            raise ErrorStoryMaker(
                "ERR-709",
                "Un agente no puede aprobar con bloqueantes abiertos. Solo una persona.",
                punto=id_punto,
            )
        if not motivo.strip():
            raise ErrorStoryMaker(
                "ERR-709", "Aprobar con bloqueantes abiertos exige motivo", punto=id_punto
            )
        proyecto.limitar_a_reservas(
            f"{id_punto} aprobado por {quien} con {len(bloqueantes)} bloqueantes abiertos"
        )

    registro.update({
        "estado": "resuelto",
        "decision": decision,
        "decidido_por": quien,
        "decidido_en": ahora(),
        "motivo": motivo,
        "elemento_afectado": elemento_afectado,
    })
    proyecto.almacen.escribir_json(ruta, registro)
    Ledger(proyecto.almacen, identificador).anexar(
        "punto_control_resuelto",
        tipo=registro["tipo"],
        decision=decision,
        quien=quien,
        motivo=motivo,
        elemento_afectado=elemento_afectado,
    )

    if registro["tipo"] == "PC-8":
        _aplicar_decision_piloto(proyecto, decision, registro)

    return registro


def _aplicar_decision_piloto(
    proyecto: Proyecto, decision: str, registro: dict[str, Any]
) -> None:
    """CT-20: las tres salidas de PC-8 (RF-046)."""
    identificador = _exigir_ejecucion(proyecto)
    Ledger(proyecto.almacen, identificador).anexar(
        "piloto_resuelto",
        decision=decision,
        version_escena=registro.get("presentado", {}).get("version_escena"),
    )
    if decision == "aprobar":
        proyecto.guardar(
            piloto_aceptado=True,
            piloto_version=registro.get("presentado", {}).get("version_escena"),
            etapa="Produccion",
        )
    elif decision == "ajustar_estilo":
        proyecto.guardar(etapa="Encargo")
    elif decision == "volver_al_canon":
        proyecto.guardar(etapa="Diseno")


def listar_puntos_control(
    proyecto: Proyecto, id_ejecucion_: str | None = None, estado_filtro: str | None = None
) -> list[dict[str, Any]]:
    identificador = id_ejecucion_ or proyecto.estado.ejecucion_activa
    if identificador is None:
        return []
    carpeta = proyecto.almacen.ejecucion(identificador) / "puntos_control"
    if not carpeta.exists():
        return []
    puntos = [proyecto.almacen.leer_json(f) for f in sorted(carpeta.glob("pct_*.json"))]
    if estado_filtro:
        puntos = [p for p in puntos if p and p.get("estado") == estado_filtro]
    return [p for p in puntos if p]


# ==========================================================================
# Contabilidad reconstruida
# ==========================================================================


def reconstruir_contabilidad(proyecto: Proyecto, id_ejecucion_: str) -> Contabilidad:
    """Reconstruye el consumo desde `consumo.jsonl`.

    El consumo no se guarda en memoria entre invocaciones del CLI: cada llamada es
    un proceso nuevo. Se reconstruye por barrido, que es barato, y asi la
    contabilidad sobrevive a una caida igual que el resto del estado.
    """
    configuracion = proyecto.almacen.leer_json(
        proyecto.almacen.fichero_ejecucion(id_ejecucion_), {}
    ) or {}
    presupuesto = Presupuesto.desde_dict(configuracion.get("presupuesto", {
        "coste_total": 0.0, "segundos_total": 0.0, "iteraciones_total": 0,
    }))
    contabilidad = Contabilidad(presupuesto)

    for registro in proyecto.almacen.leer_jsonl(proyecto.almacen.consumo(id_ejecucion_)):
        contabilidad.registrar(
            registro.get("unidad") or registro.get("id_unidad", "?"),
            Consumo(
                iteraciones=registro.get("iteraciones", 0),
                tokens_entrada=registro.get("tokens_entrada", 0),
                tokens_salida=registro.get("tokens_salida", 0),
                coste=registro.get("coste", 0.0),
                segundos=registro.get("segundos", 0.0),
                solicitudes_investigacion=registro.get("solicitudes_investigacion", 0),
            ),
            tramo=registro.get("tramo"),
        )
    return contabilidad


def hash_entradas(*partes: Any) -> str:
    """Huella de las entradas de una unidad, para su clave de idempotencia."""
    return hash_corto(*[str(parte) for parte in partes], longitud=16)


def _avance(proyecto: Proyecto) -> float:
    """Proporcion de escenas con version vigente sobre las planificadas."""
    plan = proyecto.plan_canon()
    if not plan:
        return 0.0
    planificadas = sum(len(c.get("escenas", [])) for c in plan.get("capitulos", []))
    if not planificadas:
        return 0.0
    escritas = len(proyecto.ramas().get("principal") or {})
    return min(escritas / planificadas, 1.0)


def _exigir_ejecucion(proyecto: Proyecto) -> str:
    if not proyecto.estado.ejecucion_activa:
        raise ErrorStoryMaker(
            "ERR-102",
            "No hay ninguna Ejecucion activa. Arranque una con `storymaker ejecucion iniciar`.",
        )
    return proyecto.estado.ejecucion_activa
