## ADDED Requirements

### Requirement: A joint takes part in a relation

The system SHALL give every joint declaration the verb that states a
relation between two coordinates, so a class body may write
`anchor.turn.drives(pendulum.swing)` and
`centre.turn.drives(motion_works.cannon.turn, offset=hand_setting)`. A
joint named in a relation SHALL stand for its one coordinate, exactly
as reading the joint on an instance yields that coordinate.

A NODE named as an end of a relation SHALL stand for the ONE joint of
that node's class: an arbor is one body turning at one bearing, and
`power.drives(centre)` between two such nodes SHALL relate their
coordinates. A node whose class declares no joint, or more than one,
SHALL be refused at class definition naming the node, its class and the
joints that class declares, with the advice to name the coordinate.

A joint's coordinate bound by a relation SHALL place the body exactly
as a coordinate bound by hand does: the same operations composed onto
the same rest placement, carrying the value unresolved so a symbolic
value publishes a symbolic angle or offset, tagged with the assembly
whose relations were being solved, and swept before that assembly's
next run. A declared `range` SHALL refuse a plain numeric value a
relation would bind outside it, exactly as it refuses one bound by
hand.

#### Scenario: A joint drives a joint

- **WHEN** an assembly states `anchor.turn.drives(pendulum.swing)` and
  binds `anchor.turn` in its `simulate()`
- **THEN** the pendulum's joint holds the same value, its body is
  placed about its own axis and anchor, and the motion is tagged with
  the assembly that solved the relation

#### Scenario: A node stands for its one joint

- **WHEN** an assembly states `power.drives(centre, law=going_train)`
  between two children whose class declares exactly one `Revolute`
- **THEN** the relation relates the two realized arbors' coordinates,
  and binding either places the other's body

#### Scenario: A node with the wrong number of joints is refused

- **WHEN** a class body names as an end a child whose class declares
  two joints, or none
- **THEN** class definition raises naming the child, its class and the
  joints it declares

#### Scenario: A relation past a joint's range is refused

- **WHEN** a relation would bind a joint declaring `range=(-135, 135)`
  to the plain number `170`
- **THEN** the binding raises the joint range error naming the node's
  path, the joint, the value, the range and the unit, and the node
  carries no motion from it

#### Scenario: A relation into a joint stays symbolic

- **WHEN** a joint is driven through an affine relation from a driver
  read and the tree is serialized with nothing bound
- **THEN** the published operation carries the expression the relation
  built, and `set_keyframe` makes it numeric
