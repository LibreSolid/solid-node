## Why

The joints spec states the composition of two joints on one body as the
order their coordinates were **bound**:

> Joint motion and hand-written motion SHALL coexist on one node: both
> are motion, and they apply in the order they were applied.

When both are bound by relations — the normal case — that is the
couplings solver's pass order, which is a property of where the relations
were written, not of the class carrying the joints. A reader of the class
body cannot see it, a derived coordinate can silently change it, and it
is wrong for six of the seven projects that met it.

`workflow/warts.md`, section "Motion catalogue refactor (2026-09-09,
every project onto `solid_node.motion`)", records **seven sightings**.
The campaign tracker `libresolid-studio/docs/motion-general-refactor.md`
has nine projects deferred at stage A; six of them are deferred on this
alone.

| # | Project | The composition on one body |
|---|---|---|
| 1 | OpenCycloid (`projects/Actuators/OpenCycloid`) | disks `R(in)·T(d)·R(out−in)` — `orbit` and `spin` |
| 2 | hexapod_spiderbot (`projects/Robots/hexapod_spiderbot_model`) | chassis `R_roll·R_pitch·R_yaw·T_height`, hand-inverted by `Chassis._to_chassis` (`simulation/spiderbot.py:281-284`) |
| 3 | YouCanBuildDog (`projects/Robots/YouCanBuildDog`) | `MovingHalf` = `T(slide·ŷ)·R(turn)`; the other order swings the slide by 11°, ≈3 mm at the pads |
| 4 | Internal-Cycloidal-Actuator (`projects/Actuators/Internal-Cycloidal-Actuator`) | disk `orbit`+`spin`: spin innermost puts the bore centre at `c0+Δ` (right), orbit innermost at `R_spin(Δ)+c0` (wrong by up to the full eccentricity) |
| 5 | kossel (`projects/3D-Printers/kossel`) | six rods, four joints each — spin, lean, swing, rise |
| 6 | Inmoov-sim (`projects/Robotic-Hands/Inmoov-sim`) | eight phalanx bodies, two non-commuting rotations each, on `.repeat(4)`; `pip` inside `mcp`, `dip` inside `pip` |
| 7 | v8-engine (`projects/Vibecoded-demos/v8-engine`) | connecting rods `T(crank pin)·R(rod angle)`, eight of them |

Sighting 4 is decisive: its reviewed proposal
(`.../Internal-Cycloidal-Actuator/openspec/changes/move-onto-motion/proposal.md`,
"The blocker") states that **the composition-order contract, not `Orbit`,
is the minimal unblocking primitive** — its form 2 states the machine
completely with the joints that exist today, provided the order is
declaration order, and `Orbit` alone would not do, because an orbit
translation and a spin rotation on one body still compose in an order
that matters. That one contract unblocks all seven.

The projects agree on the direction, and they agree by writing their
declarations in the order they want them applied. These are the exact
sentences they want to write:

```python
class MiddlePhalanx(StlNode):          # Inmoov-sim
    pip = Revolute(axis=(1, 0, 0), at=PROXIMAL_JOINT, unit='deg')  # inner
    mcp = Revolute(axis=(1, 0, 0), unit='deg')                     # outer

class CycloidalDisk1(StepNode):        # Internal-Cycloidal-Actuator, form 2
    spin  = Revolute(axis=(0, 1, 0), at=DISK_1_BORE_CENTRE, unit='deg')
    orbit = Revolute(axis=(0, 1, 0), unit='deg')   # about the actuator axis

class Chassis(AssemblyNode):           # hexapod_spiderbot
    roll  = Revolute(axis=(1, 0, 0), unit='deg')
    pitch = Revolute(axis=(0, 1, 0), unit='deg')
    yaw   = Revolute(axis=(0, 0, 1), unit='deg')
    lift  = Prismatic(axis=(0, 0, 1), unit='mm')

class MovingHalf(AssemblyNode):        # YouCanBuildDog
    pivot = Revolute(axis=(0, 0, 1), at=(JOINT_CENTRE_X, JOINT_CENTRE_Y, 0),
                     range=(-TURN_MAX, TURN_MAX), unit='deg')
    slide = Prismatic(axis=(0, 1, 0), range=(-SLIDE_MAX, SLIDE_MAX),
                      unit='mm')       # applied outside the pivot
```

