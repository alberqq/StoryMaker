"""spec: §4.5 · arq: §9, §11a, §11b, §11c · verif. G1, G3, G5

Las piezas de validación que cierran la novela antes de publicarla.

- `render_visual` en un navegador de verdad: lo que un lector vería, no lo que dice el HTML.
- El rechazo de la publicación: cómo cita capítulos, adónde lleva la arista y cómo llega al
  escritor el motivo cuando el Autor rehace.
- Lean en una copia de trabajo, para no pisar el caso de ejemplo versionado.
- La revisión humana: la hoja, su validación y el acta comparada con el juez.
"""

from __future__ import annotations

import json
import shutil
from typing import ClassVar

import aiosqlite
import pytest
from dobles.fabrica import NovelaDePrueba, poblar

from storymaker.commons.context import bloques
from storymaker.commons.db.repos import arnes, texto
from storymaker.commons.graph.aristas import tras_publish
from storymaker.commons.graph.estado import EstadoNovela, estado_inicial
from storymaker.commons.obs.trazas import ObservadorNulo
from storymaker.commons.validation.modelos import Incidencia, Severidad
from storymaker.publication import render, revision_humana
from storymaker.publication.nodos import capitulos_citados, registrar_rechazo
from storymaker.writing import gate as manuscrito


@pytest.fixture
async def novela(db: aiosqlite.Connection) -> NovelaDePrueba:
    return await poblar(db)


def _lectura(**cambios: object) -> render.Lectura:
    base: dict[str, object] = {
        "titulo": "La novela",
        "portada": "<h1>La novela</h1>",
        "indice": '<ol><li><a href="#capitulo-1">Capitulo 1</a></li>'
        '<li><a href="#capitulo-2">Capitulo 2</a></li></ol>',
        "capitulos": ((1, "<p>Uno.</p>"), (2, "<p>Dos.</p>")),
        "personajes": "<ul><li>Manuel Ferrer — armador</li></ul>",
    }
    base.update(cambios)
    return render.Lectura(**base)  # type: ignore[arg-type]


def _estado(**cambios: object) -> EstadoNovela:
    base = estado_inicial(
        novela="proyectos/n.db",
        fase_run_id=1,
        n_capitulos=5,
        max_intentos=2,
        huecos=0,
        gates_enabled=True,
    )
    base.update(cambios)  # type: ignore[typeddict-item]
    return base


def _bloqueante(mensaje: str, ubicacion: str | None = None, **extra: str) -> Incidencia:
    return Incidencia(
        validador=extra.get("validador", "render_visual"),
        severidad=Severidad.BLOQUEANTE,
        mensaje=mensaje,
        ubicacion=ubicacion,
        propuesta=extra.get("propuesta"),
    )


