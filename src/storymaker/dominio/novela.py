"""E5 y E6 - Redaccion, refinamiento y versionado de la Novela (RF-040 a RF-056).

ADR-05 fija el versionado: **escenas inmutables con puntero de vigencia por
rama.** Cada generacion produce una version nueva; nada se sobrescribe.
`ramas.json` mapea cada par de escena y rama a su version vigente, y es la unica
fuente de esa verdad. La version no lleva un campo `vigente` propio, porque dos
sitios que afirman lo mismo acaban divergiendo y aqui no hay transacciones que lo
impidan.

Cambiar la version vigente es escribir un puntero: barato y reversible, que es
justo lo que RF-056 necesita para conservar la mejor version y no la ultima. El
diff entre dos versiones alimenta RF-044, y la comparacion de hashes alimenta
RF-067, que prohibe aprobar un capitulo rechazado cuyo texto no ha cambiado.
"""

from __future__ import annotations

import difflib
from typing import Any, Iterable

from storymaker import SCHEMA_VERSION
from storymaker.bucles import Evaluacion
from storymaker.errores import ErrorStoryMaker
from storymaker.ids import id_pasaje, id_version_escena, normalizar, sha256_texto
from storymaker.proyecto import Proyecto
from storymaker.sobre import ahora

RAMA_PRINCIPAL = "principal"


def contar_palabras(texto: str) -> int:
    """La palabra es la unidad canonica del arnes (D28)."""
    return len([palabra for palabra in texto.split() if palabra.strip()])


# ==========================================================================
# Escribir y refinar
# ==========================================================================


def escribir(
    proyecto: Proyecto,
    id_escena: str,
    texto: str,
    *,
    id_unidad: str,
    ejecucion: str,
    iteracion: int = 1,
    rama: str = RAMA_PRINCIPAL,
    es_piloto: bool = False,
    hallazgos_aplicados: Iterable[str] = (),
    revelaciones_portadas: Iterable[str] = (),
) -> dict[str, Any]:
    """RF-040: persiste una version nueva de escena. Nunca sobrescribe.

    La puerta de INV-1 corre aqui aunque el hook `guard-canon` ya la haya corrido
    antes: el hook protege de un agente descaminado, esto protege de un error en el
    hook. La redundancia es deliberada.
    """
    plan = proyecto.exigir_canon_aprobado()

    # INV-9: fuera del piloto, ninguna escena se produce antes de que el piloto
    # haya sido aceptado.
    if not es_piloto and not proyecto.estado.piloto_aceptado:
        raise ErrorStoryMaker(
            "ERR-502",
            "No se produce en serie antes de que el Autor acepte la escena piloto "
            "(INV-9, RF-046)",
            escena=id_escena,
        )

    ficha = _ficha_de_escena(plan, id_escena)
    numero = _siguiente_numero_version(proyecto, id_escena)
    id_esv = id_version_escena(id_escena, numero)
    palabras = contar_palabras(texto)

    # Se guarda el texto crudo tambien como blob: primer paso del orden canonico
    # de persistencia (blob, ledger, artefacto, indice, puntero).
    proyecto.almacen.guardar_blob(texto)

    proyecto.almacen.escribir_texto(proyecto.almacen.texto_escena(id_escena, id_esv), texto)
    meta = {
        "schema_version": SCHEMA_VERSION,
        "id": id_esv,
        "escena": id_escena,
        "capitulo": ficha["capitulo"],
        "rama": rama,
        "version": numero,
        "texto_ref": str(proyecto.almacen.texto_escena(id_escena, id_esv).name),
        "hash_texto": sha256_texto(texto),
        "palabras": palabras,
        "presupuesto_palabras": ficha["escena"].get("presupuesto_palabras"),
        "canon_plan_version": plan["id"],
        "guia_estilo_hash": (proyecto.encargo() or {}).get("guia_estilo_hash"),
        "udt_origen": id_unidad,
        "ejecucion": ejecucion,
        "iteracion": iteracion,
        "es_piloto": es_piloto,
        "protegido_palabras": 0,
        "pasajes_protegidos": [],
        "hallazgos_aplicados": list(hallazgos_aplicados),
        "revelaciones_portadas": list(revelaciones_portadas),
        "evaluacion": None,
        "modo_cierre": None,
        "creado_en": ahora(),
    }
    proyecto.almacen.escribir_json(proyecto.almacen.meta_escena(id_escena, id_esv), meta)

    # El puntero va el ultimo: nunca un puntero a algo que no existe (ADR-04).
    fijar_vigente(proyecto, id_escena, id_esv, rama)

    return {
        "version_escena": meta,
        "extension": comprobar_extension(meta),
    }


