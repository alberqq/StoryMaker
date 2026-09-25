# Hoja de revisión humana

Hoja de trabajo para la revisión que pide el enunciado: una persona puntúa una novela completa con la misma rúbrica que el juez, para comparar los dos juicios. El procedimiento completo está en [`docs/revision-humana.md`](../docs/revision-humana.md). Esta hoja no lo sustituye: solo te deja a mano dónde anotar.

**Novela propuesta:** Madrid 1858, **versión 1**. Tiene 5 capítulos y se lee en unos 25 minutos. Ábrela desde el historial de la interfaz o con el PDF `backend/proyectos/lozoya/lozoya.v1.pdf`. La versión 2 de esta novela no sirve: salió de una regeneración que falló.

## Tres reglas antes de empezar

1. **Puntúa desde [`rubrica.yaml`](../backend/src/storymaker/publication/rubrica.yaml), el fichero.** Aquí solo están los nombres de los criterios, a propósito: si la descripción se copiara en esta hoja, la comparación dejaría de valer el día que cambie el fichero.
2. **No mires las notas del juez hasta haber escrito las tuyas.** Leer un 9 en «arco» antes de puntuar el arco contamina la nota.
3. **Lee la novela entera, seguida.** Continuidad, arco, ritmo y naturalidad de la personalización son propiedades del conjunto.

## Anotaciones mientras lees

| Capítulo | Lo que llama la atención |
|---|---|
| 1 | |
| 2 | |
| 3 | |
| 4 | |
| 5 | |

## Puntuación (1–10, con justificación)

| Criterio | Tu nota | Justificación |
|---|---|---|
| continuidad | | |
| arco | | |
| coherencia_de_personajes | | |
| ritmo | | |
| tono | | |
| prosa | | |
| naturalidad_de_la_personalizacion | | |
| autenticidad_de_epoca | | |
| **Media** | | Umbral de publicación: 6,0 |

## Después de puntuar

1. Ahora sí, compara con el juez: su puntuación está en la tabla `score` de la novela (`validador = 'juez_rubrica'`, `objeto_id = 1`), y en el anexo A5. El juez de la versión 1 puntuó con la rúbrica anterior, que no tenía «tono»: ese criterio se queda sin comparar.
2. Anota las divergencias de más de 2 puntos y qué se hace con cada una, según la tabla de §4 de `docs/revision-humana.md`.
3. Registra tu nota como `revision_humana` en la tabla `score`, con el fragmento de §3.4 de ese documento, y añade el acta a su §5.
4. Pasa tus notas al anexo A6 del deck.
