# Framework performance improvement

Test runs on real projects (the `examples/v8-engine` benchmark) are slow
enough to hurt the development loop. This report locates where the time
actually goes and lists framework-level fixes in order of payoff. Unlike
`improvements.md` entries (found incidentally by machinists), these are
dedicated performance work items.

All numbers measured 2026-07-18 in the dev VM (no GPU), venv with
trimesh 4.4.9 + manifold3d 3.5.2, OpenSCAD 2021.01, against the
v8-engine `_build` artifacts (53 STLs, 113 MB).

## Where the time goes

The assertion path in `solid_node/test.py` is:

```
node.mesh                                   # base.py mesh property
  -> trimesh.load(self.stl_file)            # from disk, EVERY access
  -> operation.mesh(mesh) per operation,    # one full-vertex pass each,
     walking node -> ancestors              # node and every ancestor
trimesh.boolean.intersection([a, b])        # per assertion / per pair
  -> is_volume watertight check, both meshes (check_volume=True)
  -> trimesh -> manifold3d conversion, both meshes
  -> exact boolean (Manifold engine)
  -> manifold -> trimesh conversion of the result
```

Measured costs on v8-engine artifacts:

| operation                                | cost |
|------------------------------------------|------|
| `trimesh.load` of one STL                | 100 ms (107k faces) – 1.05 s (camshaft, 660k faces) |
| one `apply_transform` pass, 660k faces   | ~45 ms per operation in the chain |
| `trimesh.boolean.intersection`, one pair | 220 ms (small pair) – 1.06 s (large pair), **even when the result is empty** |

Nothing is cached: a single assertion pays two full loads plus a full
boolean; `assertNoPairwiseIntersections` is O(n²) over leaves and pays
it per pair; `@testing_steps(N)` multiplies the whole thing by N
(v8-engine uses up to `@testing_steps(25)`). The suite's cost is
thousands of full-price load+convert+boolean cycles, almost all of it
redundant recomputation of identical intermediate products.

The boolean engine itself is not the problem: manifold3d is already
installed and is trimesh's preferred engine — exact, multithreaded
(TBB), state of the art. The problem is how often it is invoked and how
much conversion work surrounds each invocation.

## Fixes, in order of payoff

### 1. Cache loaded meshes; compose operations into one matrix

