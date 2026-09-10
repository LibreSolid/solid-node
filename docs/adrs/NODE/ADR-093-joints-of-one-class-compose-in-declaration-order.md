# ADR-093: The Joints of One Class Compose in Declaration Order

**Status:** Accepted
**Date:** 2026-09-10
**Extends:**
- [ADR-088: A joint owns one coordinate](./ADR-088-a-joint-owns-one-coordinate.md)
**Depends on:**
- [ADR-023: Kinematic operations and driver-tagged idempotent renders](./ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)
- [ADR-028: Cached base meshes, single-matrix world composition](./ADR-028-cached-base-meshes-and-single-matrix-world-composition.md)
- [ADR-066: render() builds the machine at rest, simulate() moves it](./ADR-066-render-at-rest-simulate-per-instant.md)
**Related:**
- [ADR-089: `drives` relates two coordinates](./ADR-089-drives-relates-two-coordinates.md)
**OpenSpec change:** `joint-composition-order`

## Context and Problem Statement

ADR-088 states one freedom per body very well and says nothing about the
case the catalogue turns out to be full of: **more than one freedom on
one body**. The joints spec settled the composition of two joints on one
node as the order the coordinates were BOUND —

> Joint motion and hand-written motion SHALL coexist on one node: both
> are motion, and they apply in the order they were applied.

— because `Joint.place` reached `apply_motion`, which reached
`_insert_motion`, which puts an operation at the END of the node's
motion block. When both joints are bound by relations, which is the
normal case, "the order they were applied" is the couplings solver's
pass order: a property of where the relations happen to be written, not
of the class carrying the joints. A reader of the class body cannot see
it, a derived coordinate can silently change it, a sweep and re-bind can
reverse it between two runs, and two assemblies animating different
joints of one node decide it between them by walk order.

The 2026-09-09 motion catalogue refactor recorded **seven sightings** in
`workflow/warts.md`, six of them deferring the project outright:

| # | Project | The composition on one body |
|---|---|---|
| 1 | OpenCycloid | disks `R(in)·T(d)·R(out−in)` — `orbit` and `spin` |
| 2 | hexapod_spiderbot | chassis `R_roll·R_pitch·R_yaw·T_height`, hand-inverted in `Chassis._to_chassis` |
| 3 | YouCanBuildDog | `MovingHalf` = `T(slide·ŷ)·R(turn)`; the other order swings the slide 11°, ≈3 mm at the pads |
| 4 | Internal-Cycloidal-Actuator | disk `orbit`+`spin`: spin innermost puts the bore centre at `c0+Δ`, orbit innermost at `R_spin(Δ)+c0` — wrong by up to the full eccentricity |
| 5 | kossel | six rods, four joints each — spin, lean, swing, rise |
| 6 | Inmoov-sim | eight phalanx bodies, two non-commuting rotations each, on `.repeat(4)` |
| 7 | v8-engine | connecting rods `T(crank pin)·R(rod angle)`, eight of them |

Sighting 4 is the decisive one. The Internal Cycloidal Actuator's
reviewed proposal states that **the composition-order contract, not an
`Orbit` primitive, is the minimal unblocker**: its tree is
`solid import-step` output mirroring the document one-for-one, so there
is no carrier body to hang an orbit on, and its form 2 states the machine
completely with the joints that exist today — provided the order is
declaration order. `Orbit` alone would not do, because an orbit
translation and a spin rotation on one body still compose in an order
that matters.

The seven projects agree on the direction, and they agree by writing
their declarations in the order they want them applied.

## Decision Drivers

- A composition order a reader of the class body can SEE, and that a
  solver, a driver, a derived coordinate, a second animator or a sweep
  cannot change.
- Ordering by JOINT, not by coordinate or by operation, so a joint owning
  several coordinates or emitting several operations fits the same rule.
