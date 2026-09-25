# Matriz de trazabilidad — Validación de la novela

Correspondencia entre los requisitos de la [spec](spec.md) y los ítems del [plan](plan.md), en las dos direcciones. La vista consolidada del repositorio sería el [`trace-matrix.md`](../../trace-matrix.md) de la raíz, que no está en el árbol, así que esta mitad todavía no se ha consolidado.

## 1. Requisito → ítem

| Requisito | Ítems | Estado |
|---|---|---|
| REQ-VA-01 | VA-01 | CUBIERTO |
| REQ-VA-02 | VA-01 | CUBIERTO |
| REQ-VA-03 | VA-01 | CUBIERTO |
| REQ-VA-04 | VA-01 | CUBIERTO |
| REQ-VA-05 | VA-02 | CUBIERTO |
| REQ-VA-06 | VA-03 | CUBIERTO |
| REQ-VA-07 | VA-04, VA-05, VA-06 | CUBIERTO |
| REQ-VA-08 | VA-04, VA-07 | CUBIERTO |
| REQ-VA-09 | VA-05, VA-06 | CUBIERTO |
| REQ-VA-10 | VA-02, VA-15, VA-16 | CUBIERTO |
| REQ-VA-11 | VA-08 | CUBIERTO |
| REQ-VA-12 | VA-09, VA-10 | CUBIERTO |
| REQ-VA-13 | VA-09 | CUBIERTO |
| REQ-VA-14 | VA-09, VA-10 | CUBIERTO |
| REQ-VA-15 | VA-11 | GAP |
| REQ-VA-16 | VA-12 | CUBIERTO |
| REQ-VA-17 | VA-13 | CUBIERTO |
| REQ-VA-18 | VA-12, VA-14 | CUBIERTO |
| REQ-VA-19 | VA-17 | CUBIERTO |
| REQ-VA-20 | VA-18, VA-19 | CUBIERTO |
| REQ-VA-21 | VA-20 | CUBIERTO |
| REQ-VA-22 | VA-03, VA-18 | CUBIERTO |

REQ-VA-15 es un GAP porque es una inspección que no se ha hecho: una persona tiene que leer una novela entera y registrar su hoja.

## 2. Ítem → requisito

| Ítem | Requisitos |
|---|---|
| VA-01 | REQ-VA-01, REQ-VA-02, REQ-VA-03, REQ-VA-04 |
| VA-02 | REQ-VA-05, REQ-VA-10 |
| VA-03 | REQ-VA-06, REQ-VA-22 |
| VA-04 | REQ-VA-07, REQ-VA-08 |
| VA-05 | REQ-VA-07, REQ-VA-09 |
| VA-06 | REQ-VA-07, REQ-VA-09 |
| VA-07 | REQ-VA-08 |
| VA-08 | REQ-VA-11 |
| VA-09 | REQ-VA-12, REQ-VA-13, REQ-VA-14 |
| VA-10 | REQ-VA-12, REQ-VA-14 |
| VA-11 | REQ-VA-15 |
| VA-12 | REQ-VA-16, REQ-VA-18 |
| VA-13 | REQ-VA-17 |
| VA-14 | REQ-VA-18 |
| VA-15 | REQ-VA-10 |
| VA-16 | REQ-VA-10 |
| VA-17 | REQ-VA-19 |
| VA-18 | REQ-VA-20, REQ-VA-22 |
| VA-19 | REQ-VA-20 |
| VA-20 | REQ-VA-21 |

## 3. Registro de cambios

| Fecha | Cambio | Motivo |
|---|---|---|
| 2026-09-25 | Primera versión | Nace con la spec y el plan |
