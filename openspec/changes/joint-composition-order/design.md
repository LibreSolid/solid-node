## Context

`node.operations` is composed by premultiplication — `_compose_matrix`
in `solid_node/node/base.py` walks the list with
`matrix = op.matrix() @ matrix` — so **index 0 is innermost** and later
indices are outermost. The list is `[motion…][rest…]`: `_insert_motion`
(base.py:307) computes the length of the leading run of operations
carrying `_motion` and inserts there, "the end of the node's motion
block".

Both kinds of motion use it:

- a hand-written `rotate`/`translate` under a simulate phase, through
  `_place_operation` (base.py:329);
- a joint, through `apply_motion` (base.py:342), whose only caller in the
  tree is `Joint.place` (`solid_node/motion/joints.py:318`). `apply_motion`
  exists because `_place_operation` *appends* outside any phase, and a
  joint's axis and anchor were already carried into the node's own frame
  by `Joint._carry`, so an appended operation would be read in the
  parent's frame instead.

So composition order is application order for both, and for a
relation-bound joint that is the couplings solver's pass order.
`solve_relations(self)` runs at the END of the simulate phase
(`solid_node/node/assembly.py:96`), after the author's `simulate()`, so a
relation-bound joint is always applied after every hand-written call in
that method.

`Joint._carry` composes only the node's NON-motion operations. A joint's
axis and anchor are therefore carried through the node's **rest**
placement and never through a sibling joint's motion. That is what makes
a fixed composition order well defined at all, and it is unchanged by
this cycle.

## Goals / Non-Goals

**Goals**

- A composition order a reader of the class body can see, and a solver,
  a driver, a derived coordinate or a second animator cannot change.
- Ordering by JOINT, not by coordinate or by operation, so a joint owning
  several coordinates or emitting several operations fits the same rule.
- One seam, one field, no new public name.

**Non-Goals**

- The `Orbit` and `Free` primitives (`workflow/docs/composed-joints.md`
  §5, §6). This cycle must not box them in; it does not build them.
- Any change to the couplings solver, its pass order, or its refusals.
- The "own placed origin" anchor mode, the `.repeat()` relation fan-out,
  the multi-source relation, and the joint-on-a-data-built-child — four
  separate findings in `workflow/warts.md` that several of the same
  projects also wait on.
- Rest placement, `render()`-phase operations, and the legacy-render path.
- Any deprecation of hand-written motion. Nothing is deprecated.

## Decisions

### 1. Declaration order is the composition order, first declared innermost

The first joint declared on a class is applied closest to the body, in
the node's own frame; the last declared is outermost. Base-class joints
come before a subclass's; a subclass redeclaring an inherited joint keeps
the base's slot with its new arguments.

`declared_joints(node_class)` already produces exactly that order: it
walks `reversed(node_class.__mro__)` — object first, base before subclass
— and assigns `found[name] = value` into a dict, so a class body's joints
arrive in definition order (PEP 520) and a redeclaration reuses its key
and keeps its position. Multiple inheritance uses the MRO's
linearization, which is deterministic. The change makes this ordering
**normative**: today it is enumeration order, and after this cycle it is
the composition order, readable off the class without instantiating
anything.

*Why declaration order and not a keyword.* YouCanBuildDog offered
"an explicit ordering keyword" as an alternative. Rejected: declaration
order is already the reading order of the class; all seven projects can
and do write their declarations in the order they want them applied; a
keyword would be a second way to say one thing, and would need a
total-order semantics across inheritance that nothing has asked for. If
an escape hatch is ever needed, reordering the declarations is it.

### 2. `apply_joint_motion(node, operations, slot)` replaces `apply_motion`

`apply_motion` takes one operation and has one caller. It is replaced by
an atomic seam that takes a joint's whole placement run and its slot:

    def apply_joint_motion(node, operations, slot):
        """Place a joint's operations as one contiguous run at the
        position its declaration slot dictates, and return them."""

