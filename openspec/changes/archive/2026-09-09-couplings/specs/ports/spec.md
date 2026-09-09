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
coordinate of every joint the class declares, under the joint's name,
so a consumer of a node's connection points sees a joint's coordinate
without knowing what a joint is, AND every derived coordinate the class
declares — a linear formula over other coordinates — under its own
name, carrying the domain and unit its terms share.

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

## ADDED Requirements

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
