## Context

`Revolute` and `Prismatic` (ADR-088) place a body by carrying a
parent-frame `axis` and `at` into the node's own frame — inverting the
node's rest placement in `Joint._carry`
(`solid_node/motion/joints.py:370-405`) — and then emitting ordinary
`Rotation`/`Translation` objects from `placement()`. ADR-093 fixed how
several of them compose on one body: one contiguous run per joint at the
slot its declaration order gives it, through
`apply_joint_motion(node, operations, slot)`
(`solid_node/node/base.py:370-426`).

Neither pair states a body whose ATTITUDE is fixed while a point of it
travels a circle. A `Revolute` about the same line turns the body too; a
pair of `Prismatic`s needs two trigonometric `law=` callables with no
inverse. Four projects carry the arithmetic by hand and three are
deferred on it.

This cycle adds the third pair. It changes nothing about `Revolute`,
`Prismatic`, the composition contract, the couplings solver, or the
document format.

## Goals / Non-Goals

**Goals**

- One coordinate, an angle, for a carried body.
- The radius and the phase DERIVED, never typed — the Internal Cycloidal
  Actuator cannot write either number and is the sharpest constraint.
- One operation, one slot, so ADR-093 covers it with no reopening.
- One `Translation` of ordinary expressions, so no document key, no
  operation kind, and no viewer change.

**Non-Goals**

- `Free` (`workflow/docs/composed-joints.md` §6). Not built here.
- The own-placed-origin anchor mode for `Revolute`'s `at`. `Orbit`'s
  `carries` default is that mode for ONE argument of ONE joint; the
  general finding stays open in `workflow/warts.md`.
- An export mapping. Neither MuJoCo nor Modelica has a native
  carried-body element; the mapping is recorded as an open question, not
  designed (§7).
- `Spherical`, a `Path` joint, and the `.repeat()` relation fan-out that
  OpenCycloid, YouCanBuildDog and fender-bender also wait on.
- Any change to `Revolute`, `Prismatic`, the couplings solver, the
  serializer, or the viewer.

## Decisions

### 1. The declaration

    Orbit(axis, at=(0, 0, 0), carries=None, range=None, unit='deg')

- **`axis`** — a direction of three components in the PARENT's frame,
  exactly as `Revolute`'s. No default, no named constants, normalized and
  refused at zero length by the base class's `resolve`.
- **`at`** — a point ON that line, in the parent's frame, defaulting to
  the parent frame's origin. Exactly `Revolute`'s meaning. Which point of
  the line is chosen does not change the placement, only which component
  of the carried point counts as radius; the framework projects it out.
- **`carries`** — the point of the BODY that travels the circle, in the
  parent's frame, resolved exactly as `at` is (numbers, declared-parameter
  tokens, derived formulas, or a callable of the realized node).
  `None`, the default, means **the body's own placed origin**.
- **`range`** — `(lo, hi)` in `unit`, refusing a plain numeric binding
  outside it exactly as any joint's does; a symbolic binding is not
  checked. Inherited from `Joint` with no new code.
- **`unit`** — `'deg'`, the label the coordinate carries. The coordinate
  is a `RotationalPort`, so `Orbit` is a rotational coordinate that
  produces a translation — which is the whole content of the joint.

**No `radius` and no `phase`.** Both are consequences of `axis`, `at` and
`carries`. Two of the four projects asked for them; the two that cannot
write them are the reason they are refused (§8).

### 2. The placement, and the frame it is computed in

Everything below is in the NODE'S OWN frame, using exactly what
`Joint._carry` already produces: the axis carried through the rotation
part of the inverted rest placement, and each point carried through the
full inverted transform.

Let `n̂` be the carried unit axis, `a` the carried anchor, `p` the carried
point. Write

    u = p − a          the carried point relative to the line
    w = (u · n̂) n̂      its component along the line
    v = u − w          its component across the line          |v| = r
    b = n̂ × v          v turned a quarter turn about the line  |b| = r

