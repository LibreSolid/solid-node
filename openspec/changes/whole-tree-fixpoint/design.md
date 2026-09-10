# Design: one enumeration, one fixpoint

Everything below is measured on this branch (`motion-catalogue-2`, base
main `5b28510`, with cycle 1 / ADR-096 on it) by the probes in
`evidence/`, not read off the source.

## 1. The order of events today

Measured by `evidence/probe_order.py`, which patches `_sweep`, `_rest`,
`clear_solved`, `solve_relations` and `assemble` to print one line each,
over a three-level tree `Root → Child → Grandchild → Leaf`.

| # | event | who runs it |
|---|---|---|
| 1 | `Root.render()` is called by a walker (`assemble`, `_receive_state`, the serializer) | walker |
| 2 | `_sweep(Root)` — drop the operations Root tagged last run | lifecycle |
| 3 | `_rest(Root, render)` — the author's `render()`, once per instance; children realized and placed at rest | lifecycle |
| 4 | `clear_solved(Root)` — drop the value and binder of every coordinate ROOT bound through a WIRING OR A RELATION last run. **What the author bound is not cleared.** | lifecycle |
| 5 | `Root.simulate()` | author |
| 6 | `solve_relations(Root)` — inventory, propagate to a fixpoint over Root's own records, wirings and derived formulas, then REFUSE what is left | lifecycle |
| 7 | the walker links Root's children and reads Root's geometry | walker |
| 8 | steps 1–7 for `Child`, then for `Grandchild`, then `Leaf` | walker |

Two consequences the change is answerable to, both measured:

- **A parent's relations are solved before any child's phase begins.**
  Every `simulate()` read of a relation-bound coordinate in the
  catalogue — 30 sites in 9 projects — depends on it — the hexapod's `Chassis.simulate()` reads eight coordinates the
  ROOT's relations bind, Metamaquina2 and snappy-reprap read theirs
  unguarded. Nothing may disturb it.
- **The walk reads a subtree's geometry before a later sibling's phase
  runs** (`probe_interleave.py`):

      geometry read of Microscope / phase Microscope
        geometry read of body / phase body
          geometry read of lower_strut / operations applied to lower_strut
        operations applied to body
        geometry read of z_axis / phase z_axis
          ...

  A binding delivered to `lower_strut` after `phase z_axis` is a pose
  nobody sees. This is why a deferred relation cannot simply be retried
  whenever some later node happens to solve.

And one more, which decides where the driver snapshot goes
(`probe_state_order.py`): `set_state` binds a node's entries immediately
before rendering THAT node, so while the root's phase runs, a child holds
`{}` on the first call and the previous pose's values on the second.

## 2. The order of events after the change

| # | event | who runs it |
|---|---|---|
| 1 | `Root.render()` is called with no tree pass open → **the pass opens**, and Root owns it | lifecycle |
| 2 | `_sweep(Root)`; `_rest(Root, render)`; Root's children are LINKED | pass |
| 3 | `clear_bound(Root)` — drop the value and binder of every coordinate Root bound **during its previous simulate phase**, whoever bound it | pass |
| 4 | `Root.simulate()` | author |
| 5 | `attempt(Root)` — inventory and propagate to a fixpoint over Root's own records, wirings and formulas, exactly as step 6 does today; **whatever is still unresolved is handed to the pass instead of refused.** A `DoublyBound` still raises here | pass |
| 6 | steps 2–5 for `Child`; then for `Grandchild`; parents before children, declaration order among siblings, over the children each `_rest` returned | pass |
| 7 | **the pass's fixpoint**: propagate over every deferred record, wiring and formula of the whole tree, repeatedly, until nothing changes. Each step runs under the phase of the assembly that STATED the item, so its motion carries that assembly's tag and lands in that assembly's cleared-next-run list | pass |
| 8 | **refuse**: `UnreachedCoordinate` / `NotInvertible` for what the pass could not reach, naming the class that stated it | pass |
| 9 | **refuse the reads**: every unbound read recorded in steps 4/6 whose coordinate steps 5–7 afterwards bound | pass |
| 10 | the pass closes; every node below Root carries a mark saying its phase already ran for this enumeration | pass |
| 11 | `Root.render()` returns Root's rest children; the walker links, reads geometry and descends; each descendant's `render()` consumes its mark and returns its rest children WITHOUT re-running its phase | walker |

`set_state(**states)` becomes: validate; propagate the snapshot over the
tree AT REST, node by node, linking as it goes, exactly as it addresses
and strips qualified names today; then run ONE enumeration from the node
it was called on. `clear_state` the same. Nothing else about them moves.

### Why per-level attempt plus one tree fixpoint, and not one tree-wide fixpoint

