## Why

Cycle 1 gave the run the coordinates and integrated every CONTINUOUS
law exactly. It stopped at the door of the two laws the campaign
exists for, refusing at construction any relation whose expression
contains `floor`, `ceil`, `sign`, `%` or a comparison and saying that
jumps are the next cycle's. This is that cycle.

The two originating laws are both periodic, and both are refused today:

- **The Curta `InputMesh` bench**
  (`projects/Calculators/Curta-Type-I-3x/simulation/input_mesh.py`).
  The pilot's illustration of the whole feature is that file two edits
  from its committed form: `time = Time.running()` on the root, and the
  tooth window made periodic —
  `4 + 72 * clamp01((angle - 360 * floor(angle / 360) - 113.5) / 11.25)`.
  The pinion must stand at `4` at the crank's rest, at `76` after one
  crank turn and at `148` after two. Under cycle 1 that root cannot be
  constructed at all; under the absolute reading it reads `76` after
  both turns. The fixture `tests/running_project/machine.py::Stepped`
  already carries the law, and its test asserts the refusal.
- **The Pascaline module's carry**
  (`projects/Calculators/Pascaline-module/.../simulation/carry.py`,
  `handed_on`), the acceptance project of this campaign by pilot
  direction. `floor` counts the carry windows the driving column has
  already passed and six `clamp01` segments shape the one in progress;
  the column is stated as one multi-source law,
  `(tens_entry & units.wheel).drives(tens.wheel, law=carried_column)`.
  After this cycle that law must compile and integrate under
  `Time.running()` UNCHANGED.

The authority is the pilot's decision of 2026-09-13 in
`workflow/open-run-simulation/design.md`, "a law is integrated, not
declared", items 3, 4 and 5: over one tick a law contributes the
CONTINUOUS part of its change; a law whose graph contains a
discontinuous primitive has the crossings of its jump surfaces located
inside the tick and the jumps SUBTRACTED; a jump never moves a part; a
law whose slope is zero everywhere, moving nothing except by jumps, is
refused as arithmetic. The cycle split is `roadmap.md`, "Execution,
2026-09-13": this is cycle 2, it depends on cycle 1 only, and stops
(cycle 3) and export (cycle 4) come after.

## What Changes

- **The refusal is lifted.** A relation whose expression contains
  `floor`, `ceil`, `sign`, `%` or a comparison compiles. `wrap()` is
  built on `ceil` and `piecewise()` on `clamp01`, so a `wrap`-based law
  compiles through the same door and a `piecewise` one never needed it.
- **A tick is cut into segments at its crossings, and the law is
  integrated over each.** The tick moves a law's sources along the
  straight line from their start values to their end values,
  parametrised by `t` in `[0, 1]`. Every value of `t` at which a jump
  node's argument reaches one of its surfaces cuts the path. On each
  open segment every jump node holds one BRANCH — an integer for
  `floor`/`ceil`, `-1`/`0`/`+1` for `sign`, `0`/`1` for a comparison,
  a fixed integer quotient for `%` — and the law with those branches
  substituted is CONTINUOUS on the closed segment. The increment is
  the sum over segments of that continuous law's change, which is the
  decision's `Σ [f(t_{i+1}⁻) − f(t_i⁺)]` computed exactly rather than
  by an epsilon offset. A jump never moves a part.
- **Every crossing inside the tick is found, not only the endpoints'
  difference.** A crank turned fast enough to pass three tooth windows
  in one tick adds three throws. A jump node whose argument is affine
  along the path — which is every law in the two originating projects —
  has its crossings SOLVED, exactly and all of them; any other
  argument is bracketed by subdivision and bisected to a stated
  tolerance. A NESTED jump (a jump node whose argument contains
  another) is handled by taking the jump nodes in postorder, so the
  inner crossings already cut the path before the outer argument is
  asked where it crosses.
- **A law that moves only by jumping is refused**, by relation identity
  at construction, as decision item 5 states: the graph with every jump
  node's subtree replaced by a constant has no free coordinate left.
  `floor(turns)` alone is refused; `9 * enabled + floor(turns)` is not,
  because `enabled` still carries slope.