- One seam, one field, no new public name, no document or viewer change.
- The rule must hold for the primitives that are designed but not built
  (`Orbit`, `Free`) without being reopened.

## Considered Options

1. **Declaration order, first declared innermost.** Chosen.
2. **An explicit ordering keyword** (`Revolute(..., outside=pivot)`, or an
   integer), which YouCanBuildDog's proposal offered as an alternative.
   Rejected: declaration order is already the reading order of the class,
   and all seven projects can and do write their declarations in the
   order they want them applied; a keyword would be a second way to say
   one thing, and would need a total-order semantics across inheritance
   that nothing has asked for. If an escape hatch is ever needed,
   reordering the declarations is it.
3. **A couplings delta fixing the solve order.** Rejected: it would
   restate the same invisible ordering in a different place. The solver's
   pass order is untouched by this decision; what changes is that pass
   order no longer decides geometry — which is what finally makes the
   couplings spec's existing promise, "the result SHALL NOT depend on the
   order the author wrote the relations in", true of the placed body and
   not only of the values.

## Decision Outcome

**The joints declared on one class compose in DECLARATION order,
innermost first, whatever order they are bound in.** The first joint
declared is applied closest to the body, the last declared is outermost,
so a class reads body-outward from top to bottom. Each joint's operations
are one contiguous run occupying exactly one position in that order, in
the order that joint's own `placement()` produces them.

Base-class joints come before a subclass's, following the MRO's
linearization, and a subclass redeclaring an inherited joint keeps the
base's slot while taking its own arguments. That is already what
`declared_joints()` reports — it walks `reversed(node_class.__mro__)` and
assigns into a dict, so a class body's joints arrive in definition order
(PEP 520) and a redeclaration reuses its key. This decision makes that
order **normative and load-bearing**: it is no longer merely enumeration
order, it is the composition order, readable off the class without
instantiating anything.

**Hand-written motion composes OUTSIDE the whole joint block**, keeping
its call order among itself. This replaces the spec's "they apply in the
order they were applied", and it is the one part of the change no project
asked for. Two reasons: the joint block has to be contiguous for the slot
rule to be stateable at all; and a hand-written motion that could sit
BETWEEN two joints would reintroduce, in a different disguise, exactly
the invisible ordering this decision removes.

**The seam.** `apply_motion(node, operation)` in `solid_node/node/base.py`
— whose only caller in the tree was `Joint.place` — is replaced by
`apply_joint_motion(node, operations, slot)`. It inserts a joint's whole
placement run at one index: the length of the prefix of `node.operations`
whose entries carry `_motion` AND a `_joint_slot` whose value is
`<= slot`. Equivalently: after every joint of an earlier-or-equal slot,
before the first joint of a later slot, before every hand-written motion,
before every rest operation. Each inserted operation carries
`_motion = True` (unchanged) and `_joint_slot = slot` (new), and is
tagged with the current phase's assembly exactly as before. `slot` is
`list(declared_joints(type(node))).index(self.name)`, read off the
per-class cache the enumerator already keeps.

`_insert_motion` is unchanged and is now the HAND-WRITTEN motion path: an
operation applied through `rotate()`/`translate()` under a simulate phase
still goes to the end of the whole motion block, and therefore lands
outside the joint block automatically. The entire behavioural change
lives in the joint's insertion index.

The run is inserted at one index rather than one operation at a time so
that contiguity is an invariant the seam enforces rather than one every
caller has to preserve.

## Consequences

- `solid_node/node/base.py`: `apply_motion` → `apply_joint_motion`, and
  the motion-block comment above `_insert_motion` states the two-part
  block. ADR-088's own mention of `apply_motion` stays as written: an ADR
  records a decision at its date, not a live reference.
- `solid_node/motion/joints.py`: `Joint.place` computes its slot and
  calls the new seam once with the whole placement; `Joint.clear` is
  unchanged. The module docstring and `declared_joints`'s docstring state
  the ordering contract — the latter is published API text through
  `docs/api-reference.rst`, so the order is its first sentence.
