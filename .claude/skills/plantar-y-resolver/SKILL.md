---
name: plantar-y-resolver
description: Como se declara que una resolucion esta preparada y que cuenta como preparacion. Cargala al disenar hilos y revelaciones, y al validar si el Canon puede aprobarse.
---

# Plantar y resolver

Un hilo que se resuelve con algo que el lector no vio venir **ni pudo ver venir** no
se lee como un giro: se lee como un truco. El Canon es el sitio donde se decide que
eso no pase, porque cuando la novela esta escrita ya es tarde.

## La regla

> Una resolucion esta preparada si el lector puede reconstruirla con lo que ya se le
> dio, aunque no la haya anticipado.

Las dos mitades importan. "Puede reconstruirla" descarta el truco. "Aunque no la
haya anticipado" descarta el spoiler: preparar no es anunciar.

## Que cuenta como preparacion

| Cuenta | No cuenta |
|---|---|
| Un hecho establecido en escena, aunque parezca menor | Una explicacion que llega con la resolucion |
| Una capacidad o un limite del personaje ya demostrados | Una capacidad que aparece cuando hace falta |
| Un objeto que estuvo presente y se uso para otra cosa | Un objeto mencionado por primera vez al resolver |
| Una relacion que el lector vio funcionar | Una relacion que se declara en el momento |
| Una mentira que el lector oyo decir | Una mentira que se revela sin que nadie la dijera |

La prueba practica: **quita la escena de resolucion y pregunta si la informacion
necesaria sigue estando en la novela**. Si no esta, no hay preparacion; hay
explicacion.

## Como se declara en el Canon

Cada hilo declara su escena de apertura, sus escenas de avance y su escena de
resolucion. Cada revelacion declara en que escena se hace conocida, ante quien, y
-- esto es lo que hace comprobable el plan -- **en que escenas hay personajes
actuando sin conocerla**:

```json
{
  "id": "rev_el-mapa-es-falso",
  "informacion": "El mapa que la corona compro esta falsificado",
  "escena": "esc_002_002",
  "ante": ["lector", "corona"],
  "escenas_actuando_sin_saberlo": ["esc_001_001", "esc_002_001"]
}
```

Con eso declarado, el nucleo comprueba que la revelacion cae **despues** de todas
las escenas en que alguien actua sin conocerla. Sin declararlo, esa comprobacion no
puede correr y el orden queda a merced de que nadie se equivoque.

## Dos errores frecuentes, y como se ven en el plan

**Resolver un hilo en una escena que no lo avanzo nunca.** Se ve porque la escena de
resolucion no aparece entre las de avance de ningun tramo anterior. El hilo aparece
al principio, desaparece treinta capitulos y reaparece resuelto.

**Revelar ante el lector mucho antes que ante los personajes, sin que eso sea el
efecto buscado.** Es legitimo -- es suspense -- pero tiene que ser deliberado y
declararse en `ante`. Si el lector lleva veinte capitulos sabiendo algo que los
personajes ignoran y eso no es el motor de la tension, es un fallo de plan.

## Hilos que quedan abiertos

Solo si el Autor los autorizo expresamente en el Encargo
(`hilos_abiertos_autorizados`). Es la unica excepcion admitida, y el nucleo la
comprueba: cualquier otro hilo sin escena de resolucion impide aprobar el Canon.

Un hilo abierto sin autorizacion no es una decision artistica: es un olvido, y se
nota al leer.
