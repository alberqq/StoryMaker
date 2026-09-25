"""spec: §4.3 · arq: §4, §11a

Pruebas unitarias de `specs/trama-rehacible/spec.md` §3.2, §3.5, §3.6, §4.4 y §4.5: las
claves enumeradas en el contrato del arquitecto, los anclajes escritos como frase, la
reparación que respeta la fecha, el aviso de lo inventado sobre personajes históricos, el
orden de los hitos y la fecha de nacimiento de época del homenajeado.
"""

from __future__ import annotations

import json

import aiosqlite
import pytest
from dobles.fabrica import NovelaDePrueba, poblar
from dobles.vectorizador import VectorizadorFalso

from storymaker.commons.db.repos import arnes, mundo
from storymaker.commons.db.repos import intake as repo_intake
from storymaker.commons.formal.generador import NACIMIENTO_DESCONOCIDO, nacimiento_de
from storymaker.commons.validation.escaleta import arco_anclado
from storymaker.commons.validation.modelos import ArcoEnRevision, EscaletaEnRevision
from storymaker.intake.esquemas import Brief, Periodo
from storymaker.plotting import gate
from storymaker.plotting.canon import nacimiento_de_epoca
from storymaker.plotting.escaleta import (
    mapa_de_claves,
    por_parecido,
    resolver_anclaje,
)
from storymaker.plotting.esquemas import SalidaArquitecto, con_claves


@pytest.fixture
async def novela(db: aiosqlite.Connection) -> NovelaDePrueba:
    return await poblar(db)


def _brief(**cambios: object) -> Brief:
    base: dict[str, object] = {
        "nombre_homenajeado": "Julia Montero",
        "fecha_nacimiento": "1967-05-21",
        "rol_epoca": "telegrafista",
        "ocasion": "sesenta cumpleanos",
        "periodo": Periodo(inicio=1917, fin=1919, denominacion="Restauracion"),
        "lugar": "Madrid",
        "genero": "novela historica",
        "tono": "calido",
    }
    base.update(cambios)
    return Brief(**base)  # type: ignore[arg-type]


async def _guardar_brief(db: aiosqlite.Connection, contenido: dict[str, object]) -> None:
    fase_run = await arnes.abrir_fase_run(db, "intake")
    await db.execute(
        "INSERT INTO intake_brief (fase_run_id, json, hash) VALUES (?, ?, 'h')",
        (fase_run, json.dumps(contenido)),
    )


class TestClavesEnElContrato:
    def test_el_esquema_enumera_las_claves_validas(self) -> None:
        esquema = con_claves([12, 13], [1]).model_json_schema()
        campos = esquema["$defs"]["AnclajePropuesto"]["properties"]
        assert campos["hecho"]["anyOf"][0]["enum"] == ["#12", "#13"]
        assert campos["dato"]["anyOf"][0]["enum"] == ["#1"]

    def test_la_enumeracion_guia_y_no_rechaza(self) -> None:
        """Un anclaje mal escrito no tumba la salida: se resuelve o avisa al volcar."""
        salida = con_claves([12], [1]).model_validate(
            {
                "premisa": "p",
                "tema": "t",
                "capitulos": [
                    {
                        "numero": 1,
                        "escenas": [
                            {"clave": "E1", "orden": 1, "anclajes": [{"hecho": "una frase"}]}
                        ],
                    }
                ],
            }
        )
        assert isinstance(salida, SalidaArquitecto)
        assert salida.capitulos[0].escenas[0].anclajes[0].hecho == "una frase"


HECHOS = {
    13: "Los telegrafistas trabajaban en turnos de ocho horas bajo jefes de sala",
    15: "El Metro de Madrid se inauguro el 17 de octubre de 1919",
}
DATOS = {1: "aprendio el alfabeto Morse con su padre golpeando la mesa de la cocina"}


