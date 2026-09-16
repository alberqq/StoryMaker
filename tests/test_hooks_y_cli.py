"""Los hooks (seccion 2.4) y la superficie del nucleo (seccion 6.4).

Los hooks son la segunda capa de ADR-02, y la unica que deniega **antes de que la
llamada exista**. Se prueban aqui como procesos reales, con su protocolo de
entrada y salida estandar, porque probar solo la funcion interna dejaria sin cubrir
justo lo que puede fallar en produccion: el contrato con el arnes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import RAIZ, aprobar_canon, cerrar_encargo, poblar_contexto

from storymaker.dominio import canon as d_canon
from storymaker.dominio import contexto as d_contexto
from storymaker.dominio import ejecucion as d_ejecucion
from storymaker.dominio import novela as d_novela
from storymaker.presupuesto import Presupuesto

HOOKS = RAIZ / ".claude" / "hooks"
TEXTO = " ".join(["palabra"] * 500)


def ejecutar_hook(nombre: str, evento: dict, entorno: dict | None = None) -> dict:
    """Lanza un hook como lo lanzaria el arnes y devuelve su decision."""
    ambiente = {**os.environ, "PYTHONPATH": str(RAIZ / "src")}
    if entorno:
        ambiente.update(entorno)
    proceso = subprocess.run(
        [sys.executable, str(HOOKS / nombre)],
        input=json.dumps(evento),
        capture_output=True, text=True, cwd=str(RAIZ), env=ambiente, timeout=60,
    )
    assert proceso.returncode == 0, proceso.stderr
    salida = json.loads(proceso.stdout)
    return salida["hookSpecificOutput"]


def ejecutar_cli(*argumentos: str, raiz: Path) -> tuple[int, dict]:
    ambiente = {**os.environ, "PYTHONPATH": str(RAIZ / "src")}
    proceso = subprocess.run(
        [sys.executable, "-m", "storymaker", "--raiz", str(raiz), *argumentos],
        capture_output=True, text=True, cwd=str(RAIZ), env=ambiente, timeout=120,
    )
    return proceso.returncode, json.loads(proceso.stdout)


# ==========================================================================
# guard-escritura: ADR-02, mecanismo 2
# ==========================================================================


def test_guard_escritura_deniega_escribir_una_escena_a_mano():
    decision = ejecutar_hook("guard_escritura.py", {
        "tool_name": "Write",
        "tool_input": {"file_path": "proyectos/prj_abc/novela/escenas/esc_001_001/esv_001_001_v1.md"},
    })
    assert decision["permissionDecision"] == "deny"
    assert "nucleo" in decision["permissionDecisionReason"]


def test_guard_escritura_deniega_escribir_el_canon_a_mano():
    decision = ejecutar_hook("guard_escritura.py", {
        "tool_name": "Edit",
        "tool_input": {"file_path": "proyectos/prj_abc/canon/plan/can_abc_v1.json"},
    })
    assert decision["permissionDecision"] == "deny"


def test_guard_escritura_permite_la_memoria_efimera():
    """La unica excepcion de ADR-02: un agente necesita donde pensar."""
    decision = ejecutar_hook("guard_escritura.py", {
        "tool_name": "Write",
        "tool_input": {"file_path": "proyectos/prj_abc/tmp/udt_1/borrador.md"},
    })
    assert decision["permissionDecision"] == "allow"


def test_guard_escritura_atrapa_la_redireccion_de_shell():
    """Lo que los permisos no ven: un `echo ... >` sobre el estado."""
    decision = ejecutar_hook("guard_escritura.py", {
        "tool_name": "Bash",
        "tool_input": {"command": "echo '{}' > proyectos/prj_abc/canon/hechos.jsonl"},
    })
    assert decision["permissionDecision"] == "deny"


def test_guard_escritura_atrapa_un_borrado_del_estado():
    decision = ejecutar_hook("guard_escritura.py", {
        "tool_name": "Bash",
        "tool_input": {"command": "rm proyectos/prj_abc/hallazgos.jsonl"},
    })
    assert decision["permissionDecision"] == "deny"


def test_guard_escritura_permite_al_nucleo_escribir():
    """El nucleo si escribe: es el unico que puede."""
    decision = ejecutar_hook("guard_escritura.py", {
        "tool_name": "Bash",
        "tool_input": {"command": "storymaker --proyecto prj_abc canon proponer --plan @plan.json"},
    })
    assert decision["permissionDecision"] == "allow"


def test_guard_escritura_no_estorba_fuera_de_proyectos():
    decision = ejecutar_hook("guard_escritura.py", {
        "tool_name": "Write",
        "tool_input": {"file_path": "notas/mis_ideas.md"},
    })
    assert decision["permissionDecision"] == "allow"


# ==========================================================================
# guard-canon: INV-1 e INV-9
# ==========================================================================


@pytest.fixture
def proyecto_con_canon_borrador(proyecto):
    from storymaker.dominio import canon as d_canon
    from conftest import plan_minimo

    cerrar_encargo(proyecto)
    poblar_contexto(proyecto)
    d_contexto.cerrar(proyecto)
    d_canon.proponer(proyecto, plan_minimo())
    return proyecto


def test_guard_canon_deniega_redactar_sobre_canon_en_borrador(proyecto_con_canon_borrador):
    proyecto = proyecto_con_canon_borrador
    decision = ejecutar_hook(
        "guard_canon.py",
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"storymaker --proyecto {proyecto.estado.id} escena escribir "
                           "--escena esc_001_001 --texto @b.md --unidad udt_1"
            },
        },
        entorno={
            "STORYMAKER_PROYECTO": proyecto.estado.id,
            "STORYMAKER_RAIZ": str(proyecto.almacen.raiz_proyectos),
        },
    )
    assert decision["permissionDecision"] == "deny"
    assert "INV-1" in decision["permissionDecisionReason"]


def test_guard_canon_deniega_produccion_en_serie_sin_piloto(proyecto_con_canon_borrador):
    proyecto = proyecto_con_canon_borrador
    d_canon.aprobar(proyecto, modo="agente", quien="sm-validador-canon")
    decision = ejecutar_hook(
        "guard_canon.py",
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"storymaker --proyecto {proyecto.estado.id} escena escribir "
                           "--escena esc_001_002 --texto @b.md --unidad udt_2"
            },
        },
        entorno={
            "STORYMAKER_PROYECTO": proyecto.estado.id,
            "STORYMAKER_RAIZ": str(proyecto.almacen.raiz_proyectos),
        },
    )
    assert decision["permissionDecision"] == "deny"
    assert "INV-9" in decision["permissionDecisionReason"]


def test_guard_canon_permite_el_piloto(proyecto_con_canon_borrador):
    proyecto = proyecto_con_canon_borrador
    d_canon.aprobar(proyecto, modo="agente", quien="sm-validador-canon")
    decision = ejecutar_hook(
        "guard_canon.py",
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"storymaker --proyecto {proyecto.estado.id} escena escribir "
                           "--escena esc_001_001 --texto @b.md --unidad udt_1 --piloto"
            },
        },
        entorno={
            "STORYMAKER_PROYECTO": proyecto.estado.id,
            "STORYMAKER_RAIZ": str(proyecto.almacen.raiz_proyectos),
        },
    )
    assert decision["permissionDecision"] == "allow"


def test_guard_canon_no_estorba_a_las_ordenes_que_no_redactan():
    decision = ejecutar_hook("guard_canon.py", {
        "tool_name": "Bash",
        "tool_input": {"command": "storymaker --proyecto prj_abc ejecucion estado"},
    })
    assert decision["permissionDecision"] == "allow"


# ==========================================================================
# guard-proteccion: RF-054
# ==========================================================================


@pytest.fixture
def proyecto_con_pasaje_protegido(proyecto):
    cerrar_encargo(proyecto)
    poblar_contexto(proyecto)
    d_contexto.cerrar(proyecto)
    aprobar_canon(proyecto)
    d_ejecucion.iniciar(
        proyecto, Presupuesto(coste_total=10.0, segundos_total=600.0, iteraciones_total=10)
    )
    fragmento = "una frase que resolvio un bloqueante"
    d_novela.escribir(
        proyecto, "esc_001_001", f"{TEXTO} {fragmento}",
        id_unidad="udt_1", ejecucion=proyecto.estado.ejecucion_activa, es_piloto=True,
    )
    d_novela.proteger_pasaje(proyecto, "esc_001_001", fragmento, "hlz_x")
    return proyecto


def _entorno(proyecto):
    return {
        "STORYMAKER_PROYECTO": proyecto.estado.id,
        "STORYMAKER_RAIZ": str(proyecto.almacen.raiz_proyectos),
    }


def test_guard_proteccion_deniega_refinar_sin_justificacion(proyecto_con_pasaje_protegido):
    proyecto = proyecto_con_pasaje_protegido
    decision = ejecutar_hook(
        "guard_proteccion.py",
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"storymaker --proyecto {proyecto.estado.id} escena refinar "
                           "--escena esc_001_001 --texto @r.md --unidad udt_2"
            },
        },
        entorno=_entorno(proyecto),
    )
    assert decision["permissionDecision"] == "deny"
    assert "RF-054" in decision["permissionDecisionReason"]


def test_guard_proteccion_permite_con_justificacion(proyecto_con_pasaje_protegido):
    proyecto = proyecto_con_pasaje_protegido
    decision = ejecutar_hook(
        "guard_proteccion.py",
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"storymaker --proyecto {proyecto.estado.id} escena refinar "
                           "--escena esc_001_001 --texto @r.md --unidad udt_2 "
                           "--justificaciones @just.json"
            },
        },
        entorno=_entorno(proyecto),
    )
    assert decision["permissionDecision"] == "allow"


# ==========================================================================
# guard-presupuesto: RF-072
# ==========================================================================


def test_guard_presupuesto_deniega_con_el_presupuesto_agotado(proyecto):
    cerrar_encargo(proyecto)
    poblar_contexto(proyecto)
    d_contexto.cerrar(proyecto)
    aprobar_canon(proyecto)
    d_ejecucion.iniciar(
        proyecto, Presupuesto(coste_total=1.0, segundos_total=60.0, iteraciones_total=4)
    )
    d_ejecucion.registrar_llamada(
        proyecto, "udt_1", prompt_renderizado="p", salida_cruda="s",
        tokens_entrada=1, tokens_salida=1, coste=1.0, segundos=1.0,
        modelo_solicitado="m", modelo_servido="m",
    )
    decision = ejecutar_hook(
        "guard_presupuesto.py",
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"storymaker --proyecto {proyecto.estado.id} escena escribir "
                           "--escena esc_001_001 --texto @b.md --unidad udt_2"
            },
        },
        entorno=_entorno(proyecto),
    )
    assert decision["permissionDecision"] == "deny"
    assert "ERR-402" in decision["permissionDecisionReason"]


# ==========================================================================
# arranque: SessionStart
# ==========================================================================


def test_arranque_resume_el_estado_del_proyecto(proyecto):
    cerrar_encargo(proyecto)
    salida = ejecutar_hook("arranque.py", {}, entorno=_entorno(proyecto))
    contexto = salida["additionalContext"]
    assert proyecto.estado.id in contexto
    assert "Sin Ejecucion activa" in contexto


def test_arranque_avisa_de_puntos_de_control_pendientes(proyecto):
    cerrar_encargo(proyecto)
    poblar_contexto(proyecto)
    d_contexto.cerrar(proyecto)
    aprobar_canon(proyecto)
    d_ejecucion.iniciar(
        proyecto, Presupuesto(coste_total=10.0, segundos_total=600.0, iteraciones_total=10)
    )
    d_ejecucion.abrir_punto_control(proyecto, "PC-8", {"version_escena": "esv_001_001_v1"})

    salida = ejecutar_hook("arranque.py", {}, entorno=_entorno(proyecto))
    assert "esperan tu decision" in salida["additionalContext"]
    assert "PC-8" in salida["additionalContext"]


# ==========================================================================
# La superficie del nucleo (seccion 6.4)
# ==========================================================================


def test_el_cli_devuelve_siempre_el_mismo_sobre(raiz):
    codigo, salida = ejecutar_cli("proyecto", "crear", "--titulo", "Prueba CLI", raiz=raiz)
    assert codigo == 0
    assert salida["ok"] is True
    assert salida["comando"] == "proyecto crear"
    assert "datos" in salida and "momento" in salida


def test_el_cli_devuelve_el_error_tipado_y_sale_con_uno(raiz):
    codigo, salida = ejecutar_cli(
        "--proyecto", "prj_que_no_existe", "ejecucion", "estado", raiz=raiz
    )
    assert codigo == 1
    assert salida["ok"] is False
    assert salida["error"]["codigo"] == "ERR-304"
    assert "reintentable" in salida["error"]
    assert "accion" in salida["error"]


def test_el_catalogo_de_errores_es_consultable(raiz):
    codigo, salida = ejecutar_cli("errores", "listar", raiz=raiz)
    assert codigo == 0
    codigos = {e["codigo"] for e in salida["datos"]["errores"]}
    for esperado in ("ERR-404", "ERR-502", "ERR-601", "ERR-704", "ERR-902"):
        assert esperado in codigos


def test_el_cerrojo_impide_dos_escritores_desde_el_cli(raiz):
    _, creado = ejecutar_cli("proyecto", "crear", "--titulo", "Cerrojo", raiz=raiz)
    identificador = creado["datos"]["proyecto"]["id"]

    # Se simula un proceso que murio dejando el cerrojo tomado.
    (raiz / identificador / ".cerrojo").write_text(
        json.dumps({"titular": "otro proceso", "pid": 1}), encoding="utf-8"
    )
    codigo, salida = ejecutar_cli(
        "--proyecto", identificador, "encargo", "sesion",
        "--semilla", "un cartografo", "--tipo", "personaje", raiz=raiz,
    )
    assert codigo == 1
    assert salida["error"]["codigo"] == "ERR-501"


def test_las_lecturas_no_toman_el_cerrojo(raiz):
    """Consultar el estado no debe bloquear a quien lo esta produciendo."""
    _, creado = ejecutar_cli("proyecto", "crear", "--titulo", "Lectura", raiz=raiz)
    identificador = creado["datos"]["proyecto"]["id"]
    (raiz / identificador / ".cerrojo").write_text(
        json.dumps({"titular": "el escritor", "pid": 1}), encoding="utf-8"
    )
    codigo, salida = ejecutar_cli(
        "--proyecto", identificador, "ejecucion", "estado", raiz=raiz
    )
    assert codigo == 0 and salida["ok"]
