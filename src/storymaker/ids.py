"""Identificadores estables (Tecnica 2.0, seccion 4.2).

Formato `<prefijo>_<sufijo>`, en minusculas. Los prefijos son parte del contrato
y no cambian.

La pieza delicada es `id_hallazgo`. RF-075 cierra un bucle cuando reaparece un
hallazgo ya resuelto, y eso solo funciona si el mismo defecto reaparecido
conserva su identidad. Por eso el hash deja fuera el enunciado, que lo redacta un
modelo y cambia entre iteraciones, y los desplazamientos de caracter, que se
mueven en cuanto el redactor corrige el texto. Con cualquiera de los dos dentro,
el mecanismo fallaria justo en el momento para el que se diseno.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
import unicodedata

PREFIJOS = {
    "prj": "Proyecto",
    "eje": "Ejecucion",
    "enc": "Version de Encargo",
    "ctx": "Version de Contexto historico",
    "can": "Version de plan de Canon",
    "aff": "Afirmacion",
    "fnt": "Fuente",
    "rst": "Restriccion de epoca",
    "hec": "Hecho",
    "ref": "Veredicto de refutacion",
    "cnt": "Contenido conservado de una Fuente",
    "hil": "Hilo de trama",
    "per": "Personaje",
    "fac": "Faccion",
    "lug": "Lugar",
    "evh": "Evento historico",
    "evf": "Evento ficticio",
    "rev": "Revelacion",
    "fig": "Figura historica real",
    "cap": "Capitulo",
    "esc": "Escena",
    "esv": "Version de escena",
    "pas": "Pasaje",
    "hlz": "Hallazgo",
    "lic": "Licencia literaria",
    "deu": "Deuda de calidad",
    "pct": "Punto de control",
    "sol": "Solicitud de investigacion",
    "udt": "Unidad de trabajo",
    "llm": "Llamada a modelo",
}

_ALFABETO_ULID = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32


def ulid(momento_ms: int | None = None, aleatorio: bytes | None = None) -> str:
    """ULID en minusculas: ordenable por tiempo y sin coordinacion.

    Los parametros existen para que las pruebas puedan fijar el valor; en uso
    normal no se pasan.
    """
    ms = int(time.time() * 1000) if momento_ms is None else momento_ms
    azar = os.urandom(10) if aleatorio is None else aleatorio
    bits = ms.to_bytes(6, "big") + azar
    numero = int.from_bytes(bits, "big")
    salida = []
    for _ in range(26):
        salida.append(_ALFABETO_ULID[numero & 0x1F])
        numero >>= 5
    return "".join(reversed(salida)).lower()


def normalizar(texto: str) -> str:
    """Normalizacion canonica para todo lo que entra en un hash de identidad.

    Sin acentos, sin mayusculas, sin puntuacion y sin espacios repetidos. Dos
    enunciados que solo difieren en eso son el mismo enunciado.
    """
    sin_tildes = "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )
    minusculas = sin_tildes.lower()
    sin_puntuacion = re.sub(r"[^\w\s]", " ", minusculas, flags=re.UNICODE)
    return re.sub(r"\s+", " ", sin_puntuacion).strip()


def hash_corto(*partes: str, longitud: int = 12) -> str:
    material = chr(31).join(normalizar(parte) for parte in partes)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:longitud]


def sha256_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def sha256_bytes(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def slug(texto: str, longitud: int = 40) -> str:
    base = normalizar(texto).replace(" ", "-")
    return base[:longitud].strip("-") or "sin-nombre"


# --- Constructores por entidad -------------------------------------------


def id_proyecto() -> str:
    return f"prj_{ulid()}"


def id_ejecucion() -> str:
    return f"eje_{ulid()}"


def sufijo(identificador: str) -> str:
    """Devuelve la parte que sigue al prefijo. `prj_01h...` -> `01h...`."""
    return identificador.split("_", 1)[1] if "_" in identificador else identificador


def id_version(prefijo: str, id_proyecto_: str, numero: int) -> str:
    """Versiones de Encargo, Contexto y plan de Canon: `<pref>_<prj>_v<n>`."""
    if prefijo not in {"enc", "ctx", "can"}:
        raise ValueError(f"prefijo no versionable: {prefijo}")
    return f"{prefijo}_{sufijo(id_proyecto_)}_v{numero}"


def numero_de_version(identificador: str) -> int:
    marca = identificador.rsplit("_v", 1)
    if len(marca) != 2 or not marca[1].isdigit():
        raise ValueError(f"identificador sin numero de version: {identificador}")
    return int(marca[1])


def id_afirmacion(enunciado: str) -> str:
    return f"aff_{hash_corto(enunciado)}"


def id_fuente(localizador: str) -> str:
    return f"fnt_{hash_corto(localizador)}"


def id_restriccion(enunciado: str) -> str:
    return f"rst_{hash_corto(enunciado)}"


def id_hecho(sujeto: str, enunciado: str) -> str:
    return f"hec_{hash_corto(sujeto, enunciado)}"


def id_refutacion(id_afirmacion_: str) -> str:
    return f"ref_{sufijo(id_afirmacion_)}"


def id_contenido(sha256: str) -> str:
    return f"cnt_{sha256}"


def id_elemento_plan(prefijo: str, nombre: str) -> str:
    """Elementos del plan y fichas de figuras reales: `<pref>_<slug>`.

    Estables entre versiones del plan: es lo que permite decir que el hilo
    `hil_el-mapa-falso` de la version 3 es el mismo que el de la version 1.
    """
    if prefijo not in {"hil", "per", "fac", "lug", "evh", "evf", "rev", "fig"}:
        raise ValueError(f"prefijo de elemento de plan desconocido: {prefijo}")
    return f"{prefijo}_{slug(nombre)}"


def id_capitulo(orden: int) -> str:
    return f"cap_{orden:03d}"


def id_escena(orden_capitulo: int, orden_escena: int) -> str:
    return f"esc_{orden_capitulo:03d}_{orden_escena:03d}"


def id_version_escena(id_escena_: str, numero: int) -> str:
    return f"esv_{sufijo(id_escena_)}_v{numero}"


def id_pasaje(id_version_escena_: str, orden: int) -> str:
    return f"pas_{sufijo(id_version_escena_)}_{orden:04d}"


def id_hallazgo(unidad: str, categoria: str, elemento_senalado: str) -> str:
    """Identidad estable de un Hallazgo (RF-075).

    Deliberadamente excluye el enunciado y los desplazamientos de caracter. Lo
    que entra es la unidad afectada, la categoria del defecto y el elemento
    senalado normalizado: el nombre del personaje, el termino anacronico, el
    identificador del hilo. Eso sobrevive a que el redactor reescriba el parrafo.
    """
    return f"hlz_{hash_corto(unidad, categoria, elemento_senalado)}"


def id_unidad_trabajo(etapa: str, unidad: str, intento: int) -> str:
    return f"udt_{hash_corto(etapa, unidad, str(intento))}"


def clave_idempotencia(etapa: str, unidad: str, intento: int, hash_entradas: str) -> str:
    """Clave determinista de una unidad de trabajo (seccion 7.4).

    Antes de despachar, el nucleo consulta el ledger: si esta clave ya tiene un
    cierre registrado, no vuelve a gastar y devuelve el resultado anterior.
    """
    return hash_corto(etapa, unidad, str(intento), hash_entradas, longitud=24)


def id_secuencial(prefijo: str, numero: int) -> str:
    if prefijo not in {"lic", "deu", "pct", "sol", "llm"}:
        raise ValueError(f"prefijo no secuencial: {prefijo}")
    return f"{prefijo}_{numero:05d}"


def prefijo_de(identificador: str) -> str:
    return identificador.split("_", 1)[0]


def valido(identificador: str) -> bool:
    return prefijo_de(identificador) in PREFIJOS
