# Matriz de trazabilidad — La Trama que se puede rehacer

Correspondencia entre los requisitos de la [spec](spec.md) y los ítems del [plan](plan.md), en las dos direcciones. La vista consolidada de todo el repositorio está en [`trace-matrix.md`](../../trace-matrix.md) de la raíz.

## 1. Requisito → ítem

| Requisito | Ítems | Estado |
|---|---|---|
| REQ-TR-01 | TR-12 | CUBIERTO |
| REQ-TR-02 | TR-01, TR-11 | CUBIERTO |
| REQ-TR-03 | TR-12 | CUBIERTO |
| REQ-TR-04 | TR-11 | CUBIERTO |
| REQ-TR-05 | TR-09 | CUBIERTO |
| REQ-TR-06 | TR-08 | CUBIERTO |
| REQ-TR-07 | TR-06, TR-07 | CUBIERTO |
| REQ-TR-08 | TR-01, TR-02, TR-03, TR-04 | CUBIERTO |
| REQ-TR-09 | TR-03, TR-04, TR-05 | CUBIERTO |
| REQ-TR-10 | TR-10, TR-13, TR-14 | CUBIERTO |

## 2. Ítem → requisito

| Ítem | Requisitos |
|---|---|
| TR-01 | REQ-TR-02, REQ-TR-08 |
| TR-02 | REQ-TR-08 |
| TR-03 | REQ-TR-08, REQ-TR-09 |
| TR-04 | REQ-TR-08, REQ-TR-09 |
| TR-05 | REQ-TR-09 |
| TR-06 | REQ-TR-07 |
| TR-07 | REQ-TR-07 |
| TR-08 | REQ-TR-06 |
| TR-09 | REQ-TR-05 |
| TR-10 | REQ-TR-10 |
| TR-11 | REQ-TR-02, REQ-TR-04 |
| TR-12 | REQ-TR-01, REQ-TR-03 |
| TR-13 | REQ-TR-10 |
| TR-14 | REQ-TR-10 |

## 3. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | Primera versión: diez requisitos y catorce ítems, sin huecos ni huérfanos | Se mueve con la spec y el plan |