Rodrigues about the line then gives, for the bound angle `θ`,

    Δ(θ) = R(θ, n̂, about a)·p − p = (cos θ − 1)·v + sin θ·b

a PURE TRANSLATION whose rotation part is exactly the identity at every
angle — which is the whole point of the joint, and the thing the tests
assert to a deviation of exactly zero (§6.1).

**Why the local frame is the right frame, and why no new carry is
needed.** The node's rest placement `M` is a composition of `Rotation`
and `Translation`, so it is rigid. Writing `R_M` for its rotation part,
the parent-frame displacement `Δ_parent` and the body-frame displacement
`Δ_local` are related by `M · T(Δ_local) = T(Δ_parent) · M`, i.e.
`Δ_local = R_M⁻¹ Δ_parent` — the translation is carried through the
ROTATION part of the inverted rest placement only, because a translation
has no anchor. Computing the whole construction from the already-carried
`n̂`, `a` and `p` gives the same vector identically:

    Δ_local = M⁻¹R_parent M · p_local − p_local
            = M⁻¹(R_parent p) − M⁻¹(p) = R_M⁻¹ (R_parent p − p) = R_M⁻¹ Δ_parent

so `Orbit` needs the rest matrix for nothing that `_carry` does not
already give it. `r` is the same number in either frame, `M` being rigid.

**One `Translation`, three expressions.** Each component is built through
`solid_node.math.cos` and `solid_node.math.sin` — the framework's own
degree trigonometry, whose symbolic face emits the OpenSCAD builtins
`cos`/`sin` that ADR-022's parity corpus covers. A component whose `v`
and `b` entries are both zero within `_SNAP` is a plain numeric `0`, not
an expression multiplied by zero, for exactly the reason `Prismatic`
already does this: otherwise every orbit puts `$t`-shaped noise in the
slot along its own axis.

### 3. The default carried point is the body's own placed origin, exactly

`carries=None` means the body's own placed origin. In the LOCAL frame
that point is `M⁻¹(M · 0) = 0` — **exactly** `(0.0, 0.0, 0.0)`, by
definition and with no arithmetic, so the default costs one inversion
less than the anchor does and introduces no floating-point residue at
all. The implementation therefore maps an unstated `carries` to the local
origin directly rather than round-tripping the placed origin through the
inverse.

This is the deferred "own-placed-origin anchor mode" of `warts.md`'s
first 2026-09-09 finding, arriving for one argument of one joint. It does
**not** give `Revolute`'s `at` the same mode: that finding needs the
anchor at realization time for thirteen Thor parts and a different
answer, and it stays open.

### 4. The refusal: a carried point on the axis

`r <= _SNAP` means the carried point lies on the line: the body would not
move, and an author who wrote that meant something else. It is refused at
the FIRST BINDING, not at realization, naming the node (through `_where`,
as `JointRangeError` does), the joint, the axis, the anchor, the carried
point and the derived radius, and advising that `carries` name a point
off the line.

Binding time rather than realization time because the radius depends on
the rest placement, which does not exist when `resolve_declared_joints`
runs — `AbstractBaseNode.__init__` completes before the parent's
`render()` places the node, which is the same fact the own-placed-origin
finding records. The ARGUMENT `carries` is still validated at realization
by the ordinary `_vector` path, so a token that is not a parameter, a
non-callable of the wrong shape, or a component that is not a number
still fails at realization naming the class, the joint and `carries`.

This refusal is what the V8 will meet if it forgets `carries`: its
`ConRod` is not placed by `CylinderUnit.render()`, so its own placed
origin is the unit origin, which is ON the crank axis. The refusal names
the radius `0.0` and points at `carries`.

### 5. The mechanism

`Joint.place` today reads

    axis, anchor, _span = self.arguments(node)
    local_axis, local_anchor = self._carry(node, axis, anchor)
    ... self.placement(node, value, local_axis, local_anchor) ...

