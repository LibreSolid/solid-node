## Context

### The contract as it stands

`AbstractBaseNode._up_to_date` (`solid_node/node/base.py:693`) is the single
freshness predicate in the framework:

```python
def _up_to_date(self, path):
    return (
        os.path.exists(path) and
        os.path.getmtime(path) == self.mtime
    )
```

`self.mtime` (`base.py:483`) is `max(os.path.getmtime(p) for p in self.files)`
over the node's import-closure source set (ADR-033). Every artifact writer
back-dates to that value with a float:

| Writer | Location | Artifact |
| --- | --- | --- |
| `_atomic_write_text` | `node/base.py:33` | `.scad` |
| `StlRenderStart.finish` | `node/base.py:716` | `.stl` (OpenSCAD path) |
| `_atomic_export` | `exact.py:89` | `.brep` and exact `.stl` |
| `JScadNode.generate_stl` | `node/adapters/jscad.py:57` | `.stl` (JSCAD path) |

All eleven call sites of `_up_to_date` (`node/leaf.py`, `node/exact_leaf.py`,
`node/fusion.py`, `node/base.py`, `node/adapters/jscad.py`,
`core/builder.py`) go through that one predicate. There is one place to fix.

### Why the equality breaks

The float is the defect, not the filesystem. Reading a source mtime with
`os.path.getmtime` yields a C double. Handing that double back to
`os.utime` makes CPython convert it to a `timespec` by **flooring**, which
lands a nanosecond or two below the value that was read. On a
nanosecond-resolution filesystem the low bits survive, the double
round-trips bit-identically, and equality holds — which is why this has
never been seen natively. On a filesystem that truncates to a coarser
quantum, those "harmless" lost nanoseconds cross a quantum boundary
roughly half the time and a whole quantum disappears.

Measured natively for this change (`.venv` CPython, ext4):

```
whole-ms stamps that lose a ms through the float path: 50 / 100
   requested ms 501  float 1787402869.501     -> ns …500999927  -> stored ms 500
   requested ms 504  float 1787402869.504     -> ns …503999948  -> stored ms 503
   requested ms 505  float 1787402869.5049999 -> ns …504999876  -> stored ms 504
ns API round trip exact: True  (1787402869540000000)
float API stored ns:     1787402869539999961   (float compare still equal on ext4)
```

That 50% matches the spike's observed 13/25, and the mechanism explains the
whole pattern the spike recorded: whether a given millisecond survives
depends only on which side of the integer its double representation falls.

### The originating reproduction

`browser-engine`, change `prove-solid-node-runs-in-browser`, upstream
finding 1, evidence `evidence/groundwork.md` (task 1.4) and
`evidence/groundwork-probes.json`. Environment: solid-node 0.5.1 at commit
`1c03e337` vendored unmodified, Pyodide 314.0.5 → CPython 3.14.2,
Emscripten 5.0.3, headless Chromium 149 via Playwright 1.61, cadquery
2.8.0, build123d 0.11.1. MEMFS stores timestamps at millisecond resolution
and truncates the remainder (quantisation sweep in the evidence:
`123456789 ns → 123000000 ns`, `999999999 → 999000000`).

Result: **13 of 25 generations** of the framework's own
`write source → max(getmtime) → back-date → compare` sequence failed
freshness, every failure exactly one millisecond low; 0/25 on native ext4;
0/25 when source mtimes were forced to whole seconds. Across 40 further
samples the stored artifact mtime **never exceeded** the node mtime.

Two properties of that evidence shape this design. First, the failure
direction is one-sided and safe: quantisation can only make an artifact
look older, so the observed failure is a wasted rebuild, never a stale
artifact served as fresh. Second, the browser probe replicated the code
path faithfully but did not import solid-node — the framework was not yet
installed at that stage — so it measured the float API only. Nothing in
the recorded evidence tells us how MEMFS behaves under `os.utime(ns=…)`.

## Goals / Non-Goals

**Goals:**

- A project whose source files carry arbitrary sub-second mtimes caches
  its artifacts normally on a millisecond-resolution filesystem.
- The safe failure direction is preserved absolutely: no change may make
  it possible for a modified source to be reported current.
- Native behavior is bit-for-bit unchanged. Every existing freshness
  scenario in `openspec/specs/build-pipeline/spec.md` keeps its outcome.
