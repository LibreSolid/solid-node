# ADR-043: Content-derived printed-piece identity

**Status:** Accepted

**Date:** 2026-08-13

**Change:** `printed-piece-identity`

**Depends on:**
- [ADR-026: Node Identity — Parameter-Hashed Artifact Keys vs. Tree-Addressing Names](../NODE/ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md)
- [ADR-034: Shared node-tree document schema across export and build snapshots](ADR-034-shared-node-tree-document-schema.md)
- [ADR-028: Cached base meshes and single-matrix world composition](../NODE/ADR-028-cached-base-meshes-and-single-matrix-world-composition.md)

## Context

A consumer laying out a print job asks: which solids in this assembly are the
same piece, and how many of each? The published document could not answer it.
Its only identity for a rigid node was `model`, the artifact path derived from
`uniq_id` — a hash of the node class plus its constructor arguments (ADR-026).

That key answers "was this built from the same call?", which is the right
question for a build cache and the wrong one for a print job. Measured against
the published `viewer.json` of the shop's projects, the two answers diverge:

- **v8-engine** — 119 rigid placements collapse to 24 artifact keys, and all 24
  STLs are byte-distinct. Nominal identity is exactly right: 16 valves, 16
  retainers, 16 bucket lifters, 10 cam bearing caps, 8 pistons.
- **gearbox** — 24 artifact keys, but only 18 distinct STL contents. Six bushing
  classes with identical parameters build byte-identical geometry under six
  keys, as do `FrontWall` and `RearWall`. A layout driven by the artifact key
  would tell the maker to print eight distinct parts where two models cover
  them.

Factoring one shape into several named classes is ordinary, readable modelling.
It should not multiply the print job. Nothing in the document exposed a piece
count either, nor the facts a layout needs — extents, volume, watertightness —
so a consumer had to load and mesh every STL to learn whether a piece fits a
bed.

## Decision Drivers

- **The question is about geometry, not code structure.** Two solids are the
  same piece when the printer would receive the same thing, however the source
  is organised.
- **The build cache must not be disturbed.** `uniq_id` is load-bearing for
  staleness (ADR-006/026); a parameter change must still invalidate an artifact.
- **Placement is not identity.** Operations are applied outside the artifact,
  so a part posed sixteen ways is one piece — and mirrored variants are two.
- **One implementation, three producers.** Builder, exporter, and browser
  snapshot share one tree walk (ADR-034) and must not drift again.
- **Additive growth.** Existing consumers of the shared schema must keep
  working untouched.

## Considered Options

1. **Content fingerprint of the built artifact** (chosen) — sha256 of the STL's
   bytes, truncated to 12 hex digits.
2. **Keep `uniq_id`** — rejected: demonstrably under-merges, and widening it to
   ignore non-geometric parameters would require the framework to know which
   parameters affect shape.
3. **Mesh-invariant fingerprint** — quantised volume, area, sorted extents and
   inertia. Robust to tessellation differences, but needs tolerances, can merge
   genuinely different shapes, and costs a mesh load per artifact even when the
   bytes already match.
4. **Canonical geometry hash** — sorted, quantised triangle soup. A middle
   ground, strictly more work than byte hashing for a failure not yet observed.

## Decision Outcome

**A printed piece is identified by a content fingerprint of its built
artifact.** `solid_node/core/pieces.py` holds the fingerprint (cached per
`(path, mtime)`, the same shape as the base-mesh cache), the per-piece geometry
facts, and `PieceInventory`, the accumulator threaded through
`serialize_node`'s new optional `piece_id(node, model)` mapper. All three
producers publish a top-level `pieces` list beside `root`, and every rigid node
carries a `piece` id resolving into it.

The mapper receives the already-resolved model reference, so each producer
records exactly what it published — build-root-relative for the builder,
`models/`-relative for the exporter — with no second mapping. Geometry facts
(`size`, `volume`, `watertight`) come from the shared base-mesh cache (ADR-028)
read in the artifact's own frame, never `node.mesh`, which applies world
placement and would leak pose and `$t` into facts that must be
placement-independent.

`uniq_id`, artifact paths, caching, and the `model` field are untouched. The
two identities now coexist deliberately: **`uniq_id` answers "rebuild needed?",
the piece fingerprint answers "same thing to print?"** — and ADR-026's central
insight, that conflating two identities produces silent wrong answers, applies a
third time.

**Identity is content or it is nothing.** An artifact that cannot be read gets
no piece id; the `OSError` propagates to whoever published a tree naming a file
that is not there. An earlier implementation fell back to a hash of `uniq_id`
to keep publication non-fatal, and that was reversed on review: falling back to
the class-and-parameters key is precisely the substitution this ADR exists to
stop, and publication is already gated on every artifact being current, so the
degraded path was covering an internal inconsistency rather than a real
condition. Deriving *facts* remains tolerant — an unloadable or unclosed mesh
publishes a piece with `watertight: false` rather than aborting the document —
because a fact that cannot be measured is not an identity that cannot be
trusted.

The document keeps `format: solid-node-export, version: 1`. The growth is
additive: no existing field changes meaning, no in-repo consumer validates the
version for equality or rejects unknown keys, and `mtime` set the precedent for
additive node metadata (ADR-034). A bump would force every consumer to move in
lockstep for a section it may ignore.

## Consequences

**Good**

- The question a print layout asks is answered in the published document, with
  no mesh loading by the consumer.
- gearbox reports 18 pieces instead of 24 artifacts, with the merged pieces
  naming every contributing source and model, so the merge is inspectable
  rather than silent. v8-engine is unchanged at 24 pieces over 119 placements.
- Build and export documents agree on piece ids and counts for one model while
  keeping their own model reference roots.
- Cost is one fingerprint and one mesh load per *distinct* artifact, in a path
  that has just run OpenSCAD, sharing caches with the build and tests.

**Bad / risks**

- Byte identity is sufficient but not necessary. Two identical shapes built
  through different code paths may differ in facet order and stay separate
  pieces — the same under-merge as before, never a wrong merge. Options 3 and 4
  fit behind the same `id` contract with no schema change if a project ever
  shows it.
- The builder decides "is there new work?" by comparing serialized document
  bytes, so piece facts are now load-bearing for republication. They derive
  only from artifact content; an unchanged rebuild republishing byte-identically
  is spec'd and tested.
- Being told "print one bushing ×6" when the code names six classes is correct
  but unfamiliar. `sources` and `models` name every contributor.

## Related

- Capability spec: `openspec/specs/printed-pieces/`
- Originating requirement: the SolidNode Studio Build area, which presents a
  plate of pieces with per-piece quantity, source, extents, and bed-fit
  findings.
