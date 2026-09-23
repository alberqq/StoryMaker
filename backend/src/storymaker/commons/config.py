"""spec: §2.2 · arq: §19

Configuración del arnés, en un solo sitio y por dos motivos distintos.

`Defaults` recoge los valores por defecto de §19 de la arquitectura como constantes
con nombre. No están aquí por comodidad: un `20` suelto en el código no dice si es el
tamaño del lote del verificador o los reintentos de otra cosa, y cuando la
arquitectura cambia un número hay que poder encontrar todos sus usos.

`Settings` es lo que se **inyecta**. Se lee del entorno y de un `.env` una sola vez al
arrancar, y a partir de ahí viaja como parámetro. Ningún otro módulo consulta el
entorno: así una prueba construye su propia configuración sin tocar el proceso.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Rol(StrEnum):
    """Los nueve roles de §5. Es el dominio de `modelo_por_rol` y de los techos de §12."""

    ENTREVISTADOR = "entrevistador"
    EXTRACTOR_INTAKE = "extractor_intake"
    INVESTIGADOR = "investigador"
    VERIFICADOR = "verificador"
    ARQUITECTO = "arquitecto"
    ESCRITOR = "escritor"
    EDITOR = "editor"
    EXTRACTOR_CAPITULO = "extractor_capitulo"
    JUEZ = "juez"


class Defaults:
    """Los valores por defecto de §19 de la arquitectura, y ningún otro.

    Cambiar uno de estos números es cambiar la arquitectura, no la configuración: lo
    que el Autor parametriza por novela vive en `Settings`, que los toma de aquí.
    """

    # Modelo
    MODELO_HAIKU: Final = "claude-haiku-4-5-20251001"

    # Dimensiones de la obra
    N_CAPITULOS: Final = 10
    PALABRAS_POR_CAPITULO: Final = 1200
    RANGO_PALABRAS: Final = (1000, 1500)
    RANGO_ESCENAS_POR_CAPITULO: Final = (2, 4)

    # Investigación: lo que el arnés impone, no el prompt
    WEBSEARCH_INVESTIGACION_INICIAL: Final = 3
    WEBFETCH_INVESTIGACION_INICIAL: Final = 3
    DIMENSIONES_DEL_PERIODO: Final = 6
    TECHO_WEBFETCH_TOKENS: Final = 10_000
    LONGITUD_MAXIMA_CITA: Final = 300
    HECHOS_POR_LOTE_VERIFICADOR: Final = 20

    # Plotting y Writing
    HUECOS_POR_PLOTTING: Final = 5
    WEBSEARCH_POR_HUECO: Final = 1
    REINTENTOS_POR_CAPITULO: Final = 2
    INVOCACIONES_EXTRACTOR_POR_CAPITULO: Final = 3

    # Arco de personaje
    ESCENAS_PARA_EXIGIR_ARCO: Final = 3
    HITOS_MINIMOS_ARCO_CON_TRANSFORMACION: Final = 2
    HITOS_ARCO_PLANO: Final = 0
    AVISOS_QUE_VIAJAN_AL_SIGUIENTE: Final = 3

    # Contexto y recuperación
    TOKENS_CONCURRENTES_MAXIMOS: Final = 100_000
    TECHO_TOTAL_PAQUETE: Final = 12_000
    MODELO_EMBEDDINGS: Final = "paraphrase-multilingual-MiniLM-L12-v2"
    DIMENSION_EMBEDDINGS: Final = 384
    K_VECINOS: Final = 8

    # Diales de la frontera historia-ficción y rúbrica
    GRADO_LICENCIA: Final = "moderado"
    ARCAISMO: Final = "moderado"
    CONTENIDO_ADMISIBLE: Final = "sin violencia explícita"
    PUNTO_DE_VISTA: Final = "tercera persona con focalización en el homenajeado"
    CRITERIOS_RUBRICA: Final = 7


def _todos_en_haiku() -> dict[Rol, str]:
    return {rol: Defaults.MODELO_HAIKU for rol in Rol}


class Settings(BaseSettings):
    """Los siete grupos de claves de §2.2 de la spec.

    Ninguna es obligatoria. Los secretos nacen vacíos porque el arranque no los
    necesita: quien los exige es el módulo que va a usarlos, en el momento de usarlos,
    y así una prueba o un `storymaker estado` corren sin credenciales de Telegram.
    """

    model_config = SettingsConfigDict(
        env_prefix="STORYMAKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Rutas - el directorio es el registro de novelas (arq. §16.4)
    directorio_proyectos: Path = Path("proyectos")

    # Modelos
    modelo_por_rol: dict[Rol, str] = Field(default_factory=_todos_en_haiku)
    sdk_version: str | None = None

    # Gates
    gates_enabled: bool = True
    timeout_gate_horas: int = Field(default=24, ge=1)

    # Telegram
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    # Langfuse
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    otlp_enabled: bool = False

    # Límites - los valores de §19
    reintentos_por_capitulo: int = Field(default=Defaults.REINTENTOS_POR_CAPITULO, ge=0)
    huecos_por_plotting: int = Field(default=Defaults.HUECOS_POR_PLOTTING, ge=0)
    k_vecinos: int = Field(default=Defaults.K_VECINOS, ge=1)
    techo_webfetch_tokens: int = Field(default=Defaults.TECHO_WEBFETCH_TOKENS, ge=1)

    # Embeddings - viajan al manifiesto (arq. §16.2)
    modelo_embeddings: str = Defaults.MODELO_EMBEDDINGS
    dimension_embeddings: int = Field(default=Defaults.DIMENSION_EMBEDDINGS, ge=1)

    def en_modo_batch(self) -> Settings:
        """Los cinco gates apagados, para que los briefs de evaluación corran solos.

        Devuelve una copia en lugar de mutar: la configuración que se inyectó a otro
        módulo no puede cambiar bajo sus pies a mitad de una ejecución.
        """
        return self.model_copy(update={"gates_enabled": False})
