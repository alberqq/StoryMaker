# Revisión humana

Cómo se revisa una novela de StoryMaker con la misma rúbrica que usa el juez, y qué se hace con lo que salga.

Esto es el protocolo de **P-122** y realiza §4.5 de [`verification.md`](verification.md). Es una capacidad de clase **I** —inspección— bajo la puerta **G2**: no bloquea una integración, pero sin ella no hay nada con lo que contrastar las notas del modelo, y un juez sin contraste es un número que nadie ha comprobado nunca.

---

## 1. Por qué existe

El juez es un agente que puntúa siete criterios del 1 al 10, y de su media sale la decisión de publicar. Esa media gobierna una puerta, así que la pregunta obvia es quién juzga al juez.

La respuesta no puede ser otro modelo: eso solo mueve la pregunta un escalón. Tiene que ser una persona leyendo la novela entera. Y para que la comparación signifique algo, **la persona y el modelo tienen que estar respondiendo literalmente la misma pregunta**, no dos parecidas.

De ahí la única regla no negociable de este documento: **se puntúa desde [`rubrica.yaml`](../backend/src/storymaker/publication/rubrica.yaml), el fichero**, no desde una copia, un resumen ni un recuerdo de lo que pedía cada criterio. Si alguien reescribe los siete criterios en una hoja aparte «para tenerlos a mano», la comparación deja de decir nada el día que el fichero cambie y la hoja no.

---

## 2. Cuándo se hace

- **Al menos una novela completa** revisada así antes de dar un hito por cerrado.
- **Una sesión de red-teaming manual por hito**, que se anota en [`red-team.md`](red-team.md) con su clase de evidencia.

Las dos son nocturnas en el sentido de G2: se hacen fuera del ciclo de integración, sin prisa, y un hallazgo abre defecto en lugar de detener a nadie.

---

## 3. El procedimiento

### 3.1 Antes de leer

Se necesita una novela **publicada**, con su versión y su manifiesto escritos. Sirve cualquiera de las tres formas de leerla: el PDF, la pantalla de impresión del frontend, o `storymaker estado <novela>` para localizar el número de versión y sacar el texto de la base.

**No se miran las notas del juez todavía.** Es la parte del procedimiento que más fácil se salta y la que más lo invalida: leer un 4 en «ritmo» antes de puntuar el ritmo contamina la nota, y lo que queda no es una revisión independiente sino un acuerdo fabricado. Las notas del juez se consultan **después** de tener las siete propias escritas.

### 3.2 Leyendo

Se lee la novela entera, seguida. No por muestreo: cuatro de los siete criterios —continuidad, arco, ritmo y naturalidad de la personalización— son propiedades del conjunto y no se pueden juzgar sobre tres capítulos sueltos. Un objeto que cambia de sitio entre el capítulo 2 y el 9 solo lo ve quien ha leído los dos.

Conviene ir anotando al margen, con el número de capítulo, cualquier cosa que llame la atención. Al terminar, esas anotaciones son la materia prima de las siete justificaciones.

### 3.3 Puntuando

Los siete criterios, del 1 al 10, **cada uno con su justificación escrita**. La justificación no es un trámite: es lo que permite que la comparación con el juez sea por criterio y no por media, y es lo único que hace accionable una divergencia. «Ritmo: 5» no dice qué cambiar; «Ritmo: 5, los capítulos 4 a 6 repiten la misma función de aplazar la inspección» sí.

El umbral de publicación es **6.0 de media**, el mismo que aplica `supera_el_umbral`.

### 3.4 Registrando

La nota humana se escribe en la tabla `score` de la novela, con el nombre `revision_humana`, para que quede al lado de la del juez y no en un documento aparte:

```python
from storymaker.commons.db.apertura import abrir_novela
from storymaker.commons.db.repos import arnes

async with abrir_novela(ruta) as db:
    await arnes.registrar_score(
        db,
        objeto_tipo="novela",
        objeto_id=<numero de version>,
        validador="revision_humana",
        valor=<media>,
        detalle={"continuidad": 7, "arco": 5, ...,
                 "justificaciones": {"arco": "..."}},
    )
    await db.commit()
```

Y el acta se añade a §5 de este documento, que es donde se acumulan.

---

## 4. Qué se hace con la divergencia

Este sistema **no reentrena nada**, y conviene no prometer más de lo que hay. Una divergencia entre la nota humana y la del juez tiene tres destinos posibles, y los tres son control, no aprendizaje:

| Qué se observa | Qué se hace |
|---|---|
| La persona puntúa sistemáticamente más bajo que el juez en un criterio | **Nueva versión del prompt del juez en Langfuse**, medida contra el eval anterior. Si no mejora, se revierte |
| La persona y el juez coinciden, y los dos puntúan bajo | El defecto está en la novela, no en la medición: va al hito como trabajo de la fase que lo produce |
| La persona detecta algo que la rúbrica no pregunta | Se propone un criterio nuevo **arriba**, en §11b de la arquitectura. La rúbrica no crece por el camino corto |

Un aviso sobre el segundo caso. La tentación al ver una nota baja es subir el rol del juez o ablandar el umbral. Eso no arregla la novela: la publica. El umbral está en el fichero de rúbrica precisamente para que moverlo sea un cambio visible y no un ajuste de paso.

Sobre la varianza del propio juez —el mismo juez puntuando dos veces la misma novela— no decide nada esta revisión: la mide [`evals/varianza_juez.py`](../evals/varianza_juez.py), y es un problema distinto. Conviene tener su número delante antes de concluir que una divergencia con la persona es sistemática: si el juez no se pone de acuerdo consigo mismo, no está discrepando de nadie.

---

## 5. Actas

Una entrada por sesión. Se añaden al final; las anteriores no se editan.

### Plantilla

```
### <fecha> · <novela> · versión <n>

**Revisor:** · **Duración de la lectura:**

| Criterio | Persona | Juez | Justificación de la persona |
|---|---|---|---|
| continuidad | | | |
| arco | | | |
| coherencia_de_personajes | | | |
| ritmo | | | |
| prosa | | | |
| naturalidad_de_la_personalizacion | | | |
| autenticidad_de_epoca | | | |
| **Media** | | | |

**Divergencias por encima de 2 puntos:**

**Qué se hace con ellas:**

**Sesión de red-teaming asociada:** RT-nn en `red-team.md`, o «ninguna».
```

### Actas registradas

Ninguna todavía. **La primera revisión necesita una novela publicada de verdad**, y eso exige una sesión de Claude Code autenticada: los nueve roles hablan con el modelo a través del Agent SDK, que hereda esa sesión, y en este repositorio no hay ni va a haber credencial de Anthropic. Hasta esa primera novela, G2 tiene esta capacidad **declarada y no ejercida**, que es distinto de tenerla en verde.

---

## 6. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-23 | Versión inicial: el protocolo de revisión con rúbrica y la plantilla de acta | P-122 declaraba este documento y no existía. Sin él, «una persona aplica la misma rúbrica que el juez» era una intención sin procedimiento: no decía desde qué fichero, ni en qué orden respecto a las notas del modelo, ni dónde se anota el resultado |
