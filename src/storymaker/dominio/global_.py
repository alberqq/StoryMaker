"""E8 - Pasada global, terminacion y entrega (RF-068, RF-077 a RF-093).

La pasada global detecta lo que es invisible desde dentro de un capitulo: deriva
de voz entre el principio y el final, hilos abiertos sin cerrar, personajes
indistinguibles, repeticiones a larga distancia, desequilibrio de ritmo.

Es la unica etapa con permiso de lectura total, y se invoca una vez.

Sobre RF-077: el estado de los hilos se **recalcula aqui**, en el momento de
decidir, y nunca se lee de `idx_hilos_estado`. MD-6 lo prohibe: un indice puede
estar obsoleto, y la decision de declarar terminada una novela no puede apoyarse
en algo que puede estarlo.
"""

from __future__ import annotations

import re
from typing import Any

from storymaker import SCHEMA_VERSION
from storymaker.dominio import novela as dominio_novela
from storymaker.dominio import validacion as dominio_validacion
from storymaker.errores import ErrorStoryMaker
from storymaker.ids import normalizar
from storymaker.invariantes import comprobar_terminacion
from storymaker.proyecto import (
    FINALIZADO,
    FINALIZADO_CON_RESERVAS,
    Proyecto,
)
from storymaker.sobre import ahora


# ==========================================================================
# Estado de hilos, recalculado (MD-6)
# ==========================================================================


def recalcular_estado_hilos(
    proyecto: Proyecto, rama: str = "principal"
) -> dict[str, str]:
    """Estado real de cada hilo a partir de las escenas validadas.

    Se calcula, no se consulta. Un hilo esta resuelto cuando su escena de
    resolucion existe en la rama vigente y su capitulo esta validado; avanzado
    cuando alguna de sus escenas de avance lo esta; abierto cuando solo lo esta su
    apertura; planificado cuando nada de eso ha ocurrido todavia.
    """
    plan = proyecto.exigir_canon_aprobado()
    ramas = proyecto.ramas().get(rama) or {}
    validados = set(dominio_validacion.capitulos_validados(proyecto))

    capitulo_de_escena: dict[str, str] = {}
    for capitulo in plan.get("capitulos", []):
        for escena in capitulo.get("escenas", []):
            capitulo_de_escena[escena["id"]] = capitulo["id"]

    def realizada(id_escena: str | None) -> bool:
        if not id_escena or id_escena not in ramas:
            return False
        return capitulo_de_escena.get(id_escena) in validados

    estado: dict[str, str] = {}
    for hilo in plan.get("hilos", []):
        if realizada(hilo.get("escena_resolucion")):
            estado[hilo["id"]] = "resuelto"
        elif any(realizada(e) for e in hilo.get("escenas_avance", [])):
            estado[hilo["id"]] = "avanzado"
        elif realizada(hilo.get("escena_apertura")):
            estado[hilo["id"]] = "abierto"
        else:
            estado[hilo["id"]] = "planificado"
    return estado


# ==========================================================================
# Indicadores de la pasada global
# ==========================================================================


def indicadores_de_estilo(texto: str) -> dict[str, float]:
    """Los tres indicadores medibles de RNF-010.

    Son deliberadamente simples y deliberadamente insuficientes: miden lo que se
    puede medir sin calibracion empirica sobre el castellano. La deteccion fina de
    deriva de voz es T-03 en la lista de asuntos abiertos, y la primera novela
    completa dara los datos para afinarla.
    """
    frases = [f for f in re.split(r"[.!?]+", texto) if f.strip()]
    palabras = texto.split()
    if not palabras:
        return {"longitud_media_frase": 0.0, "densidad_adjetival": 0.0, "proporcion_dialogo": 0.0}

    # Aproximacion por sufijos frecuentes del adjetivo en castellano. No es un
    # analizador morfologico, y no pretende serlo.
    sufijos = ("oso", "osa", "osos", "osas", "ico", "ica", "icos", "icas",
               "able", "ible", "ante", "ente", "ivo", "iva", "al", "ales")
    adjetivos = sum(1 for p in palabras if normalizar(p).endswith(sufijos))

    lineas = texto.splitlines()
    dialogo = sum(1 for l in lineas if l.lstrip().startswith(("-", "—", "–", '"')))

    return {
        "longitud_media_frase": round(len(palabras) / max(len(frases), 1), 2),
        "densidad_adjetival": round(adjetivos / len(palabras), 4),
        "proporcion_dialogo": round(dialogo / max(len(lineas), 1), 4),
    }