The briefing's alternative — every `simulate()` first, then one fixpoint
— cannot be taken. A child's `simulate()` may READ a coordinate the
parent's relation binds, and 30 sites in nine projects do; that works
today only because the parent's relations are solved before the child
simulates. Holding every relation until every `simulate()` has run would
hand the hexapod's `Chassis.simulate()` eight empty slots and stand the
robot at zero, silently. So the per-level attempt stays exactly where it
is, and only what would have been REFUSED travels to the pass.

The mirror — a parent's `simulate()` reading a coordinate a DESCENDANT's
relations solve — stays impossible, and is now refused by name (§5)
rather than reordered into working. Reordering it is the same trade seen
from the other side, and it would break all thirty.

"Defer, then re-run once" is one pass PHASE, which internally iterates to
a fixpoint the way a node's own solve already does: a deferred chain may
be arbitrarily long (clock 01's is three relations), and iterating until
nothing changes is what terminates it. The pass never re-runs a
`simulate()`.

## 3. What defers, what does not

At the end of a node's own attempt (step 5), an item that is still
unresolved is DEFERRED rather than refused:

| item | today | after |
|---|---|---|
| a record with neither end bound | `UnreachedCoordinate` at the node | defers |
| a record whose driven end is bound and whose law offers no inverse | `NotInvertible` at the node | defers — another statement may still bind the driver end, and then the record has two binders and is refused as `DoublyBound`, which is the truth |
| one copy of a BROADCAST whose driven end is bound | `NotInvertible` at the node | defers, and refuses in the pass naming the copy; a broadcast is still never read backwards |
| a derived formula, bound, with more than one unknown term | `UnreachedCoordinate` at the node | defers |
| a wiring whose source is unbound | raises at the node | defers |
| a coordinate two statements would bind (`DoublyBound`) | raises at the node | **unchanged — raises at the node.** A contradiction is not a question of timing, and deferring it would only move the message further from the class that caused it |
| a joint's declared range refusing a value | raises where it binds | unchanged |

**Nothing that solves today defers.** A record defers only where it would
otherwise raise, so no working model changes its pose, its pass order or
its timing. That is the change's central compatibility claim and the pose
comparison over 23 projects is its proof.

### Pass order

The pass's fixpoint iterates over deferred items in TREE ORDER — the
order their assemblies' phases ran, parents before children, declaration
order among siblings — and within one assembly in declaration order, with
a broadcast's copies in copy order at the position of their declaration
(ADR-096, unchanged). So the order is one a reader of the tree can state,
and it does not depend on which node happened to defer first.

### Wirings and broadcasts

A wiring is already the forward-only identity relation the couplings spec
calls it; it defers with the rest and is applied by the pass under its
declaring parent's phase, so a wiring whose source a DESCENDANT's relation
solves now binds instead of raising. A broadcast is resolved into n
records at realization (ADR-096) and the pass sees n ordinary records: each
defers, binds and refuses on its own, and each message names its copy.

### What the errors name

The three errors keep their names, their kinds and their message bodies.
Every message already carries the relation as written and the class that
declared it (`RelationRecord.described()`), and that is what the pass
prints; it adds one clause saying the relation was deferred until the
descendants had solved. The node paths get BETTER: today a root's refusal
reads `column (Leaf).turn`, because `where()` falls back to the class name
when nothing has linked the node and the root solves before its children
are linked (`probe_unreached.py`). The pass links each node's children
before descending, so the same refusal reads `z_axis.column.turn`.

## 4. The pass, concretely

- A module-level stack in `solid_node/node/phase.py`, beside the phase
  stack it already keeps. `render()` consults it: no pass open → this
  call opens one and drives the subtree; a pass open → this is the pass
  driving, and the call is the ordinary lifecycle.
- **Not** "the root of the linked tree": `top_of()` is unreliable before
  a walker has linked anything, and a component rendered alone must open
  its own pass over its own subtree — which it does, and a relation of
  its that needs the absent parent refuses at the end of that pass,
  exactly as today.
- The mark of step 10 is CONSUMED by the first `render()` that arrives
  afterwards. It is an optimization, not a semantic: without it each
  descendant's `render()` would open a pass over its own subtree and a
  node at depth d would simulate d+1 times per enumeration. With it, a
  node's phase runs once per enumeration — the same count as today. A
  node whose `render()` is a LEGACY render (one that read a driver, and
  therefore re-runs per binding) carries no mark and re-runs, as today.
  A mark left unconsumed (a walker that skipped a subtree) is harmless:
  the next pass sets it again before anything reads it.
- A node the author's `render()` did not return — an `omit()`ted child —
  is not walked by the pass, exactly as no walker reaches it today.
- Children built from data inside `render()` are in the list `_rest`
  returns, so the pass walks them like any other child.

## 5. The read of a coordinate a relation binds

**The rule.** A read of a coordinate slot holding no value, made while a
simulate phase is running, is RECORDED on the open pass: the coordinate's
declared name, the node, the class whose `simulate()` was running, and the
file and line of the read. At step 9, a recorded read whose slot was
afterwards bound **by a relation, a derived formula or a wiring** is
refused, naming the coordinate, the class that read it, the binder, and
the order: `simulate()` runs first; the relations of that class are solved
after it returns; a descendant's after that. A read whose slot the AUTHOR
then bound is not refused, and a read of a slot nothing ever bound is not
refused either — that is the unbound coordinate the solver already refuses
by its own name.

**Why not at the read.** Measured: eight `is None` guards in the
catalogue read exactly such a slot, and **five of them read a coordinate
that IS an end of a relation of the reading class** — Prusa i3's three
(`xaxis.py:208`, `yaxis.py:181`, `extruder.py:257`), the abacus's two
(`column.py:79`). In each the author binds the coordinate on the next
line and the relation reads it as its SOURCE. A refusal at the moment of
the read cannot tell that case from Thor's silent pulley, because at the
read they are the same event: an unbound slot. What separates them is
what bound it afterwards, and that is known at the end of the pass.

**A joint coordinate the same class's relation binds is the same case.**
Measured in `probe_own_read.py`: the own derived coordinate and the own
relation-bound joint coordinate both read `None` inside their class's own
`simulate()`. openflexure's `Actuator` moved its thread relation up into
`Axis` because of the second, not the first; one rule covers both, and the
message names whichever kind of binder it was.

**What the record costs.** The record is taken only on a read that finds
NO value during an open phase — the rare path — and it stores the
reader's code location (`filename` and `lineno` off the calling frame's
code object), never a frame or traceback object, so a bound read pays
nothing and an unbound one pays two attribute reads and a tuple. The
implementer measures it in tasks §8 with the rest.

