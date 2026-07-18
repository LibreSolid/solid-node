# Architecture Decision Records

This directory is solid-node's decision log. Each ADR records one
architectural decision — its context, the options weighed, and its
consequences — as a **delta** against the architecture that existed
before it. The synthesized current state lives in
[`docs/architecture.md`](../architecture.md); the behavioral contracts
live in [`openspec/specs/`](../../openspec/specs/). Read the synthesis
first, the specs to know exact behavior, and an ADR to know *why* it is
that way.

## Discipline

- **One decision per ADR**, numbered sequentially across all categories,
  filed under the subsystem directory it primarily affects.
- **Statuses:** `Proposed` → `Accepted`; later decisions may mark an ADR
  `Superseded` (with a *Superseded by* link) or amend it in place with a
  dated *Amendment* section. Superseded ADRs stay in the log — they are
  the history that makes later decisions legible.
- **Characterization ADRs** record a decision after the implementation
  landed (marked as such in the preamble). They are legitimate but
  should be the exception: the normal flow is an OpenSpec change
  proposal ratified *before* implementation, with the ADR written
  alongside. When a change is archived into the main specs, any
  architectural shift it carries gets its ADR and, if needed, an update
  to `docs/architecture.md`.
- **Cross-links** are relative paths between category directories, so
  the tree is self-contained wherever it is checked out.

## Index

### NODE — core node tree and lifecycle
- [ADR-001](NODE/ADR-001-composite-pattern-node-tree-architecture.md) — Composite pattern node tree — **Accepted**
- [ADR-002](NODE/ADR-002-template-method-pattern-for-node-lifecycle.md) — Template-method node lifecycle — **Accepted**
- [ADR-003](NODE/ADR-003-rigid-vs-non-rigid-node-distinction.md) — Rigid vs non-rigid distinction — **Accepted**
- [ADR-004](NODE/ADR-004-multi-cad-backend-adapter-pattern.md) — Multi-CAD backend adapters — **Accepted**
- [ADR-006](NODE/ADR-006-mtime-based-stl-caching-strategy.md) — Mtime-based STL caching — **Accepted**, extended by 026/028
- [ADR-008](NODE/ADR-008-time-based-animation-system-for-assemblies.md) — Time-based animation — **Accepted**, extended by 023
- [ADR-023](NODE/ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md) — Kinematic operations, driver-tagged idempotent renders — **Accepted**, extended by 027/028
- [ADR-026](NODE/ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md) — Parameter-hashed artifact keys vs tree names — **Accepted**
- [ADR-028](NODE/ADR-028-cached-base-meshes-and-single-matrix-world-composition.md) — Cached base meshes, single-matrix world composition — **Accepted** (characterization)

### BUILD — loading, watching, CLI
- [ADR-005](BUILD/ADR-005-path-based-dynamic-module-loading.md) — Path-based dynamic module loading — **Accepted**
- [ADR-007](BUILD/ADR-007-watchdog-library-filesystem-monitoring.md) — Watchdog filesystem monitoring — **Accepted**
- [ADR-021](BUILD/ADR-021-snapshot-cli-command-for-agent-autonomy.md) — Snapshot CLI command — **Accepted**
- [ADR-024](BUILD/ADR-024-command-first-cli-grammar-and-duck-typed-command-registry.md) — Command-first CLI grammar — **Accepted**

### IPC — inter-process communication
- [ADR-015](IPC/ADR-015-fastapi-unified-stack-for-http-services.md) — FastAPI + Uvicorn HTTP stack — **Accepted, amended** (broker consumer removed)
- [ADR-016](IPC/ADR-016-websocket-broker-pattern-for-ipc.md) — WebSocket broker — **Superseded** by 018
- [ADR-017](IPC/ADR-017-websocket-global-lock-for-process-synchronization.md) — WebSocket global lock — **Superseded** by 018
- [ADR-018](IPC/ADR-018-lean-framework-separation.md) — Lean framework separation — **Accepted**

### MATH — expression evaluation parity
- [ADR-022](MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md) — Cross-runtime degree-trig parity for `$t` — **Accepted** (documents a known open defect in the export widget evaluator)

### TEST-FRAMEWORK — CAD testing
- [ADR-009](TEST-FRAMEWORK/ADR-009-trimesh-based-mesh-assertions-for-cad-testing.md) — Trimesh mesh assertions — **Accepted**, extended by 025
- [ADR-010](TEST-FRAMEWORK/ADR-010-testcasemixin-pattern-for-embedded-tests.md) — TestCaseMixin embedded tests — **Accepted**
- [ADR-011](TEST-FRAMEWORK/ADR-011-animation-testing-decorators.md) — Animation testing decorators — **Accepted**
- [ADR-025](TEST-FRAMEWORK/ADR-025-perturbation-based-kinematic-fit-assertions.md) — Perturbation-based kinematic fit assertions — **Accepted**, extended by 029
- [ADR-029](TEST-FRAMEWORK/ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md) — Manifold cache, AABB broad-phase — **Accepted** (characterization)

### VIEWER-WEB — web viewer
- [ADR-012](VIEWER-WEB/ADR-012-threejs-for-3d-rendering.md) — Three.js rendering — **Accepted**
- [ADR-013](VIEWER-WEB/ADR-013-react-frontend-framework.md) — React frontend — **Accepted**
- [ADR-014](VIEWER-WEB/ADR-014-recursive-nodeapi-rest-pattern.md) — Recursive NodeAPI REST pattern — **Accepted**
- [ADR-027](VIEWER-WEB/ADR-027-absolute-matrix-composition-for-viewer-transforms.md) — Absolute world-matrix viewer transforms — **Accepted**

### EXPORT — static distribution
- [ADR-020](EXPORT/ADR-020-static-export-and-embeddable-viewer-widget.md) — Static export and embeddable widget — **Accepted**

ADR-019 (the solid-builder agent system) predates the shop and lives
with the agent tooling's own history, not in this framework log.