Three narrow changes, all inside `solid_node/motion/joints.py`:

1. **`Joint._carry(node, axis, *points)`** returns the carried axis and a
   tuple of carried points, one per argument. A point given as the module
   sentinel for "the body's own placed origin" is returned as exactly
   `(0.0, 0.0, 0.0)` without touching the inverse (§3). One inversion, as
   today.
2. **`Joint.carried_points(node, anchor)`** — a hook returning the
   parent-frame points this joint needs carried. `Joint` returns
   `(anchor,)`; `Orbit` returns `(anchor, carries-or-the-sentinel)`.
   `Joint.place` calls it, passes the result to `_carry`, and splats the
   carried points into `placement`.
3. **`Joint.resolve`** gains the fourth resolved argument for the
   subclasses that declare one; `place` unpacks `[:3]` and
   `_refuse_out_of_range` still reads index 2, so `Revolute` and
   `Prismatic` are untouched by it.

`Orbit.placement(node, value, axis, anchor, carried)` builds `v`, `b` and
`r`, makes the refusal, and returns ONE `Translation`. `Joint.clear`,
`apply_joint_motion`, the slot rule, the tagging and the sweep are all
unchanged: an orbit is one operation in one contiguous run at one slot,
which is exactly what ADR-093 stated the rule over.

### 6. Serialization: verified, not assumed

Probed against this worktree at 19730ac before the proposal was written,
with a bare `Translation` built by the formula above and inserted through
`apply_joint_motion`, on a body placed by `translate([10, 0, 0])`,
axis `z` through the origin, carried point the placed origin
(`v = (10, 0, 0)`, `b = (0, 10, 0)`):

    SYMBOLIC serialized: ['t', ['((cos(($t * 360.0)) - 1) * 10.0)',
                               '(sin(($t * 360.0)) * 10.0)',
                               '0']]
    KEYFRAME 0.25 serialized: ['t', ['-9.999999999999998', '10.0', '0']]
    CLEARED  serialized: ['t', ['((cos(($t * 360.0)) - 1) * 10.0)',
                               '(sin(($t * 360.0)) * 10.0)',
                               '0']]

- The expression math **can** express it. `cos` and `sin` are in
  `solid_node.math.SYMBOLIC_BUILTINS`, so the parity corpus already
  covers both and the viewer's evaluator has them (ADR-022).
- `set_keyframe` makes it numeric and `clear_keyframe` makes it symbolic
  again, with no help from this cycle.
- The third component is the plain numeric `'0'` the §2 rule asks for.
- The composed matrix's rotation block is the exact identity at
  θ = 0, 17, 90 and 213.5 degrees (max deviation `0.0`), and the carried
  point lands where `R(θ)·p` says.
- **One honest wart in the numbers**: `-9.999999999999998` rather than
  `-10.0`, because `cos(90°)` is `6.1e-17` in IEEE double and not `0`.
  That residue is the trigonometry, not the framework, and it is the same
  residue every one of the four projects already publishes from its own
  `cos`/`sin`. It is why the position acceptance in §6.1 of `tasks.md` is
  a stated tolerance and the ATTITUDE acceptance is exactly zero.

No new document key, no new operation kind, no viewer change.

### 7. What the four projects then write

These four sentences are the acceptance of the cycle. Three are
transcriptions of what each project's reviewed proposal already asks for;
one (`v8-engine`) is a rename of the argument it asks for, and one
(`YouCanBuildDog`) replaces two typed numbers with a point the project
already has. Each is checked against that project's own axis line below.

**Internal Cycloidal Actuator** — `simulation/actuator/assembly.py`, each
disk. The actuator axis is `+Y` through the parent's origin (its own
fallback form writes `orbit = Revolute(axis=(0, 1, 0), unit='deg')` with
no `at`), so `at` keeps its default and the carried point is the derived
bore centre:

