"""Orquestacion de una Ejecucion desde la interfaz, con dos paradas.

El Autor conduce la Ejecucion entera desde la interfaz, pero no la mira pasar: se
detiene dos veces y le espera.

    arranque -> Contexto historico -> ESPERA ---- el Autor acepta el Contexto
             -> Restricciones y cierre -> Canon -> ESPERA ---- el Autor aprueba
             -> produccion capitulo a capitulo -> pasada global -> entrega

Las dos paradas sustituyen a las etapas de validacion que se retiraron del arnes.
El Autor acepta el Contexto historico, y aprueba el Canon en PC-3 despues de leer
la critica breve que E3 escribe al final de su tramo. Por eso este modulo no firma
ni aprueba nada en nombre de nadie: solo se detiene, y quien decide lo hace desde
la pestana que corresponde, con su nombre.

La produccion, en cambio, **si** conserva sus bucles internos. El refinador y el
validador de capitulo no juzgan el plan ni la historia: trabajan sobre prosa ya
escrita, que es donde el Autor ha dicho que quiere que el arnes siga apretando.

El reparto de trabajo es el de siempre. Los pasos deterministas son ordenes al
nucleo, que es el unico que escribe. Los que investigan o producen prosa son
**etapas**, y las etapas son subagentes que viven dentro de Claude Code: este
modulo las lanza con `claude -p` y espera, pero no las sustituye ni construye sus
manifiestos. No abren ventana: lo que hacen se ve en la interfaz, linea a linea,
segun lo hacen.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gui import langfuse

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = RAIZ / "src"
PROYECTOS = RAIZ / "proyectos"

# Sin reloj. Hubo un limite de media hora por etapa y el tramo de la novela murio
# justo en el tope dos veces, con `GUI-012`, tirando a la basura lo que llevaba
# hecho. Cualquier cifra que se ponga sera corta para una novela larga y larga
# para una corta.
#
# Lo que aborta una etapa es el Autor, no un cronometro: `parar` mata la sesion en
# curso. Es una decision consciente, no un descuido: prefiero que algo se quede
# colgado y se vea, a que se corte solo y haya que rehacerlo entero.
TIEMPO_NUCLEO = 180

# Lo que el proceso espera en cada parada, y donde lo decide el Autor.
PARADAS = {
    "espera_contexto": {
        "titulo": "El Autor acepta el Contexto historico",
        "pestana": "contexto",
        "detalle": (
            "Revisa las afirmaciones y las Restricciones que salen de ellas, y acepta. "
            "Tu firma queda registrada como tuya."
        ),
    },
    "espera_canon": {
        "titulo": "PC-3, el Autor aprueba el Canon",
        "pestana": "canon",
        "detalle": (
            "Aqui no hay validador de Canon. Revisa el plan y apruebalo: sin Canon "
            "aprobado no se redacta una sola escena."
        ),
    },
}

PROCESOS: dict[str, dict[str, Any]] = {}
SENALES: dict[str, threading.Event] = {}
CERROJO = threading.Lock()


def ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def entorno() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(FUENTE)
    env["STORYMAKER_RAIZ"] = "proyectos"
    return env


def nucleo(proyecto: str | None, argumentos: list[str]) -> dict[str, Any]:
    orden = [sys.executable, "-m", "storymaker"]
    if proyecto:
        orden += ["--proyecto", proyecto]
    orden += argumentos
    try:
        hecho = subprocess.run(
            orden, cwd=RAIZ, env=entorno(), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TIEMPO_NUCLEO,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": {"codigo": "GUI-002", "mensaje": "El nucleo no respondio"}}
    try:
        return json.loads((hecho.stdout or "").strip())
    except json.JSONDecodeError:
        return {"ok": False, "error": {
            "codigo": "GUI-003", "mensaje": "El nucleo no devolvio un sobre JSON",
            "salida": (hecho.stdout or "")[:1500], "stderr": (hecho.stderr or "")[:1500],
        }}


# Lo que una etapa necesita poder usar. Sin esto las sesiones corren en modo de
# permisos `default`, y ahi todo lo que no este en el `allow` de settings.json se
# deniega **sin poder preguntar**: la primera Ejecucion real murio asi, con
# WebSearch denegado, cinco minutos y dos euros gastados para registrar cero
# Fuentes.
#
# Aflojar aqui no afloja las garantias. Los permisos son el mecanismo mas romo de
# los tres: los hooks siguen denegando cualquier escritura de estado que no venga
# del nucleo, y el nucleo vuelve a comprobar sus invariantes antes de persistir.
HERRAMIENTAS_DE_ETAPA = (
    "Task", "Bash", "Read", "Glob", "Grep", "Write", "Edit",
    "WebSearch", "WebFetch", "Skill", "ToolSearch",
)


def etapa(prompt: str, anotar=None, *, al_lanzar=None, actividad=None) -> dict[str, Any]:
    """Lanza una sesion de Claude Code para que despache una etapa.

    Sin ventana. Hubo una consola propia por etapa, y se retiro porque no
    aportaba: ensenaba exactamente lo mismo que ya se ve en la interfaz, y
    obligaba a un rodeo por PowerShell con su `Tee-Object`, su fichero de
    registro y su lio de codificaciones.

    Lo que si se conserva es lo unico que justificaba aquella ventana: **la
    salida llega segun se produce**. Con el formato de texto, `claude -p` no
    escribe nada hasta terminar, y un paso que calla durante cinco minutos es
    indistinguible de uno colgado. Con `stream-json` emite un evento por cada
    cosa que hace, y aqui se traducen a lineas legibles conforme llegan.

    El prompt viaja por la linea de ordenes como argumento, no interpolado en
    ninguna cadena que alguien vaya a interpretar.
    """
    ejecutable = shutil.which("claude")
    if ejecutable is None:
        return {"ok": False, "error": {
            "codigo": "GUI-006", "mensaje": "No hay `claude` en el PATH",
        }}

    orden = [
        ejecutable, "-p", prompt,
        "--allowed-tools", *HERRAMIENTAS_DE_ETAPA,
        "--output-format", "stream-json", "--verbose",
    ]

    lineas: list[str] = []
    resultado: dict[str, Any] = {}
    proceso_ = subprocess.Popen(
        orden, cwd=RAIZ, env=entorno(), stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        bufsize=1,
    )

    # La sesion se entrega para que `parar` pueda matarla. Ya no hay reloj que
    # corte solo una etapa colgada, asi que abortarla tiene que estar en manos
    # del Autor, y para eso hace falta el proceso.
    if al_lanzar is not None:
        al_lanzar(proceso_)

    try:
        for cruda in proceso_.stdout or ():
            evento = _evento(cruda)
            if evento.get("type") == "result":
                resultado = evento
            if actividad is not None:
                for suceso in _actividad(evento):
                    actividad(suceso)
            legible = _legible(cruda)
            if legible:
                lineas.append(legible)
                if anotar is not None:
                    anotar(legible)
        codigo = proceso_.wait()
    finally:
        if al_lanzar is not None:
            al_lanzar(None)

    salida = "\n".join(lineas).strip()
    return {
        "ok": codigo == 0,
        "datos": {"salida": salida[-6000:], "consumo": resultado},
        "error": None if codigo == 0 else {
            "codigo": "GUI-013", "mensaje": f"La etapa termino con codigo {codigo}",
            "salida": salida[-6000:],
        },
    }


def _evento(cruda: str) -> dict[str, Any]:
    """Un evento de `stream-json`, o un diccionario vacio si la linea no lo es."""
    cruda = cruda.lstrip("\ufeff").strip()
    if not cruda.startswith("{"):
        return {}
    try:
        return json.loads(cruda)
    except json.JSONDecodeError:
        return {}


def _legible(cruda: str) -> str:
    """Traduce un evento de `stream-json` a una linea que se pueda leer."""
    # La marca de orden de bytes se cuela al principio del registro y hacia que la
    # primera linea se tomara por texto suelto y saliera en crudo.
    cruda = cruda.lstrip("﻿").strip()
    if not cruda.startswith("{"):
        return cruda
    try:
        evento = json.loads(cruda)
    except json.JSONDecodeError:
        return ""

    tipo = evento.get("type")
    if tipo == "system" and evento.get("subtype") == "init":
        return "sesion iniciada"
    if tipo == "assistant":
        partes = []
        for bloque in (evento.get("message") or {}).get("content") or []:
            if bloque.get("type") == "text" and (bloque.get("text") or "").strip():
                partes.append(bloque["text"].strip())
            elif bloque.get("type") == "tool_use":
                partes.append(f"-> {bloque.get('name')}")
        return "\n".join(partes)
    if tipo == "result":
        estado = "con error" if evento.get("is_error") else "bien"
        coste = evento.get("total_cost_usd")
        cola = f", coste {coste:.3f}" if isinstance(coste, (int, float)) else ""
        return f"TERMINADO {estado}: {evento.get('subtype')}{cola}"
    return ""


def _actividad(evento: dict[str, Any]) -> list[dict[str, Any]]:
    """Traduce un evento de `stream-json` a quien empieza y quien acaba.

    El registro de lineas dice *que* se hizo, pero no *quien* lo hizo: un tramo de
    la novela son cientos de lineas donde todo lo que se ve es `-> Agent` y
    `-> Bash`, sin decir que subagente se despacho ni sobre que. Aqui se saca lo
    unico que contesta a "quien esta currando ahora": el despacho de cada etapa,
    con su tarea, y el momento en que vuelve.

    El emparejamiento va por el identificador de la llamada, que es el que trae el
    resultado cuando el subagente termina. Sin el no habria forma de saber cual de
    los despachos abiertos se acaba de cerrar.
    """
    tipo = evento.get("type")
    sucesos: list[dict[str, Any]] = []

    if tipo == "assistant":
        for bloque in (evento.get("message") or {}).get("content") or []:
            if bloque.get("type") != "tool_use":
                continue
            nombre = bloque.get("name")
            entrada = bloque.get("input") or {}
            if nombre in ("Task", "Agent"):
                sucesos.append({
                    "suceso": "empieza", "id": bloque.get("id"),
                    "quien": entrada.get("subagent_type") or "subagente",
                    "que": entrada.get("description") or "",
                })
            elif nombre == "Bash":
                # Solo las llamadas al nucleo: son las que mueven estado, y son las
                # que explican que hace el conductor cuando lleva un rato sin
                # despachar a nadie. El resto de ordenes es ruido.
                orden = entrada.get("command") or ""
                if "storymaker" in orden:
                    sucesos.append({
                        "suceso": "nucleo", "quien": "conductor",
                        "que": _comando_nucleo(orden),
                    })

    elif tipo == "user":
        for bloque in (evento.get("message") or {}).get("content") or []:
            if bloque.get("type") == "tool_result" and bloque.get("tool_use_id"):
                sucesos.append({
                    "suceso": "acaba", "id": bloque.get("tool_use_id"),
                    "error": bool(bloque.get("is_error")),
                })

    return sucesos


def _comando_nucleo(orden: str) -> str:
    """El grupo y la accion de una llamada al nucleo, sin el resto de la orden.

    Las opciones se descartan a proposito: pueden traer el texto de una escena
    entera, y lo que interesa aqui es `escena cerrar`, no sus mil palabras.
    """
    trozos = re.split(r"\s+", orden.strip())
    try:
        i = next(i for i, x in enumerate(trozos) if "storymaker" in x)
    except StopIteration:
        return "storymaker"
    limpio = [x for x in trozos[i + 1:] if not x.startswith("-")]
    # `--proyecto <prj>` deja el identificador suelto detras: fuera tambien.
    limpio = [x for x in limpio if not x.startswith("prj_")]
    return " ".join(limpio[:2]) or "storymaker"


def plan_vigente(proyecto: str) -> dict[str, Any] | None:
    planes = sorted((PROYECTOS / proyecto / "canon" / "plan").glob("can_*.json"))
    if not planes:
        return None
    return json.loads(planes[-1].read_text(encoding="utf-8"))


def estado_proyecto(proyecto: str) -> dict[str, Any] | None:
    ficha = PROYECTOS / proyecto / "proyecto.json"
    if not ficha.is_file():
        return None
    return json.loads(ficha.read_text(encoding="utf-8"))


CONTRATO_COMUN = """Trabajas sobre el Proyecto {prj} del arnes StoryMaker, en el repositorio {raiz}.

