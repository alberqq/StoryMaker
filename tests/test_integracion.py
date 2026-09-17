"""Nivel de integracion: la novela minima de dos capitulos y cuatro escenas.

Criterio de la seccion 12: **termina por convergencia y produce entrega completa.**
No se llama a ningun modelo: el nucleo es determinista y los agentes solo proponen,
asi que una prueba del nucleo sustituye las propuestas por texto fijo y comprueba
que las puertas, la contabilidad y el versionado hacen lo que dicen.
"""

from __future__ import annotations

import pytest
from conftest import aprobar_canon, cerrar_encargo, plan_minimo, poblar_contexto

from storymaker.bucles import T1_CONVERGENCIA, Evaluacion, Iteracion, decidir
from storymaker.dominio import canon as d_canon
from storymaker.dominio import contexto as d_contexto
from storymaker.dominio import ejecucion as d_ejecucion
from storymaker.dominio import global_ as d_global
from storymaker.dominio import novela as d_novela
from storymaker.dominio import validacion as d_validacion
from storymaker.errores import ErrorStoryMaker
from storymaker.hallazgos import Hallazgo
from storymaker.presupuesto import Presupuesto
from storymaker.proyecto import FINALIZADO, FINALIZADO_CON_RESERVAS

TEXTO = " ".join(["palabra"] * 500)


def _cerrar_contexto(proyecto):
    identificadores = poblar_contexto(proyecto)
    afirmacion = identificadores["indumentaria"]
    d_contexto.verificar_fidelidad(
        proyecto, afirmacion, "verificada", contenido_cotejado="vitela y compas"
    )
    d_contexto.refutar(
        proyecto, afirmacion, "confirmada",
        tipo_afirmacion="existencial_positiva",
        consultas=[{
            "consulta": "vitela Amberes 1560 desmentido",
            "modo": "web",
            "resultados_examinados": 8,
            "motivo_descarte": "ninguno contradice la afirmacion",
        }],
    )
    d_contexto.derivar_restriccion(
        proyecto, "No aparece el termino 'boligrafo'", "lexica", afirmacion,
        terminos_prohibidos=["boligrafo"],
    )
    return d_contexto.cerrar(proyecto)




def _escribir_novela(proyecto):
    for id_escena in ("esc_001_001", "esc_001_002", "esc_002_001", "esc_002_002"):
        d_novela.escribir(
            proyecto, id_escena, TEXTO,
            id_unidad=f"udt_{id_escena}", ejecucion=proyecto.estado.ejecucion_activa,
            revelaciones_portadas=["rev_el-mapa-es-falso"] if id_escena == "esc_002_002" else [],
        )
        d_novela.cerrar_escena(proyecto, id_escena, T1_CONVERGENCIA)


def _validar_y_cerrar(proyecto):
    for id_capitulo in ("cap_001", "cap_002"):
        veredicto = d_validacion.validar(proyecto, id_capitulo)
        assert veredicto["aprobado"], veredicto
        d_validacion.cerrar_capitulo(
            proyecto, id_capitulo, f"Acta de {id_capitulo}: ocurrio lo previsto."
        )


@pytest.fixture
def novela_completa(proyecto):
    """Una novela minima llevada hasta el punto de poder cerrarse."""
    cerrar_encargo(proyecto)
    _cerrar_contexto(proyecto)
    aprobar_canon(proyecto)
    d_ejecucion.iniciar(
        proyecto, Presupuesto(coste_total=100.0, segundos_total=3600.0, iteraciones_total=40)
    )
    _escribir_novela(proyecto)
    _validar_y_cerrar(proyecto)
    return proyecto


def test_novela_minima_termina_por_convergencia_y_entrega(novela_completa):
    proyecto = novela_completa

    informe = d_global.pasada_global(proyecto)
    assert informe["superada"], informe
    assert informe["hilos"]["sin_resolver"] == []

    cierre = d_global.cerrar_novela(proyecto)
    assert cierre["finalizada"], cierre
    assert cierre["estado"] == FINALIZADO

    entrega = d_global.generar_entrega(proyecto, con_pdf=False)
    assert entrega["formatos"]["markdown"]["ok"]
    assert entrega["palabras"] == 2000

    paquete = d_global.paquete_trazabilidad(proyecto)
    for clave in ("encargo", "contexto_historico", "canon_final", "licencias", "deuda_de_calidad"):
        assert clave in paquete


