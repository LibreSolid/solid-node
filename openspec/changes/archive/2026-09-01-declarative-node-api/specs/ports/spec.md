## MODIFIED Requirements

### Requirement: Per-render causal port binding

The system SHALL let the assembly that owns the render bind port
values causally each render: an emitting node SHALL set its output
port's value during `render()`, and `connect(source, sink)` on an
internal node SHALL bind a sink port to a source — a port or a plain
numeric value — applying the sink's declared linear scale when one is
present. Assigning a value to a port attribute of a node
(`unit.crank = expression`) SHALL perform the same binding as
`connect(expression, unit.crank)`, scale applied; a port declaration is a
data descriptor, so such an assignment SHALL never shadow the declaration
with a raw instance attribute. Bindings SHALL be re-evaluated on every
render, so a re-render under a new state snapshot rebinds every port
absolutely; port binding SHALL NOT accumulate history or interact with the
operation sweep.

Connection is one-directional in this version: value flows from source
to sink. Acausal connection semantics (equation generation, solver
orientation) are explicitly out of scope and MUST NOT be implied by
this surface.

#### Scenario: Stepper microsteps drive a carriage in design units

- **WHEN** an axis assembly's `render()` binds a motor's rotational
  output from its declared driver read as `self.motor` and
  `connect()`s it to a carriage input port whose scale declares
  millimetres per microstep
- **THEN** after `set_state(motor=4000)` the carriage input port reads
  the converted position in millimetres and the derived translation
  places the carriage there absolutely

#### Scenario: Rebinding is absolute across renders

- **WHEN** the same assembly renders under two successive state
  snapshots
- **THEN** each render leaves every bound port holding exactly the
  value derived from the current snapshot, with no residue of the
  previous one

#### Scenario: Assignment binds with scale

- **WHEN** a hook executes `unit.crank = angle + 90.0` on a child whose
  `crank` port declares a scale
- **THEN** the port's bound value is the expression multiplied by the scale
  and reading `unit.crank` still yields the bound port, not the raw
  expression