def refinar(
    proyecto: Proyecto,
    id_escena: str,
    texto_refinado: str,
    *,
    id_unidad: str,
    ejecucion: str,
    iteracion: int,
    rama: str = RAMA_PRINCIPAL,
    justificaciones_proteccion: dict[str, str] | None = None,
) -> dict[str, Any]:
    """RF-050 y RF-054: version refinada, sin tocar pasajes protegidos.

    Un pasaje protegido resolvio en su dia un hallazgo bloqueante. Reescribirlo sin
    justificacion registrada es exactamente la oscilacion que el mecanismo existe
    para evitar: se corrige un anacronismo, el refinador lo reescribe por estilo, y
    el anacronismo vuelve.
    """
    vigente = version_vigente(proyecto, id_escena, rama)
    if vigente is None:
        raise ErrorStoryMaker(
            "ERR-506", f"No hay version vigente de {id_escena} que refinar", escena=id_escena
        )
    meta_anterior = _meta(proyecto, id_escena, vigente)
    texto_anterior = proyecto.almacen.leer_texto(
        proyecto.almacen.texto_escena(id_escena, vigente), ""
    )

    violados = pasajes_protegidos_alterados(
        texto_anterior, texto_refinado, meta_anterior.get("pasajes_protegidos", [])
    )
    justificaciones = justificaciones_proteccion or {}
    sin_justificar = [p for p in violados if not justificaciones.get(p)]
    if sin_justificar:
        raise ErrorStoryMaker(
            "ERR-708",
            "El refinado altera pasajes protegidos sin justificacion registrada: "
            f"{sin_justificar}. La justificacion se somete al validador (RF-054).",
            escena=id_escena,
            pasajes=sin_justificar,
        )

    resultado = escribir(
        proyecto, id_escena, texto_refinado,
        id_unidad=id_unidad, ejecucion=ejecucion, iteracion=iteracion, rama=rama,
        es_piloto=meta_anterior.get("es_piloto", False),
        hallazgos_aplicados=meta_anterior.get("hallazgos_aplicados", []),
        revelaciones_portadas=meta_anterior.get("revelaciones_portadas", []),
    )

    # Las protecciones se heredan: lo que resolvio un bloqueante lo sigue
    # resolviendo mientras nadie diga lo contrario.
    nueva = resultado["version_escena"]
    nueva["pasajes_protegidos"] = meta_anterior.get("pasajes_protegidos", [])
    nueva["protegido_palabras"] = sum(
        contar_palabras(p.get("texto", "")) for p in nueva["pasajes_protegidos"]
    )
    if violados:
        nueva["protecciones_reescritas"] = [
            {"pasaje": p, "justificacion": justificaciones[p], "pendiente_validador": True}
            for p in violados
        ]
    proyecto.almacen.escribir_json(
        proyecto.almacen.meta_escena(id_escena, nueva["id"]), nueva
    )

    return {
        "version_escena": nueva,
        "diff_resumen": resumen_diff(texto_anterior, texto_refinado),
        "protecciones_reescritas": violados,
    }


