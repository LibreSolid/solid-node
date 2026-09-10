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

#### Scenario: A joint owning several coordinates enumerates each of them

- **WHEN** a consumer enumerates the declared ports of a class declaring
  one plain port and one joint that owns six coordinates
- **THEN** seven entries appear, the six under `<joint name>.<coordinate
  name>` with their own domains and units, no entry under the joint's
  bare name, and the enumeration constructed no instance
### Requirement: A coordinate may be wired down to a child declaration

The system SHALL let a parent hand one of its own coordinates — a
declared port, or the coordinate of a declared joint — to a child
declaration in its class body, by passing the declaration as the
argument of a keyword that names a port or a joint the child class
declares: `wheel = Arbor(index=index, turn=turn)`. A wiring keyword SHALL
be a name a class body can write as a keyword argument, which is what a
port, a derived coordinate and a joint owning ONE coordinate are named.

A joint owning SEVERAL coordinates SHALL NOT take part in a wiring, in
either role. Naming such a joint as a wiring SOURCE — passing it whole to
a child — SHALL be refused at class definition, naming the joint and
listing its coordinates and saying they are bound by assignment or by
relation, rather than being taken for a parameter of the child. Naming
one of its coordinates as a wiring TARGET, by the dotted name the port
enumerator reports it under, SHALL be refused the same way: a
non-identifier keyword is not a spelling this version promises, and such
a coordinate is reached by assignment on the instance
(`chassis.pose.roll = …`), as either end of a relation
(`chassis.pose.roll`), and by a driver or an expression. The framework
SHALL
record that wiring on the declaration and, on every `simulate()` of the
parent, SHALL bind the child's end from the parent's coordinate after
the parent's own `simulate()` has run and before the child is rendered,
applying the child end's declared scale as any binding does. A wiring
SHALL be rebound absolutely on every run, exactly as every other port
binding is, and SHALL carry a symbolic value through unresolved.

Binding a wiring whose source coordinate is unbound SHALL fail naming
the parent, the child and the coordinate, because an unbound source is a
wiring-order mistake rather than a zero to be assumed. A wiring whose
child end is a joint SHALL place the child's body exactly as any other
binding of that joint does.

A wired coordinate SHALL have exactly one binder. Binding the child end
of a wiring by hand — `self.wheel.turn = …` in the `simulate()` of the
parent that declared the wiring — SHALL be refused by name, naming the
parent, the child and the coordinate, and saying that the wiring already
binds it; otherwise the wiring bound at the end of that same phase would
silently overwrite the author's value. The refusal is the same rule a
later change states for a coordinate reached by two relations.

The direction of a wiring is downward only in this version: a parent
hands its coordinate to a child. Relating two coordinates that are not
in that relationship, in either direction and by path, is the subject of
a later change.

#### Scenario: One coordinate turns two children

- **WHEN** an arbor assembly declares `turn = Revolute(axis=(0, 0, 1),
  unit='deg')` and two children `wheel = Arbor(turn=turn)` and
  `rod = ArborRod(turn=turn)`, each declaring `turn` of its own, and the
  assembly's joint is bound to an angle
- **THEN** both children's `turn` read that angle after the assembly
  simulates, and the assembly's body carries the joint motion

#### Scenario: A wiring reaches two levels down

- **WHEN** a parent wires its port into a child that wires its own port
  of that name into a grandchild
- **THEN** the grandchild's port reads the parent's value after one
  enumeration of the tree, each level having bound its own child

#### Scenario: A wired scale converts

- **WHEN** a parent wires a rotational coordinate into a child port
  declaring a scale
- **THEN** the child's port holds the source value multiplied by that
  scale, as `connect()` gives

#### Scenario: A repeated child is wired per instance

- **WHEN** a declaration wiring a coordinate is repeated, so several
  identical children are realized from it
- **THEN** every realized child is bound on each run, and each carries
  its own value slot

#### Scenario: A wired coordinate has one binder

- **WHEN** the parent that declared `wheel = Arbor(turn=turn)` also
  binds `self.wheel.turn` by hand in its own `simulate()`
- **THEN** the binding is refused naming the parent, the child and
  `turn`, and saying the wiring binds it

#### Scenario: An unbound source is refused

- **WHEN** a parent wires a coordinate nothing bound into a child and
  the tree is enumerated
- **THEN** the binding raises naming the parent, the child and the
  coordinate

#### Scenario: A multi-coordinate joint cannot be wired whole

- **WHEN** a parent declaring `pose = Free()` passes it to a child as
  `Chassis(pose=pose)`
- **THEN** class definition raises naming the joint and listing its
  coordinates, saying they are bound by assignment or by relation, rather
  than passing it to the child's constructor as a parameter

#### Scenario: A coordinate of a multi-coordinate joint is not a wiring keyword

- **WHEN** a parent writes `chassis = Chassis(**{'pose.roll': roll})`,
  `Chassis` declaring `pose = Free()`
- **THEN** class definition raises naming the joint and listing its
  coordinates, saying they are bound by assignment or by relation, and no
  wiring is recorded
