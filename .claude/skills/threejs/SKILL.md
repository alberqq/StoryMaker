---
name: threejs
description: General conventions for the Three.js layer of a frontend that visualizes server-owned state (React integration via react-three-fiber, GPU resource disposal, keeping the 3D scene a projection of backend state rather than its own source of truth, and measured performance work). Use this skill whenever creating or touching a 3D scene, geometry, material, camera, render loop, or how Three.js integrates inside a React component — even if the request just says "visualize this" or "add a 3D view".
---

# Three.js

When Three.js renders a visualization of state that lives elsewhere (a database, a backend) and changes while something else is running in the background, that provenance drives more decisions than the rendering itself.

## Integration with React

- Use react-three-fiber instead of mounting a raw Three.js canvas by hand inside a React component. Mixing React's lifecycle (mount/unmount, changing props) with a hand-managed `requestAnimationFrame` is the most common source of memory leaks and duplicate renders.
- One renderer and one scene per view, not one per component. If a visualization has many pieces, a single scene that updates is cheaper than many `WebGLRenderer`s competing for the GPU.

## Memory

Every geometry, material, or texture created lives on the GPU, not on the JS heap — React/JS garbage collection doesn't free it. When unmounting a component or replacing a scene object, explicitly call `.dispose()` on whatever is no longer used. This matters most in views that refresh repeatedly as backend state changes — without dispose, every refresh leaves residue behind.

## The backend is the source of truth, not the scene

The state being drawn lives on the backend and arrives via fetch/polling/SSE. The 3D scene is a projection of that state, not a copy with a life of its own:

- Separate the data (what the fetch/polling brings back) from the representation (how it's translated into 3D objects), so the view can update without rebuilding the whole scene on every refresh.
- Don't let the frontend keep its own notion of "in progress" or "done" — always defer to the backend. Assuming state instead of checking it is the same mistake, on the frontend, as an operator assuming nothing is running and restarting a server that's mid-task: the real state lives somewhere other than what's being assumed.

## Performance, with restraint

If the object count grows (hundreds or thousands of entities), instancing or LOD beats a mesh per entity before the view gets heavy. But don't optimize ahead of need — get the view working and accurately reflecting real state first; only reach for these once an actual dataset makes it necessary.

---

Cómo se aplica esto en StoryMaker (qué estado concreto se visualiza, de dónde llega): `docs/architecture.md`, secciones 4 y 9, y la skill `fastapi`.
