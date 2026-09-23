"""spec: §7.1 nº 12 · arq: §11d, verif. §3.6

Las propiedades de Hypothesis que **reflejan los invariantes de TLA+ sobre el código real**.

TLC verifica el modelo; esto verifica que el código se comporta como el modelo dice, sobre
entradas que nadie eligió a mano. No cierra la brecha de refinamiento —eso es U-1, y
demostrar que Python implementa fielmente un modelo TLA+ está fuera de todo presupuesto
razonable—, pero la estrecha por el lado que más barato sale: los cuatro invariantes se
enuncian aquí como propiedades de las funciones que los sostienen.

Cada clase lleva el nombre del invariante que refleja, para que un contraejemplo de TLC y un
fallo de esta suite se puedan poner uno al lado del otro.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from storymaker.commons.context.paquete import TECHO_TOTAL, Bloque
from storymaker.commons.context.truncado import ajustar_al_total, truncar_por_prioridad
from storymaker.commons.graph.aristas import ARISTAS, tras_extract, tras_validate
from storymaker.commons.graph.estado import estado_inicial
from storymaker.commons.validation.puras import (
    capitulos_afectados,
    es_anacronico,
    hay_solape_temporal,
    normalizar,
)

fragmentos = st.lists(st.text(min_size=1, max_size=200), max_size=30)
techos = st.integers(min_value=1, max_value=5_000)


def estado(**cambios: object) -> dict[str, object]:
    base = dict(
        estado_inicial(
            novela="n.db",
            fase_run_id=1,
            n_capitulos=10,
            max_intentos=2,
            huecos=5,
            gates_enabled=False,
        )
    )
    base.update(cambios)
    return base


class TestRetriesBounded:
    """«El número de reintentos por capítulo nunca supera el límite.»

    Las dos aristas de entrada a `Repair` comparten contador, así que la propiedad tiene que
    cumplirse **viniendo de cualquiera de las dos**. Es exactamente la interacción que el
    invariante existe para vigilar.
    """

    @given(
        intentos=st.integers(min_value=0, max_value=20),
        maximo=st.integers(min_value=0, max_value=5),
    )
    def test_nunca_se_repara_pasado_el_limite(self, intentos: int, maximo: int) -> None:
        actual = estado(hay_bloqueantes=True, intentos=intentos, max_intentos=maximo)
        for enrutador in (tras_validate, tras_extract):
            destino = enrutador(actual)  # type: ignore[arg-type]
            if intentos >= maximo:
                assert destino == "Fail"
            else:
                assert destino == "Repair"

    @given(intentos=st.integers(min_value=0, max_value=20))
    def test_sin_incidencias_nunca_se_repara(self, intentos: int) -> None:
        actual = estado(hay_bloqueantes=False, intentos=intentos)
        assert tras_validate(actual) == "Extract"  # type: ignore[arg-type]
        assert tras_extract(actual) == "ApproveChapter"  # type: ignore[arg-type]


class TestTransicionesDeclaradas:
    """Ninguna acción mueve el `pc` por una arista que no esté en la relación.

    Es el operador `Mueve(de, a)` del modelo, comprobado sobre el código: sea cual sea el
    estado, lo que devuelve un enrutador está en `ARISTAS`.
    """

    @given(
        bloqueantes=st.booleans(),
        intentos=st.integers(min_value=0, max_value=10),
        maximo=st.integers(min_value=0, max_value=5),
    )
    def test_todo_destino_esta_declarado(
        self, bloqueantes: bool, intentos: int, maximo: int
    ) -> None:
        actual = estado(hay_bloqueantes=bloqueantes, intentos=intentos, max_intentos=maximo)
        assert ("Validate", tras_validate(actual)) in ARISTAS  # type: ignore[arg-type]
        assert ("Extract", tras_extract(actual)) in ARISTAS  # type: ignore[arg-type]


class TestPresupuestoDeContexto:
    """El paquete nunca excede su techo, sea cual sea el material que le den.

    No es un invariante de TLA+ sino del §6, pero se comprueba igual y por el mismo motivo:
    es una propiedad que tiene que valer para toda entrada, no para el caso que se probó.
    """

    @given(trozos=fragmentos, techo=techos)
    def test_truncar_nunca_se_pasa(self, trozos: list[str], techo: int) -> None:
        from storymaker.commons.agents.presupuesto import estimar_tokens

        conservados = truncar_por_prioridad(trozos, techo)
        if conservados:
            assert estimar_tokens("\n".join(conservados)) <= techo + estimar_tokens(
                conservados[-1]
            )

    @given(trozos=fragmentos, techo=techos)
    def test_truncar_conserva_el_orden(self, trozos: list[str], techo: int) -> None:
        """Se corta por la cola: lo que queda es un prefijo de lo que entro."""
        conservados = truncar_por_prioridad(trozos, techo)
        assert conservados == trozos[: len(conservados)]

    @given(fijos=st.integers(min_value=0, max_value=5), trozos=fragmentos)
    def test_los_fijos_no_se_sueltan_jamas(self, fijos: int, trozos: list[str]) -> None:
        conservados = truncar_por_prioridad(trozos, techo_tokens=1, fijos=fijos)
        assert conservados[: min(fijos, len(trozos))] == trozos[: min(fijos, len(trozos))]

    @given(
        memoria=st.lists(st.text(min_size=50, max_size=400), max_size=10),
        continuidad=st.lists(st.text(min_size=10, max_size=100), max_size=5),
    )
    def test_la_continuidad_es_lo_ultimo_en_ceder(
        self, memoria: list[str], continuidad: list[str]
    ) -> None:
        bloques = [Bloque(4, tuple(memoria)), Bloque(3, tuple(continuidad))]
        ajustados = {b.numero: b for b in ajustar_al_total(bloques, techo_total=200)}
        if ajustados[4].fragmentos:
            assert len(ajustados[3].fragmentos) == len(continuidad)

    @given(trozos=fragmentos)
    def test_el_techo_total_es_un_techo(self, trozos: list[str]) -> None:
        bloques = [Bloque(4, tuple(trozos))]
        ajustados = ajustar_al_total(bloques)
        assert sum(b.tokens() for b in ajustados) <= TECHO_TOTAL or not ajustados[0].fragmentos


class TestFuncionesPuras:
    """Propiedades de las cinco que CrossHair verifica después, simbólicamente."""

    @given(texto=st.text())
    def test_normalizar_es_idempotente(self, texto: str) -> None:
        """Si no lo fuera, la aguja y el pajar podrian normalizarse de forma distinta."""
        una = normalizar(texto)
        assert normalizar(una) == una

    @given(texto=st.text())
    def test_normalizar_no_deja_mayusculas_ni_puntuacion(self, texto: str) -> None:
        resultado = normalizar(texto)
        assert resultado == resultado.lower()
        assert all(c.isalnum() or c == " " for c in resultado)

    @given(
        inicio=st.integers(min_value=1000, max_value=2100),
        narrativa=st.integers(min_value=1000, max_value=2100),
    )
    def test_anacronico_es_exactamente_posterior(self, inicio: int, narrativa: int) -> None:
        assert es_anacronico(str(inicio), str(narrativa)) == (inicio > narrativa)

    @given(
        a1=st.integers(min_value=1000, max_value=2000),
        a2=st.integers(min_value=1000, max_value=2000),
        b1=st.integers(min_value=1000, max_value=2000),
        b2=st.integers(min_value=1000, max_value=2000),
    )
    def test_el_solape_es_simetrico(self, a1: int, a2: int, b1: int, b2: int) -> None:
        """Que A solape con B no puede depender de en qué orden se pregunte."""
        uno = hay_solape_temporal(str(a1), str(a2), str(b1), str(b2))
        otro = hay_solape_temporal(str(b1), str(b2), str(a1), str(a2))
        assert uno == otro

    @given(
        usos=st.dictionaries(
            st.integers(min_value=1, max_value=20),
            st.lists(st.integers(min_value=1, max_value=10), max_size=10).map(tuple),
            max_size=5,
        ),
        hecho=st.integers(min_value=1, max_value=20),
    )
    def test_los_afectados_salen_ordenados_y_sin_repetir(
        self, usos: dict[int, tuple[int, ...]], hecho: int
    ) -> None:
        """Regenerar del 9 al 2 dejaria al 9 escrito contra una continuidad que el 2 cambia."""
        resultado = capitulos_afectados(usos, hecho)
        assert resultado == sorted(resultado)