def test_lo_que_queda_abierto_al_cerrar_se_declara_como_deuda(novela_completa):
    """La pasada global es la ultima etapa: sus hallazgos no tienen quien los corrija.

    Antes se quedaban abiertos para siempre en un fichero que no miraba nadie, y la
    novela se entregaba como *finalizada* igual. Ahora se barren a la Deuda de
    calidad y el Proyecto queda limitado a reservas, que es lo que la Deuda
    significa: se entrega, pero se dice con que se entrega.
    """
    proyecto = novela_completa
    d_validacion.registrar_hallazgos(proyecto, [
        Hallazgo(
            unidad="novela", categoria="repeticion_larga_distancia",
            elemento_senalado="per_joos-van-der-beke", severidad="menor",
            causa_raiz="refinamiento", descripcion="la misma imagen cierra dos escenas",
            accion_exigida="variar una de las dos",
        ),
        Hallazgo(
            unidad="novela", categoria="ritmo",
            elemento_senalado="cap_002", severidad="mayor",
            causa_raiz="diseno", descripcion="el salto temporal no se cubre",
            accion_exigida="anadir una transicion",
        ),
    ])

    d_global.pasada_global(proyecto)
    cierre = d_global.cerrar_novela(proyecto)

    assert cierre["finalizada"], cierre
    assert cierre["estado"] == FINALIZADO_CON_RESERVAS
    deuda = cierre["deuda_de_calidad"]
    assert deuda["emitida"]
    assert len(deuda["hallazgos"]) == 2
    assert deuda["recuento_por_severidad"] == {"menor": 1, "mayor": 1}

    # El registro de hallazgos dice lo mismo que la Deuda: ninguno queda abierto.
    vigentes = {}
    for registro in proyecto.almacen.leer_jsonl(proyecto.almacen.hallazgos):
        vigentes[registro["id"]] = registro
    assert all(h["estado"] == "aceptado_como_deuda" for h in vigentes.values())

    # Y la Deuda esta en el paquete de trazabilidad, que es donde el Autor la lee.
    paquete = d_global.paquete_trazabilidad(proyecto)
    assert len(paquete["deuda_de_calidad"]) == 1


def test_sin_hallazgos_abiertos_la_novela_se_cierra_sin_reservas(novela_completa):
    """El caso que debe seguir pasando: barrer no puede inventar Deuda donde no la hay."""
    proyecto = novela_completa
    d_global.pasada_global(proyecto)
    cierre = d_global.cerrar_novela(proyecto)

    assert cierre["estado"] == FINALIZADO
    assert not cierre["deuda_de_calidad"]["emitida"]
    assert proyecto.almacen.leer_jsonl(proyecto.almacen.deudas) == []


def test_la_novela_no_se_cierra_si_falta_una_condicion(novela_completa):
    """RF-077 no admite aproximacion: o se cumplen las cinco, o no se cierra."""
    proyecto = novela_completa
    d_global.pasada_global(proyecto)
    cierre = d_global.cerrar_novela(proyecto, hallazgos_bloqueantes_abiertos=1)
    assert not cierre["finalizada"]
    assert any(f["requisito"] == "INV-5" for f in cierre["condiciones_que_faltan"])


def test_no_se_redacta_sobre_un_canon_no_aprobado(proyecto):
    """INV-1, comprobado en el nucleo ademas de en el hook."""
    cerrar_encargo(proyecto)
    _cerrar_contexto(proyecto)
    d_canon.proponer(proyecto, plan_minimo())
    with pytest.raises(ErrorStoryMaker) as fallo:
        d_novela.escribir(
            proyecto, "esc_001_001", TEXTO, id_unidad="udt_x", ejecucion="eje_x"
        )
    assert fallo.value.codigo == "ERR-502"




def test_el_ensamblado_aborta_si_falta_una_escena_vigente(proyecto):
    cerrar_encargo(proyecto)
    _cerrar_contexto(proyecto)
    aprobar_canon(proyecto)
    d_ejecucion.iniciar(
        proyecto, Presupuesto(coste_total=10.0, segundos_total=60.0, iteraciones_total=10)
    )
    d_novela.escribir(
        proyecto, "esc_001_001", TEXTO, id_unidad="udt_1",
        ejecucion=proyecto.estado.ejecucion_activa,
    )
    with pytest.raises(ErrorStoryMaker) as fallo:
        d_global.ensamblar(proyecto)
    assert fallo.value.codigo == "ERR-506"


