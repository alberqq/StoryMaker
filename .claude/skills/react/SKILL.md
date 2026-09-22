---
name: react
description: General conventions for a React interface that surfaces the state of a backend-owned system — translating internal state into the user's own vocabulary, treating the backend as the single source of truth instead of caching a local copy, and showing backend errors verbatim instead of a generic message. Use this skill whenever creating or touching a component, hook, piece of state, or how the interface queries its backend — even if the request just says "add a screen" or "show this in the UI".
---

# React

The interface exists so its user understands what the system is doing, not to expose the system's internal machinery. Before adding a component, the question isn't "what data do I have available" but "what does the user actually need to know right now".

## The interface explains itself

Any control the user won't understand or won't use is dead weight. Every component that shows system state translates it into the user's own vocabulary — the domain terms the rest of the product and its docs use — not the internal vocabulary of the backend (raw JSON, an internal envelope format, table/column names). If the raw detail is genuinely needed for debugging, that's a separate view, not the default one.

## The backend is the source of truth

State lives on the backend — the frontend doesn't cache it as if it owned it:

- Use polling or SSE against a status endpoint to reflect what's actually running, instead of local state that can drift out of sync the moment something changes while the tab is in the background.
- Before offering any action that depends on nothing being in flight (restart, relaunch, clear), check the real state against the backend at that moment — don't assume it's free because it was the last time it was checked. Assuming instead of checking is the same mistake, on the frontend, as an operator restarting a server that's mid-task because they didn't check first.

## Errors: show, don't translate

When the backend returns a rejection from its underlying core, show it as-is — the real reason the system gave — instead of replacing it with a generic message ("something went wrong") or silently retrying. The specific reason is what lets the user decide what to do next; a generic message takes that away from them.

## Match validation effort to what can actually happen

Don't add validation, error handling, or loading states for cases that can't occur given who's actually using this and how. Prioritize the flow reaching end-to-end without getting stuck over polishing every edge — surface cosmetic issues you notice, but don't turn each one into a blocker, especially early in a project.

---

Cómo se aplica esto en StoryMaker (el vocabulario del Autor, qué pantallas existen — Proyectos, Ejecuciones, bandeja de excepciones): `docs/architecture.md` y `AGENTS.md`, y la skill `fastapi`.