The plan this cycle is cut from is `workflow/docs/composed-joints.md`,
which also designs the two primitives that stack on it (`orbit-joint`,
`free-joint`). Nothing here depends on either.

## What Changes

- **The joints declared on one class compose in DECLARATION order,
  innermost first, whatever order they are bound in.** The first joint
  declared is applied closest to the body; the last declared is
  outermost. A class reads body-outward from top to bottom. Base-class
  joints come before a subclass's, and a subclass redeclaring an
  inherited joint keeps the base's slot — which is already what
  `declared_joints()` reports, and which this change makes normative and
  load-bearing.
- **Hand-written motion composes OUTSIDE the whole joint block**, in call
  order among itself. This replaces "they apply in the order they were
  applied". It is the one part of the change no project asked for: it is
  what makes the joint block a contiguous, reorderable unit.
- **Re-binding one joint of several keeps its place.** Today a second
  binding of the inner joint moves it outside its siblings; after this
  change it returns to its own slot.
- **Two independent animators on one node stop disturbing each other's
  composition.** After one assembly's sweep and rebind, its joint returns
  inside the other's if it is declared first.
- **One seam, one field.** `apply_motion(node, operation)` in
  `solid_node/node/base.py` — whose only caller is `Joint.place` — is
  replaced by `apply_joint_motion(node, operations, slot)`, which inserts
  a joint's whole contiguous run at the position its declaration slot
  dictates and tags each operation exactly as today. Joint operations
  carry a new `_joint_slot`. `_insert_motion` is unchanged, so
  hand-written motion keeps going to the end of the motion block and
  lands outside the joint block automatically.
- **No new public name, and no ordering keyword.** The contract is
  carried by the declaration order the class already has.
- **No document, viewer or serialization change.**
  `solid_node/core/serializer.py:361` publishes the operations list in
  order and the viewer replays it in order (ADR-028); a reader simply
  sees the joint operations first, innermost, in declaration order.

Two existing framework tests invert and are modified, not added:
`tests/test_joints.py::MotionDisciplineTest::test_joint_motion_is_innermost_and_tagged`
and `::test_hand_written_and_joint_motion_coexist_in_order`. Their
fixture `Bench` rotates a child by hand and then binds its joint, which
is precisely the case direction 2 changes.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `joints`: "Binding a joint places the body" gains the composition
  order of several joints on one node, and its sentence about
  hand-written motion changes from application order to "outside the
  joint block, in call order". "One-coordinate joint declarations" gains
  the normative promise that the enumerator's order IS the composition
  order.

The `couplings` spec is deliberately **not** changed: the solver's pass
order is untouched. What changes is that pass order no longer decides
geometry — which is what finally makes the couplings spec's existing
promise, "the result SHALL NOT depend on the order the author wrote the
relations in", true of the placed body and not only of the values.

## Impact

- `solid_node/motion/joints.py` — `Joint.place`, and the slot lookup off
  `declared_joints`.
- `solid_node/node/base.py` — `apply_motion` → `apply_joint_motion`; the
  motion-block comment block above `_insert_motion`.
- `tests/test_joints.py` §1.6 — new fixtures and cases, two modified
  assertions. `tests/test_couplings.py`, `tests/test_animator_tag.py`,
  `tests/test_simulate_split.py` must stay green.
- `docs/architecture.md` §Joints (lines 484-512), whose line 505 cites
  the seam `apply_motion` by name, and a new ADR-093 under
  `docs/adrs/NODE/` with its index row.
- User documentation: an `Unreleased` entry in `docs/changelog.rst` in
  the form the ADR-090/091/092 entries use, and the paragraph in
  `docs/driving.rst` ending "both forms may sit on one node".
  `docs/api-reference.rst:262` autodocs `declared_joints`, so its
  docstring is published API text and must lead with the order contract.
- `workflow/warts.md` — the seven sightings marked resolved on archival.
- **Downstream, not in this cycle:** the six projects deferred on this
  contract become refactorable at stage B; three of them
  (OpenCycloid, YouCanBuildDog, v8-engine) also wait on `orbit-joint`
  and the hexapod may prefer `free-joint`.
- No CLI, no document format, no viewer, no public export changes.
