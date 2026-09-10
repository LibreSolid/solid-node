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
instantiating behavior. That enumeration SHALL also report the
coordinates of every joint the class declares, so a consumer of a node's
connection points sees them without knowing what a joint is, AND every
derived coordinate the class
declares — a linear formula over other coordinates — under its own
name, carrying the domain and unit its terms share.

A joint's coordinates SHALL be reported under the joint's naming rule:
under the JOINT'S OWN NAME when the joint owns one, and under
`<joint name>.<coordinate name>` for each when it owns several. An
enumerated port name is therefore NOT guaranteed to be a Python
identifier, and a consumer SHALL reach a coordinate by the name the
enumerator reports rather than by attribute access on the node.

A NAME THE ENUMERATOR REPORTS SHALL BE A NAME THE FRAMEWORK CAN READ
BACK. The system SHALL export from `solid_node.motion.ports` a matched
pair over those names: `set_coordinate(node, name, value)`, which binds
the coordinate through the one binding path every binder takes, and
`get_coordinate(node, name)`, which SHALL return that coordinate's bound
value slot — the same slot reading the coordinate on the node yields, so
a slot nothing has bound reads its value as `None`. Both SHALL accept a
name of one segment and a name of several alike. A name the enumerator
does NOT report SHALL be refused by `get_coordinate`, naming the node,
the name asked for and the names the enumerator does report, rather than
answered with `None`; the membership test SHALL be against the
enumeration and not against attribute lookup, so a declared parameter
whose name resembles a coordinate's cannot answer for one.

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

#### Scenario: A joint's coordinate is among the declared ports

- **WHEN** a consumer enumerates the declared ports of a class that
  declares one port and one joint
- **THEN** both appear by name, the joint's entry carrying the joint's
  domain and unit, and the enumeration constructed no instance

#### Scenario: A derived coordinate is among the declared ports

- **WHEN** a consumer enumerates the declared ports of a class that
  declares two joints and `relative = a - b` over them
- **THEN** three entries appear by name, `relative` carrying the domain
  and unit its terms share, and the enumeration constructed no instance

#### Scenario: Every reported name reads back

- **WHEN** a consumer iterates `declared_ports` of a realized node
  declaring a plain port, a one-coordinate joint, a derived coordinate
  and a joint owning six, and calls `get_coordinate(node, name)` for each
- **THEN** every call yields that coordinate's value slot, carrying its
  domain and unit, and none of them raises

#### Scenario: A dotted name reads back what it was bound to

- **WHEN** `set_coordinate(node, 'pose.roll', 12.0)` is called and then
  `get_coordinate(node, 'pose.roll')`
- **THEN** the slot returned reads `12.0`, and it is the same slot
  `node.pose.roll` yields

#### Scenario: An unbound coordinate reads as a slot with no value

- **WHEN** `get_coordinate(node, 'pose.x')` is called on a node whose
  `pose.x` nothing has bound
- **THEN** the slot is returned and its value is `None`, and the name is
  still reported by the enumerator

#### Scenario: A name the enumerator does not report is refused

- **WHEN** `get_coordinate(node, 'bore')` is called, `bore` being a
  declared parameter, or `get_coordinate(node, 'pose.twist')` for a
  coordinate no joint owns
- **THEN** it raises naming the node, the name asked for and the names
  the enumerator does report, and no value is returned

#### Scenario: A joint owning several coordinates enumerates each of them

- **WHEN** a consumer enumerates the declared ports of a class declaring
  one plain port and one joint that owns six coordinates
- **THEN** seven entries appear, the six under `<joint name>.<coordinate
  name>` with their own domains and units, no entry under the joint's
  bare name, and the enumeration constructed no instance
