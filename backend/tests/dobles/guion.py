"""spec: §7.1 · arq: §16.4

Una novela entera de mentira: las respuestas de los nueve roles, encajadas entre sí.

Esto no es un montón de datos de relleno. La prueba de extremo a extremo solo dice algo si
el guion es **coherente**: el arquitecto tiene que nombrar personajes que después el
extractor pueda referenciar, las escenas tienen que anclarse a hechos que el investigador
haya escrito antes, y los capítulos tienen que llegar a las palabras que el `Brief` pidió o
`longitud_capitulo` los tumbará. Un guion incoherente haría fallar la prueba por el motivo
equivocado, y un guion sin anclajes la haría pasar sin ejercitar nada.

El texto de los capítulos se genera por repetición porque lo que se comprueba es el
recorrido, no la prosa. Lo que sí es real es su **longitud**: se construye contando palabras
contra el mismo número que el validador va a leer de la base.
"""

from __future__ import annotations

from storymaker.intake.esquemas import (
    Brief,
    ElementoPersonalizacion,
    Periodo,
    RespuestaEntrevistador,
    TipoDeDato,
)
from storymaker.investigation.esquemas import (
    Dimension,
    EstadoEpistemico,
    FuenteCitada,
    HechoPropuesto,
    HuecoResuelto,
    SalidaInvestigador,
    SalidaVerificador,
    VeredictoDeRespaldo,
)
from storymaker.plotting.esquemas import (
    AnclajePropuesto,
    ArcoPropuesto,
    BeatPropuesto,
    CapituloPropuesto,
    EscenaPropuesta,
    EscenarioPropuesto,
    HitoDeArco,
    HuecoPropuesto,
    PersonajePropuesto,
    SalidaArquitecto,
    TerminoDeGlosario,
    TipoDeArco,
    TipoDePersonaje,
)
from storymaker.publication.esquemas import Criterio, Puntuacion, SalidaJuez
from storymaker.writing.esquemas import (
    EventoNarrativo,
    SalidaEscritor,
    SalidaExtractorDeCapitulo,
    VeredictoDeEjecucion,
)

HOMENAJEADO = "Casilda Berrocal"
PALABRAS_POR_CAPITULO = 400


def brief(n_capitulos: int = 2) -> Brief:
    """El encargo cerrado. Es el que gobierna todo lo demás."""
    return Brief(
        nombre_homenajeado=HOMENAJEADO,
        fecha_nacimiento="1948-03-11",
        rol_epoca="maestra de escuela rural",
        ocasion="setenta y cinco cumpleanos",
        elementos_personalizacion=[
            ElementoPersonalizacion(
                tipo=TipoDeDato.OBJETO, valor="un reloj de bolsillo heredado", obligatorio=True
            ),
            ElementoPersonalizacion(
                tipo=TipoDeDato.LUGAR, valor="la plaza del mercado", obligatorio=False
            ),
        ],
        periodo=Periodo(inicio=1960, fin=1975, denominacion="tardofranquismo"),
        lugar="Cuenca",
        genero="drama historico",
        tono="melancolico y luminoso",
        n_capitulos=n_capitulos,
        palabras_por_capitulo=PALABRAS_POR_CAPITULO,
    )


def entrevista(n_capitulos: int = 2) -> RespuestaEntrevistador:
    """El entrevistador cierra a la primera: aquí no se prueba la conversación."""
    return RespuestaEntrevistador(brief=brief(n_capitulos), preguntas=[])


def investigacion() -> SalidaInvestigador:
    """Seis hechos, uno por dimensión, que es lo que el reparto del ensamblador espera."""
    enunciados = {
        Dimension.CRONOLOGIA: "La Ley General de Educacion se aprobo en 1970.",
        Dimension.LUGAR: "La serrania de Cuenca quedaba a media jornada del casco.",
        Dimension.CULTURA_MATERIAL: "Las aulas rurales se calentaban con estufa de lena.",
        Dimension.LENGUAJE: "A la maestra se la trataba de dona en el trato publico.",
        Dimension.MENTALIDAD: "La radio era el entretenimiento dominante en el medio rural.",
        Dimension.ESTRUCTURA_SOCIAL: "El salario de una maestra rondaba las 3.000 pesetas.",
    }
    return SalidaInvestigador(
        hechos=[
            HechoPropuesto(
                enunciado=enunciado,
                estado=EstadoEpistemico.VERIFICADO,
                dimension=dimension,
                cita=enunciado,
                fuentes=[FuenteCitada(url="https://ejemplo.invalid/fuente", titulo="Fuente")],
            )
            for dimension, enunciado in enunciados.items()
        ]
    )


def verificacion(hechos: int = 6) -> SalidaVerificador:
    """Todo respaldado: el verificador no detiene la fase, y aquí tampoco la desvía."""
    return SalidaVerificador(
        veredictos=[
            VeredictoDeRespaldo(hecho_id=i, respaldado=True, motivo="La cita sostiene el hecho.")
            for i in range(1, hechos + 1)
        ]
    )


