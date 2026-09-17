#!/usr/bin/env python3
"""Servidor de la interfaz grafica de StoryMaker.

Biblioteca estandar y nada mas: no hay dependencias que instalar, y por tanto no
hay nada que se rompa al cambiar de maquina.

La regla que gobierna este fichero es la misma que gobierna el resto del arnes:
**el estado autoritativo lo escribe unicamente el nucleo.** Este servidor no
escribe un solo byte bajo `proyectos/`. Cuando la interfaz quiere cambiar algo,
invoca al nucleo como proceso y devuelve su sobre tal cual, error incluido. Si el
nucleo rechaza, la interfaz ensena el rechazo: no lo esquiva ni lo reintenta por
otra via.

De ahi se siguen tres decisiones que conviene no deshacer sin pensarlas:

1. **El nucleo se invoca por lista de argumentos, nunca por shell.** Lo que llega
   del navegador no se interpola en una cadena que alguien vaya a interpretar.
2. **Lista blanca de comandos.** Un grupo o una accion que no este en
   `COMANDOS_PERMITIDOS` no se ejecuta, aunque el nucleo la acepte. La interfaz es
   una superficie mas estrecha que el CLI, no un atajo para saltarselo.
3. **Solo escucha en localhost.** Esto expone el nucleo por HTTP; exponerlo a la
   red seria dar a cualquiera la capacidad de escribir en el Proyecto.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Se arranca de las dos maneras: `python gui/servidor.py` y `python -m gui.servidor`.
# La primera no pone la raiz del repositorio en el path, asi que se anade.
try:
    from gui import proceso as orquestador
except ModuleNotFoundError:  # pragma: no cover - depende de como se invoque
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from gui import proceso as orquestador

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = RAIZ / "src"
PROYECTOS = RAIZ / "proyectos"
PAGINA = Path(__file__).resolve().parent / "index.html"

# Lista blanca. La clave es el grupo del nucleo; el valor, las acciones que la
# interfaz puede pedir. Lo que no esta aqui no se ejecuta.
#
# `unidad admitir` y `escena escribir` quedan deliberadamente fuera: producen
# prosa o consumen presupuesto, y son trabajo de una etapa y no de un boton.
#
# La captura conversacional del Encargo (`encargo sesion` y `encargo responder`)
# tampoco esta: el interrogatorio pregunta, y preguntar necesita una terminal.
# Lo que si expone la interfaz es el camino de fichero -- componer el Encargo,
# crear el Proyecto e ingerirlo -- porque ahi no hay conversacion que mantener.
COMANDOS_PERMITIDOS: dict[str, set[str]] = {
    "proyecto": {"crear"},
    "encargo": {"ingerir", "presentar", "confirmar", "estilo"},
    # `cerrar` e `indicadores` salieron de la interfaz: el tramo 2 cierra el
    # Contexto por su cuenta, y los indicadores no le decian nada al Autor.
    "contexto": {"firmar", "descartar"},
    # Solo aprobar: instanciar Licencias y anexar hechos es trabajo de una
    # etapa, no de un boton, y la aprobacion ocurre en la parada.
    "canon": {"aprobar"},
    "escena": {"cerrar", "proteger"},
    "capitulo": {"preparar", "validar", "cerrar"},
    "novela": {"hilos"},
    "hallazgo": {"transicionar"},
    "ejecucion": {"estado", "reanudar"},
    "informe": {"calibracion"},
    "traza": {"pasaje", "afirmacion"},
    "indices": {"reconstruir"},
    "errores": {"listar"},
}

# Tareas de etapa en curso. Vive en memoria: si el servidor cae, lo que importa
# sigue en los ficheros del Proyecto, que es donde tiene que estar.
CERROJO = threading.Lock()


def ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def entorno() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(FUENTE)
    env["STORYMAKER_RAIZ"] = "proyectos"
    return env


def invocar_nucleo(proyecto: str | None, argumentos: list[str]) -> dict[str, Any]:
    """Ejecuta el nucleo y devuelve su sobre, sea `ok` o sea error.

    El sobre del nucleo es el contrato: no se reinterpreta aqui. Si el nucleo
    dice que no, la interfaz ensena por que dice que no.
    """
    orden = [sys.executable, "-m", "storymaker"]
    if proyecto:
        orden += ["--proyecto", proyecto]
    orden += argumentos

    try:
        completado = subprocess.run(
            orden, cwd=RAIZ, env=entorno(), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": {
            "codigo": "GUI-002",
            "mensaje": "El nucleo no respondio en 120 segundos",
        }}

    salida = (completado.stdout or "").strip()
    try:
        return json.loads(salida)
    except json.JSONDecodeError:
        return {"ok": False, "error": {
            "codigo": "GUI-003",
            "mensaje": "El nucleo no devolvio un sobre JSON",
            "salida": salida[:2000],
            "stderr": (completado.stderr or "")[:2000],
        }}


def listar_proyectos() -> list[dict[str, Any]]:
    if not PROYECTOS.is_dir():
        return []
    proyectos = []
    for carpeta in sorted(PROYECTOS.iterdir()):
        ficha = carpeta / "proyecto.json"
        if not ficha.is_file():
            continue
        try:
            proyectos.append(json.loads(ficha.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return proyectos


def leer_json(ruta: Path) -> Any:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def leer_jsonl(ruta: Path) -> list[dict[str, Any]]:
    if not ruta.is_file():
        return []
    registros = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            registros.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return registros


def ultimo_por_id(registros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Los ficheros de solo anexion guardan la historia; aqui interesa el ahora.

    Se anade `veces`, el numero de lineas que el registro trae para ese
    identificador. En un hallazgo eso es informacion, no ruido: la identidad
    excluye el enunciado justo para que un defecto que reaparece traiga el mismo
    id (RF-075), de modo que un `veces` alto dice que algo se resolvio y volvio,
    que es lo que dispara la terminacion por estancamiento.
    """
    vigentes: dict[str, dict[str, Any]] = {}
    cuantas: dict[str, int] = {}
    for registro in registros:
        identificador = registro.get("id")
        if identificador:
            vigentes[identificador] = registro
            cuantas[identificador] = cuantas.get(identificador, 0) + 1
    salida = []
    for identificador, registro in vigentes.items():
        salida.append({**registro, "veces": cuantas[identificador]})
    return salida


