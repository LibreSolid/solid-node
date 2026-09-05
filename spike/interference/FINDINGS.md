# Spike: where a solid-node test run actually spends its time

Measured 2026-09-05 in the dev VM (AMD Ryzen 9 5900X, 16 threads, no GPU;
virtio display only), venv with trimesh 4.4.9, manifold3d 3.5.2 (TBB, no
CUDA symbols), cadquery 2.7 / OCP 7.8. Bench:
`solid-node/WTs/fast-interference-assertions` at base `abcdd56`.

This spike revisits `docs/performance-improvement.md`, whose fixes 1-3
landed on `perf-cache`. Those fixes worked: the faceted boolean is no
longer the bottleneck. The costs that dominate today are different ones,
and two of them are not geometry at all.

## Finding 1 (largest): the test framework imports the exact stack eagerly

`solid_node/test.py:22` imports `solid_node.exact` at module level, which
imports cadquery at module level.

| import | wall |
|--------|------|
| bare interpreter | 0.04 s |
| `import solid_node.node` | 0.19 s |
| `import trimesh` | 0.73 s |
| `import cadquery` | 2.08 s |
| **`import solid_node.test`** | **2.84 s** |

`python -X importtime -c "import solid_node.test"` attributes 1.52 s to
`solid_node.exact` -> `cadquery`, including 0.32 s of **VTK**, pulled in
by `cadquery.occ_impl.shapes` for visualization the framework never uses.

Consequence in the framework's own suite (1206 tests, **269 s** total):
`tests/test_meta.py` runs 52 cases, each spawning a `solid test`
subprocess, and every one pays that import. The durations show a flat
~2.9 s band -- 30 of the 40 slowest tests are `test_meta.py` cases, all
within 0.2 s of the bare import cost. That is roughly **150 s of the
269 s** spent importing cadquery in subprocesses.

Every project's `solid test` pays 2.8 s of startup too, including a
project modelling entirely in solid2/OpenSCAD that never constructs an
exact shape.

All five exact-kernel call sites in `test.py` (lines 298, 362-365,
872-876, 1196, 1473-1478) are already inside exact-path-only branches, so
nothing but the import site needs to move. The framework already holds
this discipline elsewhere: the `cli-startup-cost` spec,
`tests/test_lazy_test_framework.py`, `tests/test_node_lazy_exports.py`,
and `exact.py`'s own comment deferring build123d for exactly this reason.

## Finding 2: the exact (OCCT) path is 2-16x the faceted one, uncached

`spike/interference/exact_cost.py`, on the real v8-engine `_build` BREPs:

| stage | cost |
|-------|------|
| `cached_shape` import, 43 MB BREP | 242 ms (cached after first) |
| `BoundingBox()` | 0.45-2.6 ms |
| **`placed_shape`** (per solid, per assertion call) | **6-19 ms** |
| `BRepAlgoAPI_Common`, **empty** result | **65-143 ms** |
| `BRepAlgoAPI_Common`, intersecting result | 219-591 ms |

For comparison, `spike/interference/midphase.py` measured the faceted
kernel on much larger meshes: a `manifold3d` `^` over two 660k-face parts
costs **37-48 ms** warm, result read included.

So an empty verdict costs ~10x more through the exact kernel than a
non-empty one costs through the faceted kernel on bigger geometry -- and
`_intersection_stats` recomputes `placed_shape` and the whole boolean on
every animation instant, with no memoization anywhere.

## Finding 3 (negative): a triangle-level mid-phase is NOT worth it

Tested filter: intersect the two world AABBs, pull that overlap box back
into each part's local frame, and keep only triangles whose local AABB
meets it -- rejecting the pair when either survivor set is empty.

On 660k-face v8 parts the vectorized numpy scan costs **27 ms** against a
**37 ms** boolean. Manifold already builds its own BVH in C++ and culls
the same way; a Python-side pre-pass cannot beat it. Rejected.