- **`declared_joints`'s order is now load-bearing.** A refactor of the
  enumerator that changed its walk (sorting names, say) would silently
  change where every machine's parts are. `tests/test_joints.py` asserts
  the enumerator's order and the composed pose together for exactly that
  reason.
- **Re-binding one joint of several keeps its place.** Today a second
  binding of the inner joint moved it outside its siblings; it now
  returns to its own slot. That is the fix, not a side effect.
- **Two independent animators on one node stop disturbing each other's
  composition.** The wart's "wheel spun by its axle and steered by the
  steering assembly": after one assembly's sweep and rebind, its joint
  returns INSIDE the other's if it is declared first. `_sweep` needs no
  change — slot-based insertion is what makes the result
  order-independent, where tag-based removal only makes it
  accumulation-free.
- **Hand-written motion moves outside the joint block.** A visible
  behaviour change. It can only affect a node where a hand-written
  simulate-phase `rotate`/`translate` is applied BEFORE that node's joint
  is bound — including every relation-bound joint, since relations solve
  at the end of the phase. A source survey of the sixteen migrated
  catalogue projects predicted zero such sites; the measurement is the
  pose comparison below.
- **Measured: maximum deviation 0.000e+00 on every one of the 32
  capturable models of all sixteen migrated projects**, over 334 poses
  and 2 319 leaf world matrices, captured with `capture_poses.py` before
  (framework 92f4292, the primary checkout) and after (this worktree
  shadowing it), comparing leaf world matrices and bound coordinates. A
  thirty-third model, pascaline's standalone `Digit`, cannot be captured
  at all — its drum is bound from an animated expression the world
  composition refuses as non-numeric — and fails identically before and
  after. The prediction held.
- Two framework tests inverted and were MODIFIED rather than deleted
  (`test_joint_motion_is_innermost_and_tagged`, and
  `test_hand_written_and_joint_motion_coexist_in_order`, renamed
  `test_the_joint_block_is_innermost_of_hand_written_motion`), with the
  order they replaced written into the method so a future accidental
  revert reads as a revert. A third,
  `test_re_simulating_leaves_one_motion`, moved its index from 2 to 1 for
  the same reason.
- **No new public name and no ordering keyword.** The contract is carried
  by the declaration order the class already has.
- **No document, viewer or serialization change.** `_motion` and
  `_joint_slot` are Python-side attributes and are not serialized;
  `serializer.py` publishes the operations list in order and the viewer
  replays it in order (ADR-028), so a reader simply sees the joint
  operations first, innermost, in declaration order.
- **Nothing is deprecated.** Hand-written motion and joint motion still
  coexist on one node.
- **Forward compatibility with `Orbit` and `Free` is an intent, not a
  ratified promise.** The rule is stated over "the operations a joint's
  placement produces" — a contiguous run of any length — and the spec
  says no more than that, because a baseline spec may not describe an
  interface that does not exist. Because the implementation orders by
  JOINT SLOT rather than by coordinate, a future `Free` owning six
  coordinates would occupy one slot and be placed as one unit however
  many relations bind it. If a stacked cycle finds otherwise, that cycle
  revises the contract.
- **Six deferred projects become refactorable at stage B**
  (Internal-Cycloidal-Actuator on this alone; kossel, Inmoov-sim,
  hexapod_spiderbot, OpenCycloid, YouCanBuildDog and v8-engine each with
  their own remaining findings, marked in `workflow/warts.md`). Those
  refactors are not part of this cycle.
- **Not addressed here**, and unchanged: the sweep drops a joint's
  operations but not its coordinate's VALUE (a separate warts finding);
  and `save_checkpoint`/`restore_checkpoint` index from the END of the
  operations list while motion inserts at the head — a mismatch that
  predates the motion layer's slot rule and is neither worsened nor
  fixed by it.
