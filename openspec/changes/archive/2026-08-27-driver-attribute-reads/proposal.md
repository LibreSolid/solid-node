## Why

A driver is declared as a class attribute — `x = Driver(default=..., unit='mm')`
— and then read back through a string key in a mapping:
`self.state['x']`. The declaration and the read do not look like the
same thing, and the read is a magic string the class already spelled
out three lines above. The Metamaquina 2 root assembly declares `x`,
`y` and `z` and then reads `self.state['x']`, `self.state['y']`,
`self.state['z']`; a typo there is a runtime error rather than a name
error, and nothing connects the read to the declaration it depends on.

The framework already answers this exact question correctly one layer
over: a `Port` is declared as a class attribute and read as
`self.position` — a descriptor, with the declaration on the class and
the bound value per instance (`solid_node/node/ports.py`). Ports and
drivers are the same shape of thing, discovered by the same MRO scan,
and they should be read the same way. Drivers are the odd one out, and
the Metamaquina 2 assembly is the first real machine to feel it.

The `state` mapping is not a second way to do this that happens to
also exist; it is the stage-1 shape from before drivers were declared
at all. `set_state` was built in `multi-driver-state-seam`, and
`Driver` arrived in `stepped-simulation-layer` after it. Nothing has
been released, so there is nothing to stay compatible with, and
carrying two read surfaces for one value would be noise the framework
would have to keep explaining.

## What Changes

- A declared driver SHALL be read as an attribute of the node that
  declares it: `self.x` returns the bound native value, in both
  numeric and symbolic (`DriverToken`) binding modes.
- `DriverDeclaration` becomes a descriptor. `__get__` off an instance
  returns the bound value; off the CLASS it returns the declaration
  itself, so `declared_drivers`, `qualified_drivers`, the document's
  driver table and every other consumer that reads the declaration are
  unaffected. Discovery already scans `vars()`, so it never invokes
  the descriptor at all.
- Reading a driver whose entry is unbound raises loudly, naming the
  driver and `set_state`, preserving the existing unbound contract.
- Assigning to a declared driver on an instance raises loudly and
  names `set_state`. The declaration is class metadata and the value
  belongs to a snapshot; `self.x = 5` is a mistake worth catching at
  the moment it is made rather than silently shadowing the driver.
- Declaring a driver whose name would shadow an existing member of the
  node class (`render`, `color`, `mesh`, `state`, `time`, …) raises at
  class-definition time, naming the collision. This hazard is created
  by this change — a name that was previously confined to a mapping
  key now lands in the node's attribute namespace — so the change
  closes it rather than leaving it to be found by a broken render.
  Redeclaring an inherited driver stays legal: that is how a subclass
  overrides a declaration today.
- **BREAKING** The `state` mapping is REMOVED from `AssemblyNode`,
  along with the `_BoundState` view behind it. `self.x` is the only
  way to read a driver, `self.time` is the only way to read animation
  time, and `simulation.enumeration.qualified_drivers` remains what it
  already is — the one authority on what drivers a machine has.
- **BREAKING** `set_state` SHALL reject a name that no declaration in
  the tree bears: a bare name no declared driver carries, or a dotted
  name that is not a qualified id the tree publishes. `time` remains
  the one global exception. This follows from the removal rather than
  extending it — once the attribute is the only read, an entry with no
  declaration behind it can never be read by anything, so accepting
  one is a silent no-op. The rejection reuses the rollback the
  ambiguity check already performs, so a refused binding leaves no
  half-bound tree.
- Not changed, because all three are genuinely flat namespaces that a
  Python attribute cannot address: `set_state(**{'x_axis.motor': …})`
  binding by qualified id, `Instruction({'x': …})` targets, and
  `sim.state['x_axis.motor']`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kinematics`: the "Multi-driver state binding" requirement replaces
  the `state` mapping read with the attribute read for a declared
  driver, adds the loud unbound and assignment errors and the
  class-definition-time shadowing guard, and requires `set_state` to
  reject an undeclared name.
- `ports`: one scenario illustrates driver reads with
  `self.state['motor']`; it moves to the attribute form. No port
  requirement changes.

## Impact

- Code: `solid_node/node/qualified.py` (`DriverDeclaration` gains
  `__set_name__`, `__get__`, `__set__` and the shadowing guard);
  `solid_node/node/assembly.py` (delete `_BoundState` and the `state`
  property; add undeclared-name rejection to `set_state`);
  `solid_node/simulation/driver.py` (`Driver` is a frozen dataclass
  and needs its name slot set through `object.__setattr__`; no
  behavior of its own changes). No change to `serializer.py`,
  `enumeration.py`, `sim.py`, the loader, the document schema, or the
  viewer — the serializer already works directly on `_states`, and
  `Sim.state` is a different property keyed by qualified id.
- Specs: `kinematics` and `ports` deltas.
- Tests: new red-first coverage for the attribute read (numeric and
  symbolic), the unbound error, the assignment error, the shadowing
  guard, per-instance isolation, and the undeclared-name rejection.
  Every driver-declaring fixture converts to the attribute form. The
  stage-1 classes in `tests/test_state_binding.py` and
  `tests/test_ports.py` that bind names they never declared are
  converted to declare them; `tests/test_ports.py`'s `Axis` also holds
  a CHILD named `motor`, so its driver takes a distinct name — the
  shadowing hazard the guard exists for, found in the framework's own
  fixtures. Assertions of the form `dict(node.state) == {...}` become
  assertions on the contract: the attribute reads the value, or raises
  after `clear_state()`.
- Validation caller: the Metamaquina 2 project (an independent
  repository, not part of this change's commits) is the originating
  finding and the confirming caller — its root assembly's three
  `self.state[...]` reads become `self.x`, `self.y`, `self.z`.
- No dependency, CLI, viewer, or document-schema changes.