def proteger_pasaje(
    proyecto: Proyecto,
    id_escena: str,
    texto_pasaje: str,
    id_hallazgo_resuelto: str,
    *,
    rama: str = RAMA_PRINCIPAL,
) -> dict[str, Any]:
    """RF-054: marca como protegido el pasaje que resolvio un bloqueante."""
    vigente = version_vigente(proyecto, id_escena, rama)
    if vigente is None:
        raise ErrorStoryMaker("ERR-506", f"No hay version vigente de {id_escena}")
    meta = _meta(proyecto, id_escena, vigente)
    texto = proyecto.almacen.leer_texto(proyecto.almacen.texto_escena(id_escena, vigente), "")
    if normalizar(texto_pasaje) not in normalizar(texto or ""):
        raise ErrorStoryMaker(
            "ERR-304",
            "El pasaje que se pretende proteger no aparece en la version vigente",
            escena=id_escena,
        )

    protegidos = list(meta.get("pasajes_protegidos", []))
    protegidos.append({
        "id": id_pasaje(vigente, len(protegidos) + 1),
        "texto": texto_pasaje,
        "hallazgo_resuelto": id_hallazgo_resuelto,
        "protegido_en": ahora(),
        "vigente": True,
    })
    meta["pasajes_protegidos"] = protegidos
    meta["protegido_palabras"] = sum(
        contar_palabras(p["texto"]) for p in protegidos if p.get("vigente", True)
    )
    proyecto.almacen.escribir_json(proyecto.almacen.meta_escena(id_escena, vigente), meta)
    return {"version_escena": meta, "superficie": superficie_protegida(meta)}


def liberar_protecciones_caducas(
    proyecto: Proyecto, hallazgos_aun_abiertos: Iterable[str], rama: str = RAMA_PRINCIPAL
) -> dict[str, Any]:
    """RNF-026: la pasada global libera las protecciones que ya no sostienen nada.

    Sin esta liberacion la superficie protegida solo crece, y una novela en la que
    el 30 % del texto no se puede tocar deja de ser refinable.
    """
    abiertos = set(hallazgos_aun_abiertos)
    liberadas: list[str] = []
    for id_escena, id_esv in (proyecto.ramas().get(rama) or {}).items():
        meta = _meta(proyecto, id_escena, id_esv)
        cambio = False
        for pasaje in meta.get("pasajes_protegidos", []):
            if pasaje.get("vigente", True) and pasaje.get("hallazgo_resuelto") not in abiertos:
                pasaje["vigente"] = False
                pasaje["liberado_en"] = ahora()
                liberadas.append(pasaje["id"])
                cambio = True
        if cambio:
            meta["protegido_palabras"] = sum(
                contar_palabras(p["texto"])
                for p in meta["pasajes_protegidos"]
                if p.get("vigente", True)
            )
            proyecto.almacen.escribir_json(
                proyecto.almacen.meta_escena(id_escena, id_esv), meta
            )
    return {"protecciones_liberadas": liberadas, "total": len(liberadas)}


def pasajes_protegidos_alterados(
    texto_anterior: str, texto_nuevo: str, protegidos: Iterable[dict[str, Any]]
) -> list[str]:
    """Que pasajes protegidos ya no aparecen intactos en el texto nuevo."""
    normalizado = normalizar(texto_nuevo)
    return [
        pasaje["id"]
        for pasaje in protegidos
        if pasaje.get("vigente", True) and normalizar(pasaje.get("texto", "")) not in normalizado
    ]


def superficie_protegida(meta: dict[str, Any]) -> dict[str, Any]:
    palabras = meta.get("palabras", 0)
    protegidas = meta.get("protegido_palabras", 0)
    proporcion = protegidas / palabras if palabras else 0.0
    return {
        "palabras": palabras,
        "protegidas": protegidas,
        "proporcion": round(proporcion, 4),
        "aviso_umbral_capitulo": proporcion > 0.15,
    }


# ==========================================================================
# Vigencia y ramas (ADR-05)
# ==========================================================================


def fijar_vigente(
    proyecto: Proyecto, id_escena: str, id_esv: str, rama: str = RAMA_PRINCIPAL
) -> dict[str, Any]:
    """Escribe el puntero de vigencia. Es la unica fuente de esa verdad."""
    ramas = proyecto.ramas()
    ramas.setdefault(rama, {})[id_escena] = id_esv
    proyecto.almacen.escribir_json(proyecto.almacen.ramas, ramas)
    return ramas


def version_vigente(
    proyecto: Proyecto, id_escena: str, rama: str = RAMA_PRINCIPAL
) -> str | None:
    return (proyecto.ramas().get(rama) or {}).get(id_escena)


