# ADR-020: Static Export Channel with Embeddable, React-Free Viewer Widget

**Status:** Accepted
**Date:** 2026-07-17
**Depends on:**
- [ADR-001: Composite Pattern for Node Tree Architecture](../NODE/ADR-001-composite-pattern-node-tree-architecture.md)
- [ADR-003: Rigid vs Non-Rigid Node Distinction](../NODE/ADR-003-rigid-vs-non-rigid-node-distinction.md)
- [ADR-008: Time-Based Animation System for Assemblies](../NODE/ADR-008-time-based-animation-system-for-assemblies.md)

**Related to:**
- [ADR-012: Three.js for 3D Mesh Rendering and Visualization](../VIEWER-WEB/ADR-012-threejs-for-3d-rendering.md)
- [ADR-013: React as Frontend Framework](../VIEWER-WEB/ADR-013-react-frontend-framework.md)
- [ADR-014: Recursive NodeAPI REST Pattern Mirroring Node Tree](../VIEWER-WEB/ADR-014-recursive-nodeapi-rest-pattern.md)

## Context and Problem Statement

The framework's only way to view a model was the live `develop` viewer (ADR-012/013/014): a React single-page app served by a FastAPI `NodeAPI`, backed by a running Builder that watches source files. This is excellent for authoring, but it requires a live Python process and the full CAD stack for anyone who merely wants to *look at* a finished model. There was no way to:

- publish a rendered model to a static host (GitHub Pages, an S3 bucket, a CDN) with no server;
- hand a colleague a self-contained directory that renders in a browser;
- embed a live, orbitable, animatable render inside documentation.

We needed a **distribution/output channel** that produces a self-contained, offline artifact of a node tree -- geometry plus enough structure to reproduce the assembly hierarchy and its animation -- and a way to render and embed that artifact without dragging along the live server or its React application.

The artifact format itself was not a point of contention: mirroring the node tree (the same rigid/non-rigid walk `NodeAPI` already performs) with per-rigid-node STL files is the only design that preserves the assembly hierarchy, per-part colors, and animation that this framework exists to express. The genuine architectural decision was **what renders the artifact and how it gets embedded**: build a new, framework-light viewer, or reuse the existing React viewer application.

## Decision Drivers

- **Offline, serverless distribution:** the output must render on any static file host, with no Python, no FastAPI, no Builder process.
- **Self-containment:** a published directory should carry everything needed to render (manifest, meshes, and optionally the viewer itself).
- **Fidelity with the live viewer:** the same node tree, the same rigid/non-rigid walk (ADR-003/014), the same Z-up orientation, and the same animation semantics (ADR-008) must render identically offline.
- **Embeddability with isolation:** docs and third-party pages must embed a render without CSS/JS collisions or pulling in a heavy framework.
- **Light footprint:** an embed on a docs page cannot justify shipping a full React application; payload and isolation matter.
- **Docs authoring ergonomics:** authors should embed a render with a single directive next to the code that defines the node.

## The Export Artifact (design, not under debate)

`solid export` (CLI in `manager/export.py`, pipeline in `core/export.py`) builds all STLs, then writes an output directory containing:

- **`manifest.json`** -- `{format: "solid-node-export", version: 1, animation: {fps, frames}, root: <tree>}`. The tree is produced by the **same walk as `NodeAPI`** (ADR-014): a rigid node serializes to a single `model` (STL path) and stops the recursion; a non-rigid node recurses into its rendered children. Each node carries `name`, `type`, `color`, and `operations`. Rotations and translations are serialized as **raw OpenSCAD expression strings**, so `$t` animation is preserved verbatim rather than baked into frames.
- **`models/`** -- one STL per distinct rigid artifact, keyed by the STL's path relative to the build dir. This deduplicates identical instances and prevents collisions between same-named scripts in different directories.
- unless `--no-widget`: **`index.html` + `solid-widget.js`**, making the directory a self-contained, embeddable viewer.

The manifest is a versioned public contract (`format`/`version`) rather than a weighed alternative; it is the natural serialization of the existing tree. It is documented here so downstream consumers (the widget and the Sphinx extension) have a single reference.

## Considered Options

The one real decision was the renderer/embedding strategy for the static artifact:

1. **A standalone, React-free Three.js widget** (`viewers/widget/`) that loads the manifest and auto-mounts, embedded in docs via an `<iframe>`.
2. **Reuse the existing React viewer application** as the static renderer.

## Decision Outcome

Chosen option: **a standalone, React-free Three.js widget embedded via `<iframe>`**, because a documentation page or a third-party embed cannot justify shipping a full React application, and an iframe-mounted, framework-light bundle gives strong style/script isolation with a small payload while still reusing the established Three.js rendering decision (ADR-012).

**Renderer.** A new standalone TypeScript bundle under `viewers/widget/`, built by esbuild (`build.mjs`) as a minified IIFE (`globalName: SolidNodeWidget`) that **bundles Three.js and jokenizer and uses no React**. It fetches the manifest, rebuilds the tree as a Three.js `Group` hierarchy (`tree.ts`, Z-up as in OpenSCAD), fits the camera to the actual bounds, and provides orbit controls. Animated models (any operation containing `$t`) get a play/pause button and a timeline slider. Containers carrying a `data-solid-widget="<manifest url>"` attribute auto-mount on load; the page query string (`?t=<0..1>`, `?autoplay=0`) sets the initial pose.

