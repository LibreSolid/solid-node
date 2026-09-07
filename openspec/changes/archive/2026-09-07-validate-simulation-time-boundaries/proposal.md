## Why

Due-diligence finding F11 reproduced `Sim(node, dt=-0.1).run(1)` returning
normally at tick zero while every scheduled check remained stranded. The
fixed-step loop validates tick alignment but not the domain or finiteness of
its time inputs, and an action scheduled before the current tick can likewise
never run. The saved evidence also exposes a related valid boundary: a
zero-duration instruction creates a ramp that is complete at its start tick,
but the simulation does not make that target observable at that tick.

## What Changes

- Require simulation `dt` to be a finite real number strictly greater than
  zero before binding any state.
- Require every instant, cadence period, run duration, and instruction
  duration to be finite real seconds as well as satisfying its existing tick
  alignment and sign rules.
- Reject a negative run duration before firing actions or changing state.
- Reject `at(t)` when its absolute tick is before the simulation's current
  tick; allow the current tick, which fires at the beginning of the next
  `run()`, including `run(0)`.
- Keep instruction durations nonnegative and make a zero-duration instruction
  reach and bind its targets immediately at the trigger's current tick.
- Add API-boundary and side-effect regressions plus update the saved probe to
  record the expected refusals and immediate zero-duration state.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `simulation`: define the numeric domain, direction, and zero-duration
  semantics of the fixed-step clock.

## Impact

- `solid_node/simulation/`: centralize finite-real seconds validation, guard
  `Sim` construction and scheduling/running boundaries, and settle zero-tick
  driver ramps immediately.
- Simulation tests: cover zero/negative/non-finite/non-numeric `dt`, invalid
  instants/periods/durations, past scheduling, lack of mutation on refusal,
  and zero-duration instructions triggered directly and through `at()`.
- `workflow/archive/due-dilligence-2026-09-07/probe_additional.py`: the
  negative-`dt` observation becomes an expected construction refusal and the
  zero-duration observation
  becomes immediate target state in both the bank and node.
- Baseline simulation specification, architecture records, changelog, and
  due-diligence records will state the boundary. ADR disposition will be
  assessed after implementation evidence.
- No tick tolerance, trajectory format, cadence accounting, driver units,
  viewer behavior, or positive-duration ramp arithmetic changes.
