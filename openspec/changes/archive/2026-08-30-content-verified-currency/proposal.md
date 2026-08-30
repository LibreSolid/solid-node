## Why

Artifact currency is decided by mtime equality (ADR-006): an artifact is
current when its `st_mtime_ns` equals the maximum `st_mtime_ns` across the
node's source closure. The check is fast and precise about *edits*, but it is
blind to *content*. Anything that rewrites a source file's timestamp without
changing a byte invalidates the artifact it produced.

Ordinary Git work does exactly that. `git clone`, a branch switch, `git stash
pop`, `git restore`, or copying a project all stamp files with the time they
were written. So does an agent or formatter rewriting a file with identical
bytes.

Measured on a 22-part CadQuery project, touching every source with no content
change at all:

| | measured |
| --- | ---: |
| settled rebuild, nothing to do | 6.05 s |
| **rebuild after every mtime is rewritten, zero content change** | **35.66 s** |

Every second of that difference re-derives geometry that is already on disk and
provably identical. The projects in this workspace are larger than the fixture —
`v8-engine` carries 46 exact parts, `Metamaquina2` 96 published artifacts — and
the cost scales with them.

ADR-006 considered content hashing and rejected it as "expensive I/O ... slower
cache checks ... overkill for typical development workflows". That judgement was
about replacing the mtime check. It holds, and this change does not do that.

## What Changes

- The mtime equality check stays exactly as it is, and stays the only thing
  consulted when it succeeds. Nothing gets slower on the hit path.
- When it *fails*, the framework compares a digest of the node's source closure
  against the digest recorded beside the artifact when that artifact was
  produced. A match means the sources that produced it are byte-identical to
  the sources now on disk, so re-deriving the artifact would reproduce it.
- On a match the artifact is restamped to the new `mtime_ns` — the same
  `os.utime` the build already performs — and treated as current. On a mismatch,
  or with no recorded digest, the artifact is rebuilt exactly as today.
- Hashing therefore costs nothing on the hit path, and on a miss it is paid only
  where a full render would otherwise run. It reads the node's own source
  closure — a handful of small text files — not its artifacts.
- Determinism is already assumed. ADR-006 records that the framework "assumes
  deterministic CAD compilation (same SCAD always produces same STL)"; this
  change relies on exactly that assumption and no more.

## Capabilities

### Modified Capabilities

- `build-pipeline`: artifact currency gains a content-verified fallback beneath
  the mtime check, so a source whose timestamp moved without its content
  changing no longer forces a rebuild.

## Impact

- `solid_node/node/base.py` — `_up_to_date`, and the point where an artifact is
  stamped, which must also record the digest.
- `solid_node/core/builder.py` — `_artifacts_are_current`, which asks
  `_up_to_date` for both `stl_file` and `brep_file`, and
  `_sweep_unreferenced_artifacts`, which must not delete a digest sidecar whose
  artifact it is keeping.
- The recorded digest lives inside `_build`, is never referenced by
  `viewer.json`, and does not change what publication means (ADR-030).
- No CLI, dependency, or public API change. No change to artifact naming, which
  is already parameter-addressed (ADR-026).

## Explicitly out of scope

- **Retaining swept artifacts** so a reverted parameter is restored rather than
  re-rendered. The approved plan paired it with this change, but its value is
  unmeasured here while this one is measured at 35.66 s → an expected ~6 s, and
  it touches the publication boundary. It needs its own evidence and its own
  change.
- **Parallel rendering.** Investigated and dropped: the one-artifact-per-forked-
  process serialism applies to OpenSCAD-backed nodes, and this workspace's
  projects are overwhelmingly exact — `v8-engine` is 46 CadQuery nodes,
  `Metamaquina2` is Build123d and molejo. A 22-part CadQuery build ran in one
  builder generation, not 23. Parallelising exact evaluation instead is a
  different and much larger change and is the pilot's call, not a substitution
  to make quietly.
- **Sub-file invalidation granularity.** Editing a docstring inside a node's
  closure still invalidates it. That needs symbol-level dependency tracking.
