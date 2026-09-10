## MODIFIED Requirements

### Requirement: One-coordinate joint declarations

The system SHALL provide the two one-coordinate lower pairs as
declarations exported from `solid_node.motion.joints`: `Revolute(axis,
at=(0, 0, 0), range=None, unit='deg')`, which turns a body about a line,
and `Prismatic(axis, at=(0, 0, 0), range=None, unit='mm')`, which slides
a body along one. A joint SHALL be declared as a class attribute of the
node it moves — an assembly or a leaf — and SHALL be stateless class
metadata shared by every instance of that class, exactly as a port
declaration is.

`axis` SHALL be a direction of three components and `at` an anchor point
of three components, both stated in the PARENT's frame: the frame the
parent's `render()` places the declaring node in. `axis` SHALL have no
named constants; it is written as a tuple. `at` SHALL default to the
origin of that frame, which is the case of a joint whose line passes
through the node's own placed origin. `range` SHALL be a `(lo, hi)` pair
in `unit`, and `unit` SHALL be the label the coordinate carries.

A `Prismatic`'s `at` SHALL NOT affect its placement — a translation along
a line is the same wherever the line is taken to pass — and SHALL be
carried as the declared position of the slide, for a reader and for a
later exporter.

A class's joints SHALL be enumerable off the class by name, without
constructing an instance, by an enumerator exported beside the joint
kinds. That enumeration SHALL be ORDERED, and its order SHALL be the
class's DECLARATION order: the joints of each base class before those of
the class itself, following the class's method resolution order from the
most basic class outward; within one class body, the order the joints
were written in; and a joint that REDECLARES an inherited one SHALL keep
the position of the declaration it redeclares while taking its own
arguments. That order is the order the joints compose in — see "Binding a
joint places the body" — so a reader of a class body, or a consumer
reading the class alone, can see how its freedoms stack without running
anything.

A joint declaration SHALL NOT be reported by that enumerator as a
parameter, a driver or a child, and a name SHALL NOT be declared as both
a joint and a port on one class: such a class SHALL be refused at class
definition naming the name and both declarations.

#### Scenario: A joint is declared where the body is

- **WHEN** a forearm class declares
  `elbow = Revolute(axis=(0, 0, 1), at=(0, 160, 68), range=(-135, 135), unit='deg')`
- **THEN** the class carries that joint by name with its axis, anchor,
  range and unit readable off the class, no instance was constructed,
  and the axis and anchor are understood in the frame its parent places
  it in

#### Scenario: Joints are enumerable

- **WHEN** a consumer enumerates the joints of a class declaring one
  `Revolute` and one `Prismatic`, and of a subclass that redeclares the
  `Revolute` with a different range
- **THEN** it receives both joints of the base class by name, and the
  subclass's redeclaration for the name it redeclares

#### Scenario: The enumeration is in declaration order

- **WHEN** a base class declares `a` then `b`, and a subclass declares
  `c` and redeclares `a` with a different anchor
- **THEN** the enumeration reads `a`, `b`, `c` — base before subclass,
  written order within a class body, and the redeclared `a` in the
  position the base gave it, carrying the subclass's anchor

#### Scenario: A joint and a port cannot share a name

- **WHEN** a class body declares `turn = Revolute(axis=(0, 0, 1))` and
  `turn = RotationalPort(unit='deg')`
- **THEN** class definition raises naming the class, the name and both
  declarations

### Requirement: Binding a joint places the body

The system SHALL move the node a joint is declared on when that joint's
coordinate is bound, composing the motion onto the node's rest
placement. Because motion composes innermost — in the node's own frame,
before the placement its parent's `render()` applied — the framework
SHALL carry the parent-frame `axis` and `at` into the node's own frame
by inverting that rest placement: the operations on the node that are
not motion, composed in order, with a rotation carrying the axis and the
full transform carrying the anchor. A joint's axis and anchor SHALL be
carried through the node's REST placement only, and never through the
motion another joint of the same node applied, so that a joint's line is
the line the parent's frame stated whatever the body's other freedoms are
doing. It SHALL then apply, as operations of that node:

- for a `Revolute`, `translate(-anchor)`, `rotate(value, axis)`,
  `translate(anchor)` in the node's own frame, in that order, the two
  centring translations OMITTED when every component of the local anchor
  is zero within `1e-9`, so a joint through the node's placed origin
  produces one rotation and nothing else;
