"""spec: §4.7 · arq: §10, §16.1

La notificación, **detrás de una interfaz**.

Telegram no es una preferencia estética: WhatsApp exige Meta Business, número verificado y
aprobación previa de plantillas de mensaje; Telegram es un token en el `.env`. Y sobre todo
soporta **botones inline**, así que el mensaje llega con *Aprobar · Rehacer · Abortar* y se
decide sin abrir nada.

La interfaz existe para que WhatsApp pueda ser un adaptador futuro sin tocar los gates, y
para que la suite corra sin red: el `NotifierNulo` recuerda lo que se le pidió en lugar de
enviarlo, que es lo que permite comprobar **qué** se notifica sin montar un bot.
"""

from __future__ import annotations

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


class NotifierTelegram:
    """La implementación real, contra la Bot API.

    El mensaje de un gate lleva **botones inline** con las decisiones disponibles; el
    informativo, ninguno. Esa diferencia es la que distingue «el capítulo 6 de 10 está
    aprobado» de «la escaleta espera tu visto bueno».
    """

    def __init__(self, settings: Settings) -> None:
        self._token = settings.telegram_bot_token
        self._chat = settings.telegram_chat_id

    def _teclado(self, aviso: Aviso) -> dict[str, Any] | None:
        if not aviso.decisiones or aviso.gate_id is None:
            return None
        return {
            "inline_keyboard": [
                [
                    {
                        "text": decision.capitalize(),
                        "callback_data": f"{aviso.gate_id}:{decision}",
                    }
                    for decision in aviso.decisiones
                ]
            ]
        }

    async def enviar(self, aviso: Aviso) -> None:
        if not self._token or not self._chat:
            return

        import httpx

        carga: dict[str, Any] = {
            "chat_id": self._chat,
            "text": f"*{aviso.titulo}*\n\n{aviso.cuerpo}",
            "parse_mode": "Markdown",
        }
        teclado = self._teclado(aviso)
        if teclado is not None:
            carga["reply_markup"] = teclado

        async with httpx.AsyncClient(timeout=15) as cliente:
            await cliente.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage", json=carga
            )


def construir(settings: Settings) -> Notifier:
    """Telegram si hay token; si no, el nulo.

    Sin token el sistema corre igual y los gates siguen bloqueando: lo que se pierde es el
    aviso, no la puerta. Un gate que dejara de bloquear por no poder notificar sería un
    temporizador con otro nombre.
    """
    if settings.telegram_bot_token and settings.telegram_chat_id:
        return NotifierTelegram(settings)
    return NotifierNulo()
