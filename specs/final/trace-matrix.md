# Matriz de trazabilidad — Cierre del arnés

Correspondencia entre los requisitos de la [spec](spec.md) y los ítems del [plan](plan.md), en las dos direcciones. La vista consolidada del repositorio sería el [`trace-matrix.md`](../../trace-matrix.md) de la raíz, que no está en el árbol, así que esta mitad todavía no se ha consolidado.

## 1. Requisito → ítem

| Requisito | Ítems | Estado |
|---|---|---|
| REQ-FI-01 | FI-01 | CUBIERTO |
| REQ-FI-02 | FI-01 | CUBIERTO |
| REQ-FI-03 | FI-01 | CUBIERTO |
| REQ-FI-04 | FI-02 | CUBIERTO |
| REQ-FI-05 | FI-02 | CUBIERTO |
| REQ-FI-06 | FI-03 | CUBIERTO |
| REQ-FI-07 | FI-04 | CUBIERTO |
| REQ-FI-08 | FI-05, FI-06 | CUBIERTO |
| REQ-FI-09 | FI-04 | CUBIERTO |
| REQ-FI-10 | FI-07, FI-09 | CUBIERTO |
| REQ-FI-11 | FI-08 | CUBIERTO |
| REQ-FI-12 | FI-07 | CUBIERTO |
| REQ-FI-13 | FI-10 | CUBIERTO |

REQ-FI-13 se cubrió por demostración: la sesión `prueba-langfuse` de Langfuse Cloud da los mismos tokens y el mismo coste que `storymaker estado`.

## 2. Ítem → requisito

| Ítem | Requisitos |
|---|---|
| FI-01 | REQ-FI-01, REQ-FI-02, REQ-FI-03 |
| FI-02 | REQ-FI-04, REQ-FI-05 |
| FI-03 | REQ-FI-06 |
| FI-04 | REQ-FI-07, REQ-FI-09 |
| FI-05 | REQ-FI-08 |
| FI-06 | REQ-FI-08 |
| FI-07 | REQ-FI-10, REQ-FI-12 |
| FI-08 | REQ-FI-11 |
| FI-09 | REQ-FI-10 |
| FI-10 | REQ-FI-13 |

No hay ítems huérfanos.
