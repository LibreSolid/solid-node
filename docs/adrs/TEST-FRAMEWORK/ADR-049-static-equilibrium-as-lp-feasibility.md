# ADR-049: Static Equilibrium as Linear-Program Feasibility

**Status:** Accepted
**Date:** 2026-08-22
**Depends on:**
- [ADR-029: Manifold Cache and AABB Broad-Phase](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)
- [ADR-040: Topmost-Rigid Assembly Integrity](./ADR-040-topmost-rigid-assembly-integrity.md)
- [ADR-048: Gravity Support Graph Assertion](./ADR-048-gravity-support-graph-assertion.md)

## Context

ADR-048 gave `assertAssemblySupported` a support-reachability proof and
recorded its blind spot: no force or torque balance. The pilot probed the
shipped assertion with exactly that blind spot — a horizontal bar supported at
one end passes, and falls over. The finding is not a corner case: "support one
side only" is the obvious agent fix for the floating-part defect the assertion
was built for, so the documented exclusion is the *next* failure mode, not a
distant one. The pilot's direction was explicit — proper statics, in the same
method, without waiting for further project evidence.

The machinery needed already exists. The assertion computes, per support edge,
the intersection of the dropped solid with its supporter; the framework already
depends on scipy, trimesh and manifold3d.

## Decision

When reachability holds, `assertAssemblySupported` additionally proves
**frictionless static equilibrium**: that there exists an assignment of
non-negative (push-only) normal contact forces over the detected interfaces
that simultaneously balances the gravity wrench — force *and* torque — of every
non-anchored selected solid. Passing now means both phases.

### Equilibrium is a feasibility question, so it is a linear program

The assembly is modelled as rigid bodies with frictionless unilateral point
contacts, the classical rigid-body limit analysis used for masonry stability
and grasp analysis. "Can this assembly be at rest" *is* the static feasibility
question, so the physical criterion and the computational one coincide: one
linear program, deterministic, exact-geometry-friendly, and able to name the
body that fails.

A dynamics engine was rejected. Convex decomposition corrupts non-convex CAD
geometry at the same order as printed clearances, solver contact margins fight
sub-millimetre fits, and the verdict becomes a trajectory needing displacement
and duration thresholds — nondeterministic and non-diagnostic.

A per-solid centre-of-mass-inside-support-polygon heuristic was also rejected:
it does not compose. An offset stack stable at every single interface but whose
cumulative centre of mass passes the base passes it, and a counterweighted
assembly fails it. It is the single-body special case of the LP.

Frictionless is deliberately conservative. A hold that exists only through
friction fails and must be declared in `supports`, which keeps the exemption
visible in the test — the same trade ADR-048 already ratified.

### Contact interfaces come from the displaced intersections, faceted

For each detected landing, the intersection of the displaced Manifold with the
resting supporter is meshed, and each of its faces is classified to the
boundary it came from by nearest-surface distance. The supporter's faces are
the interface: the supporter never moved, so those positions and normals lie on
its real resting surface rather than on a displaced one. Deduplicated vertices
are the contact points; the face normal, oriented out of the supporter, is the
contact normal. A tie — a face lying on both boundaries, which a solid dropped
flush onto its seat produces exactly — belongs to the supporter, and the
comparison carries a relative slack so facet noise cannot decide it.

Support-edge existence keeps its ratified exact-kernel routing; contact
extraction is always faceted, including for exact pairs. Statics needs a
patch's extent and direction, not Boolean validity, and the faceted mesh is
already cached and placed.

A face whose normal is perpendicular to gravity is discarded. Such a face is a
wall the displacement drove into, not a surface anything rests on; keeping it
would let a frictionless lateral reaction hold a part up, which is precisely
what the exclusion list says the assertion does not claim.

Known bias: displacing by `max_drop` engulfs slightly more of the supporter
than true contact, widening a patch along sloped surfaces by up to the drop
distance. That errs toward feasibility, and `stability_margin` is its
counterweight. The same rule bounds the other way: a drop that carries a
feature past the face it rests on extracts no patch there at all, so the
`max_drop` window ADR-048 documents now governs contact extraction too.

### A lift sweep detects overhead restraints

Contacts that push a body *down* are invisible to the drop test and essential
to real couples: a cantilevered pin in a snug hole balances because the hole's
lower wall pushes up near the mouth and its upper wall pushes down at the pin's
inner end. Contact detection therefore runs the same displaced-versus-placed
machinery twice — the existing drop, and a lift by the negated offset — through
the same broad phase. Lift-detected intersections contribute contact patches
exactly as drop-detected ones and **never** add support-graph edges;
reachability semantics are untouched.

Purely lateral contacts remain invisible, since neither displacement enters
them. A hold needing a frictionless vertical-wall reaction typically needs
friction too, so it stays in the conservative bucket with `supports` as the
escape.

### Anchoring: a virtual floor by default, bolted `ground`

The program needs bodies whose balance is not questioned. With `ground=None` a
virtual floor — a slab built in the gravity frame, its top plane at the
assembly's furthest extent along gravity, spanning the assembly laterally —
joins the resting set for contact detection and is the *only* anchored body. A
default-seeded solid must therefore balance on the patch it really lands on: a
top-heavy solid on a small footprint fails instead of being exempt for being
lowest. Seeding keeps its ratified extent-based definition and the floor
answers no reachability question. With an explicit `ground` the resolved solids
are fully anchored — the bolted-to-an-unmodelled-frame meaning ADR-048
ratified — and no floor exists.

