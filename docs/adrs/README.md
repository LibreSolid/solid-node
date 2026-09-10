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
- [ADR-001](NODE/ADR-001-composite-pattern-node-tree-architecture.md) — Composite pattern node tree — **Accepted**, extended by 061
- [ADR-002](NODE/ADR-002-template-method-pattern-for-node-lifecycle.md) — Template-method node lifecycle — **Accepted**, amended by 033, extended by 064
- [ADR-003](NODE/ADR-003-rigid-vs-non-rigid-node-distinction.md) — Rigid vs non-rigid distinction — **Accepted**, amended by 039, third case added by 057, empty boundary defined by 082
- [ADR-004](NODE/ADR-004-multi-cad-backend-adapter-pattern.md) — Multi-CAD backend adapters — **Accepted**, universal target superseded by 046
- [ADR-006](NODE/ADR-006-mtime-based-stl-caching-strategy.md) — Mtime-based STL caching — **Accepted**, extended by 026/028/033, amended by 050/060
- [ADR-008](NODE/ADR-008-time-based-animation-system-for-assemblies.md) — Time-based animation — **Accepted**, extended by 023/072, deferred leaf geometry resolved by 057
- [ADR-023](NODE/ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md) — Kinematic operations, driver-tagged idempotent renders — **Accepted**, extended by 027/028
- [ADR-026](NODE/ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md) — Parameter-hashed artifact keys vs tree names — **Accepted**, extended by 043/063
- [ADR-028](NODE/ADR-028-cached-base-meshes-and-single-matrix-world-composition.md) — Cached base meshes, single-matrix world composition — **Accepted** (characterization), amended by 085
- [ADR-033](NODE/ADR-033-import-closure-source-set-and-up-to-date-leaf-path.md) — Import-closure source set, up-to-date leaf path — **Accepted**, one-node-per-file driver withdrawn by 071
- [ADR-039](NODE/ADR-039-solid-integrity-at-the-topmost-rigid-node.md) — Solid integrity at the topmost rigid node — **Accepted**, amended 2026-08-10
- [ADR-044](NODE/ADR-044-derived-exact-geometry-capability.md) — Derived exact-geometry capability — **Accepted**
- [ADR-045](NODE/ADR-045-exact-fusion-composition.md) — Exact fusion composition — **Accepted**
- [ADR-046](NODE/ADR-046-conditional-openscad-dependency.md) — Conditional OpenSCAD dependency — **Accepted**
- [ADR-047](NODE/ADR-047-shared-occt-currency-for-exact-backends.md) — One shared OCCT currency for every exact backend — **Accepted**, amended 2026-08-22
- [ADR-050](NODE/ADR-050-nanosecond-fidelity-artifact-freshness.md) — Nanosecond-fidelity artifact freshness — **Accepted**
- [ADR-053](NODE/ADR-053-authored-profile-as-the-sheet-part-source-of-truth.md) — Authored profile as a sheet part's source of truth — **Accepted**
- [ADR-054](NODE/ADR-054-imported-meshes-admitted-selected-and-corrected-explicitly.md) — An imported mesh is admitted, selected and corrected explicitly — **Accepted**
- [ADR-055](NODE/ADR-055-wrapper-module-in-the-imported-part-source-set.md) — The wrapper module joins an imported part's tracked source set — **Accepted**
- [ADR-056](NODE/ADR-056-signals-drivers-ports-and-stepped-simulation.md) — Signals, drivers, ports, and stepped simulation — **Proposed** (design draft, pre-OpenSpec), amended 2026-08-27, amended by 087, extended by 088
- [ADR-057](NODE/ADR-057-the-flexible-leaf-and-spec-carried-geometry.md) — The flexible leaf, whose geometry travels as a spec — **Accepted**
- [ADR-058](NODE/ADR-058-indexed-package-lookup-for-source-closures.md) — Indexed package lookup for source closures — **Accepted**
- [ADR-060](NODE/ADR-060-content-verified-currency-beneath-the-mtime-rule.md) — Content-verified currency beneath the mtime rule — **Accepted**, amends 006, amended by 071/081
- [ADR-061](NODE/ADR-061-a-call-in-a-class-body-is-a-declaration.md) — A call in a node class body is a declaration — **Accepted**, extends 001
- [ADR-062](NODE/ADR-062-typed-parameters-and-the-exponent-algebra.md) — Typed parameters and the exponent algebra — **Accepted** *(amended 2026-09-04: the vocabulary lives in `solid_node.parameters`)*
- [ADR-063](NODE/ADR-063-identity-from-resolved-declared-values.md) — Identity from resolved declared values — **Accepted**, extends 026
- [ADR-064](NODE/ADR-064-an-internal-render-that-returns-nothing.md) — An internal render() that returns nothing, and structural omission — **Accepted**, extends 002, extended by 082
- [ADR-065](NODE/ADR-065-instance-checks-after-resolution.md) — Instance checks after resolution: `check()` on a declarative node — **Accepted**, extends 062
- [ADR-066](NODE/ADR-066-render-at-rest-simulate-per-instant.md) — render() builds the machine at rest, simulate() moves it — **Accepted**, extends 002, 023, extended by 088
- [ADR-071](NODE/ADR-071-node-scoped-content-currency.md) — Node-scoped content currency — **Accepted**, amends 060/033, amended by 081
- [ADR-072](NODE/ADR-072-a-declared-time-base.md) — A declared time base: `time = Time(loop=…)`, seconds on every path — **Accepted**, extends 008, amended by 087
- [ADR-077](NODE/ADR-077-declared-tessellation-precision.md) — Declared tessellation precision: `linear_deflection` / `angular_deflection` — **Accepted**, depends on 026/044/045/047/063/071
- [ADR-078](NODE/ADR-078-the-step-part-as-an-exact-external-file-leaf.md) — The STEP part as an exact external-file leaf: `StepNode` — **Accepted**, extends 054/055, depends on 047/050/071/077
- [ADR-079](NODE/ADR-079-reading-a-step-documents-placements-and-scaffolding-source.md) — Reading a STEP document's placements and scaffolding declarative source: `StepAssembly`, `solid import-step` — **Accepted**, extends 078, depends on 077
- [ADR-081](NODE/ADR-081-per-contributor-metadata-guards-aggregate-mtime-currency.md) — Per-contributor metadata guards aggregate-mtime currency — **Accepted**, amends 060/071, depends on 033/050
- [ADR-082](NODE/ADR-082-empty-composition-belongs-to-assemblies-not-fusions.md) — Empty composition belongs to assemblies, not fusions — **Accepted**, extends 064, depends on 003/039/061
- [ADR-083](NODE/ADR-083-simulation-time-is-finite-forward-and-tick-aligned.md) — Simulation time is finite, forward, and tick-aligned — **Accepted**, extends 056
- [ADR-087](NODE/ADR-087-one-module-one-question.md) — One module, one question: ports and the declared time base move to `solid_node.motion.ports` — **Accepted**, amends 056/072 (export location only)
- [ADR-088](NODE/ADR-088-a-joint-owns-one-coordinate.md) — A joint owns one coordinate: `Revolute` and `Prismatic`, stated in the parent's frame — **Accepted**, extends 056/066, depends on 023/028/061/063/087
- [ADR-089](NODE/ADR-089-drives-relates-two-coordinates.md) — `drives` relates two coordinates: one verb, a law passed in, and a solve oriented from the bound side — **Accepted**, extends 061/066, depends on 022/056/076/080/087/088

