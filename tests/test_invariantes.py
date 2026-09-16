"""Nivel unitario determinista: las invariantes de la seccion 6.3.

Criterio de la seccion 12: cobertura completa de las invariantes, **cada una con
su caso que falla**. Una invariante probada solo con el caso que pasa no esta
probada: no se ha demostrado que rechace nada.
"""

from __future__ import annotations

import pytest
from conftest import encargo_minimo, plan_minimo

from storymaker.invariantes import (
    comprobar_contexto,
    comprobar_derivacion_restriccion,
    comprobar_encargo,
    comprobar_plan,
    comprobar_terminacion,
)


def requisitos(fallos) -> set[str]:
    return {f.requisito for f in fallos}


# ==========================================================================
# Encargo
# ==========================================================================


def test_encargo_minimo_valido_no_tiene_incumplimientos():
    assert comprobar_encargo(encargo_minimo()) == []


def test_encargo_rechaza_semilla_vacia():
    encargo = encargo_minimo(semillas=[{"tipo": "personaje", "texto_literal": "   "}])
    assert "RF-001" in requisitos(comprobar_encargo(encargo))


def test_encargo_rechaza_epoca_sin_rango():
    encargo = encargo_minimo(epoca={"precision": "siglo"})
    assert "RF-003" in requisitos(comprobar_encargo(encargo))


def test_encargo_rechaza_parametro_de_estilo_sin_estado_declarado():
    """RF-029: el vacio silencioso no es un estado admitido."""
    guia = dict(encargo_minimo()["guia_estilo"])
    guia["registro"] = None
    assert "RF-029" in requisitos(comprobar_encargo(encargo_minimo(guia_estilo=guia)))


def test_encargo_rechaza_incompatibilidad_sin_arbitraje():
    encargo = encargo_minimo(incompatibilidades=[
        {"descripcion": "la extension no cuadra", "resuelta": False, "aceptada_por_autor": False}
    ])
    assert "RF-007" in requisitos(comprobar_encargo(encargo))


def test_encargo_admite_tension_aceptada_por_el_autor():
    encargo = encargo_minimo(incompatibilidades=[
        {"descripcion": "estilo telegrafico y novela larga", "resuelta": False, "aceptada_por_autor": True}
    ])
    assert comprobar_encargo(encargo) == []


# ==========================================================================
# Plan de Canon
# ==========================================================================


def test_plan_minimo_cumple_las_ocho_invariantes():
    assert comprobar_plan(plan_minimo(), encargo_minimo(), ["fig_cualquiera"]) == []


def test_plan_rechaza_referencia_a_hilo_inexistente():
    plan = plan_minimo()
    plan["capitulos"][0]["escenas"][0]["hilos"] = ["hil_que-no-existe"]
    assert "RF-020" in requisitos(comprobar_plan(plan, encargo_minimo()))


def test_plan_rechaza_presupuestos_que_no_suman_la_extension():
    plan = plan_minimo()
    plan["capitulos"][0]["escenas"][0]["presupuesto_palabras"] = 50
    assert "RF-023" in requisitos(comprobar_plan(plan, encargo_minimo()))


def test_plan_rechaza_hilo_sin_resolucion():
    plan = plan_minimo()
    plan["hilos"][0]["escena_resolucion"] = None
    assert "RF-021" in requisitos(comprobar_plan(plan, encargo_minimo()))


def test_plan_admite_hilo_abierto_si_el_autor_lo_autorizo():
    """RNF-002 admite una sola excepcion, y es explicita."""
    plan = plan_minimo()
    plan["hilos"][0]["escena_resolucion"] = None
    encargo = encargo_minimo(hilos_abiertos_autorizados=["hil_el-mapa-falso"])
    assert "RF-021" not in requisitos(comprobar_plan(plan, encargo))


def test_plan_rechaza_revelacion_anterior_a_quien_actua_sin_saberla():
    plan = plan_minimo()
    plan["revelaciones"][0]["escena"] = "esc_001_001"
    plan["revelaciones"][0]["escenas_actuando_sin_saberlo"] = ["esc_002_001"]
    plan["capitulos"][0]["escenas"][0]["revelaciones"] = ["rev_el-mapa-es-falso"]
    plan["capitulos"][1]["escenas"][1]["revelaciones"] = []
    assert "RF-025" in requisitos(comprobar_plan(plan, encargo_minimo()))