- `.stl`, `.brep` (ADR-044) and `.scad` are covered by one rule, decided
  in one predicate.
- A native, red-first regression test that fails on today's code and
  passes after the change, without requiring a browser or Pyodide.

**Non-Goals:**

- Replacing mtime with content hashing. ADR-006 weighed and rejected
  that; nothing in this finding reopens it.
- Any of the spike's other seven upstream findings.
- Changing dependency pins, the serializer, the export document, or the
  test framework.
- Making solid-node run in a browser. This change removes one obstacle
  found there; the delivery architecture remains the pilot's open choice.
- Optimising the freshness check. It stays one `stat` per file.

## Decisions

### The fork

Three shapes were considered. The finding named the first two; the third
came out of reading the code and measuring the mechanism.

#### (a) Tolerance-based comparison on `st_mtime_ns`

Read both sides as `st_mtime_ns` and accept the artifact when
`0 <= node_ns - artifact_ns <= TOLERANCE`.

The tolerance has to be at least the filesystem's quantum to do its job:
1 ms for MEMFS, 1 s for ext3 or HFS+, 2 s for FAT/exFAT. That number is
also, exactly, the width of a window in which a **real source edit is
invisible**. Concretely: build the project, then save the file again
within `TOLERANCE` of the previous save — a double save, a
format-on-save, `git checkout` restoring several files, a script
generating sources — and the artifact built from the earlier content is
reported current. The model is silently stale.

That directly contradicts the two contracts this area rests on. ADR-006
chose equality over make-style inequality precisely because "equality
prevents false cache hits", and ADR-033 states the framework's ranking of
failures without qualification: "A missing dependency is a worse failure
than a spurious one. A stale model is wrong; an extra rebuild is merely
slow." A tolerance trades the safe failure this finding *observed* for an
unsafe failure it did not.

It also does not survive its own generalisation. Sized for MEMFS (1 ms) it
does nothing for a 1-second filesystem; sized for FAT (2 s) it is plainly
unacceptable. There is no single number that is both sufficient and safe.

**Variant (a′), quantum-normalised equality.** Probe the artifact
filesystem once per build directory (stamp a temp file, read it back),
learn its quantum `q`, and require exact equality against
`floor_q(node_ns)`. This is exact equality, not a tolerance, and it keeps
the safe direction — but it only differs from (c) when the *artifact*
filesystem is coarser than the *source* filesystem, and it pays for that
with a probe, a per-build-dir cache, and a new failure mode when the probe
is wrong. Held as the documented escalation if that case ever produces
evidence.

#### (b) An explicit stamp file

Write a sidecar per artifact (or per node) recording the source
fingerprint — the max source `st_mtime_ns`, or a digest over
`(path, size, mtime_ns)` across `node.files` — and decide freshness by
comparing that recorded value for exact equality with the current one.

This is the strongest correctness story available. The fingerprint is
*content the framework wrote and reads back*, so the artifact filesystem's
timestamp resolution stops mattering entirely — MEMFS, FAT, and a coarse
network mount all behave identically, and full source precision is
preserved rather than quantised away. It is the only option that also
closes the mixed-granularity case.

It costs more than the finding justifies:

- **A new artifact kind.** ADR-038's per-artifact atomic publication, the
  build-directory sweep that removes unreferenced files, the
  `.stl`/`.brep` pairing of ADR-044, and the `.stl.lock` protocol all have
  to learn about it. A stamp must be published *after* its artifact and
  removed *with* it, or a torn build reports fresh — which is the unsafe
  direction, reintroduced by the option chosen to avoid it.
- **A read where a `stat` used to do.** Freshness is checked on every node
  on every pass of `build_stls()`; `core/builder.py:_artifacts_are_current`
  walks the whole tree. ADR-006 rejected content hashing partly on this
  cost and explicitly listed "requires hash storage mechanism (database or
  sidecar files)" as a con.
- **A second source of truth about currency.** The build directory would
  carry both a stamp and a back-dated mtime, and they can disagree. The
  `build-pipeline` spec currently forbids recording build state inside
  published artifacts for exactly this reason; a sidecar is adjacent
  enough to that boundary to need its own ratification.
- **It does not remove the float defect**, only routes around it. The
  back-date would still be wrong; anything still reading mtimes — the
  `(path, mtime)` caches, `solid develop`'s watch loop — would keep the
  lossy value.