def test_anacronismo_lexico_se_detecta_y_bloquea(proyecto):
    """RF-063: la parte comprobable se comprueba, no se juzga."""
    cerrar_encargo(proyecto)
    _cerrar_contexto(proyecto)
    aprobar_canon(proyecto)
    d_ejecucion.iniciar(
        proyecto, Presupuesto(coste_total=10.0, segundos_total=60.0, iteraciones_total=10)
    )
    texto = TEXTO + " y sacó su boligrafo del bolsillo"
    d_novela.escribir(
        proyecto, "esc_001_001", texto, id_unidad="udt_1",
        ejecucion=proyecto.estado.ejecucion_activa,
    )
    hallazgos = d_validacion.barrer_anacronismos_lexicos(proyecto, "cap_001")
    assert [h.categoria for h in hallazgos] == ["anacronismo"]
    assert hallazgos[0].severidad == "bloqueante"


def test_capitulo_rechazado_no_se_aprueba_sin_cambio_de_texto(novela_completa):
    """RF-067, que es la puerta mas facil de saltarse sin darse cuenta."""
    proyecto = novela_completa
    d_validacion.validar(
        proyecto, "cap_001",
        hallazgos_del_agente=[Hallazgo(
            unidad="cap_001", categoria="contradiccion_canon",
            elemento_senalado="per_joos-van-der-beke", severidad="bloqueante",
            causa_raiz="redaccion", descripcion="contradice el Canon",
            accion_exigida="corregir",
        )],
    )
    with pytest.raises(ErrorStoryMaker) as fallo:
        d_validacion.validar(proyecto, "cap_001")
    assert fallo.value.codigo == "ERR-704"


def test_hecho_contradictorio_se_rechaza_con_bloqueante(novela_completa):
    """Regla 3 de la seccion 5.3."""
    proyecto = novela_completa
    d_canon.anexar_hecho(
        proyecto, "El color de ojos es gris", "per_joos-van-der-beke",
        "personaje", "esc_001_001", "esv_001_001_v1",
    )
    with pytest.raises(ErrorStoryMaker) as fallo:
        d_canon.anexar_hecho(
            proyecto, "El color de ojos es pardo", "per_joos-van-der-beke",
            "personaje", "esc_002_001", "esv_002_001_v1",
        )
    assert fallo.value.codigo == "ERR-601"


def test_anexar_el_mismo_hecho_dos_veces_es_idempotente(novela_completa):
    """Regla 1 de la seccion 5.3: permite reintentar una unidad sin ensuciar el libro."""
    proyecto = novela_completa
    primero = d_canon.anexar_hecho(
        proyecto, "El taller huele a cola de conejo", "lug_taller",
        "lugar", "esc_001_001", "esv_001_001_v1",
    )
    segundo = d_canon.anexar_hecho(
        proyecto, "El taller huele a cola de conejo", "lug_taller",
        "lugar", "esc_001_001", "esv_001_001_v1",
    )
    assert primero["anexado"] is True
    assert segundo["anexado"] is False
    assert segundo["hecho"]["id"] == primero["hecho"]["id"]


def test_la_mejor_version_se_conserva_y_no_la_ultima(novela_completa):
    """INV-4 y RF-056."""
    proyecto = novela_completa
    segunda = d_novela.escribir(
        proyecto, "esc_001_001", TEXTO + " variante",
        id_unidad="udt_2", ejecucion=proyecto.estado.ejecucion_activa, iteracion=2,
    )["version_escena"]["id"]

    rubrica = "rub_escena_v1"
    resultado = d_novela.conservar_mejor(proyecto, "esc_001_001", {
        "esv_001_001_v1": Evaluacion(rubrica, {"voz": 8.0, "funcion": 9.0}),
        segunda: Evaluacion(rubrica, {"voz": 6.0, "funcion": 5.0}),
    })
    assert resultado["version_vigente"] == "esv_001_001_v1"
    assert d_novela.version_vigente(proyecto, "esc_001_001") == "esv_001_001_v1"


