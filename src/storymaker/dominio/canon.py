"""E3 y E4 - Canon: plan versionado y libro de hechos (RF-020 a RF-035).

MD-4 parte el Canon en dos clases de dato distintas, y esa particion es lo que lo
hace viable:

| Aspecto      | Plan                              | Libro de hechos                  |
|--------------|-----------------------------------|----------------------------------|
| Clase        | Instantanea inmutable versionada  | Verdad de solo anexion           |
| Quien escribe| El nucleo, por replanificacion    | El nucleo, al cerrar cada escena |
| Frecuencia   | Unidades por novela               | Decenas por capitulo             |
| Efecto       | Version nueva, capitulos invalidados | Ninguno sobre la linea base   |
| Lectura      | Carga completa                    | Por sujeto; nunca entero         |

Sin la particion, mencionar una cicatriz en una escena generaria una version del
plan, porque INV-6 versiona toda modificacion del Canon y RF-028 anexa hechos en
cada escena. Con ella, las dos cosas conviven.

El plan **no** guarda el estado de ejecucion de los hilos. Ese estado es derivado
del libro de hechos y de las escenas validadas, y guardarlo aqui obligaria a
versionar el plan en cada capitulo. La contrapartida es que RF-077 lo recalcula en
el momento de decidir, nunca lo lee de un indice, porque MD-6 no admite decidir
sobre un derivado.
"""

from __future__ import annotations

from typing import Any, Iterable

from storymaker import SCHEMA_VERSION
from storymaker.errores import ErrorStoryMaker
from storymaker.ids import id_hecho, id_secuencial, id_version, normalizar
from storymaker.invariantes import comprobar_plan
from storymaker.proyecto import EN_PRODUCCION, Proyecto
from storymaker.sobre import ahora

BORRADOR = "borrador"
EN_VALIDACION = "en_validacion"
APROBADO = "aprobado"
SUPERADO = "superado"

TIPOS_SUJETO = ("personaje", "lugar", "objeto", "relacion", "promesa")

MODO_AGENTE = "agente"
MODO_HUMANO = "humano"


# ==========================================================================
# Plan
# ==========================================================================


def proponer(
    proyecto: Proyecto,
    plan: dict[str, Any],
    *,
    motivo_cambio: str | None = None,
    origen_cambio: str | None = None,
) -> dict[str, Any]:
    """RF-020 a RF-025: registra un plan en borrador tras comprobar sus invariantes.

    Las invariantes se comprueban **antes** de persistir, no despues. Un plan que
    no cierra referencias o cuyos presupuestos no suman la extension objetivo no
    llega al almacen: vuelve al diseno como lote de hallazgos (CT-5).
    """
    encargo = proyecto.encargo()
    if encargo is None:
        raise ErrorStoryMaker(
            "ERR-102", "No hay Encargo cerrado: el Canon no puede construirse sin el"
        )

    numero = proyecto.siguiente_version("can")
    if numero > 1 and not (motivo_cambio and origen_cambio):
        # RF-026: a partir de la version 2, motivo y origen son obligatorios. Una
        # version sin motivo registrado no explica nada dentro de seis semanas.
        raise ErrorStoryMaker(
            "ERR-604",
            "A partir de la version 2 del Canon, motivo y origen del cambio son obligatorios",
            version=numero,
        )

    figuras_documentadas = _figuras_documentadas(proyecto)
    fallos = comprobar_plan(plan, encargo, figuras_documentadas)
    if fallos:
        raise ErrorStoryMaker(
            "ERR-102",
            "El plan de Canon no cumple sus invariantes y no se persiste",
            incumplimientos=[f.como_dict() for f in fallos],
        )

    identificador = id_version("can", proyecto.estado.id, numero)
    anterior = proyecto.estado.canon_version_vigente
    registro = {
        **plan,
        "schema_version": SCHEMA_VERSION,
        "id": identificador,
        "version": numero,
        "estado": BORRADOR,
        "version_anterior": anterior,
        "motivo_cambio": motivo_cambio,
        "origen_cambio": origen_cambio,
        "aprobado_por": None,
        "capitulos_invalidados": [],
        "creado_en": ahora(),
        "encargo_version": encargo.get("id"),
        "contexto_version": proyecto.estado.contexto_version_vigente,
    }

    proyecto.almacen.escribir_json(proyecto.almacen.plan_canon(identificador), registro)
    proyecto.guardar(
        canon_version_vigente=identificador, canon_estado=BORRADOR, etapa="ValidacionCanon"
    )
    return {"plan": registro, "version": identificador}