```python
class CycloidalDisk1(StepNode):
    spin  = Revolute(axis=(0, 1, 0), at=DISK_1_BORE_CENTRE, unit='deg')  # inner
    orbit = Orbit(axis=(0, 1, 0), carries=DISK_1_BORE_CENTRE, unit='deg')  # outer

eccentric_shaft.turn.drives(cycloidal_disk_1.orbit)
eccentric_shaft.turn.drives(cycloidal_disk_1.spin, ratio=-1 / REDUCTION,
                            offset=mesh_phase)
```

with `DISK_1_BORE_CENTRE = (0.378316, -5.25, 1.963896)` derived, never
typed. The derived radius is `sqrt(0.378316² + 1.963896²) = 2.0000` mm,
which is the `_axis_distance` its proposal records, and the phase is the
−79.095935297° it records — neither written anywhere. The `-1` term its
fallback form carries (`ratio=-(1 + 1/REDUCTION)`) disappears, because an
orbit does not turn the body.

**OpenCycloid** — `simulation/actuator.py`. Its plan moves the
eccentricity into the rest placement
(`self.stage_one.translate((0.0, -ECCENTRIC_RADIUS, 0.0))`), so the
disk's own placed origin IS the eccentric centre and the DEFAULT
`carries` derives both numbers:

```python
class CycloidalDiskStageOne(...):
    spin  = Revolute(axis=(0, 0, 1), unit='deg')   # inner: its own centre
    orbit = Orbit(axis=(0, 0, 1), unit='deg')      # outer: the drive axis

eccentric_shaft.spin.drives(stage_one.orbit)
eccentric_shaft.spin.drives(stage_one.spin, ratio=-1.0 / REDUCTION)
```

`ECCENTRIC_RADIUS = 2.5` and the `-90.0` phase its wished-for form typed
both come out of the placement; the `- 1.0` in its current
`ratio=-1.0 / REDUCTION - 1.0` disappears with them.

**v8-engine** — `v8_engine/cylinders/con_rod.py`. The crank axis is `+X`
through the unit's origin, so `at` keeps its default; the carried point
is the crank pin's top-dead-centre position, which is the number the
project's proposal already writes:

```python
class ConRod(...):
    swing = Revolute(axis=(1, 0, 0), unit='deg')                    # inner
    orbit = Orbit(axis=(1, 0, 0), carries=(0, 0, CRANK_RADIUS), unit='deg')  # outer

crank.drives(con_rod.orbit)                    # 1:1, no phase term
crank.drives(con_rod.swing, law=rod_swing)     # mechanisms.crank_rod_angle
```

with `CRANK_RADIUS = 15.0`. The rod's own placed origin is its big-end
bore at the unit origin, which is ON the axis, so this joint MUST state
`carries` — and the §4 refusal is what says so if it does not.

**YouCanBuildDog** — `simulation/leg.py`, twenty bodies. `at` is the
chassis pivot, a point on the axis, exactly as its proposal writes it;
`carries` is the knee pivot, which `layout.LINK_SPANS` already measures
(`(dy, dz)` from the chassis pivot to the knee pivot):

```python
carry = Orbit(axis=(1, 0, 0), at=(0, *SHORT_PIVOT),
              carries=(0, *KNEE_PIVOT), unit='deg')
```

with `KNEE_PIVOT = SHORT_PIVOT + LINK_SPANS[leg]`. The per-leg radius and
phase its proposal typed as `radius=40.0000, phase=-55.000` and
`39.9239 / -55.104` for the short back-left leg come out of the two pivot
positions instead — the 0.076 mm difference included, because it is a
difference between two measured bores and not a constant.

### 8. Alternatives rejected

