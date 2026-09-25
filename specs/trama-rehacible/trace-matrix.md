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
| REQ-TR-06 | TR-03, TR-08 | CUBIERTO |
| REQ-TR-07 | TR-06, TR-07 | CUBIERTO |
| REQ-TR-08 | TR-01, TR-02, TR-03, TR-04 | CUBIERTO |
| REQ-TR-09 | TR-03, TR-04, TR-05 | CUBIERTO |
| REQ-TR-10 | TR-10, TR-13, TR-14 | CUBIERTO |
| REQ-TR-11 | TR-15 | CUBIERTO |
| REQ-TR-12 | TR-16 | CUBIERTO |
| REQ-TR-13 | TR-17 | CUBIERTO |
| REQ-TR-14 | TR-18 | CUBIERTO |
| REQ-TR-15 | TR-07, TR-19 | CUBIERTO |
| REQ-TR-16 | TR-20 | CUBIERTO |
| REQ-TR-17 | TR-21 | CUBIERTO |
| REQ-TR-18 | TR-22 | CUBIERTO |
| REQ-TR-19 | TR-23 | CUBIERTO |

## 2. Ítem → requisito

| Ítem | Requisitos |
|---|---|
| TR-01 | REQ-TR-02, REQ-TR-08 |
| TR-02 | REQ-TR-08 |
| TR-03 | REQ-TR-06, REQ-TR-08, REQ-TR-09 |
| TR-04 | REQ-TR-08, REQ-TR-09 |
| TR-05 | REQ-TR-09 |
| TR-06 | REQ-TR-07 |
| TR-07 | REQ-TR-07, REQ-TR-15 |
| TR-08 | REQ-TR-06 |
| TR-09 | REQ-TR-05 |
| TR-10 | REQ-TR-10 |
| TR-11 | REQ-TR-02, REQ-TR-04 |
| TR-12 | REQ-TR-01, REQ-TR-03 |
| TR-13 | REQ-TR-10 |
| TR-14 | REQ-TR-10 |
| TR-15 | REQ-TR-11 |
| TR-16 | REQ-TR-12 |
| TR-17 | REQ-TR-13 |
| TR-18 | REQ-TR-14 |
| TR-19 | REQ-TR-15 |
| TR-20 | REQ-TR-16 |
| TR-21 | REQ-TR-17 |
| TR-22 | REQ-TR-18 |
| TR-23 | REQ-TR-19 |

## 3. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-24 | Entran REQ-TR-17 a REQ-TR-19 y TR-21 a TR-23: diecinueve requisitos y veintitrés ítems, sin huecos ni huérfanos, sobre la suite en verde | Se mueve con la spec y el plan |
| 2026-09-24 | Entran REQ-TR-11 a REQ-TR-16 y TR-15 a TR-20; REQ-TR-06 gana TR-03 y REQ-TR-15 gana TR-07. Dieciséis requisitos y veinte ítems, sin huecos ni huérfanos. Los estados CUBIERTO se afirman sobre la suite del backend y del frontend en verde con las pruebas que cita el plan | Se mueve con la spec y el plan |
| 2026-09-24 | Primera versión: diez requisitos y catorce ítems, sin huecos ni huérfanos | Se mueve con la spec y el plan |
