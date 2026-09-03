## Why

The declarative node API (archived changes `declarative-node-api` and
`declarative-node-api-fixes`) left one job to the author that the
framework should own: telling a rest placement from a motion. An internal
node's `render()` runs on every re-render, and the animator sweep drops and
re-applies everything it did, so a part that never moves — a bearing cap on
its saddle, the shell a hand turns inside — is restated every frame and its
operation objects churn. The fixes cycle documented a workaround: place
stationary parts once in `__init__` after `super().__init__(**kwargs)`.

Migrating three projects (v8-engine, Metamaquina2, Inmoov-sim, branch
`declarative-api`) proved the workaround wrong in kind, not just in
ergonomics. An operation applied in `__init__` sits innermost on the part's
chain, so a once-only turn that must compose *outside* a driven rotation —
the forearm's presentation turn over the wrist rotation, the engine's static
translations after a time-driven rotation — could not be hoisted and had to
stay in `render()`. The pilot's assessment (2026-09-03): the split between
"built once" and "moved per instant" is a lifecycle fact, and the lifecycle
should say it.

The reference's rename of `render()` to `shape()`/`assemble()` is dropped
for good: "render" also means *to make*, and it names the building of the
initial state on a leaf and on an internal node alike.

## What Changes

- **`render()` builds the machine at rest.** On every node kind `render()`
  is the one build step: geometry on a leaf; structure, `omit()` and rest
  placement on an internal node. It reads no driver, no time, no port. On an
  assembly whose first run read none, the framework runs it once per
  instance and keeps its children and operations.
- **`simulate()` moves it.** A new `AssemblyNode.simulate()` hook, a no-op
  in the base, is run by the framework after `render()` under whatever
  binding is current: symbolic `$t` in the build and viewer path, plain
  numbers under `set_state`, `set_keyframe`, the test runner, the snapshot
  tool and the simulator. It is where drivers and time are read and ports
  are bound, and every operation it applies is swept before its next run.
- **Motion composes innermost.** An operation applied during `simulate()`
  goes at the head of the node's operation chain, before any placement
  `render()` or `__init__` applied, so a part spins about its own axis and
  is then carried by its rest placement. Two assemblies simulating one node
  keep their operations apart as they do today.
- **Nothing raises for a current model.** An assembly whose `render()`
  reads a driver, `time` or a port keeps today's behaviour exactly — the
  render re-runs per binding, its operations are tagged and swept — and the
  framework emits one `FutureWarning` per class naming the read and the
  new home. Placement in `__init__` keeps working.
- **Structure stays out of `simulate()`.** `omit()` during `simulate()`
  raises `StructureError`.
- **Leaves are unchanged.** Simulation is exclusive to assemblies; a leaf,
  rigid or flexible, renders from its parameters and its bound ports.
- Documentation, changelog, history and one ADR record the lifecycle;
  the fixes cycle's `__init__` recommendation is withdrawn.

## Capabilities

### New Capabilities

_none_

### Modified Capabilities

- `kinematics`: the animator sweep applies to `simulate()` operations
  (and to a legacy render that reads a driver); new requirement for the
  rest render and per-instant simulate, innermost motion composition, the
  once-per-instance render, the symbolic path, and the deprecation warning.
- `node-model`: the template-method lifecycle gains the `simulate()` step
  on assemblies.
- `ports`: causal port binding happens per `simulate()`; binding in
  `render()` is the deprecated form.
- `declarative-nodes`: `omit()` is refused during `simulate()`.
- `user-documentation`: the declaring page documents the split and stops
  recommending `__init__` placement; the animation and driving pages read
  drivers in `simulate()`.

## Impact

- `solid_node/node/base.py` (phase stack, operation placement, `omit()`),
  `solid_node/node/assembly.py` (the wrapper: sweep, once-only render,
  `simulate()`), `solid_node/node/qualified.py`, `solid_node/node/ports.py`
  (read detection), no change to any tree walker, the serializer, the
  viewer, or the test runner.
- Every existing project keeps working with a warning; the three
  `declarative-api` project branches migrate in a follow-up round.
- Originating evidence: the round-two migration findings on
  `projects/Inmoov-sim` (forearm presentation turn) and `projects/v8-engine`
  (static translations after a driven rotation), and the pilot's
  2026-09-03 assessment.
