"""spec: §4.7, §6 · arq: §10

Los gates se deciden en el PC y Telegram solo avisa.

Lo que se comprueba es la frontera entre las dos cosas: que el aviso **no lleva botones** y
ni comandos, solo «Decide en el PC», y que `aplicar` —lo que ejecuta `storymaker decidir`—
solo toca el gate pendiente y rechaza sin escribir nada lo que no se puede aplicar.
"""

from __future__ import annotations

import aiosqlite
import pytest

from storymaker.commons.db.repos import arnes
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.gates.decisiones import DECISIONES, Decision, DecisionInvalida, aplicar
from storymaker.gates.notifier import (
    Aviso,
    NotifierNulo,
    avisar_sin_fallar,
    aviso_de_aparcada,
    aviso_de_parada,
    aviso_de_terminada,
    texto_de,
)


class TestAviso:
    def test_el_aviso_de_un_gate_dice_decide_en_el_pc_sin_comandos_ni_botones(self) -> None:
        aviso = Aviso(
            titulo="Gate de Plotting",
            cuerpo="La escaleta espera tu visto bueno.",
            gate_id=3,
            decisiones=tuple(d.value for d in DECISIONES),
            novela="ejemplo",
        )
        texto = texto_de(aviso)
        assert texto.endswith("Decide en el PC")
        assert "storymaker" not in texto
        assert "inline_keyboard" not in texto

    def test_el_aviso_informativo_no_pide_decision(self) -> None:
        texto = texto_de(Aviso(titulo="Capitulo 6 de 10 aprobado", cuerpo="0,41 $"))
        assert "decidir" not in texto

    def test_el_aviso_de_parada_dice_donde_sin_comandos(self) -> None:
        aviso = aviso_de_parada("salamanca", nodo="extract", motivo="FOREIGN KEY constraint failed")
        texto = texto_de(aviso)
        assert not aviso.bloquea, "una parada informa: no hay gate que decidir"
        assert "extract" in texto and "FOREIGN KEY" in texto
        assert "storymaker" not in texto

    def test_el_aviso_de_final_trae_version_y_coste(self) -> None:
        texto = texto_de(aviso_de_terminada("salamanca", version=1, coste_usd=0.4123))
        assert "Version 1" in texto and "0.4123" in texto
        assert "decidir" not in texto

    def test_el_aviso_de_aparcada_recuerda_que_no_se_aprobo_nada(self) -> None:
        texto = texto_de(aviso_de_aparcada("salamanca", gate="Plotting"))
        assert "Plotting" in texto and "No se ha aprobado nada" in texto
        assert texto.endswith("Decide en el PC")
        assert "storymaker decidir" not in texto

    async def test_un_notifier_que_revienta_no_sube_el_fallo(self) -> None:
        class Roto:
            async def enviar(self, aviso: Aviso) -> None:
                raise RuntimeError("sin red")

        await avisar_sin_fallar(Roto(), aviso_de_terminada("x", version=1, coste_usd=0.0))

    async def test_el_nulo_recuerda_lo_que_se_le_pidio(self) -> None:
        nulo = NotifierNulo()
        await avisar_sin_fallar(nulo, aviso_de_parada("x", nodo="n", motivo="m"))
        assert len(nulo.enviados) == 1


class TestAplicar:
    async def test_decide_el_gate_pendiente(self, db: aiosqlite.Connection, fase_run: int) -> None:
        gate_id = await arnes.abrir_gate(db, fase_run)
        tomada = await aplicar(db, ObservadorNulo(), "rehacer", "mas detalle de epoca")
        assert tomada.gate_id == gate_id
        assert tomada.decision is Decision.REHACER
        assert await arnes.gate_pendiente(db) is None

    async def test_decidir_dos_veces_no_reanuda_dos_veces(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        await arnes.abrir_gate(db, fase_run)
        await aplicar(db, ObservadorNulo(), "aprobar")
        with pytest.raises(DecisionInvalida, match="ningun gate"):
            await aplicar(db, ObservadorNulo(), "aprobar")

    async def test_una_decision_desconocida_no_toca_el_gate(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        await arnes.abrir_gate(db, fase_run)
        with pytest.raises(DecisionInvalida, match="no es una decision"):
            await aplicar(db, ObservadorNulo(), "publicar")
        assert await arnes.gate_pendiente(db) is not None


class TestEntrevistaPorElGate:
    """La entrevista pasa por el gate de Intake: se contesta con «rehacer» y su comentario."""

    async def test_las_respuestas_son_los_comentarios_de_rehacer_en_orden(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
        intake = await arnes.abrir_fase_run(db, "intake")
        for comentario in ("nacio en 1792", "prefiere un final abierto"):
            await arnes.abrir_gate(db, intake)
            await aplicar(db, ObservadorNulo(), "rehacer", comentario)
        # Un «rehacer» de otra fase no es una respuesta a la entrevista.
        await arnes.abrir_gate(db, fase_run)
        await aplicar(db, ObservadorNulo(), "rehacer", "mas detalle de epoca")
        await arnes.abrir_gate(db, intake)
        await aplicar(db, ObservadorNulo(), "aprobar")
        assert await arnes.comentarios_de_rehacer(db, "intake") == [
            "nacio en 1792",
            "prefiere un final abierto",
        ]

    async def test_repetir_la_entrevista_no_duplica_los_datos_dictados(
        self, db: aiosqlite.Connection
    ) -> None:
        from storymaker.intake.cuarentena import volcar_dictados
        from storymaker.intake.esquemas import ElementoPersonalizacion, TipoDeDato

        elementos = [ElementoPersonalizacion(tipo=TipoDeDato.OBJETO, valor="una txalupa")]
        primera = await volcar_dictados(db, elementos)
        segunda = await volcar_dictados(db, elementos)
        assert len(primera) == 1 and segunda == []
