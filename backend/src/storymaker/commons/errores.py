"""spec: §8 · arq: §9, §16.4

La taxonomía de errores del arnés, en un solo módulo porque la distinción que establece
es la que gobierna el comportamiento del sistema entero:

**Una incidencia es un defecto del contenido y tiene camino de vuelta** — el capítulo
regresa al editor, el hecho se degrada, el aviso viaja al capítulo siguiente. No vive
aquí: vive como fila en `incidencia`.

**Un error es una avería y detiene la invocación.** Es lo que hay aquí. Confundirlos
aprobaría capítulos por avería, que es el fallo más caro que este sistema puede tener:
un `lake` que no arranca no significa que la cronología sea correcta.
"""

from __future__ import annotations


class ErrorDeStoryMaker(Exception):
    """Raíz de todo lo que detiene una invocación. Nunca se lanza directamente."""


class NovelaNoEncontrada(ErrorDeStoryMaker):
    """No hay fichero para esa novela. La CLI lo traduce a mensaje; la API, a `404`."""


class NovelaOcupada(ErrorDeStoryMaker):
    """Otra invocación tiene el cerrojo.

    Quien llega segundo es **rechazado, no encolado**: una cola sería un segundo lugar
    donde vive el estado, y dos invocaciones sobre la misma novela podrían duplicar un
    capítulo, que es justo lo que `ResumeIsExactlyOnce` prohíbe. La API lo traduce a
    `409`, y no se pierde nada porque la decisión del gate ya está escrita y reanudar es
    el camino de siempre.
    """


class ErrorDeArranque(ErrorDeStoryMaker):
    """El fichero no está en condiciones de aceptar trabajo. Nunca se degrada en silencio."""


class SqliteVecNoDisponible(ErrorDeArranque):
    """La extensión nativa no carga en este intérprete (U-15).

    Se detiene el arranque con un mensaje explícito en lugar de seguir sin búsqueda
    semántica: un ensamblador que no puede buscar produciría paquetes de contexto
    empobrecidos sin que nadie se enterase.
    """


class EsquemaDelFuturo(ErrorDeArranque):
    """El fichero lo escribió una versión del código posterior a esta.

    Nunca se abre una novela con un esquema que no se entiende: migrar hacia atrás no
    está definido, y adivinar significaría escribir sobre datos que no se comprenden.
    """


class PresupuestoExcedido(ErrorDeStoryMaker):
    """El prompt ensamblado supera el techo del rol, así que **la llamada no se emite**.

    No es una comprobación posterior: es la guarda de §12, que decide de antemano cuánto
    contexto se deja entrar porque el SDK no permite preguntar cuánto lleva consumido.
    """


class ErrorDeEntorno(ErrorDeStoryMaker):
    """Una herramienta externa falló por una razón que no es un veredicto.

    `lake` ausente, un subproceso roto, un navegador que no arranca. **Se distingue del
    veredicto negativo**: un invariante violado es una incidencia y vuelve al editor; una
    avería detiene y no aprueba.
    """


class EscaletaAusente(ErrorDeStoryMaker):
    """Se pidió el paquete de un capítulo que la escaleta no contempla.

    Aborta en lugar de generar a ciegas: un bloque vacío es normal —el capítulo 1 no
    tiene memoria de N-1—, pero un capítulo sin encargo no lo es.
    """


class NadaQueReintentar(ErrorDeStoryMaker):
    """`storymaker reintentar` sobre una novela que no terminó en un `Fail` de capítulo.

    Se rechaza sin tocar el checkpoint: reabrir un capítulo de una novela que sigue viva,
    espera en un gate o aún no ha sellado el corpus la sacaría del camino que el grafo
    garantiza.
    """
