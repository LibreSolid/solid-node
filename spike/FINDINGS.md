# Spike findings: stepped driver simulation, one axis end-to-end

Evidence for [ADR-056](../docs/adrs/NODE/ADR-056-signals-drivers-ports-and-stepped-simulation.md),
per [SCOPE.md](SCOPE.md). Executed 2026-08-25 in the `signal-drivers`
worktree at framework base `ce9b459`, workspace venv, OpenSCAD
/usr/bin/openscad, Linux. Runner: `spike/axis/scenario.py`; all output
reproduced by running it (artifacts build under `spike/axis/_build/`,
gitignored).

Model: 5-leaf stand-in X axis (mount, two rods, carriage, pulley),
GT2-on-20-tooth numbers (40 mm/rev, 3200 µsteps/rev, 0.0125 mm/µstep),
travel 100 mm home over 2.0 s at dt=0.02 → exactly 80 µsteps/tick.

## Verdicts

| Sub-question | Verdict |
|---|---|
| 1. Purity across re-renders | **Validated** |
| 2. Determinism | **Validated** |
| 3. Instruction ramp v1 | **Validated** |
| 4. Per-tick connect in render() | **Validated** |
| 5. Cost | **Validated** |

**Primary question: validated.** A stateful driver layer stepped the
model deterministically through the existing pure render/assert
machinery, shimmed entirely from outside the framework (zero framework
edits), at negligible cost for this model size.

### 1. Purity

`set_state(**states)` shimmed over `set_keyframe(0)` — the framework's
only public re-render trigger — worked unmodified. After 151 renders
(150 ticks + one arbitrary snapshot) the carriage held exactly **1**
driven operation: ADR-023's driver-tagged sweep replaced, never
accumulated. Binding an arbitrary snapshot (`motor=4000`) placed the
carriage mesh absolutely at x-bounds 50.000000..90.000000. Geometry is
a pure function of the snapshot, as the ADR-056 guardrail requires.

The feared design-invalidating outcome **did not occur**: per-tick
re-renders never touch the artifact path. Leaf STL/scad generation
happens once in `assemble()`; keyframe re-renders only re-resolve
operations. The stepping model composes with the mtime build machinery
untouched.

### 2. Determinism

Driver state is integer microsteps; programs distribute deltas as
`start + delta*k//n` (exact landing at `start+delta`). Two fresh
150-tick runs produced **exactly equal** trajectories (`==` on integer
tuples, no tolerance). Instants are integer tick counts (`i*dt` never
accumulated) — the ADR-050 reasoning applied to simulation state.
Recommendation: where the physical device is discrete (steppers),
driver state should be integer-typed in the real API.

### 3. Instruction ramp

`Home X` = targets + duration, triggered at t=0, ramped inside the
driver's step function (nowhere near `render()`): at t=2.5, motor
state exactly 0 µsteps, carriage x exactly 0.0 mm.

### 4. Per-tick connect

The port binding in `render()` (µsteps → pulley angle, µsteps →
carriage translation through the belt ratio) re-executed every tick
with no interaction problems with the idempotent-render sweep.

### Teeth check

Overshoot instruction (`Crash X`, x → −5 mm past the mount face at
−2 mm) failed exactly as it must:
`mount should not interfere with carriage (intersection volume 2700.0)`
— the hand-computed 3×60×15 mm³ overlap, caught by the 0.1 s cadence
at the tick it appears.

### 5. Cost

- First build + assemble: **0.34 s** (once).
- Bare stepping (advance + set_state + full re-render): **~267,000
  ticks/s** (~4 µs/tick).
- One `assertNoSolidInterference` snapshot: **~1.0 ms** mean (cached
  manifolds + AABB broad phase, ADR-029) ≈ **250× a bare tick**.
- The SCOPE scenario (150 ticks, 30 interference checks): **0.03 s**.

Cadence recommendation: stepping is free; assertion cost dominates and
scales with mesh complexity, not with the simulation. Default scenario
cadence of 0.1 s is comfortable at this model size; these absolute
numbers do NOT extrapolate to v8-scale meshes (660k-face parts), where
the per-check cost governs — the structural rule "cadence budgets
assertion cost, ticks are free" is the durable finding.

## Seams the real framework change must open

1. **`set_keyframe(time)` → state-dict binding.** The only public
   re-render/sweep trigger takes a single scalar. The real API
   generalizes it to a driver-state snapshot (`set_state(**states)`),
   with `time` as one entry and the same recursive child propagation.
2. **Driver declaration vs driver state.** The spike declares driver
   *instances* as class attributes, so state is shared across node
   instances and `Sim` must `reset()` them. The real API must separate
   declaration (class-level: default, range, unit) from
   per-simulation state — the same distinction node operations already
   honor per instance.
3. **Deferred scenario actions.** ADR-056's sketch
   `sim.at(2.5).assertEqual(sim.state.x, 0)` cannot work — arguments
   evaluate at registration time. The interface needs deferred
   callables (`sim.at(t).run(fn)`); the ADR's open-questions sketch
   should be corrected when it is next revised.
4. **Instruction targets and units.** The spike expresses `Home X` in
   driver-native µsteps; a maker thinks in mm. The real interface
   needs the port-level unit conversion (mm target → µstep target)
   so instructions are written in design units.

## Addendum (2026-08-25, after stage 1 landed)

The `multi-driver-state-seam` change absorbed the shim this spike
prototyped: `AssemblyNode` now provides `set_state`/`clear_state`/
`state` natively. The spike's `DrivenAssembly.set_state` override had
to be **deleted** (not adapted): once the framework's `set_keyframe`
delegates to `set_state`, the override intercepted the framework's own
`time` entry and rejected it — the compatibility contract holds for
every *caller* of `set_keyframe`, but not for a subclass that overrides
`set_state`. `Sim` now binds the initial snapshot explicitly, since the
framework by design invents no driver defaults (stage 2's job). With
the shim dissolved, `scenario.py` revalidates all five verdicts against
the real API (exit 0, 2026-08-25).

## Separability confirmed

Every tick binds all drivers to plain numbers; nothing symbolic was
needed anywhere in the loop. The expression-representation risk (named
driver variables for client-side viewer evaluation) is fully decoupled
from stepping and remains its own spike, exactly as ADR-056 assumed.