El estado autoritativo lo escribe unicamente el nucleo `storymaker`, invocado como
herramienta. Desde la raiz del repositorio, con PYTHONPATH=src y
STORYMAKER_RAIZ=proyectos, se invoca como `python -m storymaker --proyecto {prj} ...`.
La unica ruta escribible bajo proyectos/ es proyectos/{prj}/tmp/.

Antes de despachar cualquier etapa, admite su unidad con `unidad admitir`,
construyendo el manifiesto que esa etapa declara. Si la admision deniega, no
despaches: dilo y para.

Este Proyecto esta en modo `revision_del_autor`: el Contexto historico y el Canon
los revisa el Autor en persona, y no hay etapa de validacion que lo haga por el.
"""


def tramo_inicial(proyecto: str) -> int:
    """Por que tramo empezar, leyendo el estado en disco.

    Los procesos viven en memoria: si el servidor se reinicia, el proceso se
    pierde aunque el trabajo este hecho y persistido. Sin esto, arrancar de nuevo
    repetiria la investigacion entera sobre un Contexto ya cerrado, que es tirar
    el dinero dos veces.
    """
    estado = estado_proyecto(proyecto) or {}
    if estado.get("canon_estado") == "aprobado":
        return 3
    if estado.get("contexto_version_vigente"):
        return 2
    return 1


def _pasos(
    proyecto: str, coste: float, iteraciones: int,
    rechazos: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Tres tramos y dos paradas, que es todo lo que hay.

    Antes esto eran ocho sesiones encadenadas, una por etapa. Cada una arrancaba un
    Claude Code de cero, releia el Encargo y volvia a orientarse antes de hacer
    nada: la mayor parte del gasto se iba en reorientacion, y cada arranque era un
    sitio mas donde algo podia romperse.

    Ahora cada tramo es **una sola sesion que hace su trecho seguido**. Los cortes
    no son arbitrarios: estan exactamente donde el Autor decide, porque una sesion
    headless no se puede pausar y esas dos decisiones son suyas.

        tramo 1  arranca la Ejecucion e investiga   ->  PARA: aceptas el Contexto
        tramo 2  Restricciones, cierre y Canon      ->  PARA: apruebas el Canon
        tramo 3  produccion, pasada global, entrega
    """
    comun = CONTRATO_COMUN.format(prj=proyecto, raiz=RAIZ)
    # El diccionario es mutable a proposito: los tramos lo leen en el momento de
    # correr, no cuando se definen, asi que un rechazo posterior llega al prompt
    # sin tener que reconstruir la lista de pasos.
    rechazos = rechazos if rechazos is not None else {}

    def reproche(clave: str) -> str:
        """Lo que el Autor objeto la vez anterior, si rechazo este tramo."""
        motivo = (rechazos.get(clave) or "").strip()
        if not motivo:
            return ""
        return (
            "\n\nATENCION: el Autor rechazo el resultado anterior de este mismo tramo y "
            "pidio rehacerlo. Su motivo, literal:\n\n"
            f"    {motivo}\n\n"
            "Atiendelo antes que nada. No repitas lo mismo esperando otro veredicto: si "
            "no ves como resolverlo, dilo y para."
        )

    def tramo_uno(anotar=None, **extra) -> dict[str, Any]:
        # Si ya hay Ejecucion activa se reaprovecha: arrancar otra perderia el
        # consumo gastado y volveria a pagar trabajo hecho.
        if (estado_proyecto(proyecto) or {}).get("ejecucion_activa"):
            if anotar:
                anotar("[Ya hay una Ejecucion activa: se reaprovecha]")
            arranque = {"ok": True}
        else:
            arranque = nucleo(proyecto, [
                "ejecucion", "iniciar", "--coste", str(coste),
                "--iteraciones", str(iteraciones), "--modo-ejecucion", "revision_del_autor",
            ])
        if not arranque.get("ok"):
            return arranque
        return etapa(comun + f"""
Produce el Contexto historico del Proyecto.

Despacha `sm-investigacion`. Registra las Fuentes con `contexto fuente`, las
afirmaciones atomicas con `contexto afirmar`, y deriva las Restricciones de epoca
con `contexto restriccion` cargando antes la skill `derivar-restricciones`.

Busca con `WebSearch` y `WebFetch`, que son las unicas vias de entrada del arnes.
Declara la cobertura como reducida, que es lo que es, y declara las lagunas que
encuentres: no las rellenes con verosimilitud.

Ya no hay verificacion de fidelidad ni pasada de refutacion: se retiraron del
arnes. Una Restriccion se deriva directamente de su afirmacion.

NO cierres el Contexto. Lo siguiente que pasa es que el Autor lo lee y decide."""
                     + reproche("tramo_contexto"), anotar, **extra)

    def tramo_dos(anotar=None, **extra) -> dict[str, Any]:
        return etapa(comun + """
Cierra el Contexto historico y construye el Canon, en ese orden y de una sentada.

1. Cierra el Contexto con `contexto cerrar`, salvo que ya este cerrado, en cuyo
   caso sigue sin mas. Si falta algo, el nucleo dira que: las cinco secciones
   obligatorias necesitan afirmacion vigente o laguna declarada con su impacto.
   Si no hay ninguna Restriccion de epoca derivada, derivalas antes con
   `contexto restriccion` cargando la skill `derivar-restricciones`: sin ellas el
   validador no tiene con que cazar un anacronismo.
2. Despacha `sm-diseno` para construir el Canon, cargando antes la skill
   `plantar-y-resolver`. Mira la extension objetivo y el numero de capitulos del
   Encargo y ajusta el numero de escenas a lo que de verdad cabe: la suma de los
   presupuestos de palabras debe dar la extension objetivo, y todo hilo que abras
   tiene que cerrar.
3. Si el plan se apoya en una laguna, instancia una Licencia de alcance con
   `canon licencia`, y hazlo DESPUES de `canon proponer`: una version nueva del
   plan no arrastra las Licencias de la anterior. Comprueba en el fichero que
   quedan con su desviacion, su justificacion y sus limites.
4. Escribe al final una **critica breve del Canon**, de cinco lineas como mucho:
   que es lo mas fragil del plan y que habria que mirar antes de aprobarlo. No es
   una validacion ni emite hallazgos: es lo que el Autor leera antes de decidir.

Propon el Canon como borrador y no lo apruebes."""
                     + reproche("tramo_canon"), anotar, **extra)

    def tramo_tres(anotar=None, **extra) -> dict[str, Any]:
        plan = plan_vigente(proyecto) or {}
        capitulos = [c["id"] for c in plan.get("capitulos", [])]
        return etapa(comun + f"""
Produce la novela entera y entregala. Los capitulos son {capitulos}.

Para cada capitulo, y dentro de el para cada escena en orden:

1. Despacha `sm-redactor` con su manifiesto -- ficha de la escena, Guia de estilo
   efectiva (`encargo estilo`), hechos de los sujetos presentes (`canon hechos`),
   escenas anteriores del capitulo y sinopsis de los capitulos ya cerrados -- y
   persiste el texto con `escena escribir`. Carga antes la skill `voz-y-estilo`.
   Respeta el presupuesto de palabras de la ficha y no metas ningun personaje que
   no este en el reparto del Canon.
2. Despacha `sm-refinador` y persiste con `escena refinar`, respetando los pasajes
   protegidos. Una pasada basta salvo que quede algo evidente.
3. Cierra la escena con `escena cerrar --modo-cierre convergencia`.

Cerradas todas las escenas de un capitulo: `capitulo preparar`, despacha
`sm-validador` sobre el capitulo completo y emite el veredicto con
`capitulo validar --hallazgos @<lote en tmp>`. Si devuelve bloqueantes, corrige las
escenas senaladas y vuelve a validar. **Cuando la nueva validacion los da por
buenos, cierra cada hallazgo con `hallazgo transicionar --a resuelto`**: un
hallazgo que sigue abierto despues de haberse arreglado el texto hace creer al
Autor que queda trabajo pendiente, y le pide una decision que ya no existe. Luego redacta la sinopsis -- un acta de lo
ocurrido, quien estaba, que cambio de estado y que quedo pendiente, sin prosa ni
citas -- y cierra con `capitulo cerrar --sinopsis @<fichero en tmp>`.

Con todos los capitulos cerrados: despacha `sm-global` sobre la novela completa,
emite `novela pasada-global`, cierra con `novela cerrar` y genera la entrega con
`entrega generar`.

Si algo se atasca, informa de que y para. No inventes una salida.""",
                     anotar, **extra)

    todos = [
        {"clave": "tramo_contexto", "titulo": "Contexto historico", "tipo": "etapa",
         "detalle": (
             f"Arranca la Ejecucion con {coste} de coste y {iteraciones} iteraciones, "
             "investiga y deriva las Restricciones de epoca"
         ),
         "correr": tramo_uno},
        {"clave": "espera_contexto", "tipo": "espera", **PARADAS["espera_contexto"]},
        {"clave": "tramo_canon", "titulo": "Cierre del Contexto y Canon", "tipo": "etapa",
         "detalle": "Cierra el Contexto, construye el Canon y escribe su critica breve",
         "correr": tramo_dos},
        {"clave": "espera_canon", "tipo": "espera", **PARADAS["espera_canon"]},
        {"clave": "tramo_novela", "titulo": "Novela y entrega", "tipo": "etapa",
         "detalle": "Redacta y refina cada escena, valida cada capitulo, pasada global y entrega",
         "correr": tramo_tres},
    ]

    # Cada tramo son dos entradas (el trabajo y su parada) menos el ultimo.
    #
    # Los tramos anteriores no se recortan: se marcan como hechos en una tirada
    # previa. Recortandolos, al relanzar una Ejecucion a medias desaparecian de la
    # pantalla los tramos ya superados y parecia que se empezaba de cero, cuando lo
    # que estaba pasando era justo lo contrario.
    desde = {1: 0, 2: 2, 3: 4}[tramo_inicial(proyecto)]
    for paso in todos[:desde]:
        paso["ya_estaba"] = True
    return todos


