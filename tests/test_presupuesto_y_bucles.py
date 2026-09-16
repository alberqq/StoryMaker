"""Presupuestos (seccion 8) y terminacion de bucles (seccion 7.3).

Lo que aqui se prueba con mas insistencia es D24, los dos tramos de reserva. Es la
decision menos intuitiva de la especificacion y la que mas facil seria implementar
mal sin que nadie lo notara hasta el ultimo tercio de una novela de tres semanas.
"""

from __future__ import annotations

import pytest

from storymaker.bucles import (
    T1_CONVERGENCIA,
    T2_ESTANCAMIENTO,
    T3_REGRESION,
    T4_AGOTAMIENTO,
    T5_ESCALADO,
    Evaluacion,
    Iteracion,
    decidir,
    mejor_version,
)
from storymaker.hallazgos import (
    BLOQUEANTE,
    MAYOR,
    MENOR,
    Hallazgo,
    elevar_menores_acumulados,
    peso_total,
    severidad_canonica,
)
from storymaker.presupuesto import (
    TRAMO_FINAL,
    TRAMO_LIBRE,
    Consumo,
    Contabilidad,
    Estimacion,
    Presupuesto,
    en_ultimo_tercio,
)


def _presupuesto(**ajustes):
    base = dict(coste_total=100.0, segundos_total=3600.0, iteraciones_total=100)
    base.update(ajustes)
    return Presupuesto(**base)


def _hallazgo(severidad=BLOQUEANTE, elemento="x", categoria="contradiccion_canon"):
    return Hallazgo(
        unidad="esc_001_001", categoria=categoria, elemento_senalado=elemento,
        severidad=severidad, causa_raiz="redaccion",
        descripcion="d", accion_exigida="a",
    )


# ==========================================================================
# Los dos tramos de reserva (D24)
# ==========================================================================


def test_la_reserva_se_parte_en_dos_tramos_segun_los_valores_por_defecto():
    presupuesto = _presupuesto(iteraciones_total=100)
    assert presupuesto.reserva_total == 20      # 20 % del total
    assert presupuesto.reserva_libre == 12      # 60 % de la reserva
    assert presupuesto.reserva_final == 8       # 40 %, solo para el ultimo tercio
    assert presupuesto.iteraciones_repartidas == 80


def test_el_tramo_final_se_deniega_antes_del_ultimo_tercio():
    """No es un prestamo: una unidad anterior recibe una denegacion."""
    contabilidad = Contabilidad(_presupuesto())
    veredicto = contabilidad.admitir(
        "esc_010_001", Estimacion(iteraciones=1),
        tramo_solicitado=TRAMO_FINAL, en_ultimo_tercio=False,
    )
    assert not veredicto.admitida
    assert veredicto.codigo_error == "ERR-407"


def test_el_tramo_final_se_admite_dentro_del_ultimo_tercio():
    contabilidad = Contabilidad(_presupuesto())
    veredicto = contabilidad.admitir(
        "esc_038_001", Estimacion(iteraciones=1),
        tramo_solicitado=TRAMO_FINAL, en_ultimo_tercio=True,
    )
    assert veredicto.admitida


@pytest.mark.parametrize(
    "capitulo, total, esperado",
    [(1, 40, False), (26, 40, False), (27, 40, True), (40, 40, True), (1, 0, False)],
)
def test_frontera_del_ultimo_tercio(capitulo, total, esperado):
    assert en_ultimo_tercio(capitulo, total) is esperado


def test_una_unidad_no_agota_la_reserva_del_resto_de_la_novela():
    """Tope de tres iteraciones de reserva por unidad (10.1)."""
    contabilidad = Contabilidad(_presupuesto())
    contabilidad.registrar("cap_007", Consumo(iteraciones=3), tramo=TRAMO_LIBRE)
    veredicto = contabilidad.admitir(
        "cap_007", Estimacion(iteraciones=1), tramo_solicitado=TRAMO_LIBRE
    )
    assert not veredicto.admitida
    assert veredicto.codigo_error == "ERR-401"


# ==========================================================================
# Admision previa
# ==========================================================================


