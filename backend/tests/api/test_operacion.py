"""spec: §5.3 · arq: §16.5, §10

La operación desde la interfaz. El lanzador de la aplicación se sustituye por uno que anota
lo que habría lanzado, porque lo que se prueba aquí es qué comando se lanza y cuándo se
rechaza, no la CLI, que tiene sus propias pruebas.
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
from storymaker.commons.db.repos import arnes, mundo
from storymaker.commons.graph import cerrojo


class LanzadorFalso:
    def __init__(self) -> None:
        self.lanzados: list[list[str]] = []

    def __call__(self, carpeta: Path, argumentos: list[str], settings: Settings) -> str:
        self.lanzados.append(argumentos)
        return f"falso-{argumentos[0]}.log"


class VectorizadorFalso:
    dimension = 384

    def vectorizar(self, textos: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in textos]


@pytest.fixture
def ajustes(tmp_path: Path) -> Settings:
    directorio = tmp_path / "proyectos"
    directorio.mkdir()
    return Settings(_env_file=None, directorio_proyectos=directorio)


@pytest.fixture
def lanzador() -> LanzadorFalso:
    return LanzadorFalso()


@pytest.fixture
def cliente(ajustes: Settings, lanzador: LanzadorFalso) -> Any:
    app = crear_app(ajustes)
    app.state.lanzar = lanzador
    app.state.vectorizador = VectorizadorFalso
    return TestClient(app)


@pytest.fixture
async def publicada(ajustes: Settings) -> Path:
    ruta = ruta_de("mar", ajustes)
    await sembrar(ruta)
    return ruta


async def _abrir_gate(ruta: Path, fase: str) -> None:
    async with abrir_novela(ruta) as db:
        await arnes.abrir_gate(db, await arnes.abrir_fase_run(db, fase))
        await db.commit()


ENCARGO = {
    "homenajeado": {"nombre_homenajeado": "Ana Ruiz", "ocasion": "jubilación"},
    "obra": {"n_capitulos": 3},
}


class TestGuardas:
    def test_una_accion_sin_json_es_415(self, publicada: Path, cliente: Any) -> None:
        respuesta = cliente.post("/api/novelas/mar/continuar", content=b"x")
        assert respuesta.status_code == 415

    def test_una_accion_remota_es_403(self, ajustes: Settings, publicada: Path) -> None:
        remoto = TestClient(crear_app(ajustes), client=("10.0.0.7", 5000))
        assert remoto.post("/api/novelas/mar/continuar", json={}).status_code == 403

    def test_la_lectura_no_pasa_por_las_guardas(self, publicada: Path, cliente: Any) -> None:
        assert cliente.get("/api/novelas").status_code == 200


class TestEncargo:
    def test_validar_senala_el_campo(self, cliente: Any) -> None:
        cuerpo = cliente.post(
            "/api/encargos/validar", json={"encargo": {"obra": {"n_capitulos": 0}}}
        ).json()
        campos = {e["campo"] for e in cuerpo["errores"]}
        assert campos == {"homenajeado.nombre_homenajeado", "obra.n_capitulos"}
        assert not cuerpo["valido"]

    def test_encargar_escribe_el_encargo_y_lanza_nueva(
        self, ajustes: Settings, cliente: Any, lanzador: LanzadorFalso
    ) -> None:
        respuesta = cliente.post("/api/novelas", json={"encargo": ENCARGO, "batch": True})
        assert respuesta.status_code == 202
        nombre = respuesta.json()["nombre"]
        assert (ajustes.directorio_proyectos / nombre / "encargo.json").exists()
        assert lanzador.lanzados[0][0] == "nueva"
        assert lanzador.lanzados[0][-1] == "--batch"

    def test_la_investigacion_exhaustiva_viaja_a_la_cli(
        self, cliente: Any, lanzador: LanzadorFalso
    ) -> None:
        cuerpo = {"encargo": ENCARGO, "investigacion": "exhaustiva"}
        assert cliente.post("/api/novelas", json=cuerpo).status_code == 202
        assert lanzador.lanzados[0][-2:] == ["--investigacion", "exhaustiva"]

    def test_un_modo_de_investigacion_desconocido_se_rechaza(
        self, cliente: Any, lanzador: LanzadorFalso
    ) -> None:
        cuerpo = {"encargo": ENCARGO, "investigacion": "total"}
        assert cliente.post("/api/novelas", json=cuerpo).status_code == 422
        assert lanzador.lanzados == []

    def test_un_encargo_invalido_no_se_lanza(self, cliente: Any, lanzador: LanzadorFalso) -> None:
        assert cliente.post("/api/novelas", json={"encargo": {}}).status_code == 422
        assert lanzador.lanzados == []

    def test_no_se_pisa_una_novela_que_existe(self, publicada: Path, cliente: Any) -> None:
        cuerpo = {"encargo": ENCARGO, "nombre": "mar"}
        assert cliente.post("/api/novelas", json=cuerpo).status_code == 409

    def test_los_ejemplos_se_sirven_leidos(self, cliente: Any) -> None:
        ejemplos = cliente.get("/api/ejemplos").json()
        assert any(e["nombre"] == "brief-salamanca" for e in ejemplos)


class TestDecidirYContinuar:
    async def test_decidir_lanza_la_cli_con_su_comentario(
        self, publicada: Path, cliente: Any, lanzador: LanzadorFalso
    ) -> None:
        await _abrir_gate(publicada, "writing")
        respuesta = cliente.post(
            "/api/novelas/mar/decisiones", json={"decision": "rehacer", "comentario": "más mar"}
        )
        assert respuesta.status_code == 202
        assert lanzador.lanzados == [["decidir", "mar", "rehacer", "--comentario", "más mar"]]

    async def test_editar_nunca_se_envia(self, publicada: Path, cliente: Any) -> None:
        await _abrir_gate(publicada, "writing")
        respuesta = cliente.post("/api/novelas/mar/decisiones", json={"decision": "editar"})
        assert respuesta.status_code == 422

    async def test_abortar_solo_en_intake(
        self, publicada: Path, cliente: Any, lanzador: LanzadorFalso
    ) -> None:
        await _abrir_gate(publicada, "writing")
        respuesta = cliente.post("/api/novelas/mar/decisiones", json={"decision": "abortar"})
        assert respuesta.status_code == 422
        assert lanzador.lanzados == []

    def test_sin_gate_no_hay_nada_que_decidir(self, publicada: Path, cliente: Any) -> None:
        respuesta = cliente.post("/api/novelas/mar/decisiones", json={"decision": "aprobar"})
        assert respuesta.status_code == 422

    async def test_con_gate_no_se_continua(self, publicada: Path, cliente: Any) -> None:
        await _abrir_gate(publicada, "writing")
        assert cliente.post("/api/novelas/mar/continuar", json={}).status_code == 422

    def test_ocupada_se_rechaza_sin_encolar(
        self, publicada: Path, cliente: Any, lanzador: LanzadorFalso
    ) -> None:
        cerrojo.ruta_del_cerrojo(publicada).write_text(str(os.getpid()), encoding="utf-8")
        assert cliente.post("/api/novelas/mar/continuar", json={}).status_code == 409
        assert cliente.post("/api/novelas/mar/reintentar", json={}).status_code == 409
        assert lanzador.lanzados == []

    def test_continuar_queda_en_la_auditoria(
        self, publicada: Path, cliente: Any, lanzador: LanzadorFalso
    ) -> None:
        assert cliente.post("/api/novelas/mar/continuar", json={}).status_code == 202
        panel = cliente.get("/api/novelas/mar/panel").json()
        assert any("continuar" in s["texto"] for s in panel["actividad"])


class TestDesbloquear:
    def test_un_cerrojo_vivo_no_se_rompe(self, publicada: Path, cliente: Any) -> None:
        cerrojo.ruta_del_cerrojo(publicada).write_text(str(os.getpid()), encoding="utf-8")
        assert cliente.post("/api/novelas/mar/desbloquear", json={}).status_code == 409
        assert cerrojo.esta_tomado(publicada)

    def test_un_cerrojo_huerfano_si(self, publicada: Path, cliente: Any) -> None:
        cerrojo.ruta_del_cerrojo(publicada).write_text("999999", encoding="utf-8")
        assert cliente.post("/api/novelas/mar/desbloquear", json={}).status_code == 200
        assert not cerrojo.esta_tomado(publicada)


class TestEditar:
    async def test_una_edicion_queda_trazada(self, publicada: Path, cliente: Any) -> None:
        respuesta = cliente.post(
            "/api/novelas/mar/ediciones",
            json={
                "objeto": "personaje",
                "fila_id": 2,
                "campo": "estatus",
                "valor": "contramaestre",
                "motivo": "así era",
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        async with abrir_novela(publicada) as db:
            async with db.execute("SELECT despues FROM edicion_humana") as cursor:
                assert [f[0] for f in await cursor.fetchall()] == ["contramaestre"]

    def test_un_campo_no_editable_se_rechaza(self, publicada: Path, cliente: Any) -> None:
        respuesta = cliente.post(
            "/api/novelas/mar/ediciones",
            json={"objeto": "personaje", "fila_id": 2, "campo": "tipo", "valor": "x"},
        )
        assert respuesta.status_code == 422


async def _sembrar_hecho(
    ruta: Path, *, motivo: str | None = None, anadido: str | None = None
) -> int:
    """Un hecho sin respaldo con su fuente, y el veredicto del verificador si se pide.

    Con `anadido`, el veredicto es parcial: respaldado, y el añadido en `sin_respaldo`.
    """
    async with abrir_novela(ruta) as db:
        fase = await arnes.abrir_fase_run(db, "investigation")
        cursor = await db.execute(
            "INSERT INTO mundo_hecho (fase_run_id, enunciado, estado, dimension, origen, cita,"
            " respaldo) VALUES (?, 'En 1983 hubo nieve', 'verificado', 'cronologia',"
            " 'investigacion_inicial', 'Hubo frío', 'no_respaldado')",
            (fase,),
        )
        hecho = int(cursor.lastrowid or 0)
        if anadido is not None:
            await mundo.anotar_respaldo(db, hecho, "respaldado", anadido)
        fuente = await db.execute("INSERT INTO mundo_fuente (tipo, titulo) VALUES ('web', 'X')")
        await db.execute(
            "INSERT INTO mundo_hecho_fuente (hecho_id, fuente_id) VALUES (?, ?)",
            (hecho, fuente.lastrowid),
        )
        if motivo is not None:
            await arnes.registrar_audit(
                db,
                actor="verificador",
                accion="respaldo",
                objeto=f"hecho:{hecho}",
                despues={"respaldado": False, "motivo": motivo},
            )
        await arnes.abrir_gate(db, fase)
        await db.commit()
    return hecho


class TestDescartar:
    async def test_descartar_borra_el_hecho_y_queda_trazado(
        self, publicada: Path, cliente: Any
    ) -> None:
        hecho = await _sembrar_hecho(publicada)
        respuesta = cliente.post(
            f"/api/novelas/mar/hechos/{hecho}/descartar", json={"motivo": "adornado"}
        )
        assert respuesta.status_code == 200, respuesta.text
        async with abrir_novela(publicada) as db:
            async with db.execute("SELECT COUNT(*) FROM mundo_hecho") as cursor:
                assert (await cursor.fetchone())[0] == 0
            async with db.execute(
                "SELECT campo, antes, despues, motivo FROM edicion_humana"
            ) as cursor:
                assert [tuple(f) for f in await cursor.fetchall()] == [
                    ("descartado", "En 1983 hubo nieve", None, "adornado")
                ]

    async def test_un_hecho_que_no_existe_es_404(self, publicada: Path, cliente: Any) -> None:
        await _sembrar_hecho(publicada)
        assert cliente.post("/api/novelas/mar/hechos/999/descartar", json={}).status_code == 404

    async def test_un_corpus_sellado_no_se_toca(self, publicada: Path, cliente: Any) -> None:
        hecho = await _sembrar_hecho(publicada)
        async with abrir_novela(publicada) as db:
            await db.execute("INSERT INTO mundo_sello (hash, fase_run_id) VALUES ('h', 1)")
            await db.commit()
        respuesta = cliente.post(f"/api/novelas/mar/hechos/{hecho}/descartar", json={})
        assert respuesta.status_code == 422

    async def test_la_salida_trae_el_motivo_del_verificador(
        self, publicada: Path, cliente: Any
    ) -> None:
        await _sembrar_hecho(publicada, motivo="La cita no habla de nieve")
        hechos = cliente.get("/api/novelas/mar/fases/investigacion").json()["investigacion"][
            "hechos"
        ]
        assert hechos[0]["motivo_respaldo"] == "La cita no habla de nieve"

    async def test_la_salida_trae_la_firmeza(self, publicada: Path, cliente: Any) -> None:
        """Lo declarado se sirve intacto, y al lado lo que el escritor va a ver."""
        await _sembrar_hecho(publicada)
        (hecho,) = cliente.get("/api/novelas/mar/fases/investigacion").json()["investigacion"][
            "hechos"
        ]
        assert hecho["estado"] == "verificado"
        assert hecho["firmeza"] == "inferido"

    async def test_corregir_no_toca_el_respaldo(self, publicada: Path, cliente: Any) -> None:
        """Sobre el corpus decide el Autor: su corrección no reabre el veredicto."""
        hecho = await _sembrar_hecho(publicada)
        respuesta = cliente.post(
            "/api/novelas/mar/ediciones",
            json={"objeto": "hecho", "fila_id": hecho, "campo": "enunciado", "valor": "Nevó"},
        )
        assert respuesta.status_code == 200, respuesta.text
        async with abrir_novela(publicada) as db:
            fila = await mundo.hecho_por_id(db, hecho)
        assert fila is not None
        assert (fila["enunciado"], fila["respaldo"]) == ("Nevó", "no_respaldado")

    async def test_corregir_no_toca_el_anadido(self, publicada: Path, cliente: Any) -> None:
        """Si el Autor quita el añadido, deja de verse; el veredicto no se reescribe."""
        hecho = await _sembrar_hecho(publicada, anadido="hubo nieve")
        assert _salida_del_hecho(cliente)["no_lo_dice_la_cita"] == "hubo nieve"
        cliente.post(
            "/api/novelas/mar/ediciones",
            json={"objeto": "hecho", "fila_id": hecho, "campo": "enunciado", "valor": "En 1983"},
        )
        async with abrir_novela(publicada) as db:
            fila = await mundo.hecho_por_id(db, hecho)
        assert fila is not None
        assert fila["sin_respaldo"] == "hubo nieve"
        assert _salida_del_hecho(cliente)["no_lo_dice_la_cita"] is None

    async def test_la_salida_trae_lo_que_no_dice_la_cita(
        self, publicada: Path, cliente: Any
    ) -> None:
        await _sembrar_hecho(publicada, anadido="hubo nieve")
        hecho = _salida_del_hecho(cliente)
        assert hecho["firmeza"] == "documentado"
        assert hecho["no_lo_dice_la_cita"] == "hubo nieve"


def _salida_del_hecho(cliente: Any) -> dict[str, Any]:
    (hecho,) = cliente.get("/api/novelas/mar/fases/investigacion").json()["investigacion"][
        "hechos"
    ]
    return dict(hecho)