def arrancar(proyecto: str, *, coste: float, iteraciones: int) -> dict[str, Any]:
    """Lanza la Ejecucion en segundo plano. Se detendra dos veces a esperarte."""
    estado = estado_proyecto(proyecto)
    if estado is None:
        return {"ok": False, "error": {"codigo": "GUI-004", "mensaje": "No existe el Proyecto"}}
    if estado.get("modo") != "revision_del_autor":
        return {"ok": False, "error": {
            "codigo": "GUI-014",
            "mensaje": (
                "Esta conduccion solo corre en modo 'revision_del_autor', que es el que "
                "deja el Contexto historico y el Canon en manos del Autor. Este Proyecto "
                f"esta en '{estado.get('modo')}'."
            ),
        }}
    if estado.get("estado") in ("finalizado", "finalizado_con_reservas"):
        return {"ok": False, "error": {
            "codigo": "GUI-026",
            "mensaje": (
                "La Novela ya esta cerrada y entregada. No hay tramo que correr: "
                "cada paso lo rechazaria el nucleo en su primera puerta, despues de "
                "haber pagado la sesion. Si quieres otra version, empieza un Proyecto."
            ),
        }}
    if estado.get("encargo_version_vigente") is None:
        return {"ok": False, "error": {
            "codigo": "GUI-015",
            "mensaje": "El Encargo no esta cerrado. Componlo y confirmalo antes de arrancar.",
        }}
    # RF-105: la observabilidad se declara, no se impone. Sin claves la Ejecucion
    # corre igual y el proceso lo dice; bloquear aqui convertia una falta de
    # telemetria en una Ejecucion que no arranca, que es peor problema que el que
    # resolvia.

    id_proceso = f"prc_{uuid.uuid4().hex[:12]}"
    senal = threading.Event()
    traza = langfuse.Traza(id_proceso, f"Ejecucion · {estado.get('titulo_provisional', proyecto)}", {
        "proyecto": proyecto,
        "modo": estado.get("modo"),
        "encargo": estado.get("encargo_version_vigente"),
        "coste_presupuestado": coste,
        "iteraciones_presupuestadas": iteraciones,
    })
    with CERROJO:
        SENALES[id_proceso] = senal
        PROCESOS[id_proceso] = {
            "id": id_proceso, "proyecto": proyecto, "estado": "en_curso",
            "esperando": None, "iniciado_en": ahora(), "parar": False, "pasos": [],
            "langfuse": langfuse.estado(),
        }

    def registrar(pasos: list[dict[str, Any]]) -> None:
        with CERROJO:
            PROCESOS[id_proceso]["pasos"] += [
                {"clave": p["clave"], "titulo": p["titulo"], "tipo": p["tipo"],
                 "detalle": p["detalle"], "pestana": p.get("pestana"),
                 "estado": "pendiente", "sobre": None}
                for p in pasos
            ]

    def marcar(clave: str, **campos: Any) -> None:
        with CERROJO:
            for paso in PROCESOS[id_proceso]["pasos"]:
                if paso["clave"] == clave:
                    paso.update(campos)

    def parado() -> bool:
        with CERROJO:
            return PROCESOS[id_proceso]["parar"]

    def correr_lote(pasos: list[dict[str, Any]]) -> bool:
        # Indice en lugar de `for`: un rechazo retrocede una posicion, y eso con un
        # bucle de recorrido no se puede.
        i = 0
        while i < len(pasos):
            paso = pasos[i]
            if paso.get("ya_estaba"):
                marcar(paso["clave"], estado="hecho",
                       detalle=paso["detalle"] + " — hecho en una tirada anterior")
                i += 1
                continue
            if parado():
                marcar(paso["clave"], estado="cancelado")
                return False

            if paso["tipo"] == "espera":
                traza.paso_inicio(paso["clave"], paso["titulo"], paso["detalle"], "espera")
                marcar(paso["clave"], estado="esperando", empezado_en=ahora())
                with CERROJO:
                    PROCESOS[id_proceso]["esperando"] = paso["clave"]
                    PROCESOS[id_proceso]["estado"] = "esperando_al_autor"
                    PROCESOS[id_proceso]["decision"] = None
                senal.clear()
                senal.wait()
                with CERROJO:
                    proceso = PROCESOS[id_proceso]
                    proceso["esperando"] = None
                    proceso["estado"] = "en_curso"
                    decision = proceso.get("decision") or "aceptar"
                    motivo = proceso.get("motivo_decision") or ""
                if parado():
                    marcar(paso["clave"], estado="cancelado")
                    return False

                if decision == "rehacer" and i > 0:
                    anterior = pasos[i - 1]
                    rechazos[anterior["clave"]] = motivo
                    traza.paso_fin(paso["clave"], f"El Autor rechazo: {motivo}", None)
                    marcar(paso["clave"], estado="pendiente", sobre=None, salida_viva=None)
                    marcar(anterior["clave"], estado="pendiente", sobre=None,
                           salida_viva=None, rechazado=motivo)
                    i -= 1
                    continue

                traza.paso_fin(paso["clave"], "El Autor acepto y el proceso continua", None)
                marcar(paso["clave"], estado="hecho", terminado_en=ahora())
                i += 1
                continue

            traza.paso_inicio(paso["clave"], paso["titulo"], paso["detalle"], paso["tipo"])
            marcar(paso["clave"], estado="en_curso", empezado_en=ahora())

            def anotar(linea: str, clave: str = paso["clave"]) -> None:
                with CERROJO:
                    for p_ in PROCESOS[id_proceso]["pasos"]:
                        if p_["clave"] == clave:
                            vivo = p_.get("salida_viva") or []
                            vivo.append(linea)
                            p_["salida_viva"] = vivo[-400:]

            def apuntar(suceso: dict[str, Any], clave: str = paso["clave"]) -> None:
                """Lleva la cuenta de quien esta despachado y quien ya volvio."""
                with CERROJO:
                    for p_ in PROCESOS[id_proceso]["pasos"]:
                        if p_["clave"] != clave:
                            continue
                        agenda = p_.get("agenda") or []
                        if suceso["suceso"] == "acaba":
                            for fila in reversed(agenda):
                                if fila.get("id") == suceso["id"]:
                                    fila["estado"] = "error" if suceso["error"] else "hecho"
                                    fila["hasta"] = ahora()
                                    break
                        else:
                            agenda.append({
                                "id": suceso.get("id"),
                                "quien": suceso["quien"], "que": suceso["que"],
                                "estado": "hecho" if suceso["suceso"] == "nucleo" else "en_curso",
                                "desde": ahora(),
                            })
                        p_["agenda"] = agenda[-200:]

            sobre = paso["correr"](anotar, al_lanzar=al_lanzar, actividad=apuntar)
            datos = sobre.get("datos") or {}
            traza.consumo(paso["clave"], datos.get("consumo") or {})
            traza.paso_fin(
                paso["clave"],
                str(datos.get("salida") or json.dumps(datos, ensure_ascii=False, default=str)),
                None if sobre.get("ok") else sobre.get("error"),
            )
            if sobre.get("ok"):
                marcar(paso["clave"], estado="hecho", sobre=sobre, terminado_en=ahora())
            else:
                marcar(paso["clave"], estado="fallido", sobre=sobre, terminado_en=ahora())
                return False
            i += 1

        return True

    rechazos: dict[str, str] = {}
    # La sesion de la etapa en curso, para poder matarla si el Autor para.
    vivo: dict[str, Any] = {"sesion": None}

    def al_lanzar(sesion: Any) -> None:
        vivo["sesion"] = sesion

    with CERROJO:
        PROCESOS[id_proceso]["_vivo"] = vivo

    def hilo() -> None:
        pasos = _pasos(proyecto, coste, iteraciones, rechazos)
        registrar(pasos)
        bien = correr_lote(pasos)

        with CERROJO:
            proceso = PROCESOS[id_proceso]
            proceso["estado"] = (
                "cancelado" if proceso["parar"] else ("terminado" if bien else "fallido")
            )
            proceso["terminado_en"] = ahora()
            traza.cerrar(proceso["estado"], {
                "pasos": len(proceso["pasos"]),
                "hechos": sum(1 for x in proceso["pasos"] if x["estado"] == "hecho"),
            })


    threading.Thread(target=hilo, daemon=True).start()
    with CERROJO:
        return {"ok": True, "proceso": json.loads(json.dumps({k: v for k, v in PROCESOS[id_proceso].items() if k != "_vivo"}, default=str))}


