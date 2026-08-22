# ADR-050: Nanosecond-fidelity artifact freshness

**Status:** Accepted

**Date:** 2026-08-22

**Change:** `tolerate-coarse-mtime-filesystems`

**Amends:** [ADR-006: Mtime-Based STL Caching Strategy](ADR-006-mtime-based-stl-caching-strategy.md)

**Affects:**
- [ADR-033: Import-Closure Source Set and the Up-to-Date Leaf Path](ADR-033-import-closure-source-set-and-up-to-date-leaf-path.md)
- [ADR-044: Derived exact-geometry capability](ADR-044-derived-exact-geometry-capability.md)

## Context

ADR-006 decided that an artifact is up to date iff its mtime *equals* the
maximum mtime of the sources that produced it, and that the build stamps
that value onto every artifact with `os.utime`. It chose equality over
make-style inequality deliberately: equality prevents a false cache hit.

The implementation carried that value as a Python float. `os.path.getmtime`
returns a C double, and handing a double back to `os.utime` makes CPython
convert it to a `timespec` by **flooring** — landing a nanosecond or two
below the value that was read. On a nanosecond-resolution filesystem the
low bits survive and the double round-trips bit-identically, so equality
holds and the loss is invisible. On a filesystem that truncates to a
coarser quantum, those lost nanoseconds cross a quantum boundary about
half the time, a whole quantum disappears, and the artifact lands *below*
the stamp it was given. It never reports current again.

