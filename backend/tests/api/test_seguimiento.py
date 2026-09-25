"""spec: §5.2 · arq: §16.5

El seguimiento: el estado de una novela y de cada fase, el panel y el gate, recalculados del
fichero en cada consulta.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from dobles.novela_de_lectura import sembrar
from fastapi.testclient import TestClient

from storymaker.api.app import crear_app
from storymaker.api.novelas import ruta_de
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos import arnes
from storymaker.commons.graph import cerrojo


@pytest.fixture
def ajustes(tmp_path: Path) -> Settings:
    directorio = tmp_path / "proyectos"
    directorio.mkdir()
    return Settings(_env_file=None, directorio_proyectos=directorio)


@pytest.fixture
def cliente(ajustes: Settings) -> Any:
    return TestClient(crear_app(ajustes))


@pytest.fixture
async def publicada(ajustes: Settings) -> Path:
    ruta = ruta_de("mar", ajustes)
    await sembrar(ruta)
    return ruta


async def _abrir_gate(ruta: Path, fase: str, preguntas: list[str] | None = None) -> int:
    async with abrir_novela(ruta) as db:
        fase_run = await arnes.abrir_fase_run(db, fase)
        gate = await arnes.abrir_gate(db, fase_run)
        for pregunta in preguntas or []:
            await arnes.registrar_incidencia(
                db, validador="pregunta_del_entrevistador", severidad="aviso", mensaje=pregunta
            )
        await db.commit()
    return gate


class TestListado:
    def test_una_novela_publicada_sale_terminada_o_en_pausa(
        self, publicada: Path, cliente: Any
    ) -> None:
        tarjeta = cliente.get("/api/novelas").json()[0]
        assert tarjeta["nombre"] == "mar"
        assert tarjeta["homenajeado"] == "Elvira Ponce"
        assert tarjeta["capitulos_aprobados"] == 3 and tarjeta["capitulos_total"] == 3
        assert tarjeta["versiones"] == 2
        # Las filas de fase de la semilla siguen abiertas, así que no es «terminada».
        assert tarjeta["estado"] == "en_pausa"

    async def test_un_gate_pendiente_es_esperando_al_autor(
        self, publicada: Path, cliente: Any
    ) -> None:
        await _abrir_gate(publicada, "writing")
        tarjeta = cliente.get("/api/novelas").json()[0]
        assert tarjeta["estado"] == "esperando_autor"
        assert tarjeta["gate"]["fase"] == "writing"

    async def test_una_publicada_que_se_reescribe_esta_en_escritura(
        self, publicada: Path, cliente: Any
    ) -> None:
        """La reescritura de la Fase 6 corre en Writing con Publication ya trabajada."""
        async with abrir_novela(publicada) as db:
            await db.execute("UPDATE fase_run SET estado = 'completada', fin = datetime('now')")
            await db.commit()
        assert cliente.get("/api/novelas").json()[0]["fase"] == "publication"

        async with abrir_novela(publicada) as db:
            await arnes.abrir_fase_run(db, "writing")
            await db.commit()
        assert cliente.get("/api/novelas").json()[0]["fase"] == "writing"

    def test_un_cerrojo_vivo_es_en_marcha(self, publicada: Path, cliente: Any) -> None:
        cerrojo.ruta_del_cerrojo(publicada).write_text(str(os.getpid()), encoding="utf-8")
        assert cliente.get("/api/novelas").json()[0]["estado"] == "en_marcha"

    def test_un_cerrojo_huerfano_es_detenida(self, publicada: Path, cliente: Any) -> None:
        cerrojo.ruta_del_cerrojo(publicada).write_text("999999", encoding="utf-8")
        assert cliente.get("/api/novelas").json()[0]["estado"] == "detenida"

    def test_una_carpeta_con_encargo_y_sin_fichero_esta_arrancando(
        self, ajustes: Settings, cliente: Any
    ) -> None:
        carpeta = ajustes.directorio_proyectos / "nueva"
        (carpeta / "registro").mkdir(parents=True)
        (carpeta / "encargo.json").write_text(
            '{"homenajeado": {"nombre_homenajeado": "Ana"}}', encoding="utf-8"
        )
        (carpeta / "registro" / "20260924-100000-nueva.log").write_text("", encoding="utf-8")
        tarjeta = cliente.get("/api/novelas").json()[0]
        assert tarjeta["estado"] == "arrancando"
        assert tarjeta["homenajeado"] == "Ana"

    def test_sin_registro_reciente_ese_encargo_ha_fallado(
        self, ajustes: Settings, cliente: Any
    ) -> None:
        carpeta = ajustes.directorio_proyectos / "rota"
        carpeta.mkdir()
        (carpeta / "encargo.json").write_text("{}", encoding="utf-8")
        assert cliente.get("/api/novelas").json()[0]["estado"] == "fallida"


class TestPanel:
    def test_las_seis_fases_tienen_estado_aunque_falten_filas(
        self, publicada: Path, cliente: Any
    ) -> None:
        panel = cliente.get("/api/novelas/mar/panel").json()
        fases = {f["fase"]: f for f in panel["fases"]}
        assert list(fases) == [
            "intake",
            "investigation",
            "plotting",
            "writing",
            "publication",
            "regeneration",
        ]
        # La semilla tiene escaleta pero ninguna fila de plotting: completada, deducida.
        assert fases["plotting"]["estado"] == "completada" and fases["plotting"]["deducida"]
        assert fases["publication"]["tiene_salida"]
        assert fases["investigation"]["estado"] == "pendiente"

    def test_capitulos_actividad_y_versiones(self, publicada: Path, cliente: Any) -> None:
        panel = cliente.get("/api/novelas/mar/panel").json()
        assert [c["estado"] for c in panel["capitulos"]] == ["aprobado"] * 3
        assert panel["capitulos"][1]["intentos"] == 2
        assert any("Capítulo 2" in s["texto"] for s in panel["actividad"])
        assert [v["numero"] for v in panel["versiones_publicadas"]] == [1, 2]
        assert panel["proceso"] == {"cerrojo": False, "pid": None, "vivo": False}

    def test_una_novela_que_no_existe_es_404(self, cliente: Any) -> None:
        assert cliente.get("/api/novelas/fantasma/panel").status_code == 404


class TestGate:
    async def test_el_gate_de_intake_trae_preguntas_y_abortar(
        self, publicada: Path, cliente: Any
    ) -> None:
        await _abrir_gate(publicada, "intake", ["¿Cómo se llama su perro?"])
        gate = cliente.get("/api/novelas/mar/gate").json()
        assert gate["fase"] == "intake"
        assert gate["preguntas"] == ["¿Cómo se llama su perro?"]
        assert gate["decisiones"] == ["aprobar", "rehacer", "abortar"]
        assert gate["recuentos"]

    async def test_fuera_de_intake_no_se_ofrece_abortar(
        self, publicada: Path, cliente: Any
    ) -> None:
        await _abrir_gate(publicada, "writing")
        gate = cliente.get("/api/novelas/mar/gate").json()
        assert gate["decisiones"] == ["aprobar", "rehacer"]
        familias = {e["objeto"] for e in gate["editables"]}
        assert {"personaje", "escenario"} <= familias

    def test_sin_gate_pendiente_es_404(self, publicada: Path, cliente: Any) -> None:
        assert cliente.get("/api/novelas/mar/gate").status_code == 404


class TestConversacion:
    async def test_el_gate_de_intake_trae_la_conversacion(
        self, publicada: Path, cliente: Any
    ) -> None:
        (publicada.parent / "encargo.json").write_text(
            '{"descripcion": "Una novela de piratas", "homenajeado": {"nombre_homenajeado": "E"}}',
            encoding="utf-8",
        )
        async with abrir_novela(publicada) as db:
            primera = await arnes.abrir_gate(db, await arnes.abrir_fase_run(db, "intake"))
            await arnes.decidir_gate(
                db,
                primera,
                decision="rehacer",
                comentario="1. ¿Perro?\n   Nala",
                decidido_por="autor",
            )
            await db.commit()
        await _abrir_gate(publicada, "intake", ["¿Dónde nació?"])
        conversacion = cliente.get("/api/novelas/mar/gate").json()["conversacion"]
        assert conversacion["descripcion"] == "Una novela de piratas"
        assert conversacion["rondas"] == ["1. ¿Perro?\n   Nala"]
        # La semilla ya tiene un brief cerrado.
        assert conversacion["brief"]["ocasion"] == "jubilacion"

    async def test_fuera_de_intake_no_hay_conversacion(self, publicada: Path, cliente: Any) -> None:
        await _abrir_gate(publicada, "writing")
        assert cliente.get("/api/novelas/mar/gate").json()["conversacion"] is None


class TestCandidatosDeRegeneracion:
    async def test_cada_candidato_lleva_lo_que_hace_falta_para_elegirlo(
        self, publicada: Path, cliente: Any
    ) -> None:
        gate = await _abrir_gate(publicada, "regeneration")
        async with abrir_novela(publicada) as db:
            await arnes.registrar_audit(
                db,
                actor="autor",
                accion="peticion:lector",
                objeto=f"gate:{gate}",
                despues={
                    "texto": "sin apellido",
                    "candidatos": [
                        {
                            "objeto": "personaje",
                            "fila_id": 1,
                            "descripcion": "Manuel Pérez",
                            "capitulos_a_regenerar": [1, 2],
                            "capitulos_a_revisar": [],
                            "coste": "2",
                        },
                        # Registrado antes de guardar objeto y fila: se enseña, no se elige.
                        {"descripcion": "Un hecho viejo", "capitulos_a_regenerar": []},
                    ],
                },
            )
            await db.commit()
        candidatos = cliente.get("/api/novelas/mar/gate").json()["peticion"]["candidatos"]
        assert (candidatos[0]["objeto"], candidatos[0]["fila_id"]) == ("personaje", 1)
        assert (candidatos[0]["campo"], candidatos[0]["valor"]) == ("nombre", "Manuel Pérez")
        assert candidatos[1]["objeto"] is None and candidatos[1]["campo"] is None
