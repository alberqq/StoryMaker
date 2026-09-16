"""Los dos servidores de recuperacion (Tecnica 2.0, seccion 2.5).

Son la frontera con el exterior y el unico punto por el que entra informacion no
generada. De ahi la regla que ambos comparten y que este paquete impone en el
codigo, no en la documentacion:

> Devuelven siempre **contenido mas localizador mas fecha**, nunca contenido suelto.

Sin eso, RF-101 no tendria que conservar, y la trazabilidad de RF-082 se caeria en
cuanto muriera un enlace. Un resultado sin localizador se descarta antes de salir
del servidor: es preferible una laguna declarada a una afirmacion que no se puede
rastrear.

Se implementan sin dependencias, igual que el nucleo. El protocolo MCP sobre
entrada y salida estandar es JSON-RPC 2.0, y lo que hace falta de el -- `initialize`,
`tools/list` y `tools/call` -- cabe en `servidor.py`.
"""

__version__ = "2.0.0"