# Palabras minimas por tercio para que la comparacion signifique algo. Por debajo
# de esto, una sola frase larga mueve la longitud media y dos adjetivos mueven la
# densidad adjetival un ciento por ciento: lo que se mide es la varianza del
# muestreo, no la voz. Un indicador que no puede distinguir ruido de senal no debe
# bloquear una entrega, igual que no la bloquea una novela de dos capitulos.
MINIMO_PALABRAS_POR_TERCIO = 1_000


def motivo_no_evaluable(
    capitulos: int, palabras_primer_tercio: int, palabras_ultimo_tercio: int
) -> str | None:
    """Por que no puede medirse la deriva, o None si puede.

    Dos guardas, y las dos dicen lo mismo con distinta cara: no hay muestra. Con
    menos de tres capitulos los tercios no separan nada, y con tercios demasiado
    cortos lo que varia es el muestreo.
    """
    if capitulos < 3:
        return "menos de tres capitulos; los tercios no separan nada"
    menor = min(palabras_primer_tercio, palabras_ultimo_tercio)
    if menor < MINIMO_PALABRAS_POR_TERCIO:
        return (
            f"el tercio mas corto tiene {menor} palabras, por debajo de las "
            f"{MINIMO_PALABRAS_POR_TERCIO} que hacen falta para distinguir deriva "
            "de ruido de muestreo"
        )
    return None


