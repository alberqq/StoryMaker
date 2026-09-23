"""spec: §4.7 · arq: §10, §16.1

La notificación, **detrás de una interfaz**, y **solo para avisar**.

Telegram avisa de que un gate espera y trae el comando exacto para decidirlo, pero no lleva
botones: **la decisión se toma en el PC del Autor**, con `storymaker decidir`, donde el
informe se lee entero. Sin decisiones por Telegram no hace falta webhook ni URL pública, y
nada fuera de la máquina del Autor puede reanudar una ejecución.

La interfaz existe para que WhatsApp pueda ser un adaptador futuro sin tocar los gates, y
para que la suite corra sin red: el `NotifierNulo` recuerda lo que se le pidió en lugar de
enviarlo, que es lo que permite comprobar **qué** se notifica sin montar un bot.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Protocol

from storymaker.commons.config import Settings


@dataclass(frozen=True)
class Aviso:
    """Un mensaje que espera decisión, o uno que solo informa."""

    titulo: str
    cuerpo: str
    gate_id: int | None = None
    decisiones: tuple[str, ...] = ()
    novela: str = ""

    @property
    def bloquea(self) -> bool:
        return self.gate_id is not None


class Notifier(Protocol):
    async def enviar(self, aviso: Aviso) -> None: ...


@dataclass
class NotifierNulo:
    """No envía nada y lo recuerda todo. Es el que corre sin token y en la suite."""

    enviados: list[Aviso] = field(default_factory=list)

    async def enviar(self, aviso: Aviso) -> None:
        self.enviados.append(aviso)


def texto_de(aviso: Aviso) -> str:
    """El mensaje, en texto plano: Markdown hace que Telegram rechace un `_` suelto."""
    partes = [aviso.titulo, "", aviso.cuerpo]
    if aviso.bloquea and aviso.decisiones:
        novela = aviso.novela or "<novela>"
        partes += [
            "",
            "Decide en el PC:",
            *(f"  storymaker decidir {novela} {d}" for d in aviso.decisiones),
        ]
    return "\n".join(partes)


class NotifierTelegram:
    """La implementación real, contra la Bot API. **Solo envía**: no recibe nada."""

    def __init__(self, settings: Settings) -> None:
        self._token = settings.telegram_bot_token
        self._chat = settings.telegram_chat_id

    async def enviar(self, aviso: Aviso) -> None:
        """Envía el aviso. Si falla, lo dice en la salida y sigue.

        Se pierde el aviso, no la puerta: el gate bloquea igual, y un fallo de red en el
        móvil no puede tumbar una fase que ya ha hecho su trabajo.
        """
        if not self._token or not self._chat:
            return
        import httpx

        carga: dict[str, Any] = {"chat_id": self._chat, "text": texto_de(aviso)}
        try:
            async with httpx.AsyncClient(timeout=15) as cliente:
                respuesta = await cliente.post(
                    f"https://api.telegram.org/bot{self._token}/sendMessage", json=carga
                )
            if respuesta.status_code != 200:
                motivo = respuesta.json().get("description", respuesta.status_code)
                print(f"Aviso: Telegram rechazo la notificacion: {motivo}", file=sys.stderr)
        except httpx.HTTPError as fallo:
            print(f"Aviso: no se pudo notificar por Telegram: {fallo}", file=sys.stderr)


def construir(settings: Settings) -> Notifier:
    """Telegram si hay token; si no, el nulo.

    Sin token el sistema corre igual y los gates siguen bloqueando: lo que se pierde es el
    aviso, no la puerta. Un gate que dejara de bloquear por no poder notificar sería un
    temporizador con otro nombre.
    """
    if settings.telegram_bot_token and settings.telegram_chat_id:
        return NotifierTelegram(settings)
    return NotifierNulo()
