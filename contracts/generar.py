"""Genera los esquemas de contrato de la seccion 6.2.

Se escriben desde aqui en lugar de a mano porque los veinte contratos comparten
estructura -- el sobre comun, los identificadores, los enumerados del dominio -- y
mantener veinte ficheros sincronizados a mano es como se desincronizan.

    python contracts/generar.py

Los esquemas resultantes son los que `storymaker.esquemas.RegistroContratos` carga
en `contracts/<nombre>/v<mayor>.schema.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ.parent / "src"))

from storymaker.hallazgos import CAUSAS_RAIZ, ESTADOS, SEVERIDADES  # noqa: E402
from storymaker.invariantes import (  # noqa: E402
    CATEGORIAS_RESTRICCION,
    SECCIONES_OBLIGATORIAS,
    VEREDICTOS_REFUTACION,
)
from storymaker.ledger import EVENTOS  # noqa: E402

ID = {"type": "string", "pattern": "^[a-z]{3}_[a-z0-9][A-Za-z0-9_.-]*$"}
LISTA_ID = {"type": "array", "items": ID}
TEXTO = {"type": "string", "minLength": 1}
VERSION = {"type": "string", "pattern": "^\\d+\\.\\d+$"}
MOMENTO = {"type": "string", "format": "fecha-hora"}


def objeto(propiedades: dict, obligatorios: list[str], extra: bool = False, **resto) -> dict:
    return {
        "type": "object",
        "properties": propiedades,
        "required": obligatorios,
        "additionalProperties": extra,
        **resto,
    }


# --- El sobre comun --------------------------------------------------------

SOBRE = objeto(
    {
        "schema_version": VERSION,
        "contrato": {"type": "string", "pattern": "^CT-([1-9]|1[0-9]|20)R?$"},
        "emisor": TEXTO,
        "momento": MOMENTO,
        "proyecto": {"type": ["string", "null"]},
        "ejecucion": {"type": ["string", "null"]},
        "carga": {"type": "object"},
    },
    ["schema_version", "contrato", "emisor", "momento", "carga"],
)

# --- CT-1: E1 -> E2 --------------------------------------------------------

AMBITO_INVESTIGACION = objeto(
    {
        "epoca": objeto(
            {
                "desde": TEXTO,
                "hasta": TEXTO,
                "precision": {"enum": ["ano", "decada", "siglo", "periodo"]},
            },
            ["desde", "hasta"],
        ),
        "ambito_geografico": TEXTO,
        "premisa": TEXTO,
        "semillas": {
            "type": "array",
            "minItems": 1,
            "items": objeto(
                {
                    "tipo": {"enum": ["personaje", "epoca", "idea", "inspiracion"]},
                    "texto_literal": TEXTO,
                    "registrada_en": MOMENTO,
                },
                ["tipo", "texto_literal"],
            ),
        },
        "ejes_tematicos": {"type": "array", "items": TEXTO},
        "politica_figuras_reales": {"type": ["object", "null"]},
    },
    ["epoca", "ambito_geografico", "premisa", "semillas"],
)

# --- CT-2: E1 -> E3 --------------------------------------------------------

PARAMETRO_ESTILO = objeto(
    {
        "valor": {},
        "estado": {"enum": ["declarado", "sin_preferencia", "sin_decidir"]},
        "origen": {"type": "string"},
    },
    ["estado"],
    # RF-029: un parametro declarado trae valor; uno sin preferencia, no. La
    # condicional lo impone en el esquema en lugar de confiarlo a quien lo lea.
    **{
        "if": objeto({"estado": {"const": "declarado"}}, ["estado"], extra=True),
        "then": {"required": ["valor"]},
    },
)

ENCARGO = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "version": {"type": "integer", "minimum": 1},
        "estado": {"enum": ["abierto", "cerrado", "reabierto"]},
        "origen_captura": {"enum": ["conversacion", "fichero"]},
        "semillas": AMBITO_INVESTIGACION["properties"]["semillas"],
        "premisa": TEXTO,
        "epoca": AMBITO_INVESTIGACION["properties"]["epoca"],
        "ambito_geografico": TEXTO,
        "extension_objetivo_palabras": {"type": "integer", "exclusiveMinimum": 0},
        "tolerancia_extension": {"type": "number", "minimum": 0, "maximum": 1},
        "capitulos_objetivo": {"type": ["integer", "null"], "minimum": 1},
        "extension_por_capitulo": {
            "type": ["object", "null"],
            "properties": {
                "valor_palabras": {"type": "integer", "exclusiveMinimum": 0},
                "valor_origen": {"type": "number"},
                "unidad_origen": {"enum": ["palabras", "lineas"]},
                "palabras_por_linea": {"type": "number", "exclusiveMinimum": 0},
                "origen": {"type": "string"},
            },
            # D28: si vino en lineas, el factor aplicado es obligatorio. Sin el, la
            # cifra que el Autor dio no se puede reconstruir.
            "dependentRequired": {"unidad_origen": ["valor_palabras"]},
            "additionalProperties": False,
        },
        "guia_estilo": {
            "type": "object",
            "patternProperties": {"^[a-z_]+$": PARAMETRO_ESTILO},
            "additionalProperties": False,
        },
        "guia_estilo_hash": {"type": ["string", "null"]},
        "politica_hechos_sensibles": {"type": "object"},
        "politica_figuras_reales": {"type": "object"},
        "licencias_alcance_preautorizadas": {"type": "array", "items": {"type": "object"}},
        "hilos_abiertos_autorizados": LISTA_ID,
        "restricciones_autor": {"type": "array", "items": TEXTO},
        "incompatibilidades": {"type": "array", "items": {"type": "object"}},
        "ejes_tematicos": {"type": "array", "items": TEXTO},
        "titulo_provisional": {"type": "string"},
        "confirmado_por": TEXTO,
        "confirmado_en": MOMENTO,
        "creado_en": MOMENTO,
        "campos_sin_preferencia": {"type": "array", "items": TEXTO},
        "rondas": {"type": "integer", "minimum": 0},
    },
    [
        "schema_version", "estado", "semillas", "premisa", "epoca",
        "ambito_geografico", "extension_objetivo_palabras", "guia_estilo",
        "politica_hechos_sensibles", "politica_figuras_reales",
    ],
)

# --- CT-3: E2 -> E3 --------------------------------------------------------

AFIRMACION = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "seccion": {
            "anyOf": [
                {"enum": list(SECCIONES_OBLIGATORIAS)},
                {"type": "string", "pattern": "^otra:"},
            ]
        },
        "enunciado": TEXTO,
        "tipo_afirmacion": {
            "enum": [
                "existencial_negativa", "existencial_positiva", "datacion",
                "atribucion", "cuantitativa", "cualitativa",
            ]
        },
        "fuentes": LISTA_ID,
        "sin_fuente": {"type": "boolean"},
        "fidelidad": {"enum": ["pendiente", "verificada", "no_sostenida", "no_verificable"]},
        "fidelidad_motivo": {"type": "string"},
        "fidelidad_contenido_cotejado": {"type": "string"},
        "fidelidad_verificada_en": MOMENTO,
        "refutacion_id": {"type": ["string", "null"]},
        "estado": {"enum": ["vigente", "refutada", "retirada"]},
        "disputada": {"type": "boolean"},
        "versiones_en_conflicto": {"type": "array", "items": {"type": "object"}},
        "certeza": {"enum": ["documentada", "inferida", "conocimiento_general"]},
        "origen": {"enum": ["inicial", "bajo_demanda"]},
        "creado_en": MOMENTO,
    },
    ["schema_version", "id", "seccion", "enunciado", "fuentes", "sin_fuente",
     "fidelidad", "estado"],
)

REFUTACION = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "afirmacion_id": ID,
        "veredicto": {"enum": list(VEREDICTOS_REFUTACION)},
        "tipo_afirmacion": AFIRMACION["properties"]["tipo_afirmacion"],
        "fuentes_contrarias": LISTA_ID,
        "consultas": {
            "type": "array",
            "minItems": 1,
            "items": objeto(
                {
                    "consulta": TEXTO,
                    "modo": {"enum": ["web", "rag"]},
                    "resultados_examinados": {"type": "integer", "minimum": 0},
                    "motivo_descarte": {"type": "string"},
                },
                ["consulta", "resultados_examinados"],
            ),
        },
        "alcance_matiz": {"type": ["string", "null"]},
        "emitida_en": MOMENTO,
    },
    ["schema_version", "afirmacion_id", "veredicto", "tipo_afirmacion", "consultas"],
    # Condicional del contrato: un matiz sin alcance declarado no dice nada.
    **{
        "if": objeto({"veredicto": {"const": "matizada"}}, ["veredicto"], extra=True),
        "then": {"required": ["alcance_matiz"]},
    },
)

RESTRICCION = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "enunciado": TEXTO,
        "categoria": {"enum": list(CATEGORIAS_RESTRICCION)},
        "afirmacion_id": ID,
        "comprobable": {"type": "boolean"},
        "terminos_prohibidos": {"type": "array", "items": TEXTO},
        "severidad_incumplimiento": {"enum": list(SEVERIDADES)},
        "estado": {"enum": ["vigente", "revocada"]},
        "justificacion_revocacion": {"type": "string"},
        "derivada_en": MOMENTO,
        "revocada_en": MOMENTO,
    },
    ["schema_version", "id", "enunciado", "categoria", "afirmacion_id", "comprobable", "estado"],
)

FUENTE = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "tipo": {"enum": ["web", "rag"]},
        "localizador": TEXTO,
        "consultada_en": MOMENTO,
        "fiabilidad": {"type": "string"},
        "contenido_id": {"type": ["string", "null"]},
        "contenido_sha256": {"type": "string", "format": "sha256"},
        "motivo_no_conservable": {"type": ["string", "null"]},
    },
    ["schema_version", "id", "tipo", "localizador", "consultada_en"],
)

CONTEXTO_HISTORICO = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "version": {"type": "integer", "minimum": 1},
        "estado": {"enum": ["vacio", "en_elaboracion", "completo", "ampliado"]},
        "afirmaciones": {"type": "array", "items": AFIRMACION},
        "refutaciones": {"type": "array", "items": REFUTACION},
        "restricciones": {"type": "array", "items": RESTRICCION},
        "fuentes": {"type": "array", "items": FUENTE},
        "figuras_reales": {"type": "array", "items": {"type": "object"}},
        "lagunas": {
            "type": "array",
            "items": objeto(
                {"seccion": TEXTO, "impacto": TEXTO, "motivo": {"type": "string"},
                 "declarada_en": MOMENTO},
                ["seccion", "impacto"],  # una laguna sin impacto no cumple RF-014
            ),
        },
        "cobertura_reducida": {"type": ["string", "null"]},
        "indicadores": {"type": "object"},
        "creado_en": MOMENTO,
    },
    ["schema_version", "estado", "lagunas"],
)

# --- CT-4 y CT-6: el plan de Canon -----------------------------------------

ESCENA_PLAN = objeto(
    {
        "id": ID,
        "orden": {"type": "integer", "minimum": 1},
        "funcion_narrativa": TEXTO,
        "personajes": LISTA_ID,
        "lugar": {"type": ["string", "null"]},
        "momento": {"type": ["string", "null"]},
        "hilos": LISTA_ID,
        "revelaciones": LISTA_ID,
        "presupuesto_palabras": {"type": "integer", "exclusiveMinimum": 0},
    },
    ["id", "orden", "funcion_narrativa", "presupuesto_palabras"],
)

CANON_PLAN = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "version": {"type": "integer", "minimum": 1},
        "estado": {"enum": ["borrador", "en_validacion", "aprobado", "superado"]},
        "version_anterior": {"type": ["string", "null"]},
        "superada_por": {"type": ["string", "null"]},
        "motivo_cambio": {"type": ["string", "null"]},
        "origen_cambio": {"type": ["string", "null"]},
        "arco": TEXTO,
        "hilos": {
            "type": "array",
            "items": objeto(
                {
                    "id": ID, "pregunta": TEXTO,
                    "escena_apertura": {"type": ["string", "null"]},
                    "escenas_avance": LISTA_ID,
                    "escena_resolucion": {"type": ["string", "null"]},
                },
                ["id", "pregunta"],
            ),
        },
        "personajes": {
            "type": "array",
            "items": objeto(
                {
                    "id": ID, "nombre": TEXTO,
                    "tipo": {"enum": ["ficticio", "historico_real"]},
                    "funcion_narrativa": TEXTO,
                    "rasgos": {"type": "array", "items": TEXTO},
                    "voz": {"type": "string"},
                    "arco": {"type": "string"},
                    "conocimiento_inicial": {"type": "array", "items": TEXTO},
                    "figura_real": {"type": ["string", "null"]},
                },
                ["id", "nombre", "tipo", "funcion_narrativa"],
                # RF-022: un personaje historico real sin ficha no es admisible.
                **{
                    "if": objeto({"tipo": {"const": "historico_real"}}, ["tipo"], extra=True),
                    "then": {"required": ["figura_real"]},
                },
            ),
        },
        "facciones": {"type": "array", "items": {"type": "object"}},
        "lugares": {"type": "array", "items": {"type": "object"}},
        "linea_temporal": {"type": "array", "items": {"type": "object"}},
        "revelaciones": {
            "type": "array",
            "items": objeto(
                {
                    "id": ID, "informacion": TEXTO,
                    "escena": {"type": ["string", "null"]},
                    "ante": {"type": "array", "items": TEXTO},
                    "escenas_actuando_sin_saberlo": LISTA_ID,
                },
                ["id", "informacion"],
            ),
        },
        "capitulos": {
            "type": "array",
            "minItems": 1,
            "items": objeto(
                {
                    "id": ID, "orden": {"type": "integer", "minimum": 1},
                    "titulo": {"type": "string"},
                    "escenas": {"type": "array", "minItems": 1, "items": ESCENA_PLAN},
                },
                ["id", "orden", "escenas"],
            ),
        },
        "licencias_alcance": {"type": "array", "items": {"type": "object"}},
        "capitulos_invalidados": LISTA_ID,
        "aprobado_por": {
            "type": ["object", "null"],
            "properties": {
                "modo": {"enum": ["agente", "humano"]},
                "quien": TEXTO,
                "decidido_en": MOMENTO,
                "bloqueantes_asumidos": {"type": "array", "items": {"type": "string"}},
                "motivo_asuncion": {"type": ["string", "null"]},
            },
            "required": ["modo", "quien"],
            "additionalProperties": False,
        },
        "encargo_version": {"type": ["string", "null"]},
        "contexto_version": {"type": ["string", "null"]},
        "creado_en": MOMENTO,
    },
    # Lo obligatorio es lo que el agente de diseno posee: el contenido narrativo.
    # `schema_version`, `id`, `version` y `estado` los estampa el nucleo al
    # persistir (MD-2), y exigirselos al agente seria pedirle que declare algo que
    # no decide el.
    ["arco", "hilos", "personajes", "capitulos", "revelaciones"],
)

CANON_APROBADO = objeto(
    {
        "schema_version": VERSION,
        "plan": CANON_PLAN,
        "version": ID,
        "licencias_alcance": {"type": "array", "items": {"type": "object"}},
        "guia_estilo_efectiva": objeto(
            {
                "declarados": {"type": "object"},
                "no_evaluables": {"type": "array", "items": TEXTO},
                "hash": {"type": ["string", "null"]},
                "nota": {"type": "string"},
            },
            ["declarados", "no_evaluables"],
        ),
    },
    ["schema_version", "plan", "version", "guia_estilo_efectiva"],
)

# --- CT-5, CT-8, CT-11, CT-16: lotes de hallazgos --------------------------

HALLAZGO = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "unidad": TEXTO,
        "categoria": TEXTO,
        "elemento_senalado": {"type": "string"},
        "severidad": {"enum": list(SEVERIDADES)},
        "causa_raiz": {"enum": list(CAUSAS_RAIZ)},
        "etapa_destino": TEXTO,
        "descripcion": TEXTO,
        "accion_exigida": TEXTO,
        "evidencia": {"type": "string"},
        "localizacion": {"type": "object"},
        "estado": {"enum": list(ESTADOS)},
        "iteracion": {"type": "integer", "minimum": 1},
        "creado_en": MOMENTO,
        "motivo_transicion": {"type": "string"},
        "transicionado_en": MOMENTO,
        # CT-16: cada hallazgo global identifica al menos un capitulo afectado.
        "capitulo_destino": {"type": "string"},
    },
    ["unidad", "categoria", "severidad", "causa_raiz", "descripcion", "accion_exigida"],
    # Un bloqueante sin pasaje identificable no es accionable: CT-5 y CT-11 lo
    # exigen, y por eso esta en el esquema y no en un comentario.
    **{
        "if": objeto({"severidad": {"const": "bloqueante"}}, ["severidad"], extra=True),
        "then": {"required": ["localizacion"]},
    },
)

LOTE_HALLAZGOS = objeto(
    {
        "schema_version": VERSION,
        "emisor": TEXTO,
        "unidad": TEXTO,
        "iteracion": {"type": "integer", "minimum": 1},
        "hallazgos": {"type": "array", "items": HALLAZGO},
        "recomendacion": {"type": "string"},
    },
    ["schema_version", "emisor", "unidad", "hallazgos"],
)

# --- CT-7: version de escena -----------------------------------------------

ESCENA_VERSION = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "escena": ID,
        "capitulo": ID,
        "rama": TEXTO,
        "version": {"type": "integer", "minimum": 1},
        "texto_ref": TEXTO,
        "hash_texto": {"type": "string", "format": "sha256"},
        "palabras": {"type": "integer", "minimum": 0},
        "presupuesto_palabras": {"type": ["integer", "null"]},
        "canon_plan_version": ID,
        "guia_estilo_hash": {"type": ["string", "null"]},
        "udt_origen": TEXTO,
        "ejecucion": TEXTO,
        "iteracion": {"type": "integer", "minimum": 1},
        "protegido_palabras": {"type": "integer", "minimum": 0},
        "pasajes_protegidos": {"type": "array", "items": {"type": "object"}},
        "protecciones_reescritas": {"type": "array", "items": {"type": "object"}},
        "hallazgos_aplicados": {"type": "array", "items": {"type": "string"}},
        "revelaciones_portadas": LISTA_ID,
        "evaluacion": {"type": ["object", "null"]},
        "modo_cierre": {
            "type": ["string", "null"],
            "enum": [None, "convergencia", "estancamiento", "regresion", "agotamiento"],
        },
        "descartada": {"type": "boolean"},
        "cerrada_en": MOMENTO,
        "hallazgos_pendientes_al_cerrar": {"type": "array", "items": {"type": "string"}},
        "creado_en": MOMENTO,
        "notas_redactor": {"type": "string"},
    },
    ["schema_version", "id", "escena", "rama", "texto_ref", "hash_texto", "palabras",
     "canon_plan_version", "udt_origen", "protegido_palabras"],
)
# ADR-05: la vigencia vive solo en ramas.json. Que el campo este prohibido aqui es
# lo que impide que vuelva a haber dos fuentes de la misma verdad.
ESCENA_VERSION["properties"]["vigente"] = {"not": {}}

# --- CT-9, CT-10, CT-12/13, CT-14, CT-15, CT-17, CT-18 -------------------

PROPUESTA_REPLANIFICACION = objeto(
    {
        "schema_version": VERSION,
        "emisor": TEXTO,
        "motivo": TEXTO,
        "elementos_afectados": {"type": "array", "minItems": 1, "items": TEXTO},
        "impacto_estimado": TEXTO,
        "alternativa_sugerida": {"type": "string"},
    },
    ["schema_version", "emisor", "motivo", "elementos_afectados", "impacto_estimado"],
)

CAPITULO_PARA_VALIDAR = objeto(
    {
        "schema_version": VERSION,
        "capitulo": ID,
        "escenas_cerradas": {"type": "array", "minItems": 1, "items": ID},
        "extension_real": {"type": "integer", "minimum": 0},
        "presupuesto": {"type": "integer", "minimum": 0},
        "hash_texto": {"type": "string", "format": "sha256"},
        "fichas_escenas": {"type": "array", "items": ESCENA_PLAN},
        "hechos_emergentes": {"type": "array", "items": {"type": "object"}},
        "deuda_bucle_interno": {"type": "array", "items": {"type": "object"}},
    },
    ["schema_version", "capitulo", "escenas_cerradas", "extension_real", "hash_texto"],
)

SOLICITUD_INVESTIGACION = objeto(
    {
        "schema_version": VERSION,
        "id": ID,
        "emisor": TEXTO,
        "tema": TEXTO,
        "periodo": TEXTO,
        "ambito_geografico": TEXTO,
        "contexto_narrativo": {"type": "string"},
        "unidad": TEXTO,
    },
    ["schema_version", "emisor", "tema", "periodo", "ambito_geografico"],
)

RESPUESTA_INVESTIGACION = objeto(
    {
        "schema_version": VERSION,
        "solicitud_id": ID,
        "resultado": {"type": ["object", "null"]},
        "laguna_declarada": {"type": ["object", "null"]},
        "afirmaciones_nuevas": LISTA_ID,
        "restricciones_nuevas": LISTA_ID,
    },
    ["schema_version", "solicitud_id"],
    # O trae resultado, o declara laguna. Devolver ninguna de las dos cosas es lo
    # que permitiria al redactor inventar el dato, que es lo que RF-043 prohibe.
    **{
        "anyOf": [
            {"required": ["resultado"], "properties": {"resultado": {"type": "object"}}},
            {"required": ["laguna_declarada"], "properties": {"laguna_declarada": {"type": "object"}}},
        ]
    },
)

LOTE_HECHOS = objeto(
    {
        "schema_version": VERSION,
        "escena_origen": ID,
        "escena_version_origen": ID,
        "hechos": {
            "type": "array",
            "items": objeto(
                {
                    "enunciado": TEXTO,
                    "sujeto": TEXTO,
                    "tipo_sujeto": {"enum": ["personaje", "lugar", "objeto", "relacion", "promesa"]},
                },
                ["enunciado", "sujeto", "tipo_sujeto"],
            ),
        },
    },
    ["schema_version", "escena_origen", "escena_version_origen", "hechos"],
)

CAPITULO_VALIDADO = objeto(
    {
        "schema_version": VERSION,
        "capitulo": ID,
        "aprobado": {"const": True},  # CT-15 solo transporta capitulos aprobados
        "hash_texto": {"type": "string", "format": "sha256"},
        "momento": MOMENTO,
        "extension_real": {"type": "integer", "minimum": 0},
        "presupuesto": {"type": "integer", "minimum": 0},
        "recuento": objeto(
            {
                "bloqueante": {"type": "integer", "maximum": 0},  # cero, por contrato
                "mayor": {"type": "integer", "minimum": 0},
                "menor": {"type": "integer", "minimum": 0},
            },
            ["bloqueante", "mayor", "menor"],
        ),
        "hallazgos": {"type": "array", "items": {"type": "string"}},
        "enrutado": {"type": "object"},
        "pasajes_protegidos": {"type": "array", "items": {"type": "object"}},
    },
    ["schema_version", "capitulo", "aprobado", "hash_texto", "recuento"],
)

PAQUETE_ENTREGA = objeto(
    {
        "schema_version": VERSION,
        "generado_en": MOMENTO,
        "proyecto": {"type": "object"},
        "encargo": {"type": ["object", "null"]},
        "contexto_historico": {"type": "object"},
        "canon_final": {"type": ["object", "null"]},
        "licencias": {"type": "object"},
        "deuda_de_calidad": {"type": "array", "items": {"type": "object"}},
        "hallazgos": {"type": "array", "items": {"type": "object"}},
        "pasada_global": {"type": ["object", "null"]},
        "metricas_ejecucion": {"type": "object"},
    },
    ["schema_version", "generado_en", "proyecto", "encargo", "contexto_historico",
     "canon_final", "licencias", "deuda_de_calidad"],
)

EVENTO_LEDGER = objeto(
    {
        "schema_version": VERSION,
        "secuencia": {"type": "integer", "minimum": 1},
        "momento": MOMENTO,
        "tipo": {"enum": sorted(EVENTOS)},
        "proyecto": TEXTO,
        "ejecucion": TEXTO,
        "carga": {"type": "object"},
    },
    ["schema_version", "secuencia", "momento", "tipo", "proyecto", "ejecucion", "carga"],
)

ESQUEMAS = {
    "sobre": SOBRE,
    "ambito_investigacion": AMBITO_INVESTIGACION,
    "encargo": ENCARGO,
    "contexto_historico": CONTEXTO_HISTORICO,
    "canon_plan": CANON_PLAN,
    "canon_aprobado": CANON_APROBADO,
    "lote_hallazgos": LOTE_HALLAZGOS,
    "escena_version": ESCENA_VERSION,
    "propuesta_replanificacion": PROPUESTA_REPLANIFICACION,
    "capitulo_para_validar": CAPITULO_PARA_VALIDAR,
    "solicitud_investigacion": SOLICITUD_INVESTIGACION,
    "respuesta_investigacion": RESPUESTA_INVESTIGACION,
    "lote_hechos": LOTE_HECHOS,
    "capitulo_validado": CAPITULO_VALIDADO,
    "paquete_entrega": PAQUETE_ENTREGA,
    "evento_ledger": EVENTO_LEDGER,
}

# Que contrato de la seccion 6.2 usa cada esquema. Es la trazabilidad inversa:
# un esquema que no sirva a ningun contrato sobra, y un contrato sin esquema no
# se puede validar.
CONTRATOS = {
    "CT-1": "ambito_investigacion", "CT-2": "encargo", "CT-3": "contexto_historico",
    "CT-4": "canon_plan", "CT-5": "lote_hallazgos", "CT-6": "canon_aprobado",
    "CT-7": "escena_version", "CT-8": "lote_hallazgos",
    "CT-9": "propuesta_replanificacion", "CT-10": "capitulo_para_validar",
    "CT-11": "lote_hallazgos", "CT-12": "solicitud_investigacion",
    "CT-12R": "respuesta_investigacion", "CT-13": "solicitud_investigacion",
    "CT-13R": "respuesta_investigacion", "CT-14": "lote_hechos",
    "CT-15": "capitulo_validado", "CT-16": "lote_hallazgos",
    "CT-17": "paquete_entrega", "CT-18": "evento_ledger",
}


def main() -> None:
    for nombre, esquema in ESQUEMAS.items():
        contratos = sorted(ct for ct, e in CONTRATOS.items() if e == nombre)
        documento = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"storymaker/contracts/{nombre}/v1",
            "title": nombre,
            "description": (
                f"Contrato {', '.join(contratos)} de la Especificacion Tecnica 2.0, "
                "seccion 6.2." if contratos else "Estructura auxiliar."
            ),
            **esquema,
        }
        destino = RAIZ / nombre / "v1.schema.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(documento, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"escrito {destino.relative_to(RAIZ.parent)}")

    indice = RAIZ / "mapa_contratos.json"
    indice.write_text(
        json.dumps(CONTRATOS, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"escrito {indice.relative_to(RAIZ.parent)}")


if __name__ == "__main__":
    main()