- for a `Prismatic`, `translate(value * axis)` along the unit axis in
  the node's own frame, each component of the translation being a plain
  numeric `0` where the corresponding axis component is zero, rather
  than an expression multiplied by zero.

The carried axis and anchor SHALL be cleaned before use: a component
within `1e-9` of `0`, `1` or `-1` SHALL be snapped to that exact value,
so the inversion's floating-point residue never reaches the published
document as an axis of `(0, 1, 6e-17)`.

The operations SHALL be the framework's ordinary rotation and
translation objects, and the bound value SHALL be carried into them
unresolved, so a symbolic binding publishes a symbolic angle or offset
in the serialized document and the viewer evaluates it with the
expression math it already has. The axis and the anchor SHALL be plain
numbers by the time they are used.

The motion SHALL be applied at the moment of binding, so code that binds
a joint and then reads or measures the node sees the moved body. Binding
one joint twice SHALL leave one motion, the last: the framework SHALL
remove the operations the previous binding of that joint applied before
applying the new ones, tolerating operations a sweep has already dropped
from the node.

A joint's operations SHALL always be placed as motion — innermost,
before every rest operation — and marked as motion, WHATEVER lifecycle
phase is current, because the axis and anchor were carried into the
node's own frame and an operation appended after the rest placement would
be read in the parent's frame instead. Under a `simulate()` phase they
SHALL additionally be tagged with that assembly and swept before its next
run, exactly as a hand-written rotation there is — the assembly whose
`simulate()` bound it owns the tag, whether the joint is its own or a
child's. Bound outside any lifecycle phase — a test binding a joint
directly, a script posing a tree — they SHALL be untagged, so no sweep
removes them, and they SHALL persist until that same joint is bound
again.

**A node's motion SHALL compose innermost-first as the operations of its
declared joints in the enumerator's declaration order, each joint's own
operations contiguous and in the order that joint's placement produces
them, followed by every hand-written motion in the order it was applied.**
That is: the FIRST joint declared on the node's class is applied closest
to the body and the last declared is outermost, WHATEVER order the
joints' coordinates were bound in — by hand, by a wiring, by a relation,
or by several relations a solver reached in an order the class body does
not show — and whatever order they were bound in on a previous run. A
joint's operations SHALL be one unbroken run, so a joint whose placement
produces several operations occupies exactly one position in that order.
Hand-written motion SHALL sit OUTSIDE the whole joint block, keeping its
call order among itself.
Re-binding one joint of several SHALL return its operations to its own
position rather than moving them relative to its siblings, and the
composition after a sweep and a re-bind SHALL be the same as before it,
including when two independent assemblies each animate a different joint
of one node. A node's rest placement SHALL be unaffected: it is what the
whole motion block is composed inside.

A rest placement the framework cannot invert numerically SHALL fail by
name: when an operation of the node's rest placement carries a value
that is not a number, the framework SHALL raise naming the node, the
joint and that operation, rather than placing the body wrongly.

#### Scenario: A pivot away from the origin turns as Thor turns it

- **WHEN** a parent's `render()` places a forearm with
  `rotate(90, [1, 0, 0])` then `translate([0, 241.5, 68])`, the forearm
  declares `elbow = Revolute(axis=(0, 0, 1), at=(0, 160, 68),
  unit='deg')`, and the parent's `simulate()` binds `elbow` to `30`
- **THEN** the forearm's operations begin with
  `translate([0, 0, -81.5])`, `rotate(30, [0, 1, 0])`,
  `translate([0, 0, 81.5])` — the parent-frame axis and anchor carried
  into the forearm's own frame — followed by the two rest operations
  unchanged

#### Scenario: A joint through the placed origin needs no anchor

- **WHEN** an arbor placed by `translate([x, y, 0])` declares
  `turn = Revolute(axis=(0, 0, 1), at=(x, y, 0), unit='deg')` and is
  bound to an angle
- **THEN** its motion is one rotation about `[0, 0, 1]` in its own
  frame, with no centring translations, and the whole body turns at its
  bearing

#### Scenario: A joint bound outside any lifecycle phase still moves the body

