## Context

`AbstractBaseNode._up_to_date(path)` is `os.path.exists(path) and
os.stat(path).st_mtime_ns == self.mtime_ns`. It is called from
`generate_stl`, from `assemble`'s `_render_can_be_skipped`, and from
`Builder._artifacts_are_current` for both `stl_file` and `brep_file`.
Artifacts are stamped by `os.utime(..., ns=(time.time_ns(), mtime_ns))` in
`_atomic_write_text`, `_atomic_write_bytes` and `StlRenderStart.done()`.

The rule is precise about edits and blind to content. Measured on a 22-part
CadQuery project: a settled rebuild is 6.05 s, and a rebuild after every source
mtime is rewritten with zero content change is 35.66 s.

ADR-006 considered content hashing as a *replacement* for the mtime check and
rejected it on cost. That reasoning is sound and is not disturbed here: the
mtime check remains the only thing consulted when it succeeds.

## Goals / Non-Goals

**Goals:**

- A timestamp that moved without content changing stops costing a rebuild.
- Zero added cost when the mtime check succeeds.
- The direction-of-failure guarantee is preserved or strengthened, never
  weakened: a changed source must never be reported current.

**Non-Goals:**

- Replacing mtime equality. It stays the fast path and the primary rule.
- Retaining swept artifacts for a reverted parameter — separate change,
  unmeasured value, touches the publication boundary.
- Parallel rendering — investigated and dropped; see the proposal.
- Sub-file invalidation granularity.

## Decisions

### Digest the node's tracked sources, not its artifacts or its generated SCAD

The digest covers `node.files` — the node's own source plus its project-local
import closure — as a sorted sequence of (project-relative path, sha256 of
bytes). That set is exactly what `mtime_ns` is computed from, so the digest
answers precisely the question the mtime was standing in for.

*Alternative — digest the generated `.scad`.* Rejected: producing it requires
`render()`, which is the expensive step this change exists to avoid. For an
exact CadQuery node that is the entire cost.

*Alternative — digest the artifact.* Rejected: it answers "is the artifact
intact", not "would rebuilding produce the same artifact".

Hashing a handful of small text files on a miss is negligible against the
render it replaces, and it is never done on a hit.

### Record the digest where the artifact is stamped

An artifact and the digest vouching for it must be written together or not at
all — a digest without its artifact, or an artifact carrying a digest from a
different source state, is worse than none. Recording therefore happens at the
same place as `os.utime`, not at a separate bookkeeping step.

That is **every** stamping site, not only the ones in `node/base.py`. An exact
node's `.stl`, `.brep` and `.dxf` are stamped in `exact.py::_atomic_export`, an
`StlNode`'s mesh in `adapters/stl.py`, and a `JScadNode`'s output in place after
its renderer exits. The exact writers are the ones this change exists for, since
this workspace's projects are overwhelmingly CadQuery and Build123d.

The write order is itself the contract: drop the old record, rename the
artifact, then write the new record. An interruption anywhere leaves an artifact
with *no* record — a rebuild, which is safe — and never an artifact carrying the
record of the source state that produced its predecessor, which would certify a
stale file the moment those sources reappeared. An adapter that writes in place
rather than by rename must drop the record before starting, so a killed renderer
cannot leave a digest vouching for a half-written file.

Storage is a sidecar inside the build directory beside the artifact it
describes. It is never named by `viewer.json`, so publication (ADR-030) is
unchanged. `_sweep_unreferenced_artifacts` must keep a sidecar whose artifact
it keeps and drop one whose artifact it removes — the sweep currently deletes
anything unreferenced that is not `.scad`, `.brep`, `.stl.lock` or `.tmp`, so
the sidecar needs explicit handling or it is deleted on every publication and
the fallback silently never fires.

*Alternative — one index file for the whole build.* Rejected: it makes every
artifact write a read-modify-write of shared state, which the concurrent render
protocol would have to serialise. Per-artifact sidecars inherit the atomicity
the artifact write already has.

### Determinism is the assumption already made

The fallback is sound exactly when identical sources produce an identical
artifact. ADR-006 already records that the framework "assumes deterministic CAD
compilation (same SCAD always produces same STL)", and every existing cache hit
relies on it. This change relies on that assumption and nothing more: it never
claims an artifact is current on weaker evidence than the mtime rule would.

### Restamp, then report current

On a digest match the artifact is restamped to the current `node.mtime` so the
fast path serves every later build. Where the filesystem cannot store the exact
stamp — the coarse-filesystem case the requirement already covers — the restamp
will not achieve equality; the build must still treat the artifact as current on
the strength of the digest for this run, and simply consult the fallback again
next time. It must not loop, and it must not conclude "not current" after
deciding "current".

## Risks / Trade-offs

- **A wrong digest reports a changed source as current** — the worst failure
  in the system, a stale model presented as fresh → the digest is over exactly
  the file set `mtime_ns` is derived from; a mismatch, an unreadable source, or
  an absent record all fall through to rebuild; and the tests must include a
  real content change that must still rebuild, not only the no-change case.
- **A sidecar outliving its artifact, or surviving a parameter change** →
  artifact names are parameter-addressed (ADR-026), so a parameter change asks
  about a different filename entirely and cannot read a stale sidecar; the
  sweep must still drop sidecars for artifacts it removes, or the build
  directory accumulates them.
- **The sweep deleting sidecars** — the silent failure mode: everything keeps
  working, the fallback simply never fires and nobody notices → a test that
  performs a publication and *then* checks the fallback still works.
- **Added I/O on every genuine rebuild** — a miss now reads the closure before
  rendering → bounded by a few KB of text against a render measured in seconds,
  and only on the path that was about to do far more work.
- **Interaction with the shared OCCT currency for exact backends (ADR-047)** →
  the `.brep` participates in currency exactly as the `.stl` does; both must
  restamp together, or a node reports half-current and rebuilds anyway.
