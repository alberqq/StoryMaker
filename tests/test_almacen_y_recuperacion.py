"""Nivel de recuperacion: corte simulado en cada paso del orden canonico.

Criterio de la seccion 12: **ninguna unidad cerrada se pierde; ningun puntero
apunta al vacio.**

El orden canonico de ADR-04 es blob, ledger, artefacto, indice, puntero. La
propiedad que garantiza es asimetrica a proposito: una caida puede dejar un blob
huerfano, que es inocuo, o un artefacto sin puntero, que es invisible y se rehace.
Lo que nunca puede dejar es un puntero a algo que no existe, porque eso si
corrompe la Novela.
"""

from __future__ import annotations

import json

import pytest
from conftest import aprobar_canon, cerrar_encargo, poblar_contexto

from storymaker.almacen import ORDEN_CANONICO, Almacen, CerrojoProyecto
from storymaker.dominio import contexto as d_contexto
from storymaker.dominio import ejecucion as d_ejecucion
from storymaker.dominio import novela as d_novela
from storymaker.errores import ErrorStoryMaker
from storymaker.presupuesto import Presupuesto
from storymaker.version_esquema import fronteras_registradas, promover

TEXTO = " ".join(["palabra"] * 500)


# ==========================================================================
# Escritor unico (ADR-04 regla 1)
# ==========================================================================


def test_un_segundo_escritor_falla_con_err_501(proyecto):
    primero = CerrojoProyecto(proyecto.almacen, "primero")
    primero.tomar()
    try:
        with pytest.raises(ErrorStoryMaker) as fallo:
            CerrojoProyecto(proyecto.almacen, "segundo").tomar()
        assert fallo.value.codigo == "ERR-501"
        assert fallo.value.detalle["titular_actual"] == "primero"
    finally:
        primero.liberar()


def test_el_cerrojo_se_libera_y_admite_un_escritor_nuevo(proyecto):
    with CerrojoProyecto(proyecto.almacen, "primero"):
        pass
    with CerrojoProyecto(proyecto.almacen, "segundo"):
        pass  # no lanza


# ==========================================================================
# Escritura atomica (regla 2) y anexion de linea completa (regla 3)
# ==========================================================================


def test_la_escritura_atomica_no_deja_ficheros_temporales(proyecto):
    ruta = proyecto.almacen.raiz / "prueba.json"
    proyecto.almacen.escribir_json(ruta, {"a": 1})
    assert list(proyecto.almacen.raiz.glob("*.tmp")) == []
    assert json.loads(ruta.read_text(encoding="utf-8")) == {"a": 1}


def test_una_linea_truncada_se_descarta_y_se_anota(proyecto):
    """ERR-503: el corte deja evidencia, no se traga y no mata la lectura."""
    ruta = proyecto.almacen.raiz / "libro.jsonl"
    proyecto.almacen.anexar(ruta, {"id": "a", "valor": 1})
    proyecto.almacen.anexar(ruta, {"id": "b", "valor": 2})
    with open(ruta, "a", encoding="utf-8") as mango:
        mango.write('{"id": "c", "val')  # corte de corriente a mitad de linea

    registros = proyecto.almacen.leer_jsonl(ruta)
    assert [r["id"] for r in registros] == ["a", "b"]
    assert len(proyecto.almacen.lineas_descartadas) == 1
    assert proyecto.almacen.lineas_descartadas[0].numero == 3


def test_el_libro_de_solo_anexion_conserva_lo_anterior(proyecto):
    ruta = proyecto.almacen.raiz / "libro.jsonl"
    for numero in range(5):
        proyecto.almacen.anexar(ruta, {"id": str(numero)})
    assert len(proyecto.almacen.leer_jsonl(ruta)) == 5


# ==========================================================================
# Orden canonico (regla 4)
# ==========================================================================


def test_el_orden_canonico_esta_declarado_como_dato():
    assert ORDEN_CANONICO == ("blob", "ledger", "artefacto", "indice", "puntero")


