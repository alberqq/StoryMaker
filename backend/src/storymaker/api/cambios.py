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

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

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


class CuerpoDeCambio(BaseModel):
    """Lo que envía el lector: qué quiere cambiar y desde dónde lo pide.

    El fragmento es lo que hace resoluble la petición: «se llama Nala, no Toby» no dice qué
    perro, y el pasaje seleccionado sí. Por eso entra en la búsqueda semántica junto al texto.
    """

    texto: str = Field(min_length=1)
    fragmento: str = ""
    capitulo: int | None = None
    version: int | None = None


class CandidatoDeCambio(BaseModel):
    objeto: str
    fila_id: int
    descripcion: str
    distancia: float
    capitulos_a_regenerar: list[int]
    capitulos_a_revisar: list[int]
    coste: str


class AcuseDeCambio(BaseModel):
    peticion: str
    gate_abierto: int
    candidatos: list[CandidatoDeCambio]
    nota: str


@router.post("/{nombre}/cambios")
async def pedir_cambio(
    nombre: str, cuerpo: CuerpoDeCambio, peticion_http: Request
) -> AcuseDeCambio:
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

    peticion = PeticionDeCambio(texto=cuerpo.texto)
    consulta = f"{cuerpo.texto}\n{cuerpo.fragmento}".strip()

    vectorizador = FastEmbedVectorizador()
    async with abrir_novela(ruta) as db:
        candidatos = await cambio.buscar_candidatos(db, vectorizador, consulta)
        fase_run_id = await arnes.abrir_fase_run(db, "regeneration")
        gate_id = await arnes.abrir_gate(db, fase_run_id)

        alcances = []
        for candidato in candidatos[:3]:
            alcance = await nodos.calcular_alcance(
                db, objeto=candidato.objeto, fila_id=candidato.fila_id
            )
            alcances.append(
                CandidatoDeCambio(
                    objeto=candidato.objeto.value,
                    fila_id=candidato.fila_id,
                    descripcion=candidato.descripcion,
                    distancia=candidato.distancia,
                    capitulos_a_regenerar=list(alcance.a_regenerar),
                    capitulos_a_revisar=list(alcance.a_invalidar),
                    coste=alcance.como_texto(),
                )
            )
        # La petición y sus candidatos quedan escritos: la pantalla del gate los enseña sin
        # repetir la búsqueda, y el gate de Regeneration los precarga como comentario.
        await arnes.registrar_audit(
            db,
            actor="autor",
            accion="peticion:lector",
            objeto=f"gate:{gate_id}",
            despues={
                "texto": cuerpo.texto,
                "fragmento": cuerpo.fragmento or None,
                "capitulo": cuerpo.capitulo,
                "version": cuerpo.version,
                "candidatos": [c.model_dump() for c in alcances],
            },
        )
        await db.commit()

    return AcuseDeCambio(
        peticion=peticion.texto,
        gate_abierto=gate_id,
        candidatos=alcances,
        nota=(
            "Nada se ha cambiado todavia. El Autor elige el candidato en el gate de "
            "Regeneration, y ahi ve lo que cuesta antes de pagarlo."
        ),
    )
