"""spec: §3.7, §8 · arq: §11c

Pruebas del generador de Lean y de su *runner*.

Tres cosas se comprueban, y la última importa más que las otras dos. Que el generador
emite **solo datos** —si emitiera los invariantes, cada novela traería su propia definición
de «coherente»—. Que las fechas del corpus se convierten a los momentos que el modelo
espera. Y que **un error de entorno no se confunde nunca con un veredicto**: un `lake`
ausente detiene la invocación y no aprueba el capítulo.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from storymaker.commons.errores import ErrorDeEntorno
from storymaker.commons.formal.generador import (
    EPOCA,
    INVARIANTES,
    Evento,
    NovelaLean,
    Objeto,
    Persona,
    a_momento,
    generar,
)
from storymaker.commons.formal.runner import (
    PROYECTO_POR_DEFECTO,
    AveriaDeLean,
    escribir_generado,
    interpretar,
    verificar,
)


def novela_de_ejemplo() -> NovelaLean:
    """Lo historico y lo narrativo mezclados, que es donde aparecen las incoherencias."""
    return NovelaLean(
        personas=(
            Persona(1, "Federico Gravina", a_momento("1756-08-12") or 0, a_momento("1806-03-09")),
            Persona(2, "Manuel Ferrer", a_momento("1760-03-02") or 0, None),
        ),
        objetos=(
            Objeto(10, "catalejo", a_momento("1608-01-01") or 0, None),
            Objeto(11, "telegrafo electrico", a_momento("1837-01-01") or 0, None),
        ),
        eventos=(
            Evento(100, "trafalgar", a_momento("1805-10-21") or 0, 1, (1,), (10,), "historico"),
            Evento(
                101, "manuel-en-el-muelle", a_momento("1805-04-11") or 0, 2, (2,), (), "narrativo"
            ),
        ),
    )


class TestConversionDeFechas:
    def test_la_epoca_es_el_cero(self) -> None:
        assert a_momento(EPOCA.isoformat()) == 0

    def test_una_fecha_posterior_es_positiva(self) -> None:
        """1826 y no 1827: 1800 no es bisiesto en el calendario gregoriano."""
        assert a_momento("1805-01-01") == 1826

    def test_una_fecha_anterior_es_negativa(self) -> None:
        """El modelo admite momentos negativos: hay corpus muy anterior a la epoca."""
        assert (a_momento("1608-01-01") or 0) < 0

    @pytest.mark.parametrize("fecha", ["1805", "1805-04", "1805-04-11"])
    def test_admite_precision_desigual(self, fecha: str) -> None:
        """Exigir fecha completa dejaria fuera la mitad del material historico."""
        assert a_momento(fecha) is not None

    def test_sin_fecha_no_hay_restriccion(self) -> None:
        """`none` no es un hueco que rellenar: afirma que no hay restriccion por ese lado."""
        assert a_momento(None) is None
        assert a_momento("sin datar") is None


class TestGenerador:
    def test_emite_solo_datos(self) -> None:
        """Si emitiera los teoremas, «coherente» significaria una cosa distinta por novela."""
        fuente = generar(novela_de_ejemplo())
        assert "theorem" not in fuente
        assert "def Coherente" not in fuente
        assert "import Cronologia.Basico" in fuente
        assert "namespace Cronologia.Generado" in fuente

    def test_declara_las_tres_listas_y_la_novela(self) -> None:
        fuente = generar(novela_de_ejemplo())
        for declaracion in (
            "def personas : List Persona",
            "def objetos : List Objeto",
            "def eventos : List Evento",
            "def novela : Novela",
        ):
            assert declaracion in fuente

    def test_la_muerte_opcional_usa_some_y_none(self) -> None:
        fuente = generar(novela_de_ejemplo())
        assert "muerte := some" in fuente
        assert "muerte := none" in fuente

    def test_una_muerte_negativa_va_entre_parentesis(self) -> None:
        """`some -4035` es una resta para Lean y el fichero no compila."""
        fuente = generar(
            NovelaLean(personas=(Persona(id=7, nombre="Carlos III", nacimiento=-30681, muerte=-4035),))
        )
        assert "muerte := some (-4035)" in fuente
        assert "some -" not in fuente

    def test_el_origen_conserva_la_mezcla(self) -> None:
        fuente = generar(novela_de_ejemplo())
        assert "origen := Origen.historico" in fuente
        assert "origen := Origen.narrativo" in fuente

    def test_escapa_las_comillas_de_los_nombres_de_epoca(self) -> None:
        fuente = generar(
            NovelaLean(eventos=(Evento(1, 'la "calle real"', 0, 1),))
        )
        assert '\\"calle real\\"' in fuente

    def test_una_novela_vacia_sigue_generando_fichero_valido(self) -> None:
        """El capitulo 1 de una novela sin eventos no puede reventar el runner."""
        fuente = generar(NovelaLean())
        assert "def novela : Novela" in fuente

    def test_contrato_contra_el_fichero_de_referencia(self) -> None:
        """Si el generador cambia de forma, la diferencia se ve aqui y no en produccion."""
        referencia = Path(__file__).parent.parent / "formal" / "fixture_cronologia.lean"
        generado = generar(novela_de_ejemplo())
        if not referencia.exists():
            referencia.parent.mkdir(parents=True, exist_ok=True)
            referencia.write_text(generado, encoding="utf-8")
        assert generado == referencia.read_text(encoding="utf-8")


class TestInterpretacion:
    def test_codigo_cero_es_veredicto_favorable(self) -> None:
        veredicto = interpretar(0, "✓ Cronología coherente: 4 eventos, 3 personas.")
        assert veredicto.correcto
        assert veredicto.incidencias == ()

    def test_el_invariante_violado_se_nombra_con_sus_culpables(self) -> None:
        salida = (
            "Cronología incoherente.\n"
            "✗ I1 · participa antes de nacer\n"
            "    evento 101 · cosme-ve-la-batalla · momento 2120 · lugar 1\n"
        )
        veredicto = interpretar(1, salida)
        assert not veredicto.correcto
        assert [i.ubicacion for i in veredicto.incidencias] == ["I1"]
        assert "anterior a su nacimiento" in veredicto.incidencias[0].mensaje
        assert "cosme-ve-la-batalla" in (veredicto.incidencias[0].propuesta or "")

    def test_varios_invariantes_a_la_vez(self) -> None:
        salida = "✗ I1 · participa antes de nacer\n✗ I4 · objeto anacronico\n"
        assert len(interpretar(1, salida).incidencias) == 2

    def test_un_fallo_sin_invariante_es_una_averia(self) -> None:
        """No compilar o no poder ejecutar no es un veredicto: es un error de entorno."""
        for salida in (
            "error: build failed",
            "error: unspecified system_category error (error code: 4551)",
        ):
            with pytest.raises(AveriaDeLean):
                interpretar(1, salida)

    def test_la_averia_es_un_error_de_entorno(self) -> None:
        assert issubclass(AveriaDeLean, ErrorDeEntorno)

    def test_los_cuatro_invariantes_tienen_mensaje(self) -> None:
        assert set(INVARIANTES) == {"I1", "I2", "I3", "I4"}


class TestRunner:
    def test_el_proyecto_por_defecto_es_el_de_formal(self) -> None:
        """El proyecto Lake vive fuera del backend: el arnes lo invoca, no lo construye."""
        assert PROYECTO_POR_DEFECTO.name == "lean"
        assert PROYECTO_POR_DEFECTO.parent.name == "formal"

    def test_escribe_donde_el_proyecto_lo_espera(self, tmp_path: Path) -> None:
        destino = escribir_generado(novela_de_ejemplo(), proyecto=tmp_path)
        assert destino == tmp_path / "Cronologia" / "Generado.lean"
        assert "namespace Cronologia.Generado" in destino.read_text(encoding="utf-8")

    async def test_sin_proyecto_lake_es_error_de_entorno(self, tmp_path: Path) -> None:
        if shutil.which("lake") is None:
            pytest.skip("sin `lake` el error salta antes, y eso lo cubre la otra prueba")
        with pytest.raises(ErrorDeEntorno):
            await verificar(novela_de_ejemplo(), proyecto=tmp_path)

    @pytest.mark.skipif(shutil.which("lake") is not None, reason="lake esta instalado")
    async def test_sin_lake_es_error_de_entorno_y_no_veredicto(self, tmp_path: Path) -> None:
        """La distincion de la que depende que no se aprueben capitulos por averia."""
        with pytest.raises(ErrorDeEntorno) as fallo:
            await verificar(novela_de_ejemplo(), proyecto=tmp_path)
        assert "lake" in str(fallo.value)
        assert "en lugar de aprobarlo" in str(fallo.value)


class TestAveriaCaeAPython:
    """Una avería de Lean no aprueba ni suspende: juzga Python (arq. §11c)."""

    async def test_la_averia_la_juzga_python_con_la_misma_severidad(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from storymaker.commons.formal import cronologia, runner

        async def averiado(_novela: NovelaLean) -> None:
            raise AveriaDeLean("error code: 4551")

        monkeypatch.setattr(cronologia, "lean_activo", lambda: True)
        monkeypatch.setattr(runner, "verificar", averiado)
        antes_de_nacer = NovelaLean(
            personas=(Persona(1, "Manuel Ferrer", 1000, None),),
            eventos=(Evento(1, "cap1-e", 10, 0, (1,), (), "narrativo"),),
        )
        incidencias = await cronologia.verificar_cronologia(antes_de_nacer, bloquea=True)
        assert incidencias, "Python ve que participa antes de nacer"
        assert all(i.bloquea for i in incidencias)
        assert "Manuel Ferrer" in incidencias[0].mensaje

        coherente = NovelaLean(
            personas=(Persona(1, "Manuel Ferrer", 1, None),),
            eventos=(Evento(1, "cap1-e", 10, 0, (1,), (), "narrativo"),),
        )
        assert await cronologia.verificar_cronologia(coherente, bloquea=True) == []
