# ADR-060: Content-Verified Currency Beneath the Mtime Rule

**Status:** Accepted
**Date:** 2026-08-30
**Amends:** [ADR-006: Mtime-Based STL Caching Strategy](./ADR-006-mtime-based-stl-caching-strategy.md)
**Depends on:**
- [ADR-033: Import-Closure Source Set and Up-To-Date Leaf Path](./ADR-033-import-closure-source-set-and-up-to-date-leaf-path.md)
- [ADR-050: Nanosecond-Fidelity Artifact Freshness](./ADR-050-nanosecond-fidelity-artifact-freshness.md)
- [ADR-047: Shared OCCT Currency for Exact Backends](./ADR-047-shared-occt-currency-for-exact-backends.md)

## Context and Problem Statement

ADR-006 decides currency by mtime equality: an artifact is current when its
`st_mtime_ns` equals the maximum across the node's tracked source closure. It is
precise about *edits* and blind to *content*. Anything that rewrites a source
timestamp without changing a byte invalidates the artifact it produced.

Ordinary Git work does exactly that: `git clone`, a branch switch, `git stash
pop`, `git restore`, or copying a project stamps files with the time they were
written. So does an agent or a formatter rewriting a file identically.

Measured on a 22-part CadQuery project, touching every source with no content
change:

| | measured |
| --- | ---: |
| settled rebuild | 6.05 s |
| rebuild after every mtime rewritten, zero content change | **35.66 s** |

Every second of the difference re-derived geometry already on disk and provably
identical. `v8-engine` carries 46 exact parts and `Metamaquina2` 96 published
artifacts, so the cost scales well past the fixture.

ADR-006 considered content hashing and rejected it: "expensive I/O ... slower
cache checks ... overkill for typical development workflows". That judgement was
about *replacing* the mtime check, and it stands.

## Decision Drivers

- The hit path must not get slower. It is taken on every build of every node.
- Currency may fail in only one direction. A source that changed must never be
  reported current — the one failure ADR-006 says the system cannot survive.
- The fix must serve exact backends, since this workspace's projects are
  overwhelmingly CadQuery and Build123d.

## Considered Options

1. **A content-verified fallback consulted only when mtime equality fails**
   (chosen)
2. Replace mtime equality with content hashing (ADR-006's rejected option)
3. Make the mtime comparison a `>=` inequality, make-style
4. Do nothing

## Decision Outcome

Chosen: **a fallback beneath the existing rule, never beside it.**

`_up_to_date` is unchanged when it succeeds — `exists`, then `stat == mtime_ns`,
with nothing opened. Only on failure does it compare a digest of the node's
tracked sources, as they are now, against the digest recorded when the artifact
was written. A match means the sources that produced the artifact are
byte-identical to the sources present, so the artifact is restamped to the
current `node.mtime` and reported current. A mismatch, a missing record, or an
unreadable source falls through to a rebuild.

The digest covers `node.files` — exactly the set `mtime_ns` is the maximum of —
as a sorted mapping of *project-relative* path to sha256 of bytes. Relative
because the case this exists for includes a project that moved. Per-file hashes
are cached on `(path, mtime, size)`, without which a tree's digests would be
quadratic, since an internal node's file set is the union of its children's.

**Recording happens at every stamping site**, not only the three in
`node/base.py`: an exact node's `.stl`, `.brep` and `.dxf` in
`exact.py::_atomic_export`, an `StlNode`'s mesh, and a `JScadNode`'s output.
The write order is the contract — drop the old record, rename the artifact,
write the new record. An interruption then leaves an artifact with *no* record,
which rebuilds; never an artifact carrying its predecessor's record, which would
certify a stale file the moment those sources reappeared. An adapter writing in
place drops its record first, so a killed renderer cannot leave a digest
vouching for a half-written file.

The answer never depends on the restamp succeeding. Where the filesystem cannot
store the exact stamp (ADR-050's coarse-filesystem case), the artifact is still
current for that build on the strength of the digest, and the fallback is simply
consulted again next time. It cannot loop and cannot contradict itself.

The sweep judges a sidecar by the artifact it describes, keeping the digest of
an artifact it keeps and dropping the one whose artifact it removes. Without
that, sidecars would be deleted on every publication, the fallback would never
fire, and every test would still pass.

Measured after: rebuild following a full timestamp rewrite **35.70 s → 5.83 s**;
a relocated copy with every timestamp new builds in 5.92 s; all 72 published
artifacts byte-identical by sha256; a genuine edit still rebuilds exactly the
affected subtree and nothing else.

### Why not replace mtime equality (option 2)

ADR-006's cost objection is correct, and this design answers it by never paying
on the hit path. Replacing the check would pay on every node of every build.

### Why not `>=` inequality (option 3)

ADR-006 rejected it for false cache hits, and it would not help here anyway: a
rewritten timestamp is *newer* than the artifact, so the artifact would still
read stale.

## Consequences

- Ordinary Git work stops costing full rebuilds. Cloning a project, switching
  branches, or popping a stash now costs a settled rebuild.
- The fallback is *stricter* than the rule it stands behind: it reports current
  only on byte-identical sources, where mtime equality reports current on an
  equal timestamp. It cannot widen the stale-model window.
- **It inherits ADR-006's determinism assumption and adds nothing to it.** Same
  sources producing a different artifact was already a cache-correctness bug;
  this decision relies on that assumption and no more.
- The mid-build edit window is unchanged: the digest is read when the artifact
  is written, exactly as `mtime_ns` is, and the builder's existing
  `SOURCE_CHANGED` re-check remains the guard. Neither widened nor narrowed.
- A future writer that stamps an artifact and forgets to record a digest loses
  the optimisation for that artifact silently — the missing record reads as "not
  current", which is safe but quiet.
- `viewer.json` still records each node's source `mtime`, so a pure timestamp
  rewrite does move the published document even though no artifact changes. The
  document has never been stable across such a rewrite, before or after this
  decision.

## References

- `solid_node/currency.py` — digest, sidecar, `publish`, `restamp`
- `solid_node/node/base.py` — `_up_to_date` and the fallback
- `solid_node/core/builder.py` — `_artifacts_are_current`, sweep handling
- `tests/test_content_verified_currency.py`
- OpenSpec change `content-verified-currency`, capability `build-pipeline`
