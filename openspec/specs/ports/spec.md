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

### Requirement: The motion package holds what moves

The system SHALL provide a package `solid_node.motion` whose subject is
what moves and what drives what, laid out as three submodules so that an
import line names the kind of thing it brings in:

- `solid_node.motion.ports` — a value that flows between nodes: the port
  declarations, their bound value slot, the binding helper, the
  declaration enumerator, and the root's own time channel (`Time`, and
  the enumerator that reads a class's time declaration);
- `solid_node.motion.joints` — a pair that places a body: `Revolute` and
  `Prismatic`, their error kind and their enumerator (capability
  `joints`);
- `solid_node.motion.couplings` — a law between two coordinates: `Affine`,
  the relation and derived-coordinate kinds, their error kinds and their
  enumerators (capability `couplings`).

The package `__init__` SHALL export no name of its own and SHALL NOT
resolve a submodule's names as attributes of the package, so there is
exactly one import path for each name.

#### Scenario: The submodules hold their kinds

- **WHEN** a consumer imports `solid_node.motion.joints` and
  `solid_node.motion.couplings`
- **THEN** `Revolute` and `Prismatic` are read off the first and `Affine`
  off the second, and each module's docstring states its subject

#### Scenario: The package itself exports nothing

- **WHEN** a consumer reads any port, time-base, joint or coupling name
  off `solid_node.motion` directly
- **THEN** `AttributeError` is raised, so
  `from solid_node.motion import RotationalPort` fails at the import and
  the submodule path is the only path

### Requirement: A port takes part in a relation

The system SHALL give every port declaration the verb that states a
relation between two coordinates, so a class body may write
`elbow_pulley.turn.drives(elbow_belt.travel, ratio=pitch_arc(117))`. A
port SHALL be usable as either end of a relation, whether it is
declared on the class stating the relation or reached by path on a
declared descendant.

A relation SHALL bind its driven end through the ONE binding path a
port assignment and `connect()` already take, so the sink's declared
scale is applied exactly once and an unbound source is refused by the
same rule. The framework SHALL perform no unit conversion of its own on
behalf of a relation: what converts is the ratio or law the author
wrote.

A WIRING SHALL be solved together with the relations of the class that
declared it, as a forward-only relation carrying the identity law from
the parent's coordinate to the child's end: it SHALL bind once its
source coordinate holds a value, whether the author's `simulate()`
bound it or a relation of the same class solved it, rather than at a
fixed point before the relations run. The wiring's own rules are
otherwise unchanged: the child end's declared scale applies, an
unbound source when propagation has finished is refused by name, and
binding a wired child end by hand is refused.

A coordinate SHALL have exactly one binder during one enumeration of
the tree. A relation that would bind a coordinate an author's
`simulate()`, a wiring or another relation already bound SHALL be
refused by name.

Because a value slot keeps what was bound into it, an assembly SHALL
clear, at the start of its simulate phase and before the author's
`simulate()` runs, the value and the binder record of every coordinate
it bound through a wiring or a relation in its previous run, so that
each run's solve sees only values bound during the current walk. A
value the author's own code bound in an earlier run SHALL NOT be
cleared.

#### Scenario: A port drives a port

- **WHEN** an assembly states `pulley.turn.drives(belt.travel,
  ratio=1.2)` and `pulley.turn` is bound to `30`
- **THEN** `belt.travel` holds `36`, in the belt's own unit

#### Scenario: A relation into a scaled port converts once

- **WHEN** a relation drives a port declaring a scale
- **THEN** the port holds the relation's result multiplied by that
  scale, exactly as `connect()` gives, and nothing else was converted

#### Scenario: A wiring binds after the relation that solves its source

- **WHEN** an assembly's relation solves its own joint's coordinate and
  that same class wires that coordinate down into two children
- **THEN** both children are bound from the solved value in the same
  run, and the wiring did not refuse an unbound source

#### Scenario: A wiring is cleared and rebound each run

- **WHEN** the same assembly is enumerated at three successive instants
- **THEN** each run cleared what it bound in the previous one before
  the author's `simulate()` ran, and each child holds the current
  instant's value with nothing refused as doubly bound

#### Scenario: A wiring and a relation cannot both bind one coordinate

- **WHEN** a class wires its coordinate into a child's port and also
  states a relation driving that same port
- **THEN** solving raises naming the wiring and the relation as the two
  binders, and the wiring's own hand-binding refusal is unchanged

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