class TestAnclajesComoFrase:
    def _resolver(self, hecho: str | None, dato: str | None = None) -> object:
        return resolver_anclaje(
            hecho,
            dato,
            hechos=mapa_de_claves(HECHOS),
            datos=mapa_de_claves(DATOS),
            textos_de_hecho=HECHOS,
            textos_de_dato=DATOS,
        )

    def test_la_clave_en_su_campo_no_es_parecido(self) -> None:
        resuelto = self._resolver("#15")
        assert resuelto is not None and resuelto.hecho_id == 15  # type: ignore[attr-defined]
        assert not resuelto.por_parecido  # type: ignore[attr-defined]

    def test_un_elemento_escrito_en_el_campo_del_hecho_es_el_elemento(self) -> None:
        """Era la causa de la mitad de los anclajes sin resolver del primer `metro`."""
        resuelto = self._resolver(DATOS[1])
        assert resuelto is not None and resuelto.dato_id == 1  # type: ignore[attr-defined]
        assert not resuelto.por_parecido  # type: ignore[attr-defined]

    def test_una_frase_parecida_se_resuelve_y_se_marca(self) -> None:
        resuelto = self._resolver("los telegrafistas trabajaban en turnos de ocho horas")
        assert resuelto is not None and resuelto.hecho_id == 13  # type: ignore[attr-defined]
        assert resuelto.por_parecido  # type: ignore[attr-defined]

    def test_lo_que_no_se_parece_a_nada_sigue_sin_resolver(self) -> None:
        assert self._resolver("una tormenta sobre el Cantabrico") is None

    def test_una_sola_palabra_en_comun_no_basta(self) -> None:
        assert por_parecido(HECHOS, "el Metro") is None


class TestReparacionConFecha:
    def test_la_fecha_estrecha_las_candidatas(self) -> None:
        fechas: list[object] = ["agosto de 1917", "1917-10-02", "octubre de 1919", None]
        assert gate.escenas_de_su_fecha("inauguracion en octubre de 1919", fechas) == [2]
        assert gate.escenas_de_su_fecha("en 1917", fechas) == [0, 1]
        assert gate.escenas_de_su_fecha("octubre de 1917", fechas) == [1]

    def test_sin_fecha_o_sin_escena_de_su_anio_compiten_todas(self) -> None:
        fechas: list[object] = ["1805", "1806"]
        assert gate.escenas_de_su_fecha("sin fecha", fechas) == [0, 1]
        assert gate.escenas_de_su_fecha("en 1700", fechas) == [0, 1]

    @pytest.mark.parametrize(("fecha", "capitulo"), [("1805-04-11", 2), ("1803-01-01", 1)])
    async def test_el_evento_ancla_va_a_la_escena_de_su_fecha(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba, fecha: str, capitulo: int
    ) -> None:
        await db.execute(
            "UPDATE plan_escena SET fecha_narrativa = '1803-01-01' WHERE capitulo_id = "
            "(SELECT id FROM plan_capitulo WHERE numero = 1)"
        )
        await _guardar_brief(db, {"evento_ancla": "la orden", "fecha_evento_ancla": fecha})
        await repo_intake.insertar_dato(
            db,
            tipo="anecdota",
            valor_json='{"valor": "evento ancla: la orden"}',
            origen="entrevista",
            obligatorio=True,
        )
        avisos = await gate.reparar_cobertura(db, VectorizadorFalso())
        (reparado,) = [a for a in avisos if "evento ancla" in a.mensaje]
        assert reparado.ubicacion == f"cap{capitulo}-esc1"


