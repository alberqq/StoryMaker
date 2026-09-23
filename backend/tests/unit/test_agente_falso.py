"""spec: §7.1 · arq: §5

El doble tiene sus propias pruebas porque media suite se apoya en él: un doble que
miente en silencio deja en verde comprobaciones que no han comprobado nada.
"""

from __future__ import annotations

import pytest
from dobles.agente_falso import AgenteFalso, SinRespuestaPreparada

from storymaker.commons.config import Rol


def test_devuelve_lo_preparado_en_orden(agente_falso: AgenteFalso) -> None:
    agente_falso.preparar(Rol.ESCRITOR, "capitulo uno", "capitulo dos")
    assert agente_falso.invocar_rol(Rol.ESCRITOR, "paquete 1") == "capitulo uno"
    assert agente_falso.invocar_rol(Rol.ESCRITOR, "paquete 2") == "capitulo dos"


def test_un_rol_sin_respuesta_falla_ruidosamente(agente_falso: AgenteFalso) -> None:
    """Tocar un agente que la prueba no previó es un fallo, no un `None` silencioso."""
    with pytest.raises(SinRespuestaPreparada):
        agente_falso.invocar_rol(Rol.JUEZ, "novela entera")


def test_registra_rol_prompt_y_herramientas(agente_falso: AgenteFalso) -> None:
    agente_falso.preparar(Rol.INVESTIGADOR, {"hechos": []})
    agente_falso.invocar_rol(Rol.INVESTIGADOR, "Cádiz 1805", ("WebSearch", "WebFetch"))
    (invocacion,) = agente_falso.invocaciones
    assert invocacion.rol is Rol.INVESTIGADOR
    assert invocacion.herramientas == ("WebSearch", "WebFetch")
    assert agente_falso.prompts_de(Rol.INVESTIGADOR) == ["Cádiz 1805"]


def test_cuenta_las_invocaciones_por_rol(agente_falso: AgenteFalso) -> None:
    """El limite de reintentos por capitulo se comprueba contando invocaciones."""
    agente_falso.preparar(Rol.EDITOR, "parche 1", "parche 2")
    agente_falso.invocar_rol(Rol.EDITOR, "informe 1")
    agente_falso.invocar_rol(Rol.EDITOR, "informe 2")
    assert agente_falso.veces(Rol.EDITOR) == 2
    assert agente_falso.veces(Rol.ESCRITOR) == 0
