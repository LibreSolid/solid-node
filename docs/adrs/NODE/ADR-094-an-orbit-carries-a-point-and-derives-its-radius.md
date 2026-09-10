# ADR-094: An Orbit Carries a Point, and Derives Its Radius

**Status:** Accepted (the `_OWN_PLACED_ORIGIN` sentinel revised by [ADR-097](./ADR-097-a-joint-is-stated-in-the-frame-of-whoever-declares-it.md): `carries` now defaults to the plain `(0, 0, 0)` it always meant in the body's own frame; everything else below stands)
**Date:** 2026-09-10
**Extends:**
- [ADR-088: A joint owns one coordinate](./ADR-088-a-joint-owns-one-coordinate.md)
**Depends on:**
- [ADR-093: The joints of one class compose in declaration order](./ADR-093-joints-of-one-class-compose-in-declaration-order.md)
- [ADR-022: Cross-runtime degree-trig parity for `$t` and driver expressions](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)
**Related:**
- [ADR-028: Cached base meshes, single-matrix world composition](./ADR-028-cached-base-meshes-and-single-matrix-world-composition.md)
**OpenSpec change:** `orbit-joint`

## Context and Problem Statement

ADR-088 gave the framework the two one-coordinate lower pairs. Neither
states the body the catalogue is full of: one whose ATTITUDE never
changes while a point of it travels the circle that point makes about a
line. A `Revolute` about the same line turns the body too; a pair of
`Prismatic`s needs two trigonometric `law=` callables, which have no
inverse, so nothing can be driven backwards through them.

`workflow/warts.md` records the gap under "A carried body: the orbit
primitive" and again in the V8 and Internal Cycloidal Actuator entries.
Four projects wrote the sentence they wanted:

| Project | The carried body | What it costs today |
|---|---|---|
| OpenCycloid | two disks carried at `ECCENTRIC_RADIUS = 2.5` about the drive axis while spinning on their own centres | a `-1.0` term folded into every spin ratio, because the orbit is a `Revolute` and drags the attitude with it |
| YouCanBuildDog | twenty bodies, five per leg, translating by `R(θ)·s − s` with fixed attitude | 40 `Prismatic`s and 40 trigonometric laws, with no inverse, for 4 freedoms |
| Internal-Cycloidal-Actuator | two disks orbiting the actuator axis at 2.000 mm while spinning at `−1/8` about their own bores | a nineteen-line `_simulate_disk()` and a `ratio=-(1 + 1/REDUCTION)` that exists only because the orbit turns the body |
| v8-engine | eight connecting rods, big end riding the crank pin | three joints and three trigonometric laws per rod |

The four asked for **two irreconcilable spellings**. Two of them
(OpenCycloid, YouCanBuildDog) asked for `Orbit(axis, radius, phase)` —
the radius and the starting angle typed as numbers. Two of them (the
Internal Cycloidal Actuator, the V8) asked for `Orbit(axis, at=<the
carried point>)` — the anchor keyword re-used to mean the point that
travels, rather than a point on the line.

They cannot both be served. The Internal Cycloidal Actuator's ratified
spec forbids writing the rest bore centre or the journal position as a
literal anywhere in the project, so it could write neither a `radius=`
nor a `phase=`; and `at` cannot mean the line for a `Revolute` and a
`Prismatic` and the carried point for an `Orbit`, while YouCanBuildDog
needs BOTH a line that is not the parent frame's origin (its chassis
pivot) AND a carried point (its knee pivot), which `at`-as-carried-point
cannot express at all.

## Decision Drivers

- The two numbers the projects wanted to type are CONSEQUENCES of a point
  and a line. Typing a derived value is what the framework exists to
  remove.
- One frame and one meaning for every joint argument: `axis` and `at`
  keep exactly what they mean on a `Revolute`.
- One operation, one slot, so ADR-093's contiguous-run contract covers
  the new joint without being reopened.
- No new operation kind, no document key, no viewer change, no parity
  corpus entry.
- An affine relation into the joint must still invert.

## Considered Options

1. **`Orbit(axis, at, carries)`, radius and phase derived.** Chosen.
2. **`Orbit(axis, radius, phase)`.** Rejected: the project that most
   needs the primitive could not write it, and the dog's own proposal
   shows the cost — a per-leg `radius=40.0000` and `39.9239` that are
   really the distance between two bores it has already measured, and a
   `phase=-55.104` that its own span says is `-55.1033`.
3. **`at` as the carried point.** Rejected: two meanings for one keyword
   across three joint kinds, for the saving of one keyword, and it cannot
   state a line that is not the parent origin together with a carried
   point.
4. **A new operation kind, or a document key for an orbit.** Rejected and
   unnecessary: the expression math already publishes the translation.
5. **Two `Prismatic`s and a `law=`** — what the projects do today.
   Rejected: no inverse, and the attitude promise is nowhere stated, so
   nothing can check it.

## Decision Outcome

**`Orbit(axis, at=(0, 0, 0), carries=None, range=None, unit='deg')`**, a
third declaration exported from `solid_node.motion.joints`. It owns ONE
coordinate — an angle, a rotational port — and binding it moves a CARRIED
POINT of the body along the circle that point makes about the line,
leaving the body's attitude exactly as it was.

- **`axis` and `at` keep their `Revolute` meaning**: a direction and a
  point ON the line, both in the parent's frame.
- **`carries` is the point of the body the joint carries**, in the
  parent's frame, resolved through the same `_vector` path `at` takes.
  It DEFAULTS to the body's **own placed origin**, which in the body's
  own frame is exactly `(0, 0, 0)` — so the default costs one inversion
  less than the anchor does and carries no floating-point residue at all.
