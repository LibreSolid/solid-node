# ports Specification

## Purpose
Domain-typed connection points on nodes (ADR-056): port declarations
carrying physical domain, unit, and scale metadata, bound per render
by the parent's causal `connect()`. The reserved flow slot keeps the
door open for later acausal (bond-graph) modeling without renaming
project code.
## Requirements
### Requirement: Domain-typed ports

The system SHALL provide domain-typed port declarations for nodes:
`RotationalPort` (carries an angle), `TranslationalPort` (carries a
position), and `SignalPort` (carries a dimensionless command value),
sharing a common `Port` base. A port declaration SHALL be made as a
class attribute on a node and SHALL carry declaration metadata: its
domain, a `unit` label, an optional direction marker (`out=True` for a
port the node emits), and an optional linear scale declaring how many
design units one native unit of a connected source represents.

Declarations SHALL be stateless and shared at class level; the bound
value SHALL live in a per-instance slot materialized on first access,
so two instances of the same node class never share a port value. A
node's declared ports SHALL be discoverable by name on the class, so
later tooling (simulation, UI) can enumerate them without
instantiating behavior.

Ports in this version are kinematic only: a port SHALL NOT expose a
flow variable (torque, force). The declaration shape reserves that
extension per ADR-056; introducing it is a future spec change.

#### Scenario: Per-instance value isolation

- **WHEN** two instances of a node class declaring
  `crank = RotationalPort(out=True, unit='deg')` bind different values
  to `crank`
- **THEN** each instance reads back its own value

#### Scenario: Declared ports are discoverable

- **WHEN** a consumer inspects a node class that declares two ports
- **THEN** it can enumerate both ports with their domain, unit,
  direction, and scale without rendering the node

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

#### Scenario: Assignment binds with scale

- **WHEN** a hook executes `unit.crank = angle + 90.0` on a child whose
  `crank` port declares a scale
- **THEN** the port's bound value is the expression multiplied by the scale
  and reading `unit.crank` still yields the bound port, not the raw
  expression

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