def ramificar(
    proyecto: Proyecto, id_escena: str, nombre_rama: str, motivo: str
) -> dict[str, Any]:
    """Abre una rama alternativa desde la version vigente.

    Ocurre cuando el Autor rechaza una salida. El ensamblado final lee siempre la
    rama principal; promover una alternativa es reescribir un puntero.
    """
    vigente = version_vigente(proyecto, id_escena)
    if vigente is None:
        raise ErrorStoryMaker("ERR-506", f"No hay version vigente de {id_escena} desde la que ramificar")
    ramas = proyecto.ramas()
    ramas.setdefault("alternativas", {}).setdefault(nombre_rama, {
        "motivo": motivo, "creada_en": ahora(), "escenas": {},
    })
    ramas["alternativas"][nombre_rama]["escenas"][id_escena] = vigente
    ramas.setdefault(nombre_rama, {})[id_escena] = vigente
    proyecto.almacen.escribir_json(proyecto.almacen.ramas, ramas)
    return {"rama": nombre_rama, "escena": id_escena, "desde": vigente}


def promover(
    proyecto: Proyecto, id_escena: str, nombre_rama: str
) -> dict[str, Any]:
    """Promueve una alternativa a la rama principal: reescribir un puntero."""
    candidata = (proyecto.ramas().get(nombre_rama) or {}).get(id_escena)
    if candidata is None:
        raise ErrorStoryMaker(
            "ERR-506", f"La rama {nombre_rama} no tiene version de {id_escena}"
        )
    fijar_vigente(proyecto, id_escena, candidata, RAMA_PRINCIPAL)
    return {"escena": id_escena, "version_promovida": candidata, "desde_rama": nombre_rama}


def conservar_mejor(
    proyecto: Proyecto,
    id_escena: str,
    evaluaciones: dict[str, Evaluacion],
    rama: str = RAMA_PRINCIPAL,
) -> dict[str, Any]:
    """RF-056 e INV-4: la Novela contiene la mejor version evaluada, no la ultima.

    Se registra ademas cuales se descartan, porque una version descartada sigue
    siendo evidencia de lo que se intento.
    """
    if not evaluaciones:
        raise ErrorStoryMaker(
            "ERR-302", "No hay evaluaciones con las que elegir la mejor version"
        )
    mejor = max(evaluaciones.items(), key=lambda par: par[1].total)
    fijar_vigente(proyecto, id_escena, mejor[0], rama)
    for id_esv, evaluacion in evaluaciones.items():
        meta = _meta(proyecto, id_escena, id_esv)
        meta["evaluacion"] = evaluacion.como_dict()
        meta["descartada"] = id_esv != mejor[0]
        proyecto.almacen.escribir_json(proyecto.almacen.meta_escena(id_escena, id_esv), meta)
    return {
        "version_vigente": mejor[0],
        "puntuacion": mejor[1].total,
        "descartadas": sorted(v for v in evaluaciones if v != mejor[0]),
    }


def cerrar_escena(
    proyecto: Proyecto,
    id_escena: str,
    modo_cierre: str,
    *,
    rama: str = RAMA_PRINCIPAL,
    hallazgos_pendientes: Iterable[str] = (),
) -> dict[str, Any]:
    """RF-055: registra con cual de los cuatro modos se cerro el bucle interno."""
    vigente = version_vigente(proyecto, id_escena, rama)
    if vigente is None:
        raise ErrorStoryMaker("ERR-506", f"No hay version vigente de {id_escena} que cerrar")
    meta = _meta(proyecto, id_escena, vigente)
    meta["modo_cierre"] = modo_cierre
    meta["cerrada_en"] = ahora()
    meta["hallazgos_pendientes_al_cerrar"] = list(hallazgos_pendientes)
    proyecto.almacen.escribir_json(proyecto.almacen.meta_escena(id_escena, vigente), meta)
    return {"version_escena": meta}


# ==========================================================================
# Extension, diff y sinopsis
# ==========================================================================


def comprobar_extension(meta: dict[str, Any], tolerancia: float = 0.20) -> dict[str, Any]:
    """RF-042: extension dentro del presupuesto de la escena, con tolerancia.

    La tolerancia por escena es mas laxa que la de la novela (RNF-012): una escena
    puede desviarse si otra compensa. Lo que no puede desviarse es el total.
    """
    presupuesto = meta.get("presupuesto_palabras")
    palabras = meta.get("palabras", 0)
    if not presupuesto:
        return {"evaluable": False, "motivo": "la ficha no declara presupuesto de palabras"}
    desviacion = (palabras - presupuesto) / presupuesto
    return {
        "evaluable": True,
        "palabras": palabras,
        "presupuesto": presupuesto,
        "desviacion": round(desviacion, 4),
        "dentro_de_tolerancia": abs(desviacion) <= tolerancia,
        "severidad_si_fuera": "mayor",
    }