**`Orbit(axis, radius, phase)`**, which OpenCycloid and YouCanBuildDog
both asked for. Rejected: the Internal Cycloidal Actuator's ratified spec
forbids writing the rest bore centre or the journal position as a literal
anywhere in the project, so it could write neither number and the
primitive would not serve the project that most needs it. The radius and
the phase are consequences of a point and a line; typing them is typing a
derived value, and the dog's own proposal shows the cost — a per-leg
`40.0000` and `39.9239` that are really the distance between two bores it
has already measured.

**`at=<the carried point>`**, which the Internal Cycloidal Actuator and
the V8 both wrote. Rejected because it gives `at` two meanings across
three joint kinds — the line for a `Revolute` and a `Prismatic`, the
carried point for an `Orbit` — for the saving of one keyword. The cost of
the ratified spelling is one renamed keyword in those two projects
(§7) and it lets an orbit state BOTH a line that is not the parent origin
AND a carried point, which `at`-as-carried-point cannot (the dog needs
exactly that: `at` at the chassis pivot, `carries` at the knee).

**A new operation kind, or a document key for an orbit.** Rejected and
unnecessary: §6 shows the expression math already publishes the
translation, and inventing a kind would need a viewer change, a parity
corpus entry and a document-format delta for arithmetic the viewer
already evaluates.

**A `law=` on two `Prismatic`s**, which is what the projects do today.
Rejected: no inverse, 40 joints and 40 laws for 4 freedoms in the dog's
case, and the attitude promise is nowhere stated so nothing can check it.

## Risks / Trade-offs

- **A rotational coordinate that emits a translation.** `Orbit`'s
  coordinate is a `RotationalPort` in degrees and its operation is a
  `Translation`. That is deliberate and is what makes an affine relation
  invert, but it is the first joint where the coordinate's domain and the
  operation's kind differ, and `declared_ports` will report a rotational
  port for a body that never rotates. Stated in the spec so it cannot
  surprise a later exporter.
- **The refusal moves to bind time.** Every other joint refusal except
  the range is a realization-time `ParameterError`. An orbit whose
  carried point is on the axis is only knowable once the body is placed
  (§4). A project that never binds the joint never sees the refusal.
- **`_carry`'s signature changes.** It is private and has one caller, and
  `placement()` — protected, `NotImplementedError` on the base — grows an
  argument for subclasses that declare extra points. The motion layer has
  never been in a release, so no published surface moves; a third-party
  `Joint` subclass, if one existed, would need the new hook.
- **Float residue in the published numbers** (§6). Not new — every
  project already publishes it — but new *in the framework's own output*,
  where `Revolute` publishes a linear angle exactly. The tests say so
  rather than hiding it behind a tolerance chosen to pass.

## Migration Plan

None. `Orbit` is additive: no existing declaration, pose, document or
test changes. The four projects adopt it at stage B of the motion
catalogue refactor, in their own repositories, under their own OpenSpec
records — not in this cycle.

## Open Questions

1. **The export target.** Neither MuJoCo nor Modelica has a native
   carried-body element: an `Orbit` exports as a massless carrier body
   plus a hinge, or as a tendon. Recorded, not designed. What would
   settle it: the first real export of a machine carrying one.
2. **A `range` on an orbit.** Kept, because it costs nothing and the dog
   ranges its leg swing. No project has yet declared one on an orbit, so
   the inclusive-bounds behaviour is inherited and untested by evidence.
3. **`carries` as a callable of the realized node** is supported by the
   shared `_vector` path and is the shape the own-placed-origin finding
   would want for `Revolute`. No project needs it here; it is not a
   separate feature, just the argument path `at` already has.
4. **Whether `Orbit` should also accept a carried point in the body's OWN
   frame.** The actuator derives `DISK_1_BORE_CENTRE` in the parent's
   frame from a body-frame point (`BORE_AXIS_POINT`) it already has; a
   body-frame spelling would let it skip that derivation. Not proposed:
   one frame for every joint argument is the contract, and the project
   derives the parent-frame point anyway for its `spin` anchor.
