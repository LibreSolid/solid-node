## Context

An artifact is stamped with the maximum `st_mtime_ns` of `node.files`. On an
equality hit `_up_to_date()` returns before opening the `.sources` sidecar or
computing the node-scoped digest. This is cheap, but it collapses a set of
source states into one maximum: a future-dated source can mask every edit to an
older contributor. F05 demonstrates that failure through the public CLI.

ADR-060 added content verification only below a failed aggregate comparison,
and ADR-071 preserved that hit path while making the digest node-scoped. The
existing digest remains the strongest available evidence and preserves useful
no-op timestamp, relocated-project, and sibling-class behavior. The missing
piece is a cheap record of every contributor's observed state that decides
whether the digest may safely be skipped.

## Goals / Non-Goals

**Goals:**

- Detect an edit to any tracked contributor even when the aggregate maximum
  mtime does not move.
- Preserve a metadata-only settled path: stat tracked sources and read the
  artifact's small sidecar, but do not read source contents or parse Python.
- Retain the existing content fallback for metadata-only changes and
  node-scoped sibling edits.
- Upgrade digest-only sidecars safely without forcing geometry regeneration
  when their digest still proves the artifact current.
- Keep publication and sweeping atomicity guarantees for every artifact type.

**Non-Goals:**

- Detect changed bytes on a filesystem that reports the same path identity,
  size, mtime, and change time before and after the change.
- Replace import-closure discovery or node-scoped digest semantics.
- Change artifact timestamps, paths, viewer documents, or build locks.
- Add a database, watcher-owned currency, or a background index.

## Decisions

### D1: Record a fingerprint over every tracked source's metadata

The framework will compute a deterministic fingerprint over sorted entries of
`(project-relative real path, st_dev, st_ino, st_size, st_mtime_ns,
st_ctime_ns)`. Path and identity detect replacement; size detects ordinary
content changes even with a restored mtime; change time detects same-size
rewrites whose mtime is restored. Project-relative paths preserve relocation
behavior: relocation changes identity and invokes content verification once,
then records the new local fingerprint.

Using only the vector of mtimes was rejected because a same-mtime rewrite
would remain invisible. Using only maximum mtime is the current defect. Hashing
source bytes on every settled build was rejected because large imported
geometry is tracked source and ADR-006/060 deliberately avoid that I/O.

This is an explicit observation boundary. If a filesystem or external tool
can change bytes while preserving every recorded identity and metadata field,
the metadata-only path cannot observe it; callers requiring protection from
that condition must invalidate the artifact or sidecar. Normal writes and
`os.utime` restoration change at least size or ctime on supported filesystems.

### D2: Equality requires both the artifact stamp and source fingerprint

`_up_to_date()` will report a metadata-only hit only when the artifact exists,
its `st_mtime_ns` equals `node.mtime_ns`, and the current source-set fingerprint
equals the one recorded for that artifact. A missing, malformed, or different
fingerprint enters content verification; uncertainty never certifies an
artifact.

Keeping artifact equality as a sufficient condition was rejected because it
preserves F05. Removing the artifact stamp from the condition was rejected
because exact back-dating remains the public currency and coarse-filesystem
contract.

### D3: Keep the content digest as the fallback and refresh the complete record

On a fingerprint miss, the framework compares the existing node-scoped source
digest. A mismatch rebuilds. A match reports current, best-effort restamps the
artifact, and atomically records the current fingerprint with the same digest.
Thus timestamp rewrites, project relocation, metadata-only changes, and edits
to an unrelated sibling class still avoid geometry work and return to the
settled path on the next build.

Rebuilding on every fingerprint mismatch was rejected because it would undo
ADR-060/071. Treating a fingerprint mismatch as current was rejected because
metadata is only a change detector, not evidence of equal content.

### D4: Version the existing sidecar and accept its legacy digest form

New `.sources` files will contain a versioned structured record with the
content digest and source fingerprint. Readers will continue to accept the
legacy one-line digest as a record with no fingerprint. Such an artifact must
take the digest fallback even when its artifact stamp equals the aggregate
mtime; a digest match upgrades the sidecar without re-rendering, while a
mismatch rebuilds. Unknown versions and malformed records are treated as no
record.

The existing sidecar path and sweep ownership remain unchanged. Adding a
second sidecar was rejected because publication could expose mismatched halves
and every sweep participant would need another ownership rule.

### D5: Publish one source record through every stamping path

Nodes will expose the fingerprint beside their existing digest, and all SCAD,
STL, BREP, DXF, flexible snapshot, imported-mesh, and JSCAD stamping paths will
write the complete record. Atomic publishers retain the order “drop old
record, replace artifact, record new state.” In-place adapters retain “drop
before rendering, record after successful stamping.”

Tests will first reproduce F05 through the currency fixture and public CLI,
including a same-size edit followed by mtime restoration. Unit coverage will
pin legacy parsing/upgrading, malformed-record failure direction, scoped
fallback behavior, and the absence of source-content reads on a settled hit.
Adapter coverage will confirm all publishers supply the complete record.

## Risks / Trade-offs

- **Every hit reads a small sidecar and stats each tracked source for its
  fingerprint.** → Reuse the same per-node source metadata within a currency
  decision, keep content and AST work off the settled path, and measure the
  focused fixture before accepting the implementation.
- **`st_ctime_ns` semantics vary by platform.** → Combine it with path,
  identity, size, and mtime; exercise restored-mtime behavior on the supported
  test platform and document the identical-metadata boundary.
- **Legacy artifacts no longer take the old equality-only shortcut.** →
  Validate their existing digest once and upgrade in place without geometry
  regeneration.
- **A source may change between metadata and content observations.** → Keep
  the builder's before/after source checks and make every uncertain or
  unreadable record resolve to rebuild; do not widen this change into source
  locking.

## Migration Plan

No explicit migration command is required. The first currency check for each
legacy sidecar validates its digest and replaces it with the structured record,
or rebuilds if validation fails. Rolling back leaves structured sidecars that
an older reader cannot parse as its expected digest, causing safe one-time
rebuilds rather than false cache hits.

## Open Questions

None.