def test_la_admision_deniega_antes_de_gastar_cuando_el_coste_no_cabe():
    contabilidad = Contabilidad(_presupuesto(coste_total=1.0))
    veredicto = contabilidad.admitir("esc_001_001", Estimacion(coste=5.0))
    assert not veredicto.admitida
    assert veredicto.codigo_error == "ERR-404"


def test_el_primer_presupuesto_agotado_es_el_que_se_registra():
    """RF-072: se detiene con el primero, sin esperar a los demas."""
    contabilidad = Contabilidad(_presupuesto(segundos_total=10.0))
    veredicto = contabilidad.admitir(
        "esc_001_001", Estimacion(coste=1.0, segundos=100.0, iteraciones=1)
    )
    assert veredicto.codigo_error == "ERR-403"


def test_la_proyeccion_no_se_emite_antes_del_25_por_ciento_de_avance():
    contabilidad = Contabilidad(_presupuesto())
    contabilidad.registrar("esc_001_001", Consumo(coste=5.0))
    assert contabilidad.proyeccion(0.10) is None
    proyeccion = contabilidad.proyeccion(0.25)
    assert proyeccion is not None
    assert proyeccion["coste_proyectado"] == 20.0


def test_el_tope_de_solicitudes_de_investigacion_por_escena_se_impone():
    from storymaker.errores import ErrorStoryMaker

    contabilidad = Contabilidad(_presupuesto())
    contabilidad.registrar_solicitud_investigacion("esc_001_001")
    contabilidad.registrar_solicitud_investigacion("esc_001_001")
    with pytest.raises(ErrorStoryMaker) as fallo:
        contabilidad.registrar_solicitud_investigacion("esc_001_001")
    assert fallo.value.codigo == "ERR-405"


# ==========================================================================
# Terminacion de bucles
# ==========================================================================


def test_convergencia_cuando_no_quedan_bloqueantes_ni_mayores_sobre_el_umbral():
    iteraciones = [Iteracion(1, "esv_1", [_hallazgo(MENOR)])]
    decision = decidir(iteraciones)
    assert decision.modo == T1_CONVERGENCIA
    assert not decision.emite_deuda


def test_estancamiento_cuando_el_conjunto_ponderado_no_mejora():
    iteraciones = [
        Iteracion(1, "esv_1", [_hallazgo(BLOQUEANTE, "a")]),
        Iteracion(2, "esv_2", [_hallazgo(BLOQUEANTE, "b")]),
    ]
    decision = decidir(iteraciones)
    assert decision.modo == T2_ESTANCAMIENTO
    assert decision.emite_deuda


def test_estancamiento_por_reaparicion_de_un_hallazgo_resuelto():
    """RF-075, que solo funciona porque la identidad del hallazgo es estable."""
    vuelto = _hallazgo(BLOQUEANTE, "el reloj de pulsera", "anacronismo")
    iteraciones = [
        Iteracion(1, "esv_1", [_hallazgo(BLOQUEANTE, "a"), _hallazgo(BLOQUEANTE, "b")]),
        Iteracion(2, "esv_2", [vuelto]),
    ]
    decision = decidir(iteraciones, resueltos_previos=[vuelto.id])
    assert decision.modo == T2_ESTANCAMIENTO
    assert vuelto.id in decision.motivo


def test_la_identidad_del_hallazgo_sobrevive_a_que_cambie_el_enunciado():
    """El hash excluye el enunciado y los desplazamientos de caracter a proposito."""
    primero = Hallazgo(
        unidad="cap_003", categoria="anacronismo", elemento_senalado="reloj de pulsera",
        severidad=BLOQUEANTE, causa_raiz="redaccion",
        descripcion="El texto menciona un reloj de pulsera en 1560",
        accion_exigida="sustituir", localizacion={"desde": 120, "hasta": 140},
    )
    reaparecido = Hallazgo(
        unidad="cap_003", categoria="anacronismo", elemento_senalado="Reloj de Pulsera.",
        severidad=BLOQUEANTE, causa_raiz="redaccion",
        descripcion="Vuelve a aparecer el anacronismo del reloj",
        accion_exigida="sustituir de una vez", localizacion={"desde": 890, "hasta": 910},
    )
    assert primero.id == reaparecido.id