### BUILD — loading, watching, CLI
- [ADR-005](BUILD/ADR-005-path-based-dynamic-module-loading.md) — Path-based dynamic module loading — **Accepted**, amended by 073
- [ADR-007](BUILD/ADR-007-watchdog-library-filesystem-monitoring.md) — Watchdog filesystem monitoring — **Accepted**
- [ADR-021](BUILD/ADR-021-snapshot-cli-command-for-agent-autonomy.md) — Snapshot CLI command — **Accepted**, amended by 041
- [ADR-024](BUILD/ADR-024-command-first-cli-grammar-and-duck-typed-command-registry.md) — Command-first CLI grammar — **Accepted**, amended by 073
- [ADR-030](BUILD/ADR-030-complete-build-publication-boundary.md) — Complete-build publication boundary — **Reversed** by 038
- [ADR-031](BUILD/ADR-031-published-viewer-snapshot.md) — Published viewer snapshot — **Accepted**, amended by 034
- [ADR-032](BUILD/ADR-032-symlink-swap-build-publication.md) — Symlink-swap build publication — **Superseded** by 038
- [ADR-038](BUILD/ADR-038-per-artifact-atomic-build-publication.md) — Per-artifact atomic build publication — **Accepted**, amended by 073, extended by 086
- [ADR-041](BUILD/ADR-041-browser-rendered-transparent-snapshots.md) — Browser-rendered transparent snapshots — **Accepted**
- [ADR-059](BUILD/ADR-059-import-at-the-point-of-use.md) — Import at the point of use — **Accepted**, extends 024, extended by 069
- [ADR-067](BUILD/ADR-067-fresh-interpreter-build-subprocesses.md) — Fresh-interpreter build subprocesses — **Accepted**, amended by 084
- [ADR-069](BUILD/ADR-069-deferred-callables-for-a-modules-own-call-sites.md) — Deferred callables for a module's own call sites — **Accepted**, extends 059
- [ADR-073](BUILD/ADR-073-named-project-models-and-per-model-build-directories.md) — Named project models and per-model build directories — **Accepted**, amends 005, 024, 038
- [ADR-084](BUILD/ADR-084-one-fresh-builder-per-sealed-source-generation.md) — One fresh builder per sealed source generation — **Accepted**, amends 067
- [ADR-086](BUILD/ADR-086-state-dependent-scad-publishes-at-assembly-phase-completion.md) — State-dependent SCAD publishes at assembly phase completion — **Accepted**, extends 038