#### (c) Integer-nanosecond fidelity end to end — **recommended**

Carry the mtime as `int` nanoseconds everywhere the framework touches it:
`os.stat(p).st_mtime_ns` to read, `os.utime(path, ns=(atime_ns, mtime_ns))`
to stamp, integer `==` to compare.

The float detour disappears, and with it the loss. The value the framework
stamps is the value the filesystem itself produced for the source file, so
re-storing it is idempotent on any filesystem where sources and artifacts
share a quantum — the value has *already been quantised by that
filesystem*. MEMFS reads `…540000000 ns`, is asked for `…540000000 ns`,
stores 540 ms, returns `…540000000 ns`. Equality holds; caching works. The
same argument covers a 1-second or 2-second filesystem without a special
case, which is what neither tolerance number could do.

Why it is preferred here:

- **It preserves the contract instead of weakening it.** ADR-006's "fresh
  iff the artifact carries the stamp we gave it" survives verbatim.
  ADR-033's ranking is untouched: nothing new can be reported fresh.
- **It is smaller than either alternative.** One predicate, one property,
  four writers, no new artifact, no new I/O, no probe, no tolerance
  constant to defend.
- **It strictly improves the mixed-granularity case it does not fix.**
  Where the artifact filesystem is coarser than the source filesystem, the
  behavior stays today's: the stamp falls short, the artifact reports
  stale, the node rebuilds. Safe, and no worse than now.
- **It fixes the reported reproduction at its actual cause.** The spike
  measured a float-conversion loss, not a filesystem incapacity. MEMFS can
  store what solid-node needs; solid-node is not asking for it correctly.

The honest cost is stated in Risks: (c)'s effectiveness in the actual
browser environment is *inferred from the mechanism*, not measured, and
the measurement is not this repository's to take.

### `node.mtime` gains an integer sibling rather than changing type

`AbstractBaseNode.mtime` is public surface: `StlRenderStart` carries it,
the published `viewer.json` document records a per-node `mtime`
(ADR-031/034), and project code may read it. Changing its type from float
to int would be a breaking change with a blast radius far wider than this
finding.

So `mtime` keeps returning a float and a new `mtime_ns` property returns
`max(os.stat(p).st_mtime_ns for p in self.files)`. The freshness predicate
and all four writers move to `mtime_ns`; the published document and any
external reader keep the float they have today. `mtime` is redefined as
`mtime_ns / 1e9` so the two can never disagree about which file won the
`max`. Whether `mtime` should eventually be deprecated in favour of
`mtime_ns` is a question for a later change, not this one.

### The red-first proof runs natively, by emulating the filesystem, not the browser

The test may not require Pyodide, a browser, or a real MEMFS: this is the
framework's suite, and a test nobody can run is not a regression test.

The emulation is narrow and faithful because the loss has exactly one
mechanism. A test fixture patches **only `os.utime`** with a wrapper that
reproduces what a millisecond-resolution filesystem does — resolve the
requested value to nanoseconds the way CPython does (floor, for the float
form; verbatim, for the `ns=` form), truncate to whole milliseconds, then
delegate to the real `os.utime` with that value. Sources are stamped to
whole-millisecond mtimes the same way. Reads are left completely alone:
ext4 stores what the wrapper computed and returns it faithfully, so the
test observes a genuine filesystem doing genuine `stat` calls, with only
the write quantisation simulated.

This makes the fixture a model of the *filesystem*, while the framework's
choice of timestamp API — the thing under test — stays entirely in the
framework. Today's float call loses the millisecond through the wrapper
exactly as it does in MEMFS; tomorrow's `ns=` call does not.

**Determinism.** Half of all whole-millisecond stamps survive the float
path, so a randomly chosen stamp would make the test flaky at 50%. The
fixture pins a stamp verified to fall on the losing side — the evidence's
own `1787402869.540`, whose double is `1787402869.5399999619…` and whose
floor is `…539999961 ns` → 539 ms. The test asserts the framework's
verdict, and separately asserts the fixture's own premise (that this stamp
does lose a millisecond through the float path), so a future CPython or
platform that changed the conversion would fail loudly as a broken
premise rather than silently passing a test that proves nothing.

