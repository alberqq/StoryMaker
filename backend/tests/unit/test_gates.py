"""spec: §4.7, §6 · arq: §10

Los gates se deciden en el PC y Telegram solo avisa.

Lo que se comprueba es la frontera entre las dos cosas: que el aviso **no lleva botones** y
sí el comando exacto para decidir, y que `aplicar` —lo que ejecuta `storymaker decidir`—
solo toca el gate pendiente y rechaza sin escribir nada lo que no se puede aplicar.
"""

from __future__ import annotations

import aiosqlite
import pytest

from storymaker.commons.db.repos import arnes
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.gates.decisiones import DECISIONES, Decision, DecisionInvalida, aplicar
from storymaker.gates.notifier import Aviso, texto_de


class TestAviso:
    def test_el_aviso_de_un_gate_trae_el_comando_y_ningun_boton(self) -> None:
        aviso = Aviso(
            titulo="Gate de Plotting",
            cuerpo="La escaleta espera tu visto bueno.",
            gate_id=3,
            decisiones=tuple(d.value for d in DECISIONES),
            novela="ejemplo",
        )
        texto = texto_de(aviso)
        assert "storymaker decidir ejemplo aprobar" in texto
        assert "storymaker decidir ejemplo abortar" in texto
        assert "inline_keyboard" not in texto

    def test_el_aviso_informativo_no_pide_decision(self) -> None:
        texto = texto_de(Aviso(titulo="Capitulo 6 de 10 aprobado", cuerpo="0,41 $"))
        assert "decidir" not in texto


class TestAplicar:
    async def test_decide_el_gate_pendiente(
        self, db: aiosqlite.Connection, fase_run: int
    ) -> None:
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
