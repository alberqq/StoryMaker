"""spec: §5 · arq: §10, §16.4

`POST /webhook/telegram`: **el único endpoint que reanuda una ejecución**, y por eso el
único protegido.

Comprueba el `secret_token` que Telegram envía en la cabecera
`X-Telegram-Bot-Api-Secret-Token` y rechaza la petición que no lo traiga. La superficie
pública se protege con un secreto y no con usuarios porque es un ejercicio académico que
corre en local, y montar usuarios y sesiones costaría más que el riesgo que cubre (U-17).

Tres cosas ocurren aquí, en este orden y por este motivo: **se escribe la decisión**, **se
responde** y **se lanza la invocación como tarea de fondo**. El callback tiene que responder
en segundos y la invocación puede tardar minutos; si se hiciera en línea, Telegram
reintentaría la entrega creyendo que falló y el Autor acabaría aprobando tres veces lo
mismo.

Y es **idempotente**: un callback sobre un gate ya decidido responde `200` y se ignora.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from storymaker.api import novelas
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.obs.trazas import construir as construir_observador
from storymaker.gates.decisiones import desde_callback, registrar

router = APIRouter(prefix="/webhook", tags=["gates"])


def secreto_valido(cabecera: str | None, settings: Settings) -> bool:
    """Compara el secreto. Sin secreto configurado, **no se acepta nada**.

    Es deliberado: un despliegue sin `telegram_secret_token` no es un despliegue abierto, es
    un despliegue mal configurado, y aceptar cualquier cosa lo convertiría en una puerta sin
    cerradura que nadie ve.
    """
    esperado = settings.telegram_secret_token
    return bool(esperado) and cabecera == esperado


async def aplicar_decision(
    ruta: Any, dato_del_boton: str, settings: Settings
) -> tuple[bool, str]:
    """Escribe la decisión. Devuelve (hay que reanudar, motivo).

    No reanuda: solo deja escrito qué decidió el Autor. Reanudar es cosa de la tarea de
    fondo, y separarlo es lo que permite responder en seguida.
    """
    tomada = desde_callback(dato_del_boton)
    if tomada is None:
        return False, "callback malformado"

    async with abrir_novela(ruta) as db:
        async with db.execute(
            "SELECT estado FROM gate WHERE id = ?", (tomada.gate_id,)
        ) as cursor:
            gate = await cursor.fetchone()
        if gate is None:
            return False, "ese gate no existe"
        if str(gate["estado"]) == "decidido":
            # Telegram reintenta las entregas que no confirma: la segunda no debe hacer nada.
            return False, "ese gate ya estaba decidido"

        await registrar(db, construir_observador(settings), tomada)
        await db.commit()

    return True, tomada.decision.value


@router.post("/telegram")
async def telegram(peticion: Request, tareas: BackgroundTasks) -> dict[str, Any]:
    """El callback del botón inline."""
    settings: Settings = peticion.app.state.settings
    if not secreto_valido(
        peticion.headers.get("X-Telegram-Bot-Api-Secret-Token"), settings
    ):
        raise HTTPException(status_code=401, detail="secreto ausente o incorrecto")

    cuerpo = await peticion.json()
    callback = (cuerpo.get("callback_query") or {}).get("data", "")
    nombre = (cuerpo.get("callback_query") or {}).get("novela", "")

    ruta = await novelas.exigir(nombre, settings)
    hay_que_reanudar, motivo = await aplicar_decision(ruta, callback, settings)
    if not hay_que_reanudar:
        return {"ok": True, "ignorado": motivo}

    tareas.add_task(_reanudar_en_segundo_plano, ruta, motivo, settings)
    return {"ok": True, "decision": motivo, "reanudando": True}


async def _reanudar_en_segundo_plano(ruta: Any, decision: str, settings: Settings) -> None:
    """La invocación que desencadena la decisión. Puede tardar minutos.

    Si el servidor cae a mitad no se pierde nada que no se pierda con un fallo cualquiera:
    el último checkpoint está en disco y reanudar es el camino de siempre. Por eso esta es
    la única concesión a la asincronía que el backend se permite.
    """
    from storymaker.commons.graph.run import reanudar

    await reanudar(ruta, settings=settings, decision=decision)
