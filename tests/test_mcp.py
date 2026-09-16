"""Los dos servidores de recuperacion (seccion 2.5).

Lo que se prueba aqui, por encima de todo, es la regla que ambos comparten:
**devuelven contenido mas localizador mas fecha, nunca contenido suelto.** Sin eso
RF-101 no tendria que conservar y la trazabilidad se caeria en cuanto muriera un
enlace.

El servidor RAG se prueba de punta a punta sobre un corpus real en disco, porque no
necesita nada externo. Del servidor web se prueba el protocolo, la degradacion
declarada y el tratamiento de credenciales; su camino con proveedor real depende de
una red y de una clave, y probar eso aqui seria probar la red.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import RAIZ

from storymaker_mcp.servidor import Resultado, filtrar_validos


def hablar_con_servidor(modulo: str, peticiones: list[dict], entorno: dict | None = None):
    """Lanza el servidor MCP y le pasa una conversacion JSON-RPC completa."""
    ambiente = {**os.environ, "PYTHONPATH": str(RAIZ / "src")}
    if entorno:
        ambiente.update(entorno)
    entrada = "\n".join(json.dumps(p) for p in peticiones) + "\n"
    proceso = subprocess.run(
        [sys.executable, "-m", modulo],
        input=entrada, capture_output=True, text=True,
        cwd=str(RAIZ), env=ambiente, timeout=60,
    )
    assert proceso.returncode == 0, proceso.stderr
    return [json.loads(l) for l in proceso.stdout.splitlines() if l.strip()]


def carga(respuesta: dict) -> dict:
    return json.loads(respuesta["result"]["content"][0]["text"])


INICIALIZAR = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}


# ==========================================================================
# El contrato compartido
# ==========================================================================


def test_un_resultado_sin_localizador_no_es_valido():
    assert not Resultado(contenido="algo", localizador="").valido


def test_un_resultado_sin_contenido_no_es_valido():
    assert not Resultado(contenido="   ", localizador="https://x.test").valido


def test_lo_invalido_se_descarta_y_se_dice_por_que():
    validos, descartados = filtrar_validos([
        Resultado(contenido="bueno", localizador="https://x.test"),
        Resultado(contenido="", localizador="https://y.test"),
    ])
    assert len(validos) == 1
    assert len(descartados) == 1
    assert "sin contenido recuperable" in descartados[0]


def test_todo_resultado_valido_lleva_las_tres_piezas():
    validos, _ = filtrar_validos([Resultado(contenido="x", localizador="https://x.test")])
    for clave in ("contenido", "localizador", "consultado_en"):
        assert validos[0][clave]


# ==========================================================================
# Protocolo
# ==========================================================================


@pytest.mark.parametrize("modulo", ["storymaker_mcp.rag", "storymaker_mcp.web"])
def test_el_servidor_responde_a_initialize_y_declara_sus_herramientas(modulo):
    respuestas = hablar_con_servidor(modulo, [
        INICIALIZAR,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ])
    assert respuestas[0]["result"]["serverInfo"]["name"] == modulo.split(".")[-1].replace(
        "rag", "sm-rag"
    ).replace("web", "sm-web")
    herramientas = {h["name"] for h in respuestas[1]["result"]["tools"]}
    assert "buscar" in herramientas


@pytest.mark.parametrize("modulo", ["storymaker_mcp.rag", "storymaker_mcp.web"])
def test_una_herramienta_desconocida_devuelve_error_de_protocolo(modulo):
    respuestas = hablar_con_servidor(modulo, [
        INICIALIZAR,
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "inventada", "arguments": {}}},
    ])
    assert respuestas[1]["error"]["code"] == -32601


# ==========================================================================
# sm-rag, de punta a punta
# ==========================================================================


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    raiz = tmp_path / "corpus"
    raiz.mkdir()
    (raiz / "amberes.md").write_text(
        "Los cartografos de Amberes trabajaban con vitela y compas hacia 1560. "
        "El gremio regulaba la venta de cartas de navegacion. " * 20,
        encoding="utf-8",
    )
    (raiz / "sevilla.md").write_text(
        "La Casa de Contratacion de Sevilla custodiaba el padron real. " * 20,
        encoding="utf-8",
    )
    (raiz / "irrelevante.md").write_text("Nada que ver con el asunto. " * 20, encoding="utf-8")
    return raiz


def test_rag_recupera_con_documento_y_fragmento(corpus):
    respuestas = hablar_con_servidor(
        "storymaker_mcp.rag",
        [INICIALIZAR,
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "buscar", "arguments": {"consulta": "cartografos vitela Amberes"}}}],
        entorno={"SM_RAG_CORPUS": str(corpus)},
    )
    salida = carga(respuestas[1])
    assert salida["ok"]
    assert salida["resultados"], salida

    primero = salida["resultados"][0]
    assert "amberes" in primero["localizador"]
    # El localizador de un resultado RAG lleva la posicion: sin ella, "lo dice este
    # fichero" no localiza nada.
    assert "#palabra=" in primero["localizador"]
    assert primero["contenido"]
    assert primero["consultado_en"]


def test_rag_sin_resultados_invita_a_declarar_laguna(corpus):
    respuestas = hablar_con_servidor(
        "storymaker_mcp.rag",
        [INICIALIZAR,
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "buscar",
                     "arguments": {"consulta": "termodinamica cuantica submarina"}}}],
        entorno={"SM_RAG_CORPUS": str(corpus)},
    )
    salida = carga(respuestas[1])
    assert salida["resultados"] == []
    assert salida["codigo_error"] == "ERR-802"
    assert "laguna" in salida["mensaje"]


def test_rag_sin_corpus_declara_err_801_y_pide_degradar():
    respuestas = hablar_con_servidor(
        "storymaker_mcp.rag",
        [INICIALIZAR,
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "buscar", "arguments": {"consulta": "lo que sea"}}}],
        entorno={"SM_RAG_CORPUS": ""},
    )
    salida = carga(respuestas[1])
    assert salida["codigo_error"] == "ERR-801"
    assert "cobertura reducida" in salida["mensaje"]


def test_rag_informa_del_estado_del_corpus_sin_recuperar_nada(corpus):
    respuestas = hablar_con_servidor(
        "storymaker_mcp.rag",
        [INICIALIZAR,
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "estado_corpus", "arguments": {}}}],
        entorno={"SM_RAG_CORPUS": str(corpus)},
    )
    salida = carga(respuestas[1])
    assert salida["accesible"] and salida["documentos"] == 3


# ==========================================================================
# sm-web: degradacion y credenciales
# ==========================================================================


def test_web_sin_proveedor_degrada_con_err_801():
    respuestas = hablar_con_servidor(
        "storymaker_mcp.web",
        [INICIALIZAR,
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "buscar", "arguments": {"consulta": "Amberes 1560"}}}],
        entorno={"SM_WEB_PROVEEDOR": "", "SM_WEB_API_KEY": ""},
    )
    salida = carga(respuestas[1])
    assert salida["codigo_error"] == "ERR-801"
    assert "ERR-803" in salida["mensaje"]  # avisa de que fallar ambos detiene la etapa


def test_web_nunca_devuelve_el_valor_de_la_credencial():
    """Seccion 10: se referencia por marcador, nunca por su valor."""
    respuestas = hablar_con_servidor(
        "storymaker_mcp.web",
        [INICIALIZAR,
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "buscar", "arguments": {"consulta": "x"}}}],
        entorno={"SM_WEB_PROVEEDOR": "", "SM_WEB_API_KEY": "sk-secreto-de-verdad"},
    )
    bruto = json.dumps(respuestas)
    assert "sk-secreto-de-verdad" not in bruto
    assert carga(respuestas[1])["credencial"] == "<<presente>>"


def test_web_con_proveedor_pero_sin_credencial_devuelve_err_205():
    respuestas = hablar_con_servidor(
        "storymaker_mcp.web",
        [INICIALIZAR,
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "buscar", "arguments": {"consulta": "x"}}}],
        entorno={"SM_WEB_PROVEEDOR": "brave", "SM_WEB_API_KEY": ""},
    )
    assert carga(respuestas[1])["codigo_error"] == "ERR-205"


def test_web_rechaza_un_localizador_no_recuperable():
    respuestas = hablar_con_servidor(
        "storymaker_mcp.web",
        [INICIALIZAR,
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "recuperar", "arguments": {"url": "no-es-una-direccion"}}}],
    )
    assert carga(respuestas[1])["codigo_error"] == "ERR-802"


def test_web_declara_por_que_no_pudo_conservar(tmp_path):
    """RF-101: si no se puede conservar, se declara el motivo (ERR-607)."""
    respuestas = hablar_con_servidor(
        "storymaker_mcp.web",
        [INICIALIZAR,
         {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "recuperar",
                     "arguments": {"url": "http://localhost:1/pagina-que-no-existe"}}}],
    )
    salida = carga(respuestas[1])
    assert salida["codigo_error"] == "ERR-607"
    assert salida["motivo_no_conservable"]