- **No `radius` and no `phase`.** Both are derived from `carries`, `at`
  and `axis`, the component along the line being projected out, so which
  point of the line `at` names does not change the placement.
- **A `carries` point ON the line is refused by name** at the first
  binding — not at realization, because the radius depends on the rest
  placement, which does not exist when a joint's arguments resolve. The
  refusal names the node, the joint, the axis, the anchor, the carried
  point and the derived radius of zero, and advises `carries`.

**The placement.** In the node's own frame, with `n` the carried unit
axis, `a` the carried anchor and `p` the carried point: `v` is the
component of `p − a` across the line, `b` is `n × v`, and the bound value
`t` places the single translation

    Δ(t) = (cos t − 1)·v + sin t·b

built through `solid_node.math`'s DEGREE trigonometry, whose symbolic
face emits the OpenSCAD builtins `cos` and `sin` that ADR-022's parity
corpus covers. A component whose `v` and `b` entries are both zero within
`_SNAP` is a plain numeric `0`, for the reason a `Prismatic`'s idle
components are. The rotation part of the operation is the identity at
every value, exactly.

**The seam.** `Joint._carry(node, axis, anchor)` becomes
`_carry(node, axis, *points)`, returning the carried axis and a tuple of
carried points from the one inversion it already computes; a new hook
`Joint.carried_points(node, anchor)` says which parent-frame points a
joint needs carried (`Joint` returns the anchor; `Orbit` returns the
anchor and its carried point), and `Joint.place` splats the carried
points into `placement`. `Joint.resolve` appends a fourth resolved
argument where the subclass declares one; `place` unpacks the first
three, so `_refuse_out_of_range`'s index 2 still means the range.
`Revolute.placement` and `Prismatic.placement` are byte-identical.

## Consequences

- **A rotational coordinate that emits a translation.** `Orbit`'s
  coordinate is a `RotationalPort` in degrees and its operation is a
  `Translation`. That is deliberate — it is what makes an affine relation
  invert — but it is the first joint whose coordinate's domain and
  operation's kind differ, and `declared_ports` reports a rotational port
  for a body that never rotates. The spec says so, so a later exporter
  cannot be surprised by it.
- **A refusal at bind time.** Every other joint refusal except the range
  is a realization-time `ParameterError`. An orbit whose carried point is
  on the axis is only knowable once the body is placed, so it raises a
  `ValueError` at the first binding, in the shape the non-numeric rest
  placement already uses. No new error name is exported.
- **`_carry`'s signature changed** and `placement()` grew an argument for
  subclasses that declare extra points. Both are protected, the motion
  layer has never been in a release, and the two existing placements did
  not move.
- **Float residue in the framework's own published numbers.** A keyframed
  orbit publishes `-9.999999999999998` where `-10.0` is meant, because
  `cos(90°)` is `6.1e-17` in IEEE double. Not new — every one of the four
  projects already publishes it from its own `cos`/`sin` — but new in the
  framework's output, where a `Revolute` publishes an angle exactly. The
  tests say so: the ATTITUDE acceptance is `atol=0`, the POSITION
  acceptance is a stated `atol=1e-9`.
- **Measured, on the Internal Cycloidal Actuator's own algebraic
  identity** (`tests/test_joints.py::ProjectAlgebraTest`): over ten poses
  and two `mesh_phase` values, the project's three hand-written
  operations and the framework's spin-plus-orbit agree with a **maximum
  rotation-block deviation of exactly 0.000e+00** and a maximum position
  deviation of **4.441e-16 mm**. The radius the framework derives from
  the bore centre and the actuator axis is 2.0000 mm and the phase
  −79.0959°, the two numbers the project records and may not type.
- **`Revolute`'s own-placed-origin `at` stays OPEN.** `Orbit`'s `carries`
  default is that mode for ONE argument of ONE joint. The general finding
  in `workflow/warts.md` needs the anchor at realization time for
  thirteen Thor parts and a different answer; it is not closed here.
- **No pose comparison of the catalogue.** `Orbit` is additive, the two
  existing placements are untouched, and `_carry` returns the same
  carried axis and anchor it returned before. The evidence is the whole
  suite green, cycle 1's composition tests green with an `Orbit` in the
  fixture and no edit to a cycle-1 test, and the byte-identical
  placements. **This cycle therefore has no measurement over a real
  machine**: that comes from the four projects' adoption at stage B, in
  their own repositories.
- **Three deferred projects become refactorable at stage B**: OpenCycloid
  (which still waits on the `.repeat()` relation fan-out), YouCanBuildDog
  (which waits on nothing else) and the v8-engine (which still waits on
  the own-placed-origin anchor for its four timing gears). The Internal
  Cycloidal Actuator, already unblocked by ADR-093, gains its preferred
  form.
- **A correction the projects' proposals need at stage B.** Three of the
  four list `orbit` BEFORE `spin`/`swing`, having been written before
  ADR-093 fixed first-declared-innermost; their algebra needs the
  rotation innermost, so the declarations transpose. The sites are
  OpenCycloid's proposal lines 247-248, the Internal Cycloidal Actuator's
  lines 206-207, and the v8-engine's `docs/move-onto-motion.md` lines
  297-298.
- **The export target is open.** Neither MuJoCo nor Modelica has a native
  carried-body element: an `Orbit` exports as a massless carrier body
  plus a hinge, or as a tendon. Recorded, not designed; what would settle
  it is the first real export of a machine carrying one.
- **No CLI, document format, viewer, serialization or parity-corpus
  change; nothing is deprecated, and no existing project's pose moves.**
