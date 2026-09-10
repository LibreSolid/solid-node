## Why

A body whose ATTITUDE does not change while a point of it is carried
round a line is everywhere in the catalogue and is stateable in no
framework primitive. `Revolute` turns the body; `Prismatic` slides it
along one direction. A carried body needs two coupled components of one
angle, which today costs two `Prismatic`s and two trigonometric `law=`
callables per body — with no inverse, so nothing can be driven backwards
through them.

`workflow/warts.md` records the gap under the heading "A carried body:
the orbit primitive" and again in the V8 and Internal Cycloidal Actuator
entries. Four projects wrote the sentence they want:

| Project | The carried body | What it costs today |
|---|---|---|
| OpenCycloid (`projects/Actuators/OpenCycloid`) | two cycloidal disks carried at `ECCENTRIC_RADIUS = 2.5` about the drive axis while spinning on their own centres | a `-1.0` term folded into every spin ratio, because the orbit is a `Revolute` and drags the attitude with it |
| YouCanBuildDog (`projects/Robots/YouCanBuildDog`) | twenty bodies, five per leg (`cheek_outer`, `cheek_inner`, `toe_block`, `shin`, `foot_pad`), translating by `R(θ)·s − s` with fixed attitude | 40 `Prismatic`s and 40 trigonometric laws with no inverse, for 4 freedoms |
| Internal-Cycloidal-Actuator (`projects/Actuators/Internal-Cycloidal-Actuator`) | two disks orbiting the actuator axis at 2.000 mm while spinning at `-1/8` about their own bores | three hand-written operations per disk in `_simulate_disk`, and a `ratio=-(1 + 1/REDUCTION)` that only exists because the orbit turns the body |
| v8-engine (`projects/Vibecoded-demos/v8-engine`) | eight connecting rods, big end riding the crank pin | three joints and three trig laws per rod — 24 joints and 24 law calls for one slider-crank |

The cycle-1 contract (`joint-composition-order`, ADR-093) unblocked the
composition-order half of all four; the carried body is what remains.
OpenCycloid's, YouCanBuildDog's and the V8's deferrals in
`libresolid-studio/docs/motion-general-refactor.md` stand on this
primitive alone; the Internal Cycloidal Actuator is already refactorable
and states this as its preferred form.

The three-line arithmetic every one of them writes is the same:

```python
# YouCanBuildDog, simulation/leg.py:35-40
def swung_offset(angle, span):
    span_y, span_z = span
    turned_y = span_y * cos(angle) - span_z * sin(angle)
    turned_z = span_y * sin(angle) + span_z * cos(angle)
    return turned_y - span_y, turned_z - span_z
```

That is `R(θ)·s − s` for a span `s` from a point on the axis to the
carried point: one coordinate, an angle, and a body that never turns.

## What Changes

- **`Orbit(axis, at=(0, 0, 0), carries=None, range=None, unit='deg')`**,
  a third one-coordinate lower pair exported from
  `solid_node.motion.joints` beside `Revolute` and `Prismatic`. It owns
  ONE coordinate — an angle, a rotational port — and binding it moves a
  CARRIED POINT of the body along the circle that point makes about the
  line, leaving the body's attitude exactly as it was.
- **`axis` and `at` keep their `Revolute` meaning**: a direction and a
  point ON the line, both in the parent's frame, `at` defaulting to that
  frame's origin.
- **`carries` is the point of the body the joint carries**, in the
  parent's frame, resolved exactly as `at` is. It DEFAULTS to the body's
  **own placed origin** — the deferred "own-placed-origin anchor mode" of
  `workflow/warts.md`'s first 2026-09-09 finding, arriving here for this
  one argument and not retroactively for `Revolute`'s `at`, which stays
  open.
- **No `radius` and no `phase`.** Both are derived from `carries`, `at`
  and `axis`. That is what lets the Internal Cycloidal Actuator write the
  joint at all: its ratified spec forbids writing the rest bore centre or
  the journal position as a literal anywhere in the project, and it
  already derives the bore centre.
- **A `carries` point ON the axis is refused by name** at the first
  binding, with the node, the joint, the axis, the anchor, the carried
  point and the derived radius: the body would not move and the author
  meant something else.
- **One operation, one slot.** The placement is a single `Translation`
  whose three components are expressions in the bound angle, so ADR-093's
  contiguous-run contract covers it unchanged and an `Orbit` composes
  with a `Revolute` on one body by declaration order.
- **No new document key and no new operation kind.** The published
  operation is an ordinary `['t', [...]]` whose components are built in
  the framework's own degree trigonometry, so a symbolic binding
  publishes `((cos(($t * 360.0)) - 1) * 10.0)` and the viewer evaluates
  it with the parity ADR-022 already guarantees. Verified by probe before
  this proposal was written; the exact output is in `design.md` §5.
- **`drives` into an `Orbit` binds the angle**, so an affine relation
  inverts exactly as it does for a `Revolute`. The trigonometry is inside
  the placement, not inside the law, and no new inversion problem
  appears.

## Capabilities

### New Capabilities

(none — `Orbit` is a third declaration inside the existing `joints`
capability, not a new one)

### Modified Capabilities

- `joints`: "One-coordinate joint declarations" gains `Orbit` and its
  signature; "A joint owns one coordinate, and that coordinate is a port"
  gains `Orbit`'s rotational coordinate; "Binding a joint places the
  body" gains the orbit's single translation and the frame it is carried
  through; "Joint arguments resolve against the instance at realization"
  gains `carries`. One requirement is ADDED — "An orbit's radius and
  phase are derived, never declared" — for the carried point, its
  own-placed-origin default and the on-axis refusal.

The `couplings` spec is **not** changed: an orbit's coordinate is an
ordinary rotational coordinate and `drives` already relates two of those.
The `ports` and `node-model` specs are not changed.

## Impact

- `solid_node/motion/joints.py` — a new `Orbit` class; `Joint._carry`
  generalized to carry the axis and any number of parent-frame points;
  `Joint.place` asking the subclass which points it needs. `Revolute` and
  `Prismatic` are otherwise untouched.
- `tests/test_joints.py` — a new section for the orbit, and an `Orbit`
  added to the cycle-1 composition fixtures so ADR-093's contract is
  proved over a translation-only joint.
- `docs/api-reference.rst` (the Joints section, beside `Revolute`),
  `docs/driving.rst` (a short passage with the cycloidal disk as the
  example), `docs/changelog.rst` `Unreleased`, `docs/architecture.md`
  §Joints, and a new ADR-094 under `docs/adrs/NODE/` with its index row.
- `workflow/warts.md` — the three carried-body sightings marked fixed;
  the own-placed-origin finding stays OPEN and says so, because `Orbit`'s
  `carries` default is not `Revolute`'s `at`.
- **Downstream, not in this cycle:** OpenCycloid, YouCanBuildDog and the
  V8 become refactorable at stage B; the Internal Cycloidal Actuator,
  already unblocked by ADR-093, gains its preferred form.
- No CLI, no document format, no viewer, no serialization change; nothing
  is deprecated, and no existing project's pose moves.
