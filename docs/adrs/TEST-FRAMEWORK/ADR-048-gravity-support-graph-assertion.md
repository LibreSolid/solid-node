# ADR-048: Gravity Support Graph Assertion

**Status:** Accepted
**Date:** 2026-08-22
**Depends on:**
- [ADR-011: Animation Testing Decorators](./ADR-011-animation-testing-decorators.md)
- [ADR-025: Perturbation-Based Kinematic Fit Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md)
- [ADR-029: Manifold Cache and AABB Broad-Phase](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)
- [ADR-040: Topmost-Rigid Assembly Integrity](./ADR-040-topmost-rigid-assembly-integrity.md)

## Context

`assertNoSolidInterference` catches printed solids that share material, and
has measurably improved agent consistency. The inverse defect has no
assertion at all: a part placed in space with nothing holding it against
gravity. The pilot reports it recurring across shop mechanical projects — an
agent positions a bracket at plausible coordinates, every existing contract
passes, and the assembly cannot exist.

The framework already owns every primitive the question needs. Selection of
topmost rigid solids, cached Manifolds placed by composed world matrices,
exact placement through the B-rep kernel, conservative world AABBs, a
sweep-and-prune broad phase (ADR-029/040), and translate-then-intersect
perturbation semantics (ADR-025) are all in `solid_node/test.py` already.
What is missing is the question, not the machinery.

## Decision

Add `TestCase.assertAssemblySupported(node, gravity=(0, 0, -1), max_drop=1.0,
ground=None, supports=None)` as an ordinary project assertion, selecting
solids and reading placement exactly as `assertNoSolidInterference` does.
Zero or one selected solid passes without geometry work.

### Support is a drop test, not a proximity test

Solid `i` is directly supported by solid `j` when `i`, displaced by `max_drop`
along the normalized world gravity vector, intersects `j` with positive
volume. The displacement is one world-frame translation folded into the
placement matrix (`T @ M`), so it reuses the lazy `transform()` the
interference path already trusts and costs a matrix product rather than a
re-conversion. Zero-volume boundary contact after the drop is not support,
mirroring the "positive volume is material" rule of the interference
assertion.

The rejected alternative was an epsilon-contact connectivity graph. It is
orientation-independent, but weaker — a sideways touch would count as "held" —
and it requires a distance tolerance with no physical meaning. Mesh proximity
is also vertex-sampled and can miss face-to-face closeness, while a drop onto
a genuine resting face yields contact area × drop, far above float noise, so
no epsilon is needed at all.

### Transitive grounding over the support graph

Direct support is insufficient: a part resting on a floating part still falls.
The drop edges form a directed graph, a grounded set is seeded, and
groundedness propagates from supporter to supported by plain BFS. Every
selected solid must end grounded; the failure names all that do not, with the
drop distance and gravity direction used. A mutual-lean cycle resolves
correctly by construction — it is grounded exactly when some member rests on
something grounded, and never by leaning on itself.

### Grounded seeds default to the assembly's lowest solids

With `ground=None` a solid is a seed when its conservative world extent along
gravity comes within `max_drop` of the assembly's furthest extent along
gravity. The default contract is therefore "the assembly holds itself
together", which is the right reading of a model floating in CAD space and
also covers an assembly resting on an unmodelled floor: the parts that would
touch the floor are the lowest ones. The drop distance doubles as the seed
tolerance so seeding has the assertion's own resolution.

`ground=<node or sequence>` replaces the default outright. Each entry resolves
to selected solids — up to the enclosing solid for a feature, down to the
selected solids beneath an assembly — and an entry resolving to none is a loud
error, not a silent pass. A ground *plane* parameter was rejected: the
lowest-solid default plus explicit anchors covers its use cases without a
second coordinate-convention knob.

### `supports` declares edges the geometry cannot prove

`supports=[(supported, supporter), ...]` adds explicit edges after the same
resolution. This is the visible escape hatch for press fits, glue and friction
— physics the drop test deliberately does not model — and it keeps the
exemption reviewable in project test code instead of buried in a tolerance. A
declared supporter must still be grounded transitively; a declared edge
grounds nothing by itself. Unresolvable pairs are loud errors.

### Routing and broad phase mirror the interference assertion

A pair of exact solids is intersected by the B-rep kernel; any other pair,
including a mixed one, goes through the cached Manifolds. The broad phase is
the existing sweep-and-prune, run over the displaced boxes and the placed
boxes at once so that a pair spanning the two halves is exactly a directed
displaced-versus-placed overlap; pairs inside one half, and a solid paired
with its own drop, answer no question and are discarded. Only surviving pairs
meet a Boolean.

