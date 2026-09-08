# ADR-085: Persistent Piece Facts Behind a Verified Artifact Snapshot

**Status:** Accepted
**Date:** 2026-09-07
**Change:** `bound-framework-performance-costs`
**Amends:**
- [ADR-043: Content-Derived Printed-Piece Identity](ADR-043-content-derived-printed-piece-identity.md)
- [ADR-028: Cached Base Meshes and Single-Matrix World Composition](../NODE/ADR-028-cached-base-meshes-and-single-matrix-world-composition.md)
**Depends on:**
- [ADR-038: Per-Artifact Atomic Build Publication](../BUILD/ADR-038-per-artifact-atomic-build-publication.md)
- [ADR-081: Per-Contributor Metadata Guards Aggregate-Mtime Currency](../NODE/ADR-081-per-contributor-metadata-guards-aggregate-mtime-currency.md)

## Context and Problem Statement

ADR-043 derives a printed piece's identity and manufacturing facts from its
built STL. That is the right source of truth, but its original process-local
`(path, mtime)` caches made every fresh builder hash and decode every current
artifact again. Retaining a builder for one source generation reduces repeated
work within that process; it does not help the next build.

Persisting those facts is safe only if the record still describes the exact
artifact bytes a producer publishes or copies. Path and floating-point mtime
are insufficient. A same-size atomic replacement can retain mtime while
changing inode and ctime, and ADR-028's weaker base-mesh cache could otherwise
serve the old geometry during recomputation. Export and browser staging add a
second race: facts for one path identity must not be paired with bytes copied
from its replacement.

## Decision Drivers

- Fresh processes should reuse only facts derived from a verified current STL.
- Full digest, mesh facts and copied bytes must describe one coherent artifact
  identity.
- Same-size, restored-mtime replacement must invalidate persistent and
  process-local reuse.
- Tree names, placements, sources, models, counts and document metadata must
  always come from the current live tree.
- Failure and interruption must cost recomputation, never certify stale facts.
- The compatible public 12-hex piece id must not silently merge a collision.

## Considered Options

1. **Persist artifact-only facts behind a strong pinned snapshot** (chosen)
2. Persist facts keyed only by path and mtime
3. Persist the complete prior node document
4. Recompute digest and mesh facts in every fresh process

## Decision Outcome

A private versioned fact record beside each STL stores only the artifact's full
SHA-256 digest, printable extents, volume and watertightness, together with the
observation under which those values were derived: canonical path, device,
inode, byte size, integer-nanosecond mtime and integer-nanosecond ctime. Reuse
requires exact equality with the current path observation and current artifact
currency under ADR-081. Missing, malformed, unknown-version or mismatching
records certify nothing and trigger recomputation.

An artifact snapshot opens the file, compares open-file and path identities,
consumes the pinned bytes, and validates both identities again before accepting
the result. On a miss, the full digest and mesh facts derive from that same
snapshot; recomputation evicts or bypasses every base-mesh, local-bounds and
Manifold entry keyed by a weaker observation. On a hit, export and browser
staging copy from the same pinned snapshot whose facts they publish. A
concurrent replacement therefore yields one coherent old or new artifact/fact
pair, or causes a retry; it cannot mix them.

Fact records publish atomically only after complete computation and are swept
with their STL. They never supply display name, source labels, model paths,
count, hierarchy, placement, drivers, expressions or document version. Every
producer reserializes those values from the current tree.

The full SHA-256 is the internal inventory identity. The public piece id
remains its compatible 12-hex prefix when unique, but two different full
digests with the same prefix fail deterministically rather than merging.

This amends ADR-043's process-local derivation and ADR-028's `(path, mtime)`
artifact cache boundary. It does not cache placed meshes: callers still receive
a mutable copy of the immutable base and compose current placement afresh.

## Consequences

- A current artifact with a valid record avoids hashing and mesh decoding in a
  fresh builder while current tree metadata is still reconstructed.
- Exported and browser-staged model bytes remain coherent with the digest and
  facts in the document even across concurrent path replacement.
- Each STL gains one private fact sidecar and one atomic-write/sweep ownership
  rule. Old build directories simply compute it on their next publication.
- An uncertain observation or interrupted write causes safe recomputation.
- Lower geometry caches use a stronger key than before and eagerly discard a
  stale entry for the same path.
- Byte identity remains sufficient but not necessary for piece equivalence;
  facet-order differences may still under-merge, never falsely merge.
- As in ADR-081, a privileged operation capable of changing bytes while
  preserving every exposed identity field must explicitly invalidate the
  artifact or record.

## References

- `solid_node/_artifact.py`
- `solid_node/core/pieces.py`
- `solid_node/node/base.py`
- `solid_node/core/export.py`
- `solid_node/viewers/browser.py`
- `tests/test_persistent_piece_facts.py`
- [Archived change](../../../openspec/changes/archive/2026-09-08-bound-framework-performance-costs/)
