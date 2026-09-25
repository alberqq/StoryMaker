"""spec: §3.6 · arq: §3, §15

Pruebas de los dos hooks de `.claude/` **tal como los invoca Claude Code**: con el evento
por la entrada estándar, no con la ruta como argumento.

La prueba de contrato de `test_nodo_vs_hook.py` comprueba que el Core Domain da el mismo
veredicto por los dos caminos; esta comprueba lo que quedaba fuera de ella, que el hook
recibe de verdad el fichero editado y que solo mira capítulos. Y la del hook de policy,
que deniega **antes** de escribir y solo por lo que la edición introduce.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from storymaker.commons.validation import cli_hook, cli_policy

CONTEXTO = {
    "numero": 3,
    "nombres_canonicos": ["Manuel Ferrer"],
    "prohibidas": [{"nivel": "destinatario", "termino": "Beatriz", "normalizado": "beatriz"}],
    "entidades_fechadas": [],
    "fecha_narrativa": "1805-04-11",
    "rango_palabras": [5, 40],
}

LIMPIO = (
    "Manuel Ferrer bajo al muelle antes del amanecer y conto los cascos uno a uno, "
    "como hacia su padre, con la niebla pegada a la jarcia y el catalejo en la mano."
)


def _evento(herramienta: str, ruta: Path, **entrada: object) -> io.StringIO:
    return io.StringIO(
        json.dumps({"tool_name": herramienta, "tool_input": {"file_path": str(ruta), **entrada}})
    )


@pytest.fixture
def capitulo(tmp_path: Path) -> Path:
    ruta = tmp_path / "capitulo_03.md"
    ruta.write_text(LIMPIO, encoding="utf-8")
    ruta.with_suffix(".contexto.json").write_text(json.dumps(CONTEXTO), encoding="utf-8")
    return ruta


class TestHookDeValidacion:
    def test_lee_la_ruta_del_evento_y_deja_pasar_un_capitulo_limpio(self, capitulo: Path) -> None:
        assert cli_hook.main([], _evento("Write", capitulo)) == 0

    def test_bloquea_un_capitulo_que_rompe_una_regla(
        self, capitulo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        capitulo.write_text(LIMPIO + " Penso en Beatriz.", encoding="utf-8")
        assert cli_hook.main([], _evento("Edit", capitulo)) == cli_hook.BLOQUEA
        # Claude Code solo le enseña al agente lo que sale por `stderr`.
        assert "guardrail_prohibidas" in capsys.readouterr().err

    def test_un_fichero_que_no_es_capitulo_no_se_mira(self, tmp_path: Path) -> None:
        documento = tmp_path / "architecture.md"
        documento.write_text("Beatriz " * 3, encoding="utf-8")
        assert cli_hook.main([], _evento("Write", documento)) == 0

    def test_un_evento_ilegible_no_bloquea(self) -> None:
        assert cli_hook.main([], io.StringIO("no es json")) == 0

    def test_la_skill_sigue_pasando_la_ruta_como_argumento(self, capitulo: Path) -> None:
        assert cli_hook.main([str(capitulo)]) == 0


class TestHookDePolicy:
    def test_deniega_un_write_que_introduce_un_termino_prohibido(
        self, capitulo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        evento = _evento("Write", capitulo, content=LIMPIO + " Y penso en beatriz.")
        assert cli_policy.main(evento) == cli_hook.BLOQUEA
        assert "Beatriz" in capsys.readouterr().err

    def test_deniega_por_el_fragmento_nuevo_de_un_edit(self, capitulo: Path) -> None:
        evento = _evento("Edit", capitulo, old_string="padre", new_string="padre y Beatriz")
        assert cli_policy.main(evento) == cli_hook.BLOQUEA

    def test_mira_cada_fragmento_de_un_multiedit(self, capitulo: Path) -> None:
        evento = _evento(
            "MultiEdit",
            capitulo,
            edits=[
                {"old_string": "muelle", "new_string": "puerto"},
                {"old_string": "padre", "new_string": "Beatriz"},
            ],
        )
        assert cli_policy.main(evento) == cli_hook.BLOQUEA

    def test_deja_pasar_una_edicion_limpia(self, capitulo: Path) -> None:
        evento = _evento("Edit", capitulo, old_string="muelle", new_string="puerto")
        assert cli_policy.main(evento) == 0

    def test_no_juzga_lo_que_la_edicion_no_introduce(self, capitulo: Path) -> None:
        """La policy mira lo que entra; lo que ya estaba lo juzga el hook de validación."""
        capitulo.write_text(LIMPIO + " Beatriz.", encoding="utf-8")
        evento = _evento("Edit", capitulo, old_string="muelle", new_string="puerto")
        assert cli_policy.main(evento) == 0

    def test_fuera_de_los_capitulos_no_aplica(self, tmp_path: Path) -> None:
        documento = tmp_path / "notas.md"
        assert cli_policy.main(_evento("Write", documento, content="Beatriz")) == 0


def test_la_configuracion_declara_los_dos_hooks() -> None:
    """Lo que Claude Code carga de verdad: un hook por momento, y los dos sobre capítulos."""
    raiz = Path(__file__).resolve().parents[3]
    hooks = json.loads((raiz / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]
    pre = hooks["PreToolUse"][0]["hooks"][0]["command"]
    post = hooks["PostToolUse"][0]["hooks"][0]["command"]
    assert "cli_policy" in pre and "cli_hook" in post
    assert "CLAUDE_FILE_PATH" not in pre + post, "la ruta llega por stdin, no por entorno"
