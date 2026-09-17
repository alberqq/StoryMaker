"""E2 - Investigacion historica y refutacion (RF-010 a RF-019, RF-100 a RF-102).

MD-3 gobierna este modulo: **el Contexto historico es un conjunto de afirmaciones
atomicas; la prosa es una proyeccion.** Sobre prosa no se cuenta nada, y por eso
la cobertura documental, la fidelidad de cita y la cobertura de refutacion pueden
medirse en lugar de estimarse.

Una afirmacion es una sola proposicion verificable. Si lleva dos, son dos
afirmaciones; si no, no hay forma de decir que fuente sostiene cual.

El orden es fijo y cada paso es puerta del siguiente:

    afirmar  ->  verificar fidelidad (RF-100)  ->  refutar (RF-102)  ->  derivar
                                                                        restriccion

Ninguna Restriccion comprobable sale de una afirmacion que no haya superado los
dos veredictos (MD-7). Una cita que no dice lo que se le atribuye contamina todo
lo que se valide contra ella.
"""

from __future__ import annotations

from typing import Any, Iterable

from storymaker import SCHEMA_VERSION
from storymaker.errores import ErrorStoryMaker
from storymaker.ids import (
    id_afirmacion,
    id_contenido,
    id_fuente,
    id_refutacion,
    id_restriccion,
    id_version,
)
from storymaker.invariantes import (
    CATEGORIAS_RESTRICCION,
    FIDELIDAD_NO_SOSTENIDA,
    FIDELIDAD_NO_VERIFICABLE,
    FIDELIDAD_VERIFICADA,
    SECCIONES_OBLIGATORIAS,
    VEREDICTOS_REFUTACION,
    comprobar_contexto,
    comprobar_derivacion_restriccion,
)
from storymaker.proyecto import EN_DISENO, MODO_REVISION_DEL_AUTOR, Proyecto
from storymaker.sobre import ahora

MODOS_RECUPERACION = ("web", "rag")

# Tipos de afirmacion que determinan la estrategia de busqueda inversa del
# refutador. No es taxonomia decorativa: no se refuta igual "no existia X" que
# "X ocurrio en 1482".
TIPOS_AFIRMACION = (
    "existencial_negativa",
    "existencial_positiva",
    "datacion",
    "atribucion",
    "cuantitativa",
    "cualitativa",
)


# ==========================================================================
# Fuentes y contenido conservado
# ==========================================================================


def registrar_fuente(
    proyecto: Proyecto,
    localizador: str,
    tipo: str,
    contenido: str | None = None,
    *,
    fiabilidad: str = "sin_declarar",
    motivo_no_conservable: str | None = None,
) -> dict[str, Any]:
    """RF-011, RF-012 y RF-101: registra una Fuente y conserva su contenido.

    La conservacion ocurre en el momento de la consulta, no en el de la entrega.
    Un localizador puede morir; el contenido conservado es lo que hace que la
    trazabilidad de RF-082 siga funcionando meses despues.
    """
    if tipo not in MODOS_RECUPERACION:
        raise ErrorStoryMaker(
            "ERR-105", f"Modo de recuperacion desconocido: {tipo!r}", tipo=tipo
        )
    if contenido is None and not motivo_no_conservable:
        raise ErrorStoryMaker(
            "ERR-607",
            "Una Fuente sin contenido conservado debe declarar por que no pudo conservarse",
            localizador=localizador,
        )

    identificador = id_fuente(localizador)
    registro: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "id": identificador,
        "tipo": tipo,
        "localizador": localizador,
        "consultada_en": ahora(),
        "fiabilidad": fiabilidad,
        "contenido_id": None,
        "motivo_no_conservable": motivo_no_conservable,
    }
    if contenido is not None:
        digest = proyecto.almacen.guardar_contenido_fuente(contenido)
        registro["contenido_id"] = id_contenido(digest)
        registro["contenido_sha256"] = digest

    proyecto.almacen.anexar(proyecto.almacen.fuentes, registro)
    return registro