def continuar(id_proceso: str, decision: str = "aceptar", motivo: str = "") -> dict[str, Any]:
    """El Autor ha decidido: se sigue, o se rehace el tramo que produjo esto.

    `aceptar` avanza. `rehacer` vuelve un paso atras, relanza el tramo con el
    motivo del Autor delante y se detiene otra vez en la misma parada. Es el bucle
    de vuelta que el arnes tenia y que la conduccion en tres tramos se habia
    dejado por el camino.

    No se comprueba aqui que el Autor haya firmado o aprobado: el paso siguiente
    invoca al nucleo, y el nucleo rechaza derivar Restricciones sin veredicto o
    redactar sobre un Canon no aprobado.
    """
    if decision not in ("aceptar", "rehacer"):
        return {"ok": False, "error": {
            "codigo": "GUI-021", "mensaje": f"Decision desconocida: {decision!r}",
        }}
    with CERROJO:
        proceso = PROCESOS.get(id_proceso)
        if proceso is None:
            return {"ok": False, "error": {"codigo": "GUI-017", "mensaje": "Proceso desconocido"}}
        if proceso["esperando"] is None:
            return {"ok": False, "error": {
                "codigo": "GUI-018",
                "mensaje": "Este proceso no esta esperando ninguna decision",
            }}
        if decision == "rehacer" and not motivo.strip():
            return {"ok": False, "error": {
                "codigo": "GUI-022",
                "mensaje": (
                    "Rehacer exige un motivo. Un rechazo que no dice que cambiar obliga "
                    "a adivinar, y lo mas probable es que salga lo mismo."
                ),
            }}
        parada = proceso["esperando"]
        proceso["decision"] = decision
        proceso["motivo_decision"] = motivo
    SENALES[id_proceso].set()
    return {"ok": True, "continuado": parada, "decision": decision}


