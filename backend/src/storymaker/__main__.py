"""spec: §5.3 · arq: §16.5

`python -m storymaker`: la CLI con el mismo intérprete que la lanza.

El lanzador de la API la usa así, y no buscando el ejecutable `storymaker` en el `PATH`, para
que el proceso que abre una novela desde la interfaz corra con exactamente el mismo entorno
que el servidor que lo lanza.
"""

from storymaker.cli.comandos import app

app()
