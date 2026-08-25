# Design: stepped-simulation-layer

## Context

Stage 1 opened the node-layer seams (`set_state`, ports, animator
rename). This stage builds the layer that produces snapshots. Nearly
every mechanic is spike-proven (`spike/FINDINGS.md`): the fixed-dt
loop, integer-exact ramps, deferred actions, cadence accounting, the
five verdicts. What the spike deliberately got wrong — class-attribute
driver *instances* holding shared mutable state — is the main thing
this design corrects (FINDINGS seam 2), alongside design-unit
instruction targets (seam 4).

## Goals / Non-Goals

**Goals:** `solid_node/simulation/` package (`driver.py`,
`instruction.py`, `sim.py`, `scenario.py`, `__init__.py` exporting
`Driver`, `Instruction`, `Sim`, `ScenarioTest`, `RampProgram`); spike
migrated onto it as caller validation.

**Non-Goals:** viewer/document schema, driver-table serialization,
named-variable expressions, G-code, flow variables, CLI/`manager/`
integration, sequencing in instructions, any change under
`solid_node/node/`.

## Decisions

1. **Dependency direction: `node/` never imports `simulation/`.**
   `Driver` and `Instruction` live in `simulation/`; projects declare
   them as class attributes on their assemblies, and `Sim` discovers
   them by scanning the class MRO for instances (the same base-first,
   subclass-wins walk `declared_ports` uses). A node without drivers
   remains fully usable with no simulation import anywhere — the
   v8-engine path is untouched by construction.
2. **State lives in the Sim.** `Sim` builds a bank of per-driver
   state objects from the declarations at construction. Declarations
   are frozen (no mutable attributes); the state object holds the
   current value and the active program. This is the spike's
   `reset()` smell resolved structurally: nothing to reset, ever.
3. **Integer discipline for discrete drivers.** `dtype=int` state is
   int end-to-end: defaults validated as ints, `RampProgram` uses
   floor-division distribution, instruction targets round once at
   trigger time. Float drivers use the same program shape without the
   integer guarantee. Trajectories record whatever the state type is;
   the determinism scenario compares exactly.
4. **Design-unit conversion happens at trigger time, on the driver's
   declared `scale`.** The alternative — resolving through a port's
   scale — was rejected for now: it would couple `simulation/` to
   port wiring that only exists after a render, and the driver
   declaration is the natural single place a maker states "this axis
   moves 0.0125 mm per microstep". Unifying driver scale with port
   scale is a candidate later refinement, noted in ADR-056's open
   questions rather than forced here.
5. **`Sim` binds all defaults up front.** Resolves stage 1's
   loud-unbound error for simulation contexts exactly as designed
   there ("stage 2's declared defaults are the designed resolution").
   Build/viewer paths remain stage 3+ territory.
6. **`ScenarioTest` composes, not integrates.** It extends
   `solid_node.test.TestCase` and needs nothing from
   `manager/test.py`: scenario methods are ordinary `test_` methods
   that construct a `Sim`. The `solid test` runner's per-instant
   `set_keyframe(0)` before each method is harmless — `Sim`
   construction rebinds the full snapshot. No runner change, by
   construction, keeps this cycle inside the simulation capability.
7. **Spike migration is the caller validation.** `spike/axis/`
   switches from `steplab.py` to the shipped package;
   `scenario.py` must revalidate all five verdicts. `SCOPE.md` and
   `FINDINGS.md` stay untouched as historical record (an addendum is
   the coordinator's post-verification step). The stand-in axis
   fixture for the framework's own tests lives under `tests/`
   following the existing fixture-project pattern, kept light: mesh
   assertions only where a scenario is genuinely about geometry.

## Risks / Trade-offs

- [MRO scan for Driver instances is implicit magic] → same pattern as
  `declared_ports`, small and tested; explicit registration was
  rejected as boilerplate the spike showed nobody needs.
- [Driver `scale` duplicates port `scale` conceptually] → accepted and
  documented (decision 4); revisit when the viewer layer needs one
  authoritative unit story.
- [Scenario mesh assertions are expensive per snapshot] → the spike's
  cost rule ("cadence budgets assertion cost; ticks are free") is
  carried into the spec via per-slot cost accounting; fixtures keep
  meshes minimal.
- [Two harnesses briefly exist (steplab + package)] → the migration
  deletes `steplab.py` in the same change; divergence cannot outlive
  the cycle.

## Migration Plan

Purely additive package plus spike-local migration; rollback is
reverting the commits. No existing caller changes required.

## Open Questions

None blocking. Deferred: unit-story unification (driver vs port
scale), viewer driver table, G-code programs — ADR-056 stage 3+.