def panel(id_proyecto: str) -> dict[str, Any]:
    """Todo lo que la interfaz necesita para pintar un Proyecto, de una vez.

    Se lee de los ficheros, que son la memoria larga. Los indices derivados no se
    tocan: sirven para consultar y nunca para decidir, y aqui hay decisiones.
    """
    base = PROYECTOS / id_proyecto
    if not (base / "proyecto.json").is_file():
        return {"ok": False, "error": {
            "codigo": "GUI-004", "mensaje": f"No existe el Proyecto {id_proyecto}",
        }}

    planes = sorted((base / "canon" / "plan").glob("can_*.json"))
    contextos = sorted((base / "contexto").glob("ctx_*.json"))
    encargos = sorted((base / "encargo").glob("enc_*.json"))

    capitulos = []
    carpeta_sinopsis = base / "novela" / "sinopsis"
    if carpeta_sinopsis.is_dir():
        for fichero in sorted(carpeta_sinopsis.iterdir()):
            capitulos.append({
                "capitulo": fichero.stem,
                "sinopsis": fichero.read_text(encoding="utf-8").strip(),
            })

    escenas = []
    carpeta_escenas = base / "novela" / "escenas"
    if carpeta_escenas.is_dir():
        for carpeta in sorted(carpeta_escenas.iterdir()):
            versiones = sorted(carpeta.glob("*.md"))
            if not versiones:
                continue
            ultima = versiones[-1]
            texto = ultima.read_text(encoding="utf-8").strip()
            escenas.append({
                "escena": carpeta.name,
                "version": ultima.stem,
                "versiones": len(versiones),
                "palabras": len(texto.split()),
                "texto": texto,
            })

    entrega = base / "entrega" / "novela.md"

    # El Encargo ingerido pero sin confirmar vive como borrador, no como version.
    # Sin esto la interfaz no sabe que hay algo esperando a PC-2, y el Autor se
    # queda sin sitio donde cerrarlo.
    borrador = leer_json(base / "tmp" / "encargo" / "borrador.json")

    return {
        "ok": True,
        "proyecto": leer_json(base / "proyecto.json"),
        "encargo": leer_json(encargos[-1]) if encargos else None,
        "borrador_encargo": borrador,
        "contexto": leer_json(contextos[-1]) if contextos else None,
        "canon": leer_json(planes[-1]) if planes else None,
        "versiones_canon": [p.stem for p in planes],
        "afirmaciones": ultimo_por_id(leer_jsonl(base / "contexto" / "afirmaciones.jsonl")),
        "fuentes": ultimo_por_id(leer_jsonl(base / "contexto" / "fuentes.jsonl")),
        "restricciones": ultimo_por_id(leer_jsonl(base / "contexto" / "restricciones.jsonl")),
        "refutaciones": leer_jsonl(base / "contexto" / "refutaciones.jsonl"),
        "hallazgos": ultimo_por_id(leer_jsonl(base / "hallazgos.jsonl")),
        "capitulos": capitulos,
        "escenas": escenas,
        "entrega": entrega.read_text(encoding="utf-8") if entrega.is_file() else None,
    }



