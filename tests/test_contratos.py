"""Nivel de contrato (seccion 12).

Criterio: **ningun esquema se da por bueno sin un caso que deba rechazar.**
Un esquema probado solo con datos validos no ha demostrado que valide nada.

Se prueban ademas los condicionales, que son donde un validador flojo pasa por
alto lo que importa: un veredicto `matizada` sin alcance, un personaje historico
sin ficha, una respuesta de investigacion que no trae ni resultado ni laguna.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import RAIZ, encargo_minimo, plan_minimo

from storymaker.esquemas import (
    SUPERFICIE_AGENTE,
    SUPERFICIE_ARTEFACTO,
    RegistroContratos,
    Validador,
)

CONTRATOS = RAIZ / "contracts"


@pytest.fixture(scope="module")
def registro() -> RegistroContratos:
    return RegistroContratos(CONTRATOS)


def test_todos_los_contratos_de_la_seccion_6_2_tienen_esquema(registro):
    mapa = json.loads((CONTRATOS / "mapa_contratos.json").read_text(encoding="utf-8"))
    esperados = [f"CT-{n}" for n in range(1, 21)] + ["CT-12R", "CT-13R"]
    assert sorted(mapa) == sorted(esperados)
    for contrato, nombre in mapa.items():
        assert registro.cargar(nombre), contrato


def test_un_contrato_sin_esquema_falla_al_cargarse(registro):
    from storymaker.errores import ErrorStoryMaker

    with pytest.raises(ErrorStoryMaker) as fallo:
        registro.cargar("contrato_que_no_existe")
    assert fallo.value.codigo == "ERR-505"


# ==========================================================================
# CT-2: Encargo
# ==========================================================================


def test_encargo_valido_pasa(registro):
    encargo = {"schema_version": "2.0", "estado": "cerrado", **encargo_minimo()}
    assert registro.validador("encargo").validar(encargo)


def test_encargo_sin_campo_obligatorio_se_rechaza(registro):
    encargo = {"schema_version": "2.0", "estado": "cerrado", **encargo_minimo()}
    del encargo["premisa"]
    resultado = registro.validador("encargo").validar(encargo)
    assert not resultado
    assert any("premisa" in p for p in resultado.problemas)


def test_encargo_con_campo_desconocido_se_rechaza_nombrandolo(registro):
    """RF-110: un campo desconocido no se ignora."""
    encargo = {"schema_version": "2.0", "estado": "cerrado", "invencion": 1, **encargo_minimo()}
    resultado = registro.validador("encargo").validar(encargo)
    assert not resultado
    assert any("invencion" in p for p in resultado.problemas)


def test_parametro_de_estilo_declarado_sin_valor_se_rechaza(registro):
    """RF-029, como condicional del esquema y no como nota al pie."""
    encargo = {"schema_version": "2.0", "estado": "cerrado", **encargo_minimo()}
    encargo["guia_estilo"]["registro"] = {"estado": "declarado"}
    assert not registro.validador("encargo").validar(encargo)


def test_extension_en_lineas_exige_el_valor_convertido(registro):
    """D28: sin el valor en palabras, la cifra del Autor no se reconstruye."""
    encargo = {"schema_version": "2.0", "estado": "cerrado", **encargo_minimo()}
    encargo["extension_por_capitulo"] = {"unidad_origen": "lineas", "valor_origen": 900}
    assert not registro.validador("encargo").validar(encargo)

    encargo["extension_por_capitulo"]["valor_palabras"] = 9000
    encargo["extension_por_capitulo"]["palabras_por_linea"] = 10
    assert registro.validador("encargo").validar(encargo)


# ==========================================================================
# CT-3: Contexto historico y refutacion
# ==========================================================================


def _contexto_valido() -> dict:
    return {
        "schema_version": "2.0",
        "estado": "completo",
        "lagunas": [],
        "refutaciones": [{
            "schema_version": "2.0",
            "afirmacion_id": "aff_abc123",
            "veredicto": "confirmada",
            "tipo_afirmacion": "datacion",
            "consultas": [{"consulta": "contra x", "resultados_examinados": 3}],
        }],
    }


def test_contexto_valido_pasa(registro):
    assert registro.validador("contexto_historico").validar(_contexto_valido())


def test_veredicto_matizada_sin_alcance_se_rechaza(registro):
    contexto = _contexto_valido()
    contexto["refutaciones"][0]["veredicto"] = "matizada"
    assert not registro.validador("contexto_historico").validar(contexto)


def test_veredicto_matizada_con_alcance_pasa(registro):
    contexto = _contexto_valido()
    contexto["refutaciones"][0]["veredicto"] = "matizada"
    contexto["refutaciones"][0]["alcance_matiz"] = "solo en talleres grandes"
    assert registro.validador("contexto_historico").validar(contexto)


def test_refutacion_sin_consultas_se_rechaza(registro):
    """Lo que impide que 'confirmada' signifique 'no se busco'."""
    contexto = _contexto_valido()
    contexto["refutaciones"][0]["consultas"] = []
    assert not registro.validador("contexto_historico").validar(contexto)


def test_laguna_sin_impacto_se_rechaza(registro):
    contexto = _contexto_valido()
    contexto["lagunas"] = [{"seccion": "mentalidad"}]
    assert not registro.validador("contexto_historico").validar(contexto)


def test_veredicto_inventado_se_rechaza(registro):
    contexto = _contexto_valido()
    contexto["refutaciones"][0]["veredicto"] = "medio_confirmada"
    assert not registro.validador("contexto_historico").validar(contexto)


# ==========================================================================
# CT-4: plan de Canon
# ==========================================================================


def _plan_valido() -> dict:
    return {"schema_version": "2.0", "estado": "borrador", **plan_minimo()}


def test_plan_valido_pasa(registro):
    resultado = registro.validador("canon_plan").validar(_plan_valido())
    assert resultado, resultado.problemas


def test_personaje_historico_real_sin_ficha_se_rechaza(registro):
    """RF-022, como condicional del esquema."""
    plan = _plan_valido()
    plan["personajes"].append({
        "id": "per_felipe-ii", "nombre": "Felipe II",
        "tipo": "historico_real", "funcion_narrativa": "poder",
    })
    assert not registro.validador("canon_plan").validar(plan)


def test_plan_sin_capitulos_se_rechaza(registro):
    plan = _plan_valido()
    plan["capitulos"] = []
    assert not registro.validador("canon_plan").validar(plan)


def test_capitulo_sin_escenas_se_rechaza(registro):
    plan = _plan_valido()
    plan["capitulos"][0]["escenas"] = []
    assert not registro.validador("canon_plan").validar(plan)


def test_escena_con_presupuesto_cero_se_rechaza(registro):
    plan = _plan_valido()
    plan["capitulos"][0]["escenas"][0]["presupuesto_palabras"] = 0
    assert not registro.validador("canon_plan").validar(plan)


# ==========================================================================
# CT-7: version de escena
# ==========================================================================


def _version_escena() -> dict:
    return {
        "schema_version": "2.0",
        "id": "esv_001_001_v1",
        "escena": "esc_001_001",
        "rama": "principal",
        "texto_ref": "esv_001_001_v1.md",
        "hash_texto": "a" * 64,
        "palabras": 500,
        "canon_plan_version": "can_abc_v1",
        "udt_origen": "udt_1",
        "es_piloto": False,
        "protegido_palabras": 0,
    }


def test_version_de_escena_valida_pasa(registro):
    assert registro.validador("escena_version").validar(_version_escena())


def test_una_version_de_escena_no_puede_declarar_su_propia_vigencia(registro):
    """ADR-05: la vigencia vive solo en ramas.json.

    Dos sitios que afirman lo mismo acaban divergiendo, y aqui no hay
    transacciones que lo impidan. Por eso el campo esta prohibido por esquema.
    """
    version = _version_escena()
    version["vigente"] = True
    assert not registro.validador("escena_version").validar(version)


def test_hash_de_texto_mal_formado_se_rechaza(registro):
    version = _version_escena()
    version["hash_texto"] = "no-es-un-sha256"
    assert not registro.validador("escena_version").validar(version)


def test_modo_de_cierre_inventado_se_rechaza(registro):
    version = _version_escena()
    version["modo_cierre"] = "porque_si"
    assert not registro.validador("escena_version").validar(version)


# ==========================================================================
# CT-5, CT-11: lotes de hallazgos
# ==========================================================================


def _lote() -> dict:
    return {
        "schema_version": "2.0",
        "emisor": "sm-validador",
        "unidad": "cap_001",
        "hallazgos": [{
            "unidad": "cap_001", "categoria": "anacronismo",
            "severidad": "bloqueante", "causa_raiz": "redaccion",
            "descripcion": "aparece un reloj de pulsera",
            "accion_exigida": "sustituir",
            "localizacion": {"escena": "esc_001_001", "fragmento": "el reloj"},
        }],
    }


def test_lote_de_hallazgos_valido_pasa(registro):
    assert registro.validador("lote_hallazgos").validar(_lote())


def test_bloqueante_sin_localizacion_se_rechaza(registro):
    """CT-5 y CT-11: todo bloqueante localiza el elemento responsable."""
    lote = _lote()
    del lote["hallazgos"][0]["localizacion"]
    assert not registro.validador("lote_hallazgos").validar(lote)


def test_causa_raiz_fuera_de_las_cinco_se_rechaza(registro):
    lote = _lote()
    lote["hallazgos"][0]["causa_raiz"] = "el_universo"
    assert not registro.validador("lote_hallazgos").validar(lote)


# ==========================================================================
# CT-12R / CT-13R y CT-15
# ==========================================================================


def test_respuesta_de_investigacion_exige_resultado_o_laguna(registro):
    """Sin una de las dos, el redactor se quedaria libre para inventar (RF-043)."""
    validador = registro.validador("respuesta_investigacion")
    assert not validador.validar({"schema_version": "2.0", "solicitud_id": "sol_00001"})
    assert validador.validar({
        "schema_version": "2.0", "solicitud_id": "sol_00001",
        "laguna_declarada": {"seccion": "cultura_material", "impacto": "menor"},
    })
    assert validador.validar({
        "schema_version": "2.0", "solicitud_id": "sol_00001",
        "resultado": {"afirmaciones": []},
    })


def test_capitulo_validado_no_transporta_bloqueantes(registro):
    """CT-15: el contrato solo admite capitulos sin bloqueantes abiertos."""
    validador = registro.validador("capitulo_validado")
    base = {
        "schema_version": "2.0", "capitulo": "cap_001", "aprobado": True,
        "hash_texto": "b" * 64,
        "recuento": {"bloqueante": 0, "mayor": 1, "menor": 3},
    }
    assert validador.validar(base)
    base["recuento"]["bloqueante"] = 1
    assert not validador.validar(base)


def test_capitulo_no_aprobado_no_cabe_en_ct_15(registro):
    validador = registro.validador("capitulo_validado")
    assert not validador.validar({
        "schema_version": "2.0", "capitulo": "cap_001", "aprobado": False,
        "hash_texto": "b" * 64, "recuento": {"bloqueante": 0, "mayor": 0, "menor": 0},
    })


# ==========================================================================
# CT-20: decision sobre el piloto
# ==========================================================================


def test_decision_de_piloto_no_aceptada_identifica_que_debe_cambiar(registro):
    validador = registro.validador("decision_piloto")
    assert validador.validar({
        "schema_version": "2.0", "decision": "aceptar", "decidido_por": "autor",
    })
    assert not validador.validar({
        "schema_version": "2.0", "decision": "ajustar_estilo", "decidido_por": "autor",
    })
    assert validador.validar({
        "schema_version": "2.0", "decision": "ajustar_estilo",
        "decidido_por": "autor", "elemento_afectado": "persona_narrativa",
    })


# ==========================================================================
# CT-18: evento de ledger
# ==========================================================================


def test_evento_de_ledger_fuera_del_catalogo_se_rechaza(registro):
    validador = registro.validador("evento_ledger")
    base = {
        "schema_version": "2.0", "secuencia": 1, "momento": "2026-09-15T10:00:00Z",
        "tipo": "unidad_cerrada", "proyecto": "prj_x", "ejecucion": "eje_x", "carga": {},
    }
    assert validador.validar(base)
    base["tipo"] = "cosa_que_paso"
    assert not validador.validar(base)


# ==========================================================================
# La asimetria de la politica de campos desconocidos (seccion 6.1)
# ==========================================================================


def test_la_salida_de_un_agente_es_estricta_con_lo_desconocido():
    esquema = {"type": "object", "properties": {"a": {"type": "string"}}}
    estricto = Validador(esquema, SUPERFICIE_AGENTE)
    assert not estricto.validar({"a": "x", "campo_inventado": 1})


def test_un_artefacto_persistido_es_tolerante_al_leerlo():
    """Es lo que hace viable la promocion de esquema (ADR-06 regla 4)."""
    esquema = {"type": "object", "properties": {"a": {"type": "string"}}}
    tolerante = Validador(esquema, SUPERFICIE_ARTEFACTO)
    assert tolerante.validar({"a": "x", "campo_de_una_version_futura": 1})
