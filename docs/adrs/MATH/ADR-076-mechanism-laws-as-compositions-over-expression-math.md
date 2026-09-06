# ADR-076: Mechanism Laws as Compositions Over Expression Math

**Status:** Accepted
**Date:** 2026-09-06
**Depends on:**
- [ADR-022: Cross-Runtime Degree-Trig Parity for `$t` Expression Evaluation](ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)

**Related to:**
- [ADR-062: Typed Parameters and the Exponent Algebra](../NODE/ADR-062-typed-parameters-and-the-exponent-algebra.md)
- [ADR-056: Signals, Drivers, Ports, and Stepped Simulation](../NODE/ADR-056-signals-drivers-ports-and-stepped-simulation.md)

## Context and Problem Statement

Thirteen mechanical projects in the development workspace carry a
`kinematics.py`, and beneath each project's own arithmetic sit a handful
of textbook mechanism laws, written again and again:

- the **external spur-gear mesh**, four times — `conjugate_angle` in
  `sandbox/gearbox` over cq_gears' conventions, and
  `pinion_angle_for_wheel` / `wheel_angle_for_pinion` in three
  `3DPrintedClocks` designs over the MrBunsy `Gear` object's;
- the **lead screw**, three times, in `Inmoov-sim`,
  `openflexure-microscope` and `snappy-reprap`, each `lead * angle / 360`
  with its own sign;
- **circle geometry**, three shapes — a circle-circle intersection with a
  side, the law of cosines, and the `sqrt(L² − d²)` rise of a rigid link;
- the **slider-crank**, in `v8-engine`;
- **linear delta kinematics**, in `kossel`.

Each is a law, not a design decision. Each copy nevertheless carried a
convention its author had to rediscover against a rendered mesh — where a
gear library says a tooth sits at zero, which way a screw's handedness
falls, which of two circle intersections is meant — and getting one half a
tooth wrong looks like nothing: the numbers still read plausibly, the
leaves just land on the teeth.

Worse, several copies were **numeric-only**. A law written with Python's
`math` raises `TypeError: must be real number, not OpenSCADConstant` the
instant a symbolic driver or `$t` reaches it (ADR-022), so it works under a
keyframe test and kills `solid develop` at the first non-linear mechanism.

The museum of printers the shop plans to simulate — deltas, corexy,
i3-style — will write the delta and the screw again unless the framework
carries them.

## Decision Drivers

- **A law belongs where it is written once.** Rediscovering a sign
  convention per project is the cost this is meant to remove.
- **Both faces, for free.** Anything a project's `simulate()` calls must
  compute at a keyframe *and* build the viewer's deferred expression.
- **No new cross-runtime surface.** ADR-022's parity is enforced by a
  producer-generated fixture over a fixed corpus; a mechanism package that
  emitted a new OpenSCAD builtin would silently widen the contract three
  runtimes must satisfy.
- **A library's convention must not fork the law.** Two gear libraries
  already disagree about zero, and more will.
- **The dimension algebra (ADR-062) cannot type a degree literal.** A
  plain number is dimensionless and `Angle` is its own axis.

## Considered Options

1. **Leave the laws in the projects.** Each project keeps its copy.
2. **A framework package named `solid_node.kinematics`.**
3. **A mesh law that reads the gear object**, branching per library.
4. **Add an `Angle`-typed literal to the dimension algebra**, so a law's
   `+ 180` could be spelled in a class body and every law would have the
   third, declared face too.
5. **A framework package `solid_node.mechanisms`**, one module per family,
   every law a composition over `solid_node.math`, gear conventions passed
   in as reference angles, and no declared face.

## Decision Outcome

**Option 5.** `solid_node.mechanisms` carries the laws, with three
properties that are the actual decision:

**Compositions, not a new evaluator.** Every function is written over
`solid_node.math` and ordinary arithmetic and has exactly one definition.
It therefore inherits that module's numeric and symbolic faces, and the
symbolic string it builds contains only calls ADR-022's corpus already
pins. The `mechanisms` spec makes that a *requirement*: a future law that
wanted a new builtin must go through `solid_node.math` first, where the
corpus rule lives. The package needed no extension of the parity fixture.

**Reference angles as the seam.** `meshed_angle` takes `driver_gap` and
`driven_tooth` — plain angles saying where a gap centre and a tooth tip
point at angle zero — and reads no gear object. cq_gears' convention is
then `180 / teeth` and MrBunsy's is `gap_angle / 2`, two lines in the
caller rather than a branch in the law. The two references are asymmetric
on purpose: what defines a mesh is a tooth of the driven pointing into a
gap of the driver.

**Two faces, and the third refused loudly.** `meshed_angle` contains
`+ 180` and `screw_travel` contains `/ 360`. Under ADR-062 a declared
`Angle` plus a plain number raises, so a declared token reaching a law
raises `DimensionError` at class definition — early and loud, rather than
yielding a formula with a wrong dimension. The package states this and
documents `.value` as the way through for a static mesh phase, which is
the algebra's own escape hatch. One spec scenario pins both halves.

Option 1 was rejected as the status quo the evidence indicts. Option 2 was
rejected on naming: `kinematics.py` is what every project calls its own
module, and the `kinematics` OpenSpec capability already means operations,
poses and the expression contract. Option 3 was rejected because it makes
the law's shape a function of a third-party object's API. Option 4 is a
real gap in ADR-062 and would give these laws and any other degree-literal
arithmetic a proper third face — but it is an algebra change with its own
consequences and belongs to its own cycle; it is recorded as an open
question rather than folded in here.

## Consequences

- The framework now has an opinion about mechanism conventions, and each
  is stated in the family module a law lives in: the mesh's common frame
  and reference angles, the screw's right-hand rule (handedness and
  nut-versus-screw stay the caller's minus sign), the crank's
  `(across, along)` plane with zero at top dead centre, the delta's
  `radius` and its two-rotation posing recipe, and the linkage side rule.
- Names are unique across families by rule — `crank_rod_angle`, not
  `rod_angle`; `delta_rod`, not `rod_tilt` — so the flat re-export can
  stay flat as families grow.
- `delta_rod` returns two rotations about *constant* axes rather than one
  about the perpendicular the rod actually leans about, because a
  `Rotation`'s axis cannot carry a driver symbol (ADR-056). That framework
  finding, which cost `kossel` a rendered mesh to discover, is now a
  docstring and a spec scenario.
- Nothing guards an unreachable configuration. A `sqrt` or `acos` out of
  range raises numerically and is NaN symbolically, exactly as
  `solid_node.math`, OpenSCAD and the viewer behave. A guard would have to
  invent a pose that does not exist.
- No existing behaviour changes: the package is new, imported by nothing at
  startup, and depends only on `sin`, `cos`, `asin`, `acos`, `atan2` and
  `sqrt`.
- Each law was checked against the function it was lifted from, in that
  project's own repository, as uncommitted evidence: gearbox 900 cases at
  2.27e-13, wall_clock_01's real train at 8.53e-14, and v8-engine, kossel,
  the grasshopper, openflexure and Inmoov at exactly 0.0.
- Open questions carried forward: an `Angle`-typed literal in the algebra
  (Option 4), and whether openflexure's four-bar `leg_lean` / `lever_rise`
  becomes a law once a second flexure stage appears.

Change record: `openspec/changes/archive/2026-09-06-mechanisms/`.
