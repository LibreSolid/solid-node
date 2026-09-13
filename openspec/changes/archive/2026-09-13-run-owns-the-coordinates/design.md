## Context

Everything a running root needs sits one layer above a solver that was
built to do the opposite. Measured on this tree
(`solid_node/motion/couplings.py`, `solid_node/node/assembly.py`,
`solid_node/simulation/sim.py`):

- **The solver orients from the bound side and clears freshness.**
  `_run_phase` calls `clear_solved(assembly)` before the author's
  `simulate()`; it drops the value and binder of every slot the
  assembly's PREVIOUS phase bound whose `_enum_marker` is not the current
  enumeration (`couplings.py:1782-1811`). A coordinate the run bound
  outside any enumeration carries `_enum_marker = None` and would be
  swept on the first tick.
- **Both ends bound is a contradiction today.** `_step_relation` refuses
  `DoublyBound` when `driver_bound and driven_bound` and no direction is
  recorded (`couplings.py:2012-2018`); `_step_wiring` refuses when the
  target holds a value (`:2133-2135`); `_claim` refuses when the end is
  bound (`:1996-1997`). Under a run every relation end is bound before
  the phase runs.
- **`ResolvedEnd.bound()` reads `_bound_by`** to decide whether a
  leftover value is this enumeration's answer (`couplings.py:1478-1522`);
  a slot the run rebinds outside a phase keeps the stale `_bound_by` the
  rest render left, and would read as unbound.
- **`set_state` refuses any name that is not a declared driver id**
  (`assembly.py:341-375`) and delivers entries only into assemblies'
  `_states`; a joint on a leaf (`tests/coupling_project/parts.py::Rod`)
  is reachable by no snapshot entry.
- **`Time` requires `loop`** (`ports.py:466-487`), `read_time` scales
  `$t` by it (`assembly.py:557-560`), `animation_block` publishes it
  (`serializer.py:240-243`) and the snapshot manager multiplies by it
  (`manager/snapshot.py:227-228`).
- **`Sim.trajectory` appends every tick** (`sim.py:251`), and
  `Instruction` takes `targets` only (`instruction.py:34`).
- **A law is already an expression builder.** `Affine.forward` is
  ordinary arithmetic over whatever it is handed; a `DriverToken` or a
  `symbol()` builds an `ExpressionNode` graph (`scad_expression.py`),
  `solid_node.math`'s primitives emit `call` nodes whose names are the
  closed list `SYMBOLIC_BUILTINS`, and `GraphValue.evaluate(inputs)`
  already evaluates such a graph numerically over named inputs.
- **The spike** (`workflow/open-run-simulation/spikes/kernel.py`) proved
  the tick/rollback/checkpoint/ownership shape and measured bounded
  memory; it declared events and memory, which the decision removes. It
  is evidence for the tests and the failure modes, not a design to copy.

The authority is the pilot's decision of 2026-09-13 in
`workflow/open-run-simulation/design.md`, items 1, 2, 4, 5, 7 and 8,
restricted to continuous laws; the cycle split is in `roadmap.md`,
"Execution, 2026-09-13".

## Goals / Non-Goals

**Goals:**

- `Time.running()` as a third time base with the same declaration rules
  as `Time(loop=)`.
- One `Sim` whose bank under a running root is every driver and every
  joint coordinate of the linked tree, keyed by qualified id, initialized
  from the untimed rest pose.
- Continuous laws integrated exactly over a tick; propagation in the
  direction the rest render solved; hold; conflict with rollback.
- The run as a binder the existing solver recognizes, so nothing about
  purity, sweeping or the whole-tree fixpoint changes.
- Commands with one owner per input, an outcome handle, retirement;
  `Instruction(by=)`; snapshot/restore/reset; bounded recording.
- Nothing imported, and nothing changed, for a model that declares no
  running time.

**Non-Goals:**

- Jumps: discontinuous primitives are refused, not integrated (cycle 2).
- Stops: a joint's range is refused, not localized (cycle 3); `blocked`
  never occurs.
- Export of the compiled program, the viewer worker, phase/winding
  representation, real-time playback (cycles 4 and 5).
- A push-that-does-not-pull law kind, phase admissibility on
  re-engagement (decision item 9).
- Any state declaration by the author, any `Running` object, any
  `running(r)` protocol.
