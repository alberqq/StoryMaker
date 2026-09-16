"""E1 - Captura del encargo (RF-001 a RF-009, RF-110).

El Encargo gobierna todo lo demas: un error aqui se propaga a cien mil palabras.
De ahi que esta etapa no cierre nada sin confirmacion explicita del Autor, y que
ninguna incompatibilidad se resuelva en silencio.

Dos cosas que este modulo protege y que no son negociables:

- **El texto literal de la semilla nunca se reescribe** (RF-001). Se conserva tal
  como lo formulo el Autor, y lo que el sistema entienda de el vive en otro campo.
- **Ningun parametro de estilo tiene valor por defecto silencioso** (RF-029). Un
  campo vacio significa "sin preferencia", que es un estado declarado y no
  evaluable, nunca un valor implicito que el refinador aplicaria sin que nadie lo
  haya pedido.
"""

from __future__ import annotations

from typing import Any

from storymaker import SCHEMA_VERSION
from storymaker.errores import ErrorStoryMaker
from storymaker.ids import id_version, sha256_texto
from storymaker.invariantes import (
    CAMPOS_OBLIGATORIOS_ENCARGO,
    PARAMETROS_ESTILO,
    comprobar_encargo,
)
from storymaker.proyecto import EN_ENCARGO, EN_INVESTIGACION, Proyecto
from storymaker.sobre import ahora

TIPOS_SEMILLA = ("personaje", "epoca", "idea", "inspiracion")

# Campos admitidos en un fichero de Encargo ingerido. RF-110 es explicito: un
# campo desconocido no se ignora, se rechaza nombrandolo. El Autor no es tecnico,
# y fallar claro vale mas que ignorar en silencio.
CAMPOS_ADMITIDOS = frozenset({
    "semillas", "premisa", "epoca", "ambito_geografico",
    "extension_objetivo_palabras", "tolerancia_extension", "capitulos_objetivo",
    "extension_por_capitulo", "guia_estilo", "politica_hechos_sensibles",
    "politica_figuras_reales", "licencias_alcance_preautorizadas",
    "hilos_abiertos_autorizados", "restricciones_autor", "titulo_provisional",
    "incompatibilidades", "ejes_tematicos",
})

# Orden en que el interrogatorio pregunta. La epoca va pronto porque sin ella no
# hay investigacion posible, y porque casi todo lo demas depende de ella.
ORDEN_INTERROGATORIO = (
    "semillas", "epoca", "ambito_geografico", "premisa",
    "extension_objetivo_palabras", "capitulos_objetivo", "extension_por_capitulo",
    "guia_estilo", "politica_hechos_sensibles", "politica_figuras_reales",
)

PREGUNTAS = {
    "semillas": "De que parte la novela: un personaje, una epoca, una idea o una inspiracion. Cuenteme cual, con sus palabras.",
    "epoca": "En que periodo transcurre. Un rango, aunque sea aproximado: sin acotar la epoca no hay investigacion posible.",
    "ambito_geografico": "Donde transcurre. Ciudad, region o ambito que quiera cubrir.",
    "premisa": "En una o dos frases, de que va la novela.",
    "extension_objetivo_palabras": "Que extension busca. En palabras, o una idea de la que se pueda partir.",
    "capitulos_objetivo": "En cuantos capitulos la imagina, si lo tiene decidido.",
    "extension_por_capitulo": "Que extension quiere por capitulo. Puede darmela en palabras o en lineas.",
    "guia_estilo": "Como quiere que suene: persona narrativa, tiempo verbal, registro, densidad descriptiva, apertura.",
    "politica_hechos_sensibles": "Como quiere que se traten los hechos duros de la epoca si la trama los atraviesa.",
    "politica_figuras_reales": "Como quiere que aparezcan las personas que existieron de verdad.",
}


def _guia_vacia() -> dict[str, Any]:
    """Guia de estilo con todos los parametros explicitamente sin decidir.

    No es lo mismo que una guia vacia: aqui cada parametro existe y declara que
    nadie lo ha decidido todavia, que es lo que el interrogatorio ira cerrando.
    """
    return {
        parametro: {"valor": None, "estado": "sin_decidir"}
        for parametro in PARAMETROS_ESTILO
    }


