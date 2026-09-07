# ADR-083: Simulation time is finite, forward, and tick-aligned

**Status:** Accepted
**Date:** 2026-09-07
**Change:** `validate-simulation-time-boundaries`
**Extends:**
- [ADR-056: Signals, drivers, ports, and stepped simulation](ADR-056-signals-drivers-ports-and-stepped-simulation.md)

## Context and Problem Statement

The fixed-step simulation described by ADR-056 converted seconds to integer
ticks and rejected values that did not align with `dt`, but it did not define
the numeric domain or direction of time. A negative `dt` turned a positive run
duration into a negative tick count. The run then fired current actions,
skipped every step, and returned normally while future checks remained
stranded. NaN, infinity, booleans, and text failed later and inconsistently.

The same missing boundary affected absolute scheduling. An action registered
for a tick the simulation had already passed could never fire. At the other
edge, a zero-duration instruction created a mathematically complete ramp but
left the driver bank and bound node at different values until a later step.

## Decision Drivers

- A scenario must not appear to pass because invalid time prevents checks.
- Invalid inputs must fail before firing actions, binding state, or advancing
  accounting.
- Integer ticks and the existing alignment tolerance remain the deterministic
  representation of simulation time.
- Absolute scheduling must distinguish a past tick from the current tick.
- A zero-duration instruction must consume no time and still have observable
  same-tick semantics.

## Considered Options

1. **Accept finite forward time and settle zero-duration instructions at the
   current tick** (chosen)
2. Rely on division and rounding to reject invalid inputs incidentally
3. Permit negative `dt` as a reverse simulation mode
4. Silently discard or immediately fire actions scheduled in the past
5. Delay zero-duration instruction targets until the next positive tick

## Decision Outcome

Chosen: **public simulation time is finite, forward, and tick-aligned.**

One private validator accepts real numbers other than booleans and requires
them to be finite. `Sim` validates `dt` before it binds the node and requires
it to be strictly positive. Instants, cadence periods, run durations, and
instruction durations pass through the same numeric domain before tick
arithmetic. Runs and instructions require nonnegative duration; cadence keeps
its minimum of one whole tick.

`at(t)` remains absolute. It rejects any converted tick less than the current
tick, because the loop never rewinds. It accepts the current tick because the
next `run()`, including `run(0)`, performs the existing pre-step firing phase.
A rejected run or schedule has no effects on state, trajectory, pending
actions, or cadence accounting.

A zero-tick driver ramp sets its target directly and retains no program. Once
all targets of a zero-duration instruction settle, `Sim.trigger()` binds one
complete snapshot to the node. The tick and trajectory remain unchanged, and
later actions registered at that tick observe the target in registration
order.

## Consequences

- Invalid time configuration now raises an early `ValueError` naming the
  affected boundary and value.
- Backward simulation and rewinding are outside the API.
- Numeric strings are not coerced into time values.
- The current tick remains a valid scheduling boundary and `run(0)` remains a
  meaningful way to fire its pending actions.
- State can change at an unchanged tick when an instruction explicitly
  declares zero duration; trajectories continue to record advanced ticks
  only.
- Positive-duration ramp arithmetic, alignment tolerance, trajectory shape,
  and cadence cost accounting do not change.

## Evidence

Before implementation, 32 focused assertions failed on invalid boundaries or
zero-duration visibility. After implementation, the direct simulation suite
passed 38 tests with 28 subtests, and broader driver, enumeration, and scenario
coverage passed 68 tests with 28 subtests. The saved project probe rejects
`dt=-0.1` before construction and observes target state 10 in both the
simulation bank and node at tick zero with no trajectory entry. The complete
framework suite passed 1,638 tests with 16 skipped, 46 warnings, and 302
passing subtests.

## References

- `solid_node/simulation/timebase.py`
- `solid_node/simulation/sim.py`
- `solid_node/simulation/instruction.py`
- `solid_node/simulation/driver.py`
- `tests/test_simulation_sim.py`
- OpenSpec change `validate-simulation-time-boundaries`
