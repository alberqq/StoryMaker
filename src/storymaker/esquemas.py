"""Validador de contratos y politica de campos desconocidos (seccion 6.1).

El nucleo no depende de ninguna libreria externa: el almacen es de ficheros y la
validacion de contratos es un subconjunto de JSON Schema implementado aqui. Lo
que hace falta es exactamente esto -- tipos, obligatorios, enumerados, rangos,
formatos y `additionalProperties` -- y una dependencia para eso seria peaje sin
contrapartida.

La politica de campos desconocidos es deliberadamente asimetrica:

| Superficie                      | Politica  | Motivo                                   |
|---------------------------------|-----------|------------------------------------------|
| Salida de un agente             | Estricta  | Un campo inventado delata un prompt que se desvia |
| Contrato entre etapas           | Estricta  | En una frontera interna la ambiguedad es el enemigo |
| Artefacto persistido al leerlo  | Tolerante | Es lo que hace viable la promocion de esquema |
| Configuracion del Autor         | Estricta  | El Autor no es tecnico: fallar claro vale mas que ignorar |
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from storymaker.errores import ErrorStoryMaker

SUPERFICIE_AGENTE = "salida_agente"
SUPERFICIE_CONTRATO = "contrato_entre_etapas"
SUPERFICIE_ARTEFACTO = "artefacto_persistido"
SUPERFICIE_CONFIGURACION = "configuracion_autor"

_ESTRICTAS = {SUPERFICIE_AGENTE, SUPERFICIE_CONTRATO, SUPERFICIE_CONFIGURACION}

_FORMATOS = {
    "fecha-hora": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"),
    "identificador": re.compile(r"^[a-z]{3}_[a-z0-9][a-z0-9_-]*$"),
    "sha256": re.compile(r"^[0-9a-f]{64}$"),
    "version-esquema": re.compile(r"^\d+\.\d+$"),
}


@dataclass
class ResultadoValidacion:
    valido: bool
    problemas: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valido


class Validador:
    """Subconjunto de JSON Schema suficiente para los contratos de la seccion 6.2."""

    def __init__(self, esquema: dict[str, Any], superficie: str = SUPERFICIE_CONTRATO):
        self.esquema = esquema
        self.superficie = superficie
        self.estricta = superficie in _ESTRICTAS

    def validar(self, dato: Any) -> ResultadoValidacion:
        problemas: list[str] = []
        self._validar(dato, self.esquema, "$", problemas)
        return ResultadoValidacion(not problemas, problemas)

    def exigir(self, dato: Any, codigo: str = "ERR-302") -> None:
        resultado = self.validar(dato)
        if not resultado:
            raise ErrorStoryMaker(
                codigo,
                "El dato no cumple el contrato: " + "; ".join(resultado.problemas[:8]),
                superficie=self.superficie,
                problemas=resultado.problemas,
            )

    # -- interno -----------------------------------------------------------

    def _validar(
        self,
        dato: Any,
        esquema: dict[str, Any],
        ruta: str,
        problemas: list[str],
        solo_restricciones: bool = False,
    ) -> None:
        """Valida `dato` contra `esquema`.

        `solo_restricciones` distingue un esquema que describe un objeto entero de
        un fragmento que solo anade una condicion. Los subesquemas de `if`, `then`,
        `anyOf`, `oneOf` y `allOf` son fragmentos: dicen "ademas, esto", no "el
        objeto es exactamente esto". Tratarlos como descripciones completas haria
        que un `{"required": ["x"]}` rechazara todos los demas campos del objeto.
        """
        if "not" in esquema and self._subvalido(dato, esquema["not"]):
            problemas.append(f"{ruta}: el valor esta prohibido en esta posicion")
            return

        if "const" in esquema and dato != esquema["const"]:
            problemas.append(f"{ruta}: se esperaba el valor constante {esquema['const']!r}")
            return

        if "enum" in esquema and dato not in esquema["enum"]:
            problemas.append(f"{ruta}: {dato!r} no esta entre {esquema['enum']}")
            return

        tipo = esquema.get("type")
        if tipo and not self._tipo_ok(dato, tipo):
            problemas.append(f"{ruta}: se esperaba tipo {tipo}, llego {type(dato).__name__}")
            return

        if isinstance(dato, dict):
            self._validar_objeto(dato, esquema, ruta, problemas, solo_restricciones)
        elif isinstance(dato, list):
            self._validar_lista(dato, esquema, ruta, problemas)
        elif isinstance(dato, str):
            self._validar_cadena(dato, esquema, ruta, problemas)
        elif isinstance(dato, (int, float)) and not isinstance(dato, bool):
            self._validar_numero(dato, esquema, ruta, problemas)

        for regla in esquema.get("allOf", []):
            self._validar(dato, regla, ruta, problemas, solo_restricciones=True)

        if "anyOf" in esquema:
            if not any(self._subvalido(dato, regla) for regla in esquema["anyOf"]):
                problemas.append(f"{ruta}: no cumple ninguna de las alternativas de anyOf")

        if "oneOf" in esquema:
            cumplidas = sum(1 for regla in esquema["oneOf"] if self._subvalido(dato, regla))
            if cumplidas != 1:
                problemas.append(f"{ruta}: cumple {cumplidas} alternativas de oneOf, debe cumplir exactamente una")

        # `si/entonces`: condicionales del contrato, como "si el veredicto es
        # matizada, alcance_matiz es obligatorio".
        condicion = esquema.get("if")
        if condicion is not None and self._subvalido(dato, condicion):
            if "then" in esquema:
                self._validar(dato, esquema["then"], ruta, problemas, solo_restricciones=True)
        elif condicion is not None and "else" in esquema:
            self._validar(dato, esquema["else"], ruta, problemas, solo_restricciones=True)

    def _subvalido(self, dato: Any, esquema: dict[str, Any]) -> bool:
        acumulador: list[str] = []
        self._validar(dato, esquema, "$", acumulador, solo_restricciones=True)
        return not acumulador

    @staticmethod
    def _tipo_ok(dato: Any, tipo: Any) -> bool:
        tipos = tipo if isinstance(tipo, list) else [tipo]
        for nombre in tipos:
            if nombre == "object" and isinstance(dato, dict):
                return True
            if nombre == "array" and isinstance(dato, list):
                return True
            if nombre == "string" and isinstance(dato, str):
                return True
            if nombre == "boolean" and isinstance(dato, bool):
                return True
            if nombre == "integer" and isinstance(dato, int) and not isinstance(dato, bool):
                return True
            if nombre == "number" and isinstance(dato, (int, float)) and not isinstance(dato, bool):
                return True
            if nombre == "null" and dato is None:
                return True
        return False

    def _validar_objeto(
        self,
        dato: dict,
        esquema: dict,
        ruta: str,
        problemas: list[str],
        solo_restricciones: bool = False,
    ) -> None:
        propiedades = esquema.get("properties", {})
        for obligatorio in esquema.get("required", []):
            if obligatorio not in dato:
                problemas.append(f"{ruta}.{obligatorio}: campo obligatorio ausente")

        # Un fragmento de condicion no inventaria las propiedades del objeto, asi
        # que no puede juzgar cuales sobran.
        declara_inventario = bool(propiedades or esquema.get("patternProperties"))
        juzga_desconocidos = not solo_restricciones and declara_inventario

        for clave, valor in dato.items():
            if clave in propiedades:
                self._validar(valor, propiedades[clave], f"{ruta}.{clave}", problemas)
                continue
            patron = self._patron_que_casa(clave, esquema)
            if patron is not None:
                self._validar(valor, patron, f"{ruta}.{clave}", problemas)
                continue
            if not juzga_desconocidos:
                continue
            extra = esquema.get("additionalProperties", not self.estricta)
            if extra is False:
                problemas.append(f"{ruta}.{clave}: campo desconocido, y el contrato lo prohibe")
            elif isinstance(extra, dict):
                self._validar(valor, extra, f"{ruta}.{clave}", problemas)
            elif extra is True:
                continue
            else:
                problemas.append(f"{ruta}.{clave}: campo desconocido, y esta superficie es estricta")

        dependencias = esquema.get("dependentRequired", {})
        for disparador, exigidos in dependencias.items():
            if disparador in dato:
                for exigido in exigidos:
                    if exigido not in dato:
                        problemas.append(
                            f"{ruta}.{exigido}: obligatorio cuando esta presente {disparador}"
                        )

        if "minProperties" in esquema and len(dato) < esquema["minProperties"]:
            problemas.append(f"{ruta}: al menos {esquema['minProperties']} propiedades")

    @staticmethod
    def _patron_que_casa(clave: str, esquema: dict) -> dict | None:
        for patron, subesquema in esquema.get("patternProperties", {}).items():
            if re.search(patron, clave):
                return subesquema
        return None

    def _validar_lista(self, dato: list, esquema: dict, ruta: str, problemas: list[str]) -> None:
        if "minItems" in esquema and len(dato) < esquema["minItems"]:
            problemas.append(f"{ruta}: se exigen al menos {esquema['minItems']} elementos, hay {len(dato)}")
        if "maxItems" in esquema and len(dato) > esquema["maxItems"]:
            problemas.append(f"{ruta}: se admiten como mucho {esquema['maxItems']} elementos, hay {len(dato)}")
        if esquema.get("uniqueItems"):
            serializados = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in dato]
            if len(set(serializados)) != len(serializados):
                problemas.append(f"{ruta}: hay elementos repetidos y la lista los exige unicos")
        subesquema = esquema.get("items")
        if isinstance(subesquema, dict):
            for indice, item in enumerate(dato):
                self._validar(item, subesquema, f"{ruta}[{indice}]", problemas)

    def _validar_cadena(self, dato: str, esquema: dict, ruta: str, problemas: list[str]) -> None:
        if "minLength" in esquema and len(dato) < esquema["minLength"]:
            problemas.append(f"{ruta}: longitud minima {esquema['minLength']}")
        if "maxLength" in esquema and len(dato) > esquema["maxLength"]:
            problemas.append(f"{ruta}: longitud maxima {esquema['maxLength']}")
        if "pattern" in esquema and not re.search(esquema["pattern"], dato):
            problemas.append(f"{ruta}: no casa con el patron {esquema['pattern']}")
        formato = esquema.get("format")
        if formato in _FORMATOS and not _FORMATOS[formato].match(dato):
            problemas.append(f"{ruta}: no tiene formato {formato}")

    def _validar_numero(self, dato: float, esquema: dict, ruta: str, problemas: list[str]) -> None:
        if "minimum" in esquema and dato < esquema["minimum"]:
            problemas.append(f"{ruta}: minimo {esquema['minimum']}")
        if "maximum" in esquema and dato > esquema["maximum"]:
            problemas.append(f"{ruta}: maximo {esquema['maximum']}")
        if "exclusiveMinimum" in esquema and dato <= esquema["exclusiveMinimum"]:
            problemas.append(f"{ruta}: debe ser mayor que {esquema['exclusiveMinimum']}")
        if "multipleOf" in esquema and esquema["multipleOf"] and dato % esquema["multipleOf"] != 0:
            problemas.append(f"{ruta}: debe ser multiplo de {esquema['multipleOf']}")


class RegistroContratos:
    """Carga los esquemas de `contracts/<nombre>/v<mayor>.schema.json`."""

    def __init__(self, raiz: Path | str):
        self.raiz = Path(raiz)
        self._cache: dict[str, dict[str, Any]] = {}

    def cargar(self, nombre: str, mayor: int = 1) -> dict[str, Any]:
        clave = f"{nombre}/v{mayor}"
        if clave not in self._cache:
            ruta = self.raiz / nombre / f"v{mayor}.schema.json"
            if not ruta.exists():
                raise ErrorStoryMaker(
                    "ERR-505",
                    f"No hay esquema registrado para el contrato {clave}",
                    contrato=clave,
                    ruta=str(ruta),
                )
            self._cache[clave] = json.loads(ruta.read_text(encoding="utf-8"))
        return self._cache[clave]

    def validador(self, nombre: str, mayor: int = 1, superficie: str = SUPERFICIE_CONTRATO) -> Validador:
        return Validador(self.cargar(nombre, mayor), superficie)

    def contratos_disponibles(self) -> list[str]:
        if not self.raiz.exists():
            return []
        return sorted(
            f"{carpeta.name}/{fichero.stem.split('.')[0]}"
            for carpeta in self.raiz.iterdir()
            if carpeta.is_dir()
            for fichero in carpeta.glob("v*.schema.json")
        )
