# Matriz de trazabilidad — La Escritura que no se atasca

Correspondencia entre los requisitos de la [spec](spec.md) y los ítems del [plan](plan.md), en las dos direcciones.

## 1. Requisito → ítem

| Requisito | Ítems | Estado |
|---|---|---|
| REQ-ES-01 | ES-01 | CUBIERTO |
| REQ-ES-02 | ES-02 | CUBIERTO |
| REQ-ES-03 | ES-03, ES-05 | CUBIERTO |
| REQ-ES-04 | ES-04 | CUBIERTO |
| REQ-ES-05 | ES-03, ES-06 | CUBIERTO |
| REQ-ES-06 | ES-07 | CUBIERTO |
| REQ-ES-07 | ES-08 | CUBIERTO |
| REQ-ES-08 | ES-09, ES-10, ES-12 | CUBIERTO |
| REQ-ES-09 | ES-11 | CUBIERTO |
| REQ-ES-10 | ES-11 | CUBIERTO |
| REQ-ES-11 | ES-11 | CUBIERTO |
| REQ-ES-12 | ES-09, ES-12 | CUBIERTO |
| REQ-ES-13 | ES-13 | CUBIERTO |
| REQ-ES-14 | ES-13 | CUBIERTO |
| REQ-ES-15 | ES-14 | CUBIERTO |

## 2. Ítem → requisito

| Ítem | Requisitos |
|---|---|
| ES-01 | REQ-ES-01 |
| ES-02 | REQ-ES-02 |
| ES-03 | REQ-ES-03, REQ-ES-05 |
| ES-04 | REQ-ES-04 |
| ES-05 | REQ-ES-03 |
| ES-06 | REQ-ES-05 |
| ES-07 | REQ-ES-06 |
| ES-08 | REQ-ES-07 |
| ES-09 | REQ-ES-08, REQ-ES-12 |
| ES-10 | REQ-ES-08 |
| ES-11 | REQ-ES-09, REQ-ES-10, REQ-ES-11 |
| ES-12 | REQ-ES-08, REQ-ES-12 |
| ES-13 | REQ-ES-13, REQ-ES-14 |
| ES-14 | REQ-ES-15 |

## 3. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | Entran REQ-ES-13 a REQ-ES-15 e ítems ES-13 y ES-14. CUBIERTO sobre `test_valor_retirado.py` y `test_regeneracion.py` en verde | Se mueve con la spec y el plan |
| 2026-09-25 | Entran REQ-ES-08 a REQ-ES-12 e ítems ES-09 a ES-12, sin huecos ni huérfanos. CUBIERTO sobre las seis pruebas de `test_regeneracion.py` en verde | Se mueve con la spec y el plan |
| 2026-09-24 | Primera versión: siete requisitos y ocho ítems, sin huecos ni huérfanos. Los estados CUBIERTO se afirman sobre la suite del backend en verde con las pruebas que cita el plan | Se mueve con la spec y el plan |