def abrir_sesion(proyecto: Proyecto, semilla_texto: str, tipo: str) -> dict[str, Any]:
    """RF-001: registra la semilla con su tipo y su texto literal, sin reformular."""
    if not semilla_texto.strip():
        raise ErrorStoryMaker("ERR-101", "La semilla llega vacia")
    if tipo not in TIPOS_SEMILLA:
        raise ErrorStoryMaker(
            "ERR-101",
            f"Tipo de semilla desconocido: {tipo!r}. Los cuatro admitidos son {TIPOS_SEMILLA}.",
            tipo=tipo,
        )

    borrador = _borrador(proyecto) or {
        "schema_version": SCHEMA_VERSION,
        "estado": "abierto",
        "origen_captura": "conversacion",
        "semillas": [],
        "guia_estilo": _guia_vacia(),
        "tolerancia_extension": 0.10,
        "incompatibilidades": [],
        "rondas": 0,
        "campos_sin_preferencia": [],
    }
    borrador["semillas"].append({
        "tipo": tipo,
        "texto_literal": semilla_texto,  # RF-001: nunca se reescribe
        "registrada_en": ahora(),
    })
    _guardar_borrador(proyecto, borrador)
    proyecto.guardar(estado=EN_ENCARGO, etapa="Encargo")
    return {
        "borrador": borrador,
        "siguiente_pregunta": siguiente_pregunta(borrador),
    }


def siguiente_pregunta(borrador: dict[str, Any]) -> dict[str, Any] | None:
    """RF-002: la siguiente ronda del interrogatorio, o None si ya no hay.

    No se vuelve a preguntar por un campo que el Autor marco como sin preferencia
    en esta misma sesion: insistir es lo que convierte un interrogatorio en un
    interrogatorio.
    """
    marcados = set(borrador.get("campos_sin_preferencia", []))
    for campo in ORDEN_INTERROGATORIO:
        if campo in marcados:
            continue
        if campo == "guia_estilo":
            pendientes = [
                parametro
                for parametro, entrada in (borrador.get("guia_estilo") or {}).items()
                if entrada.get("estado") == "sin_decidir"
            ]
            if pendientes:
                return {
                    "campo": "guia_estilo",
                    "parametros_pendientes": pendientes,
                    "pregunta": PREGUNTAS["guia_estilo"],
                }
            continue
        if not borrador.get(campo):
            return {"campo": campo, "pregunta": PREGUNTAS[campo]}
    return None


def responder(
    proyecto: Proyecto,
    campo: str,
    valor: Any = None,
    *,
    sin_preferencia: bool = False,
    limite_rondas: int = 25,
) -> dict[str, Any]:
    """Registra una respuesta del Autor y devuelve la siguiente pregunta.

    RF-008 acota el bucle: al alcanzar el limite de rondas se deja de preguntar y
    se presenta el Encargo tal como esta. Sin limite, un Autor indeciso y un
    agente insistente no terminan.
    """
    borrador = _exigir_borrador(proyecto)
    if campo not in CAMPOS_ADMITIDOS and campo not in PARAMETROS_ESTILO:
        raise ErrorStoryMaker("ERR-105", f"Campo desconocido del Encargo: {campo}", campo=campo)

    borrador["rondas"] = borrador.get("rondas", 0) + 1

    if campo in PARAMETROS_ESTILO:
        borrador.setdefault("guia_estilo", _guia_vacia())[campo] = (
            {"valor": None, "estado": "sin_preferencia"}
            if sin_preferencia
            else {"valor": valor, "estado": "declarado"}
        )
    elif sin_preferencia:
        borrador.setdefault("campos_sin_preferencia", []).append(campo)
    else:
        borrador[campo] = valor

    agotado = borrador["rondas"] >= limite_rondas
    if agotado:
        # RF-008: se marcan como sin preferencia los que quedan y no se pregunta mas.
        borrador = _cerrar_por_agotamiento(borrador)

    _guardar_borrador(proyecto, borrador)
    return {
        "borrador": borrador,
        "rondas": borrador["rondas"],
        "limite_rondas_alcanzado": agotado,
        "siguiente_pregunta": None if agotado else siguiente_pregunta(borrador),
    }


