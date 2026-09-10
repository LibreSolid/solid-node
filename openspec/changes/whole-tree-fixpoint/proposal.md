## Why

A relation says what turns what. Today it may only say it about
coordinates that are bound, or reachable, **by the end of one node's own
simulate phase** — because that is when the solver runs, and it runs once
per node, parents before children, refusing whatever it could not reach.

So a machine cannot be described where it is understood. The survey
(`evidence/survey.md`, 27 simulation packages, 676 `drives` sentences)
found
**fourteen distinct workarounds in twelve projects**, each of them a
constant or a sentence in the wrong class:

- **The 8:1 of OpenTorque's planetary reducer is stated twice**, once in
  the reducer that owns the tooth counts and once at the root, because
  `reducer.planet_1.orbit.drives(output_stack.planet_carrier_b.turn)` —
  the carrier plates ARE the body the planets orbit with — is refused
  with `UnreachedCoordinate`. Its archived proposal quotes the refusal.
- **openflexure's root sentence does not exist.** Four laws are sourced
  from the root's `z_motor` instead of from
  `z_axis.actuator.column.travel`, each composing `column_travel(steps)`,
  so the gear ratio and the screw pitch are re-entered downstream of the
  `Axis` that already states them. The same project pushed the thread
  relation UP out of `Actuator` into `Axis` for the mirror reason.
- **Wall clock 01's going train cannot be stated in `Train`.**
  `centre.drives(third)` inside `Train` while `power.drives(train.centre)`
  stays in `Movement` is refused at `Movement`'s end, because `Train`'s
  relations have not run yet.
- **Every one of the 32 clocks writes a second relation whose only job is
  to make a coordinate readable** (`train.centre.turn.drives(motion_works.minute_arbor)`),
  and five write another. Two ports exist for it and nothing drives them.
- Thor states four ratios twice each — once as a relation, once
  recomputed in `simulate()` — with a comment naming the wart; the abacus
  re-binds a port **to its own already-bound value** so its own relations
  do not raise; open_robot_actuator hoisted `gear.spin.drives(pinion.spin)`
  into the root and said so; Prusa, Metamaquina2, snappy-reprap,
  poseidon, OpenCycloid and hangprinter each carry one more.

Three riders travel with it, all measured on this tree:

- **A class's own derived coordinate reads as an empty slot inside its own
  `simulate()`, and the code that reads it silently does nothing.**
  `probe_own_read.py`: `self.left` yields `<rotational port left of Art4:
  None>`, `rotate(None, ...)` appends a rotation that turns nothing, and
  the same coordinate reads `18.0` one phase later. That is Thor's two
  motor pulleys, caught only by a pose comparison. A JOINT coordinate the
  same class's relation binds behaves identically — openflexure's thread
  ratio moved a level up for it, and 3DPrintedClocks reads two such
  coordinates in `shared/motion.py:1060-1072` at 32 clocks, writing `None`
  into two ports.
- **An author-bound joint keeps its value between runs while its motion is
  swept.** `probe_stale.py`: run one leaves `value=37.5` and one
  translation; runs two and three leave `value=37.5` and NO operations.
  The `if value is None:` guard skips the rebind and the body stands at
  rest holding a number that says it moved. Prusa i3 measured 37.5 mm,
  70.4 mm and 0.05 mm of pose deviation on a second render; hangprinter's
  winches carry the same guard, masked by a zero default.
- **A subclass cannot replace a named relation of its base.**
  `probe_subclass.py`: the subclass's `drive` and the base's `drive` are
  two relations and the solve raises `DoublyBound`. OpenTorque's
  `ReducerPosePreview` is a SIBLING rather than a subclass for exactly
  this; hangprinter copied a whole winch class rather than inherit one.

## What Changes

**One tree pass.** The outermost `render()` of an enumeration opens a
TREE PASS and drives every assembly's simulate phase itself, parents
before children, declaration order among siblings — the order the walk
already produces. Each node's own relations, wirings and derived
coordinates still attempt at the end of that node's own phase, exactly as
today, so **no relation that solves today is deferred and no coordinate a
child's `simulate()` reads today becomes unbound** (every `simulate()`
read of a relation-bound coordinate in the catalogue — 30 sites in nine
projects — takes it from an ANCESTOR's relation, and every one keeps its
value). What today would be
REFUSED is instead DEFERRED to the pass, which runs one fixpoint over the
whole tree's deferred records once every phase has run, and only then
refuses.