def hueco_resuelto() -> HuecoResuelto:
    """La micro-sesión encuentra lo que se le pide. El otro final ya lo cubre otra prueba."""
    return HuecoResuelto(
        encontrado=True,
        hecho=HechoPropuesto(
            enunciado="Los pupitres eran de madera con tintero empotrado.",
            estado=EstadoEpistemico.VERIFICADO,
            dimension=Dimension.CULTURA_MATERIAL,
            cita="Los pupitres eran de madera con tintero empotrado.",
            fuentes=[FuenteCitada(url="https://ejemplo.invalid/micro", titulo="Micro")],
        ),
    )


def _escena(capitulo: int, orden: int) -> EscenaPropuesta:
    return EscenaPropuesta(
        clave=f"c{capitulo}e{orden}",
        orden=orden,
        escenario="aula",
        fecha_narrativa="1970-09-15",
        pdv=HOMENAJEADO,
        objetivo="abrir el curso",
        conflicto="la estufa no tira",
        resultado="la clase empieza igual",
        personajes=[HOMENAJEADO],
        beats=[
            BeatPropuesto(orden=1, accion="entra en el aula", cambio_de_valor="de duda a decision")
        ],
        anclajes=[
            AnclajePropuesto(
                tipo_vinculo="sostiene la escena",
                hecho="Las aulas rurales se calentaban con estufa de lena.",
            )
        ],
    )


def arquitectura(
    n_capitulos: int = 2, *, huecos: tuple[str | HuecoPropuesto, ...] = ()
) -> SalidaArquitecto:
    """La escaleta completa, con sus arcos anclados a escenas que existen."""
    return SalidaArquitecto(
        titulo="El reloj de la maestra",
        premisa="Una maestra rural sostiene su escuela mientras el pais cambia de siglo.",
        tema="lo que se hereda y lo que se ensena",
        voz="tercera persona limitada",
        personajes=[
            PersonajePropuesto(
                nombre=HOMENAJEADO,
                tipo=TipoDePersonaje.INVENTADO,
                objetivo="mantener abierta la escuela",
                miedo="que el pueblo se vacie",
                voz="serena",
                estatus="maestra",
                fecha_nacimiento="1948-03-11",
                es_homenajeado=True,
            ),
            PersonajePropuesto(
                nombre="Don Emeterio",
                tipo=TipoDePersonaje.HISTORICO_DE_FONDO,
                objetivo="cerrar la escuela",
                estatus="inspector",
            ),
        ],
        arcos=[
            ArcoPropuesto(
                personaje=HOMENAJEADO,
                tipo=TipoDeArco.POSITIVO,
                estado_inicial="obediente",
                estado_final="firme",
                hitos=[
                    HitoDeArco(orden=n, descripcion=f"decide por si misma ({n})", escena=f"c{n}e1")
                    for n in range(1, n_capitulos + 1)
                ],
            )
        ],
        escenarios=[
            EscenarioPropuesto(clave="aula", descripcion="Un aula unitaria", lugar="Cuenca")
        ],
        glosario=[TerminoDeGlosario(termino="tintero", significado="recipiente para la tinta")],
        capitulos=[
            CapituloPropuesto(
                numero=n,
                titulo=f"Capitulo {n}",
                funcion="avanzar el curso",
                gancho="la inspeccion se anuncia",
                escenas=[_escena(n, 1)],
            )
            for n in range(1, n_capitulos + 1)
        ],
        huecos=[h if isinstance(h, HuecoPropuesto) else HuecoPropuesto(pregunta=h) for h in huecos],
    )


def capitulo(numero: int, palabras: int = PALABRAS_POR_CAPITULO) -> SalidaEscritor:
    """Prosa de relleno con la longitud exacta que el validador va a contar."""
    cuerpo = " ".join(f"palabra{i % 40}" for i in range(palabras - 4))
    return SalidaEscritor(texto=f"Capitulo {numero}. {cuerpo} Y el reloj de bolsillo siguio.")


def extraccion(numero: int) -> SalidaExtractorDeCapitulo:
    """Lo que el extractor devuelve de un capítulo limpio.

    Sin `hechos_usados` ni `elementos_usados` a propósito: los identificadores reales no se
    conocen al escribir el guion, y los validadores que dependen de ellos tienen sus propias
    pruebas. Lo que sí va completo es la cronología, que es lo que Lean lee.
    """
    return SalidaExtractorDeCapitulo(
        resumen=f"En el capitulo {numero} la maestra abre el curso pese a la estufa rota.",
        eventos=[
            EventoNarrativo(
                clave=f"apertura-{numero}",
                descripcion="La maestra abre el curso",
                momento=f"19{70 + numero}-09-15",
                escena=1,
            )
        ],
        veredicto=VeredictoDeEjecucion(beats_ejecutados=["entra en el aula"]),
    )


def juicio(valor: int = 8) -> SalidaJuez:
    """Notas por encima del umbral. La rama del rechazo tiene su propia prueba."""
    return SalidaJuez(
        puntuaciones=[
            Puntuacion(
                criterio=criterio,
                valor=valor,
                justificacion="Cumple con holgura lo que la rubrica pide en este criterio.",
            )
            for criterio in Criterio
        ]
    )
