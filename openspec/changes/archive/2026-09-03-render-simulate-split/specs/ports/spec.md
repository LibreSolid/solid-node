## MODIFIED Requirements

### Requirement: Per-render causal port binding

The system SHALL let the assembly that owns the simulation bind port values
causally each `simulate()`: an emitting node SHALL set its output port's
value during `simulate()`, and `connect(source, sink)` on an internal node
SHALL bind a sink port to a source — a port or a plain numeric value —
applying the sink's declared linear scale when one is present. Assigning a
value to a port attribute of a node (`unit.crank = expression`) SHALL
perform the same binding as `connect(expression, unit.crank)`, scale
applied; a port declaration is a data descriptor, so such an assignment
SHALL never shadow the declaration with a raw instance attribute. Bindings
SHALL be re-evaluated on every `simulate()`, so a run under a new state
snapshot rebinds every port absolutely; port binding SHALL NOT accumulate
history or interact with the operation sweep. Binding or reading a port in
`render()` SHALL keep working as the deprecated form: the render re-runs per
binding and the framework warns once per class.

#### Scenario: Stepper microsteps drive a carriage in design units

- **WHEN** an axis assembly's `simulate()` binds a motor's rotational
  output from its declared driver read as `self.motor` and
  `connect()`s it to a carriage input port whose scale declares
  millimetres per microstep
- **THEN** after `set_state(motor=4000)` the carriage input port reads
  the converted position in millimetres and the derived translation
  places the carriage there absolutely

#### Scenario: A port bound in render warns

- **WHEN** an assembly's `render()` binds a child's port from a constant
  and reads nothing
- **THEN** a `FutureWarning` names the class and the port, and the render
  keeps re-running per binding

#### Scenario: Rebinding is absolute across simulations

- **WHEN** the same assembly simulates under two successive state
  snapshots
- **THEN** each run leaves every bound port holding exactly the value
  derived from that snapshot
