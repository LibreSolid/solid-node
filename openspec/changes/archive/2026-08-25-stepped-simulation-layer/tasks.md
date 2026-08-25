# Tasks: stepped-simulation-layer

## 1. Drivers and programs

- [x] 1.1 Red: new `tests/test_simulation_drivers.py` covering the
      declaration scenarios — declarations carry no state (two sims,
      same class, independent trajectories); discovery off the class
      with default/range/unit/dtype/scale; integer ramp lands exactly
      with all-integer intermediates; exact-equality determinism of
      two fresh runs
- [x] 1.2 Implement `solid_node/simulation/driver.py`: frozen `Driver`
      declaration, MRO discovery helper, per-sim state object,
      `Program` protocol, `RampProgram` (integer floor-division
      distribution; float variant same shape)
- [x] 1.3 Green: driver tests pass

## 2. Instructions and the Sim loop

- [x] 2.1 Red: new `tests/test_simulation_sim.py` covering — defaults
      bind before first render (state-consuming assembly constructs
      without unbound error); non-whole instants rejected naming the
      instant and `dt`; deferred `at(t).run(fn)` sees post-tick state
      and runs exactly once; `at(t).trigger(name)` starts the ramp at
      that tick; `every()` cadence executes at the right ticks and
      accounts cost per slot; mm-target instruction reaches an
      integer microstep driver through the declared scale; trajectory
      records every tick
- [x] 2.2 Implement `solid_node/simulation/instruction.py` and
      `solid_node/simulation/sim.py` per design decisions 2–5
- [x] 2.3 Green: sim tests pass; full suite green

## 3. Scenario testing

- [x] 3.1 Red: minimal axis fixture project under `tests/` (existing
      fixture-project pattern, light geometry) plus
      `tests/test_simulation_scenario.py`: a homing scenario test class
      extending the scenario base — trigger at t=0, cadence
      interference assertion, deferred terminal check, bounded run —
      failing while `ScenarioTest` does not exist
- [x] 3.2 Implement `solid_node/simulation/scenario.py`
      (`ScenarioTest` extending `solid_node.test.TestCase`, fresh
      `Sim` per scenario) and `solid_node/simulation/__init__.py`
      exports
- [x] 3.3 Green: scenario tests pass under pytest; spot-check the same
      class runs under `solid test` against the fixture project

## 4. Spike migration (caller validation) and full validation

- [x] 4.1 Migrate `spike/axis/` to `solid_node.simulation`: delete
      `steplab.py`, update `axis_model.py` and `scenario.py` imports
      and driver/instruction declarations (design units for the mm
      targets); do NOT edit `spike/SCOPE.md` or `spike/FINDINGS.md`
- [x] 4.2 Run `spike/axis/scenario.py`: exit 0 with all five verdicts
      validated against the shipped package
- [x] 4.3 Full framework suite green
      (`PYTHONPATH=$PWD .venv pytest tests/ -q`); confirm
      `solid_node/node/` and `solid_node/test.py` are untouched by
      `git status`
- [x] 4.4 Records (coordinator): sync/archive the change, architecture
      overview simulation section, ADR-056 disposition, FINDINGS
      addendum
      (Verified independently: 813 passed full suite, v8-engine 33/33,
      spike five verdicts exit 0. architecture.md simulation section
      added with stage-3 boundaries; ADR-056 implementation-status
      section and updated open questions; FINDINGS addendum 2 records
      the migration and closed seams.)