def aprobar(
    proyecto: Proyecto,
    *,
    modo: str,
    quien: str,
    bloqueantes_asumidos: Iterable[str] = (),
    motivo_asuncion: str = "",
) -> dict[str, Any]:
    """RF-030, RF-031 y D23: aprueba el Canon como linea base.

    El punto delicado es quien puede aprobar con bloqueantes abiertos. **Solo una
    persona.** Un agente validador nunca. Y cuando ocurre, cada bloqueante se
    convierte en Deuda de calidad o en Licencia registrada, la decision y su autor
    quedan en el ledger, y el Proyecto queda limitado a *finalizado con reservas*
    para siempre.
    """
    if modo not in (MODO_AGENTE, MODO_HUMANO):
        raise ErrorStoryMaker("ERR-302", f"Modo de aprobacion desconocido: {modo!r}")

    asumidos = list(bloqueantes_asumidos)
    if asumidos and modo != MODO_HUMANO:
        raise ErrorStoryMaker(
            "ERR-709",
            "Un agente validador no puede aprobar un Canon con bloqueantes abiertos. "
            "Solo una persona, y dejando constancia.",
            modo=modo,
            bloqueantes=asumidos,
        )
    if asumidos and not motivo_asuncion.strip():
        raise ErrorStoryMaker(
            "ERR-709", "Asumir bloqueantes exige motivo registrado", bloqueantes=asumidos
        )

    version = proyecto.estado.canon_version_vigente
    plan = proyecto.plan_canon()
    if plan is None or version is None:
        raise ErrorStoryMaker("ERR-304", "No hay ningun plan de Canon que aprobar")
    if plan.get("estado") == APROBADO:
        raise ErrorStoryMaker(
            "ERR-604",
            "Este plan ya esta aprobado. Un Canon aprobado es inmutable: toda "
            "modificacion genera version nueva (INV-6).",
            version=version,
        )

    aprobado = dict(plan)
    aprobado.update({
        "estado": APROBADO,
        "aprobado_por": {
            "modo": modo,
            "quien": quien,
            "decidido_en": ahora(),
            "bloqueantes_asumidos": asumidos,
            "motivo_asuncion": motivo_asuncion or None,
        },
    })
    proyecto.almacen.escribir_json(proyecto.almacen.plan_canon(version), aprobado)
    proyecto.guardar(canon_estado=APROBADO, etapa="Piloto")

    if asumidos:
        proyecto.limitar_a_reservas(
            f"Canon {version} aprobado con {len(asumidos)} bloqueantes asumidos por {quien}"
        )

    return {
        "plan": aprobado,
        "version": version,
        "limitado_a_reservas": bool(asumidos),
        "codigo_error": "ERR-709" if asumidos else None,
        "guia_estilo_efectiva_disponible": True,
    }