**Embedding.** A Sphinx extension (`sphinx.py`) registers a `.. solid-node:: <export-dir>` directive that emits an `<iframe>` pointing at the export's `index.html`, mapping `:height:`, `:t:` and `:autoplay:` options onto the widget's query string. At `html-collect-pages` it copies referenced exports into `_solid_node/` in the HTML output and, for exports made with `--no-widget`, completes the widget files from the installed package. The extension duplicates the `MANIFEST_FORMAT` constant (asserted equal by tests) so docs can build without importing the CAD stack, and declares itself parallel read/write safe.

The `--no-widget` split lets repositories commit tiny exports (just `manifest.json` + `models/`) and have the viewer completed from the installed package at docs-build time. The prebuilt bundle `dist/solid-widget.js` is **not committed**: source checkouts must `npm install && npm run build` (surfaced by an explicit `WidgetBundleMissing` error), while releases ship the built artifact.

## Pros and Cons of the Options

### Standalone React-free Three.js widget + iframe (chosen)

- Good: small, dependency-light bundle; no React runtime imposed on a docs page or a user's published site.
- Good: iframe embedding guarantees style/script isolation from the host page or docs theme.
- Good: auto-mount + query-string API make embedding trivial and let the Sphinx directive drive a static pose.
- Good: reuses the Three.js rendering decision (ADR-012) and the rigid/non-rigid + `$t` semantics (ADR-003/008/014), so offline output matches the live viewer.
- Good: bundles only MIT dependencies (Three.js, jokenizer) with the license banner retained for redistribution.
- Bad: a second renderer to maintain alongside the React app -- risk of feature drift between the live and static viewers.
- Bad: hand-rolled DOM controls (no component framework) for play/pause and the timeline.

### Reuse the existing React viewer application

- Good: a single rendering codebase, eliminating drift between live and static viewers.
- Bad: a heavy bundle to ship on every docs page or exported directory.
- Bad: the React app is built around the live `NodeAPI` REST shape (ADR-014), not a static manifest fetched from a file host; adapting it would mean carrying server-oriented assumptions into an offline artifact.
- Bad: weaker isolation on a host page without still wrapping it in an iframe anyway, giving up the payload advantage for no isolation gain.

## Consequences

The framework now has two parallel output channels: the **live** viewer (ADR-012/013/014: server + React + `NodeAPI`) for authoring, and the **static** export (this ADR: manifest + STLs + React-free widget) for distribution and embedding. Both walk the node tree with the same rigid/non-rigid rules (ADR-003) and honor the same `$t` animation model (ADR-008), which keeps them visually consistent but establishes a maintenance obligation: geometry and animation semantics must be updated in both renderers together.

The manifest is now a versioned public contract (`format: "solid-node-export"`, `version: 1`) with three consumers -- the exporter, the widget, and the Sphinx extension. Changes to operation serialization or the tree shape are breaking changes that must bump the version and update all consumers.

The prebuilt widget bundle (`dist/solid-widget.js`) is not committed; source checkouts must build it while releases ship the built artifact. This introduces a build-time dependency for anyone exporting *with* the widget from a source checkout, mitigated by the explicit `WidgetBundleMissing` error and the `--no-widget` escape hatch.

The widget evaluates `$t` expressions in the browser (jokenizer + a `Math`-populated context) so that a pose renders identically offline and in Python tests. This mirrors the framework's Python-side animation/`math.py` evaluation and is therefore a **cross-language coupling**: the two evaluators must agree for offline output to match. This ADR only *notes* that dependency; the coupling itself is tracked as a separate gap and will be addressed in its own ADR. It is intentionally out of scope here.

Future work this opens up: additional export targets (glTF/3MF), signed or pinned manifest versions, and possibly converging the two renderers if drift becomes costly.

## References

- `solid_node/core/export.py` -- export pipeline, manifest format, tree serialization, widget copy
- `solid_node/manager/export.py` -- `solid export` CLI (`-o`, `--fps`, `--frames`, `--no-widget`)
- `solid_node/viewers/widget/build.mjs` -- esbuild IIFE bundle, license banner
- `solid_node/viewers/widget/src/widget.ts` -- mount/auto-mount, orbit controls, play/pause + timeline
- `solid_node/viewers/widget/src/tree.ts` -- manifest to Three.js Group hierarchy, per-frame matrix recompute
- `solid_node/viewers/widget/src/evaluator.ts` -- client-side `$t` expression evaluation
- `solid_node/viewers/widget/src/types.ts` -- manifest TypeScript contract
- `solid_node/sphinx.py` -- `.. solid-node::` directive, iframe emission, export copy/completion
- `tests/test_export.py`, `tests/test_sphinx_ext.py`
- Commits: `6dc991c`, `b6cc1be`, `b2bd3c9`, `aef0473`, `492e71e`, `2019d30`
