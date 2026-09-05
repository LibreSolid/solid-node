## Context

`docs/performance-improvement.md` fixes 1-3 landed on `perf-cache` and did
what they promised: the faceted path caches one mesh and one Manifold per
`(stl_file, mtime)`, places them with a lazy `transform()`, and an AABB broad
phase culls disjoint pairs. A `manifold3d` intersection of two 660k-face
parts now costs 37 ms warm.

Two things have changed since that report was written. Exact
boundary-representation geometry arrived, and it is the path real projects
now take — the v8-engine suite makes 36 347 intersection calls and not one of
them is faceted. And the assertion surface grew an animation sweep that
recompares the same pairs at up to 73 instants.

The result, measured in `spike/interference/FINDINGS.md`: the v8 suite spends
99% of its 1687 s inside intersection assertions, 66% of it recomputing
verdicts it already had. Separately, `solid_node/test.py` imports the exact
stack at module scope, which costs 2.84 s in every test process — including
the 52 subprocesses of the framework's own `tests/test_meta.py`, about 150 s
of its 269 s suite.

Neither cost is geometry the assertions actually need. Both are addressable
without touching a verdict.

## Goals / Non-Goals

**Goals:**

- No comparison is computed twice in one run when its answer cannot have
  changed.
- No test process loads the exact stack unless an exact comparison runs.
- No placed exact shape or bounding box is rebuilt for a placement already
  built.
- Every verdict, failure message, and epsilon semantic is bit-for-bit what it
  is today. The change is invisible except in time.

**Non-Goals:**

- Any new tolerance, epsilon, or approximation. A faster answer that is
  sometimes a different answer is out of scope by construction.
- Parallelism across pairs or instants (`docs/performance-improvement.md`
  fix 4). It is real, it is orthogonal, and it should be measured after the
  redundant work is gone rather than used to hide it.
- A triangle-level mid-phase between the broad phase and the boolean.
  Measured and rejected: 27 ms of numpy against a 37 ms boolean, because
  manifold already builds the same BVH in C++.
- Any GPU evaluation path, for the reasons recorded in FINDINGS.md and
  already appraised in `docs/performance-improvement.md`.
- Caching across runs (a build cache for tests). It needs a durable
  invalidation story; this change caches within one process only.

## Decisions

### The memo key is the relative placement, and it is exact

A pair's verdict depends on its two geometries and their relative rigid
placement, and on nothing else — emptiness and volume are invariant under a
common rigid transform. So the key is
`(geometry identity 1, geometry identity 2, path, bytes of inv(M1) @ M2)`.

The matrix bytes are compared **exactly**, with no rounding. Rounding to a
tolerance would introduce exactly the thing this change refuses: a placement
difference small enough to be called equal. Bit-identical comparison can only
ever cause a miss, never a wrong hit, and a miss costs what today costs.

The bet this makes is that a static-structure pair recomputes a bit-identical
world matrix at every animation instant, because the same constants flow
through the same arithmetic. The spike's 54% hit rate was measured with the
key rounded at 1e-9, so the exact-byte rate is an upper bound, not a
measurement. **The implementation must report the exact-byte hit rate on the
v8 suite; if it falls materially short of 54%, that is a finding for the
pilot, not a licence to add a tolerance.**

Geometry identity reuses the `(file, mtime)` identity the mesh and Manifold
caches already key on, so a rebuilt part is a new key rather than a stale hit.
A node with no such identity — a `.mesh`-only test double, a flexible leaf
evaluating its binding — is not cached at all.

Alternative rejected: keying on the two absolute world matrices. Simpler, but
it misses the case where an assembly is compared in one placement and later
in another as a whole, and it is no safer.

### The memo lives in the helper every assertion already routes through

`_intersection_stats` and `_placed_intersection` are the two funnels the
spec's "Accelerated intersection evaluation" requirement already names. The
memo sits there, so every assertion inherits it and none of them knows about
it. This is also why the cache is keyed independently of which assertion
asked: the pairwise sweep and the whole-assembly assertion comparing the same
pair in the same placement are the same question.