### The program, and its diagnostics

Variables are one `f_k >= 0` per contact point, carrying `f_k * n_k` onto the
supported body and its reaction onto a supporter that is not anchored, plus one
free six-component wrench per declared `supports` edge — force and torque in
both signs, which is what glue and a press fit really transmit. Equations are
six rows per non-anchored body: forces plus weight vanish, and their torque
about its centre of mass vanishes. Mass properties come from the placed faceted
mesh at uniform unit density under unit gravity, so weight is volume;
feasibility is invariant to positive scaling, so neither density nor `g` is
ever named.

The relaxed problem is solved directly: elastic slack on every row, minimizing
the L1 slack norm normalized by each row's own tolerance, with
`scipy.optimize.linprog(method='highs')`. One deterministic solve yields both
the verdict — every row's slack inside its tolerance, scaled per body by weight
for force rows and by weight times bounding-box diagonal for torque rows — and
the diagnosis. Failure raises `AssertionError` naming each unbalanced solid and
whether force or torque is what does not close, and points at `supports=`. A
body whose reachability rests on edges yielding no extractable interface keeps
six unsatisfiable rows and fails here rather than passing silently.

### `stability_margin`

`stability_margin` (mm, default `0.0`) shrinks each contact patch toward its own
centroid before the decision; a point closer than the margin collapses onto the
centroid. At the default the check is pure feasibility, so a knife-edge balance
with the centre of mass exactly over a patch boundary is an equilibrium and
passes. A positive margin demands that much interior reserve and rejects it,
making robustness an explicit statement in the test rather than a hidden
constant. A negative value is a loud error.

## Consequences

- A passing `assertAssemblySupported` now claims support reachability, force
  balance, torque balance and toppling over the contacts it detects. The
  exclusions shrink to friction, adhesion, purely lateral wall reactions,
  single-solid floor toppling (the zero-or-one-solid shortcut is preserved, so
  a lone solid still passes without geometric work), and dynamics.
- Reachability runs first and unchanged. It is cheaper and its failure
  ("floating, nothing under it") is the clearer diagnostic for the grossest
  defect; equilibrium failure is the finer one ("reaches ground, cannot
  balance").
- Friction-dependent designs — inclined seats, lateral wedges — now fail. That
  is the intended conservatism, and `supports=` is the visible exemption.
  Existing fixtures that passed only through the old blind spot were rebalanced
  rather than exempted, and that rebalancing is evidence: the hook fixture's lip
  was thickened so a 1 mm drop straddles the post's top face instead of
  tunnelling past it, and extended so the hook's centre of mass sits over the
  patch that carries it; the mutual-lean pair was redesigned as two interlocked
  shelf-and-tongue pieces, with the right piece standing only because the left
  piece's tongue restrains it from above through the new lift sweep.
- The L1 relaxation blames whichever body is cheapest to blame in its own
  normalized units, so a coupled failure may name one member of a chain rather
  than all of them. The named body is always genuinely unbalanced.
- Cost is one extra displaced Boolean sweep, intersection meshing and face
  classification per landing, and one HiGHS solve — all test-time only,
  broad-phase-culled, and small next to the Booleans already paid.
- No new dependency: scipy was already required.

## Alternatives rejected

Recorded above under the decision: a rigid-body dynamics engine, and a
per-solid centre-of-mass-versus-support-polygon heuristic. Also rejected was a
separate weaker stability heuristic living beside the support assertion, which
would have made a passing support test and a passing stability test two
different claims a maker has to remember to combine.

## Evidence

- Unit coverage in `tests/test_assembly_supported.py`: a bar supported at one
  end failing with the bar and its torque named while reachability passes; the
  same bar with a second support passing; an offset stack whose upper pair's
  combined centre of mass leaves the lowest patch; an overhanging beam failing
  alone and passing counterweighted; a cantilevered pin passing through the
  drop-plus-lift couple and failing when the hole's upper wall is removed; a
  top-heavy default seed failing on the virtual floor while its squat neighbour
  is not named; explicit `ground` anchoring with no floor; a declared support
  transmitting an unrestricted wrench; boundary-exact balance passing at the
  default margin and rejected at a positive one; the negative-margin error,
  including for a trivial selection; an overhead restraint that is a contact and
  not a support edge; broad-phase culling of both sweeps; and a repeated-run
  determinism check.
- Meta fixtures through the real CLI, builder and kernel:
  `assembly_supported_balanced` (green — a bar carried at both ends, a
  counterweighted beam, a pin on its couple) and
  `assembly_supported_unbalanced` (deliberately red — the pilot's one-end bar,
  and a top-heavy seed), plus the pre-existing `assembly_supported`,
  `assembly_supported_floating`, `assembly_supported_exact` and
  `assembly_supported_lifted` fixtures re-validated under both phases.

## References

- `solid_node/test.py`
- `tests/test_assembly_supported.py`
- `tests/meta_project/assembly_supported_balanced.py`
- `tests/meta_project/assembly_supported_unbalanced.py`
- `tests/test_meta.py`
- `docs/testing.rst`
- OpenSpec change `add-static-equilibrium`