def test_plan_rechaza_personaje_en_dos_lugares_a_la_vez():
    plan = plan_minimo()
    plan["lugares"].append({"id": "lug_puerto", "nombre": "El puerto", "naturaleza": "ficticio"})
    plan["capitulos"][1]["escenas"][0]["momento"] = "1560-03-01"
    plan["capitulos"][1]["escenas"][0]["lugar"] = "lug_puerto"
    assert "RF-024" in requisitos(comprobar_plan(plan, encargo_minimo()))


def test_plan_rechaza_escena_que_no_avanza_nada():
    plan = plan_minimo()
    plan["capitulos"][0]["escenas"][1]["hilos"] = []
    plan["capitulos"][0]["escenas"][1]["revelaciones"] = []
    assert "RF-023" in requisitos(comprobar_plan(plan, encargo_minimo()))


def test_plan_rechaza_escena_sin_funcion_narrativa():
    plan = plan_minimo()
    plan["capitulos"][0]["escenas"][0]["funcion_narrativa"] = ""
    assert "RF-023" in requisitos(comprobar_plan(plan, encargo_minimo()))


def test_plan_rechaza_personaje_historico_sin_ficha_documentada():
    plan = plan_minimo()
    plan["personajes"].append({
        "id": "per_felipe-ii", "nombre": "Felipe II", "tipo": "historico_real",
        "funcion_narrativa": "poder", "figura_real": "fig_felipe-ii",
    })
    assert "RF-022" in requisitos(comprobar_plan(plan, encargo_minimo(), []))


def test_plan_rechaza_extension_por_capitulo_que_no_cuadra():
    encargo = encargo_minimo(extension_por_capitulo={"valor_palabras": 5000, "unidad_origen": "palabras"})
    assert "D28" in requisitos(comprobar_plan(plan_minimo(), encargo))


# ==========================================================================
# Contexto historico
# ==========================================================================


def _contexto_valido():
    afirmaciones = [
        {
            "id": f"aff_{seccion}", "seccion": seccion, "enunciado": "x",
            "fuentes": ["fnt_a"], "fidelidad": "verificada", "estado": "vigente",
        }
        for seccion in (
            "indumentaria", "cultura_material", "organizacion_social",
            "mentalidad", "economia_y_trabajo",
        )
    ]
    refutaciones = [{
        "afirmacion_id": "aff_indumentaria", "veredicto": "confirmada",
        "fuentes_contrarias": [], "consultas": [{"consulta": "contra x", "resultados_examinados": 5}],
    }]
    restricciones = [{
        "id": "rst_1", "enunciado": "no aparece el termino 'reloj de pulsera'",
        "categoria": "lexica", "afirmacion_id": "aff_indumentaria",
        "comprobable": True, "estado": "vigente",
    }]
    return {"lagunas": []}, afirmaciones, refutaciones, restricciones


def test_contexto_valido_no_tiene_incumplimientos():
    cabecera, afirmaciones, refutaciones, restricciones = _contexto_valido()
    assert comprobar_contexto(cabecera, afirmaciones, refutaciones, restricciones) == []


def test_contexto_rechaza_seccion_obligatoria_vacia_sin_laguna():
    cabecera, afirmaciones, refutaciones, restricciones = _contexto_valido()
    afirmaciones = [a for a in afirmaciones if a["seccion"] != "mentalidad"]
    fallos = comprobar_contexto(cabecera, afirmaciones, refutaciones, restricciones)
    assert "RF-014" in requisitos(fallos)


def test_contexto_admite_seccion_vacia_declarada_como_laguna_con_impacto():
    cabecera, afirmaciones, refutaciones, restricciones = _contexto_valido()
    afirmaciones = [a for a in afirmaciones if a["seccion"] != "mentalidad"]
    cabecera = {"lagunas": [{"seccion": "mentalidad", "impacto": "sin efecto sobre la trama"}]}
    assert "RF-014" not in requisitos(
        comprobar_contexto(cabecera, afirmaciones, refutaciones, restricciones)
    )


def test_contexto_rechaza_laguna_sin_impacto_evaluado():
    cabecera, afirmaciones, refutaciones, restricciones = _contexto_valido()
    afirmaciones = [a for a in afirmaciones if a["seccion"] != "mentalidad"]
    cabecera = {"lagunas": [{"seccion": "mentalidad"}]}
    assert "RF-014" in requisitos(
        comprobar_contexto(cabecera, afirmaciones, refutaciones, restricciones)
    )


def test_contexto_rechaza_afirmacion_en_alcance_sin_veredicto():
    cabecera, afirmaciones, _, restricciones = _contexto_valido()
    assert "RF-102" in requisitos(comprobar_contexto(cabecera, afirmaciones, [], restricciones))


