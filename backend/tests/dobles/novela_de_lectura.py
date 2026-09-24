"""Una novela pequeña, ya publicada dos veces, para probar la superficie de lectura.

Tres capítulos; la versión 2 regenera el segundo y reutiliza los otros dos, que es la forma
exacta de una regeneración (arq. §4, Fase 6). Los nombres son inventados.
"""

from __future__ import annotations

import json
from pathlib import Path

from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos import arnes, texto


async def sembrar(ruta: Path) -> None:
    async with abrir_novela(ruta, crear=True) as db:
        fase = await arnes.abrir_fase_run(db, "writing")
        await db.execute(
            "INSERT INTO intake_brief (fase_run_id, json, hash) VALUES (?, ?, ?)",
            (
                fase,
                json.dumps({"nombre_homenajeado": "Elvira Ponce", "ocasion": "jubilacion"}),
                "h",
            ),
        )
        await db.execute(
            """INSERT INTO mundo_entidad (id, tipo, nombre, nombre_epoca)
               VALUES (1, 'lugar', ?, ?)""",
            ("Cadiz", "Cadiz de las Cortes"),
        )
        await db.executemany(
            """INSERT INTO canon_personaje (id, nombre, tipo, rasgos_json, estatus)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (1, "Elvira Ponce", "inventado", json.dumps(["tenaz", "curiosa"]), "armadora"),
                (2, "Tomas Ruiz", "inventado", None, "piloto"),
                (3, "Sin Escena", "inventado", None, ""),
            ],
        )
        await db.execute("INSERT INTO canon_relacion (a_id, b_id, tipo) VALUES (1, 2, 'hermano')")
        await db.execute(
            "INSERT INTO canon_obra (id, titulo, homenajeado_id) VALUES (1, 'La mar de Cadiz', 1)"
        )
        await db.execute(
            """INSERT INTO canon_escenario (id, lugar_entidad_id, descripcion)
               VALUES (1, 1, 'El muelle')"""
        )
        await db.execute(
            "INSERT INTO canon_licencia (alteracion, justificacion) VALUES (?, ?)",
            ("Se adelanta la botadura un año", "Para que coincida con la boda"),
        )

        ids_v1: list[int] = []
        for numero in (1, 2, 3):
            await db.execute(
                "INSERT INTO plan_capitulo (id, numero, titulo) VALUES (?, ?, ?)",
                (numero, numero, f"Titulo {numero}"),
            )
            await db.execute(
                """INSERT INTO plan_escena (id, capitulo_id, orden, escenario_id)
                   VALUES (?, ?, 1, 1)""",
                (numero, numero),
            )
            cursor = await db.execute(
                """INSERT INTO capitulo_version (capitulo_id, fase_run_id, texto, palabras, estado)
                   VALUES (?, ?, ?, 4, 'aprobado')""",
                (numero, fase, f"Texto del capitulo {numero}.\nSegundo parrafo."),
            )
            ids_v1.append(int(cursor.lastrowid or 0))
        await db.executemany(
            "INSERT INTO plan_escena_personaje (escena_id, personaje_id) VALUES (?, ?)",
            [(1, 1), (2, 1), (3, 1), (2, 2)],
        )
        await texto.publicar_version(db, numero=1, capitulo_version_ids=ids_v1)

        otra_fase = await arnes.abrir_fase_run(db, "regeneration")
        cursor = await db.execute(
            """INSERT INTO capitulo_version (capitulo_id, fase_run_id, texto, palabras, estado)
               VALUES (2, ?, 'Texto regenerado del capitulo 2.', 5, 'aprobado')""",
            (otra_fase,),
        )
        regenerado = int(cursor.lastrowid or 0)
        await texto.publicar_version(
            db, numero=2, capitulo_version_ids=[ids_v1[0], regenerado, ids_v1[2]]
        )
        await db.commit()