This also closes the GPU question the pilot raised, consistently with
`docs/performance-improvement.md`'s own appraisal: the faceted kernel is
already cheap and TBB-parallel with no GPU backend upstream, the exact
kernel is OCCT B-rep work that no GPU implementation exists for, and the
one GPU-shaped subproblem (a touch/no-touch predicate) cannot produce the
`volume` the assertions contract on.

## Finding 4: v8 census (pairs, repeats, memoizable work)

`spike/interference/census.py` wraps `_intersection_stats`,
`intersect_shapes`, `placed_shape` and `_cached_manifold`, then runs the
real v8-engine suite through the `solid test` runner, keying each call on
(part names, RELATIVE world placement) -- the identity under which a
verdict stays valid, since intersection emptiness and volume are
invariant under a common rigid transform.

Full v8-engine suite, all tests passing:

| measure | value |
|---------|-------|
| suite wall time | **1687 s (28 min)** |
| `_intersection_stats` calls | 36 347 |
| time inside those calls | **1670 s = 99% of the suite** |
| of which faceted path | 0 calls (v8 is exact throughout) |
| mean cost per call | 46 ms |
| calls repeating a key already computed | **19 747 (54%)** |
| time in those repeat calls | **1108 s = 66% of the suite** |

So the v8 suite is, to within measurement noise, *nothing but* exact
intersection assertions, and two thirds of that work is recomputation of
comparisons whose answer the run already had.

The multiplier is the animation sweep: `test_v8_engine.py` uses
`@testing_steps` up to 73, and an assembly's static structure (block,
heads, cradles, caps) does not move relative to itself between instants,
so those pairs are recompared at full price at every step.

Instrumentation caveat: `occt_common` and `occt_placed` report zero calls
because `solid_node/test.py` binds those functions by name at import, so
patching `solid_node.exact`'s attributes did not intercept them. The
`exact` row is measured at `_intersection_stats`, which encloses them, so
the totals above are unaffected. `occt_import` (66 214 calls, 1.01 s
total) confirms `cached_shape` is a cheap cache hit and not a cost.

## What follows

1. Lazy exact import in the test framework -- ~150 s off the framework's
   own 269 s suite, 2.8 s off every project `solid test` invocation.
2. Memoized intersection verdicts keyed on (geometry identity, relative
   placement, options) -- up to 1108 s off the v8 suite's 1687 s.
3. Cache `placed_shape` and the exact bounding box per (shape, matrix);
   at 6-19 ms per solid per call this is the largest remaining per-call
   overhead once repeats are gone.

Not pursued: the triangle mid-phase (finding 3), and any GPU path.


## Finding 5: after the change -- what moved, and what the cost really is

Measured 2026-09-05 on the same bench, with the change implemented.

| measure | before | after |
|---------|-------:|------:|
| `import solid_node.test` | 2.84 s | **0.79 s** |
| framework suite (`pytest tests`) | 269.2 s | **179.1 s** |
| framework suite test count | 1206 | 1224 (15 added) |
| v8-engine suite | 1687 s | **1623 s** |

The framework's own suite fell by a third, as predicted: 52 `test_meta.py`
subprocesses no longer import cadquery.

The v8 suite barely moved, and the instrumented run says exactly why:

| measure | value |
|---------|------:|
| comparisons via `_intersection_stats` | 36 347 (1609 s) |
| pairs via `_placed_intersection` | **0** |
| keyed evaluations | 30 227 |
| served from cache, EXACT bytes | **6 398 (21%)** |
| computed (keyed) | 23 829, **110 s** |
| **uncacheable -- no geometry identity** | **6 120, ~1499 s** |

### The design's first open question, answered: 21%, not 54%

The spike's 54% was measured with a key of (part NAMES, relative placement
rounded at 1e-9). That key is unsound for a flexible part: a valve spring's
geometry is a function of the driver binding, so two instants at the same
relative placement are NOT the same question, and the census counted them
as repeats. The exact-byte key is 21%, and the difference is mostly the
census having been too generous rather than exactness being too strict.

### Where the time actually is: flexible parts, on the exact kernel