def replanificar(
    proyecto: Proyecto,
    plan_nuevo: dict[str, Any],
    *,
    motivo: str,
    origen: str,
    capitulos_validados: Iterable[str],
) -> dict[str, Any]:
    """RF-026 y RF-027: version nueva, con los capitulos que invalida identificados.

    `capitulos_validados` es obligatorio a proposito. Un valor por defecto vacio
    significaria "no se invalida nada", que es exactamente el fallo silencioso que
    RF-027 existe para evitar: el llamante tiene que decir que estaba validado.

    Lo que invalida un cambio de plan no se deduce despues: se calcula aqui,
    comparando la estructura de escenas de las dos versiones. Un capitulo validado
    cuyas escenas cambian de ficha deja de estar validado, y hay que decirlo antes
    de aprobar la replanificacion, no cuando se descubra la incoherencia.
    """
    anterior = proyecto.plan_canon()
    if anterior is None:
        raise ErrorStoryMaker("ERR-304", "No hay plan vigente que replanificar")

    invalidados = capitulos_invalidados(anterior, plan_nuevo, capitulos_validados)
    resultado = proponer(proyecto, plan_nuevo, motivo_cambio=motivo, origen_cambio=origen)

    registro = dict(resultado["plan"])
    registro["capitulos_invalidados"] = invalidados
    proyecto.almacen.escribir_json(proyecto.almacen.plan_canon(registro["id"]), registro)

    # La version anterior queda superada, no destruida (INV-6).
    superada = dict(anterior)
    superada["estado"] = SUPERADO
    superada["superada_por"] = registro["id"]
    proyecto.almacen.escribir_json(proyecto.almacen.plan_canon(anterior["id"]), superada)

    return {
        "plan": registro,
        "version_anterior": anterior["id"],
        "version_nueva": registro["id"],
        "capitulos_invalidados": invalidados,
        "requiere_punto_control": "PC-4",
        "codigo_error": "ERR-603" if invalidados else None,
    }


def capitulos_invalidados(
    anterior: dict[str, Any],
    nuevo: dict[str, Any],
    capitulos_validados: Iterable[str] = (),
) -> list[str]:
    """Que capitulos ya validados deja sin valor la version nueva (RF-027)."""
    validados = set(capitulos_validados)
    fichas_antes = _fichas_por_capitulo(anterior)
    fichas_ahora = _fichas_por_capitulo(nuevo)
    invalidados = []
    for capitulo in sorted(validados):
        if fichas_antes.get(capitulo) != fichas_ahora.get(capitulo):
            invalidados.append(capitulo)
    return invalidados


def _fichas_por_capitulo(plan: dict[str, Any]) -> dict[str, Any]:
    """Huella comparable de cada capitulo: lo que define lo que hay que escribir."""
    salida: dict[str, Any] = {}
    for capitulo in plan.get("capitulos", []):
        salida[capitulo["id"]] = [
            {
                "id": escena.get("id"),
                "orden": escena.get("orden"),
                "funcion_narrativa": escena.get("funcion_narrativa"),
                "personajes": sorted(escena.get("personajes", [])),
                "lugar": escena.get("lugar"),
                "momento": escena.get("momento"),
                "hilos": sorted(escena.get("hilos", [])),
                "revelaciones": sorted(escena.get("revelaciones", [])),
                "presupuesto_palabras": escena.get("presupuesto_palabras"),
            }
            for escena in sorted(capitulo.get("escenas", []), key=lambda e: e.get("orden", 0))
        ]
    return salida


def arrancar_produccion(proyecto: Proyecto) -> dict[str, Any]:
    """Transicion a produccion tras aceptarse el piloto (INV-9)."""
    proyecto.exigir_canon_aprobado()
    if not proyecto.estado.piloto_aceptado:
        raise ErrorStoryMaker(
            "ERR-502",
            "Ninguna escena se produce en serie antes de que el piloto haya sido "
            "aceptado por el Autor (INV-9, RF-046)",
        )
    proyecto.guardar(estado=EN_PRODUCCION, etapa="Produccion")
    return {"estado": proyecto.estado.como_dict()}


# ==========================================================================
# Licencias de alcance
# ==========================================================================