**What it costs.** One site in the catalogue is refused by this rule:
`3DPrintedClocks/simulation/shared/motion.py:1060-1072`, at 32 clocks
(and its seconds-hand twin at 5). It reads two arbor coordinates
`Movement`'s own relations bind and assigns the resulting `None` into two
ports nothing drives — dead code the change lets the project delete along
with 37 forwarding relations. Proposal, "Decisions for the pilot" (a).

## 6. The stale author-bound joint

**Chosen: clear the value with the swept motion.** At the start of an
assembly's simulate phase, the framework drops the value and binder of
every coordinate that assembly bound **during its previous simulate
phase** — the author's bindings included — in the same moment as the
sweep that drops the operations it applied. `bind()` records the slot on
the running phase exactly as `_place_operation` records the operation on
it; the two lists are cleared together.

**Why not refuse the stale read.** The other half of the ratified choice
was to refuse a read of a value the sweep had invalidated. Three reasons
against: the `if value is None:` guard is what eight sites in the
catalogue write and it would refuse all of them, requiring an edit in
every project this cycle is not allowed to touch; the value and the motion
are two halves of one binding, so clearing them by one rule REMOVES the
asymmetry rather than naming it; and the ports spec already promises what
the clear delivers — "Bindings SHALL be re-evaluated on every
`simulate()`", "port binding SHALL NOT accumulate history".

**What `.value` reads between runs.** Unchanged outside a phase: a
coordinate holds what the last enumeration bound until the assembly that
bound it begins its next simulate phase. `capture_poses.py` reads every
coordinate after `set_state` returns and sees exactly what it sees today;
so do the tests and the serializer. Inside a phase it reads what has been
bound in THIS enumeration, and `None` before that.

**What is never cleared.** A binding made outside any simulate phase — in
`__init__`, in a test, through a bare `render()` with no walker — is not
recorded and not cleared, exactly as an untagged operation is never swept.
Two assemblies binding coordinates of one node clear only their own.

**The measurement.** `probe_stale.py` on the current tree prints
`value=37.5 operations=['Translation[37.5, 0, 0]']`, then
`value=37.5 operations=[]` twice. After the change all three runs print
the first line. Prusa i3's second-render deviations (37.5 mm, 70.4 mm,
0.05 mm) go to 0 and hangprinter's zero-defaulted winches are covered by
a test with a non-zero default.

## 7. A subclass replaces a named relation

- **The name is the attribute the relation was assigned to**, set by
  `Relation.__set_name__`, which already runs.
- `declared_relations(cls)` walks the MRO base-first, as now. A NAMED
  relation replaces any relation of the same name already found, and
  **keeps the base's position** in the enumeration — the rule a redeclared
  joint obeys (ADR-093, `declared_joints`), so the pass order a reader
  sees does not shift under inheritance.
