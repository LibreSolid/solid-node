# Tasks: driver-attribute-reads

## 1. Red: the attribute read

- [ ] 1.1 New `tests/test_driver_attribute_reads.py` covering the
      kinematics-delta read scenarios: a declared driver reads as
      `self.x` and drives the pose; two sibling instances of one class
      read their own values; class access still returns the
      declaration and `declared_drivers_of` is unaffected; a read
      under `symbolic_drivers` yields the `DriverToken` and reverts to
      numbers on restore
- [ ] 1.2 Same file: the unbound read raises naming the driver and
      `set_state`
- [ ] 1.3 Confirm every new test fails for the right reason against
      unmodified source (the read returns the declaration object, not
      the value)

## 2. Red: the new loud failures

- [ ] 2.1 Assigning `node.motor = 5` raises naming the driver and
      `set_state`, and leaves the bound snapshot unchanged
- [ ] 2.2 Declaring a driver under a name a base already carries
      (`render`, `time`) fails at class-definition time naming the
      collision; redeclaring an inherited driver with a different
      default still defines and wins discovery
- [ ] 2.3 `set_state` refuses an undeclared bare name and an unknown
      qualified id, each naming the rejected entry and the declared
      ids, and leaves the whole tree's snapshot exactly as it was
- [ ] 2.4 Confirm all three fail red

## 3. Implement the descriptor

- [ ] 3.1 `solid_node/node/qualified.py`: give `DriverDeclaration`
      `__set_name__` (storing the name in a private non-field slot
      through `object.__setattr__`, with the base-MRO shadowing
      guard), `__get__` (declaration on class access, bound value on
      instance access, `AttributeError` naming `set_state` when
      unbound), and `__set__` (always `AttributeError` naming
      `set_state`)
- [ ] 3.2 Extend the module docstring to state the descriptor
      responsibility and why it sits in the node layer rather than in
      `simulation/driver.py`
- [ ] 3.3 Note in `Driver`'s docstring that the read surface is
      inherited from the marker and that the frozen dataclass fields
      are untouched by the name slot
- [ ] 3.4 Green: sections 1 and 2.1–2.2 pass

## 4. Remove the mapping and close the binding

- [ ] 4.1 `solid_node/node/assembly.py`: delete `_BoundState` and the
      `state` property, and the now-unused `Mapping` import
- [ ] 4.2 Same file: reject a bare name absent from the `declared` map
      the propagation walk already builds, and a dotted name absent
      from the union of its qualified ids, with `time` exempt; reuse
      the ambiguity path's rollback and re-render so a refused binding
      leaves nothing bound
- [ ] 4.3 Green: section 2.3 passes
- [ ] 4.4 Measure the per-tick cost of always building the rollback
      snapshot against a stepping loop, and report the number; return
      to the pilot if it is material rather than absorbing it

## 5. Converge every caller in the repository

- [ ] 5.1 Convert declared-driver reads to the attribute form in
      `tests/meta_project/machine.py`, `tests/meta_project/axis.py`,
      `tests/test_simulation_drivers.py`, `tests/test_simulation_sim.py`
      and `solid_node/viewers/widget/tools/generate_parity_fixture.py`
- [ ] 5.2 Give the stage-1 classes in `tests/test_state_binding.py`
      declarations for the names they bind; convert their
      `dict(node.state)` assertions to attribute reads and to the
      loud-unbound contract after `clear_state()`; convert the single
      `state['time']` read to the `time` property
- [ ] 5.3 Give `tests/test_ports.py`'s `Axis` a driver declaration,
      renaming to clear the collision with its `self.motor` CHILD node
- [ ] 5.4 Update the `spike/` models only if they are exercised by the
      suite; leave a historical spike record alone otherwise
- [ ] 5.5 Update the driver examples in `docs/` prose that show
      `self.state['...']`

## 6. Prove it whole

- [ ] 6.1 Full framework test suite green, with the pre-existing
      unrelated `test_pieces.py` failure unchanged from the recorded
      base
- [ ] 6.2 Validation caller: convert the Metamaquina 2 root assembly's
      three reads to `self.x` / `self.y` / `self.z` and run that
      project's suite (independent repository; committed there, not
      here)

## 7. Records

- [ ] 7.1 Extract an ADR for the descriptor read surface, its node-
      layer placement, and the single-read-path decision; update
      `docs/adrs/README.md`
- [ ] 7.2 Update the kinematics and simulation paragraphs of
      `docs/architecture.md`, which currently say `render()` reads
      drivers "through the `state` mapping"
- [ ] 7.3 OpenSpec sync and archive; final validation
