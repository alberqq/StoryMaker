"""El manifiesto de contexto (seccion 3.4) y la sinopsis acumulada (seccion 3.5).

La idea que sostiene todo esto: **el arnes recuerda en estructuras, no en prosa.**
Para saber si un personaje puede saber algo no se relee la novela: se consulta el
plan de revelaciones. Para saber de que color tiene los ojos no se relee: se
consulta el libro de hechos. La prosa se lee cuando hay que juzgar prosa, y nunca
para averiguar un dato.

De ahi se sigue la propiedad que hace viable una novela de cien mil palabras: la
unidad de contexto es la unidad de trabajo, asi que **el contexto no crece con la
novela**. Redactar la escena 3 y redactar la escena 180 cuestan lo mismo.

Cada etapa declara aqui que recibe, en que orden de prelacion y con que limite. El
manifiesto se registra en el ledger junto con la llamada, de modo que siempre se
puede reconstruir con que informacion se tomo una decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from storymaker.errores import ErrorStoryMaker
from storymaker.ids import sha256_texto

# Aproximacion de tokens por caracter para el castellano. Es una estimacion
# deliberadamente conservadora: el manifiesto se recorta antes de desbordar, no
# despues.
CARACTERES_POR_TOKEN = 3.6


@dataclass
class Bloque:
    """Una pieza del manifiesto, con su rango de prelacion."""

    nombre: str
    contenido: str
    prelacion: int
    recortable: bool = True

    @property
    def tokens(self) -> int:
        return int(len(self.contenido) / CARACTERES_POR_TOKEN) + 1


@dataclass
class Manifiesto:
    etapa: str
    unidad: str
    bloques: list[Bloque] = field(default_factory=list)
    limite_tokens: int = 120_000
    excluidos: list[str] = field(default_factory=list)

    @property
    def tokens(self) -> int:
        return sum(bloque.tokens for bloque in self.bloques)

    def hash(self) -> str:
        material = "\n".join(f"{b.nombre}:{sha256_texto(b.contenido)}" for b in self.bloques)
        return sha256_texto(material)

    def render(self) -> str:
        partes = [f"### {bloque.nombre}\n{bloque.contenido}" for bloque in self.bloques]
        return "\n\n".join(partes)

    def como_dict(self) -> dict[str, Any]:
        """Lo que se anexa al ledger: que se dio, en que orden y que se dejo fuera.

        No se anexa el contenido -- eso va al almacen por contenido -- sino su
        huella, para que el ledger siga siendo legible y siga permitiendo
        reconstruir la decision.
        """
        return {
            "etapa": self.etapa,
            "unidad": self.unidad,
            "hash": self.hash(),
            "tokens_estimados": self.tokens,
            "limite_tokens": self.limite_tokens,
            "bloques": [
                {
                    "nombre": b.nombre,
                    "prelacion": b.prelacion,
                    "tokens": b.tokens,
                    "recortable": b.recortable,
                    "hash": sha256_texto(b.contenido),
                }
                for b in self.bloques
            ],
            "excluidos_por_prelacion": self.excluidos,
        }

    def ajustar(self) -> "Manifiesto":
        """Regla 3 de la politica de compactacion (seccion 3.6): el manifiesto es el techo.

        Si no cabe, no se recorta en caliente: se emite ERR-206 y se aplica la
        prelacion declarada, dejando constancia de que se dejo fuera. Un recorte
        silencioso es un error de continuidad esperando a ocurrir.
        """
        if self.tokens <= self.limite_tokens:
            return self

        # Se recorta empezando por la prelacion mas baja, y nunca lo no recortable.
        candidatos = sorted(
            [b for b in self.bloques if b.recortable],
            key=lambda b: -b.prelacion,
        )
        for bloque in candidatos:
            if self.tokens <= self.limite_tokens:
                break
            self.bloques.remove(bloque)
            self.excluidos.append(bloque.nombre)

        if self.tokens > self.limite_tokens:
            raise ErrorStoryMaker(
                "ERR-206",
                "El manifiesto no cabe en la ventana ni tras aplicar la prelacion "
                "declarada. Lo que queda es todo no recortable.",
                etapa=self.etapa,
                unidad=self.unidad,
                tokens=self.tokens,
                limite=self.limite_tokens,
                excluidos=self.excluidos,
            )
        return self


# La tabla de la seccion 3.4, declarada como dato. El orden de la lista es el
# orden de prelacion al recortar: el primero es lo ultimo que se suelta.
PRELACION: dict[str, tuple[str, ...]] = {
    "sm-entrada": ("semillas", "campos_cubiertos"),
    "sm-investigacion": ("ambito_investigacion",),
    # RF-102: el refutador ve la afirmacion, sus fuentes citadas y su contenido
    # conservado, y NUNCA el razonamiento con que se compuso. Es fijo por
    # requisito: si viera el razonamiento, su busqueda en contra estaria guiada
    # por la misma linea de pensamiento que quiere poner a prueba.
    "sm-refutador": ("afirmacion", "fuentes_citadas", "contenido_conservado"),
    "sm-diseno": ("encargo", "restricciones", "figuras_reales", "contexto_tematico"),
    "sm-validador-canon": ("plan", "encargo", "restricciones"),
    "sm-redactor": (
        "ficha_escena",
        "estilo_y_piloto",
        "hechos_de_sujetos_presentes",
        "escenas_del_capitulo",
        "sinopsis_previas",
    ),
    "sm-refinador": ("texto_escena", "pasajes_protegidos", "estilo_y_piloto"),
    "sm-validador": (
        "capitulo",
        "fichas_escenas",
        "hechos",
        "revelaciones",
        "restricciones",
    ),
    # Sin recorte: es la unica etapa cuyo objeto es el conjunto.
    "sm-global": ("novela_completa", "canon", "guia_estilo", "indicadores_por_tercio"),
}

# Bloques que ningun recorte puede tocar, porque sin ellos la unidad no tiene
# objeto o incumpliria un requisito.
NO_RECORTABLES: dict[str, frozenset[str]] = {
    "sm-refutador": frozenset({"afirmacion", "fuentes_citadas", "contenido_conservado"}),
    "sm-redactor": frozenset({"ficha_escena", "estilo_y_piloto"}),
    "sm-refinador": frozenset({"texto_escena", "pasajes_protegidos"}),
    "sm-validador": frozenset({"capitulo", "fichas_escenas"}),
    "sm-validador-canon": frozenset({"plan"}),
    "sm-diseno": frozenset({"encargo"}),
    "sm-global": frozenset(PRELACION["sm-global"]),
}


def construir(
    etapa: str,
    unidad: str,
    contenidos: dict[str, str],
    limite_tokens: int = 120_000,
) -> Manifiesto:
    """Monta el manifiesto de una etapa a partir de su tabla de prelacion.

    Un contenido que no figure en la tabla de la etapa se rechaza: dar a un agente
    algo que su manifiesto no declara rompe la promesa de que siempre se puede
    reconstruir con que informacion se tomo una decision.
    """
    if etapa not in PRELACION:
        raise ErrorStoryMaker(
            "ERR-302", f"Etapa sin manifiesto declarado: {etapa}", etapa=etapa
        )

    declarados = PRELACION[etapa]
    intrusos = sorted(set(contenidos) - set(declarados))
    if intrusos:
        raise ErrorStoryMaker(
            "ERR-105",
            f"La etapa {etapa} no declara estos bloques en su manifiesto: {intrusos}",
            etapa=etapa,
            intrusos=intrusos,
            declarados=list(declarados),
        )

    no_recortables = NO_RECORTABLES.get(etapa, frozenset())
    bloques = [
        Bloque(
            nombre=nombre,
            contenido=contenidos[nombre],
            prelacion=orden + 1,
            recortable=nombre not in no_recortables,
        )
        for orden, nombre in enumerate(declarados)
        if nombre in contenidos
    ]
    return Manifiesto(etapa, unidad, bloques, limite_tokens).ajustar()


# ==========================================================================
# La sinopsis acumulada (seccion 3.5)
# ==========================================================================

LIMITE_SINOPSIS_PALABRAS = 400


def normalizar_sinopsis(texto: str, limite: int = LIMITE_SINOPSIS_PALABRAS) -> str:
    """Impone el limite duro de extension de una sinopsis de capitulo.

    Una sinopsis es un acta, no un resumen literario: que ocurrio, quien estaba,
    que cambio de estado y que quedo pendiente. Sin limite duro se convierte en
    prosa, y entonces deja de ser barata y empieza a competir con el texto.
    """
    palabras = texto.split()
    if len(palabras) <= limite:
        return texto.strip()
    return " ".join(palabras[:limite]) + " [...]"


def ordenar_sinopsis(
    sinopsis_por_capitulo: Sequence[tuple[str, str]],
    capitulo_actual: str,
) -> list[tuple[str, str]]:
    """Orden de entrega al redactor: inverso de cercania.

    Se recortan por prelacion empezando por las mas lejanas. La del capitulo
    inmediatamente anterior no se recorta nunca, porque es la que sostiene la
    continuidad inmediata, que es donde las contradicciones se notan.
    """
    previas = [(cap, texto) for cap, texto in sinopsis_por_capitulo if cap < capitulo_actual]
    return sorted(previas, key=lambda par: par[0], reverse=True)


def componer_sinopsis_previas(
    sinopsis_por_capitulo: Sequence[tuple[str, str]],
    capitulo_actual: str,
    limite_palabras: int = 2_000,
) -> tuple[str, list[str]]:
    """Compone el bloque `sinopsis_previas` del manifiesto del redactor.

    Devuelve el texto y la lista de capitulos que quedaron fuera por el limite,
    que es lo que el ledger necesita para dejar constancia de que se recorto.
    """
    ordenadas = ordenar_sinopsis(sinopsis_por_capitulo, capitulo_actual)
    incluidas: list[str] = []
    excluidas: list[str] = []
    consumidas = 0

    for indice, (capitulo, texto) in enumerate(ordenadas):
        palabras = len(texto.split())
        # La del capitulo inmediatamente anterior entra siempre, cueste lo que cueste.
        inmediata = indice == 0
        if not inmediata and consumidas + palabras > limite_palabras:
            excluidas.append(capitulo)
            continue
        incluidas.append(f"## {capitulo}\n{texto}")
        consumidas += palabras

    return "\n\n".join(incluidas), excluidas