`identity_probe.py` says the uncacheable evaluations are comparisons
involving the 16 flexible `ValveSpring` leaves -- uncacheable BY
CONSTRUCTION, exactly as the spec requires, since their geometry changes
with the instant.

`flexible_cost.py` splits one such comparison (spring against valve, at
three instants):

| stage | cost |
|-------|-----:|
| `spring.shape()` -- flexible evaluation | 48-94 ms |
| **full comparison** | **360-443 ms** |
| verdict | **empty**, every time |

So roughly 300 ms per comparison is the exact kernel placing two shapes
and computing a boolean that comes back EMPTY -- the AABB broad phase
cannot cull it, because a spring's box genuinely encloses the valve stem
it coils around.

### This reopens finding 3

Finding 3 rejected a triangle-level mid-phase after measuring it against
the FACETED kernel: 27 ms of numpy against a 37 ms `manifold3d` boolean.
Against the EXACT kernel the economics invert -- 27 ms against ~300 ms for
an empty verdict, on the pairs that now dominate the suite.

It is not a free win. A tessellated proxy is an approximation of the
B-rep, so a mesh-level "no contact" verdict is only exact-negative for the
solids if the proxies are separated by more than the tessellation
deviation (the framework writes STLs at `tolerance=0.1`,
`angularTolerance=0.1`). That margin argument is the whole design, and it
belongs to the pilot, not to this cycle.

## Finding 6: the mesh path answers the same question 30x cheaper

Finding 5 left the mid-phase reopened. The pilot asked a different and
better question: if the exact kernel is the villain, should the DEFAULT be
the mesh path, with exact comparison an explicit developer opt-in?

`mesh_default.py` measures both paths on the same pair (one valve spring
against its valve) at four instants, separating evaluation from the
boolean:

| | evaluate the part | the boolean | verdict |
|---|---:|---:|---|
| exact (OCCT) | 40-84 ms | **358-418 ms** | empty |
| mesh (molejo -> manifold3d) | 12-24 ms | **1.6-2.9 ms** | empty |

About 430 ms against about 14 ms, with the same verdict at every instant.
Neither path's broad phase could cull the pair, so the 380 ms is real
kernel work producing "no".

Two independent reasons it wins. The boolean itself is two orders of
magnitude cheaper on `manifold3d` than on OCCT for this geometry. And
molejo's native output is a mesh -- building an OCCT solid from the same
spec is the optional expensive extra -- so the exact path pays twice.

Projected on the v8 suite: the 6120 uncacheable flexible comparisons
carrying ~1499 s would cost roughly 86 s, taking the suite from 1622.8 s
to roughly 210 s.

### This closes finding 3 rather than reopening it

There is nothing worth culling ahead of a 2 ms boolean. The triangle
mid-phase is rejected for good: it was only ever a way to avoid the exact
kernel, and routing to the mesh path avoids it outright and by more.

### What it costs, and why it is not this cycle's to spend

The mesh path is not the exact path with the cost removed. It answers a
slightly different question, and four matching instants are encouraging
rather than proof:

- Precision falls to the tessellation tolerance (STLs are written at
  `tolerance=0.1`). Interference thinner than that can be missed, and
  near-contact can read as slight overlap.
- `assertNoSolidInterference` breaks as written. It documents
  "intentionally no public overlap epsilon" and passes a pair only at
  EXACTLY 0.0 mm^3 volume -- an exact-kernel property (ADR-025, ADR-029).
  Meshes produce contact noise, not exactly 0.0, so a flush-abutting
  assembly that passes today would start failing. That assertion needs a
  tolerance-derived epsilon, and choosing it is a product decision.
- `volume_epsilon` changes meaning across the API: today
  `assertBlockedBeyond`/`assertFreeWithin` ignore it on exact pairs and
  warn; under a mesh default it becomes live everywhere.
- Every project suite has to be run both ways and any disagreement
  explained rather than accepted.

That is a ratified behavior change, not a semantics-preserving
optimization, so it cannot ride inside this cycle. It is recorded here as
evidence for the pilot's next one.