def test_regresion_cuando_la_evaluacion_empeora_y_se_revierte_a_la_mejor():
    rubrica = "rub_escena_v1"
    iteraciones = [
        Iteracion(1, "esv_1", [_hallazgo()], Evaluacion(rubrica, {"voz": 9.0})),
        Iteracion(2, "esv_2", [_hallazgo()], Evaluacion(rubrica, {"voz": 4.0})),
    ]
    decision = decidir(iteraciones)
    assert decision.modo == T3_REGRESION
    assert decision.version_conservada == "esv_1"


def test_agotamiento_cuando_se_acaba_el_presupuesto():
    iteraciones = [Iteracion(1, "esv_1", [_hallazgo()])]
    decision = decidir(iteraciones, presupuesto_agotado=True)
    assert decision.modo == T4_AGOTAMIENTO
    assert decision.emite_deuda


def test_el_escalado_no_cierra_la_unidad():
    """T5 detiene y eleva; no es un modo de cierre."""
    iteraciones = [Iteracion(1, "esv_1", [_hallazgo()])]
    decision = decidir(iteraciones, bloqueo_irresoluble=True, presupuesto_agotado=True)
    assert decision.modo == T5_ESCALADO
    assert not decision.emite_deuda
    assert decision.codigo_error == "ERR-705"


def test_la_evaluacion_con_historial_no_es_comparable():
    """SUP-023: un evaluador que arrastra contexto se ablanda segun avanza el bucle."""
    limpia = Evaluacion("rub_v1", {"voz": 8.0}, sin_historial=True)
    contaminada = Evaluacion("rub_v1", {"voz": 6.0}, sin_historial=False)
    assert not limpia.comparable_con(contaminada)


def test_la_regresion_no_se_declara_sobre_evaluaciones_no_comparables():
    iteraciones = [
        Iteracion(1, "esv_1", [_hallazgo()], Evaluacion("rub_v1", {"voz": 9.0})),
        Iteracion(2, "esv_2", [], Evaluacion("rub_v2", {"otro": 4.0})),
    ]
    decision = decidir(iteraciones)
    assert decision.modo == T1_CONVERGENCIA


def test_mejor_version_ignora_el_orden_de_generacion():
    rubrica = "rub_v1"
    iteraciones = [
        Iteracion(1, "esv_1", [], Evaluacion(rubrica, {"voz": 9.0})),
        Iteracion(2, "esv_2", [], Evaluacion(rubrica, {"voz": 3.0})),
    ]
    assert mejor_version(iteraciones) == "esv_1"


# ==========================================================================
# Severidad
# ==========================================================================


def test_un_agente_no_puede_rebajar_la_severidad_de_un_anacronismo():
    assert severidad_canonica("anacronismo", MENOR) == BLOQUEANTE


def test_un_agente_si_puede_elevar_la_severidad():
    """Elevar nunca relaja una puerta, asi que se admite."""
    assert severidad_canonica("adjetivo_mejorable", BLOQUEANTE) == BLOQUEANTE


def test_los_menores_acumulados_elevan_un_mayor_agregado():
    menores = [_hallazgo(MENOR, f"e{n}", "adjetivo_mejorable") for n in range(9)]
    agregado = elevar_menores_acumulados(menores, "cap_001", umbral=8)
    assert agregado is not None
    assert agregado.severidad == MAYOR
    assert agregado.fuerza_iteracion


def test_por_debajo_del_umbral_los_menores_no_fuerzan_iteracion():
    menores = [_hallazgo(MENOR, f"e{n}", "adjetivo_mejorable") for n in range(3)]
    assert elevar_menores_acumulados(menores, "cap_001", umbral=8) is None
    assert not any(h.fuerza_iteracion for h in menores)


def test_el_peso_ordena_bloqueante_sobre_mayor_sobre_menor():
    assert peso_total([_hallazgo(BLOQUEANTE)]) > peso_total(
        [_hallazgo(MAYOR, "a"), _hallazgo(MAYOR, "b")]
    )