- **WHEN** a test realizes a node, places it by hand and binds its joint
  with no `render()` or `simulate()` running
- **THEN** the joint's operations sit before the rest placement, marked
  as motion and tagged with no animator, the body is placed about the
  line the parent frame stated, and binding the joint again replaces
  them rather than adding to them

#### Scenario: A slide moves along its axis

- **WHEN** a carriage declaring
  `travel = Prismatic(axis=(1, 0, 0), range=(0, 200), unit='mm')` is
  bound to `120`
- **THEN** the carriage carries one translation of 120 along the unit
  axis expressed in its own frame, and its declared `at` changed
  nothing

#### Scenario: Two joints on one body compose in declaration order

- **WHEN** a class declares `pivot = Revolute(...)` at an anchor away
  from its placed origin and then `slide = Prismatic(...)` along an axis
  the pivot turns, and one assembly binds `pivot` then `slide` while
  another binds `slide` then `pivot`
- **THEN** both nodes carry the same operations in the same order — the
  pivot's run first, innermost, then the slide's — and both are placed
  by the same composed transform, the slide applied outside the pivot

#### Scenario: The order a solver reaches two joints in changes nothing

- **WHEN** two `Revolute`s declared on one body, `spin` then `orbit`,
  are both bound by relations from one shaft coordinate, and the two
  relation statements are then written in the other order
- **THEN** the body is placed identically in both cases, with `spin`
  applied inside `orbit`, and the composition is what the class body
  reads rather than what the solve order was

#### Scenario: Re-binding one joint of several keeps the order

- **WHEN** a node's first-declared and second-declared joints are bound
  in turn, and then the first-declared one is bound again to a new value
- **THEN** the node carries one motion per joint, the first-declared
  joint's operations are still innermost, and the composed transform is
  the same as if the two had been bound once in either order

#### Scenario: The bound value stays symbolic

- **WHEN** a joint is bound from an expression in the animation time and
  the tree is serialized with nothing bound
- **THEN** the published operation carries that expression as its angle,
  and `set_keyframe` makes it numeric and `clear_keyframe` symbolic
  again, exactly as a hand-written rotation does

#### Scenario: Re-binding is absolute

- **WHEN** an assembly binding a child's joint is simulated twice at the
  same instant, and once more at another
- **THEN** the child carries exactly one joint motion each time, for
  that instant, with nothing accumulated

#### Scenario: Hand-written motion and joint motion coexist

- **WHEN** an assembly's `simulate()` rotates a child by hand, then
  binds that child's joint, then translates the same child by hand again
- **THEN** the child's operations read: the joint's run first, innermost;
  then the hand-written rotation and the hand-written translation in the
  order they were called; then the child's rest placement — and all the
  motion is swept before the next run

#### Scenario: Inherited joints compose inside a subclass's own

- **WHEN** a base class declares `a` then `b`, a subclass declares `c`
  and redeclares `a` with a different anchor, and all three are bound
- **THEN** the body is placed with `a` innermost, then `b`, then `c`
  outermost, and `a` moves about the subclass's anchor

#### Scenario: Two assemblies animating one node keep each other's order

- **WHEN** one assembly binds the first-declared joint of a node, a
  second assembly binds its second-declared joint, and the first
  assembly is then walked again so its previous operations are swept and
  re-applied
- **THEN** the first-declared joint's operations are innermost of the
  second's, before and after the sweep, and each assembly's sweep
  removed only what it tagged

#### Scenario: A joint bound by the node's own simulate moves it

- **WHEN** an assembly declaring its own joint binds it in its own
  `simulate()` from a port it was handed
- **THEN** the assembly itself carries the joint motion, tagged with
  itself, and it is swept before its own next run

#### Scenario: A serialized node reads innermost-first

- **WHEN** a node carrying two bound joints and one hand-written motion
  is serialized
- **THEN** its published operations list reads, in order, the
  first-declared joint's operations, the second-declared joint's, the
  hand-written motion, and the rest placement, so a viewer applying them
  in list order reproduces the same pose the framework composed

#### Scenario: An unresolvable rest placement is refused

- **WHEN** a node whose rest placement carries a symbolic value has a
  joint bound
- **THEN** the framework raises naming the node, the joint and the
  operation it could not invert