- **A jumping law must drive a coordinate the run OWNS**, and one whose
  driven ends are all intermediates — a plain port, a derived
  coordinate — is refused by relation identity too. A subtracted jump
  implies a history, and an intermediate keeps none: cycle 1 recomputes
  it absolutely from the bank on every tick, so its value would snap
  while the joint behind it moved smoothly. The message says to state
  the relation into the joint coordinate and let the port follow it.
  This is the Pascaline module's own shape — its `wheel` is a
  `RotationalPort` wired to `drum.turn` — so it names what that
  module's running migration has to do.
- **Crossings are recorded, bounded.** Under a running root with
  `record=N`, `sim.crossings` reads a ring of the most recent `N`
  crossings, each `(tick, relation, coordinate, primitive, level, t)`.
  With `record=None` nothing is kept and nothing is built.
- **A tick that would cross more than a thousand surfaces in one law is
  refused** naming the relation, the primitive and the count, and
  commits nothing: a `dt` that coarse is not resolving the mechanism.

What does NOT change: everything cycle 1 settled. Untimed and looping
documents and `Time(loop=)`; the bank, the compile step's node
classification, edge ordering and program identity; propagation, hold,
conflict, rollback; commands, ownership, `Instruction(by=)`, snapshot,
restore, reset, the trajectory ring; the document schema; the
render/simulate purity contract. Propagation in particular is
untouched: with one determiner per coordinate a zero increment and no
increment are the same thing, so DISENGAGEMENT needs no switch — it
lives inside a law, as a gate factor in a multi-source law
(`-2 * shaft * (sleeve > 0.5)`) or as the zero-slope region of a
single-source one (the Curta window outside its ramp). No stops (a
joint range still fails the tick; cycle 3), no export, no memory, no
declared events, no `Running` object, no new symbolic primitive and no
change to what a document publishes.

## Capabilities

### New Capabilities

None. Jumps are a mode of the existing `simulation` capability over the
existing motion capabilities.

### Modified Capabilities

- `simulation`: the compile requirement loses the discontinuous-primitive
  refusal and gains the jump plan it builds instead; a new requirement
  states how a crossing is located inside the tick and subtracted, with
  repeated, nested and multi-source crossings, the branch evaluation,
  the tolerances and the bounded crossing record; a new requirement
  states the refusal of a law that moves only by jumping; the
  continuous-integration requirement gains one sentence naming where a
  discontinuous law is answered.

## Impact

- `solid_node/simulation/program.py`: `_JUMP_CALLS` and
  `_JUMP_OPERATORS` become the RECOGNIZED set rather than the refused
  one; `_graph_of` stops refusing them and returns a `GraphValue`
  beside a `JumpPlan` when the graph holds one; `_relation_edge` gains
  the refusal of a jumping law whose driven ends are all
  intermediates; new `JumpPlan` —
  the jump nodes in postorder, the branch-parameterized skeleton, each
  node's branch-parameterized argument graph, its affine classification
  and its surface family; new `_skeleton`, `_argument_graph`,
  `_affine_in_sources`, `_only_jumps`; `UnsupportedLaw` gains the
  only-jumps message and a new `TooManyCrossings` is raised per tick;
  `Edge.increments` takes the branch path when a graph has a plan and
  appends to a crossing list when one is given.
- `solid_node/simulation/run.py`: a second bounded ring for crossings,
  `Run.crossings`, cleared by `restore`/`reset` as the trajectory ring
  is; the tick's edge loop catches `TooManyCrossings`, refuses the tick
  and retires the commands that moved, exactly as `RunConflict` does.
- `solid_node/simulation/sim.py`: `sim.crossings` delegating to the run
  and refused under an untimed or looping root as the other running-only
  properties are.
- `solid_node/simulation/__init__.py`: `TooManyCrossings` exported
  lazily beside `UnsupportedLaw` and `RunConflict`.
- Tests: `tests/running_project/machine.py` gains the jump fixtures
  (the periodic window already there stops being a refusal fixture, and
  `SteppedBody` stays as the untimed control); a new
  `tests/test_running_jumps.py`; the three jump cases of
  `tests/test_running_simulation.py` change from refusal to behaviour;
  every other suite unchanged.
- Docs: `docs/scenarios.rst` ("Running a machine that keeps its
  history" — the jump bullet leaves "What this release refuses" and a
  new subsection states the integrated reading of a jump, with the
  Curta window), `docs/api-reference.rst`, `docs/changelog.rst`,
  `docs/architecture.md` (the Simulation section's running paragraph).
- Projects: none edited here. The Curta bench and the Pascaline module
  migrate in their own repositories, which this cycle unblocks.
