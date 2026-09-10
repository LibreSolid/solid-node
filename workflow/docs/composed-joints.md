# Composed joints: a composition order, an orbit, and a free body

**Status: provisional plan, 2026-09-10.** Nothing here is ratified. It is
the working document three OpenSpec cycles are cut from; where it and a
baseline spec or an accepted ADR disagree, the spec and the ADR are right
and this note is stale. It does *not* claim that any of the three
primitives exists, that the interfaces below are settled, or that the
projects named have been refactored. Cycle 1 (`joint-composition-order`)
is cut from §4 of this note, cycle 2 (`orbit-joint`) from §5 and cycle 3
(`free-joint`) from §6. All three have been taken up: each section's own
note names the OpenSpec change that is now the authority for it.

---

## 1. The gap

The motion layer landed in `openspec/changes/archive/2026-09-09-joints`
and `2026-09-09-couplings` (ADR-088, ADR-089). It states one freedom per
body very well and says nothing about the case a machine catalogue turns
out to be full of: **more than one freedom on one body**.

The joints spec's sentence today is

> Joint motion and hand-written motion SHALL coexist on one node: both
> are motion, and they apply in the order they were applied.

`Joint.place` reaches `apply_motion` in `solid_node/node/base.py`, which
reaches `_insert_motion`, which puts the operation **at the end of the
node's motion block** — after the motion already applied, before every
rest operation. So the composition of two joints on one body is the order
their coordinates were *bound*. When both are bound by relations, that is
the couplings solver's pass order (`openspec/specs/couplings/spec.md`,
"Within one pass the order SHALL be declaration order"), which is a
property of where the relations were written, not of the class carrying
the joints. A reader of the class body cannot see it, a derived
coordinate can silently change it, and it is not what any of the seven
projects below wants.

Two related shapes fall out of the same gap:

