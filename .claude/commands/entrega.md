---
description: Genera la entrega en Markdown y PDF con su paquete de trazabilidad.
allowed-tools: Bash, Read
---

Entrega (RF-090 a RF-093).

## Antes de nada, comprueba que se puede

```
storymaker --proyecto <prj> novela pasada-global
storymaker --proyecto <prj> novela cerrar
```

Las cinco condiciones de RF-077 se cumplen a la vez o no se cumplen: todos los
capitulos validados, todos los hilos resueltos, ningun bloqueante abierto, pasada
global superada, extension dentro de tolerancia.

Si falta alguna, el nucleo te dice cual. **Preséntala y para.** No se entrega una
novela que no esta terminada llamandola terminada.

## Generar

```
storymaker --proyecto <prj> entrega generar
```

Produce:

- `entrega/novela.md` -- el formato canonico.
- `entrega/novela.pdf` -- si hay conversor disponible.
- `entrega/paquete_trazabilidad.json` -- Encargo, Contexto con sus fuentes y su
  contenido conservado, Canon final, licencias e informe de Deuda de calidad.

## Que decir al Autor

1. **El estado real**: *finalizado* o *finalizado con reservas*. Si es lo segundo,
   **di por que**, con los motivos concretos. Entregar con reservas sin decirlo es
   justo lo que la Deuda de calidad existe para impedir.
2. **La Deuda de calidad**, si la hay: que hallazgos se cerraron sin resolver, con
   que severidad y por que motivo.
3. **Las Licencias literarias aplicadas**: de que hecho documentado se desvia cada
   una, con que justificacion, quien la propuso y quien la autorizo. Las de alcance
   figuran una sola vez, con sus limites y los pasajes que amparan.
4. **Las fuentes que no se pudieron conservar**, con el motivo.
5. **Si el PDF fallo**: se entrega solo Markdown y se dice (ERR-902). No se entrega
   en silencio algo distinto de lo que se prometio.
