## Why

Artifact freshness is decided by *equality* of floating-point mtimes
(ADR-006, extended by ADR-033/044): every artifact is back-dated with
`os.utime` to the node's maximum source mtime, and is current iff
`os.path.getmtime(artifact) == node.mtime`. On a filesystem whose
timestamp resolution is coarser than a nanosecond, that equality is not a
fixed point: the float detour between reading a source mtime and stamping
an artifact loses a sub-quantum remainder, the filesystem then truncates,
and the artifact lands *below* the value it was asked to carry. Caching
stops working entirely — every build rebuilds everything.

This is not hypothetical. The browser-delivery spike
`prove-solid-node-runs-in-browser` (repository `browser-engine`, evidence
`evidence/groundwork.md`, task 1.4) ran solid-node 0.5.1 at commit
`1c03e337` unmodified under Pyodide 314.0.5 / Emscripten 5.0.3 in headless
Chromium. Emscripten's MEMFS stores timestamps at millisecond resolution.
A 25-generation probe replicating the framework's own
`write source → max(getmtime) → back-date artifact → compare` sequence
**failed freshness in 13 of 25 generations**, every failure off by exactly
one millisecond — against 0/25 on native ext4 and 0/25 when source mtimes
were forced to whole seconds. A real maker's project loaded from a zip or
a filesystem handle carries arbitrary sub-second mtimes, so in that
environment it gets no artifact caching at all.

The failure direction is safe — a quantised artifact can only look *older*
than its sources, so the result is a spurious rebuild and never a stale
artifact reported as fresh — which is why this is a performance and
portability defect rather than a correctness bug. It is nonetheless a
defect: the framework's central invalidation promise is unmet on an entire
class of filesystems, and the only mitigation available today is to demand
that every source file carry a whole-second mtime.

Measured here, natively, rather than recalled: of 100 consecutive
whole-millisecond stamps, **50 lose a millisecond** through the
float→ns→truncate chain (`1787402869.540` becomes `…539999961` ns, which a
millisecond-resolution filesystem stores as `…539`), while
`os.utime(path, ns=…)` round-trips the same value exactly.

## What Changes

- Artifact freshness stops depending on float mtime arithmetic. Source
  mtimes are read as integer nanoseconds (`os.stat().st_mtime_ns`) and
  artifacts are stamped with integer nanoseconds (`os.utime(..., ns=…)`),
  so the value the framework writes is the value it read, with no
  representation loss between them. On any filesystem whose stored
  resolution is the same for sources and artifacts, the stamp is then a
  fixed point — including a millisecond-resolution one — because the
  value being copied was already quantised by that filesystem.
- Freshness stays **exact equality**. No tolerance window is introduced.
  A tolerance is the one option on the table that would convert today's
  safe failure (spurious rebuild) into an unsafe one (an edit landing
  inside the window reported as fresh), and the finding does not ask for
  it: the reproduction is under-caching, not staleness.
- Both artifact kinds are covered. An exact rigid node's `.brep` and
  `.stl` (ADR-044) obey the same rule, as does the `.scad` that a leaf's
  fast path checks.
- The ADR-006 contract is preserved, not replaced: an artifact is fresh
  iff it carries the stamp the framework gave it. What changes is the
  numeric representation used to carry and compare that stamp.
- No behavioral change on a nanosecond-resolution filesystem. Exact
  equality continues to hold there and every existing freshness scenario
  keeps its current outcome.
- One case is knowingly left unfixed: a build directory on a filesystem
  *coarser* than the one holding the sources (sources on ext4, `_build`
  on exFAT or a coarse network mount). No evidence of a user hitting it
  exists, and its behavior remains today's safe one — spurious rebuild,
  never stale. `design.md` records what closing it would cost.

Not in scope, deliberately: the framework's dependency pins, the
serializer, `set_keyframe` publication, `assertNoSolidInterference`'s
`manifold3d` requirement, the `rtree` boundary, and the absent headless
test entry point. Those are separate findings from the same spike and
belong to separate changes.

## Capabilities

### New Capabilities

None. This corrects an existing capability rather than adding one.

### Modified Capabilities

- `build-pipeline`: the **Mtime-equality caching** requirement changes
  from float equality to integer-nanosecond equality, and gains an
  explicit statement that the back-date must be a fixed point on a
  filesystem coarser than nanosecond resolution — so a project whose
  sources carry sub-second mtimes caches normally there. The
  requirement's existing guarantees — invalidation by any contributing
  source, both artifacts current for an exact node, over-approximating
  source sets, no build state recorded inside artifacts — are unchanged.

The `exact-geometry` spec defers artifact currency to `build-pipeline`
and needs no delta.

## Impact

- `solid_node/node/base.py` — `AbstractBaseNode.mtime`,
  `AbstractBaseNode._up_to_date`, `_atomic_write_text`, and
  `StlRenderStart.finish`.
- `solid_node/exact.py` — `_atomic_export` (the `.brep` and exact `.stl`
  writer).
- `solid_node/node/adapters/jscad.py` — the one remaining direct
  `os.utime` back-date.
- Callers of `_up_to_date` are unaffected in shape: `node/leaf.py`,
  `node/exact_leaf.py`, `node/fusion.py`, `node/base.py`,
  `core/builder.py`. There is a single freshness predicate and it stays
  single.
- Caches keyed on `(path, mtime)` — `cached_base_mesh`,
  `exact.cached_shape`, `sources._import_cache`, the Manifold cache in
  `solid_node/test.py`, `core/pieces.py` — are **not** freshness
  decisions. They compare a file's mtime against its own previously
  observed mtime, so quantisation cannot make them wrong. They are
  reviewed but expected to keep their current form.
- ADR disposition is decided after implementation, per the shop's
  framework-change discipline. The likely outcome is one short ADR
  amending ADR-006 — the equality mechanism survives, its numeric
  representation is fixed — plus a wording update to
  `docs/architecture.md`'s "mtime is its clock" commitment and its
  load-bearing-invariant list. Neither is presumed here.
- No new dependency, no new artifact, no build-directory format change,
  and no change to `uniq_id` or artifact naming.
- Originating provenance, to be preserved in the ADR: `browser-engine`
  change `prove-solid-node-runs-in-browser`, upstream finding 1,
  `evidence/groundwork.md`.