### Knobs

`gravity` is any nonzero vector, normalized internally; the zero vector is a
loud error. `max_drop` (mm, default 1.0) must exceed the design's vertical
clearance play and stay below the thinnest supporting feature's thickness plus
its gap; non-positive values are loud errors. The default sits in the common
window between typical clearances (≤ 0.5 mm) and typical printed walls
(≥ 1.2 mm), and the docstring states the rule.

## Consequences

- Projects gain a one-line whole-assembly contract against the floating-part
  defect, usable from a project's first leaf: a single selected solid passes
  trivially, as with assembly integrity.
- The assertion claims support reachability and nothing else. No force or
  torque balance, no toppling analysis, no friction or adhesion, no
  lateral-restraint analysis — a part free to slide or tip over passes. The
  docstring and `docs/testing.rst` state those exclusions, because a passing
  support test must not read as a stability certificate. That blind spot was
  the next failure the pilot met in practice; the force and torque balance it
  excludes was added as a second phase of the same method by
  [ADR-049](./ADR-049-static-equilibrium-as-lp-feasibility.md), which leaves
  the reachability decision recorded here unchanged.
- `max_drop` is a real judgement the maker must make. Too small and a part
  sitting in its clearance gap reads as floating; too large and the dropped
  solid tunnels through a thin support and reads as floating again. The
  framework pins both edges of that window in its own tests rather than
  leaving the limitation latent.
- Legitimate friction and adhesion holds fail the drop test by design and must
  be declared in `supports`. That is the intended trade: an exemption that is
  visible in the test beats a tolerance that hides one.
- Gravity assumes the model's orientation is physical; the `gravity` knob
  covers models built in another orientation, and the default matches the
  framework's Z-up convention.
- Cost is N cheap transforms plus box computations, with Booleans proportional
  to interacting pairs — the same output-sensitive profile as assembly
  integrity, since the placement reuses the Manifold cache. Placement work is
  read once per solid and used for both its resting and dropped records, so an
  exact solid's `shape()` is not fetched twice.
- Correctness of the culling still rests on broad-phase completeness, already a
  framework obligation proved separately (ADR-040). The directed pairing adds
  no new tolerance.

## Alternatives rejected

### A physics engine

Dropping the assembly into a rigid-body simulator would answer stability, not
just support, but it introduces a heavy dependency, a nondeterministic verdict
that depends on solver settings and timestep, and diagnostics that cannot name
the offending part in the model's own vocabulary. The defect being solved is
"nothing is under this part", which needs no dynamics.

### Contact-graph connectivity with a distance epsilon

Recorded above under the drop-test decision: weaker (a sideways touch reads as
support), needs a physically meaningless tolerance, and relies on sampled mesh
proximity.

### A ground-plane parameter

A plane would introduce a second coordinate convention next to `gravity` and
still not cover an assembly hung from a ceiling. The lowest-extent default
plus explicit `ground` nodes covers both without it.

## Evidence

- Unit coverage in `tests/test_assembly_supported.py`: trivial selections,
  drop edges (resting, clearance play, hanging by engagement, zero-volume
  tangency), the `max_drop` window from both sides, gravity direction and
  normalization, mutual-lean cycles grounded and ungrounded, default and
  explicit seeding including resolution up from an ingredient and down through
  an assembly, declared supports and their refusal to ground a floating
  supporter, loud knob errors, exact/mixed pair routing, directed candidate
  pairing, broad-phase culling counted as Boolean calls, and keyframe-driven
  placement.
- Meta fixtures through the real CLI, builder and kernel: `assembly_supported`
  (green — resting stack, clearance play, a hook hanging by its lip, a
  declared press fit, and a whole assembly anchored by explicit ground),
  `assembly_supported_floating` (deliberately red — a rider on a floating part,
  and a mutually leaning pair whose ground sits out of reach),
  `assembly_supported_exact` (green — an all-exact assembly whose drop pair is
  intersected by the kernel), and `assembly_supported_lifted` (deliberately
  red — a block lifted off its base across three instants, whose `--failfast`
  dot trace shows the same assertion passing at the first instant and failing
  at the second).
- The mutual-lean fixtures were verified to carry edges in BOTH directions
  before being relied on, so the cycle behaviour is genuinely exercised rather
  than passing for a simpler reason.

## References

- `solid_node/test.py`
- `tests/test_assembly_supported.py`
- `tests/meta_project/assembly_supported*.py`
- `tests/test_meta.py`
- `docs/testing.rst`
- OpenSpec change `add-assembly-supported`