### IPC — inter-process communication
- [ADR-015](IPC/ADR-015-fastapi-unified-stack-for-http-services.md) — FastAPI + Uvicorn HTTP stack — **Accepted, amended** (broker consumer removed)
- [ADR-016](IPC/ADR-016-websocket-broker-pattern-for-ipc.md) — WebSocket broker — **Superseded** by 018
- [ADR-017](IPC/ADR-017-websocket-global-lock-for-process-synchronization.md) — WebSocket global lock — **Superseded** by 018
- [ADR-018](IPC/ADR-018-lean-framework-separation.md) — Lean framework separation — **Accepted**

### MATH — expression evaluation parity
- [ADR-022](MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md) — Cross-runtime degree-trig parity for `$t` and driver expressions — **Accepted**, revised 2026-09-06 (defect fixed and parity enforced 2026-08-26; vocabulary widened beyond trigonometry, and the corpus must cover every emitted name)
- [ADR-076](MATH/ADR-076-mechanism-laws-as-compositions-over-expression-math.md) — Mechanism laws as compositions over expression math — **Accepted**, depends on 022

### TEST-FRAMEWORK — CAD testing
- [ADR-009](TEST-FRAMEWORK/ADR-009-trimesh-based-mesh-assertions-for-cad-testing.md) — Trimesh mesh assertions — **Accepted**, extended by 025
- [ADR-010](TEST-FRAMEWORK/ADR-010-testcasemixin-pattern-for-embedded-tests.md) — TestCaseMixin embedded tests — **Accepted**
- [ADR-011](TEST-FRAMEWORK/ADR-011-animation-testing-decorators.md) — Animation testing decorators — **Accepted**
- [ADR-025](TEST-FRAMEWORK/ADR-025-perturbation-based-kinematic-fit-assertions.md) — Perturbation-based kinematic fit assertions — **Accepted**, extended by 029, adjacency guidance superseded by 040
- [ADR-029](TEST-FRAMEWORK/ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md) — Manifold cache, AABB broad-phase — **Accepted** (characterization), extended by 070, 091
- [ADR-040](TEST-FRAMEWORK/ADR-040-topmost-rigid-assembly-integrity.md) — Topmost-rigid assembly integrity — **Accepted**, revised 2026-08-11 (volume certificate removed)
- [ADR-048](TEST-FRAMEWORK/ADR-048-gravity-support-graph-assertion.md) — Gravity support graph assertion — **Accepted**, extended by 049
- [ADR-049](TEST-FRAMEWORK/ADR-049-static-equilibrium-as-lp-feasibility.md) — Static equilibrium as LP feasibility — **Accepted**
- [ADR-052](TEST-FRAMEWORK/ADR-052-conditional-mesh-engine-dependency.md) — Conditional mesh-engine dependency — **Accepted**
- [ADR-070](TEST-FRAMEWORK/ADR-070-relative-placement-as-the-identity-of-an-intersection-question.md) — Relative placement as the identity of an intersection question — **Accepted**, extends 029, amended by 090
- [ADR-073](TEST-FRAMEWORK/ADR-073-the-comparison-kernel-is-a-property-of-the-test-run.md) — The comparison kernel is a property of the test run — **Accepted**, extends 044, 029
- [ADR-074](TEST-FRAMEWORK/ADR-074-the-mesh-engine-judges-its-own-input.md) — The mesh engine judges its own input — **Accepted**, amends 029
- [ADR-075](TEST-FRAMEWORK/ADR-075-the-perturbation-is-the-nodes-first-operation.md) — The perturbation is the node's first operation — **Accepted**, amends 025
- [ADR-090](TEST-FRAMEWORK/ADR-090-the-placement-quantum-is-a-property-of-the-test-run.md) — The placement quantum is a property of the test run — **Accepted**, amends 070
- [ADR-091](TEST-FRAMEWORK/ADR-091-the-broad-phase-chooses-its-indexing-frame.md) — The broad phase chooses its indexing frame — **Accepted**, extends 029

