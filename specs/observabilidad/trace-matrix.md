# Matriz de trazabilidad — La traza de una generación en Langfuse

Correspondencia entre los requisitos de la [spec](spec.md) y los ítems del [plan](plan.md), en las dos direcciones. La vista consolidada del repositorio sería el `trace-matrix.md` de la raíz, que no está en el árbol, así que esta mitad todavía no se ha consolidado.

## 1. Requisito → ítem

| Requisito | Ítems | Estado |
|---|---|---|
| REQ-OB-01 | OB-04 | CUBIERTO |
| REQ-OB-02 | OB-10 | CUBIERTO |
| REQ-OB-03 | OB-06 | CUBIERTO |
| REQ-OB-04 | OB-03, OB-05 | CUBIERTO |
| REQ-OB-05 | OB-05 | CUBIERTO |
| REQ-OB-06 | OB-06 | CUBIERTO |
| REQ-OB-07 | OB-02 | CUBIERTO |
| REQ-OB-08 | OB-01 | CUBIERTO |
| REQ-OB-09 | OB-07 | CUBIERTO |
| REQ-OB-10 | OB-08 | CUBIERTO |
| REQ-OB-11 | OB-09 | CUBIERTO |
| REQ-OB-12 | OB-09 | CUBIERTO |
| REQ-OB-13 | OB-11 | CUBIERTO |
| REQ-OB-14 | OB-12 | GAP |

REQ-OB-14 es un GAP porque es una demostración que no se ha hecho: falta correr una novela con claves de Langfuse y mirar su sesión.

## 2. Ítem → requisito

| Ítem | Requisitos |
|---|---|
| OB-01 | REQ-OB-08 |
| OB-02 | REQ-OB-07 |
| OB-03 | REQ-OB-04 |
| OB-04 | REQ-OB-01 |
| OB-05 | REQ-OB-04, REQ-OB-05 |
| OB-06 | REQ-OB-03, REQ-OB-06 |
| OB-07 | REQ-OB-09 |
| OB-08 | REQ-OB-10 |
| OB-09 | REQ-OB-11, REQ-OB-12 |
| OB-10 | REQ-OB-02 |
| OB-11 | REQ-OB-13 |
| OB-12 | REQ-OB-14 |
