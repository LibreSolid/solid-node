# ADR-081: Per-contributor metadata guards aggregate-mtime currency

**Status:** Accepted
**Date:** 2026-09-07
**Change:** `guard-source-set-currency`
**Amends:**
- [ADR-060: Content-Verified Currency Beneath the Mtime Rule](ADR-060-content-verified-currency-beneath-the-mtime-rule.md)
- [ADR-071: Node-Scoped Content Currency](ADR-071-node-scoped-content-currency.md)
**Depends on:**
- [ADR-033: Import-Closure Source Set and Up-To-Date Leaf Path](ADR-033-import-closure-source-set-and-up-to-date-leaf-path.md)
- [ADR-050: Nanosecond-Fidelity Artifact Freshness](ADR-050-nanosecond-fidelity-artifact-freshness.md)

## Context and Problem Statement

The artifact stamp is the maximum `st_mtime_ns` over `node.files`. That scalar
does not identify the state of the set: if one source is future-dated, another
contributor can change while remaining older and the maximum stays equal to the
artifact stamp. `_up_to_date()` then returned before ADR-060's content digest
was consulted. Due-diligence finding F05 reproduced a helper changing a cube
from 1 mm³ to 8,000 mm³ while two successful builds kept publishing 1 mm³.

ADR-060 and ADR-071 intentionally kept source contents off the settled path.
That constraint matters for imported meshes and STEP files as well as small
Python modules, but maximum-mtime equality cannot also support the stronger
claim that every observable contributing edit invalidates. Currency needs a
cheap observation of every member before it may skip content verification.

## Decision Drivers

- An edit to any tracked contributor must be observed even when the maximum
  source mtime stays fixed.
- Settled builds must not read or parse source contents.
- Timestamp-only rewrites, relocated projects, and unrelated sibling-class
  edits must continue to avoid geometry regeneration.
- Existing digest-only sidecars must upgrade without certifying stale output or
  forcing a render when their digest still proves equal content.
- Every uncertain or malformed state must resolve toward validation or rebuild.

## Considered Options

1. **Guard artifact-mtime equality with a fingerprint of every contributor's
   observable filesystem metadata, then retain the scoped content fallback**
   (chosen)
2. Hash every tracked source on every currency check
3. Record only the vector of source mtimes
4. Keep maximum-mtime equality as sufficient and accept the collision
5. Store contributor state in a second sidecar beside the existing digest

## Decision Outcome

Chosen: **artifact timestamp equality is necessary but no longer sufficient.**
The metadata-only path also compares a recorded source-set fingerprint with the
current fingerprint. Each sorted entry contains the project-relative real path,
filesystem device and inode, byte size, `st_mtime_ns`, and `st_ctime_ns`.
Replacement changes identity, an ordinary edit changes size or timestamps, and
a same-size edit whose mtime is restored still changes ctime. Computing it uses
`stat`, never source-content reads or AST analysis.

A fingerprint disagreement or absence enters ADR-060's node-scoped content
fallback. A digest mismatch rebuilds. A digest match restamps the artifact and
atomically records the current fingerprint with the digest, returning timestamp
rewrites, relocation, and ADR-071 sibling-only edits to the settled path without
re-deriving geometry.

The existing `.sources` file becomes a versioned JSON record containing the
digest and fingerprint. Its path, atomic write order, sweep ownership, and
absence from viewer documents do not change. A legacy one-line digest is read
as a record with no fingerprint, so it must be content-verified even when the
artifact stamp matches; a match upgrades it in place. Malformed and unknown
records certify nothing. Rolling back encounters JSON where an older reader
expects a digest, producing a safe rebuild.

The same metadata identity also keys the in-process byte and AST caches. Keying
those caches only on `(path, mtime, size)` would let the newly detected
same-size, restored-mtime edit reuse its old digest and defeat the fallback.

### Why not hash every settled source

It provides the strongest answer but imposes source I/O on every node of every
settled build, including large imported geometry. The fingerprint closes the
observed aggregate collision while retaining ADR-006/060's performance
boundary.

### Why not record only every mtime

It fixes the future-maximum reproduction but still misses a rewrite whose mtime
is restored. Size, change time, and filesystem identity are available from the
same stat operation and cover ordinary preserved-mtime edits and replacements.

### Why not use a second sidecar

Two independently published records can disagree after interruption and add a
second ownership rule to the sweep. One versioned record preserves the existing
atomic publication boundary.

## Consequences

- A contributing edit hidden below an unchanged maximum mtime now rebuilds the
  affected node and its ancestors.
- A settled currency check reads one small sidecar and stats tracked sources;
  it does not read source bytes or parse Python.
- Existing build directories perform one digest verification per artifact and
  then upgrade without rendering when their sources still match.
- No-op metadata changes still invoke content verification once, and
  node-scoped digest equality still spares unaffected sibling nodes.
- The guarantee has an explicit observation boundary: if a filesystem or
  privileged operation changes bytes while preserving path identity, size,
  mtime, and ctime exactly, a metadata-only check cannot detect it. Such a
  caller must remove the artifact or currency record to force verification.
- Every SCAD, STL, BREP, DXF, flexible snapshot, imported mesh, and JSCAD
  publisher records the same complete currency state.

## Evidence

The pre-fix focused run failed both stale-geometry regressions and accepted a
malformed structured record. After implementation, 17 currency tests and a
296-test publisher/currency set passed. The saved CLI probe changed from
publishing 1 mm³ after the masked edit to the expected 8,000 mm³. The complete
suite passed 1,540 tests with 16 skipped, 38 warnings, and 258 passing
subtests.

## References

- `solid_node/currency.py`
- `solid_node/node/base.py`
- `tests/test_content_verified_currency.py`
- OpenSpec change `guard-source-set-currency`