def test_pasaje_protegido_no_se_reescribe_sin_justificacion(novela_completa):
    """RF-054: evita la oscilacion entre refinador y redactor."""
    proyecto = novela_completa
    fragmento = "una frase que resolvio un bloqueante"
    d_novela.escribir(
        proyecto, "esc_001_002", f"{TEXTO} {fragmento}",
        id_unidad="udt_p", ejecucion=proyecto.estado.ejecucion_activa,
    )
    protegido = d_novela.proteger_pasaje(proyecto, "esc_001_002", fragmento, "hlz_ficticio")
    id_pasaje = protegido["version_escena"]["pasajes_protegidos"][-1]["id"]

    with pytest.raises(ErrorStoryMaker) as fallo:
        d_novela.refinar(
            proyecto, "esc_001_002", TEXTO,
            id_unidad="udt_p2", ejecucion=proyecto.estado.ejecucion_activa, iteracion=2,
        )
    assert fallo.value.codigo == "ERR-708"

    # Con justificacion registrada si pasa, y queda pendiente del validador.
    resultado = d_novela.refinar(
        proyecto, "esc_001_002", TEXTO,
        id_unidad="udt_p3", ejecucion=proyecto.estado.ejecucion_activa, iteracion=3,
        justificaciones_proteccion={id_pasaje: "el hallazgo se resolvio de otra forma"},
    )
    assert resultado["protecciones_reescritas"]


def test_la_sinopsis_de_un_capitulo_cerrado_no_se_reescribe(novela_completa):
    proyecto = novela_completa
    with pytest.raises(ErrorStoryMaker) as fallo:
        d_novela.escribir_sinopsis(proyecto, "cap_001", "otra acta distinta")
    assert fallo.value.codigo == "ERR-604"


def test_el_estado_de_hilos_se_recalcula_y_no_se_lee_del_indice(novela_completa):
    """MD-6: un indice puede estar obsoleto; una decision no puede apoyarse en eso."""
    proyecto = novela_completa
    estado = d_global.recalcular_estado_hilos(proyecto)
    assert estado["hil_el-mapa-falso"] == "resuelto"


def test_el_canon_aprobado_no_admite_modificacion_sin_version_nueva(novela_completa):
    """INV-6."""
    proyecto = novela_completa
    with pytest.raises(ErrorStoryMaker) as fallo:
        d_canon.aprobar(proyecto, modo="agente", quien="otro")
    assert fallo.value.codigo == "ERR-604"


def test_replanificar_identifica_los_capitulos_que_invalida(novela_completa):
    """RF-027: se calcula antes de aprobar, no cuando se descubre la incoherencia."""
    proyecto = novela_completa
    plan = plan_minimo()
    plan["capitulos"][0]["escenas"][0]["funcion_narrativa"] = "otra funcion distinta"
    resultado = d_canon.replanificar(
        proyecto, plan, motivo="la apertura no funcionaba", origen="sm-refinador",
        capitulos_validados=d_validacion.capitulos_validados(proyecto),
    )
    assert "cap_001" in resultado["capitulos_invalidados"]
    assert "cap_002" not in resultado["capitulos_invalidados"]
    assert resultado["requiere_punto_control"] == "PC-4"


def test_la_deriva_de_voz_no_se_evalua_sobre_una_muestra_sin_tamano(novela_completa):
    """RNF-010 no bloquea cuando no hay muestra con la que medir.

    Un indicador que no puede distinguir senal de ruido no debe impedir una
    entrega. Se declara no evaluable con su motivo, sus valores se entregan como
    informativos, y la pasada global sigue adelante.
    """
    proyecto = novela_completa
    deriva = d_global.deriva_de_voz(proyecto)
    assert deriva["evaluable"] is False
    assert deriva["motivo"]
    assert "indicadores_informativos" in deriva
    assert d_global.pasada_global(proyecto)["superada"]


def test_las_dos_guardas_de_la_deriva_de_voz():
    """La decision vive en una funcion pura, asi que se prueba sin montar novelas."""
    # Con menos de tres capitulos los tercios no separan nada.
    assert "tres capitulos" in d_global.motivo_no_evaluable(2, 50_000, 50_000)
    # Con tercios demasiado cortos, lo que varia es el muestreo.
    assert "ruido de muestreo" in d_global.motivo_no_evaluable(3, 170, 165)
    # El tercio corto manda: no vale compensar uno largo con otro raquitico.
    assert d_global.motivo_no_evaluable(40, 40_000, 200) is not None
    # Una novela de verdad si se mide.
    assert d_global.motivo_no_evaluable(40, 33_000, 34_000) is None
