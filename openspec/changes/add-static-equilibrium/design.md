# Design: static equilibrium in `assertAssemblySupported`

## Context

`assertAssemblySupported` (archived change `add-assembly-supported`, ADR-048)
proves transitive support reachability over a directed drop-test graph. Its
documented blind spot — no force or torque balance — is precisely the failure
the pilot now needs caught: a bar supported at one end reaches ground and
passes while it would tip over. The pilot rejected both waiting for more
project evidence and a separate weaker heuristic; the direction is proper
statics inside the same method.

The framework already depends on scipy (`requirements.txt`, `pyproject.toml`;
scipy 1.18 in the workspace venv), trimesh 4.4, and manifold3d. The assertion
already computes, per support edge, the exact geometry a statics phase needs:
the intersection of the dropped solid with its supporter.

## Decision 1: equilibrium as LP feasibility, not dynamics simulation

Model the assembly as rigid bodies with frictionless unilateral point
contacts and ask whether ANY distribution of non-negative normal contact
forces balances every body's gravity wrench — the classical rigid-body limit
analysis used for masonry stability (Whiting et al.) and grasp analysis. This
is decided by one linear program.

Rejected: a dynamics engine (pybullet-style). Convex decomposition corrupts
non-convex CAD geometry at the same order as printed clearances; solver
contact margins fight sub-millimetre fits; verdicts are trajectories needing
displacement/duration thresholds, nondeterministic and non-diagnostic. For
"can this assembly be at rest" the static feasibility question IS the
physical criterion, and it is deterministic, exact-geometry-friendly, and
names the failing body.

Rejected: per-solid centre-of-mass-inside-support-polygon heuristic. It does
not compose — an offset stack stable at every interface but with cumulative
centre of mass past the base passes it, and a counterweighted assembly fails
it. It is the single-body special case of the LP.

Frictionless is deliberately conservative: a hold that exists only through
friction fails and must be declared in `supports`, keeping the exemption
visible — the same philosophy the reachability phase already ratified.

## Decision 2: one method, two phases