def _cerrar_por_agotamiento(borrador: dict[str, Any]) -> dict[str, Any]:
    marcados = set(borrador.get("campos_sin_preferencia", []))
    for campo in ORDEN_INTERROGATORIO:
        if campo == "guia_estilo":
            for parametro, entrada in (borrador.get("guia_estilo") or {}).items():
                if entrada.get("estado") == "sin_decidir":
                    borrador["guia_estilo"][parametro] = {
                        "valor": None,
                        "estado": "sin_preferencia",
                        "origen": "agotamiento_de_rondas",
                    }
        elif not borrador.get(campo) and campo not in marcados:
            marcados.add(campo)
    borrador["campos_sin_preferencia"] = sorted(marcados)
    return borrador


def convertir_lineas_a_palabras(
    lineas: float, palabras_por_linea: float
) -> dict[str, Any]:
    """D28 y RF-003: la conversion ocurre una vez, en la captura.

    La palabra es la unidad canonica del arnes. Se admite la entrada en lineas
    porque es como muchos autores piden la extension, pero nada aguas abajo
    trabaja en lineas: una magnitud que depende de la maquetacion contaminaria los
    presupuestos, las tolerancias y las metricas, todos ellos en palabras.

    Se conservan ambos valores y el factor aplicado, para que el Autor reconozca
    despues la cifra que dio.
    """
    if palabras_por_linea <= 0:
        raise ErrorStoryMaker(
            "ERR-103", "El factor de conversion de lineas a palabras debe ser positivo"
        )
    return {
        "valor_palabras": int(round(lineas * palabras_por_linea)),
        "valor_origen": lineas,
        "unidad_origen": "lineas",
        "palabras_por_linea": palabras_por_linea,
        "origen": "conversion_declarada_en_captura",
    }


def detectar_incompatibilidades(borrador: dict[str, Any]) -> list[dict[str, Any]]:
    """RF-007: se exponen, no se resuelven.

    Solo se detecta aqui lo que es comprobable con el Encargo en la mano. La
    incompatibilidad entre premisa y periodo -- "un motivo que exige una
    institucion inexistente" -- no puede verse sin el Contexto historico, y por eso
    aflora en E3 y no aqui.
    """
    tensiones: list[dict[str, Any]] = []

    objetivo = borrador.get("extension_objetivo_palabras")
    capitulos = borrador.get("capitulos_objetivo")
    por_capitulo = (borrador.get("extension_por_capitulo") or {}).get("valor_palabras")
    tolerancia = borrador.get("tolerancia_extension", 0.10)

    if objetivo and capitulos and por_capitulo:
        implicito = capitulos * por_capitulo
        if abs(implicito - objetivo) > objetivo * tolerancia:
            tensiones.append({
                "tipo": "extension_incoherente",
                "descripcion": (
                    f"{objetivo:,} palabras, {capitulos} capitulos y {por_capitulo:,} "
                    f"palabras por capitulo dan {implicito:,}: las tres cifras no encajan "
                    "dentro de la tolerancia."
                ),
                "lecturas_posibles": [
                    "Ajustar la extension total",
                    "Ajustar el numero de capitulos",
                    "Ajustar la extension por capitulo",
                    "Tratar la extension por capitulo como promedio y no como objetivo",
                ],
                "bloqueante": True,
                "resuelta": False,
            })

    guia = borrador.get("guia_estilo") or {}
    frase = (guia.get("longitud_media_frase") or {})
    if (
        objetivo
        and objetivo >= 100_000
        and frase.get("estado") == "declarado"
        and isinstance(frase.get("valor"), (int, float))
        and frase["valor"] <= 8
    ):
        tensiones.append({
            "tipo": "estilo_vs_extension",
            "descripcion": (
                f"Una voz de frases muy breves (media de {frase['valor']} palabras) sobre "
                f"{objetivo:,} palabras es una tension conocida. Ambos valores quedan "
                "registrados; ninguno se modifica por cuenta del sistema."
            ),
            "lecturas_posibles": ["Mantener ambos", "Alargar la frase media", "Reducir la extension"],
            "bloqueante": False,
            "resuelta": False,
        })

    return tensiones