- A BARE statement has no name and is additive, exactly as today. So is a
  named relation whose name no base used.
- **What the replaced relation reads as:** `declared_relations(Subclass)`
  reports only the replacing one, so no instance of the subclass ever
  resolves or records the base's. `Subclass.drive` off the class yields
  the replacing declaration and off an instance that instance's record.
  `Base.drive` and `declared_relations(Base)` are untouched, and an
  instance of `Base` still solves the base's relation.
- **Naming an inherited declaration needs no new vocabulary.** Measured
  (`probe_subclass.py`): a subclass body cannot write `rotor.spin`,
  because the base's declarations are not in its namespace; it writes
  `Actuator.rotor.spin`. The catalogue already does this —
  `shared.TrainArbor.turn.drives(...)` (wall clock 28),
  `MotionWorks.hour_holder.drives(...)` (three clocks).
- The relation cache is per class and already keyed on the class, so a
  subclass's enumeration is computed once.

## 8. Cost, and how it is measured

What is added per enumeration:

- one walk of the tree at rest to propagate the driver snapshot
  (`set_state`/`clear_state` only) — replacing the render-at-every-level
  the propagation does today, so it should be CHEAPER;
- one fixpoint iteration over the deferred items, which for every project
  in the catalogue today is over an EMPTY list — one predicate on an empty
  container per enumeration;
- one dictionary write per node to set the phase mark, and one read to
  consume it;
- for a project that DOES defer, one extra propagation pass per deferred
  chain link.

What is not added: no `simulate()` runs twice, and no node's phase runs
more often than it does today (the mark makes the walker's descent free,
where today it re-runs the whole phase at each level).

Measured in tasks §8, all on this branch, base against head, with one
heavy process at a time:

1. `capture_poses.py` wall time on Thor, 3DPrintedClocks wall clock 01,
   openflexure and the hexapod — the four largest trees — three runs each,
   reported as a ratio with the spread.
2. `pytest tests/test_couplings.py tests/test_kinematics.py
   tests/test_joints.py tests/test_ports.py` wall time, three runs.
3. A micro-benchmark in `evidence/`: 200 enumerations of the coupling
   fixture's `Train` and of a five-level synthetic tree, reported in
   microseconds per enumeration.

A regression worse than 5% on (1) is reported to the pilot rather than
absorbed.

## 9. Open questions

1. **Should the pass refuse a read that a WIRING bound?** A wiring is a
   binder like any other and the rule as written covers it, but no
   catalogue site reads a wired coordinate in its own `simulate()`, so
   the case is unmeasured.
2. **A relation deferred across two independent trees.** The pass is one
   enumeration of one tree; a project that renders two roots and expects a
   relation to cross between them was never supported and still is not.
   Nothing in the catalogue does it.
3. **Should `set_state`'s propagation validate before or after the
   enumeration?** Today an undeclared name is refused after a partial
   walk and rolled back; the proposal keeps that shape (propagate, judge,
   roll back, then enumerate). If the pilot would rather the enumeration
   never start on a rejected snapshot, that is a stricter contract and a
   smaller one — it is written the stricter way here.
4. **Does the read record belong in the released `ports` surface?**
   `BoundPort.value` is the seam; recording an unbound read there costs a
   branch on every read of an unbound slot only. If the pilot wants the
   rule confined to the couplings layer, the alternative is to record only
   reads of slots the pass knows a relation names, which is a larger
   pre-index and a weaker message.

## 10. What contradicts the ratified direction, plainly

- §3.4 says `UnreachedCoordinate` is raised "only when the whole tree's
  fixpoint leaves a relation unreached". **`DoublyBound` is excluded**
  here: it is not a timing failure and deferring it would move the message
  away from the class that caused it.
- §3.4's rider (b) offers "clear the value" or "refuse the stale read" and
  leaves the choice to the proposer. **Clear is chosen**, on the measured
  ground that eight catalogue sites write the guard the refusal would
  break (§6).
- §3.4 says the own-derived-coordinate read is "REFUSED by name" and
  reads as if the refusal happens at the read. **It happens at the end of
  the pass**, because five of the catalogue's eight guards read exactly
  such a slot legitimately and a refusal at the read would refuse them
  (§5). The read still never yields a value that silently turns nothing.
- §3.4 does not mention the driver snapshot. **`set_state` has to
  change**, measured in `probe_state_order.py`: without it every
  descendant simulates one pose late.
- §2 calls the solver change "a fixpoint over the tree instead of over one
  node's relations". Measured, it is **both**: over one node's relations
  first (30 catalogue reads depend on it) and over the tree afterwards for
  what is left.