The equilibrium phase runs after the existing reachability phase and only
when reachability passes. Reachability is unchanged — same graph, same seeds,
same routing, same failure — and stays first because it is cheaper and its
failure ("floating, no path to ground") is the clearer diagnostic for the
grossest defect. Equilibrium failure is the finer diagnostic ("reaches
ground, cannot balance"). Passing the assertion now means both. The
zero-or-one-solid shortcut is preserved: a lone solid still passes without
geometric work, so single-part floor toppling remains out of scope
(documented).

## Decision 3: contact patches from the drop-intersection meshes, faceted

For each detected support edge (dropped `A` intersecting resting `B` with
positive volume), the contact interface is extracted from the faceted
intersection `A_dropped ∩ B` of the placed Manifolds:

- Mesh the intersection; classify each face to the boundary it came from by
  nearest-surface distance (a face lies either on `∂A_dropped` or on `∂B`).
- The `∂B` faces are the landing patch: they sit on the supporter's REAL
  resting surface (B never moved), so contact positions and normals are true,
  not displaced. Contact points are those faces' vertices (deduplicated);
  the contact normal at each is the face normal oriented out of `B`, toward
  `A`.

Edge existence keeps its ratified routing (exact pairs by the
boundary-representation kernel); contact extraction always uses the placed
Manifolds, including for exact pairs. Statics tolerates faceting — the LP
needs patch extent and normal direction, not boolean validity — and the
faceted mesh is already cached and placed.

Known bias: dropping by `max_drop` engulfs slightly more of `B` than true
contact, widening the patch by up to the drop distance along sloped surfaces.
That errs toward feasibility (less conservative); `stability_margin`
(Decision 7) is the counterweight, and the `max_drop` selection rule already
bounds the error to the clearance scale.

## Decision 4: a lift pass detects overhead restraints

Contacts that push a body DOWN are invisible to the drop test but essential
to real couples: a cantilevered pin in a snug hole balances because the hole's
lower wall pushes up near its mouth and its upper wall pushes down at the
pin's inner end. So contact detection runs the same displaced-versus-placed
machinery twice: the existing drop (offset `+max_drop·ĝ`) and a lift (offset
`−max_drop·ĝ`). Lift-detected intersections contribute contact patches
exactly as drop-detected ones (patch on the restrainer's surface, normal out
of the restrainer). Lift edges do NOT feed the reachability graph — its
ratified semantics ("displaced along gravity, lands in support") are
untouched.

Still invisible: purely lateral contacts (vertical walls parallel to
gravity), which neither displacement can enter. A hold that needs a
frictionless vertical-wall reaction typically also needs friction, so this
stays in the conservative bucket with friction, documented, with `supports`
as the escape.

## Decision 5: anchoring — virtual floor by default, bolted `ground`

The LP needs anchored bodies whose balance is not questioned (they receive
the ground's reaction). Two regimes:

- `ground=None`: a virtual floor — a slab spanning the assembly's lateral
  bounds with margin, its top plane at the assembly's furthest extent along
  gravity, built in the gravity frame — joins the resting set for contact
  detection only. It is the ONLY anchored body, so default-seeded solids must
  balance on their real floor patches: a tall tippy solid on a small
  footprint now fails instead of being exempt as a seed. The floor
  participates in no reachability question; seeds keep their ratified
  extent-based definition.
- `ground=<node(s)>`: the resolved solids are fully anchored (bolted to an
  unmodelled frame — the ratified meaning). No virtual floor; every other
  solid must balance.

## Decision 6: the LP, its variables, and its diagnostics

- Variables: one `f_k ≥ 0` per contact point (force `f_k·n̂_k` from
  supporter on supported, reaction `−f_k·n̂_k` on the supporter when it is
  not anchored); six FREE variables (a full wrench) per declared `supports`
  edge — glue/press-fit transmits force and torque in both signs.
- Equations: for every non-anchored solid, `ΣF + w·ĝ = 0` and `Στ = 0`
  about its centre of mass — six rows per solid. Mass properties come from
  the placed faceted mesh (watertight by construction) at uniform unit
  density with unit gravity magnitude: `w = volume`. Feasibility is invariant
  to positive scaling, so density and g never matter.
- Solve the RELAXED problem directly with `scipy.optimize.linprog`
  (`method='highs'`): elastic slack variables on every balance row, minimize
  the L1 slack norm. Optimum zero (within a tolerance scaled per body — by
  weight for force rows, by weight times bounding-box diagonal for torque
  rows) means equilibrium exists; a nonzero optimum names each solid with
  residual slack and whether its force or torque balance failed. One solve
  yields both verdict and diagnosis; `highs` is deterministic.

## Decision 7: `stability_margin` knob

`stability_margin` (mm, default `0.0`) shrinks each contact patch: every
contact point moves toward its patch's centroid by up to the margin (points
closer than the margin collapse to the centroid). At the default the check is
pure feasibility — a knife-edge balance with the centre of mass exactly over
the edge is physically an equilibrium and passes. A positive margin demands
that much interior reserve in every patch, rejecting boundary-exact and
knife-edge balances. Default 0.0 keeps the semantics pure and the change
non-arbitrary; the knob makes robustness an explicit design statement in the
test.

## Decision 8: failure message and errors

Equilibrium failure raises `AssertionError` naming every unbalanced solid
with the failing balance kind, e.g. `bar cannot rest in frictionless static
equilibrium on its detected contacts (unbalanced torque)`, and points at
`supports=` for holds that are real but outside frictionless statics.
Existing loud-error knobs are unchanged; `stability_margin < 0` is an error.
A reachability pass whose support edges yield no extractable contact patch
for a needed body is reported as that body's equilibrium failure, never
silently passed.

## Risks

- False failures on friction-dependent designs (inclined seats, lateral
  wedges): intended conservatism; `supports=` is the visible exemption. The
  existing fixture set re-runs under the new phase — a fixture that passed
  only through the old blind spot gets rebalanced, as evidence.
- Patch overestimation from the drop distance (Decision 3): bounded by the
  ratified `max_drop` selection rule; `stability_margin` available.
- Faceting/LP numerics near marginal balance: tolerances scaled per body;
  marginal-by-design cases belong behind `stability_margin`.
- Cost: one extra displaced boolean sweep (lift), intersection meshing, and
  face classification per edge, plus one HiGHS solve — all test-time only,
  broad-phase-culled, and small next to the booleans already paid.