class TestInventadoSobreHistoricos:
    async def test_lo_inventado_que_nombra_a_un_historico_avisa(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await db.execute(
            "INSERT INTO canon_personaje (nombre, tipo, estatus) "
            "VALUES ('Federico Gravina', 'historico_de_fondo', 'almirante')"
        )
        fase_run = await arnes.abrir_fase_run(db, "plotting")
        sobre_el = await mundo.insertar_hecho(
            db,
            fase_run_id=fase_run,
            enunciado="Los carpinteros cobraban a traves del almirante Gravina",
            estado="inferido",
            dimension="estructura_social",
            origen="invencion_autorizada",
            respaldo="no_aplica",
        )
        await mundo.insertar_hecho(
            db,
            fase_run_id=fase_run,
            enunciado="Los carpinteros cobraban los sabados",
            estado="inferido",
            dimension="estructura_social",
            origen="invencion_autorizada",
            respaldo="no_aplica",
        )
        avisos = await gate.invenciones_sobre_historicos(db)
        assert [a.ubicacion for a in avisos] == [f"hecho #{sobre_el}"]
        assert "Federico Gravina" in avisos[0].mensaje
        assert not avisos[0].bloquea

    async def test_el_homenajeado_no_es_un_historico_a_estos_efectos(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        await db.execute("UPDATE canon_personaje SET tipo = 'historico_ficcionalizado'")
        fase_run = await arnes.abrir_fase_run(db, "plotting")
        await mundo.insertar_hecho(
            db,
            fase_run_id=fase_run,
            enunciado="Manuel Ferrer compraba el roble en invierno",
            estado="inferido",
            dimension="cultura_material",
            origen="invencion_autorizada",
            respaldo="no_aplica",
        )
        avisos = await gate.invenciones_sobre_historicos(db)
        assert not [a for a in avisos if "Manuel Ferrer" in a.mensaje]

    async def test_corregir_el_hecho_retira_su_aviso(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """La revisión no se repite al editar: el aviso se recalcula para no mentir."""
        fase_run = await arnes.abrir_fase_run(db, "plotting")
        await db.execute(
            "INSERT INTO canon_personaje (nombre, tipo, estatus) "
            "VALUES ('Federico Gravina', 'historico_de_fondo', 'almirante')"
        )
        hecho = await mundo.insertar_hecho(
            db,
            fase_run_id=fase_run,
            enunciado="Gravina pagaba a los carpinteros",
            estado="inferido",
            dimension="estructura_social",
            origen="invencion_autorizada",
            respaldo="no_aplica",
        )
        await gate.recalcular_invenciones(db)
        assert await arnes.incidencias_sin_capitulo(db, "invencion_sobre_historico")
        await db.execute(
            "UPDATE mundo_hecho SET enunciado = 'El astillero pagaba los sabados' WHERE id = ?",
            (hecho,),
        )
        await gate.recalcular_invenciones(db)
        assert not await arnes.incidencias_sin_capitulo(db, "invencion_sobre_historico")


class TestOrdenDeLosHitos:
    def _escaleta(self, hitos: tuple[int, ...]) -> EscaletaEnRevision:
        return EscaletaEnRevision(
            n_capitulos=5,
            apariciones_por_personaje={1: 5},
            nombres_por_personaje={1: "Julia"},
            arcos=(
                ArcoEnRevision(
                    1, "Julia", "positivo", hitos_por_capitulo=hitos, es_homenajeado=True
                ),
            ),
        )

    def test_dos_hitos_en_el_mismo_capitulo_no_van_hacia_atras(self) -> None:
        assert arco_anclado(self._escaleta((1, 1, 2, 4, 5))) == []

    def test_un_hito_que_retrocede_si_avisa(self) -> None:
        (incidencia,) = arco_anclado(self._escaleta((1, 3, 2, 5)))
        assert "retroceden" in incidencia.mensaje


class TestNacimientoDeEpoca:
    def test_vale_la_del_arquitecto_si_le_da_edad_en_el_periodo(self) -> None:
        assert nacimiento_de_epoca("1890-03-01", _brief()) == "1890-03-01"

    def test_una_fecha_real_no_entra_en_el_canon(self) -> None:
        """Copiada, dejaba a Julia sin nacer en todas sus escenas de 1917 a 1919."""
        assert nacimiento_de_epoca("1967-05-21", _brief()) is None
        assert nacimiento_de_epoca(None, _brief(fecha_nacimiento="1885-01-01")) == "1885-01-01"

    def test_sin_fecha_la_publicacion_no_la_inventa(self) -> None:
        """Con `0` nacia en 1800, y una novela del siglo XVI no se habria publicado."""
        assert nacimiento_de(None) == NACIMIENTO_DESCONOCIDO
        assert nacimiento_de("") == NACIMIENTO_DESCONOCIDO


class TestResumenParaElMovil:
    def test_agrupa_los_avisos_por_tipo_y_pone_lo_grave_primero(self) -> None:
        from storymaker.commons.validation.modelos import Incidencia, Severidad
        from storymaker.plotting.informe import HuecoDelInforme, InformeDePlotting

        def aviso(validador: str, grave: bool = False) -> Incidencia:
            severidad = Severidad.BLOQUEANTE if grave else Severidad.AVISO
            return Incidencia(validador=validador, severidad=severidad, mensaje="…")

        informe = InformeDePlotting(
            capitulos=5,
            escenas=11,
            inventados_por_dimension={"lugar": 1},
            huecos_gastados=2,
            incidencias=(
                aviso("cronologia_escaleta"),
                aviso("cronologia_escaleta"),
                aviso("arco_anclado", grave=True),
            ),
            huecos=(
                HuecoDelInforme("a", "lugar", "inventado", "x", 1, 1),
                HuecoDelInforme("b", "lugar", "encontrado", "y", 1, 2),
            ),
        )
        assert informe.como_resumen() == [
            "Huecos: 1 encontrado, 1 inventado",
            "Revisión: 3 avisos, 1 grave",
            "  · arco: 1 (grave)",
            "  · cronología: 2",
        ]

    def test_sin_avisos_lo_dice_en_una_linea(self) -> None:
        from storymaker.plotting.informe import InformeDePlotting

        informe = InformeDePlotting(
            capitulos=1, escenas=2, inventados_por_dimension={}, huecos_gastados=0
        )
        assert informe.como_resumen() == ["Revisión en verde"]


class TestAvisoDelGateDePlotting:
    async def test_el_movil_recibe_cifras_y_no_el_informe_entero(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """El informe entero se lee en el PC; al móvil van los recuentos y los tipos."""
        from dobles.agente_falso import TransporteFalso

        from storymaker.commons.config import Settings
        from storymaker.commons.graph.dependencias import Dependencias, usando
        from storymaker.commons.obs.trazas import ObservadorNulo
        from storymaker.gates.nodos import _resumen, resumen_movil

        await repo_intake.insertar_dato(
            db,
            tipo="objeto",
            valor_json='{"valor": "la brujula del abuelo"}',
            origen="entrevista",
            obligatorio=True,
        )
        await gate.revisar(db, VectorizadorFalso())
        with usando(
            Dependencias(
                db=db,
                settings=Settings(_env_file=None),
                transporte=TransporteFalso(),
                vectorizador=VectorizadorFalso(),
                observador=ObservadorNulo(),
            )
        ):
            movil = await resumen_movil("AwaitApproval3")
            entero = await _resumen("AwaitApproval3")

        assert movil.splitlines()[0] == "2 capítulos · 2 escenas · 2 personajes"
        assert "  · anclado por el arnés: 1" in movil.splitlines()
        assert "la brujula del abuelo" not in movil, "el mensaje de cada aviso se queda en el PC"
        assert "la brujula del abuelo" in entero


class TestFechasEnProsa:
    @pytest.mark.parametrize(
        ("texto", "esperada", "precision"),
        [
            ("24 junio 1858, madrugada", "1858-06-24", "dia"),
            ("Noche 23 de junio de 1858", "1858-06-23", "dia"),
            ("Tarde julio 1858", "1858-07-01", "mes"),
            ("Primavera 1856, madrugada", "1856-04-01", "mes"),
            ("Recuerdo de infancia, circa 1846-1850", "1846-01-01", "anio"),
            ("1805-04-11", "1805-04-11", "dia"),
            ("1805-04", "1805-04-01", "mes"),
            ("1805", "1805-01-01", "anio"),
            ("711 d.C.", "0711-01-01", "anio"),
        ],
    )
    def test_se_lee_el_anio_y_no_el_primer_numero(
        self, texto: str, esperada: str, precision: str
    ) -> None:
        """«24 junio 1858» se leía como el año 24."""
        from datetime import date, timedelta

        from storymaker.commons.formal.generador import EPOCA, leer_fecha

        leida = leer_fecha(texto)
        assert leida.momento is not None
        assert EPOCA + timedelta(days=leida.momento) == date.fromisoformat(esperada)
        assert leida.precision == precision

    def test_un_dia_sin_anio_no_es_una_fecha(self) -> None:
        from storymaker.commons.formal.generador import leer_fecha

        assert leer_fecha("24 junio").momento is None
        assert leer_fecha("madrugada").momento is None

    async def test_sin_dia_no_se_esta_en_dos_sitios_a_la_vez(
        self, db: aiosqlite.Connection, novela: NovelaDePrueba
    ) -> None:
        """Dos escenas «de 1805» en sitios distintos no ocurren el mismo 1 de enero."""
        from storymaker.commons.formal.evaluacion import evaluar

        otro = await db.execute("INSERT INTO canon_escenario (descripcion) VALUES ('La lonja')")
        await db.execute("UPDATE plan_escena SET fecha_narrativa = 'Primavera 1805'")
        await db.execute(
            "UPDATE plan_escena SET escenario_id = ? WHERE id = (SELECT MIN(id) FROM plan_escena)",
            (otro.lastrowid,),
        )
        await db.execute(
            "INSERT OR IGNORE INTO plan_escena_personaje (escena_id, personaje_id) "
            "SELECT e.id, o.homenajeado_id FROM plan_escena e, canon_obra o"
        )
        cronologia = await gate.cronologia_de_la_escaleta(db)
        assert all(e.lugar == 0 for e in cronologia.eventos)
        assert not [i for i in evaluar(cronologia).incidencias if "dos lugares" in i.mensaje]


class TestNombresDeLugar:
    @pytest.mark.parametrize(
        ("texto", "nombre", "nombra"),
        [
            ("La inauguracion del Canal Isabel II", "Isabel II", False),
            ("La reina Isabel II presidio el acto", "Isabel II", True),
            ("La calle de Gravina estaba llena", "Federico Gravina", False),
            ("Gravina pagaba a los carpinteros", "Federico Gravina", True),
            ("el agua bajaba por el valle del Lozoya", "Lucio del Valle", False),
            ("Valle reviso las compuertas", "Lucio del Valle", True),
            ("encabezado por el ingeniero Lucio del Valle", "Lucio del Valle", True),
        ],
    )
    def test_un_sitio_con_su_nombre_no_es_la_persona(
        self, texto: str, nombre: str, nombra: bool
    ) -> None:
        assert gate.nombra_a(texto, nombre) is nombra


class TestReglaDeLosArcosEnElPrompt:
    def test_el_arquitecto_la_conoce_antes_de_la_revision(self) -> None:
        from storymaker.plotting.nodos import regla_de_los_arcos

        regla = regla_de_los_arcos()
        assert "3 escenas" in regla and "plano" in regla and "tercio final" in regla

    def test_la_fecha_de_la_escena_se_pide_en_iso(self) -> None:
        esquema = SalidaArquitecto.model_json_schema()
        fecha = esquema["$defs"]["EscenaPropuesta"]["properties"]["fecha_narrativa"]
        assert fecha["description"] == "AAAA, AAAA-MM o AAAA-MM-DD"