def deriva_de_voz(
    proyecto: Proyecto, banda: float = 0.25, rama: str = "principal"
) -> dict[str, Any]:
    """RNF-010: desviacion de los indicadores entre el primer y el ultimo tercio."""
    capitulos = _capitulos_ordenados(proyecto)
    corte = max(1, len(capitulos) // 3)
    unir = "\n".join
    primero = unir(
        dominio_validacion.texto_capitulo(proyecto, c, rama) for c in capitulos[:corte]
    )
    ultimo = unir(
        dominio_validacion.texto_capitulo(proyecto, c, rama) for c in capitulos[-corte:]
    )

    motivo = motivo_no_evaluable(len(capitulos), len(primero.split()), len(ultimo.split()))
    if motivo is not None:
        return {
            "evaluable": False,
            "motivo": motivo,
            "palabras_por_tercio": {"primero": len(primero.split()), "ultimo": len(ultimo.split())},
            # Los valores se entregan igualmente, marcados como informativos: no
            # deciden nada, pero al Autor le dicen algo.
            "indicadores_informativos": {
                "primer_tercio": indicadores_de_estilo(primero),
                "ultimo_tercio": indicadores_de_estilo(ultimo),
            },
        }

    inicio = indicadores_de_estilo(primero)
    final = indicadores_de_estilo(ultimo)
    desviaciones = {}
    for clave, valor_inicial in inicio.items():
        if valor_inicial:
            desviaciones[clave] = round(abs(final[clave] - valor_inicial) / valor_inicial, 4)
        else:
            desviaciones[clave] = 0.0

    fuera = sorted(clave for clave, valor in desviaciones.items() if valor > banda)
    return {
        "evaluable": True,
        "primer_tercio": inicio,
        "ultimo_tercio": final,
        "desviacion_relativa": desviaciones,
        "banda": banda,
        "indicadores_fuera_de_banda": fuera,
        "dentro_de_banda": not fuera,
    }


def repeticiones_a_larga_distancia(
    proyecto: Proyecto, longitud_minima: int = 8, rama: str = "principal"
) -> list[dict[str, Any]]:
    """Frases largas repetidas en capitulos distantes.

    Solo se señalan si estan a mas de tres capitulos de distancia: una repeticion
    proxima suele ser un eco deliberado, y una lejana casi nunca lo es.
    """
    capitulos = _capitulos_ordenados(proyecto)
    vistas: dict[str, list[tuple[int, str]]] = {}
    for indice, id_capitulo in enumerate(capitulos):
        texto = dominio_validacion.texto_capitulo(proyecto, id_capitulo, rama)
        palabras = normalizar(texto).split()
        for inicio in range(0, max(0, len(palabras) - longitud_minima)):
            ventana = " ".join(palabras[inicio:inicio + longitud_minima])
            vistas.setdefault(ventana, []).append((indice, id_capitulo))

    hallazgos = []
    for ventana, apariciones in vistas.items():
        capitulos_distintos = sorted({c for _, c in apariciones})
        if len(capitulos_distintos) < 2:
            continue
        indices = sorted({i for i, _ in apariciones})
        if indices[-1] - indices[0] < 3:
            continue
        hallazgos.append({
            "fragmento": ventana,
            "capitulos": capitulos_distintos,
            "distancia_capitulos": indices[-1] - indices[0],
        })
    return sorted(hallazgos, key=lambda h: -h["distancia_capitulos"])[:50]


def pasada_global(
    proyecto: Proyecto, banda_estilo: float = 0.25, rama: str = "principal"
) -> dict[str, Any]:
    """RF-068: todo lo que solo se ve mirando la novela entera."""
    estado_hilos = recalcular_estado_hilos(proyecto, rama)
    encargo = proyecto.encargo() or {}
    autorizados = set(encargo.get("hilos_abiertos_autorizados", []))
    sin_resolver = sorted(
        identificador for identificador, situacion in estado_hilos.items()
        if situacion != "resuelto" and identificador not in autorizados
    )

    gestor_protegido = _superficie_protegida(proyecto, rama)
    deriva = deriva_de_voz(proyecto, banda_estilo, rama)
    palabras = _palabras_totales(proyecto, rama)
    objetivo = encargo.get("extension_objetivo_palabras") or 0
    tolerancia = encargo.get("tolerancia_extension", 0.10)

    informe = {
        "schema_version": SCHEMA_VERSION,
        "momento": ahora(),
        "hilos": {"estado": estado_hilos, "sin_resolver": sin_resolver},
        "deriva_de_voz": deriva,
        "repeticiones_larga_distancia": repeticiones_a_larga_distancia(proyecto, rama=rama),
        "superficie_protegida": gestor_protegido,
        "extension": {
            "palabras": palabras,
            "objetivo": objetivo,
            "tolerancia": tolerancia,
            "dentro_de_tolerancia": (
                not objetivo or abs(palabras - objetivo) <= objetivo * tolerancia
            ),
        },
    }
    informe["superada"] = (
        not sin_resolver
        and deriva.get("dentro_de_banda", True)
        and informe["extension"]["dentro_de_tolerancia"]
    )
    proyecto.almacen.escribir_json(
        proyecto.almacen.raiz / "novela" / "pasada_global.json", informe
    )
    return informe


# ==========================================================================
# Terminacion (RF-077)
# ==========================================================================


def cerrar_novela(
    proyecto: Proyecto,
    hallazgos_bloqueantes_abiertos: int = 0,
    rama: str = "principal",
) -> dict[str, Any]:
    """Las cinco condiciones simultaneas de RF-077, o la que falta.

    No hay aproximacion: o se cumplen las cinco, o la novela no se declara
    finalizada. Lo que si admite matiz es el estado resultante, porque un Proyecto
    que en algun momento aprobo algo con bloqueantes asumidos ya solo puede
    alcanzar *finalizado con reservas*.
    """
    plan = proyecto.exigir_canon_aprobado()
    encargo = proyecto.encargo() or {}
    informe = proyecto.almacen.leer_json(
        proyecto.almacen.raiz / "novela" / "pasada_global.json", {}
    ) or {}

    fallos = comprobar_terminacion(
        plan,
        dominio_validacion.capitulos_validados(proyecto),
        recalcular_estado_hilos(proyecto, rama),
        hallazgos_bloqueantes_abiertos,
        bool(informe.get("superada")),
        _palabras_totales(proyecto, rama),
        encargo,
    )

    if fallos:
        return {
            "finalizada": False,
            "condiciones_que_faltan": [f.como_dict() for f in fallos],
            "estado": proyecto.estado.estado,
        }

    estado_final = (
        FINALIZADO_CON_RESERVAS if proyecto.estado.limitado_a_reservas else FINALIZADO
    )
    proyecto.guardar(estado=estado_final, etapa="Entrega")
    return {
        "finalizada": True,
        "estado": estado_final,
        "motivo_reservas": proyecto.estado.motivo_reservas,
        "palabras": _palabras_totales(proyecto, rama),
    }


# ==========================================================================
# Ensamblado y entrega (RF-090 a RF-093)
# ==========================================================================


def ensamblar(proyecto: Proyecto, rama: str = "principal") -> dict[str, Any]:
    """RF-090: la novela final, a partir de la version vigente de cada escena.

    El orden lo fija el Canon vigente, no el sistema de ficheros. Una escena sin
    version vigente aborta el ensamblado con ERR-506 en lugar de entregarse con un
    agujero.
    """
    plan = proyecto.exigir_canon_aprobado()
    ramas = proyecto.ramas().get(rama) or {}
    partes: list[str] = []
    palabras = 0
    faltantes: list[str] = []

    for capitulo in sorted(plan.get("capitulos", []), key=lambda c: c.get("orden", 0)):
        titulo = capitulo.get("titulo") or capitulo["id"]
        partes.append(f"# {titulo}")
        for escena in sorted(capitulo.get("escenas", []), key=lambda e: e.get("orden", 0)):
            vigente = ramas.get(escena["id"])
            if vigente is None:
                faltantes.append(escena["id"])
                continue
            texto = proyecto.almacen.leer_texto(
                proyecto.almacen.texto_escena(escena["id"], vigente)
            )
            if texto is None:
                faltantes.append(escena["id"])
                continue
            partes.append(texto.strip())
            palabras += dominio_novela.contar_palabras(texto)

    if faltantes:
        raise ErrorStoryMaker(
            "ERR-506",
            f"Faltan versiones vigentes de {len(faltantes)} escenas: no se ensambla una "
            "novela con agujeros",
            escenas=faltantes[:20],
        )

    markdown = "\n\n".join(partes) + "\n"
    ruta = proyecto.almacen.entrega / "novela.md"
    proyecto.almacen.escribir_texto(ruta, markdown)
    return {"ruta": str(ruta), "palabras": palabras, "capitulos": len(plan.get("capitulos", []))}


def generar_entrega(
    proyecto: Proyecto,
    *,
    con_pdf: bool = True,
    rama: str = "principal",
) -> dict[str, Any]:
    """RF-091 a RF-093: la novela mas su paquete de trazabilidad.

    El PDF se intenta y puede fallar (ERR-902); el Markdown es el formato canonico
    y nunca falla en silencio. RNF-025 exige que si ambos existen, su texto sea el
    mismo: solo pueden diferir la paginacion y la presentacion.
    """
    ensamblado = ensamblar(proyecto, rama)
    paquete = paquete_trazabilidad(proyecto)

    ruta_paquete = proyecto.almacen.entrega / "paquete_trazabilidad.json"
    proyecto.almacen.escribir_json(ruta_paquete, paquete)

    formatos = {"markdown": {"ruta": ensamblado["ruta"], "ok": True}}
    avisos: list[str] = []
    if con_pdf:
        formatos["pdf"] = _intentar_pdf(proyecto, ensamblado["ruta"])
        if not formatos["pdf"]["ok"]:
            avisos.append(
                "ERR-902: no se pudo generar el PDF. Se entrega solo Markdown y se declara."
            )

    return {
        "formatos": formatos,
        "paquete_trazabilidad": str(ruta_paquete),
        "palabras": ensamblado["palabras"],
        "estado_proyecto": proyecto.estado.estado,
        "avisos": avisos,
    }


def paquete_trazabilidad(proyecto: Proyecto) -> dict[str, Any]:
    """RF-091, RF-092 y RF-078: todo lo que acompaña a la novela.

    Incluye las Licencias de alcance una sola vez, con sus limites y los pasajes
    que amparan, en lugar de repetirlas escena a escena (RF-092).
    """
    almacen = proyecto.almacen
    licencias = almacen.leer_jsonl(almacen.licencias)
    de_alcance = [l for l in licencias if l.get("alcance") == "proyecto"]
    puntuales = [l for l in licencias if l.get("alcance") != "proyecto"]

    fuentes = almacen.leer_jsonl(almacen.fuentes)
    sin_conservar = [f for f in fuentes if not f.get("contenido_id")]

    return {
        "schema_version": SCHEMA_VERSION,
        "generado_en": ahora(),
        "proyecto": proyecto.estado.como_dict(),
        "encargo": proyecto.encargo(),
        "contexto_historico": {
            "cabecera": proyecto.contexto_cabecera(),
            "afirmaciones": almacen.leer_jsonl(almacen.afirmaciones),
            "refutaciones": almacen.leer_jsonl(almacen.refutaciones),
            "restricciones": almacen.leer_jsonl(almacen.restricciones),
            "fuentes": fuentes,
            "fuentes_sin_contenido_conservado": [
                {"id": f["id"], "motivo": f.get("motivo_no_conservable")}
                for f in sin_conservar
            ],
        },
        "canon_final": proyecto.plan_canon(),
        "licencias": {
            "de_alcance": de_alcance,
            "puntuales": puntuales,
            "nota": (
                "Las Licencias de alcance figuran una sola vez, con sus limites "
                "declarados y la lista de pasajes que amparan (RF-092)."
            ),
        },
        "deuda_de_calidad": almacen.leer_jsonl(almacen.deudas),
        "hallazgos": almacen.leer_jsonl(almacen.hallazgos),
        "pasada_global": almacen.leer_json(almacen.raiz / "novela" / "pasada_global.json"),
    }


def _intentar_pdf(proyecto: Proyecto, ruta_markdown: str) -> dict[str, Any]:
    """Genera el PDF si hay un conversor disponible; si no, lo declara.

    El nucleo no arrastra una dependencia de maquetacion. Si el entorno tiene
    `pandoc`, se usa; si no, se entrega solo Markdown y se dice, que es lo que
    ERR-902 prescribe.
    """
    import shutil
    import subprocess

    pandoc = shutil.which("pandoc")
    if pandoc is None:
        return {
            "ok": False,
            "codigo_error": "ERR-902",
            "motivo": "No hay conversor a PDF disponible en el entorno (se busco pandoc)",
        }
    destino = proyecto.almacen.entrega / "novela.pdf"
    try:
        subprocess.run(
            [pandoc, ruta_markdown, "-o", str(destino)],
            check=True, capture_output=True, timeout=300,
        )
    except Exception as fallo:  # noqa: BLE001 - se degrada, no se propaga
        return {"ok": False, "codigo_error": "ERR-902", "motivo": str(fallo)[:300]}
    return {"ok": True, "ruta": str(destino)}


# -- interno ---------------------------------------------------------------


def _capitulos_ordenados(proyecto: Proyecto) -> list[str]:
    plan = proyecto.exigir_canon_aprobado()
    return [
        capitulo["id"]
        for capitulo in sorted(plan.get("capitulos", []), key=lambda c: c.get("orden", 0))
    ]


def _palabras_totales(proyecto: Proyecto, rama: str = "principal") -> int:
    total = 0
    for id_escena, id_esv in (proyecto.ramas().get(rama) or {}).items():
        meta = proyecto.almacen.leer_json(
            proyecto.almacen.meta_escena(id_escena, id_esv), {}
        ) or {}
        total += meta.get("palabras", 0)
    return total


def _superficie_protegida(proyecto: Proyecto, rama: str = "principal") -> dict[str, Any]:
    from storymaker.indices import GestorIndices

    gestor = GestorIndices(proyecto.almacen)
    gestor.reconstruir_todos()
    return gestor.leer("idx_protegido") or {}
