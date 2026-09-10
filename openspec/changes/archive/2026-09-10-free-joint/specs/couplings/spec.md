## MODIFIED Requirements

### Requirement: Each end of a relation resolves to one coordinate

The system SHALL resolve both ends of a relation to a coordinate. The
kinds of end SHALL be:

- a PORT or JOINT declared on the class stating the relation, resolving
  to that instance's own coordinate;
- a CHILD DECLARATION, resolving to the realized child's ONE joint's
  coordinate;
- a PATH REFERENCE — `anchor.turn`, `motion_works.cannon.turn`,
  `shoulder.art2.art3.wrist` — resolving to the coordinate of the
  realized descendant the path names;
- a `Driver` declaration, resolving to the driver's value, which SHALL
  be a SOURCE only;
- a DERIVED COORDINATE of the class.

A PATH REFERENCE SHALL be read segment by segment, and a COORDINATE at
its end SHALL occupy as many TRAILING SEGMENTS as the name the port
enumerator reports it under has dot-separated parts: one for a plain port
or the coordinate of a joint that owns one, and two for a coordinate of a
joint that owns several — `chassis.pose.roll` names the realized child
`chassis` and its coordinate `pose.roll`. Every segment before those
SHALL be a child the previous segment's class declares, as it is today.

A path that STOPS on a joint owning several coordinates — `chassis.pose`
— SHALL be refused at class definition naming the joint and listing its
coordinates, with the advice to name one, because a relation has one end.
A path naming a part that such a joint does not own — `chassis.pose.twist`
— SHALL be refused the same way, listing what it does own.

A child declaration named as an end SHALL mean the one joint of that
child's class. A child whose class declares NO joint, or more than one,
SHALL be refused at class definition, naming the child attribute, its
class, and the joints that class declares, with the advice to name the
coordinate. A child whose class declares exactly one joint, that joint
owning several coordinates, SHALL be refused the same way, listing that
joint's coordinates.

A relation SHALL bind either end through the SAME path an author's
assignment takes, whatever the coordinate's name is: a coordinate whose
name has more than one segment SHALL be bound through the joint that owns
it, and never by setting an attribute of that name on the node.

A `Driver` named as the DRIVEN end SHALL be refused at class
definition, naming the driver, because a driver's value belongs to the
bound snapshot and is set by `set_state`.

The ends SHALL resolve at realization, at the end of the instance's
construction and after its children are realized, since an end may be a
child or a descendant of one. Whatever the classes alone decide SHALL
be refused AT CLASS DEFINITION — an attribute no class along a path
declares, a node end with the wrong number of joints, a driver as a
driven end, a path through a repeated or list-held child, `ratio=` or
`offset=` given together with `law=` — and whatever depends on the
instance SHALL be refused AT REALIZATION, naming the relation, the path
as written, the node the walk stopped at and what that node declares.

#### Scenario: A node end is its one joint

- **WHEN** an assembly declares `power = TrainArbor(index=0)` and
  `centre = TrainArbor(index=1)`, `TrainArbor` declaring exactly one
  `Revolute` named `turn`, and states `power.drives(centre)`
- **THEN** the relation's ends are the two realized arbors' `turn`
  coordinates, and binding one places the other

#### Scenario: A node with two joints is refused

- **WHEN** a class body states `wrist.drives(tool)` where `tool`'s class
  declares two joints, or none
- **THEN** class definition raises naming the child attribute, its
  class and the joints it declares, with the advice to name the
  coordinate

#### Scenario: A path reaches a descendant's coordinate

- **WHEN** a root states `art3.drives(shoulder.art2.art3.wrist)`, three
  levels of declared children below it
- **THEN** the relation's driven end is the realized wrist coordinate
  of that descendant, and no intermediate class declared or forwarded a
  port for it

#### Scenario: A driver may not be driven

- **WHEN** a class body states `centre.turn.drives(some_driver)`
- **THEN** class definition raises naming the driver and saying its
  value belongs to the bound snapshot

#### Scenario: A path through a repeated child is refused

- **WHEN** a class declaring `units = Unit().repeat(count)` states
  `power.drives(units.turn)`
- **THEN** class definition raises naming the repeated declaration and
  advising that the relation be stated inside the repeated class

#### Scenario: A path that does not resolve on the instance fails at realization

- **WHEN** a path names a child of a class realized through an ordinary
  constructor that does not produce it
- **THEN** realization raises naming the relation, the path as written,
  the node the walk stopped at and what that node declares

#### Scenario: A path reaches one coordinate of a multi-coordinate joint

- **WHEN** a root declaring `chassis = Chassis()`, `Chassis` declaring
  `pose = Free()`, states `tilt.drives(chassis.pose.pitch)`
- **THEN** the relation's driven end is that realized chassis's
  `pose.pitch` coordinate, binding it places the chassis, and the other
  five coordinates are untouched

#### Scenario: A path stopping on a multi-coordinate joint is refused

- **WHEN** a class body states `tilt.drives(chassis.pose)`, or
  `tilt.drives(chassis.pose.twist)`
- **THEN** class definition raises naming the joint and listing the
  coordinates it owns, with the advice to name one of them

