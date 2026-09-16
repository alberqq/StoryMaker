"""Invariantes que el esquema no puede expresar (seccion 6.3).

Un esquema JSON comprueba forma, no coherencia. Estas son puertas de codigo que
el nucleo aplica antes de persistir. Su ausencia era la razon de que RF-014 no lo
comprobara nadie.

Cada comprobacion devuelve una lista de incumplimientos, no lanza. El llamante
decide si un incumplimiento es un hallazgo bloqueante o un rechazo de la
operacion, porque no es lo mismo un plan que no cierra referencias -- que se
devuelve al diseno -- que una Restriccion derivada de una afirmacion refutada,
que sencillamente no se persiste.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from storymaker.ids import normalizar

SECCIONES_OBLIGATORIAS = (
    "indumentaria",
    "cultura_material",
    "organizacion_social",
    "mentalidad",
    "economia_y_trabajo",
)

FIDELIDAD_VERIFICADA = "verificada"
FIDELIDAD_NO_SOSTENIDA = "no_sostenida"
FIDELIDAD_NO_VERIFICABLE = "no_verificable"

VEREDICTOS_REFUTACION = (
    "confirmada",
    "matizada",
    "disputada",
    "refutada",
    "no_refutable_documentalmente",
)

# Una afirmacion solo puede sostener una Restriccion comprobable si su fidelidad
# esta verificada y su refutacion la deja en pie. `no_refutable_documentalmente`
# no es una confirmacion: una afirmacion de mentalidad no se puede desmentir con
# fuentes, y mezclarla con las que han resistido una busqueda en contra enganaria
# a quien lea la entrega. Solo puede sostener una Restriccion cualitativa.
VEREDICTOS_QUE_SOSTIENEN_COMPROBABLE = ("confirmada", "matizada")

CATEGORIAS_RESTRICCION = ("lexica", "material", "tecnologica", "institucional", "mentalidad")


@dataclass
class Incumplimiento:
    codigo: str
    requisito: str
    mensaje: str
    elemento: str | None = None

    def como_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "requisito": self.requisito,
            "mensaje": self.mensaje,
            "elemento": self.elemento,
        }


def _inc(codigo: str, requisito: str, mensaje: str, elemento: str | None = None) -> Incumplimiento:
    return Incumplimiento(codigo, requisito, mensaje, elemento)


# ==========================================================================
# Contexto historico
# ==========================================================================


def comprobar_contexto(
    cabecera: dict[str, Any],
    afirmaciones: Iterable[dict[str, Any]],
    refutaciones: Iterable[dict[str, Any]],
    restricciones: Iterable[dict[str, Any]],
    figuras: Iterable[dict[str, Any]] = (),
    ids_figuras_referenciadas: Iterable[str] = (),
) -> list[Incumplimiento]:
    """Las cinco invariantes del Contexto historico de la seccion 6.3."""
    afirmaciones = list(afirmaciones)
    refutaciones = {r["afirmacion_id"]: r for r in refutaciones}
    restricciones = list(restricciones)
    figuras = {f["id"]: f for f in figuras}
    fallos: list[Incumplimiento] = []

    por_id = {a["id"]: a for a in afirmaciones}
    lagunas = {normalizar(l.get("seccion", "")) for l in cabecera.get("lagunas", [])}

    # 1. Las cinco secciones obligatorias tienen al menos una afirmacion, o
    #    figuran como laguna con su impacto (RF-014).
    for seccion in SECCIONES_OBLIGATORIAS:
        tiene = any(
            a.get("seccion") == seccion and a.get("estado", "vigente") == "vigente"
            for a in afirmaciones
        )
        if tiene:
            continue
        if normalizar(seccion) not in lagunas:
            fallos.append(_inc(
                "ERR-102", "RF-014",
                f"La seccion obligatoria '{seccion}' no tiene ninguna afirmacion vigente "
                "ni esta declarada como laguna. Las lagunas se declaran, no se rellenan "
                "con verosimilitud.",
                seccion,
            ))
            continue
        laguna = next(
            (l for l in cabecera.get("lagunas", [])
             if normalizar(l.get("seccion", "")) == normalizar(seccion)),
            {},
        )
        if not laguna.get("impacto"):
            fallos.append(_inc(
                "ERR-102", "RF-014",
                f"La laguna de '{seccion}' esta declarada sin evaluar su impacto",
                seccion,
            ))

    # 2. Toda afirmacion en alcance de refutacion tiene veredicto emitido
    #    (RF-102, RNF-028).
    en_alcance = alcance_de_refutacion(afirmaciones, restricciones, ids_figuras_referenciadas)
    for id_afirmacion in sorted(en_alcance):
        if id_afirmacion not in refutaciones:
            fallos.append(_inc(
                "ERR-606", "RF-102",
                "Afirmacion en alcance de refutacion sin veredicto emitido. El alcance "
                "es el que sostiene una Restriccion o una ficha de figura real.",
                id_afirmacion,
            ))

    for id_afirmacion, refutacion in sorted(refutaciones.items()):
        veredicto = refutacion.get("veredicto")
        if veredicto not in VEREDICTOS_REFUTACION:
            fallos.append(_inc(
                "ERR-302", "RF-102",
                f"Veredicto de refutacion desconocido: {veredicto!r}",
                id_afirmacion,
            ))
        if veredicto == "matizada" and not refutacion.get("alcance_matiz"):
            fallos.append(_inc(
                "ERR-302", "RF-102",
                "Un veredicto 'matizada' exige declarar el alcance del matiz",
                id_afirmacion,
            ))
        if not refutacion.get("consultas"):
            fallos.append(_inc(
                "ERR-608", "RF-102",
                "Refutacion sin consultas registradas. Es lo que impide que "
                "'confirmada' signifique 'no se busco'.",
                id_afirmacion,
            ))
        # 4. Ninguna fuente contraria pertenece a las fuentes de la afirmacion.
        afirmacion = por_id.get(id_afirmacion, {})
        propias = set(afirmacion.get("fuentes", []))
        contrarias = set(refutacion.get("fuentes_contrarias", []))
        solapadas = propias & contrarias
        if solapadas:
            fallos.append(_inc(
                "ERR-608", "RF-102",
                "Una refutacion se apoya en las mismas fuentes que la afirmacion que "
                f"pretende desmentir: {sorted(solapadas)}. Toda refutacion exige fuente distinta.",
                id_afirmacion,
            ))
        if veredicto in ("refutada", "matizada", "disputada") and not contrarias:
            fallos.append(_inc(
                "ERR-608", "RF-102",
                f"Un veredicto '{veredicto}' sin fuente contraria no es una refutacion "
                "y no se registra.",
                id_afirmacion,
            ))

    # 3. Ninguna Restriccion comprobable deriva de afirmacion no verificada,
    #    refutada, o declarada no refutable (MD-7, INV-8).
    for restriccion in restricciones:
        if restriccion.get("estado") == "revocada":
            continue
        fallos.extend(comprobar_derivacion_restriccion(restriccion, por_id, refutaciones))

    # 5. Toda figura real referenciada por el Canon existe aqui con al menos una
    #    fuente (RF-019, RF-022, RNF-021).
    for id_figura in sorted(set(ids_figuras_referenciadas)):
        ficha = figuras.get(id_figura)
        if ficha is None:
            fallos.append(_inc(
                "ERR-304", "RF-022",
                "El Canon referencia una figura historica real sin ficha documental "
                "en el Contexto historico",
                id_figura,
            ))
        elif not ficha.get("fuentes"):
            fallos.append(_inc(
                "ERR-605", "RF-019",
                "Ficha de figura historica real sin ninguna Fuente documental",
                id_figura,
            ))

    return fallos


def alcance_de_refutacion(
    afirmaciones: Iterable[dict[str, Any]],
    restricciones: Iterable[dict[str, Any]],
    ids_figuras_referenciadas: Iterable[str] = (),
    figuras: Iterable[dict[str, Any]] = (),
) -> set[str]:
    """Afirmaciones sometidas a RF-100 y RF-102.

    El alcance no son todas: son las que sostienen una Restriccion de epoca o una
    ficha de figura real. El coste crece con el numero de restricciones, no con el
    de afirmaciones, y verificar el Contexto entero encareceria E2 sin ganancia:
    lo que no deriva en restriccion no valida nada.
    """
    alcance: set[str] = set()
    for restriccion in restricciones:
        if restriccion.get("estado") == "revocada":
            continue
        alcance.add(restriccion.get("afirmacion_id", ""))
    for ficha in figuras:
        if ficha.get("id") in set(ids_figuras_referenciadas):
            alcance.update(ficha.get("afirmaciones", []))
    alcance.discard("")
    return alcance


def comprobar_derivacion_restriccion(
    restriccion: dict[str, Any],
    afirmaciones_por_id: dict[str, dict[str, Any]],
    refutaciones_por_afirmacion: dict[str, dict[str, Any]],
) -> list[Incumplimiento]:
    """MD-7 e INV-8: de que puede derivarse una Restriccion y de que no.

    Una cita que no dice lo que se le atribuye contamina todo lo que se valide
    contra ella. Por eso esta puerta corre antes de persistir la Restriccion, y no
    despues.
    """
    fallos: list[Incumplimiento] = []
    identificador = restriccion.get("id", "?")
    comprobable = restriccion.get("comprobable", True)
    id_afirmacion = restriccion.get("afirmacion_id")

    if restriccion.get("categoria") not in CATEGORIAS_RESTRICCION:
        fallos.append(_inc(
            "ERR-302", "RF-016",
            f"Categoria de Restriccion desconocida: {restriccion.get('categoria')!r}. "
            f"Las cinco son {CATEGORIAS_RESTRICCION}.",
            identificador,
        ))

    afirmacion = afirmaciones_por_id.get(id_afirmacion or "")
    if afirmacion is None:
        fallos.append(_inc(
            "ERR-304", "RF-016",
            "La Restriccion no es trazable a ninguna afirmacion del Contexto historico",
            identificador,
        ))
        return fallos

    if afirmacion.get("estado") == "refutada":
        fallos.append(_inc(
            "ERR-606", "MD-7",
            "La afirmacion de la que deriva esta refutada",
            identificador,
        ))

    if not comprobable:
        # Una Restriccion cualitativa no exige fidelidad verificada: es criterio
        # de evaluacion, no puerta binaria.
        return fallos

    if afirmacion.get("fidelidad") != FIDELIDAD_VERIFICADA:
        fallos.append(_inc(
            "ERR-605", "RF-100",
            "Una Restriccion comprobable no puede derivar de una afirmacion cuya "
            f"fidelidad es '{afirmacion.get('fidelidad')}'. Se exige 'verificada'.",
            identificador,
        ))

    veredicto = (refutaciones_por_afirmacion.get(id_afirmacion or "") or {}).get("veredicto")
    if veredicto is None:
        fallos.append(_inc(
            "ERR-606", "RF-102",
            "Una Restriccion comprobable no puede derivar de una afirmacion sin "
            "veredicto de refutacion",
            identificador,
        ))
    elif veredicto not in VEREDICTOS_QUE_SOSTIENEN_COMPROBABLE:
        fallos.append(_inc(
            "ERR-606", "RF-102",
            f"Una afirmacion con veredicto '{veredicto}' no puede sostener una "
            "Restriccion comprobable. Como mucho, un criterio cualitativo.",
            identificador,
        ))

    return fallos


# ==========================================================================
# Plan de Canon
# ==========================================================================


def comprobar_plan(
    plan: dict[str, Any],
    encargo: dict[str, Any],
    ids_figuras_documentadas: Iterable[str] = (),
) -> list[Incumplimiento]:
    """Las ocho invariantes del plan de Canon de la seccion 6.3."""
    fallos: list[Incumplimiento] = []
    fallos.extend(_cierre_referencial(plan))
    fallos.extend(_presupuestos_de_palabra(plan, encargo))
    fallos.extend(_hilos_con_resolucion(plan, encargo))
    fallos.extend(_revelaciones_posteriores(plan))
    fallos.extend(_personajes_en_un_solo_lugar(plan))
    fallos.extend(_escena_avanza_algo(plan))
    fallos.extend(_figuras_reales_documentadas(plan, ids_figuras_documentadas))
    fallos.extend(_extension_por_capitulo_cuadra(plan, encargo))
    return fallos


def _escenas(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        escena
        for capitulo in plan.get("capitulos", [])
        for escena in capitulo.get("escenas", [])
    ]


def _orden_de_escena(plan: dict[str, Any]) -> dict[str, int]:
    """Posicion absoluta de cada escena en la novela, que es lo que ordena revelaciones."""
    orden: dict[str, int] = {}
    posicion = 0
    for capitulo in sorted(plan.get("capitulos", []), key=lambda c: c.get("orden", 0)):
        for escena in sorted(capitulo.get("escenas", []), key=lambda e: e.get("orden", 0)):
            orden[escena["id"]] = posicion
            posicion += 1
    return orden


def _cierre_referencial(plan: dict[str, Any]) -> list[Incumplimiento]:
    """RF-020: todo identificador citado existe."""
    fallos: list[Incumplimiento] = []
    hilos = {h["id"] for h in plan.get("hilos", [])}
    personajes = {p["id"] for p in plan.get("personajes", [])}
    lugares = {l["id"] for l in plan.get("lugares", [])}
    revelaciones = {r["id"] for r in plan.get("revelaciones", [])}
    escenas = {e["id"] for e in _escenas(plan)}

    def exigir(referencias: Iterable[str], universo: set[str], clase: str, donde: str) -> None:
        for referencia in referencias:
            if referencia not in universo:
                fallos.append(_inc(
                    "ERR-304", "RF-020",
                    f"{donde} referencia {clase} inexistente: {referencia}",
                    donde,
                ))

    for escena in _escenas(plan):
        exigir(escena.get("hilos", []), hilos, "un hilo", escena["id"])
        exigir(escena.get("personajes", []), personajes, "un personaje", escena["id"])
        exigir(escena.get("revelaciones", []), revelaciones, "una revelacion", escena["id"])
        if escena.get("lugar") and escena["lugar"] not in lugares:
            fallos.append(_inc(
                "ERR-304", "RF-020",
                f"{escena['id']} referencia un lugar inexistente: {escena['lugar']}",
                escena["id"],
            ))

    for hilo in plan.get("hilos", []):
        for clave in ("escena_apertura", "escena_resolucion"):
            referencia = hilo.get(clave)
            if referencia and referencia not in escenas:
                fallos.append(_inc(
                    "ERR-304", "RF-020",
                    f"El hilo {hilo['id']} cita en {clave} una escena inexistente: {referencia}",
                    hilo["id"],
                ))
        exigir(hilo.get("escenas_avance", []), escenas, "una escena", hilo["id"])

    for revelacion in plan.get("revelaciones", []):
        if revelacion.get("escena") and revelacion["escena"] not in escenas:
            fallos.append(_inc(
                "ERR-304", "RF-025",
                f"La revelacion {revelacion['id']} se situa en una escena inexistente",
                revelacion["id"],
            ))

    return fallos


def _presupuestos_de_palabra(plan: dict[str, Any], encargo: dict[str, Any]) -> list[Incumplimiento]:
    """RF-023 y RNF-012: la suma cae dentro de la extension objetivo y su tolerancia."""
    objetivo = encargo.get("extension_objetivo_palabras")
    if not objetivo:
        return []
    tolerancia = encargo.get("tolerancia_extension", 0.10)
    suma = sum(escena.get("presupuesto_palabras", 0) for escena in _escenas(plan))
    minimo, maximo = objetivo * (1 - tolerancia), objetivo * (1 + tolerancia)
    if not (minimo <= suma <= maximo):
        return [_inc(
            "ERR-103", "RF-023",
            f"La suma de presupuestos de escena ({suma:,} palabras) queda fuera de la "
            f"extension objetivo con su tolerancia ({minimo:,.0f} a {maximo:,.0f})",
        )]
    return []


def _hilos_con_resolucion(plan: dict[str, Any], encargo: dict[str, Any]) -> list[Incumplimiento]:
    """RF-021 y RNF-002: todo hilo sin autorizacion expresa tiene escena de resolucion."""
    autorizados = set(encargo.get("hilos_abiertos_autorizados", []))
    fallos = []
    for hilo in plan.get("hilos", []):
        if hilo["id"] in autorizados:
            continue
        if not hilo.get("escena_resolucion"):
            fallos.append(_inc(
                "ERR-102", "RF-021",
                "Hilo sin escena de resolucion planificada, y no figura entre los "
                "hilos que el Autor autorizo a quedar abiertos",
                hilo["id"],
            ))
    return fallos


def _revelaciones_posteriores(plan: dict[str, Any]) -> list[Incumplimiento]:
    """RF-025 y RF-041: toda revelacion cae despues de las escenas en que se actua sin ella.

    Es la comprobacion estatica de INV-2. La dinamica -- que el texto no adelante
    lo que el plan reserva -- la hace el validador sobre la prosa.
    """
    orden = _orden_de_escena(plan)
    fallos = []
    for revelacion in plan.get("revelaciones", []):
        escena_revelacion = revelacion.get("escena")
        if escena_revelacion not in orden:
            continue
        posicion = orden[escena_revelacion]
        for escena_previa in revelacion.get("escenas_actuando_sin_saberlo", []):
            if escena_previa in orden and orden[escena_previa] >= posicion:
                fallos.append(_inc(
                    "ERR-102", "RF-025",
                    f"La revelacion se situa en {escena_revelacion}, que no es posterior "
                    f"a {escena_previa}, donde un personaje actua sin conocerla",
                    revelacion["id"],
                ))
    return fallos


def _personajes_en_un_solo_lugar(plan: dict[str, Any]) -> list[Incumplimiento]:
    """RF-024: ningun personaje esta en dos lugares incompatibles a la vez."""
    fallos = []
    por_momento: dict[str, list[dict[str, Any]]] = {}
    for escena in _escenas(plan):
        momento = escena.get("momento")
        if momento:
            por_momento.setdefault(str(momento), []).append(escena)

    for momento, escenas in sorted(por_momento.items()):
        ubicacion: dict[str, tuple[str, str]] = {}
        for escena in escenas:
            for personaje in escena.get("personajes", []):
                lugar = escena.get("lugar")
                if personaje in ubicacion and ubicacion[personaje][0] != lugar:
                    anterior_lugar, anterior_escena = ubicacion[personaje]
                    fallos.append(_inc(
                        "ERR-103", "RF-024",
                        f"{personaje} esta en {anterior_lugar} ({anterior_escena}) y en "
                        f"{lugar} ({escena['id']}) en el mismo momento '{momento}'",
                        personaje,
                    ))
                elif lugar:
                    ubicacion[personaje] = (lugar, escena["id"])
    return fallos


def _escena_avanza_algo(plan: dict[str, Any]) -> list[Incumplimiento]:
    """RF-023: toda escena avanza al menos un hilo o porta al menos una revelacion.

    Y toda escena declara funcion narrativa. Una escena que no hace ninguna de las
    dos cosas es extension sin proposito, y se paga en presupuesto.
    """
    fallos = []
    for escena in _escenas(plan):
        if not escena.get("funcion_narrativa"):
            fallos.append(_inc(
                "ERR-102", "RF-023",
                "Escena sin funcion narrativa declarada",
                escena["id"],
            ))
        if not escena.get("hilos") and not escena.get("revelaciones"):
            fallos.append(_inc(
                "ERR-102", "RF-023",
                "Escena que no avanza ningun hilo ni porta ninguna revelacion",
                escena["id"],
            ))
    return fallos


def _figuras_reales_documentadas(
    plan: dict[str, Any], ids_documentadas: Iterable[str]
) -> list[Incumplimiento]:
    """RF-022 y RNF-021: todo personaje historico real referencia una ficha con fuente."""
    documentadas = set(ids_documentadas)
    fallos = []
    for personaje in plan.get("personajes", []):
        if personaje.get("tipo") != "historico_real":
            continue
        figura = personaje.get("figura_real")
        if not figura:
            fallos.append(_inc(
                "ERR-605", "RF-022",
                "Personaje declarado historico real sin ficha de figura documentada",
                personaje["id"],
            ))
        elif figura not in documentadas:
            fallos.append(_inc(
                "ERR-304", "RF-022",
                f"El personaje apunta a una figura ({figura}) que no existe documentada "
                "en el Contexto historico",
                personaje["id"],
            ))
    return fallos


def _extension_por_capitulo_cuadra(
    plan: dict[str, Any], encargo: dict[str, Any]
) -> list[Incumplimiento]:
    """D28 y RF-007: si hay extension por capitulo declarada, cuadra con la total.

    La palabra es la unidad canonica: si el Autor la dio en lineas, la conversion
    ocurrio en la captura y aqui ya no hay lineas.
    """
    por_capitulo = encargo.get("extension_por_capitulo")
    if not por_capitulo:
        return []
    valor = por_capitulo.get("valor_palabras") or por_capitulo.get("valor")
    if not valor:
        return []
    capitulos = plan.get("capitulos", [])
    if not capitulos:
        return []
    objetivo = encargo.get("extension_objetivo_palabras") or 0
    tolerancia = encargo.get("tolerancia_extension", 0.10)
    implicito = valor * len(capitulos)
    if objetivo and abs(implicito - objetivo) > objetivo * tolerancia:
        return [_inc(
            "ERR-103", "D28",
            f"La extension por capitulo ({valor:,} palabras) por {len(capitulos)} capitulos "
            f"da {implicito:,}, que no cuadra con la extension objetivo ({objetivo:,}) "
            "dentro de la tolerancia. El sistema no ajusta ninguna de las tres por su cuenta.",
        )]
    return []


# ==========================================================================
# Encargo
# ==========================================================================

CAMPOS_OBLIGATORIOS_ENCARGO = (
    "semillas",
    "premisa",
    "epoca",
    "ambito_geografico",
    "extension_objetivo_palabras",
    "guia_estilo",
    "politica_hechos_sensibles",
    "politica_figuras_reales",
)

PARAMETROS_ESTILO = (
    "persona_narrativa",
    "tiempo_verbal",
    "registro",
    "densidad_descriptiva",
    "recursos_apertura",
    "longitud_media_frase",
    "prohibiciones",
)


def comprobar_encargo(encargo: dict[str, Any]) -> list[Incumplimiento]:
    """Condicion de avance de E1: todo cubierto o marcado como sin preferencia."""
    fallos: list[Incumplimiento] = []

    for campo in CAMPOS_OBLIGATORIOS_ENCARGO:
        if not encargo.get(campo):
            fallos.append(_inc(
                "ERR-102", "RF-002",
                f"Campo obligatorio del Encargo sin valor ni marca: {campo}",
                campo,
            ))

    for semilla in encargo.get("semillas", []):
        if not (semilla.get("texto_literal") or "").strip():
            fallos.append(_inc("ERR-101", "RF-001", "Semilla con texto literal vacio"))
        if semilla.get("tipo") not in ("personaje", "epoca", "idea", "inspiracion"):
            fallos.append(_inc(
                "ERR-101", "RF-001",
                f"Tipo de semilla desconocido: {semilla.get('tipo')!r}. "
                "Los cuatro admitidos son personaje, epoca, idea e inspiracion.",
            ))

    epoca = encargo.get("epoca") or {}
    if not (epoca.get("desde") and epoca.get("hasta")):
        fallos.append(_inc(
            "ERR-104", "RF-003",
            "La epoca no esta acotada a un rango, y sin rango no hay investigacion posible",
            "epoca",
        ))

    # RF-029: nunca hay valor por defecto silencioso. Cada parametro declara su
    # estado, y 'sin_preferencia' significa no evaluable, no un valor implicito.
    guia = encargo.get("guia_estilo") or {}
    for parametro in PARAMETROS_ESTILO:
        entrada = guia.get(parametro)
        if entrada is None:
            fallos.append(_inc(
                "ERR-102", "RF-029",
                f"El parametro de estilo '{parametro}' no esta ni declarado ni marcado "
                "como sin preferencia. El vacio silencioso no es un estado admitido.",
                parametro,
            ))
        elif entrada.get("estado") not in ("declarado", "sin_preferencia"):
            fallos.append(_inc(
                "ERR-102", "RF-029",
                f"El parametro '{parametro}' tiene un estado desconocido: {entrada.get('estado')!r}",
                parametro,
            ))
        elif entrada.get("estado") == "declarado" and entrada.get("valor") in (None, ""):
            fallos.append(_inc(
                "ERR-102", "RF-029",
                f"El parametro '{parametro}' se declara pero no trae valor",
                parametro,
            ))

    tensiones = [t for t in encargo.get("incompatibilidades", []) if not t.get("resuelta")]
    for tension in tensiones:
        if not tension.get("aceptada_por_autor"):
            fallos.append(_inc(
                "ERR-103", "RF-007",
                f"Incompatibilidad sin arbitraje del Autor: {tension.get('descripcion')}",
            ))

    return fallos


# ==========================================================================
# Terminacion de la Novela
# ==========================================================================


def comprobar_terminacion(
    plan: dict[str, Any],
    capitulos_validados: Iterable[str],
    estado_hilos: dict[str, str],
    hallazgos_bloqueantes_abiertos: int,
    pasada_global_superada: bool,
    palabras_totales: int,
    encargo: dict[str, Any],
) -> list[Incumplimiento]:
    """Las cinco condiciones simultaneas de RF-077.

    El estado de los hilos se recalcula en el momento de decidir y nunca se lee de
    un indice: MD-6 no admite decidir sobre un derivado, porque un indice puede
    estar obsoleto y una decision no puede apoyarse en algo que puede estarlo.
    """
    fallos: list[Incumplimiento] = []
    validados = set(capitulos_validados)
    autorizados = set(encargo.get("hilos_abiertos_autorizados", []))

    planificados = {c["id"] for c in plan.get("capitulos", [])}
    pendientes = sorted(planificados - validados)
    if pendientes:
        fallos.append(_inc(
            "ERR-701", "RF-077",
            f"Quedan capitulos planificados sin validar: {', '.join(pendientes)}",
        ))

    for hilo in plan.get("hilos", []):
        if hilo["id"] in autorizados:
            continue
        if estado_hilos.get(hilo["id"]) != "resuelto":
            fallos.append(_inc(
                "ERR-701", "RNF-002",
                f"El hilo sigue en estado '{estado_hilos.get(hilo['id'], 'desconocido')}'",
                hilo["id"],
            ))

    if hallazgos_bloqueantes_abiertos:
        fallos.append(_inc(
            "ERR-701", "INV-5",
            f"Hay {hallazgos_bloqueantes_abiertos} hallazgos bloqueantes abiertos",
        ))

    if not pasada_global_superada:
        fallos.append(_inc("ERR-701", "RF-068", "La pasada global no se ha superado"))

    objetivo = encargo.get("extension_objetivo_palabras") or 0
    tolerancia = encargo.get("tolerancia_extension", 0.10)
    if objetivo and abs(palabras_totales - objetivo) > objetivo * tolerancia:
        fallos.append(_inc(
            "ERR-701", "RNF-012",
            f"La extension total ({palabras_totales:,} palabras) queda fuera de la "
            f"tolerancia del objetivo ({objetivo:,} +/- {tolerancia:.0%})",
        ))

    return fallos