def consultar(id_proceso: str) -> dict[str, Any]:
    with CERROJO:
        proceso = PROCESOS.get(id_proceso)
        if proceso is None:
            return {"ok": False, "error": {"codigo": "GUI-017", "mensaje": "Proceso desconocido"}}
        return {"ok": True, "proceso": json.loads(json.dumps({k: v for k, v in proceso.items() if k != "_vivo"}, default=str))}


def listar(proyecto: str | None = None) -> dict[str, Any]:
    with CERROJO:
        procesos = [
            json.loads(json.dumps({k: v for k, v in p.items() if k != "_vivo"}, default=str))
            for p in PROCESOS.values()
            if proyecto is None or p["proyecto"] == proyecto
        ]
    return {"ok": True, "procesos": procesos}


def parar(id_proceso: str) -> dict[str, Any]:
    """Corta la Ejecucion: mata la etapa en curso y no arranca la siguiente.

    Antes solo se pedia la parada y se dejaba terminar el paso, para no dejar
    ninguna unidad a medio cerrar. Eso valia mientras hubo un reloj que mataba
    solo una etapa pasada de tiempo; retirado el reloj, parar es la unica salida
    de una etapa colgada, y una salida que espera a que la etapa colgada termine
    no es una salida.

    Lo que el nucleo haya persistido se queda --- por eso una Ejecucion cortada se
    puede relanzar y continua por donde iba. Lo que la etapa tuviera a medias se
    pierde, que es exactamente lo que el Autor pide al parar.
    """
    with CERROJO:
        proceso = PROCESOS.get(id_proceso)
        if proceso is None:
            return {"ok": False, "error": {"codigo": "GUI-017", "mensaje": "Proceso desconocido"}}
        proceso["parar"] = True
        sesion = (proceso.get("_vivo") or {}).get("sesion")
    SENALES[id_proceso].set()

    matada = False
    if sesion is not None and sesion.poll() is None:
        try:
            sesion.kill()
            matada = True
        except Exception:  # noqa: BLE001
            matada = False
    return {
        "ok": True, "sesion_matada": matada,
        "nota": ("Se ha matado la etapa en curso" if matada else
                 "No corria ninguna etapa; no se arrancara la siguiente"),
    }