**Deferral is exactly the set that refuses today.** An unreached record,
a record whose driven end is bound and whose law offers no inverse, a
derived formula with more than one unknown, and a wiring whose source is
unbound all defer. A DOUBLY BOUND coordinate never defers: it is a
contradiction, not a question of timing, and it is refused where it is
found.

**The refusal moment moves, the refusals do not.**
`UnreachedCoordinate`, `NotInvertible` and `DoublyBound` keep their names,
their kinds and their contents, and every message still names the class
that STATED the relation. They get better paths: today a root's refusal
reads `column (Leaf).turn` because children are not linked when the root
solves (`probe_unreached.py`); the pass links each node before descending,
so the same refusal reads `z_axis.column.turn`.

**A read of a coordinate a relation goes on to bind is refused by name.**
An unbound coordinate read during a simulate phase is RECORDED — the
coordinate, the node, the reading class and the line. At the end of the
pass, every recorded read whose slot was afterwards bound by a relation, a
derived formula or a wiring is refused, naming the binder and stating the
two-phase order. A read of a coordinate the AUTHOR then binds is not
refused: that is the rest-default guard eight sites in the catalogue
write, and five of those read a coordinate that IS an end of a relation of
the reading class, so a refusal at the moment of the read would refuse
every one of them. Deferring the judgement to the end of the pass is what
makes "a guard" and "a silent no-op" decidable, and it is decided by what
actually bound the coordinate.

**A coordinate is cleared with the motion it caused.** The value and
binder of every coordinate an assembly bound DURING ITS SIMULATE PHASE —
whoever bound it, the author included — are dropped at the start of that
assembly's next phase, in the same moment and by the same rule as the
sweep that drops the operations. A binding made outside a phase (in
`__init__`, in a test, by a hand `render()`) is never recorded and never
cleared, exactly as an untagged operation is never swept. Between
enumerations a coordinate still reads what the last one bound, which is
what `capture_poses.py`, the tests and the serializer read.

**A subclass replaces its base's relation by NAME.** The name is the
attribute the relation was assigned to. A subclass assigning a relation to
a name a base already used replaces it, keeping the base's position in the
pass order (the rule a redeclared joint already obeys, ADR-093). A bare
statement has no name and stays additive. The replaced relation is not
enumerated for the subclass, never resolves and never records; the base
still enumerates its own.

**The driver snapshot moves ahead of the enumeration.** `set_state` binds
each node's entries immediately before rendering that node, so at the
moment the root's phase runs a child holds `{}` on the first call and the
PREVIOUS pose on the second (`probe_state_order.py`). A pass driven from
the root would simulate every descendant one pose late. `set_state` and
`clear_state` therefore propagate the snapshot over the tree at rest
first, and then run ONE enumeration. Everything they refuse, they refuse
the same way.

**Why a tree pass and not a lazy retry.** `probe_interleave.py`: for a
root with two subtrees the walk reads the FIRST subtree's geometry before
the SECOND subtree's `simulate()` runs. openflexure's sentence drives a
body in `body` from a coordinate in `z_axis`; solved after the walk had
passed `body`, it would be a pose nobody sees. Every simulate phase must
finish before the walk reads anything.

## Decisions for the pilot

**(a) 32 clocks go red on the read refusal, and the fix is a deletion this
change makes possible.** `3DPrintedClocks/simulation/shared/motion.py:1060-1072`
reads `self.arbor(minute_index).turn.value` — a coordinate `Movement`'s own
relations bind — and assigns the `None` it gets into
`motion_works.minute_arbor`, a port nothing drives. Five clocks do it
again for the seconds hand. It is dead code today; under the new rule it
is a refusal. Those thirteen lines and the two ports go away when the
project is resumed, together with 37 forwarding relations. The options
are: refuse now, and carry 3DPrintedClocks red until it is resumed (the
window cycle 2 already opened for three projects); or refuse behind a
`FutureWarning` for one cycle. **This proposal refuses now**, and the
change's own pose evidence for that project runs on a read-only overlay
with those thirteen lines deleted, the discipline cycles 2 and 3 use.
Nothing else in the catalogue is refused by the new rule.

