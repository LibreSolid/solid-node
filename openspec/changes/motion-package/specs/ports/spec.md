## MODIFIED Requirements

### Requirement: Domain-typed ports

The system SHALL provide domain-typed port declarations for nodes:
`RotationalPort` (carries an angle), `TranslationalPort` (carries a
position), and `SignalPort` (carries a dimensionless command value),
sharing a common `Port` base. These declarations, the port base, the
binding helper and the declaration enumerator SHALL be exported from
`solid_node.motion.ports`, the module that answers what moves and what
carries a value, and SHALL NOT be exported from `solid_node.node`. A
port declaration SHALL be made as a class attribute on a node and SHALL
carry declaration metadata: its domain, a `unit` label, an optional
direction marker (`out=True` for a port the node emits), and an optional
linear scale declaring how many design units one native unit of a
connected source represents.

Declarations SHALL be stateless and shared at class level; the bound
value SHALL live in a per-instance slot materialized on first access,
so two instances of the same node class never share a port value. A
node's declared ports SHALL be discoverable by name on the class, so
later tooling (simulation, UI) can enumerate them without
instantiating behavior.

Ports in this version are kinematic only: a port SHALL NOT expose a
flow variable (torque, force). The declaration shape reserves that
extension per ADR-056; introducing it is a future spec change.

#### Scenario: The port kinds are imported from the motion package

- **WHEN** a project writes
  `from solid_node.motion.ports import Port, RotationalPort, TranslationalPort, SignalPort, declared_ports`
- **THEN** every name resolves to the declaration it names, and the same
  names are absent from `solid_node.node`

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
applying the sink's declared linear scale when one is present. `connect`
SHALL remain a method of the internal node that performs it, not an
imported name; the binding helper it calls SHALL be exported from
`solid_node.motion.ports`. Assigning a
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

## ADDED Requirements

### Requirement: The motion package holds what moves

The system SHALL provide a package `solid_node.motion` whose subject is
what moves and what drives what, laid out as three submodules so that an
import line names the kind of thing it brings in:

- `solid_node.motion.ports` — a value that flows between nodes: the port
  declarations, their bound value slot, the binding helper, the
  declaration enumerator, and the root's own time channel (`Time`, and
  the enumerator that reads a class's time declaration);
- `solid_node.motion.joints` — a pair that places a body;
- `solid_node.motion.couplings` — a law between two coordinates.

`solid_node.motion.joints` and `solid_node.motion.couplings` SHALL exist
and SHALL export no name in this version; each SHALL carry a docstring
stating what it will hold. The package `__init__` SHALL export no name
of its own and SHALL NOT resolve a submodule's names as attributes of
the package, so there is exactly one import path for each name.

#### Scenario: The submodules exist and are empty

- **WHEN** a consumer imports `solid_node.motion.joints` and
  `solid_node.motion.couplings`
- **THEN** both modules import successfully, each carries a docstring
  naming what it will hold, and neither exports a public name

#### Scenario: The package itself exports nothing

- **WHEN** a consumer reads any port, time-base, joint or coupling name
  off `solid_node.motion` directly
- **THEN** `AttributeError` is raised, so
  `from solid_node.motion import RotationalPort` fails at the import and
  the submodule path is the only path

### Requirement: Ports and the time base are not node exports

The system SHALL NOT export `Port`, `RotationalPort`,
`TranslationalPort`, `SignalPort`, `declared_ports` or `Time` from
`solid_node.node`, and SHALL NOT provide a module
`solid_node.node.ports` or `solid_node.node.timebase`. There SHALL be no
re-export, alias, or deprecation shim by which a project can keep
importing them from the node package: a project that has not migrated
SHALL fail at its import line.

Reading one of those names — or either of the two removed submodule
names — as an attribute of `solid_node.node` SHALL raise an error whose
message names `solid_node.motion.ports` as the module that now answers
for it, so a reader of the failure learns where the name went. Because
the import machinery converts that attribute failure, `from
solid_node.node import <name>` SHALL raise `ImportError` carrying the
same message.

#### Scenario: The old path is refused

- **WHEN** a project runs
  `from solid_node.node import AssemblyNode, RotationalPort, SignalPort, Time`
- **THEN** the import raises `ImportError`, the message names
  `solid_node.motion.ports` and shows the import line that replaces it,
  and no port or time-base name is bound

#### Scenario: The removed submodules are gone

- **WHEN** a consumer imports `solid_node.node` and reads
  `solid_node.node.ports` or `solid_node.node.timebase`
- **THEN** the read fails with a message naming
  `solid_node.motion.ports`, and no such module exists on disk

#### Scenario: A node class is still a node export

- **WHEN** a project runs `from solid_node.node import AssemblyNode`
  after the move
- **THEN** it receives the same class it received before, so only the
  names that answer a different question have left the package
