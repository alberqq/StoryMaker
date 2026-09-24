"""spec: §4.1 · arq: §4

El encargo en prosa: la descripción libre va delante y entra en la premisa, no en la
cuarentena.
"""

from __future__ import annotations

import json
from pathlib import Path

from storymaker.intake.encargo import leer, redactar


def test_la_descripcion_abre_la_premisa() -> None:
    premisa = redactar(
        {
            "descripcion": "Quiero una novela de piratas en Cádiz, con su perro Nala.",
            "homenajeado": {"nombre_homenajeado": "Ana Ruiz"},
        }
    )
    assert premisa.startswith("Quien encarga la novela la cuenta asi:")
    assert "su perro Nala" in premisa
    assert "Ana Ruiz" in premisa


def test_sin_descripcion_la_premisa_no_cambia() -> None:
    assert "cuenta asi" not in redactar({"homenajeado": {"nombre_homenajeado": "Ana Ruiz"}})


def test_la_descripcion_no_es_texto_pegado(tmp_path: Path) -> None:
    """Lo que escribe el Autor no va a la cuarentena: eso es solo `texto_libre`."""
    fichero = tmp_path / "encargo.json"
    fichero.write_text(
        json.dumps(
            {"descripcion": "Una novela de piratas", "homenajeado": {"nombre_homenajeado": "Ana"}}
        ),
        encoding="utf-8",
    )
    encargo = leer(fichero)
    assert encargo.texto_pegado == ""
    assert "Una novela de piratas" in encargo.premisa