def resumen_diff(anterior: str, nuevo: str) -> dict[str, Any]:
    """Alimenta RF-044: la correccion debe ser localizada, no una reescritura.

    Si el refinado cambia casi todo, no esta aplicando hallazgos: esta reescribiendo,
    y eso es justo lo que RF-044 prohibe.
    """
    lineas_antes = (anterior or "").splitlines()
    lineas_ahora = (nuevo or "").splitlines()
    diff = list(difflib.unified_diff(lineas_antes, lineas_ahora, lineterm="", n=0))
    anadidas = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
    borradas = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
    total = max(len(lineas_antes), 1)
    return {
        "lineas_anadidas": anadidas,
        "lineas_borradas": borradas,
        "proporcion_tocada": round((anadidas + borradas) / (2 * total), 4),
        "hash_anterior": sha256_texto(anterior or ""),
        "hash_nuevo": sha256_texto(nuevo or ""),
        "texto_cambio": (anterior or "") != (nuevo or ""),
    }


def escribir_sinopsis(proyecto: Proyecto, id_capitulo: str, texto: str) -> dict[str, Any]:
    """Seccion 3.5: un acta por capitulo, congelada al cerrarlo.

    Nunca se reescribe. Un capitulo cerrado tiene su sinopsis congelada, igual que
    su texto: si la sinopsis cambiara, el redactor de un capitulo posterior veria
    una novela distinta de la que se escribio.
    """
    from storymaker.manifiesto import normalizar_sinopsis

    ruta = proyecto.almacen.sinopsis(id_capitulo)
    if ruta.exists():
        raise ErrorStoryMaker(
            "ERR-604",
            f"La sinopsis de {id_capitulo} ya esta congelada y no se reescribe",
            capitulo=id_capitulo,
        )
    contenido = normalizar_sinopsis(texto)
    proyecto.almacen.escribir_texto(ruta, contenido)
    return {"capitulo": id_capitulo, "palabras": contar_palabras(contenido)}


def sinopsis_disponibles(proyecto: Proyecto) -> list[tuple[str, str]]:
    carpeta = proyecto.almacen.raiz / "novela" / "sinopsis"
    if not carpeta.exists():
        return []
    return [
        (fichero.stem, fichero.read_text(encoding="utf-8"))
        for fichero in sorted(carpeta.glob("*.md"))
    ]


# -- interno ---------------------------------------------------------------


def _meta(proyecto: Proyecto, id_escena: str, id_esv: str) -> dict[str, Any]:
    meta = proyecto.almacen.leer_json(proyecto.almacen.meta_escena(id_escena, id_esv))
    if meta is None:
        raise ErrorStoryMaker(
            "ERR-506", f"No existen metadatos de la version {id_esv}", escena=id_escena
        )
    return meta


def _siguiente_numero_version(proyecto: Proyecto, id_escena: str) -> int:
    carpeta = proyecto.almacen.raiz / "novela" / "escenas" / id_escena
    if not carpeta.exists():
        return 1
    numeros = []
    for fichero in carpeta.glob("esv_*.json"):
        marca = fichero.stem.rsplit("_v", 1)
        if len(marca) == 2 and marca[1].isdigit():
            numeros.append(int(marca[1]))
    return max(numeros, default=0) + 1


def _ficha_de_escena(plan: dict[str, Any], id_escena: str) -> dict[str, Any]:
    for capitulo in plan.get("capitulos", []):
        for escena in capitulo.get("escenas", []):
            if escena.get("id") == id_escena:
                return {"capitulo": capitulo["id"], "escena": escena}
    raise ErrorStoryMaker(
        "ERR-304",
        f"La escena {id_escena} no existe en el Canon vigente. El redactor no inventa "
        "escenas: emite hallazgo contra el Canon (RF-043, ERR-602).",
        escena=id_escena,
        canon=plan.get("id"),
    )