The insertion index is **the length of the prefix of `node.operations`
whose entries are motion, carry a `_joint_slot`, and whose slot is
`<= slot`.** Equivalently: after every joint of an earlier-or-equal slot,
before the first joint of a later slot, before every hand-written motion,
before every rest operation. Each inserted operation carries
`_motion = True` (unchanged) and `_joint_slot = slot` (new), and is
tagged with the current phase's assembly exactly as `apply_motion` tags
it today: under a simulate phase it is tagged and swept; outside any
phase it is marked as motion and left untagged.

The scan is O(len(operations)) and tolerant of a missing operation in
exactly the way `Joint.clear` already is: an operation a sweep or a
checkpoint restore has dropped is simply not there.

`slot` is `list(declared_joints(type(node))).index(self.name)`, from the
per-class cache `declared_joints` already keeps.

*Why an atomic run and not one call per operation.* A `Revolute` with an
off-origin anchor emits three operations, an `Orbit` will emit one and a
`Free` up to four. Inserting them one at a time would need the
"equal slot" case to be a well-defined append, which is a second rule for
no benefit; inserting the run at one index makes contiguity an invariant
the seam enforces rather than one the caller preserves.

*Why `apply_motion` is replaced rather than kept.* It has exactly one
caller, is not exported from any public module, and does not appear in
`tests/test_docs_exports.py`. Keeping a single-operation variant would
leave a path by which a joint operation could enter the list without a
slot.

### 3. Hand-written motion composes outside the whole joint block, in call order

`_insert_motion` is **unchanged**: a hand-written `rotate`/`translate`
under a simulate phase still goes to the end of the whole motion block.
Since joint operations are now inserted by slot at the head, a
hand-written operation applied earlier stays outside them, and one
applied later lands after them. Hand-written operations keep their call
order among themselves. The entire behavioural change lives in the
joint's insertion index.

This replaces the joints spec's "they apply in the order they were
applied". It is the one part of the change no project asked for. Two
reasons for it: the joint block has to be contiguous for the slot rule to
be stateable at all; and a hand-written motion that could sit *between*
two joints would reintroduce, in a different disguise, exactly the
invisible ordering this cycle removes.