### The cache is process-scoped and bounded

Module-level, like the existing mesh and Manifold caches, with stale entries
evicted when a geometry identity changes — the same discipline, so there is
one eviction story rather than two. It is bounded by insertion order so a
long-lived `solid develop` process cannot grow it without limit; a test run
never approaches the bound.

### The exact import is deferred by self-replacing callables

Each name `solid_node.test` takes from `solid_node.exact` is bound at module
scope to a deferred wrapper. The first call imports `solid_node.exact`,
resolves the real function, rebinds the module global to it unless a caller
has patched that global meanwhile, and calls through. Every later call is the
resolved function reached by an ordinary global lookup.

The five call sites are therefore unchanged, which matters in a file where
they sit inside carefully documented verdict semantics: the diff is the import
site, not the logic.

**PEP 562 module `__getattr__` was ratified first and does not work here**, and
this is the correction. `solid_node.node` and `solid_node.simulation` are
package facades whose names are only ever read as attributes from outside, and
`__getattr__` serves exactly that. `solid_node/test.py` *calls* these names
from inside its own functions, which is a global-name lookup, and a module's
`__getattr__` is never consulted for one. Verified directly: an internal call
raises `NameError: name 'thing' is not defined` until an outside attribute
access happens to populate the global, after which the same call succeeds. As
ratified, the exact path would have failed on first use.

Patching keeps working because the deferred name is an ordinary module global:
assigning `solid_node.test.intersect_shapes` replaces it, before or after
first use, and the wrapper declines to overwrite a global that is no longer
itself. Known caveat, accepted: before first use the exported name is the
wrapper, so `solid_node.test.intersect_shapes is
solid_node.exact.intersect_shapes` is False. Nothing in the framework or its
tests depends on that identity.

Alternative rejected: `__getattr__` kept for outside readers, with the five
call sites routed through an accessor such as
`_exact('intersect_shapes')(...)`. Behaviourally identical and it preserves
the identity above, but it changes five call sites and puts the same decision
in two places.

Alternative rejected: a function-local `import` at each call site. Smallest
diff, but a patch on `solid_node.test` would no longer be seen, which would
mean dropping a scenario the spec states.

### The exact placement cache keys on shape identity, not object address

`(shape cache key, matrix bytes)`, where the shape cache key is the
`(brep_file, mtime)` pair `_shape_cache` already uses. Keying on `id(shape)`
would be wrong: CPython reuses addresses after collection, so a freed shape's
address could serve a placement for an unrelated one. A shape with no file
identity is simply not cached.

## Risks / Trade-offs

- **A stale hit returns a wrong verdict** → The only way to hit is an exact
  byte match on both geometry identities and the relative matrix. Geometry
  identity carries mtime, so a rebuild misses. This is the risk that matters
  and the design gives it no room; the spec's rebuild and moved-pair
  scenarios test it directly.
- **Bit-identical matrices do not recur, and the hit rate is far below 54%**
  → The change still pays for itself through the deferred import and the
  placement cache, but the headline number would be wrong. Mitigated by
  measuring the real rate during implementation and reporting it, rather than
  by loosening the key.
- **Memory growth in a long-lived process** → Bounded cache; test runs are
  far below the bound.
- **The deferred import hides a broken cadquery installation until later in a
  run** → Already governed by the existing "Deferred imports do not hide a
  broken installation" requirement: the underlying error is raised at first
  use, naming the name.
- **A flexible leaf's binding changes without its identity changing** →
  Excluded from caching outright rather than given a weaker key.

## Open Questions

- The exact-byte hit rate on the v8 suite (see above) — settled by
  measurement during implementation.
- Whether `assertNoSolidInterference`'s batch-union path benefits from the
  same memo, or whether its candidate sweep already visits each pair once per
  instant. To be answered from the implementation's own counters, not
  assumed.
