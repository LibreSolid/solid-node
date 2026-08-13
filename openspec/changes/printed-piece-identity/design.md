## Context

Three producers write the shared versioned tree document today: the builder
(`viewer.json`), the exporter (`manifest.json`), and the browser snapshot
renderer. All three call `serialize_node(node, model_path)` and supply their own
model-path mapper, which is what keeps one tree walk while letting each producer
root its models differently.

Node identity in the tree is `uniq_id` (ADR-026): sha256 of
`<class __qualname__>,<args>,<sorted kwargs>`. It is the build-cache key — a
parameter change must invalidate an artifact — and it is deliberately nominal.
Placement (`rotate`/`translate`) is applied outside the artifact, so a part
placed many ways already shares one STL. That is why the artifact key gets
v8-engine exactly right (119 instances → 24 artifacts, all byte-distinct) and
gets gearbox wrong (24 artifacts → 18 distinct geometries): factoring one shape
into six classes yields six keys for one printed piece.

The originating requirement is the shop's Build area
(`solid-node-studio/docs/design/build`), which presents a plate of pieces with
per-piece quantity, source, dimensions, and bed-fit findings.

## Goals / Non-Goals

**Goals:**

- One geometry-derived answer to "is this the same thing to print?", available
  to any consumer of a published document without loading a single mesh.
- Per-piece facts sufficient to lay out a print job: extents, volume,
  watertightness, count, source provenance.
- One implementation shared by all three producers, keeping the single tree
  walk.
- No change to caching, artifact keys, or any existing published field.

**Non-Goals:**

- Replacing or weakening `uniq_id`. Artifact identity and piece identity answer
  different questions and both stay.
- Recognising two meshes as "the same shape" across differing facet output
  (tessellation, vertex order, floating-point drift). See Risks.
- Print-layout policy: nesting, orientation, bed sizes, slicer settings, or
  material. The framework publishes facts; the layout consumer decides.
- A CLI surface for pieces. Add one only when a caller needs it.

## Decisions

**Identity is the sha256 of the built STL's bytes, truncated to 12 hex digits.**

The question being answered is about geometry, not code structure, and the
built artifact *is* the geometry the printer receives. Byte hashing is exact,
cheap, order-independent, and needs no tolerance parameter. Empirically it
already fires: the six gearbox bushings and the two housing walls are
byte-identical files today, so the same OpenSCAD input reliably produces the
same bytes.

Alternatives considered:

- *Keep `uniq_id`.* Rejected: demonstrably under-merges (gearbox), and widening
  it to ignore non-geometric parameters would require the framework to know
  which parameters affect shape.
- *Mesh-invariant fingerprint* (quantised volume, area, sorted extents,
  inertia). Robust to tessellation differences, but needs tolerances, can merge
  genuinely different shapes, and costs a mesh load per artifact even when the
  bytes already match. Held in reserve until a project shows byte identity
  failing.
- *Canonical geometry hash* (sorted, quantised triangle soup). Middle ground,
  strictly more work than byte hashing for a case not yet observed. Deferred.

**The inventory is a top-level `pieces` list; rigid nodes gain a `piece` id.**

A consumer could group by `model`, but model → piece is many-to-one (gearbox),
so grouping by `model` reproduces the very bug being fixed. Publishing the
resolved id on the node makes the join trivial and unambiguous. The inventory
sits beside `root` rather than inline so each piece's facts are stated once, not
once per placement — v8-engine would otherwise repeat the valve's facts sixteen
times.

**The document keeps `format: "solid-node-export"`, `version: 1`.**

The growth is purely additive: no existing field changes meaning, and no
in-repo consumer validates the version for equality or rejects unknown keys.
The `mtime` field set the precedent for additive node metadata under version 1.
A bump would force every consumer to move in lockstep for a section they may
ignore.

**`serialize_node` gains an optional `piece_id(node, model)` mapper.**

Same shape as the existing `model_path` mapper, defaulting to `None` so every
current caller and test keeps working. The producer owns the accumulator; the
serializer stays a walk. The mapper receives the already-resolved model path so
the inventory records exactly the reference the tree publishes — build-relative
for the builder, `models/`-relative for the exporter — with no second mapping.

**Geometry facts come from the existing base-mesh cache.**

`solid_node/node/base.py` already caches loaded meshes by `(path, mtime)` and
already depends on trimesh; extents, volume, and watertightness come from the
same cached object a build or test may have loaded. Cost is one mesh load per
*distinct* artifact, after OpenSCAD has already produced it — small next to the
build it follows. Facts are read in the artifact's own frame, so no placement or
`$t` value can leak into them.

**Piece name and provenance under merging.** When several classes collapse to
one piece, `name` is the class name of the first contributing node in document
order (deterministic given a deterministic walk), and `sources` and `models`
list every contributor, sorted, so nothing about the merge is hidden from the
maker.

**Deriving facts is tolerant; deriving identity is not.** If an artifact cannot
be *meshed*, the piece is still published with the facts that were derivable and
`watertight: false` rather than aborting a publication whose tree is otherwise
complete — publication already tolerates imperfect geometry, and piece facts
must not become a new way for a build to fail. If an artifact cannot be *read at
all*, no piece id is produced and the read failure propagates: the only
fallbacks available are the class-and-parameter key this capability exists to
stop substituting for geometry, and publication is already gated on every
artifact being current, so an unreadable artifact is an internal inconsistency
belonging to whoever published a tree that names it. A fact that cannot be
measured is not an identity that cannot be trusted.

## Risks / Trade-offs

- **Byte identity is sufficient but not necessary.** Two identical shapes built
  through different code paths may differ in facet order and stay separate
  pieces — the same under-merge as today, no worse, and never a wrong merge.
  → Mitigation: the fallback is a canonical or invariant fingerprint behind the
  same `id` contract; nothing in the published schema has to change to adopt it.

- **Mesh loading on every publication.** A large model (the v8-engine camshaft
  is 660k faces) costs a load per distinct artifact.
  → Mitigation: shared `(path, mtime)` cache, once per distinct artifact rather
  than per placement, in a path that has just run OpenSCAD.

- **Document comparison drives republication.** The builder decides "anything
  new?" by comparing serialized bytes, so non-deterministic piece facts would
  cause spurious notifications.
  → Mitigation: every input is the artifact's own content; the requirement that
  an unchanged rebuild republishes byte-identically is spec'd and tested.

- **Additive growth without a version bump.** A hypothetical strict consumer
  that rejects unknown keys would break.
  → Mitigation: no such consumer exists in-repo, the widget's manifest type
  reads named fields, and the `mtime` precedent stands.

- **A merged piece can surprise.** Being told "print one bushing ×6" when the
  code names six classes is correct but unfamiliar.
  → Mitigation: `sources` and `models` name every contributor, so the merge is
  inspectable rather than silent.
