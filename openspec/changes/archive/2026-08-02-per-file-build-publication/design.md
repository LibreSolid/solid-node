## Context

Publication today has three moving parts. `BuildSession` makes a private
candidate directory seeded by copying the current build tree.
`Builder` renders into it and writes `viewer.json` there. `BuildSessionPublisher`
renames the candidate to a versioned sibling `_build.<token>` and moves a
symlink onto `_build` with `os.replace`, then deletes the tree it superseded.

Two ADRs stand behind that. ADR-030 established the complete-build boundary and
explicitly rejected rendering into the public directory because "readers can
observe a mixed artifact set while a build is in progress". ADR-032 kept the
boundary but replaced the two-rename dance with the symlink swap, after
measuring the build path absent 228 times across 200 publications.

F1 changed the ground under both. Racing publishers — ADR-032's second defect,
and the reason the pipeline tolerates a lost publication race at all — cannot
happen now: every producer holds the project build lock while it renders and
publishes. What remains of the old rationale is the torn-read fear, and that
does not need a set.

The measurement that matters for this sprint: a single leaf edit on
`projects/v8-engine` currently republishes 113 MB across 55 STLs, and the
consumer must reload all of it because the publication is one event.

## Goals / Non-Goals

**Goals:**

- One `_build` directory, written in place, with no symlink, no versioned
  siblings and no candidate copy.
- A reader never sees a half-written artifact, and one already reading an
  artifact finishes reading the bytes it opened.
- An artifact becomes reachable only through the manifest, so ordering is:
  artifacts, then manifest; manifest, then sweep.
- A node removed from the model stops occupying the build directory.
- `errors.json` has an explicit, proven lifecycle rather than an inherited one.
- The BUILD architecture record for D1 and D2 is filed with its evidence.

**Non-Goals:**

- Content-addressed artifact names (PRD section 8). A single directory plus the
  existing `(path, mtime)` staleness key removes the need.
- Any change to what the viewer renders, or to the shared `viewer.json` schema.
- Targeted updating in the viewer, which is F3, and the floor's event pipeline,
  which is S1. This cycle only changes how artifacts reach the directory.
- Reader-side locking. Consumers do not take the build lock and a browser
  cannot be made to.

## Decisions

**D-1 — `os.replace` per artifact, in the artifact's own directory.**
Every writer produces a temporary sibling and renames it over the target: the
rename is atomic on POSIX and, because the temporary is in the same directory,
never crosses a filesystem. A reader holding an open descriptor keeps reading
the old inode to completion, which is precisely the torn-read guarantee ADR-030
wanted; what it does not provide — and what this cycle deliberately gives up —
is a consistent *set*. Alternatives: writing in place and hoping readers retry,
rejected as the defect this replaces; keeping a candidate directory and hard
linking artifacts into `_build`, rejected because it reintroduces set thinking
without its guarantee and doubles the bookkeeping.

**D-2 — OpenSCAD renders to a temporary file, `finish()` publishes it.**
`generate_stl` today deletes the target and points OpenSCAD at it, so the STL is
absent for the whole render and partial as it is written — invisible while the
directory was private, fatal in a shared one. The render target becomes
`<artifact>.<token>.tmp`; `StlRenderStart.finish()` stamps the source mtime on
it and `os.replace`s it into place, keeping mtime-equality caching exactly as
specified. The existing `.stl.lock` PID file stays: it guards two processes
rendering the same artifact, which the project build lock already prevents but
which is cheap and orthogonal.

**D-3 — The manifest is written last and is the only thing that makes an
artifact reachable.**
Additions: every artifact, then `viewer.json`. Removals: `viewer.json` first,
then sweep. A reader that sees a new manifest can always fetch what it names;
a reader still holding an old manifest can still fetch what *it* names, until
the sweep — and a sweep only removes what the current manifest does not
reference, so the window is one manifest generation. Alternative: sweeping
before writing the manifest, rejected because it can delete an artifact the
still-published manifest names.

**D-4 — The sweep is manifest-driven and confined to the build tree.**
After a successful build, files under `_build` that the new manifest does not
reference are removed, except the manifest itself, `errors.json`, in-flight
temporaries and live `.stl.lock` files. `.scad` files are kept, keyed to their
STL: they are inputs to a render, not artifacts a consumer reaches, and dropping
them would force a re-render on the next build. Alternative: sweeping by age,
rejected because a legitimately unchanged artifact is arbitrarily old.

**D-5 — `errors.json` is written atomically, cleared on every successful build,
and never swept.**
The candidate copy used to carry it forward or drop it as a side effect of
`copytree`; with the copy gone, both edges are explicit. It is cleared after a
successful publication rather than at load, so a consumer never sees a moment
with a stale model and no error. R2 in the PRD calls this out as assumed rather
than verified, so it gets its own tests rather than inheriting behaviour.

**D-6 — Migration is a one-time in-place conversion.**
A build path that is a symlink — every project built under ADR-032 — is
converted on the next build: the referenced versioned directory is renamed onto
the build path after the symlink is removed, and stale `_build.<token>` siblings
are removed. That single publication is not atomic, exactly as ADR-032's own
migration was not. Alternative: leaving the symlink in place and writing through
it, rejected because it keeps defect B alive for every existing project.

**D-7 — A partially updated model is an accepted observable state (PRD D8).**
This is the cycle's real cost. A build that fails midway now leaves some
artifacts new and some old, where the pipeline previously guaranteed the last
complete set. The framework's `Last successful artifacts survive a failed later
build` requirement is withdrawn, not weakened. The maker is not left guessing:
`errors.json` still reports the failure, and the ordering rule means the
manifest still names a reachable artifact for every node. If this proves
unacceptable in use, PRD R1 records the fallback — a build-in-progress signal,
not a return to set atomicity.

## Risks / Trade-offs

- **ADR-030's reversal is contested by construction.** A reviewer reading only
  ADR-030 will see this as reintroducing the defect it rejected → mitigation:
  the new record argues the conflation head-on (complete set versus no torn
  reads) and carries the measurement; ADR-030 is marked as reversed rather than
  quietly ignored.
- **The sweep can delete a live artifact if the manifest is wrong.** A
  serializer bug becomes data loss rather than a stale file → mitigation: sweep
  only after a successful publication, only within the build tree, and never
  files a manifest generation still names; tests cover a removed node and a
  renamed one.
- **Consumers relying on set atomicity break quietly.** The shop's viewer host
  reads `viewer.json` and its models as one unit today → mitigation: this is
  the intended direction (S1 and S2 consume it deliberately), and the sprint
  integrates both repositories before the floor is exercised.
- **Migration runs while a consumer is reading.** The one-time conversion is
  not atomic → mitigation: it happens under the project build lock, and a
  reader following `_build` sees either the symlink's target or the same tree
  at the same path.
- **Temporary files accumulate if a render dies.** A killed OpenSCAD leaves
  `<artifact>.<token>.tmp` → mitigation: the sweep removes temporaries older
  than the build that started them, and they are ignored by every consumer
  because the manifest never names them.