@pytest.fixture
def listo_para_escribir(proyecto):
    cerrar_encargo(proyecto)
    poblar_contexto(proyecto)
    d_contexto.cerrar(proyecto, [
        {"seccion": seccion, "impacto": "sin efecto"} for seccion in ()
    ])
    aprobar_canon(proyecto)
    d_ejecucion.iniciar(
        proyecto, Presupuesto(coste_total=10.0, segundos_total=600.0, iteraciones_total=10)
    )
    return proyecto


def test_el_puntero_se_escribe_el_ultimo_y_apunta_a_algo_que_existe(listo_para_escribir):
    proyecto = listo_para_escribir
    resultado = d_novela.escribir(
        proyecto, "esc_001_001", TEXTO,
        id_unidad="udt_1", ejecucion=proyecto.estado.ejecucion_activa,
    )
    vigente = d_novela.version_vigente(proyecto, "esc_001_001")
    assert vigente == resultado["version_escena"]["id"]
    assert proyecto.almacen.texto_escena("esc_001_001", vigente).exists()
    assert proyecto.almacen.meta_escena("esc_001_001", vigente).exists()


def test_un_artefacto_sin_puntero_es_invisible_y_no_corrompe(listo_para_escribir):
    """Simula el corte justo antes de escribir el puntero."""
    proyecto = listo_para_escribir
    d_novela.escribir(
        proyecto, "esc_001_001", TEXTO,
        id_unidad="udt_1", ejecucion=proyecto.estado.ejecucion_activa,
    )
    # El corte: se deja el artefacto de la version 2 pero no se mueve el puntero.
    proyecto.almacen.escribir_texto(
        proyecto.almacen.texto_escena("esc_001_001", "esv_001_001_v2"), "huerfano"
    )
    assert d_novela.version_vigente(proyecto, "esc_001_001") == "esv_001_001_v1"


def test_un_blob_huerfano_es_inocuo(proyecto):
    digest = proyecto.almacen.guardar_blob("contenido que nadie llego a referenciar")
    assert proyecto.almacen.recuperar_blob(digest) is not None
    assert proyecto.almacen.leer_json(proyecto.almacen.fichero_proyecto) is not None


def test_guardar_el_mismo_blob_dos_veces_es_idempotente(proyecto):
    primero = proyecto.almacen.guardar_blob("mismo contenido")
    segundo = proyecto.almacen.guardar_blob("mismo contenido")
    assert primero == segundo


# ==========================================================================
# Idempotencia y reanudacion (seccion 7.4, RF-084)
# ==========================================================================


def test_una_clave_ya_cerrada_no_vuelve_a_gastar(listo_para_escribir):
    proyecto = listo_para_escribir
    from storymaker.manifiesto import construir
    from storymaker.presupuesto import Estimacion

    manifiesto = construir("sm-redactor", "esc_001_001", {"ficha_escena": "la ficha"})
    primera = d_ejecucion.admitir_unidad(
        proyecto, "sm-redactor", "esc_001_001", manifiesto, Estimacion(coste=0.5)
    )
    assert primera["admitida"] and not primera["ya_ejecutada"]

    d_ejecucion.cerrar_unidad(
        proyecto, primera["id_unidad"], "esc_001_001", "convergencia",
        clave_idempotencia_=primera["clave_idempotencia"], version_vigente="esv_001_001_v1",
    )

    segunda = d_ejecucion.admitir_unidad(
        proyecto, "sm-redactor", "esc_001_001", manifiesto, Estimacion(coste=0.5)
    )
    assert segunda["ya_ejecutada"]
    assert segunda["resultado_anterior"]["version_vigente"] == "esv_001_001_v1"


def test_reanudar_conserva_el_consumo_ya_gastado(listo_para_escribir):
    proyecto = listo_para_escribir
    d_ejecucion.registrar_llamada(
        proyecto, "udt_1", prompt_renderizado="p", salida_cruda="s",
        tokens_entrada=1000, tokens_salida=500, coste=1.25, segundos=3.0,
        modelo_solicitado="m", modelo_servido="m",
    )
    reanudada = d_ejecucion.reanudar(proyecto)
    assert reanudada["consumo_conservado"]["coste"] == 1.25
    assert reanudada["remanente"]["coste"] == 8.75


