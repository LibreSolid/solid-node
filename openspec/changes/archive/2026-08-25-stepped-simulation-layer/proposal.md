# Proposal: stepped-simulation-layer

## Why

Stage 1 (`2026-08-25-multi-driver-state-seam`, archived) gave the node
layer multi-driver state binding and ports, but nothing produces those
snapshots: a project cannot yet declare its drivers, trigger an
instruction, or run a deterministic simulated time slice. ADR-056
stage 2 is that layer, and the spike (`spike/FINDINGS.md`) already
validated its exact mechanics — this change productionizes the
spike-proven harness as `solid_node/simulation/`, honoring the
spike's seams: declaration separated from state, deferred scenario
actions, and instruction targets in design units.

## What Changes

- New package `solid_node/simulation/` providing:
  - `Driver` — a stateless class-attribute declaration on assemblies
    (default, range, unit, optional integer dtype, optional linear
    scale in design units per native unit), discoverable off the class
    without instantiation, mirroring the ports pattern.
  - Per-simulation driver state owned by the `Sim`, never shared
    across node instances; integer-typed state for discrete devices.
  - `Program` protocol plus `RampProgram`: distributes a delta over n
    ticks; integer-exact (`start + delta*k//n`) for integer drivers,
    landing exactly on target.
  - `Instruction` — named driver targets in design units plus a
    duration; targets convert to native driver state through the
    driver's declared scale at trigger time.
  - `Sim` — the fixed-`dt` stepping loop: instants as integer tick
    counts (whole-tick validated), events at ticks, deferred `at(t)`
    actions (`.trigger(name)`, `.run(fn)`), cadence `every(period,
    fn, *args)` with per-slot cost accounting, per-tick snapshot
    binding via `set_state`, trajectory recording, and initial
    binding of every declared driver's default (resolving stage 1's
    loud-unbound behavior for simulation contexts).
  - `ScenarioTest` — a `solid_node.test.TestCase` base for scenario
    methods: builds the node once, constructs a fresh `Sim` per
    scenario, runs under plain pytest and under the `solid test`
    runner unchanged.
- Migrate the spike caller: `spike/axis/` drops its local harness
  (`steplab.py`) in favor of `solid_node.simulation`, and
  `spike/axis/scenario.py` must revalidate all five recorded verdicts
  against the shipped package.
- Excluded (later stages per ADR-056): viewer/document schema and
  driver-table serialization, named-variable symbolic expressions,
  G-code interpreter, flow variables, equation solving, and any
  `manager/` CLI integration.

## Capabilities

### New Capabilities
- `simulation`: driver declarations and per-simulation state,
  programs, instructions with design-unit targets, the deterministic
  fixed-dt stepping loop, and scenario testing.

### Modified Capabilities

(none — stage 1's `kinematics` and `ports` baselines are consumed
as-is; `test-framework` requirements are unchanged because
`ScenarioTest` is specified in `simulation` and only builds on the
existing public `TestCase` surface)

## Impact

- Code: new `solid_node/simulation/{__init__,driver,instruction,sim,
  scenario}.py`; no changes to `solid_node/node/` or `solid_node/
  test.py`; `solid_node/node/` continues to not import `simulation`.
- Specs: new `simulation` spec.
- Tests: new red-first tests plus a minimal axis fixture project under
  `tests/`; spike migration as caller validation.
- Existing suites must stay green untouched: framework 775, v8-engine
  33 (which uses no simulation surface).
- No dependency, CLI, or viewer changes.