def flujo_de_agentes(id_proyecto: str) -> dict[str, Any]:
    """Quien trabajo, sobre que y cuanto tardo, sacado del Run Ledger.

    La pestana de Proceso ya ensena esto en vivo, pero lo hace desde la memoria
    del servidor: se pierde al reiniciar, y no existe para las Ejecuciones de
    antes. El ledger, en cambio, esta en disco y sobrevive a todo, que es la
    diferencia entre una vista bonita y un registro del que uno se puede fiar.

    Se emparejan `unidad_iniciada` y `unidad_cerrada` por el identificador de
    unidad. No se usa `unidades.jsonl` a proposito: ahi el estado se queda en
    `en_curso` aunque el cierre haya ocurrido, porque nadie lo reescribe. El
    ledger es de solo anadir y por eso no tiene ese problema.
    """
    carpeta = PROYECTOS / id_proyecto / "ejecuciones"
    if not carpeta.is_dir():
        return {"ok": True, "ejecuciones": []}

    ejecuciones = []
    for sitio in sorted(carpeta.iterdir()):
        fichero = sitio / "ledger.jsonl"
        if not fichero.is_file():
            continue

        abiertas: dict[str, dict[str, Any]] = {}
        pasos: list[dict[str, Any]] = []
        for linea in fichero.read_text(encoding="utf-8", errors="replace").splitlines():
            if not linea.strip():
                continue
            try:
                evento = json.loads(linea)
            except json.JSONDecodeError:
                continue
            carga = evento.get("carga") or {}
            tipo = evento.get("tipo")

            if tipo == "unidad_iniciada":
                paso = {
                    "clase": "unidad",
                    "id": carga.get("id_unidad"),
                    "quien": carga.get("etapa"),
                    "sobre": carga.get("unidad"),
                    "intento": carga.get("intento"),
                    "desde": evento.get("momento"),
                    "estado": "en_curso",
                }
                abiertas[carga.get("id_unidad")] = paso
                pasos.append(paso)

            elif tipo == "unidad_cerrada":
                paso = abiertas.pop(carga.get("id_unidad"), None)
                if paso is not None:
                    paso["hasta"] = evento.get("momento")
                    paso["estado"] = "hecho"
                    paso["modo_cierre"] = carga.get("modo_cierre")
                    paso["iteraciones"] = carga.get("iteraciones_consumidas")
                    paso["version"] = carga.get("version_vigente")
                    paso["deuda"] = bool(carga.get("deuda"))

            elif tipo == "error_registrado":
                error = carga.get("error") or {}
                pasos.append({
                    "clase": "error",
                    "desde": evento.get("momento"),
                    "codigo": error.get("codigo"),
                    "mensaje": error.get("mensaje"),
                    "comando": (carga.get("contexto") or {}).get("comando"),
                })

            elif tipo == "punto_control_abierto":
                pasos.append({
                    "clase": "parada",
                    "desde": evento.get("momento"),
                    "sobre": carga.get("tipo") or "punto de control",
                })

        ejecuciones.append({
            "ejecucion": sitio.name,
            "pasos": pasos,
            "abiertas": len(abiertas),
        })

    return {"ok": True, "ejecuciones": ejecuciones}