class TestRenderEnNavegador:
    """Chromium está instalado en el entorno de pruebas: se ejercita el navegador real."""

    async def test_una_lectura_sana_no_abre_nada(self) -> None:
        assert await render.en_navegador(_lectura()) == []

    async def test_un_capitulo_sin_texto_cita_su_numero(self) -> None:
        incidencias = await render.en_navegador(_lectura(capitulos=((1, "<p>Uno.</p>"), (2, ""))))
        assert incidencias is not None
        assert [(i.ubicacion, i.bloquea) for i in incidencias] == [("cap2", True)]
        assert "sin texto" in incidencias[0].mensaje

    async def test_un_enlace_del_indice_que_no_lleva_a_ninguna_parte(self) -> None:
        indice = '<ol><li><a href="#capitulo-1">1</a></li><li><a href="#capitulo-9">9</a></li></ol>'
        incidencias = await render.en_navegador(_lectura(indice=indice))
        assert incidencias is not None
        assert any(i.ubicacion == "cap9" and "ninguna parte" in i.mensaje for i in incidencias)

    async def test_una_portada_que_no_se_pinta(self) -> None:
        """En el HTML está; en pantalla no se ve. La comprobación estructural no lo notaría."""
        oculta = _lectura(portada='<h1 style="display:none">La novela</h1>')
        assert render.estructura(oculta) == []
        incidencias = await render.en_navegador(oculta)
        assert incidencias is not None
        assert [i.ubicacion for i in incidencias] == ["portada"]

    async def test_sin_navegador_avisa_y_no_para(self, monkeypatch: pytest.MonkeyPatch) -> None:
        async def ausente(_: render.Lectura) -> None:
            return None

        monkeypatch.setattr(render, "en_navegador", ausente)
        incidencias = await render.render_visual(_lectura())
        assert len(incidencias) == 1
        assert not incidencias[0].bloquea

    async def test_la_candidata_es_la_misma_lectura_que_la_version(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Lo que se juzga antes de escribir es exactamente lo que se publicaría."""
        candidata = await render.construir_lectura_candidata(db, [novela.version_capitulo_1])
        version = await texto.publicar_version(
            db, numero=1, capitulo_version_ids=[novela.version_capitulo_1]
        )
        assert candidata == await render.construir_lectura(db, version)


class TestRechazoDeLaPublicacion:
    def test_la_cronologia_cita_capitulos_por_la_clave_del_evento(self) -> None:
        de_python = _bloqueante("Nace despues.", "cap4-esc10", validador="cronologia_publicacion")
        de_lean = _bloqueante(
            "Un personaje participa en un evento anterior a su nacimiento.",
            "I1",
            validador="cronologia_publicacion",
            propuesta="evento 5 · cap1-ritual · momento 42733\nevento 13 · cap2-convocatoria",
        )
        assert capitulos_citados(de_python) == [4]
        assert capitulos_citados(de_lean) == [1, 2]

    def test_la_arista_sigue_el_tope_del_juez(self) -> None:
        assert tras_publish(_estado(hay_bloqueantes=False)) == "Idle"
        assert tras_publish(_estado(hay_bloqueantes=True, rechazos_juez=1)) == "AwaitApproval4"
        assert tras_publish(_estado(hay_bloqueantes=True, rechazos_juez=2)) == "Fail"

    async def test_el_rechazo_llega_al_gate_y_elige_los_capitulos(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await registrar_rechazo(db, (_bloqueante("El capitulo 2 se pinta sin texto.", "cap2"),))
        informe = await manuscrito.construir(db)
        assert informe.rechazos == (("render_visual", "El capitulo 2 se pinta sin texto."),)
        assert "La publicacion rechazo la version candidata" in informe.como_texto()
        assert await manuscrito.capitulos_a_rehacer(db, 2) == [2]

    async def test_cada_rechazo_sustituye_al_anterior(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await registrar_rechazo(db, (_bloqueante("Primero.", "cap1"),))
        await registrar_rechazo(db, (_bloqueante("Segundo.", "cap2"),))
        assert await arnes.incidencias_sin_capitulo(db, "render_visual") == ["Segundo."]

    async def test_sin_citas_se_rehace_el_ultimo(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        assert await manuscrito.capitulos_a_rehacer(db, 2) == [2]

    async def test_el_motivo_viaja_al_encargo_del_capitulo_que_cita(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await registrar_rechazo(db, (_bloqueante("El capitulo 1 se pinta sin texto.", "cap1"),))
        assert await bloques.motivos_para_rehacer(db, 1) == ["El capitulo 1 se pinta sin texto."]
        assert await bloques.motivos_para_rehacer(db, 2) == []


class TestCoberturaEnElGate:
    async def test_deja_incidencia_y_score(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        observador = ObservadorNulo()
        informe = await manuscrito.revisar(db, observador)
        async with db.execute(
            "SELECT valor FROM score WHERE validador = 'cobertura_personalizacion'"
        ) as cursor:
            notas = [float(f["valor"]) for f in await cursor.fetchall()]
        assert notas == [0.0 if informe.incidencias else 1.0]
        assert len(await arnes.incidencias_sin_capitulo(db, "cobertura_personalizacion")) == len(
            informe.incidencias
        )


@pytest.mark.skipif(shutil.which("lake") is None, reason="sin `lake` no hay Lean que ejecutar")
class TestLeanEnCopia:
    async def test_no_pisa_el_generado_del_repositorio(self) -> None:
        from storymaker.commons.formal.generador import Evento, NovelaLean, Persona
        from storymaker.commons.formal.runner import (
            FICHERO_GENERADO,
            PROYECTO_POR_DEFECTO,
            verificar,
        )

        versionado = (PROYECTO_POR_DEFECTO / FICHERO_GENERADO).read_bytes()
        novela = NovelaLean(
            personas=(Persona(id=1, nombre="A", nacimiento=1000, muerte=None),),
            objetos=(),
            eventos=(
                Evento(
                    id=1,
                    clave="cap1-e",
                    momento=10,
                    lugar=0,
                    participantes=(1,),
                    objetos=(),
                    origen="narrativo",
                ),
            ),
        )
        veredicto = await verificar(novela)
        assert not veredicto.correcto, "el evento cae antes del nacimiento: I1"
        assert (PROYECTO_POR_DEFECTO / FICHERO_GENERADO).read_bytes() == versionado

    async def test_lean_decide_y_python_explica(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """El editor necesita saber quién y cuándo; Lean solo dice qué invariante cae."""
        from storymaker.commons.formal.cronologia import verificar_cronologia
        from storymaker.commons.formal.generador import Evento, NovelaLean, Persona

        monkeypatch.setenv("STORYMAKER_LEAN", "1")
        novela = NovelaLean(
            personas=(Persona(id=1, nombre="Manuel Ferrer", nacimiento=1000, muerte=None),),
            objetos=(),
            eventos=(
                Evento(
                    id=1,
                    clave="cap1-e",
                    momento=10,
                    lugar=0,
                    participantes=(1,),
                    objetos=(),
                    origen="narrativo",
                ),
            ),
        )
        (incidencia,) = await verificar_cronologia(novela, bloquea=True, validador="x")
        assert "Manuel Ferrer" in incidencia.mensaje
        assert incidencia.bloquea


class TestRevisionHumana:
    def _hoja(self, **notas: int) -> str:
        valores = {c: notas.get(c, 7) for c in revision_humana.criterios()}
        criterios = {
            c: {"valor": v, "justificacion": f"justificacion suficiente de {c}"}
            for c, v in valores.items()
        }
        return json.dumps({"novela": "n", "version": 1, "revisor": "R", "criterios": criterios})

    def test_la_hoja_nombra_todos_los_criterios_y_no_copia_preguntas(self) -> None:
        hoja = revision_humana.hoja("n", 1)
        for criterio in revision_humana.criterios():
            assert f"  {criterio}:" in hoja
        assert "pregunta:" not in hoja
        assert "¿" not in hoja, "las preguntas se leen en rubrica.yaml, no en una copia"
        assert "juez" not in hoja.split("criterios:")[1]

    def test_una_hoja_incompleta_no_se_registra(self) -> None:
        with pytest.raises(revision_humana.HojaInvalida, match="Faltan criterios"):
            revision_humana.leer_hoja("criterios: {continuidad: {valor: 7}}")

    def test_una_nota_fuera_de_escala_no_se_registra(self) -> None:
        with pytest.raises(revision_humana.HojaInvalida, match="entero"):
            revision_humana.leer_hoja(self._hoja(ritmo=11))

    async def test_registra_el_score_y_compara_con_el_juez(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await texto.publicar_version(db, numero=1, capitulo_version_ids=[novela.version_capitulo_1])
        juez = {c: 8 for c in revision_humana.criterios()}
        await arnes.registrar_score(
            db,
            objeto_tipo="novela",
            objeto_id=1,
            validador="juez_rubrica",
            valor=8.0,
            detalle={**juez, "contradicciones": []},
        )
        acta = await revision_humana.registrar_revision(db, ObservadorNulo(), self._hoja(ritmo=3))
        assert [f.criterio for f in acta.divergencias] == ["ritmo"]
        assert acta.media_juez == 8.0
        async with db.execute(
            "SELECT valor FROM score WHERE validador = 'revision_humana'"
        ) as cursor:
            fila = await cursor.fetchone()
        assert fila is not None and float(fila["valor"]) == acta.media_persona
        texto_acta = acta.como_markdown()
        assert "| ritmo | 3 | 8 |" in texto_acta
        assert "ritmo: persona 3, juez 8 (-5)" in texto_acta

    async def test_una_version_que_no_existe_no_se_registra(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        with pytest.raises(revision_humana.HojaInvalida, match="version 1"):
            await revision_humana.registrar_revision(db, ObservadorNulo(), self._hoja())


class TestEscenarioDeLaEscena:
    """Lo encontró la inspección en el navegador: las escenas de `metro` sin escenario."""

    CLAVES: ClassVar[dict[str, int]] = {
        "escenario:sala_telegrafia": 1,
        "escenario:cocina_casa": 2,
        "Julia": 3,
    }

    def test_la_clave_exacta(self) -> None:
        from storymaker.plotting.escaleta import resolver_escenario

        assert resolver_escenario("cocina_casa", self.CLAVES, clave_de_escena="e1") == 2

    def test_otra_grafia_se_resuelve_y_se_dice(self) -> None:
        from storymaker.plotting.escaleta import resolver_escenario

        adivinados: list[str] = []
        valor = resolver_escenario(
            "Sala Telegrafía",
            self.CLAVES,
            clave_de_escena="e2",
            resueltos_por_parecido=adivinados,
        )
        assert valor == 1
        assert adivinados == ["escena e2: escenario «Sala Telegrafía»"]

    def test_lo_que_no_se_resuelve_se_ensena(self) -> None:
        from storymaker.plotting.escaleta import resolver_escenario

        perdidos: list[str] = []
        assert (
            resolver_escenario(
                "el puerto", self.CLAVES, clave_de_escena="e3", sin_resolver=perdidos
            )
            is None
        )
        assert perdidos == ["escena e3: escenario «el puerto»"]
