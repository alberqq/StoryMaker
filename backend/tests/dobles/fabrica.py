"""spec: §7.1 · arq: §6, §7

Una novela mínima pero completa, para las pruebas que necesitan una base poblada.

Tiene lo justo para que el ensamblador tenga algo que ensamblar: dos capítulos con sus
escenas y beats, un homenajeado con su arco, un escenario, corpus con hechos anclados, un
elemento de personalización obligatorio y el capítulo 1 ya aprobado con su continuidad. No
pretende parecerse a una novela de verdad; pretende ejercitar los siete bloques.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import aiosqlite

from storymaker.commons.db.repos import arnes, intake, mundo, texto


@dataclass(frozen=True)
class NovelaDePrueba:
    fase_run: int
    capitulo_1: int
    capitulo_2: int
    escena_1: int
    escena_2: int
    homenajeado: int
    hecho_anclado: int
    hecho_suelto: int
    dato_obligatorio: int
    version_capitulo_1: int
    hito: int


async def poblar(db: aiosqlite.Connection) -> NovelaDePrueba:
    fase_run = await arnes.abrir_fase_run(db, "plotting")

    # --- Canon -------------------------------------------------------------------
    cursor = await db.execute(
        """
        INSERT INTO canon_personaje (nombre, tipo, objetivo, miedo, voz, estatus,
                                     fecha_nacimiento)
        VALUES ('Manuel Ferrer', 'inventado', 'salvar el astillero', 'morir sin legado',
                'seca y marinera', 'armador', '1760-03-02')
        """
    )
    homenajeado = int(cursor.lastrowid or 0)
    cursor = await db.execute(
        """
        INSERT INTO canon_personaje (nombre, tipo, objetivo, voz, estatus)
        VALUES ('Tomasa', 'inventado', 'mantener la taberna', 'burlona', 'tabernera')
        """
    )
    tabernera = int(cursor.lastrowid or 0)
    cursor = await db.execute(
        "INSERT INTO canon_escenario (descripcion) VALUES ('El muelle al amanecer, con niebla')"
    )
    escenario = int(cursor.lastrowid or 0)
    await db.execute(
        """
        INSERT INTO canon_obra (titulo, premisa, tema, genero, voz, estilo_json, homenajeado_id)
        VALUES ('La bahia de los toneleros', 'Un armador contra el bloqueo',
                'lo que se hereda no es el oficio', 'novela historica',
                'tercera persona con focalizacion en el homenajeado', ?, ?)
        """,
        (
            json.dumps(
                {
                    "grado_licencia": "moderado",
                    "arcaismo": "moderado",
                    "contenido_admisible": "sin violencia explicita",
                },
                ensure_ascii=False,
            ),
            homenajeado,
        ),
    )
    await db.execute(
        "INSERT INTO canon_glosario (termino, significado) VALUES ('jarcia', 'cabos del barco')"
    )
    await db.execute(
        """
        INSERT INTO canon_prohibida (nivel, termino, normalizado)
        VALUES ('destinatario', 'Beatriz', 'beatriz')
        """
    )
    cursor = await db.execute(
        """
        INSERT INTO canon_arco (personaje_id, tipo, estado_inicial, estado_final)
        VALUES (?, 'positivo', 'se cree solo', 'acepta ayuda')
        """,
        (homenajeado,),
    )
    arco = int(cursor.lastrowid or 0)

    # --- Escaleta ----------------------------------------------------------------
    cursor = await db.execute(
        "INSERT INTO plan_capitulo (numero, titulo, funcion, gancho) "
        "VALUES (1, 'La niebla', 'presentar al armador', 'llega la orden de embargo')"
    )
    capitulo_1 = int(cursor.lastrowid or 0)
    cursor = await db.execute(
        "INSERT INTO plan_capitulo (numero, titulo, funcion, gancho) "
        "VALUES (2, 'El roble', 'el armador busca madera', 'la taberna arde')"
    )
    capitulo_2 = int(cursor.lastrowid or 0)

    cursor = await db.execute(
        """
        INSERT INTO plan_escena (capitulo_id, orden, escenario_id, fecha_narrativa,
                                 pdv_personaje_id, objetivo, conflicto, resultado)
        VALUES (?, 1, ?, '1805-04-11', ?, 'conseguir roble americano',
                'el puerto esta bloqueado', 'consigue media carga')
        """,
        (capitulo_2, escenario, homenajeado),
    )
    escena_2 = int(cursor.lastrowid or 0)
    cursor = await db.execute(
        """
        INSERT INTO plan_escena (capitulo_id, orden, escenario_id, fecha_narrativa,
                                 pdv_personaje_id, objetivo, conflicto, resultado)
        VALUES (?, 1, ?, '1805-04-02', ?, 'presentar el astillero',
                'llega la orden', 'la acepta a reganadientes')
        """,
        (capitulo_1, escenario, homenajeado),
    )
    escena_1 = int(cursor.lastrowid or 0)

    await db.execute(
        "INSERT INTO plan_beat (escena_id, orden, accion, cambio_de_valor) "
        "VALUES (?, 1, 'Manuel discute con el contramaestre', 'confianza -> duda')",
        (escena_2,),
    )
    presencias = ((escena_1, homenajeado), (escena_2, homenajeado), (escena_2, tabernera))
    for escena, personaje in presencias:
        await db.execute(
            "INSERT INTO plan_escena_personaje (escena_id, personaje_id) VALUES (?, ?)",
            (escena, personaje),
        )

    cursor = await db.execute(
        """
        INSERT INTO canon_arco_hito (arco_id, orden, descripcion, escena_id)
        VALUES (?, 1, 'Manuel pide ayuda por primera vez', ?)
        """,
        (arco, escena_2),
    )
    hito = int(cursor.lastrowid or 0)

    # --- Corpus ------------------------------------------------------------------
    hecho_anclado = await mundo.insertar_hecho(
        db,
        fase_run_id=fase_run,
        enunciado="El roble americano llegaba a Cadiz por el puerto de La Habana",
        estado="verificado",
        dimension="cultura_material",
        cita="fragmento de la fuente",
        respaldo="respaldado",
    )
    hecho_suelto = await mundo.insertar_hecho(
        db,
        fase_run_id=fase_run,
        enunciado="Las tabernas del muelle abrian antes del amanecer",
        estado="inferido",
        dimension="mentalidad",
    )
    await db.execute(
        """
        INSERT INTO plan_anclaje (escena_id, hecho_id, tipo_vinculo)
        VALUES (?, ?, 'sostiene la escena')
        """,
        (escena_2, hecho_anclado),
    )

    # --- Encargo -----------------------------------------------------------------
    dato_obligatorio = await intake.insertar_dato(
        db,
        tipo="objeto",
        valor_json=json.dumps({"descripcion": "el reloj de bolsillo del abuelo"}),
        origen="entrevista",
        obligatorio=True,
    )
    await db.execute(
        """
        INSERT INTO plan_anclaje (escena_id, dato_id, tipo_vinculo)
        VALUES (?, ?, 'aparece en escena')
        """,
        (escena_2, dato_obligatorio),
    )

    # --- El capitulo 1, ya escrito y aprobado -------------------------------------
    version_capitulo_1 = await texto.insertar_capitulo_version(
        db,
        capitulo_id=capitulo_1,
        fase_run_id=fase_run,
        texto=(
            "La niebla subia del agua como si el mar exhalase. Manuel Ferrer conto los "
            "cascos del astillero antes de que el sol tocara la jarcia."
        ),
        resumen="Manuel recibe la orden de embargo y decide resistir.",
    )
    await texto.aprobar_capitulo(db, version_capitulo_1)
    await texto.insertar_continuidad(
        db,
        capitulo_version_id=version_capitulo_1,
        personaje_id=homenajeado,
        escenario_id=escenario,
        fecha_narrativa="1805-04-02",
        conocimiento_json=json.dumps(["sabe del embargo"]),
        posesiones_json=json.dumps(["el reloj del abuelo"]),
        estado_json=json.dumps({"animo": "tenso"}),
    )

    return NovelaDePrueba(
        fase_run=fase_run,
        capitulo_1=capitulo_1,
        capitulo_2=capitulo_2,
        escena_1=escena_1,
        escena_2=escena_2,
        homenajeado=homenajeado,
        hecho_anclado=hecho_anclado,
        hecho_suelto=hecho_suelto,
        dato_obligatorio=dato_obligatorio,
        version_capitulo_1=version_capitulo_1,
        hito=hito,
    )
