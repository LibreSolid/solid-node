# Tasks: driver-attribute-reads

## 1. Red: the attribute read

- [x] 1.1 New `tests/test_driver_attribute_reads.py` covering the
      kinematics-delta read scenarios: a declared driver reads as
      `self.x` and drives the pose; two sibling instances of one class
      read their own values; class access still returns the
      declaration and `declared_drivers_of` is unaffected; a read
      under `symbolic_drivers` yields the `DriverToken` and reverts to
      numbers on restore
- [x] 1.2 Same file: the unbound read raises naming the driver and
      `set_state`
- [x] 1.3 Confirm every new test fails for the right reason against
      unmodified source (the read returns the declaration object, not
      the value)

## 2. Red: the new loud failures

- [x] 2.1 Assigning `node.motor = 5` raises naming the driver and
      `set_state`, and leaves the bound snapshot unchanged
- [x] 2.2 Declaring a driver under a name a base already carries
      (`render`, `time`) fails at class-definition time naming the
      collision; redeclaring an inherited driver with a different
      default still defines and wins discovery
- [x] 2.3 `set_state` refuses an undeclared bare name and an unknown
      qualified id, each naming the rejected entry and the declared
      ids, and leaves the whole tree's snapshot exactly as it was
- [x] 2.4 Confirm all three fail red

## 3. Implement the descriptor

- [x] 3.1 `solid_node/node/qualified.py`: give `DriverDeclaration`
      `__set_name__` (storing the name in a private non-field slot
      through `object.__setattr__`, with the base-MRO shadowing
      guard), `__get__` (declaration on class access, bound value on
      instance access, `AttributeError` naming `set_state` when
      unbound), and `__set__` (always `AttributeError` naming
      `set_state`)
- [x] 3.2 Extend the module docstring to state the descriptor
      responsibility and why it sits in the node layer rather than in
      `simulation/driver.py`
- [x] 3.3 Note in `Driver`'s docstring that the read surface is
      inherited from the marker and that the frozen dataclass fields
      are untouched by the name slot
- [x] 3.4 Green: sections 1 and 2.1–2.2 pass

## 4. Remove the mapping and close the binding

- [x] 4.1 `solid_node/node/assembly.py`: delete `_BoundState` and the
      `state` property, and the now-unused `Mapping` import
- [x] 4.2 Same file: reject a bare name absent from the `declared` map
      the propagation walk already builds, and a dotted name absent
      from the union of its qualified ids, with `time` exempt; reuse
      the ambiguity path's rollback and re-render so a refused binding
      leaves nothing bound
- [x] 4.3 Green: section 2.3 passes
- [x] 4.4 Measured: 32.1 vs 30.1 us/tick on the two-axis fixture over
      200 ticks, best of five — 2.0 us/tick, 6.7% of a BARE tick and
      three orders of magnitude under the millisecond mesh assertion
      that sets real scenario runtime. Absorbed; recorded in design.md
      and the ADR-056 amendment

## 5. Converge every caller in the repository

- [x] 5.1 Convert declared-driver reads to the attribute form in
      `tests/meta_project/machine.py`, `tests/meta_project/axis.py`,
      `tests/test_simulation_drivers.py` and
      `tests/test_simulation_sim.py`, plus the node-side assertions in
      `test_document_drivers`, `test_simulation_enumeration`,
      `test_build_defaults` and `meta_project/test_axis`. The parity
      fixture needed none: its `Driver()`s are local variables, never
      class attributes, so no read goes through the descriptor
- [x] 5.2 Give the stage-1 classes in `tests/test_state_binding.py`
      declarations for the names they bind; convert their
      `dict(node.state)` assertions to attribute reads and to the
      loud-unbound contract after `clear_state()`; convert the single
      `state['time']` read to the `time` property
- [x] 5.3 Give `tests/test_ports.py`'s `Axis` a driver declaration,
      renaming to clear the collision with its `self.motor` CHILD node
- [x] 5.4 Verified `spike/` is not collected (`testpaths = ["tests"]`)
      and is referenced only in prose; the spike models are historical
      records of runs already made and are left untouched
- [x] 5.5 Verified no user-facing doc shows a driver read: the only
      `state['...']` in `docs/` is ADR-056's `sim.state['x']`, which is
      the simulation's own dict keyed by qualified id and unchanged

## 6. Prove it whole

- [x] 6.1 Full framework test suite green: 902 passed, 0 failed. The
      one failure seen at the recorded base (`test_pieces.py`, a file
      this change does not touch) did not reproduce in any run after
      it, and passes 3/3 in isolation — it was flaky at baseline, not
      a pre-existing defect this change had to work around
- [x] 6.2 Validation caller: convert the Metamaquina 2 root assembly's
      three reads to `self.x` / `self.y` / `self.z` and run that
      project's suite (independent repository; committed there, not
      here)

## 7. Records

- [x] 7.1 Amend ADR-056 with the descriptor read surface, its node-
      layer placement, and the single-read-path decision — the read
      surface is a seam that ADR left unsettled, not a separate
      decision; mark the amendment in `docs/adrs/README.md`
- [x] 7.2 Update the kinematics and simulation paragraphs of
      `docs/architecture.md`, which currently say `render()` reads
      drivers "through the `state` mapping"
- [x] 7.3 OpenSpec sync and archive; final validation