`AbstractBaseNode.mesh` reloads the STL from disk on every access and
applies each operation (own + every ancestor's) as a separate
`apply_transform` pass.

Fix: a module-level cache of the immutable base mesh keyed on
`(stl_file, mtime)`; `.mesh` returns a copy with a **single** composed
4×4 world matrix applied — the same operation composition the web
viewer already does (improvements.md #23, commit 23bd5e1), so mesh and
viewer placement share one code path.

Payoff: removes 100 ms – 1 s of disk load per mesh access plus all but
one vertex pass. Semantics unchanged.

### 2. AABB broad-phase before any exact boolean

Before running a boolean, transform only the 8 corners of each part's
local bounding box by its composed world matrix. The axis-aligned box
of those corners is a conservative superset of the part's world AABB —
if two parts' boxes are disjoint, their intersection is exactly empty
and the boolean can be skipped in microseconds.

Applies to every intersection-based assertion:
`assertNotIntersecting`, `assertFreeWithin`,
`assertNoPairwiseIntersections` (in an assembly most leaf pairs are
nowhere near each other — the O(n²) sweep collapses to booleans on
genuinely adjacent pairs only), and `assertBlockedBeyond` /
`assertIntersecting` fail fast with a clear message when the boxes are
disjoint.

Payoff: expected 10–50× on the pairwise sweep alone. Exact-negative,
never changes a verdict.

### 3. Cache Manifold objects; lazy transforms; skip the round trip

`trimesh.boolean.intersection` per call: re-checks watertightness of
both meshes (`check_volume=True` — itself nontrivial), re-converts both
trimeshes to `manifold3d.Manifold`, runs the boolean, and converts the
result back to a trimesh even when the caller only needs
`is_empty` / `volume`.

Fix: cache one `Manifold` per `(stl_file, mtime)` (watertightness
validated once at cache fill). Per placement, apply the composed world
matrix with `Manifold.transform()` — **lazy** in Manifold, essentially
free. Intersect with `a ^ b` and read `result.is_empty()` /
`result.volume()` directly; only convert back to a trimesh when an
assertion fails and diagnostics are wanted.

Payoff: amortizes conversion + watertight checks to once per part per
suite instead of once per boolean; for `@testing_steps(25)` sweeps the
per-instant cost drops to the boolean core alone. See spike results
below.

### 4. Parallelism

- The pairwise sweep and independent test instants are embarrassingly
  parallel (process pool over pairs/instants). Caveat: Manifold already
  multithreads a single boolean via TBB, so gains are sub-linear —
  measure before committing.
- `build_stls` renders STLs strictly one at a time
  (`StlRenderStart` → `wait()` → retry). Launching all pending
  `openscad` jobs concurrently uses every core on a cold build.

### 5. Faster STL generation (OpenSCAD backend)

The VM has OpenSCAD 2021.01, which renders with CGAL. Recent OpenSCAD
releases support `--backend Manifold`, commonly 10–100× faster on
render. `stl_builder_command` could probe for support and add the flag.

Longer term: the framework holds a solid2 CSG tree for every node; it
could evaluate that tree in-process with manifold3d and skip OpenSCAD
entirely for STL production. That is a real project (primitive mapping,
`$fn` semantics, extrusions), not a tweak — noted, not scheduled.

### 6. Opt-in accuracy reduction and assertion memoization

- A test-resolution profile (lower `$fn` for spatial assertions) would
  cut face counts ~10×, but it changes tolerance semantics for
  tight-fit contracts (`assertBlockedBeyond` epsilons) — only viable as
  an explicit per-node opt-in.
- STL identity is already content-keyed (`uniq_id`); passing assertions
  could be memoized on `(stl ids, world matrices, assertion, params)`
  and skipped when nothing changed — a build cache for tests. In the
  TDD loop (touch one part, rerun suite) only pairs involving the
  changed part would recompute.

## GPU appraisal

The GPU is not the lever here:

- There is no production-ready GPU path for **exact** mesh booleans
  usable from Python. Manifold itself started as a CUDA project and
  dropped the GPU backend around v2.0 — CPU+TBB matched it with far
  less complexity.
- What a GPU could accelerate is *approximate* interference checking
  (SDF / voxel sampling via Warp, PyTorch). But the assertions are
  contracts about exact geometry with small `volume_epsilon` values,
  and per-pair host↔device transfer at these mesh sizes would eat much
  of the gain.
- The dev VM has no GPU available anyway.

Fixes 1–3 are semantic no-ops that remove redundant work; together they
are expected to yield one to two orders of magnitude on real suites
before any hardware question matters.

## Spike results: mesh/Manifold cache (fixes 1 + 3)

Spike: `spike/mesh_manifold_cache.py`. An
`assertNoPairwiseIntersections`-shaped workload — 8 size-diverse
v8-engine parts (camshaft included), 2 animation instants, 56 pair
checks, placements stacked so neighbours overlap and distant pairs
don't (7 of 56 pairs genuinely intersect) — run four ways. All four
modes produced identical verdicts (empty flags equal, volumes within
1e-3 relative).

| mode | what it models | time | speedup |
|------|----------------|------|---------|
| A baseline | today's framework path | 24.89 s | 1× |
| B trimesh cache | fix 1 alone | 10.92 s | 2.3× |
| C manifold cache | fixes 1+3 | 0.61 s (+1.47 s one-time cache fill) | **41×** |
| D C + broad-phase | fixes 1+2+3 | 0.09 s (42/56 pairs culled) | **288×** |

Conclusions:

- Fix 1 alone (skip disk reloads, one composed transform pass) already
  gives 2.3×, but the dominant remaining cost is trimesh's per-call
  boolean overhead: watertight re-checks, trimesh→Manifold conversion,
  and the result round trip.
- Fix 3 removes that: with Manifolds cached per STL and placed via lazy
  `transform()`, the exact boolean core itself is cheap — 56 exact
  intersections on real geometry in 0.61 s. The one-time cache fill
  (1.47 s for 8 parts incl. the 660k-face camshaft) amortizes over a
  suite in the first handful of assertions.
- Fix 2 stacks multiplicatively: 75 % of pairs culled by the AABB
  broad-phase in this workload, and the fraction grows with assembly
  size (the sweep is O(n²) but real contacts are O(n)).
- `Manifold.volume()` clamps epsilon-thin slivers to zero, which is the
  same distinction `volume_epsilon` exists to make; the flush-contact
  noise cases just need the existing epsilon semantics preserved when
  porting the assertions (compare volume, not `is_empty`, when
  `volume_epsilon > 0`).

## Implementation

Fixes 1-3 landed on branch `perf-cache`, one commit each, TDD'd against
the framework's own test suites:

- `1c92147` — fix 1: `_cached_base_mesh` (module-level cache keyed on
  `(stl_file, mtime)`) and `_compose_world_matrix` in
  `solid_node/node/base.py`; `Rotation`/`Translation` gain a
  `.matrix()` method (`solid_node/node/operations.py`) resolving
  through `as_number()` at access time. `AbstractBaseNode.mesh` now
  returns a copy of the cached base mesh with one composed matrix
  applied, instead of reloading from disk and applying each operation
  as a separate pass.
- `e292625` — fix 2: `_intersection_stats`/`_fast_geometry`/
  `_world_bounds`/`_boxes_disjoint` in `solid_node/test.py`. An AABB
  broad-phase culls disjoint pairs before any boolean runs, for
  `assertNotIntersecting`, `assertFreeWithin`,
  `assertNoPairwiseIntersections` (skip, pass) and `assertIntersecting`,
  `assertBlockedBeyond` (expect_intersect=True) (fail fast, same
  messages).
- `d725d23` — fix 3: `_cached_manifold` (module-level Manifold cache
  keyed the same way as fix 1's mesh cache, built from the same
  loaded trimesh mesh) in `solid_node/test.py`. `_intersection_stats`
  places each cached Manifold with a lazy `.transform()` and
  intersects directly (`a ^ b`), reading `is_empty()`/`volume()`
  without a round trip back to trimesh.

**Deviation from this report's CRITICAL semantics note** (fix 3): the
note above says a `volume_epsilon == 0` verdict should treat
`is_empty() or volume() == 0` as empty. Built against the real
flush-contact fixtures in `tests/meta_project/flush_strict.py` and
`flush_keyed_strict.py`, that folding regresses improvements.md #21
(`VolumeEpsilonMetaTest` in `tests/test_meta.py`): a legitimate flush
abutment reproducibly comes back **non-empty** with **exactly**
0.0mm³ volume in BOTH trimesh and Manifold (verified directly against
the built geometry) — #21's strict default is specifically that this
must still be reported as a foul, forcing an explicit `volume_epsilon`
opt-in. Folding `volume() == 0` into "empty" silently defeats that
feature for every exact-zero-volume noise sliver. The spike's own
verdict-agreement check happened not to exercise an exact-zero,
non-empty case, so it didn't surface this before the report was
written.

Implemented instead: `is_empty` is Manifold's own `is_empty()` alone
(empirically identical to trimesh's `is_empty` on this framework's
flush geometry); `volume` is read only when non-empty. A
`volume_epsilon > 0` comparison is unaffected either way, since 0.0 is
always `<=` any positive epsilon. Flagged here for ratification; if
the chief engineer wants the literal folding for some other reason,
`VolumeEpsilonMetaTest`'s two strict-default tests
(`test_flush_faces_reported_without_epsilon`,
`test_flush_shoulder_noise_reported_without_epsilon`) would need to be
re-ratified first.

### Perf sanity check

Adapted the spike's workload (8 size-diverse v8-engine parts including
the 660k-face camshaft, 2 animation instants, 56 pair checks) against
the actual landed code (`solid_node.test._intersection_stats` over
real `AbstractBaseNode.mesh`-backed nodes, not the spike's standalone
reimplementation), reading the `examples/v8-engine/_build/root` STLs
read-only:

| mode | time | speedup |
|------|------|---------|
| baseline (today's pre-fix path) | 25.21 s | 1× |
| fixes 1+2+3, cold cache (fill included) | 1.93 s | 13× |
| fixes 1+2+3, warm cache | 0.10 s | 253× |

All 56×2 verdicts (empty flag, volume within 1e-3 relative) agreed
with the baseline in both runs — consistent with the spike's own
41×/288× figures (this run's cold-cache number is lower than the
spike's C mode because it includes the AABB culling from the first
pass, mixing fixes 2+3's cost together; the warm-cache number isolates
steady-state suite behavior once the caches are populated, matching
the spike's D mode closely).