def instanciar_licencia_alcance(
    proyecto: Proyecto,
    *,
    figura_o_hecho: str,
    desviacion: str,
    justificacion_narrativa: str,
    limites: list[str],
    propuesta_por: str,
) -> dict[str, Any]:
    """RF-035: una Licencia de alcance vive en el plan y se aprueba con el.

    Sin ella, una premisa que hace participar a una figura real en una trama no
    documentada exigiria tantas autorizaciones como escenas en las que aparezca.
    Con ella, se autoriza una vez, con limites declarados, y el validador comprueba
    que cada aparicion cae dentro de esos limites (RF-059).
    """
    if not limites:
        raise ErrorStoryMaker(
            "ERR-706",
            "Una Licencia de alcance sin limites declarados es un cheque en blanco "
            "sobre toda la novela",
        )
    plan = proyecto.plan_canon()
    if plan is None:
        raise ErrorStoryMaker("ERR-304", "No hay plan de Canon donde instanciar la licencia")
    if plan.get("estado") == APROBADO:
        raise ErrorStoryMaker(
            "ERR-604",
            "Las Licencias de alcance se aprueban con el Canon en PC-3. Anadir una a un "
            "Canon aprobado exige replanificacion.",
        )

    existentes = plan.get("licencias_alcance", [])
    licencia = {
        "schema_version": SCHEMA_VERSION,
        "id": id_secuencial("lic", len(existentes) + 1),
        "alcance": "proyecto",
        "figura_o_hecho": figura_o_hecho,
        "desviacion": desviacion,
        "justificacion_narrativa": justificacion_narrativa,
        "limites": limites,
        "propuesta_por": propuesta_por,
        "autorizada_por": None,
        "estado": "propuesta",
        "creada_en": ahora(),
    }
    plan.setdefault("licencias_alcance", []).append(licencia)
    proyecto.almacen.escribir_json(proyecto.almacen.plan_canon(plan["id"]), plan)
    proyecto.almacen.anexar(proyecto.almacen.licencias, licencia)
    return licencia


# ==========================================================================
# Libro de hechos
# ==========================================================================


def anexar_hecho(
    proyecto: Proyecto,
    enunciado: str,
    sujeto: str,
    tipo_sujeto: str,
    escena_origen: str,
    escena_version_origen: str,
) -> dict[str, Any]:
    """RF-028 con la resolucion de conflictos de la seccion 5.3.

    Tres reglas al anexar, en este orden:

    1. Si coincide exactamente con un hecho existente, **no anexa** y devuelve el
       identificador existente. Eso hace la operacion idempotente, que es lo que
       permite reintentar una unidad sin ensuciar el libro.
    2. Si es compatible, anexa.
    3. Si contradice, **rechaza y emite hallazgo bloqueante** de continuidad con
       causa raiz en la redaccion.

    La deteccion de contradiccion entre proposiciones en lenguaje natural es el
    punto blando de todo esto. Aqui se resuelve lo que se puede resolver de forma
    determinista -- misma clave de sujeto y atributo con valor distinto -- y el
    resto queda declarado como comprobacion por modelo con rubrica (T-03).
    """
    if tipo_sujeto not in TIPOS_SUJETO:
        raise ErrorStoryMaker(
            "ERR-302",
            f"Tipo de sujeto desconocido: {tipo_sujeto!r}. Los cinco son {TIPOS_SUJETO}.",
        )

    identificador = id_hecho(sujeto, enunciado)
    existentes = _hechos_vigentes(proyecto)

    for hecho in existentes:
        if hecho["id"] == identificador:
            # Regla 1: idempotencia.
            return {"hecho": hecho, "anexado": False, "motivo": "ya existia identico"}

    del_sujeto = [h for h in existentes if normalizar(h.get("sujeto", "")) == normalizar(sujeto)]
    contradiccion = _detectar_contradiccion(enunciado, del_sujeto)
    if contradiccion is not None:
        # Regla 3: rechazo con hallazgo bloqueante.
        raise ErrorStoryMaker(
            "ERR-601",
            f"El hecho contradice uno ya establecido sobre {sujeto}: "
            f"{contradiccion['enunciado']!r} (de {contradiccion['escena_origen']})",
            sujeto=sujeto,
            enunciado_nuevo=enunciado,
            hecho_en_conflicto=contradiccion["id"],
            escena_en_conflicto=contradiccion.get("escena_origen"),
            severidad="bloqueante",
            causa_raiz="redaccion",
        )

    registro = {
        "schema_version": SCHEMA_VERSION,
        "id": identificador,
        "enunciado": enunciado,
        "sujeto": sujeto,
        "tipo_sujeto": tipo_sujeto,
        "escena_origen": escena_origen,
        "escena_version_origen": escena_version_origen,
        "retracta": None,
        "retractado_por": None,
        "creado_en": ahora(),
    }
    proyecto.almacen.anexar(proyecto.almacen.hechos, registro)
    return {"hecho": registro, "anexado": True}