class Manejador(BaseHTTPRequestHandler):
    server_version = "StoryMakerGUI/1.0"

    def log_message(self, formato: str, *args: Any) -> None:  # noqa: A002
        sys.stderr.write(f"  {self.address_string()} {formato % args}\n")

    def _responder(self, cuerpo: bytes, tipo: str, codigo: int = 200) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos: Any, codigo: int = 200) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self._responder(cuerpo, "application/json; charset=utf-8", codigo)

    def do_GET(self) -> None:  # noqa: N802
        ruta = self.path.split("?")[0].rstrip("/") or "/"

        if ruta == "/":
            if not PAGINA.is_file():
                self._json({"ok": False, "error": {
                    "codigo": "GUI-007", "mensaje": "Falta gui/index.html",
                }}, 500)
                return
            self._responder(PAGINA.read_bytes(), "text/html; charset=utf-8")
            return

        if ruta == "/logo":
            # El logo de verdad, si se ha dejado uno. La pagina lo pide primero y
            # cae a su version dibujada cuando esto responde 404, asi que basta
            # con soltar el fichero en gui/ para que aparezca el autentico.
            for nombre, tipo in (
                ("logo.svg", "image/svg+xml"), ("logo.png", "image/png"),
                ("logo.jpg", "image/jpeg"), ("logo.webp", "image/webp"),
            ):
                fichero = PAGINA.parent / nombre
                if fichero.is_file():
                    self._responder(fichero.read_bytes(), tipo)
                    return
            self._json({"ok": False, "error": {
                "codigo": "GUI-019",
                "mensaje": "No hay logo propio: deja gui/logo.svg o gui/logo.png",
            }}, 404)
            return

        if ruta.startswith("/api/fuente/"):
            # El documento conservado de una Fuente, entero. Es lectura pura: el
            # almacen por contenido guarda el texto tal como se leyo el dia de la
            # consulta, y eso es lo que sostiene la trazabilidad cuando el enlace
            # deja de responder.
            partes = ruta.split("/")
            if len(partes) != 5:
                self._json({"ok": False, "error": {
                    "codigo": "GUI-023", "mensaje": "Falta el Proyecto o la huella",
                }}, 400)
                return
            _, _, _, id_proyecto, huella = partes
            if not huella.isalnum() or len(huella) != 64:
                self._json({"ok": False, "error": {
                    "codigo": "GUI-024", "mensaje": "La huella no es un SHA-256",
                }}, 400)
                return
            fichero = PROYECTOS / id_proyecto / "blobs" / huella[:2] / huella
            if not fichero.is_file():
                self._json({"ok": False, "error": {
                    "codigo": "GUI-025", "mensaje": "No hay contenido conservado con esa huella",
                }}, 404)
                return
            self._json({"ok": True, "contenido": fichero.read_text(
                encoding="utf-8", errors="replace")})
            return

        if ruta.startswith("/api/flujo/"):
            # Quien trabajo y en que orden, desde el ledger. A diferencia del
            # panel en vivo, esto existe aunque no haya ningun proceso corriendo.
            self._json(flujo_de_agentes(ruta.split("/")[-1]))
            return

        if ruta == "/api/proyectos":
            self._json({"ok": True, "proyectos": listar_proyectos()})
            return

        if ruta.startswith("/api/panel/"):
            self._json(panel(ruta.rsplit("/", 1)[-1]))
            return

        if ruta.startswith("/api/proceso/"):
            self._json(orquestador.consultar(ruta.rsplit("/", 1)[-1]))
            return

        if ruta == "/api/procesos":
            self._json(orquestador.listar())
            return

        self._json({"ok": False, "error": {
            "codigo": "GUI-009", "mensaje": f"Ruta desconocida: {ruta}",
        }}, 404)

    def do_POST(self) -> None:  # noqa: N802
        ruta = self.path.split("?")[0].rstrip("/")
        longitud = int(self.headers.get("Content-Length") or 0)
        try:
            peticion = json.loads(self.rfile.read(longitud) or b"{}")
        except json.JSONDecodeError:
            self._json({"ok": False, "error": {
                "codigo": "GUI-010", "mensaje": "El cuerpo no es JSON",
            }}, 400)
            return

        if ruta == "/api/nucleo":
            grupo = peticion.get("grupo")
            accion = peticion.get("accion")
            permitidas = COMANDOS_PERMITIDOS.get(grupo or "")
            if permitidas is None or accion not in permitidas:
                self._json({"ok": False, "error": {
                    "codigo": "GUI-001",
                    "mensaje": (
                        f"La interfaz no expone `{grupo} {accion}`. No es un fallo del "
                        "nucleo: es que esta superficie es mas estrecha que la del CLI."
                    ),
                }}, 403)
                return

            opciones = peticion.get("opciones") or []
            if not all(isinstance(o, str) for o in opciones):
                self._json({"ok": False, "error": {
                    "codigo": "GUI-011", "mensaje": "Las opciones son cadenas",
                }}, 400)
                return

            sobre = invocar_nucleo(peticion.get("proyecto"), [grupo, accion, *opciones])
            self._json(sobre, 200 if sobre.get("ok") else 422)
            return

        if ruta == "/api/proceso":
            self._json(orquestador.arrancar(
                peticion.get("proyecto") or "",
                coste=float(peticion.get("coste") or 25),
                iteraciones=int(peticion.get("iteraciones") or 40),
            ))
            return

        if ruta == "/api/proceso-continuar":
            self._json(orquestador.continuar(
                peticion.get("proceso") or "",
                peticion.get("decision") or "aceptar",
                peticion.get("motivo") or "",
            ))
            return

        if ruta == "/api/proceso-parar":
            self._json(orquestador.parar(peticion.get("proceso") or ""))
            return

        self._json({"ok": False, "error": {
            "codigo": "GUI-009", "mensaje": f"Ruta desconocida: {ruta}",
        }}, 404)


def main() -> int:
    # Las credenciales de la observabilidad viven en `.env`, fuera del Proyecto.
    # Se cargan aqui, al arrancar, para que las hereden tanto el servidor como
    # las sesiones de etapa que lanza.
    cargadas = orquestador.langfuse.cargar_env()
    puerto = int(os.environ.get("STORYMAKER_GUI_PUERTO", "8765"))
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    print(f"StoryMaker GUI en http://127.0.0.1:{puerto}")
    print(f"  raiz del repositorio: {RAIZ}")
    print(f"  proyectos: {len(listar_proyectos())}")
    traza = orquestador.langfuse.estado()
    print(f"  observabilidad: {'activa' if traza['activo'] else 'sin configurar'}"
          f" ({cargadas} variables de .env)")
    print("  Ctrl-C para parar")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nParado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
