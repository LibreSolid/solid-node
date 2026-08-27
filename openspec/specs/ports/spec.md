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

The system SHALL let the assembly that owns the render bind port
values causally each render: an emitting node SHALL set its output
port's value during `render()`, and `connect(source, sink)` on an
internal node SHALL bind a sink port to a source — a port or a plain
numeric value — applying the sink's declared linear scale when one is
present. Bindings SHALL be re-evaluated on every render, so a
re-render under a new state snapshot rebinds every port absolutely;
port binding SHALL NOT accumulate history or interact with the
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

