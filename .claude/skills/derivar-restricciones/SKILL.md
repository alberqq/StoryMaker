---
name: derivar-restricciones
description: Como convertir una afirmacion historica en regla comprobable sobre un texto, sus cinco categorias y el criterio para declararla cualitativa. Cargala al derivar Restricciones de epoca.
---

# Derivar Restricciones de epoca

El Contexto historico describe. Una Restriccion **decide**. Entre una cosa y otra
hay un salto que conviene dar con cuidado, porque una Restriccion mal enunciada o
censura la novela por nada, o no detecta el anacronismo que existia para detectar.

## La pregunta que separa lo comprobable de lo cualitativo

> Dado un texto cualquiera, se puede decidir sin juicio si lo cumple?

Si la respuesta es si, es **comprobable**. Si es no, es **cualitativa**, y se declara
como tal sin reparos: la mitad de lo que importa de una epoca no es comprobable.

| Enunciado | Veredicto |
|---|---|
| "No aparece el termino *boligrafo*" | Comprobable: el termino esta o no esta |
| "No aparecen relojes de pulsera" | Comprobable, con la lista de terminos |
| "Los personajes no razonan sobre derechos individuales" | Cualitativa: hay que leerlo |
| "El dinero se cuenta en maravedis, no en pesetas" | Comprobable |
| "La muerte se trata sin la distancia higienica moderna" | Cualitativa |

Una Restriccion comprobable **enuncia sobre el texto**, no sobre el mundo. "No
existia el boligrafo" es una afirmacion; "no aparece el termino *boligrafo*" es una
Restriccion.

## Las cinco categorias

| Categoria | Que delimita | Tipico enunciado |
|---|---|---|
| `lexica` | Que palabras pueden aparecer | Terminos prohibidos, con su lista |
| `material` | Que objetos y materiales existen | Un objeto ausente del periodo |
| `tecnologica` | Que procedimientos son posibles | Una tecnica no disponible |
| `institucional` | Que instituciones y cargos existen | Un organismo aun no fundado |
| `mentalidad` | Como se piensa y se siente | Casi siempre cualitativa |

Las `lexica` son las unicas que el nucleo barre automaticamente por capitulo, y por
eso **una lexica comprobable debe declarar sus terminos prohibidos**. Sin terminos
no es comprobable sobre un texto, y el nucleo la rechazara.

## La puerta de MD-7

Una Restriccion **comprobable** solo puede derivar de una afirmacion que cumple las
dos cosas:

- Su fidelidad esta `verificada`: la fuente dice lo que se le atribuye (RF-100).
- Su veredicto de refutacion es `confirmada` o `matizada` (RF-102).

Una afirmacion `refutada`, `disputada` o `no_refutable_documentalmente` no puede
sostener una Restriccion comprobable. Como mucho, un criterio cualitativo.

Esto no es burocracia. Una cita que no dice lo que se le atribuye contamina **todo
lo que se valide contra ella**: si una Restriccion falsa prohibe un termino que si
existia, cada aparicion legitima se convierte en un hallazgo bloqueante y el bucle
no converge nunca.

## Severidad del incumplimiento

Por defecto, `bloqueante`: un anacronismo impide cerrar la unidad. Baja a `mayor`
cuando el incumplimiento sea discutible -- un termino atestado pero raro, un objeto
documentado en otra region -- y deja constancia de por que.

## Revocar

Una Restriccion se revoca con justificacion registrada; **nunca se borra**. La
revocacion se anexa, y el libro conserva por que se derivo y por que dejo de valer.

```
storymaker --proyecto <prj> contexto restriccion \
  --enunciado "No aparece el termino 'boligrafo'" \
  --categoria lexica --afirmacion <aff> --termino boligrafo --termino boli
```
