---
name: fastapi
description: General conventions for a FastAPI backend that wraps a separate core library or CLI instead of reimplementing its logic — safe process invocation, validation at the boundary, error propagation, streaming long-running operations, and keeping the exposed surface narrower than the core. Use this skill whenever creating or touching a router, endpoint, Pydantic model, dependency or middleware, or deciding how an endpoint should fail and respond — even if the request doesn't say "FastAPI" explicitly.
---

# FastAPI

A backend that fronts a separate core library or CLI is a thin wrapper, not a reimplementation. Business logic — what counts as valid, how a change gets applied, what constitutes a rejection — lives in the core, not in the endpoints. An endpoint that validates, computes, or decides something the core already decides is duplicated logic that can drift out of sync.

## Invoke the core, don't reimplement it

- Invoke the core by argument list, never through a shell (`subprocess.run(["tool", "verb", ...], shell=False)`). Nothing that arrives from an HTTP client gets interpolated into a string someone else will parse.
- Whitelist which core verbs each endpoint may trigger. An endpoint isn't a generic pass-through for "run this core command"; each route maps to one specific, closed verb, the same way the core itself exposes closed verbs instead of raw access.
- Return the core's response envelope as-is, errors included. If the core rejects an operation, the endpoint doesn't paper over it, doesn't translate it into a generic message, and doesn't silently retry through another path: it propagates the rejection.
- The backend never writes to the underlying store directly, nor bypasses the core "just this once" for convenience. If an endpoint needs something the core doesn't expose, that's a missing verb in the core, not a shortcut in the backend.

## Models and validation

- Use typed request/response models (Pydantic), not loose dicts — but shape validation at the HTTP boundary is not a second copy of the core's business rules. Trust the core to reject what shouldn't pass.
- Don't validate or handle cases that can't occur given the actual deployment (e.g. a single-user local tool doesn't need multi-tenant edge-case handling). Match the validation effort to what can really happen, not to a hypothetical audience.

## Long-running operations and in-memory state

- If the backend keeps in-memory state about what's running (in progress, waiting on the user), that state is lost if the process restarts — there's no way to recover it unless it was also persisted. Any endpoint or operator action that restarts the server should check first whether something is in flight.
- Long-running operations don't fit a single request-response cycle: expose their progress via Server-Sent Events or a polling status endpoint, so the frontend can reflect real state instead of guessing.

## Surface and scope

- For a single-user local tool, bind to localhost only — don't add auth, open CORS, or anything meant for network exposure unless that's explicitly the goal.
- Keep the API surface narrower than the core, not a shortcut around it: if a core verb doesn't make sense exposed over HTTP, don't expose it.

---

Cómo se aplica esto en StoryMaker (qué es "el núcleo", qué verbos expone el CLI `nh`, el patrón de un solo escritor): `docs/architecture.md`, secciones 3 y 8. El caso concreto de estado en memoria perdido al reiniciar el servidor no está todavía recogido en `docs/` — solo en memoria de sesión; pendiente de trasladar.