- Performance beyond correctness: the evaluator is `GraphValue.evaluate`
  per relation per tick; a compiled evaluator is cycle 4's business.

## Decisions

### 1. `Time.running()` is `Time` with no loop, and it reads as an undeclared root until bound

`Time` keeps its one field, `loop`, which becomes optional: `Time(loop=L)`
as today, and `Time.running()`, a classmethod returning a frozen instance
whose `loop` is `None`. `Time()` with no argument is refused naming both
spellings. `mode` is a property: `'loop'` or `'running'`, readable off
the class (`Root.time.mode`) as `loop` is. `__set_name__` is untouched,
so the name and the assembly rules — and the below-the-root refusal in
`read_time` — apply to both bases. `declared_time(cls)` returns the
declaration either way; a consumer reads `.mode`.

Under a running root `self.time` reads: bound, the bound number (the
`Sim` binds `k * dt` seconds as it does today); unbound, **bare `$t`**,
exactly what an undeclared root reads. Elapsed seconds have no symbolic
form until the compiled program is published (cycle 4), and the three
producers that read `loop` — `animation_block`, the snapshot manager and
`read_time` — treat `loop is None` as "no loop": no `loop` key, a
fraction keyframed as an undeclared root's, `$t` unscaled. A running
root's document is therefore byte-identical to an undeclared root's,
and `solid build`, `solid develop` and `solid snapshot` keep working on
it.

*Alternatives.* `Time(running=True)` — a second field that must be
exclusive with the first, checked in `__post_init__`; rejected as two
spellings of one fact where a constructor per base reads as the
declaration it is. Refusing an unbound read of `time` under a running
root — honest about the missing symbolic form, but it would fail a
build whose `simulate()` reads `self.time` for a reason that lives
entirely in the run, and a running model does not need to read time
in `simulate()`; rejected, and recorded as an open question for cycle 4.

### 2. The bank: drivers and joint coordinates, by qualified id, leaves included