This was found in a real environment, not reasoned into existence. The
browser-delivery spike `prove-solid-node-runs-in-browser` (repository
`browser-engine`, upstream finding 1, `evidence/groundwork.md` task 1.4)
ran solid-node 0.5.1 at commit `1c03e337` vendored unmodified under
Pyodide 314.0.5 / Emscripten 5.0.3 in headless Chromium 149. Emscripten's
MEMFS stores timestamps at millisecond resolution. A 25-generation probe
replicating the framework's own `write source → max(getmtime) →
back-date → compare` sequence failed freshness in **13 of 25 generations**,
every failure exactly one millisecond low, against 0/25 on native ext4 and
0/25 when source mtimes were forced to whole seconds. A project whose
sources carry sub-second mtimes — anything unpacked from a zip or handed
over through a filesystem handle — got no artifact caching at all.

Two measurements taken while implementing this change sharpen the picture:

- Of 100 consecutive whole-millisecond stamps, **50 lose a millisecond**
  through the float path. The 13-of-25 the spike saw is that coin flip.
- The consequence is worse than lost caching. `build_stls()` loops
  `while True` until nothing reports stale. When nothing can ever stop
  reporting stale, it **does not terminate**: it re-runs OpenSCAD forever.
  Reproduced here in a bounded harness — six consecutive renders of the
  same node, each immediately stale. The spike never saw this because it
  measured freshness directly rather than driving a faceted build loop.

## Decision

The freshness clock is **integer nanoseconds**, end to end, and freshness
stays **exact equality**.

- `AbstractBaseNode.mtime_ns` is the build's value: `max(st_mtime_ns)` over
  the node's tracked source set (ADR-033). `_up_to_date` compares
  `os.stat(path).st_mtime_ns == self.mtime_ns`.
- Every artifact writer stamps with `os.utime(..., ns=…)`:
  `_atomic_write_text` (`.scad`), `StlRenderStart.finish` (the OpenSCAD
  `.stl`), `exact._atomic_export` (`.brep` and the exact `.stl`), and the
  JSCAD adapter. `.stl`, `.brep` and `.scad` obey one rule, decided in one
  predicate (ADR-044 unchanged: an exact node is current only when both of
  its artifacts are).
- `AbstractBaseNode.mtime` remains public and float — the published viewer
  document records it per node — but is now *derived* from `mtime_ns`
  rather than computed beside it, so the two cannot disagree about which
  source file won the `max`. Nothing in the build path decides currency
  from it.

  It is derived as `sec + 1e-9 * nsec`, which is how CPython itself builds
  `st_mtime`, and **not** as `mtime_ns / 1e9`. At the current epoch the
  nanosecond integer is past `2**53`, so converting it to a double before
  dividing rounds to a different last bit than the OS does. Measured:
  `mtime_ns / 1e9` diverges from `os.stat().st_mtime` for **5455 of 20000**
  random timestamps; `sec + 1e-9 * nsec` for **0 of 20000**. The first
  version of this change used the division and was caught by
  `test_build_lock`'s published-document assertion
  (`1787426198.5385911 != 1787426198.5385914`). A published float that
  shifts in its last bit is a silent change to a document consumers
  already read, so the derivation is pinned by its own regression test.

The value the framework stamps is the value that filesystem produced for
the source file, so re-storing it is idempotent wherever sources and
artifacts share a quantum — nanosecond, millisecond, one second, or the
two seconds of a FAT volume. No special case per filesystem, no probe, no
constant to tune.

ADR-006's rule is preserved, not replaced. What changes is the numeric
representation used to carry and compare the stamp.

## Alternatives rejected

- **Tolerance on `st_mtime_ns`** (`0 <= node_ns - artifact_ns <= TOL`), the
  first option the spike proposed. A tolerance must be at least the
  filesystem's quantum to do its job, and that is exactly the width of a
  window in which a real edit becomes invisible: save twice within the
  window — a double save, format-on-save, `git checkout` restoring several
  files — and the artifact built from the earlier content is reported
  current. It contradicts ADR-006's stated reason for choosing equality and
  inverts ADR-033's ranking ("a stale model is wrong; an extra rebuild is
  merely slow"). It would trade the safe failure this finding *observed*
  for an unsafe one it did not. It also does not generalise: sized for
  MEMFS (1 ms) it does nothing for a one-second filesystem; sized for FAT
  (2 s) it is plainly unacceptable.
- **An explicit stamp file** recording the source fingerprint, the spike's
  second suggestion. It is the strongest correctness story — the
  fingerprint is content the framework writes and reads back, so the
  artifact filesystem's timestamp resolution stops mattering entirely — and
  it is the only option that also covers a build directory *coarser* than
  its sources. It was not taken because it costs a new artifact kind that
  ADR-038's per-artifact atomic publication, the unreferenced-artifact
  sweep, and the `.stl`/`.brep` pairing must all learn (a stamp published
  before its artifact reports fresh on a torn build — the unsafe direction,
  reintroduced by the option chosen to avoid it); a file read where a
  `stat` used to do, on every node of every build pass; and a second source
  of truth about currency, which the build-pipeline spec's prohibition on
  recording build state inside artifacts exists to prevent. ADR-006 had
  already weighed sidecar hash storage and rejected it.
- **Quantum-normalised equality** — probe the artifact filesystem's quantum
  and compare against `floor_q(node_ns)`. Exact equality, safe direction,
  and it would cover the mixed-granularity case; but it only differs from
  the chosen design when the artifact filesystem is coarser than the source
  filesystem, and it pays a probe, a per-build-directory cache, and a new
  failure mode when the probe is wrong. Held as the documented escalation
  if that case ever produces evidence.

## Consequences

**Positive**

- A project with sub-second source mtimes caches normally on a
  millisecond-resolution filesystem, and `build_stls()` terminates there.
- The contract is unweakened. Nothing that was invalidating stops
  invalidating; no new state can be reported fresh. The guard tests assert
  this at the smallest change the emulated filesystem can record.
- One predicate still decides freshness, and every mtime-keyed cache —
  `cached_base_mesh`, `exact.cached_shape`, `sources._import_cache`,
  `core/pieces.fingerprint_artifact`, the Manifold cache — is untouched.
  Each compares a file's mtime against its own previously observed mtime,
  on one filesystem, with no `utime` round trip in between, so none was
  ever exposed to this.
- `Builder`'s "the newest source wins" check moved to `mtime_ns` too. As a
  float it could not distinguish two source states closer together than a
  double's ~238 ns resolution at the current epoch; now it can.

**Negative**

- A build directory produced by an earlier version rebuilds once. The old
  float back-date is not a fixed point even on ext4: re-stamping a v8-engine
  build the old way moved **108** artifact stamps, and the next build
  regenerated everything (58.0 s) before settling (7.1 s). This is the same
  one-off cost ADR-033 accepted for its own source-set correction, in the
  safe direction.
- A build directory on a filesystem *coarser* than the one holding the
  sources still cannot be stamped exactly, and its artifacts still report
  stale on every build. That is unchanged from before this ADR and safe in
  direction; no evidence of a user in that position exists.
- Any node-like object must now supply `mtime_ns`. Three in-repo test
  doubles were updated; no public API changed.

## Validation

`tests/test_coarse_filesystem_freshness.py`, against
`tests/coarse_fs.py` — a millisecond-resolution filesystem built by
patching `os.utime` only, leaving reads to the real filesystem, so the
framework's own choice of timestamp API is what the test varies. The stamp
is pinned to the evidence's own `1787402869.540` because half of all
whole-millisecond stamps survive the float path and an arbitrary one would
be a coin flip; the fixture asserts that premise, and its own fidelity to
CPython's conversion, separately.

`tests/test_coarse_filesystem_freshness.py` also pins the public float:
`mtime` must stay bit-identical to `os.path.getmtime` of the newest
tracked source.

Before the change, 4 failed / 7 passed: the exact leaf's artifacts not
current (`…539000000` ns stored against `1787402869.54` requested), an
unchanged leaf re-rendered, and both `build_stls()` paths failing to
converge in three passes. After, 12 passed. Full suite: 555 passed, 2
failed — both pre-existing, both `ModuleNotFoundError: build123d` in this
workspace's virtualenv, unrelated to this change and red at the base
commit too.

On a copy of the real v8-engine project (ext4, 24 artifacts): cold build
55.9 s, no-op rebuild 6.7 s reporting "Published artifacts are already
current", and an edit to `kinematics.py` — a module that defines no node —
advancing exactly the 8 artifacts that import it and leaving the other 16
alone, so ADR-033's invalidation promise is intact under the new
comparison.

What is **not** proven here: MEMFS behaviour under `os.utime(ns=…)`. The
spike's probe measured only the float path, and it never imported
solid-node. The mechanism is well understood — CPython uses `utimensat`
under Emscripten, and MEMFS's millisecond arithmetic on an
already-whole-millisecond value is exact — but that is reasoning, not
measurement, and the harness that could measure it belongs to
`browser-engine`. Until that probe runs, this change is proven to fix a
millisecond-resolution filesystem as emulated natively, and is *expected*
to fix the browser.