def test_contexto_rechaza_fuente_contraria_que_es_la_propia_fuente():
    cabecera, afirmaciones, refutaciones, restricciones = _contexto_valido()
    refutaciones[0]["veredicto"] = "refutada"
    refutaciones[0]["fuentes_contrarias"] = ["fnt_a"]
    fallos = comprobar_contexto(cabecera, afirmaciones, refutaciones, restricciones)
    assert "RF-102" in requisitos(fallos)


def test_contexto_rechaza_refutacion_sin_consultas():
    cabecera, afirmaciones, refutaciones, restricciones = _contexto_valido()
    refutaciones[0]["consultas"] = []
    assert "RF-102" in requisitos(
        comprobar_contexto(cabecera, afirmaciones, refutaciones, restricciones)
    )


def test_contexto_rechaza_figura_referenciada_sin_ficha():
    cabecera, afirmaciones, refutaciones, restricciones = _contexto_valido()
    fallos = comprobar_contexto(
        cabecera, afirmaciones, refutaciones, restricciones, [], ["fig_felipe-ii"]
    )
    assert "RF-022" in requisitos(fallos)


# ==========================================================================
# MD-7: de que puede derivarse una Restriccion
# ==========================================================================


@pytest.mark.parametrize("veredicto", ["refutada", "disputada", "no_refutable_documentalmente"])
def test_restriccion_comprobable_no_deriva_de_veredicto_que_no_la_sostiene(veredicto):
    afirmaciones = {"aff_1": {"id": "aff_1", "fidelidad": "verificada", "estado": "vigente"}}
    refutaciones = {"aff_1": {"veredicto": veredicto}}
    restriccion = {
        "id": "rst_1", "categoria": "material", "afirmacion_id": "aff_1", "comprobable": True
    }
    assert comprobar_derivacion_restriccion(restriccion, afirmaciones, refutaciones)


def test_restriccion_cualitativa_si_deriva_de_no_refutable_documentalmente():
    """El veredicto no es una confirmacion, pero si admite criterio cualitativo."""
    afirmaciones = {"aff_1": {"id": "aff_1", "fidelidad": "no_verificable", "estado": "vigente"}}
    refutaciones = {"aff_1": {"veredicto": "no_refutable_documentalmente"}}
    restriccion = {
        "id": "rst_1", "categoria": "mentalidad", "afirmacion_id": "aff_1", "comprobable": False
    }
    assert comprobar_derivacion_restriccion(restriccion, afirmaciones, refutaciones) == []


def test_restriccion_comprobable_no_deriva_de_fidelidad_no_verificada():
    afirmaciones = {"aff_1": {"id": "aff_1", "fidelidad": "no_sostenida", "estado": "vigente"}}
    refutaciones = {"aff_1": {"veredicto": "confirmada"}}
    restriccion = {
        "id": "rst_1", "categoria": "lexica", "afirmacion_id": "aff_1", "comprobable": True
    }
    fallos = comprobar_derivacion_restriccion(restriccion, afirmaciones, refutaciones)
    assert "RF-100" in requisitos(fallos)


# ==========================================================================
# Terminacion (RF-077)
# ==========================================================================


def test_terminacion_exige_las_cinco_condiciones():
    plan = plan_minimo()
    fallos = comprobar_terminacion(
        plan, ["cap_001", "cap_002"], {"hil_el-mapa-falso": "resuelto"},
        0, True, 2000, encargo_minimo(),
    )
    assert fallos == []


@pytest.mark.parametrize(
    "ajuste, requisito_esperado",
    [
        ({"capitulos_validados": ["cap_001"]}, "RF-077"),
        ({"estado_hilos": {"hil_el-mapa-falso": "avanzado"}}, "RNF-002"),
        ({"hallazgos_bloqueantes_abiertos": 1}, "INV-5"),
        ({"pasada_global_superada": False}, "RF-068"),
        ({"palabras_totales": 500}, "RNF-012"),
    ],
)
def test_terminacion_falla_si_falta_cualquiera(ajuste, requisito_esperado):
    parametros = {
        "plan": plan_minimo(),
        "capitulos_validados": ["cap_001", "cap_002"],
        "estado_hilos": {"hil_el-mapa-falso": "resuelto"},
        "hallazgos_bloqueantes_abiertos": 0,
        "pasada_global_superada": True,
        "palabras_totales": 2000,
        "encargo": encargo_minimo(),
    }
    parametros.update(ajuste)
    assert requisito_esperado in requisitos(comprobar_terminacion(**parametros))