def ingerir_fichero(proyecto: Proyecto, datos: dict[str, Any]) -> dict[str, Any]:
    """RF-110: el Encargo como fichero JSON, con las mismas validaciones.

    Un campo desconocido no se ignora: se rechaza el fichero nombrandolo.
    """
    desconocidos = sorted(set(datos) - CAMPOS_ADMITIDOS - {"schema_version"})
    if desconocidos:
        raise ErrorStoryMaker(
            "ERR-105",
            f"El fichero de Encargo trae campos que el sistema no conoce: {', '.join(desconocidos)}",
            campos_desconocidos=desconocidos,
            campos_admitidos=sorted(CAMPOS_ADMITIDOS),
        )

    borrador = {
        "schema_version": SCHEMA_VERSION,
        "estado": "abierto",
        "origen_captura": "fichero",
        "guia_estilo": _guia_vacia(),
        "tolerancia_extension": 0.10,
        "incompatibilidades": [],
        "rondas": 0,
        "campos_sin_preferencia": [],
        **datos,
    }
    # Un fichero puede traer la guia a medias: los parametros que no menciona
    # quedan sin decidir, no con un valor por defecto.
    guia = _guia_vacia()
    guia.update(borrador.get("guia_estilo") or {})
    borrador["guia_estilo"] = guia
    borrador["incompatibilidades"] = detectar_incompatibilidades(borrador)

    _guardar_borrador(proyecto, borrador)
    proyecto.guardar(estado=EN_ENCARGO, etapa="Encargo")
    return {
        "borrador": borrador,
        "incompatibilidades": borrador["incompatibilidades"],
        "pendiente_confirmacion": True,
        "aviso": (
            "RF-006: el fichero no cierra el Encargo. Sigue haciendo falta la "
            "confirmacion explicita del Autor."
        ),
    }


def presentar(proyecto: Proyecto) -> dict[str, Any]:
    """RF-006: presenta el Encargo integro para que el Autor lo confirme.

    El Autor ve de una vez todo lo que el sistema entendio, que es la unica forma
    de corregirlo antes de que se gaste presupuesto.
    """
    borrador = _exigir_borrador(proyecto)
    borrador["incompatibilidades"] = detectar_incompatibilidades(borrador)
    _guardar_borrador(proyecto, borrador)

    incumplimientos = comprobar_encargo(_normalizar_para_validar(borrador))
    return {
        "encargo_propuesto": borrador,
        "incumplimientos": [i.como_dict() for i in incumplimientos],
        "puede_cerrarse": not incumplimientos,
        "sin_preferencia": borrador.get("campos_sin_preferencia", []),
        "parametros_sin_preferencia": [
            parametro
            for parametro, entrada in (borrador.get("guia_estilo") or {}).items()
            if entrada.get("estado") == "sin_preferencia"
        ],
    }


def confirmar(proyecto: Proyecto, confirmado_por: str) -> dict[str, Any]:
    """PC-2: cierra y versiona el Encargo tras la confirmacion del Autor."""
    borrador = _exigir_borrador(proyecto)
    borrador["incompatibilidades"] = detectar_incompatibilidades(borrador)
    encargo = _normalizar_para_validar(borrador)

    incumplimientos = comprobar_encargo(encargo)
    if incumplimientos:
        raise ErrorStoryMaker(
            "ERR-102",
            "El Encargo no puede cerrarse: quedan campos obligatorios sin valor ni marca, "
            "o incompatibilidades sin arbitraje.",
            incumplimientos=[i.como_dict() for i in incumplimientos],
        )

    numero = proyecto.siguiente_version("enc")
    identificador = id_version("enc", proyecto.estado.id, numero)
    encargo.update({
        "id": identificador,
        "version": numero,
        "estado": "cerrado",
        "confirmado_por": confirmado_por,
        "confirmado_en": ahora(),
        "creado_en": ahora(),
        "guia_estilo_hash": sha256_texto(
            repr(sorted((encargo.get("guia_estilo") or {}).items()))
        ),
    })

    proyecto.almacen.escribir_json(proyecto.almacen.encargo(identificador), encargo)
    _borrar_borrador(proyecto)
    proyecto.guardar(
        encargo_version_vigente=identificador,
        estado=EN_INVESTIGACION,
        etapa="Investigacion",
    )
    return {"encargo": encargo, "version": identificador}