The bank's keys come from the same walk `qualified_drivers` performs
(`node.qualified.drive_tree`), extended by a `visit` that collects, for
EVERY linked node the walk reaches — assemblies and leaves alike, since a
joint may be declared on a leaf (`coupling_project.Rod`) — the coordinates
of `declared_joints(type(node))` under `driver_id(path, name)`, where
`name` is the name `coordinates_of(joint)` reports: the joint's own name
for a one-coordinate joint, `<joint>.<coordinate>` for a `Free`. A
site-declared joint is class metadata of the child's specialization
(joints spec, "A joint declared where a child is placed"), so the same
enumerator reports it. Plain ports and derived coordinates are NOT in the
bank: they are calculations over the state, recomputed by the ordinary
enumeration every tick (decision item 2; design.md "Runtime-owned
mechanical state"). An id claimed twice — a driver and a joint of one name
on one node — is refused at construction naming both. A root driver named
like a child's coordinate has the ambiguity `set_state` already refuses;
nothing new.

Every bank coordinate must hold a plain number after the rest render. A
joint coordinate the rest render leaves unbound is **refused at
construction**, naming the node path and the coordinate and saying that
the run owns every joint coordinate and needs a rest value for each —
bind it under a guard in `simulate()` or drive it. *Alternative:* omit
unbound coordinates from the bank, as the untimed solver tolerates them
(a `Free` whose machine binds four of six); rejected because it would
make "every joint coordinate" silently false and give the run a
coordinate with no history to keep. Recorded as an open question.

### 3. One `Sim`, and the engine in two new modules imported only for a running root

`Sim(node, dt, meshes=False, state=None, record=None)` stays the one
class and the one constructor `ScenarioTest.simulation()` builds. Its
constructor reads `declared_time(type(node))`; when the mode is
`'running'` it imports `solid_node.simulation.program` and
`solid_node.simulation.run` inside the constructor and builds a `Run`
that owns the bank, the program and the commands; every running-only
method (`move`, `rate`, `snapshot`, `restore`, `reset`, `commands`,
`program`, `initial`) delegates to it, and under an untimed or looping
root each of them is refused naming `Time.running()`. `sim.running` is a
boolean property. `state=` is accepted under every root: a mapping of
qualified driver ids to initial values bound over the declared defaults
(a coordinate id there is refused: initial coordinates come from the
rest pose).

Module layout, respecting ADR-056/ADR-087's one-way dependency and the
`cli-startup-cost` ceiling:

- `solid_node/motion/ports.py`: `RunBinder` (a marker class carrying a
  `described()` text; no imports), `Time.running()`, `Time.mode`.
- `solid_node/motion/couplings.py`: recognition of `RunBinder` in the
  places §5 lists. No new import.
- `solid_node/simulation/program.py`: `Program`, `compile_program`,
  `UnsupportedLaw`. Imports `solid_node.scad_expression`,
  `solid_node.expression_graph`, `solid_node.math` (for
  `SYMBOLIC_BUILTINS`) and the motion modules at module scope; imported
  by `Sim.__init__` only under a running root.
- `solid_node/simulation/run.py`: `Run`, `Command`, `RunSnapshot`,
  `RunConflict`. Imports `program.py` and the node/motion layers.
- `solid_node/simulation/sim.py`: the running branch; `instruction.py`:
  `by=`; `__init__.py` `_EXPORTS` gains `RunConflict` and
  `UnsupportedLaw` (lazy, as every export there is).

*Alternative:* a separate `Run` class the author constructs
(`Run(machine, dt)`) — rejected because the decision names
`Sim(machine, dt, state=...)` as the one path and `ScenarioTest` builds a
`Sim`; a `RunningSim` subclass chosen by a factory — rejected as a second
public name for one thing.

### 4. Initial state: the rest render, then the run takes the coordinates

Construction under a running root:

1. Validate `dt`; build the driver bank from `qualified_drivers` (which
   binds defaults and renders once, as today); apply `state=`.
2. `node.set_state(**drivers, time=0.0)` — the untimed rest render, one
   enumeration, author bindings and relations solved exactly as today.
3. Read every bank coordinate off the tree (`get_coordinate`), refusing
   an unbound one (§2); compile the program (§6) from the records the
   rest render solved.
4. Take the initial snapshot.
5. Bind the whole snapshot as the run: `node.set_state(**bank, time=0.0)`,
   whose DELIVERY walk binds every coordinate entry under
   `binding_as(run_binder)` and whose one ENUMERATION then runs with no
   run binder active — one more enumeration. From this moment the run
   owns the coordinates. The scoping is load-bearing: were the
   enumeration itself run under the run binder, every plain port an
   author's `simulate()` binds during it would be recorded as run-bound,
   exempt from the freshness clear, and stale from the second tick on —
   the Prusa i3 shape ADR-099 fixed. A plain port bound by the author
   keeps `binder = None`, is cleared and rebound every tick, and follows
   the run-bound coordinate it reads (the Pascaline module's
   `self.stop.angle = self.angle.value` idiom).

Step 5 is where an author's `simulate()` that binds a run-owned
coordinate UNCONDITIONALLY (`self.first.turn = self.crank * 2`) is
refused, at construction, naming the class and the coordinate: it is a
law written imperatively and belongs in a relation. The catalogue's
rest-default idiom, `if self.slide.travel.value is None: self.slide.travel = 4.0`,
survives untouched: it binds in step 2, where nothing is run-owned yet,
and never fires again because a run-owned slot is never `None`.

*Alternative:* skip step 5 and let the first tick's binding refuse —
rejected: a refusal that names the model's mistake belongs at
construction, and step 5 is also what makes `sim.state`, the node's
pose and the bank agree before the first tick.

### 5. The run is a binder kind the solver recognizes

`RunBinder` is the binder every run binds as; each `Run` holds one
instance (identity = the run). A slot is *run-bound* when its value is
not `None` and its `binder` is a `RunBinder`. The rules, each at the
place the context measured:

- **`ports.bind`**: when the sink is run-bound and the current binder
  (`_binder`) is not that run, the binding is refused — a `DoublyBound`
  imported inside the branch (couplings is necessarily loaded when a run
  exists) — naming the coordinate, the owning class (the phase's
  assembly when one is running, else the slot's node) and the run:
  "the running simulation owns `first.turn`; a `simulate()` that binds it
  states a law imperatively — write it as a relation". This is the one
  refusal the wiring rule already has the shape of (`ports.py:311-319`).
- **`ResolvedEnd.bound()`**: a run-bound slot is bound, checked before
  the `_enum_marker`/`_bound_by` reasoning.
- **`clear_solved`**: a run-bound slot is skipped, whatever its
  `_enum_marker`.
- **`_step_relation`**: a record whose driven ends are ALL run-bound is
  marked `direction = 'run'` and returns `False`, whatever its sources
  hold — it is the run's to solve. A record whose driven ends are NOT
  run-bound solves as today; if that would bind a run-bound SOURCE
  backward, `_refuse_double` fires as today, naming the run as the other
  binder. A driven group mixing run-bound and other ends is refused at
  compile (§6), so the solver never meets one.
- **`_step_wiring`**: a wiring whose target is run-bound is marked
  `applied` and returns `False` (the run holds parent and child
  consistent; the wiring is an identity edge of the program). A wiring
  whose target is a plain port applies as today from a run-bound source.
- **`_step_derived`**: unchanged. A formula whose terms are run-bound
  computes forward and binds its own slot as the formula; a formula a
  relation binds while its terms are run-bound is the over-determined
  shape the untimed solver already tolerates and the run checks (§7).
- **`_claim`** and `_refuse_double`: unchanged; `_describe_binder`
  describes a `RunBinder` as "the running simulation".
- **`refuse_reads`**: unchanged. A run-bound slot holds a value before
  any phase runs, so no unbound read of it is ever recorded; the rule
  treats the run as a binder by construction.

**`set_state` accepts a qualified joint-coordinate id under a running
root only.** In `_receive_state`, before the dotted split, an entry whose
remaining name is one `declared_ports(type(self))` reports as a JOINT
coordinate is this node's own and is bound with `set_coordinate` (so
`chassis.pose.roll` reaches `pose.roll` on `chassis`); its id is recorded
in `declared` beside the driver ids so the unknown/ambiguous checks
cover it; the delivery walk hands a LEAF child the entries addressed to it
and binds those naming its joint coordinates the same way. `saved`
records `(slot, value, binder)` for every coordinate slot bound so `_undo`
restores them with the `_states`. Under an untimed or looping root a
coordinate id is refused exactly as today, listing the declared driver
ids. *Alternative:* accept coordinate ids under every root as sugar for
`set_coordinate` — rejected because it changes an existing refusal for
every project and gives the untimed solver a third binder with no owner;
outside a run a coordinate has no history for a snapshot entry to carry.

### 6. The compiled program: laws applied to symbols, once

`compile_program(root, bank)` runs after the rest render and builds a
`Program` from what that render recorded on every node:
`node.__dict__['_relations']` (each `RelationRecord` with its `law`,
`driver_ends`, `driven_ends` and the `direction` the render solved it
in), the wirings `_wirings(assembly)` yields, and the derived coordinates
`_solved_formulas` yields.

**Nodes.** A bank coordinate; or an INTERMEDIATE — a plain port or a
derived coordinate whose binder after the rest render is a relation, a
wiring or its own formula and whose own sources are, transitively,
program nodes. Anything else is OPAQUE: a plain port bound by the
author's `simulate()` (binder `None`), or unbound.

**Edges.** For each relation record: the law is applied ONCE to
`symbol(id)` tokens for its source nodes (`scad_expression.symbol`);
the result — one graph, or a sequence of exactly m graphs for m driven
ends, checked as `_checked_return` checks a value — is stored with the
record's direction. A record solved BACKWARD stores the graph of
`law.inverse(symbol(driven))` instead. A wiring whose target is a bank
coordinate is an identity edge parent → child (joint coordinates declare
no scale). A derived coordinate is a linear edge — its coefficient map
and constant — in the direction the render resolved: forward when its
own slot's binder is the formula, backward into the one term whose
binder is the formula, or a CHECK when its slot and every term were bound
by others. Edges are ordered by Kahn's algorithm over their determined
ends; the graph is acyclic because the render's own propagation
produced it and refuses a doubly bound coordinate.

**What is left to the enumeration.** A relation or wiring whose driven
ends are all outside the bank and reach no bank coordinate through
intermediates (a pulley driving a belt's plain port) is not compiled; the
ordinary solver keeps computing it every tick from the run-bound
sources.

**Refusals at construction**, each `UnsupportedLaw` naming the relation
as written (`RelationRecord.described()`) and the class that stated it:

- a graph containing a `call` whose name is `floor`, `ceil` or `sign`,
  or a `binop` whose operator is `%`, `<`, `<=`, `>`, `>=`, `==` or
  `!=` — "contains a jump; jumps are not yet supported by the running
  mode" (the Curta window is this case until cycle 2);
- a law that raises when applied to a symbol (a `TypeError` from
  `math.sin`, a truth test on a symbolic value), or that returns a value
  that is neither a number nor an `OpenSCADConstant`, or whose graph
  holds a `raw` node or a `call` outside `SYMBOLIC_BUILTINS` — "cannot be
  applied to symbols; a running law is an expression over its sources";
- an edge into a bank coordinate whose source is OPAQUE — "sourced from
  `X.port`, which `X.simulate()` binds; the run integrates relations over
  drivers and joint coordinates, so state that port's value as a
  relation or a joint";
- a driven group mixing bank coordinates and other ends.

A law whose graph has no free name (a constant) has zero slope
everywhere; in this cycle its edge contributes zero and its driven end
holds. The refusal the decision asks for (item 5) needs jump detection
to tell a gate from a constant and is cycle 2's, as stated.

**Identity.** `Program.identity` is the SHA-256 of the canonical listing:
root class qualified name; every node id with its kind; every input with
`dtype` and `scale`; every edge with its kind, its ends, its direction and
the SCAD text of its graph (`scad_expression`) or its coefficients.

*Alternative for the direction:* decide propagation per tick by a
worklist from the inputs that moved — rejected because the direction of
every relation is already decided, by the rest render, from the same
facts (which coordinates are inputs), and a fixed program is what
cycle 4 exports and the browser worker executes.

### 7. The tick

With `B` the committed bank, `V(B)` the intermediate values computed from
it, and `k = tick + 1`:

1. `Δ[i]` for every input `i`: the movement its active command admits
   for tick `k`, `0` with no command. An input is always DETERMINED.
2. For every edge in program order: from the increments of its
   determined ends, compute the increment of the end it determines —
   forward, `Δ[d_j] = f_j(s + Δ[s]) − f_j(s)` over the start values;
   backward, `Δ[s] = f⁻¹(d + Δ[d]) − f⁻¹(d)`; identity for a wiring;
   the linear formula forward, or backward into its one term. A CHECK
   edge computes the increment its formula predicts and compares it with
   the increment its slot received.
3. A coordinate no edge determines HOLDS: `Δ = 0`.
4. Disagreement — `|a − b| > 1e-9 · max(1, |a|, |b|)` — is a
   `RunConflict` naming the formula, the binder that determined the
   coordinate, the coordinate and both increments. A joint coordinate
   whose new value leaves its declared range is a `JointRangeError`
   naming the joint, the value and the range (cycle 3 turns this into a
   stop).
5. On either refusal nothing has been committed: `B` and `tick` stand;
   every command that moved an input this tick is marked `refused`,
   keeps the travel it had admitted, and is retired; the error is raised.
6. Commit `B ← B + Δ`, `tick ← k`; advance every command; retire the
   completed.
7. Bind: `node.set_state(**B, time=k·dt)` — one delivery at rest, whose
   coordinate bindings alone run under `binding_as(run)`, then one
   enumeration with no run binder active (§4.5); the solver sees every
   bank coordinate run-bound (§5) and every author-bound plain port fresh.
8. Record into the ring when recording is on; fire `at(k)` actions; run
   due cadences.

Steps 2–4 run over increments only; nothing is bound until step 7, so a
failed tick touches no slot.

**An input is never back-driven.** A `Driver` is a source only (ADR-089),
so the rest render never orients an edge INTO a driver and the program
never determines one: an uncommanded input holds, whatever pushes the
coordinates behind it. A coordinate that is physically pushed from two
sides — the Pascaline column's wheel, turned by its own dial and by the
previous column's carry — is therefore ONE multi-source law,
`(dial & carry.turn).drives(column.turn, law=...)`, never two relations
(the untimed solver already refuses two binders). Under that law the
dial's driver is the operand the person turns and the column's joint
coordinate is where the wheel stands, which the carry advances without
the driver changing. Whether an input should instead EXPOSE a coordinate,
as the controls record of 2026-09-12 puts it, is an open question for
cycles 4 and 5, not this one. Only a check edge can disagree in this
cycle: a relation into a bank coordinate has one binder (the untimed
solver refuses two), so the reachable conflict is two inputs
prescribing one rigid group through a linear formula the rest render
could not check (the differential in the test project). The contract is
stated generally because cycle 3's stops widen it.

### 8. Commands: one owner per input, an outcome handle, retirement

`Command` is the handle `move` and `rate` return: `input`, `kind`
(`'move'`/`'rate'`), `status` (`'active'`, `'completed'`, `'blocked'`,
`'refused'`, `'cancelled'`), `requested` and `admitted` in the input's
DESIGN units (the units an instruction target is stated in; the bank
stays native), `started`, `ticks` (`None` for a rate), `remaining`, and
`cancel()`. `sim.commands` is the tuple of active handles.

- `move(input, by=None, to=None, duration=)`: exactly one of `by`/`to`;
  `duration` whole ticks (`_ticks`, ADR-083), `0` allowed. `to` is
  converted to a `by` from the committed value. `by` is converted through
  the driver's scale once (`Driver.native`). A negative `by`, a `to`
  below the committed value, or a negative `rate` is refused naming the
  input: reverse travel meets no stop until cycle 3.
- Per-tick admission is a pure function of the tick count from the
  command's start: a move reuses `RampProgram(start, start + native,
  ticks, dtype)` and admits `value_at(k) − value_at(k−1)`, integer-exact
  for an integer input; a rate admits `cumulative(k) − cumulative(k−1)`
  with `cumulative(k) = native_rate · dt · k`, floored for an integer
  input.
- Ownership: an input with an active move or rate refuses a second move
  or a rate naming the input and the owning command. `rate(input, 0)`
  completes the active rate (status `completed`) and is a no-op when
  none is active.
- A zero-duration move integrates at once, at the current tick, as one
  extra pass of §7 with `tick` unchanged — the rule ADR-083 states for a
  zero-duration instruction.
- Retirement: a command leaves the active table the tick it completes;
  the handle the caller holds keeps reporting. A hundred completed moves
  leave at most one active entry.
- `trigger(name)` under a running root claims every input the
  instruction names before starting any command, so an ownership
  conflict refuses the whole instruction. Under an untimed or looping
  root `trigger` ramps drivers exactly as today.

*Alternative:* return a `refused` handle from a request that fails
validation — rejected: every other refusal in the framework raises by
name, and a handle that was never active has nothing to report.
`refused` is the status of a command whose tick failed (§7.5).

### 9. `Instruction(by=)`

`Instruction(targets=None, duration=None, *, by=None)`: exactly one of
`targets`/`by`, both mappings of class-local driver names to design
units; `duration` as today. `instruction.by` and `instruction.targets`
read back the one given (the other is `None`). Under an untimed or
looping root a `by=` instruction ramps each driver from its current
value by the converted delta through the same `RampProgram` and the
same last-wins rule a `targets=` ramp uses. Under a running root
`targets=` maps to `move(to=)` and `by=` to `move(by=)`. The serializer
does NOT publish a relative instruction in this cycle: the shipped
viewer's button reads `targets` off every entry of the instructions table
and would fail on one without them, so a `by=` instruction is omitted
from the table until cycle 4 publishes the compiled program under a new
schema version, and a root whose instructions are all relative publishes
an empty table. The document is therefore unchanged by this cycle.

*Alternative:* refuse `by=` outside a running root — rejected: a relative
ramp is well-defined over a driver bank and refusing it would make one
declaration legal under one time base only.

### 10. Snapshot, restore, reset

`RunSnapshot` is a frozen value object: `program` (the identity string),
`dt`, `tick`, `bank` (a tuple of `(id, value)` in id order) and
`commands` (a tuple of frozen records: input, kind, parameters, start
tick, admitted, status). Two snapshots of one state compare equal.
`restore` compares `program` and `dt` FIRST and refuses a mismatch
naming both, touching nothing; then replaces the bank, the tick and the
command table (fresh handles reachable through `sim.commands`; handles
issued before the restore are marked `cancelled` with what they had
admitted), clears the recording, and binds the restored bank (§7.7).
`sim.initial` is the snapshot of §4.4; `reset()` is `restore(initial)`.
`sim.time` stays `tick * dt`.

### 11. Recording

`Sim(..., record=None)`: `None` keeps nothing and `sim.trajectory` reads
`[]`; an integer `N ≥ 1` keeps a ring of the most recent `N`
`(tick, bank)` entries, read back oldest first; anything else is
refused. Under an untimed or looping root `record` is ignored and
`trajectory` appends every tick as today. Restore and reset clear the
ring. Unbounded recording is not offered under a running root; a caller
wanting more uses `every()`.

### 12. What stays untouched

The untimed and looping paths of `Sim`, `DriverState`, `RampProgram`,
`ScenarioTest`; `Time(loop=)` and every consumer of `loop`; the solver
for every slot that is not run-bound; the sweep, the phase stack, the
whole-tree fixpoint, the read-refusal rule; `render()`/`simulate()`
purity; the document schema and the viewer; joints, ranges (outside the
run's own pre-check), broadcasts, groups; the projects.

### 13. Decisions that become ADRs after implementation

1. **A third time base: `Time.running()`** — elapsed seconds, never
   wrapping, mechanics that retain state; reads as an undeclared root
   until the program is published.
2. **The run owns the coordinates and binds them** — the bank of drivers
   and joint coordinates by qualified id, initialized from the rest pose,
   bound by the run through `set_state`'s delivery and never through an
   enumeration, recognized by the solver as one binder; one owner per
   input and retirement of commands; an input is never back-driven, so a
   coordinate pushed from two sides is one multi-source law.
3. **One law, two readings** — untimed and looping a relation sets
   `f(driver)`; running it contributes `f(end) − f(start)` over a tick,
   in the direction the rest render solved it, exact across kinks; a law
   is inspected as the expression it builds over symbols, and what the
   expression cannot say (a jump, opaque Python) is refused by identity.

## Risks / Trade-offs

- [Two extra enumerations at construction and one `set_state` per tick,
  each a full delivery walk and enumeration] → the cost is what every
  tick already paid for drivers; measured per tick in the evidence, and
  the ring keeps memory flat. Cycle 4's evaluator is where speed lives.
- [`GraphValue.evaluate` builds a dict per evaluation and walks the
  graph twice per edge per tick] → acceptable for the module's three
  columns; recorded as the known cost, with the spike's 500-coordinate
  budget as the target for cycle 4.
- [A run-bound slot survives `clear_solved`, so a coordinate the run
  stops owning (after `Sim` is discarded) keeps its last value] → exactly
  what a hand binding outside a phase does today; a later `set_state` or
  construction rebinds it.
- [The unbound-coordinate refusal (§2) bites a `Free` whose machine binds
  four of six] → the fix is one guarded line per unused coordinate;
  raised as an open question rather than silently omitted.
- [Bare `$t` for unbound time under a running root previews a model
  as if time ran 0..1 s] → the preview is what an undeclared root shows;
  cycle 4 replaces it. No producer change is needed later beyond
  reading the program.
- [Conflicts are reachable only through linear formulas in this cycle]
  → the contract and its test are stated for the general case so
  cycle 3's stops do not reopen it.
- [`bind` importing `DoublyBound` inside a branch] → runs only when a
  run binding exists, which implies couplings is loaded; a module-scope
  import would close the cycle ADR-089 keeps open.
- [Reverse moves refused] → the Pascaline module's forward-only dials
  need none until cycle 3; a jog that reverses is refused loudly, not
  ignored.

## Migration Plan

Additive. No project changes: a root that does not declare
`Time.running()` sees no new behaviour, and `Instruction(targets=...)`
keeps its positional form. The Curta bench and the Pascaline module opt
in by declaring the base, in their own repositories, after cycle 2 lands
the `floor` their windows use. Rollback is removing the declaration.

## Open Questions

- Should an input be able to EXPOSE a joint coordinate, so that a wheel
  advanced by a carry reads as the input's position (the controls record
  of 2026-09-12), instead of a `Driver` being the input? Cycles 4 and 5.

- Should a joint coordinate the rest render leaves unbound be omitted
  from the bank instead of refused (§2)? The proposal refuses.
- Should `by=` be accepted under an untimed root (§9)? The proposal
  accepts it as a relative ramp.
- Should an unbound `time` read under a running root be refused instead
  of previewing as `$t` (§1)? Deferred to cycle 4 with the export.
- Whether `blocked` (cycle 3) reports per command or per rigid group is
  cycle 3's to decide; the vocabulary is fixed here.