- a body whose **attitude does not change** while a point of it is
  carried round a line (a cycloidal disk, a dog's lower leg, a
  connecting rod's small end). Two `Prismatic`s and two trigonometric
  `law=` callables state it with no inverse; nothing states it as one
  coordinate.
- a body with **no parent to be jointed to** — a walking robot's
  chassis, four to six freedoms against the ground. Four joints state it
  and put the whole attitude at the mercy of binding order.

## 2. The evidence

All of it is in `workflow/warts.md`, sections "3DPrintedClocks wall clock
01 and Thor (2026-09-09, motion layer refactors)" and "Motion catalogue
refactor (2026-09-09, every project onto `solid_node.motion`)". The
campaign tracker is
`libresolid-studio/docs/motion-general-refactor.md`: 16 projects done and
archived, 9 deferred at stage A on a missing primitive. Each deferred
project's reviewed proposal carries the sentence it wants to write; those
sentences are the requirement.

### Composition order — seven sightings

| # | Project | Site | The composition | Deferred on |
|---|---|---|---|---|
| 1 | OpenCycloid | `projects/Actuators/OpenCycloid/openspec/changes/move-onto-motion/proposal.md` | disks `R(in)·T(d)·R(out−in)`; `orbit` and `spin` on one disk | order + `.repeat()` fan-out |
| 2 | hexapod_spiderbot | `projects/Robots/hexapod_spiderbot_model/.../proposal.md` §"second known limit"; `simulation/spiderbot.py:281-284` | chassis `R_roll·R_pitch·R_yaw·T_height`, hand-inverted by `Chassis._to_chassis` | order (or `Free`) |
| 3 | YouCanBuildDog | `projects/Robots/YouCanBuildDog/.../proposal.md` §2 | `MovingHalf` = `T(slide·ŷ)·R(turn)`; the other order swings the slide by 11°, ≈3 mm at the pads | order + `Orbit` |
| 4 | Internal-Cycloidal-Actuator | `projects/Actuators/Internal-Cycloidal-Actuator/.../proposal.md` §"The blocker" | disk `orbit`+`spin`; spin innermost puts the bore centre at `c0+Δ` (right), orbit innermost at `R_spin(Δ)+c0` (wrong by up to the full eccentricity) | **order alone** |
| 5 | kossel | `projects/3D-Printers/kossel/.../proposal.md` §3 | six rods, four joints each — spin, lean, swing, rise | order |
| 6 | Inmoov-sim | `projects/Robotic-Hands/Inmoov-sim/.../proposal.md` §1 | eight phalanx bodies, two non-commuting rotations each, on `.repeat(4)`; `pip` inside `mcp`, `dip` inside `pip` | order |
| 7 | v8-engine | `projects/Vibecoded-demos/v8-engine/docs/move-onto-motion.md` | connecting rods `T(crank pin)·R(rod angle)`, eight of them | order |

Sighting 4 is the decisive one, because that project says plainly that
**the composition-order contract, not `Orbit`, is the minimal unblocking
primitive**: its form 2 states the machine completely with the joints
that exist today, provided the order is declaration order; and `Orbit`
alone would not be enough, since an orbit translation and a spin rotation
on one body still compose in an order that matters. It also unblocks 1,
2, 3, 5, 6 and 7 at once.

The projects agree on the direction, and they agree by writing their
declarations in the order they want them applied:

    class MiddlePhalanx(StlNode):          # Inmoov-sim
        pip = Revolute(axis=(1, 0, 0), at=PROXIMAL_JOINT, unit='deg')  # inner
        mcp = Revolute(axis=(1, 0, 0), unit='deg')                     # outer

    class CycloidalDisk1(StepNode):        # Internal-Cycloidal-Actuator, form 2
        spin  = Revolute(axis=(0, 1, 0), at=DISK_1_BORE_CENTRE, unit='deg')
        orbit = Revolute(axis=(0, 1, 0), unit='deg')

    class Chassis(AssemblyNode):           # hexapod
        roll  = Revolute(axis=(1, 0, 0), unit='deg')
        pitch = Revolute(axis=(0, 1, 0), unit='deg')
        yaw   = Revolute(axis=(0, 0, 1), unit='deg')
        lift  = Prismatic(axis=(0, 0, 1), unit='mm')

    class MovingHalf(AssemblyNode):        # YouCanBuildDog
        pivot = Revolute(axis=(0, 0, 1), at=(JOINT_CENTRE_X, JOINT_CENTRE_Y, 0), ...)
        slide = Prismatic(axis=(0, 1, 0), ...)   # applied outside the pivot

### The carried body — three sightings

- OpenCycloid asked for `Orbit(axis, radius, phase)`.
- YouCanBuildDog wants twenty of them, five per leg, and it is the first
  project where an orbit is the *only* statable form: the alternative is
  40 `Prismatic`s and 40 trigonometric laws with no inverse for 4
  freedoms. Its radii are per leg (40.0000 mm at −55.000° for three legs,
  39.9239 mm at −55.104° for the short back-left one).
- The Internal Cycloidal Actuator wants
  `Orbit(axis, at=<the carried point>)` and **may not type a radius or a
  phase at all**: its own ratified spec says neither the rest bore centre
  nor the journal position may be written as a literal anywhere in the
  project. Both are derived from an anchor the project already derives.
- The V8's connecting rod reads as `Orbit(axis=(1,0,0), at=(0,0,CRANK_RADIUS))`
  plus its own `Revolute`.

### The floating body — one sighting

The hexapod's chassis, four freedoms against the ground, whose inverse
kinematics hand-inverts exactly `R_roll·R_pitch·R_yaw·T_height`. The
motion layer's own design record
(`workflow/archive/motion-layer-2026-09-09/joints-and-couplings.md`,
the pair table) lists Free as "native joint, later" and says "Free is what
a walking robot's body sits on and has no composition"; the targets it is
meant to fit are MuJoCo's `free` and Modelica's `Joints.FreeMotion`.

## 3. The direction (settled with the pilot, 2026-09-10)

1. **Innermost end.** The FIRST joint declared on a class is applied
   closest to the body, in its own frame; the last declared is outermost.
   A class reads body-outward from top to bottom. Base-class joints come
   before subclass joints, as `declared_joints` already walks base-first;
   a subclass redeclaring an inherited joint keeps the base's slot.
2. **Hand-written motion composes OUTSIDE the joint block**, in call
   order. A visible change from "in the order they were applied", to be
   proved harmless on the sixteen migrated projects by pose comparison,
   not by assertion.
3. **Orbit** is a one-coordinate joint (an angle). The body's attitude
   stays fixed and a carried point of the body moves on a circle about
   the axis. `axis` and `at` keep their `Revolute` meaning. The carried
   point is a separate keyword defaulting to the body's own placed origin.
   A carried point on the axis is refused by name. Radius and phase are
   never typed.
4. **Free** is a native joint owning six named coordinates reachable as
   attributes, each behaving like any other joint coordinate. Rotation
   order fixed by the contract, translation outermost, matching the
   hexapod's `R_roll·R_pitch·R_yaw·T_height`. Spherical is out of scope.
5. Everything stays in `solid_node.motion.joints`. No new module, nothing
   moves, no re-export changes.

Cycle 1 must not box cycles 2 and 3 in: the composition contract has to
hold for an `Orbit` (a translation-only joint) and for a `Free` (a joint
that applies several operations and owns several coordinates) declared
alongside `Revolute` and `Prismatic`.

---

## 4. Cycle 1 — `joint-composition-order`

> **Taken up, 2026-09-10.** This section has been cut into the OpenSpec
> change `joint-composition-order`, which is now the AUTHORITY for
> everything below: its `proposal.md`, `design.md`, `tasks.md` and the
> delta on `openspec/specs/joints/spec.md`, with ADR-093 recording the
> decision. Where this section and those artifacts disagree, they are
> right and this section is the older draft they were cut from. §5
> (`orbit-joint`) and §6 (`free-joint`) remain provisional: nothing has
> been proposed for either.

### 4.1 The rule, in one sentence

A node's motion composes innermost-first as **the operations of its
declared joints in declaration order, each joint's own operations
contiguous and in the order its `placement()` returns them, followed by
every hand-written motion in the order it was applied**, the whole block
sitting inside the node's rest placement.

### 4.2 What the code does today

`node.operations` is composed by premultiplication
(`_compose_matrix`: `matrix = op.matrix() @ matrix`), so index 0 is
innermost and later indices are outermost. The list is
`[motion…][rest…]`. `_insert_motion` (base.py:307) computes the length of
the leading motion run and inserts there — the end of the motion block.
Both `Joint.place` (through the `apply_motion` seam, base.py:342, whose
only caller is `joints.py:318`) and a hand-written `rotate`/`translate`
under a simulate phase (through `_place_operation`) use it. Order is
therefore application order for both kinds.

### 4.3 The declared interface

**No new public name, and no ordering keyword.** The contract is carried
entirely by the existing declaration order, which is already what
`declared_joints()` reports.

- `declared_joints(node_class)` gains a normative ordering promise: it
  already walks `reversed(node_class.__mro__)` and assigns into a dict,
  so a base's joints come first, a class body's joints come in definition
  order (PEP 520), and a redeclaration reuses its key and therefore keeps
  the base's position. Today that is enumeration order; the cycle makes
  it the **composition order**, readable off the class without
  instantiating anything.
- **Rejected: an explicit ordering keyword** (`Revolute(..., outside=pivot)`
  or an integer), which YouCanBuildDog offered as an alternative. Reasons:
  declaration order is already the reading order of the class and all
  seven projects can write their declarations in the order they want;
  a keyword is a second way to say the same thing; and it would need a
  total-order semantics across inheritance that nothing has asked for.
  The escape hatch, if one is ever needed, is to reorder the declarations.
- **Rejected: a couplings delta.** The solver's pass order does not
  change. What changes is that pass order no longer decides geometry —
  which is what finally makes the couplings spec's existing promise
  ("the result SHALL NOT depend on the order the author wrote the
  relations in") true of the *pose* and not only of the values.

### 4.4 The mechanism

`apply_motion(node, operation)` has exactly one caller and is replaced by
one atomic seam:

    apply_joint_motion(node, operations, slot)  ->  list

which inserts the whole contiguous run at the position the slot dictates
and tags each operation with the current phase's assembly, exactly as
`apply_motion` does today. Each inserted operation carries
`operation._motion = True` (unchanged) and a new
`operation._joint_slot = slot`.

The insertion index is the length of the prefix of `node.operations`
whose entries are motion, carry a `_joint_slot`, and whose slot is
`<= slot`. Equivalently: after every joint of an earlier-or-equal slot,
before the first joint of a later slot, before every hand-written motion,
before every rest operation. It is O(n), and it is tolerant of a missing
operation exactly as `Joint.clear` already is: an operation a sweep or a
checkpoint restore has dropped is simply not there.

`slot` is the index of the joint's name in `declared_joints(type(node))`,
which is already cached per class.

`_insert_motion` is unchanged, so hand-written motion under a simulate
phase keeps going to the end of the whole motion block. It therefore ends
up outside the joint block automatically — the entire behavioural change
lives in the joint's insertion index.

### 4.5 The consequences, case by case

**Re-binding one joint of several.** `Joint.clear` removes that joint's
previous operations by object identity; `place` re-inserts them at the
joint's own slot. The rebound joint returns to its own position instead
of jumping outside its siblings. This is a fix, not a side effect: today
a second binding of the inner joint silently reverses the composition.

**The sweep between simulate runs.** `_sweep(assembly)` drops every
operation tagged with that assembly, wholesale, at the head of that
assembly's render. Afterwards the joint block holds only the joints
another animator owns, or untagged ones; the run that follows rebuilds
the swept joints at their own slots, whatever order the solver reaches
them in. Two independent assemblies animating one node (the wart's
"a wheel spun by its axle and steered by the steering assembly") is
therefore also fixed: after A's sweep and rebind, A's joint returns
inside B's if it is declared first, instead of landing outside it.

**Hand-written motion.** Outside the whole joint block, in call order
among themselves. The visible change is confined to a node where a
hand-written simulate-phase `rotate`/`translate` is applied *before* that
node's joint is bound — including every relation-bound joint, since
`solve_relations` runs at the END of the simulate phase, after every
hand-written call in that `simulate()`. The framework's own
`tests/test_joints.py::Bench` is exactly this case and its two assertions
invert.

**Inheritance and redeclaration.** Base joints innermost, in the base's
declaration order; then the subclass's new joints, in its declaration
order. A redeclared joint keeps the base's slot and its new arguments.
Multiple inheritance uses the MRO's linearization, which is deterministic
and is already what the enumerator uses.

**The carried axis is unaffected.** `Joint._carry` composes only the
node's NON-motion operations, so a joint's axis and anchor are carried
through the rest placement and never through a sibling joint's motion.
The outer joint's line is the rest line and the body swings about it —
which is MuJoCo's semantics (a joint's `axis`/`pos` are stated in the
body's rest frame and applied along the chain) and is exactly the algebra
the Internal Cycloidal Actuator proved:
`T_Δ · T_c0 R_σ T_(−c0) · T_t R_r = T_c(θ) R_(r+σ) T_(−B)`, with `c0` the
REST bore centre.

**Serialization.** `solid_node/core/serializer.py:361` publishes
`[operation.serialized for operation in node.operations]` in list order,
and the viewer replays that list in the same order (ADR-028). A reader of
the document therefore sees the joint operations first, innermost, in
declaration order, then the hand-written motion, then the rest placement.
No viewer change, no document format change, no new key.

**Forward compatibility with cycles 2 and 3 — an intent, not a promise.**
The rule is stated over "the operations a joint's placement produces", a
contiguous run of any length; today that is one or three operations for a
`Revolute` and one for a `Prismatic`, and the cycle-1 spec says no more
than that, because a baseline spec may not describe an interface that
does not exist. The intent is that an `Orbit` (one translation) and a
`Free` (up to four operations, and six coordinates on one slot, since the
implementation orders by joint rather than by coordinate) would then need
no reopening. If a stacked cycle finds otherwise, that cycle revises the
contract; cycle 1 does not pre-ratify it.

### 4.6 Tests, red-first

In `tests/test_joints.py` §1.6 (motion discipline), with new fixtures
beside `Bench`:

1. **Two joints, either binding order.** A class declaring `spin`
   (a `Revolute` at an off-origin anchor) then `lift` (a `Prismatic`),
   non-commuting. One bench binds spin then lift, another lift then spin.
   Both must produce the same operations list, in declaration order, and
   the same composed matrix, equal to the hand-composed `T·R`. **Red
   today**: the lists differ and one matrix is wrong.
2. **Relation-bound joints.** The cycloidal case: two `Revolute`s on one
   body driven by two `drives(...)` relations from one shaft coordinate.
   Assert the pose matches first-declared-innermost, and that writing the
   two relation statements in the other order changes nothing. **Red.**
3. **Re-binding one joint of several** keeps the order and leaves one
   motion per joint. **Red.**
4. **Hand-written motion is outside the joint block.** `Bench` (hand
   rotate 10, then bind swing to 25) becomes `['t','r'(25),'t','r'(10),'t']`.
   Two existing assertions invert and are MODIFIED, not added:
   `test_joint_motion_is_innermost_and_tagged` and
   `test_hand_written_and_joint_motion_coexist_in_order`. A second bench
   with hand-written calls on both sides of a binding proves call order
   survives among the hand-written ones. **Red.**
5. **Inheritance.** Base declares `a` then `b`; subclass declares `c` and
   redeclares `a` with a different anchor. Composition order `a, b, c`.
   **Red** only in the redeclaration's placement; assert `declared_joints`
   reports the same order, which is already true and must stay true.
6. **Sweep across runs.** An assembly walked at two instants where the
   solve reaches the two joints in different orders: identical operations
   list at both. **Red.**
7. **Two independent animators on one node.** A owns the first-declared
   joint, B the second. Walk A, B, then A again: A's operations stay
   innermost. **Red.**
8. **Contiguity.** A three-operation `Revolute` stays one contiguous run
   between a `Prismatic` and a hand-written rotation. Guards cycles 2/3.
9. **Serialization.** `serialize()` on a two-joint node reads
   innermost-first in declaration order.
10. **No pose regression in the catalogue.** Not a unit test: the
    campaign's `capture_poses.py` over the sixteen migrated projects,
    before and after, **max deviation 0** as the acceptance, reported per
    project. This is the only *evidence* that direction 3.2 is harmless
    (see the static survey in §4.7 below, which is a prediction, not
    evidence).
11. The whole suite green, `tests/test_couplings.py`,
    `tests/test_animator_tag.py` and `tests/test_simulate_split.py`
    included.

### 4.7 A static survey of the at-risk case, 2026-09-10

The one behaviour that can change a catalogue pose is a hand-written
simulate-phase `rotate`/`translate` on a node **that also carries a bound
joint**. A source survey of all sixteen migrated projects found **zero
such sites**:

- Six declare joints and have no `simulate()` at all (poseidon,
  open_manipulator, BCN3D-Moveo, HACKberry, science-jubilee,
  open_robot_actuator_hardware).
- Five have `simulate()` bodies that only assign coordinates or connect
  ports (OpenTorque-Actuator, openarm, pascaline, hangprinter,
  AlbertPro).
- Five do move something by hand in `simulate()`, and in every case the
  moved node's class declares no joint: openvmp's nine `spin()` sites on
  blueprint-built children (`simulation/don1/link.py:56,90,116` — the
  warts finding "a joint on a child built from data"), openflexure's
  `M3Nut` and `FlexureLeg` (`simulation/microscope/body/body.py:86,96,97`),
  Prusa3-vanilla's `ZScrew` (`simulation/zaxis.py:69`, the tracker's
  "Z screws stay by hand"), Metamaquina2's `ThreadedRod` and
  `ShaftCoupling` (`z_bars.py:61`, `z_couplings.py:54`, "Z bars/couplings
  stay hand-turned"), and snappy-reprap's `CableChainLink`
  (`simulation/cable_chain.py:263-264`).

Hand-written placement on a joint-carrying node is common, but always in
`render()` — rest placement, which this cycle does not touch.

This is a prediction from source, not a measurement, and it does not
replace item 10: a helper call, a `.repeat()` copy or a path binding
could hide a site the survey read past, and only the pose comparison can
say so.

### 4.8 Documents

ADR-093 (`docs/adrs/NODE/`), extending ADR-088 and depending on ADR-023,
ADR-028 and ADR-066; the index row; `docs/architecture.md` §joints
(lines 484-512, whose last sentence states the old coexistence rule);
`openspec/specs/joints/spec.md` through the change's delta; and the
warts entries marked resolved on archival.

---

## 5. Cycle 2 — `orbit-joint`

> **Taken up, 2026-09-10.** This section has been cut into the OpenSpec
> change `orbit-joint`, which is now the AUTHORITY for everything below:
> its `proposal.md`, `design.md`, `tasks.md` and the delta on
> `openspec/specs/joints/spec.md`, with ADR-094 to record the decision.
> Where this section and those artifacts disagree, they are right and
> this section is the older draft they were cut from. Three points the
> change settled that this draft states differently:
>
> - the carried point defaults to the body's own placed origin, which in
>   the body's OWN frame is exactly `(0, 0, 0)` — so the default is not a
>   derivation from the rest placement at all, it is the origin, and it
>   carries no floating-point residue (change `design.md` §3);
> - the on-axis refusal happens at the FIRST BINDING, not at realization,
>   because the radius depends on a placement that does not exist when
>   joint arguments resolve (`design.md` §4);
> - the placement is computed entirely in the body's own frame from the
>   already-carried axis, anchor and carried point; "carried into the
>   node's own frame through the ROTATION part of the inverted rest
>   placement" below is the same vector by a different route, proved
>   identical in `design.md` §2, and needs no second inversion.
>
> **Implemented, 2026-09-10.** `Orbit` is built, ADR-094 records the
> decision, and the cycle's own `evidence.md` carries the measurements:
> the Internal Cycloidal Actuator's algebraic identity holds at a
> rotation deviation of exactly 0 and a position deviation of 4.4e-16 mm,
> and the dog's two spans derive the radii and phases its proposal typed.
> Two facts this draft could not know: the placement is computed from the
> already-carried axis, anchor and carried point with no second inversion
> (confirmed), and the projects' listings put `orbit` before `spin`, which
> ADR-093 reverses — see the ADR's Consequences for the three sites.
>
> §6 (`free-joint`) remains provisional: nothing has been proposed for it.

### 5.1 Interface

    Orbit(axis, at=(0, 0, 0), carries=None, range=None, unit='deg')

- `axis` and `at` keep their `Revolute` meaning exactly: a direction and
  a point on the line, both in the PARENT's frame. This is the ratified
  direction, and it **diverges from the sentence the Internal Cycloidal
  Actuator wrote** (`Orbit(axis, at=<the carried point>)`) — see §7.
- `carries` is the point of the body the joint carries round that line,
  in the parent's frame, resolved like `at`. It defaults to the body's
  **own placed origin**, derived from the rest placement at first bind
  (the translation column of the matrix `Joint._carry` already builds),
  which is the deferred "own-placed-origin anchor mode" of
  `warts.md`'s first 2026-09-09 finding arriving here first. It does not
  retroactively give `Revolute` that mode; that finding stays open.
- One coordinate, an angle, rotational, `unit` defaulting to `'deg'`.
- **Refusals by name**: a `carries` point ON the axis (radius below the
  module's `_SNAP`) — the body would not move and the author meant
  something else; and every refusal `Joint.resolve` already makes.
- **No `radius`, no `phase`.** Both are derived from `carries`, `at` and
  `axis`, which is what makes the actuator able to write it at all.

### 5.2 Placement

With `n̂` the unit axis, `a` a point on it, `p` the carried point, and
`u = p − a`, split `u = w + v` where `w = (u·n̂)n̂` and `v = u − w`; let
`b = n̂ × v`, so `|v| = |b| = r`, the derived radius. Then

    Δ(θ) = R(θ, n̂, about a)·p − p = (cos θ − 1)·v + sin θ·b

a pure translation, in the parent's frame, whose attitude term is exactly
zero — which is the whole point of the joint. It is carried into the
node's own frame through the ROTATION part of the inverted rest placement
only (a translation needs no anchor), and applied as **one**
`Translation`. Each component is built in the framework's expression math,
so a symbolic θ publishes `(cos($t…)−1)*v_i + sin($t…)*b_i` and the
viewer evaluates it with the degree-trig parity ADR-022 already
guarantees. The derived radius and phase never appear as numbers.

`drives` into an `Orbit` binds θ, so an affine relation inverts exactly as
it does for a `Revolute`; the trigonometry is inside the placement, not
inside the law, and no new inversion problem appears.

Composition: one operation, one slot. Cycle 1 covers it unchanged.

### 5.3 Tests, red-first

The attitude is provably untouched (the rotation block of the composed
matrix is the identity at several angles and radii); the carried point
lands where `R(θ)·p` says at those angles; `carries` on the axis is
refused by name; the default carried point equals the placed origin for a
body placed by a `translate` and by a `rotate`+`translate` pair; a
symbolic binding publishes the trig expression and `set_keyframe` makes
it numeric; and the Internal Cycloidal Actuator's algebraic identity as a
fixture, maximum deviation 0.

## 6. Cycle 3 — `free-joint`

> **Taken up, 2026-09-10.** This section has been cut into the OpenSpec
> change `free-joint`, which is now the AUTHORITY for everything below:
> its `proposal.md`, `design.md`, `tasks.md` and the deltas on
> `openspec/specs/joints/spec.md`, `openspec/specs/ports/spec.md` and
> `openspec/specs/couplings/spec.md`, with ADR-095 to record the
> decision. Where this section and those artifacts disagree, they are
> right and this section is the older draft they were cut from. Five
> points the change settled that this draft states differently or not at
> all:
>
> - **the naming rule**, which this draft left to "`declared_ports`
>   reports six entries" without saying under what names. It is
>   `<joint name>.<coordinate name>` — one dot — and it is the port's
>   name, the enumerator's key and the tail of a relation path, with no
>   second spelling. The hexapod's own `Chassis`
>   already declares `roll`, `pitch` and `yaw` as `SignalPort`s
>   (`spiderbot.py:85-92`), so unqualified names were never available. A
>   dotted name is not a Python identifier, so it is deliberately NOT a
>   wiring keyword: both wiring roles — the joint passed whole, and a
>   coordinate named by its dotted name — are refused at class
>   definition, and such a coordinate is reached by assignment, by
>   relation path, and by a driver or an expression;
> - **up to SIX operations, not four.** Four is right for the default
>   anchor, which is the hexapod's case; a non-origin `at` adds the two
>   centring translations exactly as a `Revolute`'s does. Still one
>   contiguous run at one slot, which is all ADR-093 asks
>   (change `design.md` §4);
> - **unbound is not an exception.** §6.2 below calls identity "a
>   deliberate exception to 'an unbound coordinate reads as unbound
>   rather than as zero'". It is not: the READ stays unbound, and
>   "an unbound coordinate places nothing" is the rule every joint
>   already obeys. Only the free joint has to state it, because its
>   placement runs while some of its coordinates are unbound
>   (change `design.md` §6);
> - **three seams must change, measured rather than assumed.** This
>   draft supposed the coordinates would simply enumerate. On the tree as
>   it stands, `declared_ports` reports NOTHING for a six-coordinate
>   joint, `read_through` raises the *parameter* refusal for it, and
>   `setattr(node, 'pose.roll', v)` silently creates an instance
>   attribute and binds nothing. The change carries the probes
>   (change `design.md` §3, §7, §8);
> - **the composition is measured, not asserted.** The hexapod's four
>   hand-written calls equal `T · Rz · Ry · Rx` to 1.11e-16 and
>   `_to_chassis` inverts them to 1.42e-14 mm, over seven poses
>   (change `evidence/probe_matrix.py`).
>
> **Implemented, 2026-09-10, ADR-095 accepted.** Two further points the
> implementation settled that neither this draft nor the change's design
> states:
>
> - **which frame the three TRANSLATIONAL coordinates are read in.** The
>   design carries the three DIRECTIONS into the body's frame and writes
>   the translation as `T(x, y, z)`; on an identity rest placement — every
>   case the evidence has, the hexapod included — the two readings are the
>   same. Where they differ, the implementation displaces along the three
>   CARRIED directions, the way a `Prismatic`'s value runs along its
>   carried axis, because that is what the change's own acceptance test
>   states (`tasks.md` 1.3: the anchored fixture equals "the same product
>   conjugated by its rest placement and its anchor") and because it is
>   what makes a floating body float against the PARENT's frame rather
>   than its own. The plain numeric `0` per unreached component survives
>   unchanged;
> - **the default anchor on a body its parent MOVES.** `at` defaults to
>   the parent frame's ORIGIN, not to the body's own placed origin, so a
>   `Free()` on a body the parent translates turns about the parent's
>   origin and emits the two centring translations — exactly what a
>   `Revolute` with a default `at` does. The hexapod cannot see this (its
>   chassis has an identity rest placement); it is the visible half of
>   open question 11.

### 6.1 Interface

    pose = Free(at=(0, 0, 0), angle_unit='deg', length_unit='mm')

Six coordinates reachable as attributes of the joint read on an instance:
`chassis.pose.roll`, `.pitch`, `.yaw`, `.x`, `.y`, `.z`. Each is an
ordinary coordinate: bindable by assignment, nameable as either end of
`drives`, wirable into a child, readable by a driver or an expression.
`at` is the point the three rotations pass through, in the parent's frame,
defaulting to the body's own placed origin by cycle 2's derivation.

`Free` is the first joint that owns more than one coordinate, so the
`Joint` base grows "a joint owns one or more coordinates" and
`declared_ports` reports six entries. Naming the joint itself as a
relation end, or naming a node whose class declares only a `Free` as a
relation end, is refused by name listing the six — the "a node stands for
its ONE joint" rule is unchanged and simply does not apply.

### 6.2 Placement

Fixed by the contract and stated in the spec, innermost first:

    R(roll, x̂) · R(pitch, ŷ) · R(yaw, ẑ) · T(x, y, z)

— roll innermost, translation outermost, which is exactly what
`Chassis._to_chassis` hand-inverts in `simulation/spiderbot.py:281-284`.
Up to four operations, contiguous, one slot: cycle 1 covers it unchanged.
An unbound coordinate contributes the identity (angle 0, offset 0) while
still *reading* as unbound — the hexapod binds four of the six. That is
a deliberate exception to "an unbound coordinate reads as unbound rather
than as zero" and is an open question (§7).

No `range` in this cycle: a floating body has no travel. Open question.

### 6.3 Tests, red-first

Six coordinates enumerate and bind; the composition reproduces the
hexapod's hand-inverted matrix at a set of poses, maximum deviation 0;
partial binding leaves the unbound freedoms at identity; naming the joint
or the node as a relation end is refused by name; a `Free` and a
`Revolute` on one body compose by declaration slot (the cycle-1
contract); symbolic bindings publish expressions.

---

## 7. Open questions

**Cycle 1**

1. *Does the contract need an escape hatch?* All seven projects can order
   their declarations freely, so none is known to need one. What would
   settle it: a project whose joint declarations are GENERATED in an
   order it does not control — an `import-step` tree, or OpenVMP Don1's
   blueprint-built children, whose joints do not exist yet for a separate
   reason recorded in the warts.
2. *A same-slot survivor.* If an operation of the joint being re-bound
   survives both `_sweep` and `Joint.clear` — the path `Joint.clear`'s
   docstring names, the test runner's checkpoint restore resurrecting an
   old object — the `<= slot` rule places the new run after it and leaves
   the stale one innermost. The `<` and `<=` rules differ only in this
   case. What would settle it: a test that restores a checkpoint between
   two bindings of one joint and reads the resulting list.
3. *A legacy render inside a joint's frame.* A `render()` that read a
   driver re-runs per binding and appends TAGGED but NON-motion
   operations, which `Joint._carry` therefore composes into the rest
   placement it inverts — so such a node's carried axis changes with the
   binding. This predates the cycle and the cycle does not change it, but
   it is a latent hazard worth naming. What would settle it: whether any
   catalogue project still triggers the legacy-render `FutureWarning` on
   a node that also declares a joint.
4. *Is direction 3.2 actually harmless?* The static survey of §4.7 found
   zero at-risk sites in the sixteen migrated projects, which predicts
   yes. Only the pose comparison is evidence, and it must be run before
   the change is called harmless rather than asserted. The survey also
   leaves the NINE deferred projects unexamined: they will be refactored
   onto this contract, so their poses are the stage-B acceptance, not
   this cycle's.

**Cycle 2**

5. *`carries=` versus `at=<carried point>`.* **CLOSED, 2026-09-10, in
   favour of `carries=`** — the change `orbit-joint` owns it, and its
   `design.md` §7 states what each of the four projects then writes,
   checked against that project's own axis line as this question asked:
   - Internal Cycloidal Actuator — `carries=DISK_1_BORE_CENTRE`, no `at`.
     Its actuator axis is `+Y` through the parent's origin (its fallback
     form writes `orbit = Revolute(axis=(0, 1, 0))` with no `at`), so the
     spelling costs it one renamed keyword.
   - OpenCycloid — no `carries` at all. Its plan moves the eccentricity
     into the rest placement, so the disk's own placed origin IS the
     eccentric centre and the DEFAULT derives both the 2.5 mm radius and
     the −90° phase it wanted to type.
   - v8-engine — `carries=(0, 0, CRANK_RADIUS)`, `at` default. One
     renamed keyword. **Its `at` was never a point on the axis**: the
     proposal's own prose says `(0, 0, 15)` is the crank pin's
     top-dead-centre position, i.e. the carried point. Its rod's own
     placed origin is ON the crank axis, so it MUST state `carries` and
     the on-axis refusal is what says so if it forgets.
   - YouCanBuildDog — `at=(0, *SHORT_PIVOT)` unchanged, plus
     `carries=(0, *KNEE_PIVOT)`. **The default is not enough here**: the
     five carried bodies per leg have five different rest placements but
     are all carried by ONE offset, so the knee pivot must be named. It
     is `SHORT_PIVOT + LINK_SPANS[leg]`, which the layout already
     measures, so the per-leg `radius=40.0000 / 39.9239` and
     `phase=-55.000 / -55.104` it typed are derived instead — the
     0.076 mm short leg included.
6. *Export target.* Neither MuJoCo nor Modelica has a native carried-body
   element; an `Orbit` exports as a massless carrier body plus a hinge,
   or as a tendon. The mapping is not designed here. **Still open**, and
   now carried by the change's own open questions.

**Cycle 3**

7. *An unbound `Free` coordinate: identity, or a refusal?* **CLOSED,
   2026-09-10, as IDENTITY** — the change `free-joint` owns it. And it is
   NOT an exception to "an unbound coordinate reads as unbound rather
   than as zero", which this draft wrongly called it: the read stays
   unbound and the enumerator still reports the coordinate. What the
   free joint adds is that its placement RUNS while some coordinates are
   unbound, because binding one re-places all six; the rule it then
   obeys — an unbound coordinate places nothing — is the one an unbound
   `Revolute` already obeys, stated per coordinate rather than per joint.
   The hexapod binds four of six.
8. *A range on a `Free`.* **CLOSED, 2026-09-10, as NONE** — a floating
   body has no travel to bound, and no project asked for one. The
   declaration takes no `range` at all rather than accepting and ignoring
   one, so a `Free(range=…)` is refused where it is written.
9. *Euler versus quaternion.* MuJoCo's `free` carries a quaternion and
   Modelica's `FreeMotion` its own angle sequence; six Euler coordinates
   are lossy at gimbal lock. The design record accepts this for `Free`
   while insisting `Spherical` must be native and quaternion-valued.
   Whether `Free`'s three angles should be a quaternion instead — and
   what a driver would then bind — is not settled, and the hexapod does
   not need it settled. **Still open**, and now carried by the change's
   own open questions.
10. *The export target for a `Free`.* Both MuJoCo and Modelica have a
    native element for it — the only joint of the four for which that is
    true — so it is the cheapest one to get wrong by guessing, and the
    mapping is designed nowhere. **Open**, raised by the change.
11. *Is `at` read in the parent's frame or the body's own?* The hexapod
    cannot tell them apart: its chassis has an IDENTITY rest placement,
    so the parent's origin and the body's own placed origin are the same
    point, and both readings give the same answer at every pose. The rule
    chosen is the parent's frame, by consistency with ADR-088, and it is
    stated in the spec as a rule rather than as something the hexapod
    proved. What would settle it: a floating body whose parent's
    `render()` actually places it somewhere. **Open**, raised by the
    change.
    Half of it is now VISIBLE rather than merely stated: a `Free()` with
    the default anchor on a body its parent MOVES turns about the
    parent's origin and emits the two centring translations, which the
    anchored fixtures in `tests/test_joints.py` record.
12. *Is a dotted wiring keyword wanted at all?* **CLOSED, 2026-09-10:
    NOT IN THIS CYCLE, REFUSED BY NAME.** `Chassis(**{'pose.roll': roll})`
    works — measured, Python accepts a non-identifier `**` key and it
    reaches `_check_wiring` intact — and the change deliberately does not
    offer it: it would be the first non-identifier keyword in the API,
    it is unreadable at the call site, and no project asked for it. Both
    wiring roles are refused at class definition, naming the joint and
    listing its coordinates. A `Free` coordinate is reached by assignment
    on the instance, by relation path, and by a driver or an expression.
    If a later project wants one wired downward, that is a NEW SIGHTING,
    arriving with a real call site to judge the spelling against.
13. *Which frame a `Free`'s three TRANSLATIONAL coordinates are read
    in.* Settled by the implementation as the three CARRIED directions
    (see §6's implementation note), which the change's own acceptance
    test states and which no evidence distinguishes: every case in hand
    has an identity rest placement, where the two readings agree
    exactly. **Recorded rather than open**, but it is a rule chosen and
    not a thing a project proved — the same shape as question 11.

## 8. Where the evidence and the direction disagree

Recorded plainly rather than reconciled:

- **`Orbit`'s anchor spelling** (open question 5). Two of the four
  projects that asked for an orbit wrote a radius and a phase, which the
  direction refuses; two wrote `at=<carried point>`, which the direction
  re-spells as `carries=`. **No project wrote the ratified spelling**,
  and that remains true: the question was closed by DECISION, not by
  evidence. What the check added, 2026-09-10, is the cost to each — one
  renamed keyword for the actuator and the V8, nothing at all for
  OpenCycloid (the default derives both numbers), and one derived point
  for the dog in place of two typed ones. The reason the direction wins
  is not that a project asked for it but that the two spellings the
  projects asked for cannot both be served: `at` cannot mean the line for
  a `Revolute` and the carried point for an `Orbit`, and the dog needs
  BOTH a line that is not the parent origin AND a carried point, which
  `at`-as-carried-point cannot express.
- **The V8's `at` was misread in the campaign's own briefing** as "the
  crank centre, a point ON the axis". It is not: the project's proposal
  says in prose that `(0, 0, CRANK_RADIUS)` is the crank pin's
  top-dead-centre position — the carried point. The conclusion (one
  renamed keyword) survives; the reason given for it did not.
- **One of the dog's typed numbers was wrong, which is the argument in
  miniature.** Its proposal typed `phase=-55.104` for the back-left leg;
  the span it derived that from, `(22.8404, -32.7450)`, is -55.1033
  degrees. The framework derives the span's own angle. A number nobody
  types is a number nobody can transcribe wrongly, and this is the only
  instance the check found.
- **The dog's radius does not come out of the placement for free.** The
  briefing's expectation that the default `carries` would derive the
  per-leg 40.0000 / 39.9239 mm is wrong: five bodies per leg, five rest
  placements, one shared offset. The numbers are still derived rather
  than typed, but from a named knee pivot, not from the default.
- **Nothing in the evidence contradicts the composition-order
  direction.** All seven sightings ask for declaration order,
  innermost-first, and all seven wrote their declarations that way.
  Direction 3.2 (hand-written motion outside the joint block) is the one
  part of cycle 1 that no project asked for: it is the framework's own
  choice, made so that the joint block is a contiguous, reorderable unit,
  and it is the part the pose comparison exists to check.
- **The design record says a `Free` "has no composition", and cycle 3
  gives it one.** `workflow/archive/motion-layer-2026-09-09/joints-and-couplings.md`
  §1 says "Free is what a walking robot's body sits on and has no
  composition", meaning it is not built out of other joints the way a
  screw or a universal is — and in that sense the change agrees, because
  `Free` is native. But the change DOES fix an internal order among its
  six coordinates, `R(roll)·R(pitch)·R(yaw)·T`, and that order is exactly
  the composition the record's sentence says a `Free` does not have. The
  reason it must exist is the hexapod: `Chassis._to_chassis` hand-inverts
  that product and every leg solution in the model depends on it. Stated
  plainly rather than reconciled: "no composition" is true of how a
  `Free` is BUILT and false of what it DOES.
- **`Spherical` is to be a quaternion because Euler triples gimbal-lock,
  and `Free` carries an Euler triple anyway.** The same design record
  makes that argument for `Spherical` in the sentence above the pair
  table and accepts three angles for `Free` in the row below it. Cycle 3
  ratifies the three angles the pilot chose and records the limit rather
  than quietly inheriting it: the fixture includes a `pitch = 90°` pose,
  so the degenerate case is on the record as a measurement and a picture,
  not as an omission. Open question 9 carries the rest.
- **No project asked for a `Free`.** One project — the hexapod — has a
  floating body, and what it wrote (and what its reviewed proposal asked
  for) is FOUR JOINTS in declaration order, which ADR-093 already gives
  it. `Free` is the framework's own choice, made because the two export
  targets both have one element for it and because six freedoms on one
  body read better as one declaration than as four plus six forwarding
  ports. Like direction 3.2, it is a framework choice and not an
  empirical requirement, and it should be read as one.