**(b) `set_state`'s restructuring is a real change to a released
surface.** It is required by the tree pass and cannot be deferred to
another cycle without leaving every descendant a pose behind. Its
observable contract is unchanged — the same merge, the same qualified
addressing, the same refusals, the same rollback — but the propagation no
longer renders at each level, and the errors an unbound driver raises
surface in the single enumeration that follows rather than partway down
the walk. Confirm this belongs in this cycle.

**(c) The tree fixpoint does NOT make a class's own relation readable
inside its own `simulate()`, and this change makes that permanent.** It
makes the SENTENCE statable, not the value early. openflexure's
`Actuator` may now state its own thread relation, but if it does, the
`band.span` line that reads `column.travel.value` becomes a refusal
instead of the working read it is today. Which of the two it keeps is its
own stage-B choice; the framework names the order either way.

## Impact

- **Specs:** `couplings` — two ADDED requirements ("Relations defer to a
  whole-tree fixpoint", "A read of a coordinate a relation binds is
  refused, never an empty slot") and three MODIFIED ("A relation is stated
  by `drives` in a class body" for the named replacement, "Relations are
  solved from the bound side, at the end of the owning simulate phase" for
  the deferral and the clear rule, "Three refusals keep a wrong drive
  network from becoming a pose" for the refusal moment). `kinematics` —
  two MODIFIED ("Render at rest, simulate per instant" for the tree pass
  and the clear rule, "Multi-driver state binding" for the snapshot ahead
  of the enumeration). `joints` — one ADDED ("An author-bound joint is
  cleared with its motion"). `node-model` — one MODIFIED ("Template-method
  render lifecycle": a node's phase runs once per enumeration, driven by
  the pass). `ports` is untouched: "Bindings SHALL be re-evaluated on
  every `simulate()`" and "port binding SHALL NOT accumulate history" are
  what the clear rule finally makes true of every coordinate.
- **ADRs:** one new ADR — the enumeration's simulate phases are one tree
  pass — revising ADR-089's per-instance solve boundary and citing
  ADR-093 for the position a replaced relation keeps and ADR-096 for how
  a broadcast's copies sit in the pass.
- **Code:** `solid_node/motion/couplings.py` (the solver splits into an
  attempt that defers and a pass that refuses; `clear_solved` becomes
  "clear what this phase bound"; `declared_relations` replaces by name),
  `solid_node/node/assembly.py` (the pass, the phase mark, `set_state`'s
  propagation), `solid_node/motion/ports.py` (`bind` records the slot on
  the running phase; the unbound read is recorded), `solid_node/node/phase.py`
  (the pass's own stack). `joints.py`, `declarative.py` and the serializer
  are untouched.
- **Tests:** `tests/test_couplings.py`, `tests/test_kinematics.py`,
  `tests/test_animator_tag.py`, `tests/coupling_project/` — the deferred
  chain, the ancestor sourcing from a descendant, the read refusal, the
  stale rebind, the named replacement, and the order guarantees that must
  NOT change.
- **Projects:** none is edited. The evidence is the pose comparison over
  all 23, base against head, at maximum deviation 0 — except Prusa i3 and
  hangprinter, whose SECOND-render deviations (37.5 mm, 70.4 mm, 0.05 mm)
  must go to 0, and 3DPrintedClocks, which is captured at head on the
  read-only overlay of (a).
- **Users:** none. The motion layer is unreleased and lives in
  `docs/changelog.rst`'s Unreleased section; the catalogue is every reader
  there is. `set_state` IS released (0.6.0) and its observable contract
  does not change.
- **Dependency:** cycle 1 (`repeat-fan-out`, ADR-096) must be on the
  branch — it is; a broadcast's n records defer and refuse one by one.
  Cycles 2 and 3 are independent of this one: they change where a joint's
  arguments are read, never when a relation solves.
