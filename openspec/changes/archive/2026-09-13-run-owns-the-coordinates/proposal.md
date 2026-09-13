## Why

A pose today is a function of the current input values and nothing else.
Two originating projects under `projects/Calculators/` show what that
loses:

- **The Curta `InputMesh` bench**
  (`Curta-Type-I-3x/simulation/input_mesh.py`). One selectable drum row
  drives its transmission pinion through the project's own law,
  `4 + 72 * clamp01((angle - 113.5) / 11.25)`: the pinion turns 72° while
  the tooth is engaged and holds outside the window. Posed at any crank
  angle the model is right. Turned through two crank revolutions it is
  wrong: the pinion stands at 76 after the first turn and at 76 after
  the second, because the law can only say where the pinion IS for a
  crank angle, never where it WAS. The pilot's illustration of the fix
  is that same file, two edits away — `time = Time.running()` on the
  root and the tooth window made periodic — leaving the pinion at 76
  after one turn and 148 after two.
- **The Pascaline module** (`Pascaline-module/`, the first project the
  running feature is developed against by pilot direction). Its
  acceptance record (`docs/open-run-acceptance.md`) requires that
  "repeated commands must accumulate without register re-entry" and that
  no arithmetic result may generate a wheel pose: a dial turned again
  must move on from where its wheel stood, which is history the absolute
  reading of a relation cannot carry.