**Coverage.** Red-first on: a faceted rigid leaf's `.stl`; an exact
leaf's `.brep` and `.stl` together (ADR-044 requires both current); a
second build reporting the artifacts current and performing no work. Plus
a guard test that on an unpatched filesystem exact equality still holds
and a genuinely edited source still invalidates — the anti-regression for
the safe direction.

### The `(path, mtime)` caches are reviewed, not changed

`cached_base_mesh` (`node/base.py:52`), `exact.cached_shape`,
`sources._import_cache`, `core/pieces.py`, and the Manifold cache in
`solid_node/test.py` key on `(path, mtime)`. None is a freshness decision:
each compares a file's mtime against the mtime observed when that same
file was last read, on the same filesystem, with no `utime` round trip in
between. Quantisation cannot make them serve wrong content — a coarser
clock can only merge two distinct states into one key if the file changed
*within one quantum*, which is the pre-existing granularity limit of every
mtime cache and is not introduced here. They are checked during
implementation and expected to stay as they are.

## Risks / Trade-offs

- **[(c) is validated by mechanism, not by measurement in the target
  environment.]** The spike's probe never exercised `os.utime(ns=…)` under
  Emscripten. The reasoning is strong — CPython uses `utimensat` there, and
  MEMFS's millisecond arithmetic on an already-whole-millisecond value is
  exact — but it is reasoning. → The native emulation proves the framework
  side conclusively. Confirming the MEMFS side needs a probe in
  `browser-engine`, which owns that harness and is out of this
  repository's scope. Named as an open question for the pilot rather than
  quietly assumed; if it comes back negative, (a′) or (b) is the fallback
  and this change's spec would have to be revisited before archival.
- **[The emulation could be unfaithful and prove nothing.]** A fixture
  that models the filesystem wrongly can go red for its own reasons. →
  The fixture asserts its own premise separately (the pinned stamp loses a
  millisecond through the float path; the `ns=` path is a fixed point) and
  patches one function only, leaving reads to the real filesystem.
- **[`mtime` and `mtime_ns` drift apart.]** Two properties over the same
  file set can disagree if maintained independently. → `mtime` is derived
  from `mtime_ns`, not computed in parallel.
- **[A build directory carried over from an older version rebuilds
  once.]** Artifacts stamped through the float path sit a few nanoseconds
  below the new integer comparison and report stale. → One rebuild, the
  same consequence ADR-033 accepted for its own source-set correction, and
  the safe direction. Stated in the spec deltas so it is not a surprise.
- **[Mixed-granularity build directories remain uncached.]** Sources on
  ext4, `_build` on exFAT or a coarse network mount, still rebuild every
  time. → Unchanged from today, safe in direction, no evidence anyone has
  hit it. (a′) and (b) are documented above as the escalation if evidence
  appears.
- **[Scope creep into ADR-006's rejected options.]** The word "stamp file"
  is one step from content hashing, which ADR-006 weighed and rejected. →
  (b) is recorded as analysed-and-not-taken rather than deferred work, so
  a later reader sees why.

## Migration Plan

No migration. No data format, artifact name, `uniq_id`, published document
or public signature changes. Existing build directories self-heal by
rebuilding once on first use of the new version; a rollback simply
rebuilds once in the other direction. No project source change is needed,
and the whole-second-mtime workaround the browser spike adopted becomes
unnecessary rather than wrong.

## Open Questions

1. **Ratify (c) alone, or (c) plus a fallback for coarser artifact
   filesystems?** The recommendation is (c) alone, leaving (a′)/(b) as
   documented escalations. The pilot may prefer to close the
   mixed-granularity case now.
2. **Who confirms MEMFS under `os.utime(ns=…)`, and does this change wait
   for it?** The probe belongs to `browser-engine`. This change can be
   ratified, implemented, and validated natively without it; the browser
   claim would then be "expected to fix" until that repository measures
   it. The alternative is to hold the cycle until the probe reports.
3. **Should `mtime` be deprecated in favour of `mtime_ns`?** Out of scope
   as proposed — `viewer.json` publishes the float and project code may
   read it — but the pilot may want the deprecation started here rather
   than leaving two properties indefinitely.
4. **Does the tolerance option deserve a second hearing?** It is rejected
   above on the ADR-006/033 safety ranking. If the pilot values caching on
   a coarse filesystem the framework cannot otherwise serve more than the
   strictness of the equality contract, that ranking is the pilot's to
   change — not an agent's.