*What it can change.* Only a node where a hand-written simulate-phase
`rotate`/`translate` is applied BEFORE that node's joint is bound —
including every relation-bound joint, since relations solve last. A
source survey of all sixteen migrated projects
(`workflow/docs/composed-joints.md` §4.7) found zero such sites: six
projects have no `simulate()` at all, five assign only coordinates, and
the five that do move something by hand move a node whose class declares
no joint (openvmp's blueprint-built children, openflexure's `M3Nut` and
`FlexureLeg`, Prusa3-vanilla's `ZScrew`, Metamaquina2's `ThreadedRod` and
`ShaftCoupling`, snappy-reprap's `CableChainLink`). Hand-written
placement on a joint-carrying node is common but always in `render()`,
which is rest placement and is untouched. That survey is a prediction
from source, not evidence; the pose comparison (task 5) is the evidence —
and task 5.1 states which framework tree each half of it must run
against, because the workspace venv imports `solid_node` editable from
the PRIMARY checkout and a capture taken with `PYTHONPATH=.` alone
measures main, not this worktree.

### 4. Re-binding, sweeping, and two animators

**Re-binding one joint of several.** `Joint.place` calls `Joint.clear`
first, which removes that joint's previous operations by object
identity; the new run is then inserted at the joint's own slot. The
rebound joint returns to its place instead of jumping outside its
siblings. Today a second binding of the inner joint silently reverses the
composition; that is the fix, not a side effect.

**The sweep.** `_sweep(assembly)` (`solid_node/node/assembly.py:14`)
drops every operation tagged with that assembly, wholesale, at the head
of that assembly's render. Afterwards the joint block holds only joints
another animator owns, or untagged ones, and the run that follows
rebuilds the swept joints at their own slots — whatever order the solver
reaches them in, and whatever order they were reached in last time. The
sweep therefore needs no change: slot-based insertion is what makes the
result order-independent, where object- or tag-based removal only makes
it accumulation-free.

**Two independent animators on one node.** The wart's "a wheel spun by
its axle and steered by the steering assembly": assembly A owns the
first-declared joint, B the second. After A's sweep and rebind, A's
operations return inside B's instead of landing outside them. This too is
a fix that falls out of the slot rule.

**Not addressed here.** The sweep drops a joint's operations but not its
coordinate's VALUE, which is the separate finding "An author-bound joint
keeps its value but loses its motion between runs" in `workflow/warts.md`
(Prusa3-vanilla, hangprinter). It is untouched by this cycle.

**Not addressed here.** `save_checkpoint`/`restore_checkpoint`
(base.py:1140) index from the END of the operations list while motion
inserts at the head. That mismatch predates this cycle — motion has
inserted at the head since the motion layer landed — and this cycle
neither worsens nor fixes it.

### 5. Inheritance and redeclaration

Base joints innermost, in the base's declaration order; then the
subclass's new joints, in its own declaration order. A redeclared joint
keeps the base's slot and takes its new axis, anchor, range and unit.
This is what `declared_joints` already reports, and decision 1 makes it
the contract.

The existing refusal in `Joint.__set_name__` — a joint may not shadow a
non-joint attribute of a base — is unchanged, as is the joint/port
name collision refusal.

### 6. What a reader sees when the tree is serialized

`solid_node/core/serializer.py:361` publishes
`[operation.serialized for operation in node.operations]` in list order,
and the viewer applies them in the same order (ADR-028: mesh and viewer
placement share one composition semantics). A node's `operations` array
therefore reads, left to right, innermost to outermost:

    [ joint 1's operations ][ joint 2's ] … [ hand-written, in call order ][ rest placement ]

with joint *n* being the *n*-th declared on the node's class. `_motion`
and `_joint_slot` are Python-side attributes and are **not** serialized:
the document format, its keys and the viewer are unchanged. A symbolic
binding still publishes its expression, and `set_keyframe` /
`clear_keyframe` still work on it.

### 7. Forward compatibility with `orbit-joint` and `free-joint`

The ratified rule is stated over "the operations a joint's placement
produces": a contiguous run of any length, ordered among themselves as
that joint's own `placement()` returns them — one or three operations for
a `Revolute` today, one for a `Prismatic`. That is all the SPEC says, and
deliberately so: it describes only the joints that exist.

The forward-compatibility INTENT, which is this design's and not a
ratified promise, is that the same rule should carry the two stacked
cycles without being reopened. An `Orbit` would emit one translation and
a `Free` up to four operations, which the contiguous-run rule already
covers. A `Free` would additionally own six coordinates — and because the
implementation orders by JOINT SLOT rather than by coordinate, it would
occupy one slot and be placed as one unit even though six separate
relations might bind it in any order. Nothing in this cycle depends on
that being true, and if cycle 3 finds it is not, cycle 3 revises the
contract rather than this one having over-promised. Task 1.8 pins the
part that IS testable today — a three-operation joint staying one
unbroken run — so the guarantee is measured rather than asserted.

## Risks / Trade-offs

- **A visible behaviour change with no project asking for it**
  (decision 3). Mitigated by the survey in §3 and proved by the
  sixteen-project pose comparison, max deviation 0, before the cycle is
  called done. If any project's pose moves, the finding goes back to the
  pilot rather than being absorbed by loosening the rule.
- **Two framework tests invert.** They are the fixture for exactly the
  case that changes, so they must be modified rather than deleted, and
  the modified assertions have to state the new order explicitly enough
  that a future accidental revert fails them.
- **A same-slot survivor.** If an operation of the joint being re-bound
  survives both `_sweep` and `Joint.clear` — the path `Joint.clear`'s
  docstring names, the test runner's checkpoint restore resurrecting an
  old object — the `<= slot` rule places the new run after it, leaving
  the stale one innermost. `<` and `<=` differ only in this case. Open;
  a test that restores a checkpoint between two bindings of one joint
  would settle it.
- **A legacy render inside a joint's frame.** A `render()` that read a
  driver re-runs per binding and appends tagged but NON-motion
  operations, which `Joint._carry` composes into the rest placement it
  inverts — so such a node's carried axis moves with the binding. This
  predates the cycle and the cycle does not change it, but it is a
  latent hazard worth naming.
- **`declared_joints`'s order becomes load-bearing.** A future
  refactor of the enumerator that changed its walk (e.g. sorting names)
  would now silently change geometry. Task 1.5 asserts the enumerator's
  order and the composed order together for exactly that reason.
