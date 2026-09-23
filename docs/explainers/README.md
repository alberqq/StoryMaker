# Explainers

Un documento por **concepto del curso**, contado desde cómo se aplica en StoryMaker. No repiten la arquitectura: la arquitectura dice *qué se decidió*, y estos dicen *qué es eso y por qué aquí se hace así*.

Se leen sueltos y en cualquier orden. Si solo vas a leer uno, que sea [`validadores.md`](validadores.md): la decisión de que los validadores sean nodos del grafo es de la que cuelga todo lo demás.

| Explainer | Concepto | La idea en una línea |
|---|---|---|
| [`harness-y-orquestacion.md`](harness-y-orquestacion.md) | Harness multiagente | Nueve roles que no se eligen unos a otros: los cablea un grafo |
| [`memoria-y-contexto.md`](memoria-y-contexto.md) | Memoria y gestión de contexto | El agente recibe su contexto, no lo busca |
| [`validadores.md`](validadores.md) | Validación programática y semántica | Lo que un modelo puede olvidarse de llamar no es una comprobación |
| [`verificacion-formal.md`](verificacion-formal.md) | Lean 4 y TLA+ | Dos verificaciones distintas: la historia y el sistema |
| [`guardrails-y-policy.md`](guardrails-y-policy.md) | Guardrails | Prohibir una palabra es fácil; prohibirla en todas sus formas es el trabajo |
| [`observabilidad.md`](observabilidad.md) | Trazas, scores y costes | Si el que optimiza la métrica es el que la produce, la métrica no vale |
| [`evals.md`](evals.md) | Evaluación de sistemas no deterministas | Cinco briefs que no se eligieron por representativos, sino por incómodos |
| [`mcp-y-claude-code.md`](mcp-y-claude-code.md) | MCP, skills y hooks | Dónde acaba el arnés y empieza la herramienta de quien lo desarrolla |
