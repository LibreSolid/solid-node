# Spike: stepped driver simulation, one axis end-to-end

Design evidence for [ADR-056](../docs/adrs/NODE/ADR-056-signals-drivers-ports-and-stepped-simulation.md)
(Proposed, pre-OpenSpec). This spike validates or invalidates the
stepped-simulation direction; it creates no requirements and ships no
framework code. Everything under `spike/` is non-shipping.

## Primary question

Can a stateful driver layer step a model deterministically and drive
the *existing* pure render/assert machinery per snapshot — without
modifying framework internals, and at acceptable cost?

Separability note: every tick binds all drivers to *numbers*, so
per-snapshot rendering needs nothing symbolic. The
expression-representation risk (named driver variables for client-side
evaluation) is a separate, later spike. Confirming that separability
cleanly is itself a finding.

## Sub-questions — each gets a verdict

1. **Purity holds.** Can `set_keyframe(time)` generalize to a
   multi-driver `set_state(x=...)` as a spike-local shim (subclass or
   wrapper, no framework edits), with `_idempotent_render`'s sweep
   keeping per-tick re-renders absolute rather than accumulating? If a
   shim cannot reach it without touching framework internals, the
   finding is the exact seam the OpenSpec change must open — success,
   not failure.
2. **Determinism.** Fixed `dt`, instants as integer step counts
   (`i*dt`), events injected at ticks. The same scenario run twice must
   produce *exactly* equal state trajectories (no accumulated floats —
   the ADR-050 reasoning).
3. **Instruction semantics v1 works.** One event ("Home X" at t=0) →
   driver ramps linearly to target over its duration → carriage
   translates accordingly. The ramp lives in the driver step function,
   nowhere near `render()`.
4. **Per-tick connect survives re-render.** A minimal port binding in
   the parent's `render()` (stepper angle → carriage position through a
   belt ratio), re-executed every tick, interacting with the
   idempotent-render sweep.
5. **Cost is measurable and survivable.** Ticks/second without
   assertions; cost of one mesh-assertion snapshot; from those numbers,
   a concrete default recommendation for scenario assertion cadence.

## The model

A minimal stand-in X axis — motor body, pulley, carriage, rods; a few
simple leaves. Metamaquina2 dimensions where convenient, but geometry
fidelity is explicitly out of scope; the axis exists to move and be
asserted against (carriage clears the motor mount, reaches x=0).
Metamaquina2 remains the named originating project.

## The scenario

    dt=0.02; at t=0 trigger 'Home X' (x: 100 -> 0 over 2.0 s);
    every 0.1 s: interference assertion; at t=2.5: assert x == 0;
    run 3.0 s

Written against the `sim.at / sim.every / sim.run` sketch — the spike
doubles as the ergonomics check on that interface.

## Out of scope

- Symbolic / named-variable expressions (separate spike)
- Viewer, browser, buttons, document schema — headless spike
- G-code, multiple axes, acceleration profiles, anything bond-graph
- Ports beyond the one minimal binding; `Driver`/`Instruction` as real
  framework API
- Any edit to framework source files — spike code shims from outside

## Deliverables and exit

- Spike code plus `FINDINGS.md`: verdict per sub-question (validated /
  invalidated / blocked), the timing numbers, and the list of framework
  seams the real change must open.
- Committed on the `signal-drivers` branch beside ADR-056, citable by
  the eventual OpenSpec proposal.
- Timebox: day-scale, a few hundred lines. If sub-question 1 blocks
  early, stop and report the seam — that alone justifies the spike.

Design-invalidating outcome to watch for: per-tick re-render cost
dominated by something unavoidable in `assemble()` (e.g. scad
regeneration per snapshot rather than operation re-resolution).
