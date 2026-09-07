## Context

`Sim._ticks()` rounds `value / dt` and verifies alignment within `1e-9`, but
neither operand is first constrained to finite forward time. A negative `dt`
turns positive instants and durations into negative tick numbers. `run()` then
computes an end before the current tick, fires the current tick, skips its
stepping loop, and returns successfully. NaN and infinity reach arithmetic
errors at inconsistent later points.

The scheduler stores actions by absolute integer tick. Once the simulation has
passed a tick, adding an action there strands it because `_fire()` never moves
backward. The current tick is different: every `run()`, including `run(0)`,
fires it before stepping and can therefore honor a newly registered action.

`Instruction` already rejects negative duration and `RampProgram.value_at(0)`
already returns the target for a zero-tick ramp. `DriverState.ramp_to()` still
stores that completed program, however, and `Sim.trigger()` does not rebind the
node until a later step. The state bank and node therefore disagree with the
ramp's existing zero-tick meaning at the trigger instant.

## Goals / Non-Goals

**Goals:**

- Validate all public simulation time values as finite real seconds before
  tick arithmetic or state mutation.
- Require `dt > 0`, `run(duration) >= 0`, instruction duration `>= 0`, and
  cadence period of at least one tick.
- Reject absolute scheduled instants before the current tick while accepting
  the current and future ticks.
- Preserve whole-tick alignment and integer tick storage.
- Apply and bind a zero-duration instruction's target at the current tick
  without adding a trajectory tick.
- Produce `ValueError` diagnostics that name the offending boundary and value.

**Non-Goals:**

- Support backward simulation, negative time steps, or rewinding.
- Change the absolute meaning of `at(t)` or make it relative to the current
  tick.
- Change the `1e-9` alignment tolerance or accumulate floating-point time.
- Sequence instructions, introduce programs beyond linear ramps, or add a
  trajectory entry when no tick advanced.
- Validate driver target values, ranges, or units in this change.

## Decisions

### D1: Validate one finite-real seconds domain

A private simulation helper will accept Python real numbers except booleans
and require `math.isfinite(value)`. `Sim.__init__`, `_ticks()`, and
`Instruction.__init__` will use it, so strings, `None`, NaN, and infinities
receive a deliberate `ValueError` rather than an incidental arithmetic error.
The original numeric value is retained after validation; valid integer and
float callers keep their current arithmetic.

Relying on division or `round()` to reject invalid inputs was rejected because
negative finite values remain arithmetically valid and NaN/infinity fail with
unrelated messages. Coercing numeric strings was rejected because a time API
should not silently parse configuration text.

### D2: Validate `dt` before simulation initialization

Construction will require finite `dt > 0` before enumerating drivers, binding
the node, assembling meshes, or creating mutable simulation state. The fixed
step is the denominator and direction of every clock conversion; no later
boundary can make a nonpositive value meaningful.

Allowing negative `dt` for reverse motion was rejected because programs,
trajectory ordering, deferred actions, and cadence are all forward-only.
Allowing zero was rejected because it defines no tick duration.

### D3: Reject invalid relative and absolute times before effects

`run(duration)` will convert and reject a negative tick count before `_fire()`
or state changes. `at(t)` will convert the absolute instant and reject a tick
less than `self.tick`. A tick equal to `self.tick` remains valid because the
next call to `run()`, including a zero-duration run, fires current actions.
`every(period)` retains its minimum one-tick rule after finite/alignment
validation. Instruction duration remains nonnegative.

Silently ignoring a past action was rejected because it creates the same false
green result as the audit reproduction. Firing it immediately was rejected
because it would claim an action ran at an instant the simulation has already
passed. Rejecting the current tick was rejected because the run loop has an
explicit pre-step firing phase for it.

### D4: Complete zero-tick ramps at trigger time

`DriverState.ramp_to(target, ticks=0, tick)` will set its value directly and
retain no active program. After all instruction targets are applied,
`Sim.trigger()` will rebind the complete state snapshot when the duration is
zero. Direct triggers and triggers fired by `at()` then expose the target in
both `sim.state` and the node at that same tick; later actions registered for
the tick observe it according to registration order. No trajectory entry is
added because the clock did not advance.

Waiting for tick one was rejected because `RampProgram` already defines a
zero-tick ramp as complete at elapsed tick zero. Advancing the clock solely to
apply the instruction was rejected because duration zero must consume no
simulation time.

### D5: Prove refusal has no hidden progress

Regressions will cover invalid `dt` at construction and invalid values at
`at`, `every`, `run`, and `Instruction`. Negative-run and past-schedule tests
will assert unchanged tick, state, trajectory, and pending actions. Separate
zero-duration cases will prove immediate direct binding and registration-order
visibility through the scheduled path. The saved probe must report the
negative `dt` refusal and state/node target 10 immediately after the zero-time
instruction.

## Risks / Trade-offs

- **Previously accepted bad inputs now fail earlier.** They could not produce
  a valid forward simulation; early `ValueError` is the intended correction.
- **A zero-duration trigger mutates state without a trajectory entry.** The
  trajectory records advanced ticks. The current state and bound node remain
  the source of truth at the unchanged tick.
- **Current-tick actions can be registered after a prior run.** They remain
  deferred until the next `run()` call, preserving the scheduler's explicit
  execution boundary and making `run(0)` meaningful.

## Migration Plan

No stored data migration is required. Scenario code using invalid time values
must correct them. Code relying on a zero-duration instruction taking effect
one positive tick late will observe the declared target immediately instead.

## Open Questions

None.