### VIEWER-WEB — web viewer
- [ADR-012](VIEWER-WEB/ADR-012-threejs-for-3d-rendering.md) — Three.js rendering — **Accepted** — *Relocated* to solid-node-viewer (ADR-068)
- [ADR-013](VIEWER-WEB/ADR-013-react-frontend-framework.md) — React frontend — **Accepted**, amended by 036 — *Relocated* to solid-node-viewer (ADR-068)
- [ADR-014](VIEWER-WEB/ADR-014-recursive-nodeapi-rest-pattern.md) — Recursive NodeAPI REST pattern — **Superseded** by 036 — *Relocated* to solid-node-viewer (ADR-068)
- [ADR-027](VIEWER-WEB/ADR-027-absolute-matrix-composition-for-viewer-transforms.md) — Absolute world-matrix viewer transforms — **Superseded** by 036 — *Relocated* to solid-node-viewer (ADR-068)
- [ADR-036](VIEWER-WEB/ADR-036-snapshot-served-shared-viewer-shell.md) — Snapshot-served shared viewer shell — **Accepted** — *Relocated* to solid-node-viewer (ADR-068)
- [ADR-037](VIEWER-WEB/ADR-037-targeted-in-place-viewer-updates.md) — Targeted in-place viewer updates — **Accepted** — *Relocated* to solid-node-viewer (ADR-068)

### EXPORT — static distribution
- [ADR-068](EXPORT/ADR-068-optional-viewer-package-behind-a-process-boundary.md) — Optional viewer package behind a process boundary — **Accepted**, amends 020, 035, 036, 041
- [ADR-020](EXPORT/ADR-020-static-export-and-embeddable-viewer-widget.md) — Static export and embeddable widget — **Accepted** — *Relocated* to solid-node-viewer (ADR-068)
- [ADR-034](EXPORT/ADR-034-shared-node-tree-document-schema.md) — Shared node-tree document schema across export and build snapshots — **Accepted**, amended by 051
- [ADR-035](EXPORT/ADR-035-reusable-viewer-core-and-declared-api.md) — Reusable viewer core and declared API version — **Accepted** — *Relocated* to solid-node-viewer (ADR-068)
- [ADR-042](EXPORT/ADR-042-host-controlled-viewer-assembly-navigation.md) — Host-controlled viewer assembly navigation — **Accepted** — *Relocated* to solid-node-viewer (ADR-068)
- [ADR-043](EXPORT/ADR-043-content-derived-printed-piece-identity.md) — Content-derived printed-piece identity — **Accepted**, amended by 085
- [ADR-051](EXPORT/ADR-051-producer-owned-animation-time-in-node-documents.md) — Producer-owned animation time in node-tree documents — **Accepted**
- [ADR-080](EXPORT/ADR-080-a-shared-subexpression-is-named-once.md) — A shared subexpression is named once: the document's `bindings` table — **Accepted**, extends 034, depends on 022/051
- [ADR-085](EXPORT/ADR-085-persistent-piece-facts-behind-a-verified-artifact-snapshot.md) — Persistent piece facts behind a verified artifact snapshot — **Accepted**, amends 043/028

ADR-019 (the solid-builder agent system) predates the shop and lives
with the agent tooling's own history, not in this framework log.