def retractar_hecho(
    proyecto: Proyecto, identificador: str, enunciado_correcto: str, motivo: str
) -> dict[str, Any]:
    """Un hecho erroneo se retracta anexando otro. Nunca se borra.

    Es la unica forma de compensacion que admite un libro de solo anexion, y es lo
    que lo mantiene auditable: el error sigue ahi, y tambien su correccion.
    """
    original = next((h for h in _hechos_vigentes(proyecto) if h["id"] == identificador), None)
    if original is None:
        raise ErrorStoryMaker("ERR-304", f"No existe el hecho {identificador}")

    correccion = {
        "schema_version": SCHEMA_VERSION,
        "id": id_hecho(original["sujeto"], enunciado_correcto),
        "enunciado": enunciado_correcto,
        "sujeto": original["sujeto"],
        "tipo_sujeto": original["tipo_sujeto"],
        "escena_origen": original["escena_origen"],
        "escena_version_origen": original["escena_version_origen"],
        "retracta": identificador,
        "retractado_por": None,
        "motivo_retractacion": motivo,
        "creado_en": ahora(),
    }
    proyecto.almacen.anexar(proyecto.almacen.hechos, correccion)
    return {"retractado": identificador, "correccion": correccion}


def hechos_de_sujetos(proyecto: Proyecto, sujetos: Iterable[str]) -> list[dict[str, Any]]:
    """Lo que el manifiesto del redactor y del validador reciben (seccion 3.4).

    El redactor no recibe la novela previa. Recibe esto, que es mas barato y mas
    fiable: la sinopsis da el hilo, y los hechos dan la letra pequena -- que mano,
    que color, que promesa exacta -- que es justo el detalle que causa las
    contradicciones de continuidad.
    """
    claves = {normalizar(s) for s in sujetos}
    return [
        hecho for hecho in _hechos_vigentes(proyecto)
        if normalizar(hecho.get("sujeto", "")) in claves
    ]


def _hechos_vigentes(proyecto: Proyecto) -> list[dict[str, Any]]:
    todos = proyecto.almacen.leer_jsonl(proyecto.almacen.hechos)
    retractados = {h["retracta"] for h in todos if h.get("retracta")}
    return [h for h in todos if h.get("id") not in retractados]


def _detectar_contradiccion(
    enunciado: str, hechos_del_sujeto: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Parte determinista de la deteccion de contradiccion (T-03).

    Cubre el caso comprobable: dos hechos que atribuyen al mismo sujeto el mismo
    atributo con valor distinto. Lo que no cubre -- contradiccion semantica entre
    proposiciones libres -- es comprobacion por modelo con rubrica, y asi se
    declara en lugar de fingir que un `if` la resuelve.
    """
    atributo_nuevo, valor_nuevo = _atributo_y_valor(enunciado)
    if atributo_nuevo is None:
        return None
    for hecho in hechos_del_sujeto:
        atributo, valor = _atributo_y_valor(hecho.get("enunciado", ""))
        if atributo == atributo_nuevo and valor and valor != valor_nuevo:
            return hecho
    return None


# Atributos cuya unicidad por sujeto es comprobable sin juicio: un personaje no
# tiene dos colores de ojos.
_ATRIBUTOS_UNICOS = (
    "color de ojos", "color de pelo", "edad", "altura", "mano dominante",
    "lugar de nacimiento", "oficio", "cicatriz",
)


def _atributo_y_valor(enunciado: str) -> tuple[str | None, str | None]:
    texto = normalizar(enunciado)
    for atributo in _ATRIBUTOS_UNICOS:
        clave = normalizar(atributo)
        if clave in texto:
            resto = texto.split(clave, 1)[1].strip()
            for particula in ("es ", "son ", "de ", "tiene "):
                if resto.startswith(particula):
                    resto = resto[len(particula):]
            return clave, resto or None
    return None, None


def _figuras_documentadas(proyecto: Proyecto) -> list[str]:
    carpeta = proyecto.almacen.raiz / "contexto" / "figuras_reales"
    if not carpeta.exists():
        return []
    return [fichero.stem for fichero in carpeta.glob("*.json")]