def guia_estilo_efectiva(encargo: dict[str, Any]) -> dict[str, Any]:
    """RF-029: la Guia de estilo efectiva, con lo no declarado como no evaluable.

    El refinador comprueba la adherencia solo contra lo declarado (RF-051). Los
    parametros sin preferencia no se evaluan, y no se les asigna un valor por
    detras: eso convertiria una ausencia de decision en una decision del sistema.
    """
    guia = encargo.get("guia_estilo") or {}
    declarados = {
        parametro: entrada.get("valor")
        for parametro, entrada in guia.items()
        if entrada.get("estado") == "declarado"
    }
    no_evaluables = sorted(
        parametro for parametro, entrada in guia.items()
        if entrada.get("estado") != "declarado"
    )
    return {
        "declarados": declarados,
        "no_evaluables": no_evaluables,
        "hash": encargo.get("guia_estilo_hash"),
        "nota": (
            "Los parametros no evaluables no tienen valor por defecto. El refinador "
            "no aplica ninguna preferencia sobre ellos (RF-029, RF-051)."
        ),
    }


def ambito_investigacion(encargo: dict[str, Any]) -> dict[str, Any]:
    """CT-1: lo que E1 pasa a E2 (RF-010)."""
    return {
        "epoca": encargo.get("epoca"),
        "ambito_geografico": encargo.get("ambito_geografico"),
        "premisa": encargo.get("premisa"),
        "semillas": encargo.get("semillas", []),
        "ejes_tematicos": encargo.get("ejes_tematicos", []),
        "politica_figuras_reales": encargo.get("politica_figuras_reales"),
    }


# -- borrador en memoria efimera -------------------------------------------
#
# El borrador del Encargo vive bajo `tmp/`, que es la unica ruta bajo `proyectos/`
# donde los permisos dejan escribir. No es autoritativo: solo lo es la version
# confirmada bajo `encargo/`.


def _ruta_borrador(proyecto: Proyecto):
    return proyecto.almacen.preparar_tmp("encargo") / "borrador.json"


def _borrador(proyecto: Proyecto) -> dict[str, Any] | None:
    return proyecto.almacen.leer_json(_ruta_borrador(proyecto))


def _exigir_borrador(proyecto: Proyecto) -> dict[str, Any]:
    borrador = _borrador(proyecto)
    if borrador is None:
        raise ErrorStoryMaker(
            "ERR-102",
            "No hay ninguna sesion de captura abierta. Empiece por registrar una semilla.",
        )
    return borrador


def _guardar_borrador(proyecto: Proyecto, borrador: dict[str, Any]) -> None:
    proyecto.almacen.escribir_json(_ruta_borrador(proyecto), borrador)


def _borrar_borrador(proyecto: Proyecto) -> None:
    proyecto.almacen.borrar_tmp("encargo")


def _normalizar_para_validar(borrador: dict[str, Any]) -> dict[str, Any]:
    """Convierte 'sin_decidir' en lo que la invariante espera ver.

    Un campo que el Autor marco como sin preferencia esta cubierto a efectos de
    RF-002; uno que sigue sin decidir, no. La distincion es justo lo que separa
    "el Autor lo penso y no tiene preferencia" de "nadie lo ha mirado".
    """
    encargo = dict(borrador)
    marcados = set(encargo.get("campos_sin_preferencia", []))
    for campo in CAMPOS_OBLIGATORIOS_ENCARGO:
        if campo in marcados and not encargo.get(campo):
            encargo[campo] = {"estado": "sin_preferencia"}
    return encargo
