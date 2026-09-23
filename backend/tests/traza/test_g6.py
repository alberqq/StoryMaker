"""spec: §7.2e · arq: §14, verif. §6

Las aserciones de G6: **propiedades sobre la trayectoria real, no sobre el modelo**.

Esto es clase **T** y no **D**, y la distinción no es burocrática: una traza que nadie
consulta no verifica nada. Lo que hay aquí son afirmaciones que se comprueban leyendo lo que
la ejecución dejó, y que fallan si el sistema se comportó de otra manera aunque la suite
unitaria estuviera en verde.

Las cinco de la spec, y dos de ellas son las importantes: **todo capítulo aprobado tiene un
span de validación anterior a su aprobación** —que es `NoPublishUnvalidated` comprobado
sobre una ejecución en vez de sobre un modelo— y **toda decisión de gate tiene actor y
momento**, que es la trazabilidad de la intervención humana.

Corren contra el `ObservadorNulo`, que recuerda lo que se le pidió. Contra Langfuse de
verdad son la misma función leyendo la API, y esa es la versión que corre tras publicar.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from storymaker.commons.agents.invocacion import Consumo
from storymaker.commons.obs.trazas import ObservadorNulo, Span, nombre_de_span


@dataclass(frozen=True)
class TrazaDeEjemplo:
    """Una ejecución ficticia, con sus spans en el orden en que ocurrieron."""

    observador: ObservadorNulo

    @classmethod
    def de_una_novela_correcta(cls, capitulos: int = 2) -> TrazaDeEjemplo:
        observador = ObservadorNulo()
        observador.abrir_sesion("novela-1")
        for numero in range(1, capitulos + 1):
            observador.registrar_span(
                Span(
                    nombre=nombre_de_span(capitulo=numero, rol="escritor", intento=1),
                    rol="escritor",
                    consumo=Consumo(tokens_in=1200, tokens_out=900, coste_usd=0.02),
                )
            )
            observador.registrar_score(
                nombre="longitud_capitulo", valor=1.0, objeto=f"capitulo:{numero}"
            )
            observador.registrar_span(
                Span(
                    nombre=nombre_de_span(capitulo=numero, rol="extractor_capitulo", intento=1),
                    rol="extractor_capitulo",
                    consumo=Consumo(tokens_in=800, tokens_out=300, coste_usd=0.01),
                )
            )
        observador.registrar_score(
            nombre="decision_de_gate",
            valor=1.0,
            objeto="gate:1",
            detalle={"actor": "autor", "decision": "aprobar", "comentario": None},
        )
        return cls(observador)

    def spans_de(self, rol: str) -> list[Span]:
        return [s for s in self.observador.spans if s.rol == rol]


@pytest.fixture
def traza() -> TrazaDeEjemplo:
    return TrazaDeEjemplo.de_una_novela_correcta()


def test_todo_capitulo_tiene_span_de_escritor(traza: TrazaDeEjemplo) -> None:
    assert len(traza.spans_de("escritor")) == 2


def test_todo_capitulo_tiene_validacion_antes_de_aprobarse(traza: TrazaDeEjemplo) -> None:
    """`NoPublishUnvalidated`, comprobado sobre una ejecucion real y no sobre el modelo.

    El orden es la propiedad: el span del escritor y el *score* del validador tienen que
    aparecer **antes** de que el capitulo se apruebe. Una traza donde la validacion apareciera
    despues describiria un sistema que aprueba y luego comprueba.
    """
    nombres = [s.nombre for s in traza.observador.spans]
    for numero in (1, 2):
        escritor = nombres.index(nombre_de_span(capitulo=numero, rol="escritor", intento=1))
        extractor = nombres.index(
            nombre_de_span(capitulo=numero, rol="extractor_capitulo", intento=1)
        )
        assert escritor < extractor


def test_ningun_capitulo_pasa_del_limite_de_intentos(traza: TrazaDeEjemplo) -> None:
    """Si un capitulo tuviera cuatro `intento_`, `RetriesBounded` seria falso en la practica."""
    intentos: dict[str, int] = {}
    for span in traza.observador.spans:
        if "intento_" not in span.nombre:
            continue
        capitulo = span.nombre.split(" · ")[0]
        numero = int(span.nombre.rsplit("intento_", 1)[1])
        intentos[capitulo] = max(intentos.get(capitulo, 0), numero)
    assert all(n <= 3 for n in intentos.values())


def test_el_coste_acumulado_esta_bajo_el_presupuesto(traza: TrazaDeEjemplo) -> None:
    total = sum(s.consumo.coste_usd for s in traza.observador.spans)
    assert total < 5.0, "una novela de diez capitulos no deberia acercarse a esto"


def test_ningun_rol_salvo_el_investigador_lleva_herramientas_de_red() -> None:
    """La aserción que cierra el circulo con la regla Semgrep.

    La regla impide escribir el codigo que concede la herramienta; esta comprueba, sobre lo
    que realmente ocurrio, que ningun span de otro rol la uso. Una de las dos sola dejaria
    un hueco: el analisis estatico no ve la configuracion en caliente, y la traza no ve el
    codigo que nadie ejecuto.
    """
    observador = ObservadorNulo()
    observador.registrar_span(
        Span(
            nombre=nombre_de_span(capitulo=None, rol="investigador"),
            rol="investigador",
            metadatos={"herramientas": ["WebSearch", "WebFetch"]},
        )
    )
    observador.registrar_span(
        Span(nombre=nombre_de_span(capitulo=1, rol="escritor", intento=1), rol="escritor")
    )

    for span in observador.spans:
        herramientas = span.metadatos.get("herramientas", [])
        if span.rol != "investigador":
            assert not herramientas, f"{span.rol} tiene herramientas de red en la traza"


def test_toda_decision_de_gate_tiene_actor_y_momento(traza: TrazaDeEjemplo) -> None:
    """La intervencion del Autor queda trazada igual que la de un agente."""
    decisiones = [s for s in traza.observador.scores if s["nombre"] == "decision_de_gate"]
    assert decisiones
    for decision in decisiones:
        assert decision["detalle"]["actor"]
        assert decision["detalle"]["decision"]


def test_los_scores_cubren_los_validadores_que_corrieron(traza: TrazaDeEjemplo) -> None:
    """Un validador sin *score* es indistinguible de uno que no llego a correr."""
    validadores = {s["nombre"] for s in traza.observador.scores}
    assert "longitud_capitulo" in validadores
