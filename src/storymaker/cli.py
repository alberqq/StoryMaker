"""La superficie del nucleo (seccion 6.4).

El nucleo se invoca como herramienta. Todo comando acepta `--json` y devuelve el
sobre de respuesta con `ok`, comando, y datos o error.

Que la salida sea siempre la misma forma es lo que permite que los hooks y los
comandos de barra la consuman sin saber que comando la produjo. Y que el codigo de
salida sea 0 o 1 segun `ok` es lo que permite a un hook `PreToolUse` denegar una
operacion sin parsear nada.

Toda escritura entra por aqui y toma el cerrojo de Proyecto (ADR-04 regla 1). Las
lecturas no lo toman: consultar el estado no debe bloquear a quien lo esta
produciendo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from storymaker import SCHEMA_VERSION, __version__
from storymaker.almacen import CerrojoProyecto
from storymaker.bucles import Evaluacion, Iteracion, decidir, distribucion_modos
from storymaker.dominio import canon as d_canon
from storymaker.dominio import contexto as d_contexto
from storymaker.dominio import ejecucion as d_ejecucion
from storymaker.dominio import encargo as d_encargo
from storymaker.dominio import global_ as d_global
from storymaker.dominio import novela as d_novela
from storymaker.dominio import traza as d_traza
from storymaker.dominio import validacion as d_validacion
from storymaker.errores import CATALOGO, ErrorStoryMaker
from storymaker.esquemas import SUPERFICIE_AGENTE, RegistroContratos
from storymaker.hallazgos import Hallazgo
from storymaker.indices import GestorIndices
from storymaker.manifiesto import construir as construir_manifiesto
from storymaker.presupuesto import Estimacion, Presupuesto
from storymaker.proyecto import Proyecto
from storymaker.sobre import Respuesta

RAIZ_POR_DEFECTO = os.environ.get("STORYMAKER_RAIZ", "proyectos")

# Comandos que escriben estado y por tanto toman el cerrojo. Los que no estan aqui
# solo leen, y no deben bloquear a quien esta produciendo.
COMANDOS_QUE_ESCRIBEN = {
    "proyecto crear", "encargo sesion", "encargo responder", "encargo ingerir",
    "encargo confirmar", "contexto fuente", "contexto afirmar", "contexto verificar",
    "contexto refutar", "contexto restriccion", "contexto figura", "contexto cerrar",
    "canon proponer", "canon aprobar", "canon replanificar", "canon licencia",
    "canon hecho", "escena escribir", "escena refinar", "escena proteger",
    "escena cerrar", "escena ramificar", "escena promover", "capitulo validar",
    "capitulo cerrar", "novela pasada-global", "novela cerrar", "novela ensamblar",
    "ejecucion iniciar", "ejecucion reanudar", "ejecucion pausar", "ejecucion finalizar",
    "unidad admitir", "unidad llamada", "unidad cerrar", "control abrir",
    "control resolver", "entrega generar", "indices reconstruir", "hallazgo emitir",
    "hallazgo transicionar", "sinopsis escribir",
}


def _cargar_json(valor: str | None) -> Any:
    """Acepta JSON inline, `@fichero` o `-` para leer de la entrada estandar."""
    if valor is None:
        return None
    if valor == "-":
        return json.loads(sys.stdin.read())
    if valor.startswith("@"):
        return json.loads(Path(valor[1:]).read_text(encoding="utf-8"))
    return json.loads(valor)


def _proyecto(args: argparse.Namespace) -> Proyecto:
    return Proyecto(args.raiz, args.proyecto)


def _validar_contrato(
    args: argparse.Namespace, nombre: str, dato: Any, contrato: str
) -> Any:
    """Valida una propuesta de agente contra su contrato (seccion 6.1).

    La superficie es **estricta**: un campo inventado es senal de que el prompt se
    desvia, y dispara reparacion. Se valida aqui, en la frontera, y no dentro del
    dominio, porque el dominio tambien lo llaman las pruebas y el propio nucleo con
    estructuras que ya sabe bien formadas.

    Si el esquema no esta disponible -- alguien movio `contracts/` -- se deja pasar
    y se avisa: quedarse sin validar es peor que parar, porque las invariantes de
    §6.3 siguen corriendo despues y son las que de verdad protegen el estado.
    """
    try:
        validador = RegistroContratos(args.contratos).validador(
            nombre, superficie=SUPERFICIE_AGENTE
        )
    except ErrorStoryMaker:
        return dato
    resultado = validador.validar(dato)
    if not resultado:
        raise ErrorStoryMaker(
            "ERR-302",
            f"La propuesta no cumple el contrato {contrato} ({nombre}): "
            + "; ".join(resultado.problemas[:6]),
            contrato=contrato,
            esquema=nombre,
            problemas=resultado.problemas,
        )
    return dato


# ==========================================================================
# Manejadores
# ==========================================================================


def _proyecto_crear(args) -> dict[str, Any]:
    proyecto = Proyecto.crear(args.raiz, args.titulo, modo=args.modo)
    return {"proyecto": proyecto.estado.como_dict()}


def _encargo_sesion(args) -> dict[str, Any]:
    return d_encargo.abrir_sesion(_proyecto(args), args.semilla, args.tipo)


def _encargo_responder(args) -> dict[str, Any]:
    valor = _cargar_json(args.valor) if args.valor else None
    return d_encargo.responder(
        _proyecto(args), args.campo, valor, sin_preferencia=args.sin_preferencia
    )


def _encargo_ingerir(args) -> dict[str, Any]:
    return d_encargo.ingerir_fichero(_proyecto(args), _cargar_json(args.datos))


def _encargo_presentar(args) -> dict[str, Any]:
    return d_encargo.presentar(_proyecto(args))


def _encargo_confirmar(args) -> dict[str, Any]:
    proyecto = _proyecto(args)
    resultado = d_encargo.confirmar(proyecto, args.quien)
    resultado["ambito_investigacion"] = d_encargo.ambito_investigacion(resultado["encargo"])
    resultado["guia_estilo_efectiva"] = d_encargo.guia_estilo_efectiva(resultado["encargo"])
    return resultado


def _encargo_estilo(args) -> dict[str, Any]:
    proyecto = _proyecto(args)
    encargo = proyecto.encargo()
    if encargo is None:
        raise ErrorStoryMaker("ERR-102", "No hay Encargo cerrado")
    return d_encargo.guia_estilo_efectiva(encargo)


def _contexto_fuente(args) -> dict[str, Any]:
    contenido = None
    if args.contenido:
        contenido = (
            Path(args.contenido[1:]).read_text(encoding="utf-8")
            if args.contenido.startswith("@") else args.contenido
        )
    return {"fuente": d_contexto.registrar_fuente(
        _proyecto(args), args.localizador, args.tipo, contenido,
        fiabilidad=args.fiabilidad, motivo_no_conservable=args.motivo_no_conservable,
    )}


def _contexto_afirmar(args) -> dict[str, Any]:
    return {"afirmacion": d_contexto.afirmar(
        _proyecto(args), args.enunciado, args.seccion,
        fuentes=args.fuente or [], sin_fuente=args.sin_fuente,
        certeza=args.certeza, origen=args.origen, tipo_afirmacion=args.tipo,
        disputada=args.disputada,
    )}


def _contexto_verificar(args) -> dict[str, Any]:
    return d_contexto.verificar_fidelidad(
        _proyecto(args), args.afirmacion, args.resultado,
        contenido_cotejado=args.contenido_cotejado, motivo=args.motivo or "",
    )


def _contexto_refutar(args) -> dict[str, Any]:
    return d_contexto.refutar(
        _proyecto(args), args.afirmacion, args.veredicto,
        tipo_afirmacion=args.tipo, consultas=_cargar_json(args.consultas),
        fuentes_contrarias=args.fuente_contraria or [], alcance_matiz=args.alcance_matiz,
    )


def _contexto_restriccion(args) -> dict[str, Any]:
    return {"restriccion": d_contexto.derivar_restriccion(
        _proyecto(args), args.enunciado, args.categoria, args.afirmacion,
        comprobable=not args.cualitativa,
        terminos_prohibidos=args.termino or [],
        severidad_incumplimiento=args.severidad,
    )}


def _contexto_figura(args) -> dict[str, Any]:
    return {"figura": d_contexto.documentar_figura(
        _proyecto(args), args.id, args.nombre,
        fuentes=args.fuente or [], afirmaciones=args.afirmacion or [],
        hechos_documentados=args.hecho or [],
    )}


def _contexto_cerrar(args) -> dict[str, Any]:
    lagunas = _cargar_json(args.lagunas) if args.lagunas else []
    return d_contexto.cerrar(
        _proyecto(args), lagunas,
        cobertura_reducida=args.cobertura_reducida,
        ids_figuras_referenciadas=args.figura or [],
    )


def _contexto_indicadores(args) -> dict[str, Any]:
    return d_contexto.indicadores(_proyecto(args), args.figura or [])


def _canon_proponer(args) -> dict[str, Any]:
    plan = _validar_contrato(args, "canon_plan", _cargar_json(args.plan), "CT-4")
    return d_canon.proponer(
        _proyecto(args), plan,
        motivo_cambio=args.motivo, origen_cambio=args.origen,
    )


def _canon_aprobar(args) -> dict[str, Any]:
    return d_canon.aprobar(
        _proyecto(args), modo=args.modo_aprobacion, quien=args.quien,
        bloqueantes_asumidos=args.bloqueante_asumido or [],
        motivo_asuncion=args.motivo or "",
    )


def _canon_replanificar(args) -> dict[str, Any]:
    proyecto = _proyecto(args)
    plan = _validar_contrato(args, "canon_plan", _cargar_json(args.plan), "CT-4")
    return d_canon.replanificar(
        proyecto, plan, motivo=args.motivo, origen=args.origen,
        capitulos_validados=d_validacion.capitulos_validados(proyecto),
    )


def _canon_licencia(args) -> dict[str, Any]:
    return {"licencia": d_canon.instanciar_licencia_alcance(
        _proyecto(args), figura_o_hecho=args.figura, desviacion=args.desviacion,
        justificacion_narrativa=args.justificacion, limites=args.limite or [],
        propuesta_por=args.quien,
    )}


def _canon_hecho(args) -> dict[str, Any]:
    return d_canon.anexar_hecho(
        _proyecto(args), args.enunciado, args.sujeto, args.tipo_sujeto,
        args.escena, args.version_escena,
    )


def _canon_hechos(args) -> dict[str, Any]:
    return {"hechos": d_canon.hechos_de_sujetos(_proyecto(args), args.sujeto or [])}


def _escena_escribir(args) -> dict[str, Any]:
    texto = (
        Path(args.texto[1:]).read_text(encoding="utf-8")
        if args.texto.startswith("@") else args.texto
    )
    proyecto = _proyecto(args)
    return d_novela.escribir(
        proyecto, args.escena, texto,
        id_unidad=args.unidad, ejecucion=proyecto.estado.ejecucion_activa or "sin_ejecucion",
        iteracion=args.iteracion, es_piloto=args.piloto,
        hallazgos_aplicados=args.hallazgo or [],
        revelaciones_portadas=args.revelacion or [],
    )


def _escena_refinar(args) -> dict[str, Any]:
    texto = (
        Path(args.texto[1:]).read_text(encoding="utf-8")
        if args.texto.startswith("@") else args.texto
    )
    proyecto = _proyecto(args)
    return d_novela.refinar(
        proyecto, args.escena, texto,
        id_unidad=args.unidad, ejecucion=proyecto.estado.ejecucion_activa or "sin_ejecucion",
        iteracion=args.iteracion,
        justificaciones_proteccion=_cargar_json(args.justificaciones) if args.justificaciones else None,
    )


def _escena_proteger(args) -> dict[str, Any]:
    return d_novela.proteger_pasaje(_proyecto(args), args.escena, args.pasaje, args.hallazgo)


def _escena_cerrar(args) -> dict[str, Any]:
    return d_novela.cerrar_escena(
        _proyecto(args), args.escena, args.modo_cierre,
        hallazgos_pendientes=args.hallazgo or [],
    )


def _escena_ramificar(args) -> dict[str, Any]:
    return d_novela.ramificar(_proyecto(args), args.escena, args.rama, args.motivo)


def _escena_promover(args) -> dict[str, Any]:
    return d_novela.promover(_proyecto(args), args.escena, args.rama)


def _escena_decidir(args) -> dict[str, Any]:
    """Aplica los cinco modos de terminacion a las iteraciones de una escena."""
    datos = _cargar_json(args.iteraciones)
    iteraciones = [
        Iteracion(
            numero=item.get("numero", indice + 1),
            id_version=item["id_version"],
            hallazgos=[Hallazgo.desde_dict(h) for h in item.get("hallazgos", [])],
            evaluacion=Evaluacion.desde_dict(item["evaluacion"]) if item.get("evaluacion") else None,
        )
        for indice, item in enumerate(datos)
    ]
    decision = decidir(
        iteraciones,
        presupuesto_agotado=args.presupuesto_agotado,
        bloqueo_irresoluble=args.bloqueo_irresoluble,
        umbral_mayores=args.umbral_mayores,
        resueltos_previos=args.resuelto_previo or [],
    )
    return decision.como_dict()


def _sinopsis_escribir(args) -> dict[str, Any]:
    texto = (
        Path(args.texto[1:]).read_text(encoding="utf-8")
        if args.texto.startswith("@") else args.texto
    )
    return d_novela.escribir_sinopsis(_proyecto(args), args.capitulo, texto)


def _hallazgo_emitir(args) -> dict[str, Any]:
    crudos = _cargar_json(args.hallazgos)
    for hallazgo in crudos:
        _validar_contrato(args, "lote_hallazgos", {
            "schema_version": SCHEMA_VERSION, "emisor": args.emisor,
            "unidad": hallazgo.get("unidad", "?"), "hallazgos": [hallazgo],
        }, "CT-5/8/11/16")
    lote = [Hallazgo.desde_dict(h) for h in crudos]
    return {"hallazgos": d_validacion.registrar_hallazgos(_proyecto(args), lote)}


def _hallazgo_transicionar(args) -> dict[str, Any]:
    return {"hallazgo": d_validacion.transicionar_hallazgo(
        _proyecto(args), args.id, args.estado, args.motivo or ""
    )}


def _capitulo_validar(args) -> dict[str, Any]:
    lote = [Hallazgo.desde_dict(h) for h in (_cargar_json(args.hallazgos) or [])]
    return d_validacion.validar(
        _proyecto(args), args.capitulo,
        hallazgos_del_agente=lote, umbral_mayores=args.umbral_mayores,
    )


def _capitulo_preparar(args) -> dict[str, Any]:
    return d_validacion.preparar_para_validar(_proyecto(args), args.capitulo)


def _capitulo_cerrar(args) -> dict[str, Any]:
    sinopsis = (
        Path(args.sinopsis[1:]).read_text(encoding="utf-8")
        if args.sinopsis.startswith("@") else args.sinopsis
    )
    return d_validacion.cerrar_capitulo(
        _proyecto(args), args.capitulo, sinopsis,
        con_reservas=args.con_reservas, hallazgos_en_deuda=args.hallazgo or [],
    )


def _novela_pasada_global(args) -> dict[str, Any]:
    return d_global.pasada_global(_proyecto(args), banda_estilo=args.banda)


def _novela_cerrar(args) -> dict[str, Any]:
    return d_global.cerrar_novela(_proyecto(args), args.bloqueantes_abiertos)


def _novela_ensamblar(args) -> dict[str, Any]:
    return d_global.ensamblar(_proyecto(args))


def _novela_hilos(args) -> dict[str, Any]:
    return {
        "estado_hilos": d_global.recalcular_estado_hilos(_proyecto(args)),
        "nota": "Recalculado en el momento de consultar. MD-6 prohibe decidir sobre el indice.",
    }


def _entrega_generar(args) -> dict[str, Any]:
    return d_global.generar_entrega(_proyecto(args), con_pdf=not args.sin_pdf)


def _ejecucion_iniciar(args) -> dict[str, Any]:
    presupuesto = Presupuesto(
        coste_total=args.coste, segundos_total=args.segundos,
        iteraciones_total=args.iteraciones,
    )
    return d_ejecucion.iniciar(
        _proyecto(args), presupuesto, modo=args.modo_ejecucion,
        versiones_agentes=_cargar_json(args.versiones_agentes) if args.versiones_agentes else None,
        versiones_rubricas=_cargar_json(args.versiones_rubricas) if args.versiones_rubricas else None,
    )


def _ejecucion_estado(args) -> dict[str, Any]:
    return d_ejecucion.estado(_proyecto(args), args.ejecucion)


def _ejecucion_reanudar(args) -> dict[str, Any]:
    return d_ejecucion.reanudar(_proyecto(args), args.ejecucion)


def _ejecucion_pausar(args) -> dict[str, Any]:
    return d_ejecucion.pausar(_proyecto(args), args.motivo)


def _ejecucion_finalizar(args) -> dict[str, Any]:
    modos = _cargar_json(args.modos) if args.modos else distribucion_modos([])
    return d_ejecucion.finalizar(
        _proyecto(args), args.estado, modos, args.coste_generacion_bruta
    )


def _etapa_reejecutar(args) -> dict[str, Any]:
    return d_ejecucion.reejecutar_etapa(_proyecto(args), args.etapa, args.unidad)


def _unidad_admitir(args) -> dict[str, Any]:
    manifiesto = construir_manifiesto(
        args.etapa, args.unidad, _cargar_json(args.contenidos), limite_tokens=args.limite_tokens
    )
    estimacion = Estimacion(
        iteraciones=args.iteraciones_estimadas, coste=args.coste_estimado,
        segundos=args.segundos_estimados, tokens_manifiesto=manifiesto.tokens,
    )
    resultado = d_ejecucion.admitir_unidad(
        _proyecto(args), args.etapa, args.unidad, manifiesto, estimacion,
        intento=args.intento, tramo_solicitado=args.tramo,
        capitulo_actual=args.capitulo_actual, capitulos_totales=args.capitulos_totales,
    )
    resultado["manifiesto"] = manifiesto.como_dict()
    if args.render:
        resultado["manifiesto_renderizado"] = manifiesto.render()
    return resultado


def _unidad_llamada(args) -> dict[str, Any]:
    return d_ejecucion.registrar_llamada(
        _proyecto(args), args.unidad,
        prompt_renderizado=args.prompt, salida_cruda=args.salida,
        tokens_entrada=args.tokens_entrada, tokens_salida=args.tokens_salida,
        coste=args.coste, segundos=args.segundos,
        modelo_solicitado=args.modelo_solicitado, modelo_servido=args.modelo_servido,
    )


def _unidad_cerrar(args) -> dict[str, Any]:
    return d_ejecucion.cerrar_unidad(
        _proyecto(args), args.unidad, args.nombre_unidad, args.modo_cierre,
        clave_idempotencia_=args.clave, version_vigente=args.version_vigente,
        deuda=_cargar_json(args.deuda) if args.deuda else None,
        iteraciones_consumidas=args.iteraciones, tramo=args.tramo,
    )


def _control_abrir(args) -> dict[str, Any]:
    return d_ejecucion.abrir_punto_control(
        _proyecto(args), args.tipo, _cargar_json(args.presentado), modo_requerido=args.modo_pc
    )


def _control_listar(args) -> dict[str, Any]:
    return {"puntos_control": d_ejecucion.listar_puntos_control(
        _proyecto(args), estado_filtro=args.estado
    )}


def _control_resolver(args) -> dict[str, Any]:
    return d_ejecucion.resolver_punto_control(
        _proyecto(args), args.id, args.decision, args.quien,
        motivo=args.motivo or "", elemento_afectado=args.elemento,
    )


def _traza_pasaje(args) -> dict[str, Any]:
    return d_traza.trazar_pasaje(_proyecto(args), args.version_escena)


def _traza_afirmacion(args) -> dict[str, Any]:
    return d_traza.trazar_afirmacion(_proyecto(args), args.consulta)


def _indices_reconstruir(args) -> dict[str, Any]:
    return {"indices": GestorIndices(_proyecto(args).almacen).reconstruir_todos()}


def _informe_calibracion(args) -> dict[str, Any]:
    proyecto = _proyecto(args)
    identificador = args.ejecucion or proyecto.estado.ejecucion_activa
    if identificador is None:
        raise ErrorStoryMaker("ERR-102", "No hay Ejecucion de la que informar")
    contabilidad = d_ejecucion.reconstruir_contabilidad(proyecto, identificador)
    modos = _cargar_json(args.modos) if args.modos else distribucion_modos([])
    return contabilidad.informe_calibracion(modos, args.coste_generacion_bruta)


def _contratos_listar(args) -> dict[str, Any]:
    registro = RegistroContratos(args.contratos)
    return {"contratos": registro.contratos_disponibles(), "raiz": str(registro.raiz)}


def _errores_listar(args) -> dict[str, Any]:
    return {
        "errores": [
            {
                "codigo": d.codigo, "familia": d.familia, "condicion": d.condicion,
                "reintentable": d.reintentable, "accion": d.accion,
            }
            for d in sorted(CATALOGO.values(), key=lambda d: d.codigo)
        ]
    }


# ==========================================================================
# Analizador de argumentos
# ==========================================================================


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="storymaker",
        description=(
            "Nucleo determinista de StoryMaker. Propietario unico del estado: los "
            "agentes proponen, aqui se valida, se versiona, se contabiliza y se persiste."
        ),
    )
    parser.add_argument("--version", action="version", version=f"storymaker {__version__}")
    parser.add_argument("--raiz", default=RAIZ_POR_DEFECTO, help="Raiz del arbol de proyectos")
    parser.add_argument("--proyecto", help="Identificador del Proyecto")
    parser.add_argument("--contratos", default="contracts", help="Raiz de los esquemas de contrato")
    parser.add_argument("--json", action="store_true", help="Salida en JSON (la de por defecto)")

    grupos = parser.add_subparsers(dest="grupo", required=True)

    def sub(grupo_parser, nombre: str, funcion: Callable[[argparse.Namespace], dict[str, Any]], ayuda: str):
        """Declara un subcomando y le cuelga su manejador."""
        p = grupo_parser.add_parser(nombre, help=ayuda)
        p.set_defaults(_funcion=funcion)
        return p

    # -- proyecto ----------------------------------------------------------
    g = grupos.add_parser("proyecto", help="Ciclo de vida del Proyecto").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "crear", _proyecto_crear, "Crea un Proyecto")
    p.add_argument("--titulo", required=True)
    p.add_argument("--modo", default="asistido", choices=["asistido", "autonomo_supervisado", "autonomo"])

    # -- encargo (E1) ------------------------------------------------------
    g = grupos.add_parser("encargo", help="E1 - Captura del encargo").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "sesion", _encargo_sesion, "Abre la captura registrando una semilla")
    p.add_argument("--semilla", required=True)
    p.add_argument("--tipo", required=True, choices=list(d_encargo.TIPOS_SEMILLA))
    p = sub(g, "responder", _encargo_responder, "Registra una respuesta del Autor")
    p.add_argument("--campo", required=True)
    p.add_argument("--valor")
    p.add_argument("--sin-preferencia", action="store_true")
    p = sub(g, "ingerir", _encargo_ingerir, "Ingiere un Encargo en JSON (RF-110)")
    p.add_argument("--datos", required=True, help="JSON inline, @fichero o -")
    sub(g, "presentar", _encargo_presentar, "Presenta el Encargo para confirmacion (RF-006)")
    p = sub(g, "confirmar", _encargo_confirmar, "Cierra el Encargo (PC-2)")
    p.add_argument("--quien", required=True)
    sub(g, "estilo", _encargo_estilo, "Guia de estilo efectiva (RF-029)")

    # -- contexto (E2) -----------------------------------------------------
    g = grupos.add_parser("contexto", help="E2 - Investigacion y refutacion").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "fuente", _contexto_fuente, "Registra una Fuente y conserva su contenido")
    p.add_argument("--localizador", required=True)
    p.add_argument("--tipo", required=True, choices=list(d_contexto.MODOS_RECUPERACION))
    p.add_argument("--contenido", help="Texto o @fichero")
    p.add_argument("--fiabilidad", default="sin_declarar")
    p.add_argument("--motivo-no-conservable")
    p = sub(g, "afirmar", _contexto_afirmar, "Registra una afirmacion atomica")
    p.add_argument("--enunciado", required=True)
    p.add_argument("--seccion", required=True)
    p.add_argument("--fuente", action="append")
    p.add_argument("--sin-fuente", action="store_true")
    p.add_argument("--certeza", default="documentada")
    p.add_argument("--origen", default="inicial")
    p.add_argument("--tipo", default="existencial_positiva", choices=list(d_contexto.TIPOS_AFIRMACION))
    p.add_argument("--disputada", action="store_true")
    p = sub(g, "verificar", _contexto_verificar, "Verifica que la Fuente sostiene la afirmacion (RF-100)")
    p.add_argument("--afirmacion", required=True)
    p.add_argument("--resultado", required=True, choices=["verificada", "no_sostenida", "no_verificable"])
    p.add_argument("--contenido-cotejado", required=True)
    p.add_argument("--motivo")
    p = sub(g, "refutar", _contexto_refutar, "Emite el veredicto de refutacion (RF-102)")
    p.add_argument("--afirmacion", required=True)
    p.add_argument("--veredicto", required=True, choices=list(d_contexto.VEREDICTOS_REFUTACION))
    p.add_argument("--tipo", required=True, choices=list(d_contexto.TIPOS_AFIRMACION))
    p.add_argument("--consultas", required=True, help="JSON inline, @fichero o -")
    p.add_argument("--fuente-contraria", action="append")
    p.add_argument("--alcance-matiz")
    p = sub(g, "restriccion", _contexto_restriccion, "Deriva una Restriccion de epoca (RF-016)")
    p.add_argument("--enunciado", required=True)
    p.add_argument("--categoria", required=True, choices=list(d_contexto.CATEGORIAS_RESTRICCION))
    p.add_argument("--afirmacion", required=True)
    p.add_argument("--cualitativa", action="store_true")
    p.add_argument("--termino", action="append")
    p.add_argument("--severidad", default="bloqueante", choices=["bloqueante", "mayor", "menor"])
    p = sub(g, "figura", _contexto_figura, "Documenta una figura historica real (RF-019)")
    p.add_argument("--id", required=True)
    p.add_argument("--nombre", required=True)
    p.add_argument("--fuente", action="append", required=True)
    p.add_argument("--afirmacion", action="append")
    p.add_argument("--hecho", action="append")
    p = sub(g, "cerrar", _contexto_cerrar, "Versiona y valida el Contexto historico")
    p.add_argument("--lagunas", help="JSON inline, @fichero o -")
    p.add_argument("--cobertura-reducida")
    p.add_argument("--figura", action="append", help="Figuras referenciadas por el Canon")
    p = sub(g, "indicadores", _contexto_indicadores, "RNF-004, 006, 027 y 028")
    p.add_argument("--figura", action="append")

    # -- canon (E3 y E4) ---------------------------------------------------
    g = grupos.add_parser("canon", help="E3 y E4 - Canon").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "proponer", _canon_proponer, "Propone un plan en borrador")
    p.add_argument("--plan", required=True, help="JSON inline, @fichero o -")
    p.add_argument("--motivo")
    p.add_argument("--origen")
    p = sub(g, "aprobar", _canon_aprobar, "Aprueba el Canon como linea base (PC-3)")
    p.add_argument("--modo-aprobacion", required=True, choices=["agente", "humano"])
    p.add_argument("--quien", required=True)
    p.add_argument("--bloqueante-asumido", action="append")
    p.add_argument("--motivo")
    p = sub(g, "replanificar", _canon_replanificar, "Version nueva con capitulos invalidados")
    p.add_argument("--plan", required=True)
    p.add_argument("--motivo", required=True)
    p.add_argument("--origen", required=True)
    p = sub(g, "licencia", _canon_licencia, "Instancia una Licencia de alcance (RF-035)")
    p.add_argument("--figura", required=True)
    p.add_argument("--desviacion", required=True)
    p.add_argument("--justificacion", required=True)
    p.add_argument("--limite", action="append", required=True)
    p.add_argument("--quien", required=True)
    p = sub(g, "hecho", _canon_hecho, "Anexa un hecho emergente (RF-028)")
    p.add_argument("--enunciado", required=True)
    p.add_argument("--sujeto", required=True)
    p.add_argument("--tipo-sujeto", required=True, choices=list(d_canon.TIPOS_SUJETO))
    p.add_argument("--escena", required=True)
    p.add_argument("--version-escena", required=True)
    p = sub(g, "hechos", _canon_hechos, "Hechos por sujeto, para el manifiesto")
    p.add_argument("--sujeto", action="append", required=True)

    # -- escena (E5 y E6) --------------------------------------------------
    g = grupos.add_parser("escena", help="E5 y E6 - Redaccion y refinamiento").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "escribir", _escena_escribir, "Persiste una version nueva de escena")
    p.add_argument("--escena", required=True)
    p.add_argument("--texto", required=True, help="Texto o @fichero")
    p.add_argument("--unidad", required=True)
    p.add_argument("--iteracion", type=int, default=1)
    p.add_argument("--piloto", action="store_true")
    p.add_argument("--hallazgo", action="append")
    p.add_argument("--revelacion", action="append")
    p = sub(g, "refinar", _escena_refinar, "Version refinada, respetando protegidos")
    p.add_argument("--escena", required=True)
    p.add_argument("--texto", required=True)
    p.add_argument("--unidad", required=True)
    p.add_argument("--iteracion", type=int, default=2)
    p.add_argument("--justificaciones", help="JSON de justificaciones de proteccion")
    p = sub(g, "proteger", _escena_proteger, "Marca un pasaje como protegido (RF-054)")
    p.add_argument("--escena", required=True)
    p.add_argument("--pasaje", required=True)
    p.add_argument("--hallazgo", required=True)
    p = sub(g, "cerrar", _escena_cerrar, "Cierra el bucle interno (RF-055)")
    p.add_argument("--escena", required=True)
    p.add_argument("--modo-cierre", required=True,
                   choices=["convergencia", "estancamiento", "regresion", "agotamiento"])
    p.add_argument("--hallazgo", action="append")
    p = sub(g, "decidir", _escena_decidir, "Aplica los modos de terminacion T1-T5")
    p.add_argument("--iteraciones", required=True, help="JSON inline, @fichero o -")
    p.add_argument("--presupuesto-agotado", action="store_true")
    p.add_argument("--bloqueo-irresoluble", action="store_true")
    p.add_argument("--umbral-mayores", type=int, default=2)
    p.add_argument("--resuelto-previo", action="append")
    p = sub(g, "ramificar", _escena_ramificar, "Abre una rama alternativa")
    p.add_argument("--escena", required=True)
    p.add_argument("--rama", required=True)
    p.add_argument("--motivo", required=True)
    p = sub(g, "promover", _escena_promover, "Promueve una alternativa a principal")
    p.add_argument("--escena", required=True)
    p.add_argument("--rama", required=True)

    # -- sinopsis ----------------------------------------------------------
    g = grupos.add_parser("sinopsis", help="Memoria de trabajo del redactor").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "escribir", _sinopsis_escribir, "Congela la sinopsis de un capitulo")
    p.add_argument("--capitulo", required=True)
    p.add_argument("--texto", required=True)

    # -- hallazgo ----------------------------------------------------------
    g = grupos.add_parser("hallazgo", help="Hallazgos").add_subparsers(dest="accion", required=True)
    p = sub(g, "emitir", _hallazgo_emitir, "Anexa un lote de hallazgos")
    p.add_argument("--hallazgos", required=True, help="JSON inline, @fichero o -")
    p.add_argument("--emisor", default="agente-critico")
    p = sub(g, "transicionar", _hallazgo_transicionar, "Cambia el estado de un hallazgo")
    p.add_argument("--id", required=True)
    p.add_argument("--estado", required=True,
                   choices=["abierto", "en_correccion", "resuelto", "aceptado_como_deuda", "descartado"])
    p.add_argument("--motivo")

    # -- capitulo (E7) -----------------------------------------------------
    g = grupos.add_parser("capitulo", help="E7 - Validacion").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "preparar", _capitulo_preparar, "CT-10: capitulo listo para validar")
    p.add_argument("--capitulo", required=True)
    p = sub(g, "validar", _capitulo_validar, "Emite el veredicto del capitulo")
    p.add_argument("--capitulo", required=True)
    p.add_argument("--hallazgos", help="JSON del lote del subagente")
    p.add_argument("--umbral-mayores", type=int, default=2)
    p = sub(g, "cerrar", _capitulo_cerrar, "Cierra el capitulo y congela su sinopsis")
    p.add_argument("--capitulo", required=True)
    p.add_argument("--sinopsis", required=True, help="Texto o @fichero")
    p.add_argument("--con-reservas", action="store_true")
    p.add_argument("--hallazgo", action="append")

    # -- novela (E8) -------------------------------------------------------
    g = grupos.add_parser("novela", help="E8 - Pasada global y terminacion").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "pasada-global", _novela_pasada_global, "RF-068")
    p.add_argument("--banda", type=float, default=0.25)
    p = sub(g, "cerrar", _novela_cerrar, "Las cinco condiciones de RF-077")
    p.add_argument("--bloqueantes-abiertos", type=int, default=0)
    sub(g, "ensamblar", _novela_ensamblar, "RF-090")
    sub(g, "hilos", _novela_hilos, "Estado de hilos recalculado")

    # -- entrega -----------------------------------------------------------
    g = grupos.add_parser("entrega", help="RF-090 a RF-093").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "generar", _entrega_generar, "Markdown, PDF y paquete de trazabilidad")
    p.add_argument("--sin-pdf", action="store_true")

    # -- ejecucion ---------------------------------------------------------
    g = grupos.add_parser("ejecucion", help="Orquestacion").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "iniciar", _ejecucion_iniciar, "Arranca con la configuracion congelada")
    p.add_argument("--coste", type=float, required=True)
    p.add_argument("--segundos", type=float, default=86400.0)
    p.add_argument("--iteraciones", type=int, required=True)
    p.add_argument("--modo-ejecucion", default="asistido",
                   choices=["asistido", "autonomo_supervisado", "autonomo"])
    p.add_argument("--versiones-agentes")
    p.add_argument("--versiones-rubricas")
    p = sub(g, "estado", _ejecucion_estado, "RF-086")
    p.add_argument("--ejecucion")
    p = sub(g, "reanudar", _ejecucion_reanudar, "RF-084")
    p.add_argument("--ejecucion")
    p = sub(g, "pausar", _ejecucion_pausar, "Detiene sin consumir presupuesto")
    p.add_argument("--motivo", required=True)
    p = sub(g, "finalizar", _ejecucion_finalizar, "Cierra y emite calibracion (RF-079)")
    p.add_argument("--estado", required=True)
    p.add_argument("--modos", help="JSON con la distribucion de modos de terminacion")
    p.add_argument("--coste-generacion-bruta", type=float, default=0.0)

    # -- etapa -------------------------------------------------------------
    g = grupos.add_parser("etapa", help="Reejecucion aislada").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "reejecutar", _etapa_reejecutar, "RF-085")
    p.add_argument("--etapa", required=True)
    p.add_argument("--unidad", required=True)

    # -- unidad ------------------------------------------------------------
    g = grupos.add_parser("unidad", help="Unidades de trabajo").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "admitir", _unidad_admitir, "Puerta de admision previa (seccion 8.1)")
    p.add_argument("--etapa", required=True)
    p.add_argument("--unidad", required=True)
    p.add_argument("--contenidos", required=True, help="JSON con los bloques del manifiesto")
    p.add_argument("--intento", type=int, default=1)
    p.add_argument("--iteraciones-estimadas", type=int, default=1)
    p.add_argument("--coste-estimado", type=float, default=0.0)
    p.add_argument("--segundos-estimados", type=float, default=0.0)
    p.add_argument("--limite-tokens", type=int, default=120000)
    p.add_argument("--tramo", choices=["libre", "final"])
    p.add_argument("--capitulo-actual", type=int, default=0)
    p.add_argument("--capitulos-totales", type=int, default=0)
    p.add_argument("--render", action="store_true")
    p = sub(g, "llamada", _unidad_llamada, "Contabiliza una llamada a modelo")
    p.add_argument("--unidad", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--tokens-entrada", type=int, required=True)
    p.add_argument("--tokens-salida", type=int, required=True)
    p.add_argument("--coste", type=float, required=True)
    p.add_argument("--segundos", type=float, default=0.0)
    p.add_argument("--modelo-solicitado", required=True)
    p.add_argument("--modelo-servido", required=True)
    p = sub(g, "cerrar", _unidad_cerrar, "Cierra la unidad y libera la memoria efimera")
    p.add_argument("--unidad", required=True, help="Identificador udt_")
    p.add_argument("--nombre-unidad", required=True, help="Escena o capitulo afectado")
    p.add_argument("--modo-cierre", required=True)
    p.add_argument("--clave", required=True)
    p.add_argument("--version-vigente")
    p.add_argument("--deuda")
    p.add_argument("--iteraciones", type=int, default=1)
    p.add_argument("--tramo", choices=["libre", "final"])

    # -- control -----------------------------------------------------------
    g = grupos.add_parser("control", help="Puntos de control PC-1 a PC-8").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "abrir", _control_abrir, "Abre un punto de control")
    p.add_argument("--tipo", required=True, choices=list(d_ejecucion.PUNTOS_CONTROL))
    p.add_argument("--presentado", required=True, help="JSON de lo que se presenta")
    p.add_argument("--modo-pc", choices=["agente", "humano"])
    p = sub(g, "listar", _control_listar, "Lista los puntos de control")
    p.add_argument("--estado", choices=["pendiente", "resuelto"])
    p = sub(g, "resolver", _control_resolver, "Recoge la decision")
    p.add_argument("--id", required=True)
    p.add_argument("--decision", required=True, choices=list(d_ejecucion.DECISIONES))
    p.add_argument("--quien", required=True)
    p.add_argument("--motivo")
    p.add_argument("--elemento")

    # -- traza -------------------------------------------------------------
    g = grupos.add_parser("traza", help="RF-081 y RF-082").add_subparsers(
        dest="accion", required=True
    )
    p = sub(g, "pasaje", _traza_pasaje, "Origen completo de un pasaje")
    p.add_argument("--version-escena", required=True)
    p = sub(g, "afirmacion", _traza_afirmacion, "Respaldo de una afirmacion historica")
    p.add_argument("--consulta", required=True, help="Identificador o fragmento de texto")

    # -- indices, informes y catalogos -------------------------------------
    g = grupos.add_parser("indices", help="Indices derivados").add_subparsers(
        dest="accion", required=True
    )
    sub(g, "reconstruir", _indices_reconstruir, "Barrido completo")

    g = grupos.add_parser("informe", help="Informes").add_subparsers(dest="accion", required=True)
    p = sub(g, "calibracion", _informe_calibracion, "RF-079")
    p.add_argument("--ejecucion")
    p.add_argument("--modos")
    p.add_argument("--coste-generacion-bruta", type=float, default=0.0)

    g = grupos.add_parser("contratos", help="Esquemas de contrato").add_subparsers(
        dest="accion", required=True
    )
    sub(g, "listar", _contratos_listar, "Contratos disponibles")

    g = grupos.add_parser("errores", help="Taxonomia de errores").add_subparsers(
        dest="accion", required=True
    )
    sub(g, "listar", _errores_listar, "Catalogo completo")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    comando = f"{args.grupo} {getattr(args, 'accion', '')}".strip()
    funcion = getattr(args, "_funcion", None)

    if funcion is None:
        parser.error("subcomando no reconocido")
        return 2

    escribe = comando in COMANDOS_QUE_ESCRIBEN
    necesita_proyecto = comando != "proyecto crear" and not comando.startswith(("contratos", "errores"))
    if necesita_proyecto and not args.proyecto:
        respuesta = Respuesta.fallo(
            comando,
            ErrorStoryMaker("ERR-102", "Falta --proyecto", comando=comando),
        )
        print(respuesta.como_json())
        return 1

    cerrojo = None
    try:
        if escribe and args.proyecto:
            from storymaker.almacen import Almacen

            cerrojo = CerrojoProyecto(Almacen(args.raiz, args.proyecto), titular=comando)
            cerrojo.tomar()
        datos = funcion(args)
        respuesta = Respuesta.exito(comando, **datos)
        print(respuesta.como_json())
        return 0
    except ErrorStoryMaker as error:
        respuesta = Respuesta.fallo(comando, error)
        print(respuesta.como_json())
        _registrar_en_ledger(args, error, comando)
        return 1
    except (json.JSONDecodeError, FileNotFoundError, KeyError, ValueError) as fallo:
        error = ErrorStoryMaker("ERR-301", str(fallo), comando=comando)
        print(Respuesta.fallo(comando, error).como_json())
        return 1
    finally:
        if cerrojo is not None:
            cerrojo.liberar()


def _registrar_en_ledger(args: argparse.Namespace, error: ErrorStoryMaker, comando: str) -> None:
    """Regla transversal de la seccion 10: ningun error se traga.

    Si el fallo impide siquiera abrir el Proyecto, no hay ledger donde anexar y se
    deja pasar: lo que no se puede registrar no se registra, pero la salida ya lo
    dijo por `stderr` del proceso llamante.
    """
    try:
        proyecto = Proyecto(args.raiz, args.proyecto)
        if not proyecto.estado.ejecucion_activa:
            return
        from storymaker.ledger import Ledger

        Ledger(proyecto.almacen, proyecto.estado.ejecucion_activa).registrar_error(
            error, comando=comando
        )
    except Exception:  # noqa: BLE001 - el registro no puede enmascarar el error original
        return


if __name__ == "__main__":
    raise SystemExit(main())