The lost-history finding is recorded in
`workflow/open-run-simulation/design.md` ("The original empirical
limitation was loss of mechanical history when every pose was reduced to
a function of the current input values"), and the spike campaign under
`workflow/open-run-simulation/spikes/` proved a stateful, integer-tick
engine with checkpoints and bounded memory viable
(`evidence/report.md`) — while also finding that declaring events and
memory per law was the wrong authoring interface. The pilot's decision of
2026-09-13 ("a law is integrated, not declared") fixes the interface and
gives the go-ahead. This change is cycle 1 of the five that decision
splits the work into: **the run owns the coordinates**. Its value is the
interface; jumps (cycle 2), stops (cycle 3), export (cycle 4) and the
viewer (cycle 5) stack on it.

## What Changes

- **A third time base.** `time = Time.running()` on a root assembly
  declares elapsed simulation seconds that never wrap and mechanics that
  retain state. It is refused below the root and on a non-assembly by the
  rule `Time(loop=)` already obeys; `declared_time(cls).mode` reports
  `'running'` or `'loop'`. Untimed roots and `Time(loop=)` are untouched.
- **The run owns the coordinates.** Under a running root, `Sim` owns a
  bank of every driver AND every joint coordinate of the linked tree, by
  the same qualified ids `qualified_drivers` and `declared_ports`
  produce (`path.joint`, or `path.joint.coordinate` for a joint owning
  several). `sim.state` returns all of them. There is no memory bank and
  the author declares no state.
- **Initial state is the untimed rest pose.** `Sim(node, dt, state=...)`
  binds the requested driver values, renders once through the existing
  enumeration, and reads every joint coordinate off the tree as the
  initial bank — admissible by construction. A joint coordinate the
  rest render leaves unbound is refused by name.
- **One law, two readings.** Untimed and looping, a relation still sets
  the driven coordinate to `f(driver)`. Running, over one tick a
  CONTINUOUS law contributes exactly `f(end) - f(start)` to the driven
  coordinate, from where it stood — exact across the kinks of `abs`,
  `min`, `max` and the compositions built on them (`clamp`, `clamp01`,
  `ramp`, `piecewise`). Increments propagate over the relation graph in
  the direction the rest render solved each relation — forward through a
  law, backward through an invertible one — a coordinate no increment
  reaches holds, and two increments that disagree on one coordinate are
  a conflict refused by name with the tick rolled back.
- **A law is inspected as an expression.** At `Sim` construction each
  relation's law is applied once to symbolic tokens for its sources; the
  resulting expression graph over coordinate ids is what the run
  evaluates. A running root whose relation graphs contain a
  DISCONTINUOUS primitive (`floor`, `ceil`, `sign`, `%`, a comparison) is
  refused by relation identity saying jumps are not yet supported; a law
  that cannot be applied to symbols is refused by identity too.
- **The run is a binder the solver leaves alone.** Every bank coordinate
  is bound by the run through `set_state`, so `render()`/`simulate()`
  stay pure over the snapshot and an inspection, an extra render or an
  extra `set_state` of the same snapshot advances nothing. The solver
  recognizes a run binding: `clear_solved` leaves run-bound slots alone,
  a relation whose driven ends are run-bound is marked solved by the run
  rather than refused, and the read-refusal rule treats a run binding as
  a binding. An author's `simulate()` binding of a run-owned coordinate
  is refused as doubly bound, naming the class and the coordinate.
- **`set_state` accepts qualified joint-coordinate ids under a running
  root**, delivered to the owning node — a leaf included — through the
  one binding path `set_coordinate` already is. Under any other root such
  an entry is refused exactly as today.
- **Commands, one path and one ownership rule.** `sim.move(input, by=,
  duration=)`, `sim.move(input, to=, duration=)`, `sim.rate(input, rate)`
  (input units per simulated second, `0` releases) and
  `sim.trigger(name)`. Only a declared input (a `Driver`) can be moved;
  one owner per input at a time. A move or rate returns a handle
  reporting `active`, `completed`, `blocked`, `refused` or `cancelled`
  and the travel actually admitted (`blocked` cannot occur before
  cycle 3; the vocabulary is fixed now). Completed commands are retired.
  A reverse move — negative travel or negative rate — is refused in this
  cycle.
- **`Instruction(by=..., duration=)`** is new and relative.
  `Instruction(targets=..., duration=)` keeps its absolute ramp contract
  in untimed and looping documents; under a running root a `targets=`
  instruction maps onto `move(to=)`. Exactly one of `by`/`targets` per
  instruction.
- **Snapshot, restore, reset.** `sim.snapshot()` is a value object (the
  bank, tick, `dt`, active commands, the compiled program's identity);
  `sim.restore(snapshot)` refuses a snapshot whose program identity or
  `dt` differs, before touching live state; `sim.reset()` restores the
  initial snapshot. `sim.time` stays `tick * dt`.
- **Recording is explicit and bounded** under a running root: an option
  at construction keeps a ring of the most recent ticks, or nothing.
- **Module layout.** The running engine and the compile step live in new
  modules of `solid_node.simulation` imported only when a running root is
  simulated; a model that declares no running time imports nothing new.

What does NOT change: untimed models and `Time(loop=)`, and every
existing `Sim`, `Instruction(targets=)`, `ScenarioTest`, driver, port,
joint and coupling test; `Sim.trajectory` under an untimed or looping
root; the solver for coordinates the run does not own (plain ports,
derived coordinates); the render/simulate purity contract; the document schema (a running root publishes exactly what an
undeclared root publishes, and a relative instruction is omitted from
the instructions table until cycle 4 publishes the program); no `Running` object, no memory
declaration, no `running(r)` law protocol. Jumps, stops, export and the
viewer are the later cycles and are named as such where this change
refuses what they will accept.

## Capabilities

### New Capabilities

None. Running simulation is a mode of the existing `simulation`
capability over the existing motion capabilities.

### Modified Capabilities

- `simulation`: `Sim` construction under a running root (`state=`,
  `record=`, the coordinate bank, the compiled program); integration of
  continuous laws per tick with propagation, hold and conflict; commands
  with one owner per input and an outcome handle; `Instruction(by=)`;
  snapshot, restore and reset; bounded recording; the refusals of this
  cycle (discontinuous primitives, non-symbolic laws, reverse moves,
  unbound joint coordinates, author bindings of run-owned coordinates).
- `kinematics`: the "Declared time base" requirement gains the third
  base `Time.running()` and what `self.time` reads under it; the
  "Multi-driver state binding" requirement admits a qualified
  joint-coordinate id under a running root.
- `couplings`: the run as a binder kind the solver recognizes — left
  alone by the freshness clear, a relation whose driven ends are
  run-bound solved by the run, a wiring whose target is run-bound solved
  by the run, and the doubly-bound refusal naming the run.
- `ports`: `Time.running()` and `mode` on the time-base declaration, the
  run-binder marker exported from `solid_node.motion.ports`, and the rule
  that a run-owned coordinate has one binder.
- `cli-startup-cost`: the running engine costs nothing to a model that
  declares no running time.

## Impact

- `solid_node/motion/ports.py`: `Time.running()`, `Time.mode`,
  `Time.loop` may be `None`; `RunBinder`; `bind` refuses a binding of a
  run-owned slot by anything but its run.
- `solid_node/motion/couplings.py`: run-binder recognition in
  `ResolvedEnd.bound`, `clear_solved`, `_step_relation`, `_step_wiring`,
  `_claim`, `_describe_binder`.
- `solid_node/node/assembly.py`: `read_time` under a running root;
  `set_state`/`_receive_state`/`_undo` deliver qualified joint-coordinate
  entries to their owning node under a running root.
- `solid_node/core/serializer.py`, `solid_node/manager/snapshot.py`: a
  `Time` whose `loop` is `None` publishes no `loop` and keyframes the
  fraction as an undeclared root does; the instructions table omits a
  relative instruction until cycle 4.
- `solid_node/simulation/sim.py`: the running branch of `Sim`;
  `instruction.py`: `by=`; new `program.py` (compile) and `run.py`
  (engine, commands, snapshot); `__init__.py` exports.
- Tests: `tests/running_project/` (the tiny machine), a new
  `tests/test_running_simulation.py`, additions to `tests/test_time_base.py`
  and `tests/test_couplings.py`, an import-cost case beside
  `tests/test_motion_package.py`; every existing suite unchanged.
- Docs: `docs/animation.rst` (the third base), `docs/driving.rst` and
  `docs/scenarios.rst` (commands, `by=`, snapshot), `docs/api-reference.rst`,
  `docs/changelog.rst`.
- Projects: none edited here. The Curta bench and the Pascaline module
  migrate in their own repositories after cycles 1 and 2 (the Curta
  window needs `floor`).