def test_la_memoria_efimera_se_borra_al_cerrar_la_unidad(listo_para_escribir):
    proyecto = listo_para_escribir
    carpeta = proyecto.almacen.preparar_tmp("udt_efimera")
    (carpeta / "notas.txt").write_text("borrador del agente", encoding="utf-8")
    assert carpeta.exists()

    d_ejecucion.cerrar_unidad(
        proyecto, "udt_efimera", "esc_001_001", "convergencia",
        clave_idempotencia_="clave_x",
    )
    assert not carpeta.exists()


# ==========================================================================
# Versionado de esquema (ADR-06)
# ==========================================================================


def test_sin_promotor_registrado_no_se_arranca():
    """Regla 3: se prefiere no arrancar a leer mal."""
    with pytest.raises(ErrorStoryMaker) as fallo:
        promover({"schema_version": "1.0"}, "entidad_sin_promotor", "2.0")
    assert fallo.value.codigo == "ERR-505"


def test_con_promotor_registrado_se_promueve_en_memoria():
    registro = {"schema_version": "1.0", "id": "esv_1", "vigente": True}
    promovido, fronteras = promover(registro, "escena_version", "2.0")
    assert "vigente" not in promovido           # la vigencia vive solo en ramas.json
    assert promovido["schema_version"] == "2.0"
    assert fronteras == ["escena_version:1->2"]
    assert registro["vigente"] is True          # el original no se reescribe (regla 4)


def test_un_registro_de_version_mayor_futura_no_se_lee():
    with pytest.raises(ErrorStoryMaker) as fallo:
        promover({"schema_version": "9.0"}, "escena_version", "2.0")
    assert fallo.value.codigo == "ERR-505"


def test_un_registro_sin_schema_version_no_se_lee():
    with pytest.raises(ErrorStoryMaker) as fallo:
        promover({"id": "x"}, "escena_version", "2.0")
    assert fallo.value.codigo == "ERR-505"


def test_hay_al_menos_un_promotor_registrado():
    assert any(f.entidad == "escena_version" for f in fronteras_registradas())


# ==========================================================================
# Indices (ADR-06 regla 6)
# ==========================================================================


def test_un_indice_de_otra_version_del_codigo_se_descarta(proyecto):
    from storymaker.indices import GestorIndices, Indice

    gestor = GestorIndices(proyecto.almacen)
    gestor.escribir(Indice("idx_cache", {"clave": "valor"}, version_codigo="0.0.1-antigua"))
    assert gestor.leer("idx_cache") is None


def test_reconstruir_los_indices_no_pierde_informacion(proyecto):
    from storymaker.indices import CATALOGO_INDICES, GestorIndices

    resultado = GestorIndices(proyecto.almacen).reconstruir_todos()
    for nombre in CATALOGO_INDICES:
        assert nombre in resultado


# ==========================================================================
# Credenciales
# ==========================================================================


def test_ninguna_credencial_llega_a_un_artefacto_persistido(listo_para_escribir):
    """Regla transversal de la seccion 10, comprobada sobre el ledger real."""
    proyecto = listo_para_escribir
    from storymaker.ledger import Ledger

    ledger = Ledger(proyecto.almacen, proyecto.estado.ejecucion_activa)
    ledger.anexar(
        "llamada_modelo",
        id_unidad="udt_1",
        api_key="sk-secretosecretosecreto",
        cabecera="Authorization: Bearer abcdefghijklmnop",
    )
    crudo = proyecto.almacen.ledger(proyecto.estado.ejecucion_activa).read_text(encoding="utf-8")
    assert "sk-secretosecretosecreto" not in crudo
    assert "abcdefghijklmnop" not in crudo
    assert "REDACTADO" in crudo
