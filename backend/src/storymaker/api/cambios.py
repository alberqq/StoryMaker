"""spec: §5 · arq: §4, §16.4

`POST /novelas/{id}/cambios`: la petición de cambio del lector.

**No toca nada.** Abre la Fase 6, que se detiene en su gate, y ahí el Autor ve los
candidatos que la búsqueda semántica propuso y el recuento de capítulos afectados antes de
pagarlo. Por eso este endpoint no necesita protección aunque escriba en la base: lo único
que deja es una petición pendiente de aprobación, y una petición pendiente no cambia la
novela.

Que la resolución la haga el arnés y la confirme el Autor es lo que permite que el lector
escriba «el perro se llama Nala, no Toby» en lugar de tener que conocer los identificadores
internos.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from storymaker.api import novelas
from storymaker.commons.config import Settings
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos import arnes
from storymaker.commons.embeddings.modelo import FastEmbedVectorizador
from storymaker.commons.errores import NovelaOcupada
from storymaker.commons.graph import cerrojo
from storymaker.regeneration import cambio, nodos
from storymaker.regeneration.esquemas import PeticionDeCambio

router = APIRouter(prefix="/novelas", tags=["regeneracion"])


@router.post("/{nombre}/cambios")
async def pedir_cambio(nombre: str, peticion_http: Request) -> dict[str, Any]:
    """Recibe la petición, propone candidatos y deja el gate abierto.

    Rechaza si la novela está ocupada: una petición que llegara mientras corre una
    invocación escribiría sobre el mismo checkpoint, y eso es lo que el cerrojo existe para
    impedir.
    """
    settings: Settings = peticion_http.app.state.settings
    ruta = await novelas.exigir(nombre, settings)

    if cerrojo.esta_tomado(ruta):
        raise NovelaOcupada(
            f"Hay una invocacion en curso sobre {nombre}: la peticion no se acepta ahora."
        )

    cuerpo = await peticion_http.json()
    peticion = PeticionDeCambio(texto=str(cuerpo.get("texto", "")))

    vectorizador = FastEmbedVectorizador()
    async with abrir_novela(ruta) as db:
        candidatos = await cambio.buscar_candidatos(db, vectorizador, peticion.texto)
        fase_run_id = await arnes.abrir_fase_run(db, "regeneration")
        gate_id = await arnes.abrir_gate(db, fase_run_id)

        alcances = []
        for candidato in candidatos[:3]:
            alcance = await nodos.calcular_alcance(
                db, objeto=candidato.objeto, fila_id=candidato.fila_id
            )
            alcances.append(
                {
                    "objeto": candidato.objeto.value,
                    "fila_id": candidato.fila_id,
                    "descripcion": candidato.descripcion,
                    "distancia": candidato.distancia,
                    "capitulos_a_regenerar": list(alcance.a_regenerar),
                    "capitulos_a_revisar": list(alcance.a_invalidar),
                    "coste": alcance.como_texto(),
                }
            )
        await db.commit()

    return {
        "peticion": peticion.texto,
        "gate_abierto": gate_id,
        "candidatos": alcances,
        "nota": (
            "Nada se ha cambiado todavia. El Autor elige el candidato en el gate de "
            "Regeneration, y ahi ve lo que cuesta antes de pagarlo."
        ),
    }