# ==========================================================================
# Afirmaciones
# ==========================================================================


def afirmar(
    proyecto: Proyecto,
    enunciado: str,
    seccion: str,
    *,
    fuentes: Iterable[str] = (),
    sin_fuente: bool = False,
    certeza: str = "documentada",
    origen: str = "inicial",
    tipo_afirmacion: str = "existencial_positiva",
    disputada: bool = False,
    versiones_en_conflicto: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """RF-013 y RF-015: registra una afirmacion atomica con su fuente o su carencia.

    `fuentes` y `sin_fuente` son mutuamente excluyentes por construccion: no hay
    forma de registrar una afirmacion que a la vez tenga fuente y declare no
    tenerla, porque eso haria inutil el recuento de cobertura de RNF-004.
    """
    fuentes = list(fuentes)
    if bool(fuentes) == bool(sin_fuente):
        raise ErrorStoryMaker(
            "ERR-302",
            "Una afirmacion lleva fuentes o se marca como sin fuente, nunca ambas ni ninguna",
            enunciado=enunciado[:120],
        )
    if seccion not in SECCIONES_OBLIGATORIAS and not seccion.startswith("otra:"):
        raise ErrorStoryMaker(
            "ERR-302",
            f"Seccion desconocida: {seccion!r}. Las cinco obligatorias son "
            f"{SECCIONES_OBLIGATORIAS}; cualquier otra se nombra como 'otra:<nombre>'.",
            seccion=seccion,
        )
    if tipo_afirmacion not in TIPOS_AFIRMACION:
        raise ErrorStoryMaker(
            "ERR-302", f"Tipo de afirmacion desconocido: {tipo_afirmacion!r}"
        )

    registro = {
        "schema_version": SCHEMA_VERSION,
        "id": id_afirmacion(enunciado),
        "seccion": seccion,
        "enunciado": enunciado,
        "tipo_afirmacion": tipo_afirmacion,
        "fuentes": fuentes,
        "sin_fuente": sin_fuente,
        # La fidelidad nace sin verificar. Solo `verificar_fidelidad` la mueve.
        "fidelidad": FIDELIDAD_NO_VERIFICABLE if sin_fuente else "pendiente",
        "refutacion_id": None,
        "estado": "vigente",
        "disputada": disputada,
        "versiones_en_conflicto": list(versiones_en_conflicto),
        "certeza": certeza,
        "origen": origen,
        "creado_en": ahora(),
    }
    proyecto.almacen.anexar(proyecto.almacen.afirmaciones, registro)
    return registro


def verificar_fidelidad(
    proyecto: Proyecto,
    id_afirmacion_: str,
    resultado: str,
    *,
    contenido_cotejado: str,
    motivo: str = "",
) -> dict[str, Any]:
    """RF-100: comprueba que la Fuente sostiene lo que se le atribuye.

    Se aplica al subconjunto que sostiene una Restriccion o una ficha de figura
    real: el coste crece con el numero de restricciones, no con el de
    afirmaciones, y verificar el Contexto entero encareceria E2 sin ganancia,
    porque lo que no deriva en restriccion no valida nada.

    Un resultado `no_sostenida` no borra la afirmacion: la deja en pie y marcada,
    y genera un hallazgo bloqueante con causa raiz en la investigacion. Borrarla
    perderia la evidencia de que alguien la afirmo.
    """
    if resultado not in (FIDELIDAD_VERIFICADA, FIDELIDAD_NO_SOSTENIDA, FIDELIDAD_NO_VERIFICABLE):
        raise ErrorStoryMaker("ERR-302", f"Resultado de fidelidad desconocido: {resultado!r}")

    afirmacion = _exigir_afirmacion(proyecto, id_afirmacion_)
    actualizada = dict(afirmacion)
    actualizada.update({
        "fidelidad": resultado,
        "fidelidad_motivo": motivo,
        "fidelidad_contenido_cotejado": contenido_cotejado,
        "fidelidad_verificada_en": ahora(),
    })
    proyecto.almacen.anexar(proyecto.almacen.afirmaciones, actualizada)

    return {
        "afirmacion": actualizada,
        "genera_hallazgo_bloqueante": resultado == FIDELIDAD_NO_SOSTENIDA,
        "codigo_error": "ERR-605" if resultado == FIDELIDAD_NO_SOSTENIDA else None,
    }


# ==========================================================================
# Refutacion (B11, pasada unica)
# ==========================================================================


def refutar(
    proyecto: Proyecto,
    id_afirmacion_: str,
    veredicto: str,
    *,
    tipo_afirmacion: str,
    consultas: list[dict[str, Any]],
    fuentes_contrarias: Iterable[str] = (),
    alcance_matiz: str | None = None,
) -> dict[str, Any]:
    """RF-102: veredicto de la pasada adversarial.

    Tres reglas que este codigo impone y no sugiere:

    1. **Toda refutacion exige fuente distinta de la citada.** Una fuente contraria
       que esta entre las de la afirmacion no contradice nada: se apoya en lo mismo.
    2. **Una refutacion sin fuente que la sostenga no es una refutacion y no se
       registra.** Vale para `refutada`, `matizada` y `disputada`.
    3. **Las consultas son obligatorias.** Son lo que impide que `confirmada`
       signifique `no se busco`.

    No hay bucle entre investigador y refutador, y es deliberado: un bucle
    exigiria un arbitro y una condicion de terminacion declarada, que es justo lo
    que se evito al elegir una critica asimetrica de una sola pasada.
    """
    if veredicto not in VEREDICTOS_REFUTACION:
        raise ErrorStoryMaker(
            "ERR-302",
            f"Veredicto desconocido: {veredicto!r}. Los cinco son {VEREDICTOS_REFUTACION}.",
        )
    if tipo_afirmacion not in TIPOS_AFIRMACION:
        raise ErrorStoryMaker("ERR-302", f"Tipo de afirmacion desconocido: {tipo_afirmacion!r}")
    if not consultas:
        raise ErrorStoryMaker(
            "ERR-608",
            "Una refutacion sin consultas registradas no se registra: seria imposible "
            "distinguir 'confirmada' de 'no se busco'.",
            afirmacion=id_afirmacion_,
        )
    for consulta in consultas:
        if not consulta.get("consulta") or "resultados_examinados" not in consulta:
            raise ErrorStoryMaker(
                "ERR-608",
                "Cada consulta declara su texto, su modo, los resultados examinados y el "
                "motivo de descarte",
                consulta=consulta,
            )

    afirmacion = _exigir_afirmacion(proyecto, id_afirmacion_)
    contrarias = list(fuentes_contrarias)
    propias = set(afirmacion.get("fuentes", []))
    solapadas = sorted(propias & set(contrarias))
    if solapadas:
        raise ErrorStoryMaker(
            "ERR-608",
            f"Las fuentes contrarias {solapadas} son las mismas que sostienen la "
            "afirmacion. Toda refutacion exige fuente distinta de la citada.",
            afirmacion=id_afirmacion_,
            solapadas=solapadas,
        )
    if veredicto in ("refutada", "matizada", "disputada") and not contrarias:
        raise ErrorStoryMaker(
            "ERR-608",
            f"Un veredicto '{veredicto}' sin fuente contraria no es una refutacion",
            afirmacion=id_afirmacion_,
        )
    if veredicto == "matizada" and not alcance_matiz:
        raise ErrorStoryMaker(
            "ERR-302", "Un veredicto 'matizada' exige declarar el alcance del matiz"
        )

    registro = {
        "schema_version": SCHEMA_VERSION,
        "id": id_refutacion(id_afirmacion_),
        "afirmacion_id": id_afirmacion_,
        "veredicto": veredicto,
        "tipo_afirmacion": tipo_afirmacion,
        "fuentes_contrarias": contrarias,
        "consultas": consultas,
        "alcance_matiz": alcance_matiz,
        "emitida_en": ahora(),
    }
    proyecto.almacen.anexar(proyecto.almacen.refutaciones, registro)

    # Una afirmacion refutada deja de estar vigente, y con ella cae lo que
    # sostenia. No se borra: se anexa su nuevo estado.
    actualizada = dict(afirmacion)
    actualizada["refutacion_id"] = registro["id"]
    if veredicto == "refutada":
        actualizada["estado"] = "refutada"
    proyecto.almacen.anexar(proyecto.almacen.afirmaciones, actualizada)

    return {
        "refutacion": registro,
        "afirmacion": actualizada,
        "puede_sostener_comprobable": (
            veredicto in ("confirmada", "matizada")
            and actualizada.get("fidelidad") == FIDELIDAD_VERIFICADA
        ),
        "solo_cualitativa": veredicto == "no_refutable_documentalmente",
    }


def firmar_como_autor(
    proyecto: Proyecto,
    identificadores: Iterable[str],
    *,
    quien: str,
    motivo: str = "",
) -> dict[str, Any]:
    """El Autor asume en persona la verificacion y la refutacion (RF-100, RF-102).

    Esto **no** debilita MD-7. El invariante exige que una Restriccion comprobable
    derive de una afirmacion con fidelidad verificada y con veredicto de refutacion;
    lo que cambia aqui es quien los emite, no que hagan falta. El Autor puede
    verificar lo que sabe, y su firma queda registrada como suya: la trazabilidad
    distingue despues una afirmacion sostenida por una pasada adversarial de otra
    sostenida por el criterio de una persona, que es una diferencia que importa al
    releer la novela dentro de seis meses.

    Se exige `quien` porque una firma sin firmante no es una firma, y el ledger
    tiene que poder decir de quien se fio el Contexto.
    """
    if not quien.strip():
        raise ErrorStoryMaker(
            "ERR-302",
            "Firmar la verificacion exige decir quien firma: una afirmacion "
            "respaldada por nadie no esta respaldada",
        )

    if proyecto.estado.modo != MODO_REVISION_DEL_AUTOR:
        raise ErrorStoryMaker(
            "ERR-604",
            "La firma del Autor como verificador solo opera en modo "
            f"'{MODO_REVISION_DEL_AUTOR}'. Este Proyecto esta en "
            f"'{proyecto.estado.modo}', donde la verificacion la emiten las etapas.",
            modo=proyecto.estado.modo,
        )

    pedidos = list(identificadores)
    vigentes = {a["id"]: a for a in _afirmaciones_vigentes(proyecto)}
    if not pedidos:
        pedidos = sorted(vigentes)
    desconocidos = [i for i in pedidos if i not in vigentes]
    if desconocidos:
        raise ErrorStoryMaker(
            "ERR-304",
            f"No existen estas afirmaciones en el Contexto: {desconocidos}",
            afirmaciones=desconocidos,
        )

    momento = ahora()
    firmadas, refutaciones = [], []
    for identificador in pedidos:
        afirmacion = dict(vigentes[identificador])
        afirmacion.update({
            "fidelidad": FIDELIDAD_VERIFICADA,
            "fidelidad_motivo": motivo,
            "fidelidad_contenido_cotejado": (
                f"Verificada por el Autor ({quien}) en revision directa del Contexto"
            ),
            "fidelidad_verificada_en": momento,
            "verificada_por": {"modo": "autor", "quien": quien},
        })

        registro = {
            "schema_version": SCHEMA_VERSION,
            "id": id_refutacion(identificador),
            "afirmacion_id": identificador,
            "veredicto": "confirmada",
            "tipo_afirmacion": afirmacion.get("tipo_afirmacion", "cualitativa"),
            "fuentes_contrarias": [],
            # No se finge una busqueda que no ha ocurrido: la consulta declara que
            # el respaldo es el criterio del Autor, y eso es lo que se podra leer.
            "consultas": [{
                "consulta": f"Revision directa del Autor ({quien})",
                "modo": "autor",
                "resultados_examinados": 0,
                "motivo_descarte": "El Autor asume la afirmacion sin busqueda inversa",
            }],
            "alcance_matiz": None,
            "emitida_por": {"modo": "autor", "quien": quien},
            "emitida_en": momento,
        }
        afirmacion["refutacion_id"] = registro["id"]

        proyecto.almacen.anexar(proyecto.almacen.refutaciones, registro)
        proyecto.almacen.anexar(proyecto.almacen.afirmaciones, afirmacion)
        firmadas.append(afirmacion)
        refutaciones.append(registro)

    return {
        "firmadas": [a["id"] for a in firmadas],
        "cuantas": len(firmadas),
        "quien": quien,
        "nota": (
            "Con fidelidad y refutacion firmadas, estas afirmaciones ya pueden "
            "sostener Restricciones comprobables (MD-7)."
        ),
    }


def descartar(
    proyecto: Proyecto,
    *,
    afirmaciones: Iterable[str] = (),
    restricciones: Iterable[str] = (),
    quien: str,
    motivo: str = "",
) -> dict[str, Any]:
    """El Autor retira del Contexto lo que no da por bueno (RF-015).

    Es la salida fina del punto en que el Autor revisa el Contexto historico:
    antes solo podia aceptarlo entero o rechazarlo entero, y una sola afirmacion
    mal traida obligaba a rehacer la investigacion completa.

    **Nada se borra.** El almacen es de solo anexion, asi que descartar es anexar
    el estado nuevo: la afirmacion sigue ahi, marcada, y con ella la constancia de
    que alguien la afirmo y de que el Autor la retiro. Borrarla perderia las dos
    cosas.

    Descartar una afirmacion **arrastra lo que colgaba de ella**: las Restricciones
    derivadas se descartan tambien, porque una regla que se apoya en algo retirado
    no se sostiene. Esa cascada se hace aqui y no se deja al que llama, que es
    justo donde se olvidaria.
    """
    if not quien.strip():
        raise ErrorStoryMaker(
            "ERR-302", "Descartar exige decir quien lo hace: queda en el Contexto"
        )

    pedidas = set(afirmaciones)
    pedidas_rst = set(restricciones)
    if not pedidas and not pedidas_rst:
        raise ErrorStoryMaker("ERR-302", "No se ha indicado nada que descartar")

    vigentes = {a["id"]: a for a in _afirmaciones_vigentes(proyecto)}
    desconocidas = sorted(pedidas - set(vigentes))
    if desconocidas:
        raise ErrorStoryMaker(
            "ERR-304", f"No existen estas afirmaciones: {desconocidas}",
            afirmaciones=desconocidas,
        )

    momento = ahora()
    sello = {"quien": quien, "motivo": motivo, "descartado_en": momento}

    for identificador in sorted(pedidas):
        registro = dict(vigentes[identificador])
        registro.update({"estado": "descartada", "descartada_por": sello})
        proyecto.almacen.anexar(proyecto.almacen.afirmaciones, registro)

    # La cascada: lo que derivaba de una afirmacion descartada cae con ella.
    todas_rst = {r["id"]: r for r in _restricciones_vigentes(proyecto)}
    arrastradas = {
        i for i, r in todas_rst.items()
        if r.get("afirmacion_id") in pedidas and r.get("estado") != "descartada"
    }
    desconocidas_rst = sorted(pedidas_rst - set(todas_rst))
    if desconocidas_rst:
        raise ErrorStoryMaker(
            "ERR-304", f"No existen estas Restricciones: {desconocidas_rst}",
            restricciones=desconocidas_rst,
        )

    for identificador in sorted(pedidas_rst | arrastradas):
        registro = dict(todas_rst[identificador])
        registro.update({"estado": "descartada", "descartada_por": sello})
        proyecto.almacen.anexar(proyecto.almacen.restricciones, registro)

    return {
        "afirmaciones_descartadas": sorted(pedidas),
        "restricciones_descartadas": sorted(pedidas_rst | arrastradas),
        "arrastradas_por_su_afirmacion": sorted(arrastradas),
        "quien": quien,
        "nota": (
            "Nada se borra: el almacen es de solo anexion y lo descartado queda "
            "marcado, con constancia de quien lo retiro y por que."
        ),
    }


def _restricciones_vigentes(proyecto: Proyecto) -> list[dict[str, Any]]:
    ultimas: dict[str, dict[str, Any]] = {}
    for registro in proyecto.almacen.leer_jsonl(proyecto.almacen.restricciones):
        ultimas[registro["id"]] = registro
    return list(ultimas.values())


# ==========================================================================
# Restricciones de epoca
# ==========================================================================


def derivar_restriccion(
    proyecto: Proyecto,
    enunciado: str,
    categoria: str,
    id_afirmacion_: str,
    *,
    comprobable: bool = True,
    terminos_prohibidos: Iterable[str] = (),
    severidad_incumplimiento: str = "bloqueante",
) -> dict[str, Any]:
    """RF-016 con la puerta de MD-7 e INV-8.

    Una Restriccion comprobable exige que su afirmacion este verificada contra el
    contenido de su Fuente y que la refutacion la deje en pie. Una cualitativa no:
    es criterio de evaluacion, no puerta binaria, y para eso sirve el veredicto
    `no_refutable_documentalmente`, que no es una confirmacion.
    """
    if categoria not in CATEGORIAS_RESTRICCION:
        raise ErrorStoryMaker(
            "ERR-302",
            f"Categoria desconocida: {categoria!r}. Las cinco son {CATEGORIAS_RESTRICCION}.",
        )

    afirmaciones = {a["id"]: a for a in _afirmaciones_vigentes(proyecto)}
    refutaciones = {r["afirmacion_id"]: r for r in _refutaciones(proyecto)}

    candidata = {
        "schema_version": SCHEMA_VERSION,
        "id": id_restriccion(enunciado),
        "enunciado": enunciado,
        "categoria": categoria,
        "afirmacion_id": id_afirmacion_,
        "comprobable": comprobable,
        "terminos_prohibidos": sorted(set(terminos_prohibidos)),
        "severidad_incumplimiento": severidad_incumplimiento,
        "estado": "vigente",
        "derivada_en": ahora(),
    }

    fallos = comprobar_derivacion_restriccion(candidata, afirmaciones, refutaciones)
    if fallos:
        raise ErrorStoryMaker(
            fallos[0].codigo,
            "La Restriccion no puede derivarse: " + "; ".join(f.mensaje for f in fallos),
            incumplimientos=[f.como_dict() for f in fallos],
        )

    if categoria == "lexica" and comprobable and not candidata["terminos_prohibidos"]:
        raise ErrorStoryMaker(
            "ERR-302",
            "Una Restriccion lexica comprobable sin terminos prohibidos no es comprobable "
            "sobre un texto. O declara los terminos, o se marca como cualitativa.",
            restriccion=candidata["id"],
        )

    proyecto.almacen.anexar(proyecto.almacen.restricciones, candidata)
    return candidata


def revocar_restriccion(proyecto: Proyecto, identificador: str, justificacion: str) -> dict[str, Any]:
    """Una Restriccion se revoca con justificacion; nunca se borra."""
    if not justificacion.strip():
        raise ErrorStoryMaker("ERR-302", "Revocar una Restriccion exige justificacion")
    actual = next(
        (r for r in reversed(proyecto.almacen.leer_jsonl(proyecto.almacen.restricciones))
         if r.get("id") == identificador),
        None,
    )
    if actual is None:
        raise ErrorStoryMaker("ERR-304", f"No existe la Restriccion {identificador}")
    revocada = dict(actual)
    revocada.update({
        "estado": "revocada",
        "justificacion_revocacion": justificacion,
        "revocada_en": ahora(),
    })
    proyecto.almacen.anexar(proyecto.almacen.restricciones, revocada)
    return revocada


# ==========================================================================
# Figuras historicas reales
# ==========================================================================


def documentar_figura(
    proyecto: Proyecto,
    identificador: str,
    nombre: str,
    *,
    fuentes: Iterable[str],
    afirmaciones: Iterable[str] = (),
    hechos_documentados: Iterable[str] = (),
    restricciones_derivadas: Iterable[str] = (),
) -> dict[str, Any]:
    """RF-019 y RNF-021: la ficha documental de una figura real.

    Sin ficha con fuente, el Canon no puede usar a esa persona como personaje
    (RF-022), y toda accion que se le atribuya sin respaldo exige Licencia
    literaria registrada.
    """
    fuentes = list(fuentes)
    if not fuentes:
        raise ErrorStoryMaker(
            "ERR-605",
            "Una figura historica real sin ninguna Fuente documental no se documenta",
            figura=identificador,
        )
    ficha = {
        "schema_version": SCHEMA_VERSION,
        "id": identificador,
        "nombre": nombre,
        "fuentes": fuentes,
        "afirmaciones": list(afirmaciones),
        "hechos_documentados": list(hechos_documentados),
        "restricciones_derivadas": list(restricciones_derivadas),
        "documentada_en": ahora(),
    }
    proyecto.almacen.escribir_json(proyecto.almacen.figura_real(identificador), ficha)
    return ficha


# ==========================================================================
# Cierre del Contexto
# ==========================================================================


def declarar_laguna(
    proyecto: Proyecto, seccion: str, impacto: str, motivo: str = ""
) -> dict[str, Any]:
    """RF-015: las lagunas se declaran, no se rellenan con verosimilitud."""
    if not impacto.strip():
        raise ErrorStoryMaker(
            "ERR-102",
            "Una laguna sin impacto evaluado no cumple la condicion de avance de E2",
            seccion=seccion,
        )
    return {"seccion": seccion, "impacto": impacto, "motivo": motivo, "declarada_en": ahora()}


def cerrar(
    proyecto: Proyecto,
    lagunas: Iterable[dict[str, Any]] = (),
    *,
    cobertura_reducida: str | None = None,
    ids_figuras_referenciadas: Iterable[str] = (),
) -> dict[str, Any]:
    """Versiona el Contexto historico y comprueba sus cinco invariantes."""
    afirmaciones = _afirmaciones_vigentes(proyecto)
    refutaciones = _refutaciones(proyecto)
    restricciones = _restricciones_vigentes(proyecto)
    figuras = _figuras(proyecto)

    cabecera = {
        "schema_version": SCHEMA_VERSION,
        "lagunas": list(lagunas),
        "cobertura_reducida": cobertura_reducida,
    }

    fallos = comprobar_contexto(
        cabecera, afirmaciones, refutaciones, restricciones, figuras,
        ids_figuras_referenciadas,
    )
    if fallos:
        raise ErrorStoryMaker(
            "ERR-102",
            "El Contexto historico no cumple sus invariantes y no se cierra",
            incumplimientos=[f.como_dict() for f in fallos],
        )

    numero = proyecto.siguiente_version("ctx")
    identificador = id_version("ctx", proyecto.estado.id, numero)
    cabecera.update({
        "id": identificador,
        "version": numero,
        "estado": "completo",
        "creado_en": ahora(),
        "indicadores": indicadores(proyecto, ids_figuras_referenciadas),
    })
    proyecto.almacen.escribir_json(proyecto.almacen.contexto(identificador), cabecera)
    proyecto.guardar(
        contexto_version_vigente=identificador, estado=EN_DISENO, etapa="Diseno"
    )
    return {"contexto": cabecera, "version": identificador}


def indicadores(
    proyecto: Proyecto, ids_figuras_referenciadas: Iterable[str] = ()
) -> dict[str, Any]:
    """RNF-004, RNF-006, RNF-027 y RNF-028, medibles porque MD-3 atomiza.

    RNF-004 es un indicador de salud que se vigila y se entrega, **no un umbral
    que detenga la Ejecucion**: mide lo que el sistema decidio afirmar, no lo que
    la novela necesita saber.
    """
    afirmaciones = _afirmaciones_vigentes(proyecto)
    restricciones = _restricciones_vigentes(proyecto)
    refutaciones = {r["afirmacion_id"]: r for r in _refutaciones(proyecto)}
    total = len(afirmaciones) or 1

    from storymaker.invariantes import alcance_de_refutacion

    en_alcance = alcance_de_refutacion(
        afirmaciones, restricciones, ids_figuras_referenciadas, _figuras(proyecto)
    )
    con_veredicto = [i for i in en_alcance if i in refutaciones]
    reparto = {veredicto: 0 for veredicto in VEREDICTOS_REFUTACION}
    for identificador in con_veredicto:
        reparto[refutaciones[identificador]["veredicto"]] += 1

    verificadas = [
        a for a in afirmaciones
        if a["id"] in en_alcance and a.get("fidelidad") == FIDELIDAD_VERIFICADA
    ]
    con_fuente = [a for a in afirmaciones if a.get("fuentes")]
    clasificadas = [
        a for a in afirmaciones
        if any(r.get("afirmacion_id") == a["id"] for r in restricciones)
    ]

    return {
        "RNF-004_cobertura_documental": {
            "valor": round(len(con_fuente) / total, 4),
            "objetivo": 0.90,
            "naturaleza": "indicador de salud, no umbral que detenga la Ejecucion",
        },
        "RNF-006_cobertura_restricciones": {
            "valor": round(len(clasificadas) / total, 4),
            "objetivo": 1.0,
        },
        "RNF-027_fidelidad_de_cita": {
            "en_alcance": len(en_alcance),
            "verificadas": len(verificadas),
            "valor": round(len(verificadas) / (len(en_alcance) or 1), 4),
            "objetivo": 1.0,
        },
        "RNF-028_cobertura_refutacion": {
            "en_alcance": len(en_alcance),
            "con_veredicto": len(con_veredicto),
            "valor": round(len(con_veredicto) / (len(en_alcance) or 1), 4),
            "reparto_veredictos": reparto,
            "nota": (
                "La proporcion de 'no_refutable_documentalmente' se declara aparte "
                "porque no es una confirmacion. La de 'refutada' no tiene umbral: es "
                "el indicador que dice si la investigacion de un periodo es de fiar."
            ),
        },
    }


# -- lecturas internas -----------------------------------------------------
#
# Los libros son de solo anexion, asi que el estado actual de una entidad es su
# ultima aparicion. Compensar por anexion en lugar de sobrescribir es lo que hace
# el libro mayor auditable.


def _ultimo_por_id(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ultimo: dict[str, dict[str, Any]] = {}
    for registro in registros:
        ultimo[registro.get("id", "")] = registro
    return list(ultimo.values())


def _afirmaciones_vigentes(proyecto: Proyecto) -> list[dict[str, Any]]:
    return _ultimo_por_id(proyecto.almacen.leer_jsonl(proyecto.almacen.afirmaciones))


def _refutaciones(proyecto: Proyecto) -> list[dict[str, Any]]:
    return _ultimo_por_id(proyecto.almacen.leer_jsonl(proyecto.almacen.refutaciones))


def _restricciones_vigentes(proyecto: Proyecto) -> list[dict[str, Any]]:
    return [
        r for r in _ultimo_por_id(proyecto.almacen.leer_jsonl(proyecto.almacen.restricciones))
        if r.get("estado") != "revocada"
    ]


def _figuras(proyecto: Proyecto) -> list[dict[str, Any]]:
    carpeta = proyecto.almacen.raiz / "contexto" / "figuras_reales"
    if not carpeta.exists():
        return []
    return [
        proyecto.almacen.leer_json(fichero)
        for fichero in sorted(carpeta.glob("*.json"))
    ]


def _exigir_afirmacion(proyecto: Proyecto, identificador: str) -> dict[str, Any]:
    afirmacion = next(
        (a for a in _afirmaciones_vigentes(proyecto) if a["id"] == identificador), None
    )
    if afirmacion is None:
        raise ErrorStoryMaker(
            "ERR-304", f"No existe la afirmacion {identificador}", afirmacion=identificador
        )
    return afirmacion
