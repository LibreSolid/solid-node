## ADDED Requirements

### Requirement: A driver states a relation to a coordinate

The system SHALL give every `Driver` declaration the verb that states a
relation between two coordinates, so a root class body may write
`art3.drives(shoulder.art2.art3.elbow)` and a driver reach a joint or a
port at any depth without every class between them declaring and
forwarding one. The driver's value SHALL be what reaches the relation:
the bound number under `set_state`, the test runner and the stepped
simulation, and the driver's symbolic token when nothing is bound, so
the relation publishes an expression in that driver's qualified id.

A driver SHALL be a SOURCE only. A `Driver` named as the DRIVEN end of
a relation SHALL be refused at class definition, naming the driver and
saying that its value belongs to the bound snapshot and is set with
`set_state`, which is the rule an assignment to a driver already
states.

A driver's declared range SHALL remain presentation metadata and never
a clamp; a relation SHALL NOT read it and SHALL NOT check against it.
A range declared by a joint the relation drives SHALL apply to the
value that reaches that joint, exactly as it does for a hand binding.

Reaching a driver sideways — reading one off a child declaration in a
class body — SHALL be refused, because a driver is addressed by the
qualified id its position in the tree gives it and a second address for
one value is what that qualification exists to prevent.

#### Scenario: A driver reaches a deep joint

- **WHEN** a root declares `art3 = Driver(...)`, three levels of
  children below it, and states
  `art3.drives(shoulder.art2.art3.elbow)`
- **THEN** the elbow coordinate holds the driver's value on every run,
  the forearm is placed by it, and no intermediate class declares a
  port for it

#### Scenario: A driver drives through a ratio

- **WHEN** a root states `art1.drives(base.pinion.turn, ratio=5.0)` and
  binds `art1` to `12` with `set_state`
- **THEN** the pinion's coordinate reads `60`

#### Scenario: A driver's symbolic read rides through a relation

- **WHEN** the same tree is serialized with nothing bound
- **THEN** the pinion's operation carries an expression in the driver's
  qualified id, and `set_state` makes it numeric

#### Scenario: A driver cannot be driven

- **WHEN** a class body states `some_port.drives(art3)` where `art3` is
  a `Driver` declaration
- **THEN** class definition raises naming the driver and pointing at
  `set_state`

#### Scenario: A driver read off a declaration is refused

- **WHEN** a class body reads a `Driver` off a child declaration
- **THEN** class definition raises, naming the declaration and the
  driver, and the driver's qualified id remains its one address
