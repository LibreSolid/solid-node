## ADDED Requirements

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

A class's joints SHALL be enumerable off the class by name, base-first
with a subclass redeclaration winning, without constructing an instance,
by an enumerator exported beside the joint kinds. A joint declaration
SHALL NOT be reported by that enumerator as a parameter, a driver or a
child, and a name SHALL NOT be declared as both a joint and a port on
one class: such a class SHALL be refused at class definition naming the
name and both declarations.

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

#### Scenario: A joint and a port cannot share a name

- **WHEN** a class body declares `turn = Revolute(axis=(0, 0, 1))` and
  `turn = RotationalPort(unit='deg')`
- **THEN** class definition raises naming the class, the name and both
  declarations

### Requirement: A joint owns one coordinate, and that coordinate is a port

The system SHALL give every joint exactly one coordinate, which SHALL be
a port: rotational for a `Revolute`, translational for a `Prismatic`,
carrying the joint's `unit`. Read on an instance, a joint SHALL be that
coordinate's bound value slot — the same per-instance slot a declared
port of the same kind yields — so two instances of one class never share
a joint value and an unbound coordinate reads as unbound rather than as
zero. Assigning to a joint on an instance SHALL bind its coordinate
exactly as assigning to a port binds one: from a plain number, a
symbolic expression, a driver read, or another bound port, through the
one binding path `connect()` also uses. A joint SHALL be a data
descriptor, so an assignment can never replace the declaration with a
raw attribute.

The port enumerator SHALL report a joint's coordinate under the joint's
name alongside the class's plain ports, so every consumer that
enumerates a node's connection points — tooling, wiring, later
simulation surfaces — sees a joint's coordinate without knowing about
joints. A joint's coordinate SHALL NOT declare a scale or a direction
marker: what a joint's value means is stated by its `unit`, and a
conversion between two coordinates is a relation, not a property of the
joint.

#### Scenario: Reading a joint yields its coordinate

- **WHEN** a node declaring `elbow = Revolute(axis=(0, 0, 1), unit='deg')`
  is realized and `node.elbow` is read
- **THEN** the read yields a bound port slot of rotational domain whose
  unit is `'deg'` and whose value is unbound, and a second instance of
  the class reads its own slot

#### Scenario: Binding the joint binds the coordinate

- **WHEN** a parent's `simulate()` executes `self.forearm.elbow = 30.0`,
  and another assembly instead binds the same joint from a driver read
- **THEN** in both cases `self.forearm.elbow.value` reads what was
  bound, and the binding went through the same path a port assignment
  takes

#### Scenario: A joint's coordinate enumerates as a port

- **WHEN** a consumer enumerates the declared ports of a class declaring
  one `RotationalPort` and one `Revolute`
- **THEN** it receives two entries by name, the joint's carrying the
  rotational domain and the joint's unit

### Requirement: Binding a joint places the body

The system SHALL move the node a joint is declared on when that joint's
coordinate is bound, composing the motion onto the node's rest
placement. Because motion composes innermost — in the node's own frame,
before the placement its parent's `render()` applied — the framework
SHALL carry the parent-frame `axis` and `at` into the node's own frame
by inverting that rest placement: the operations on the node that are
not motion, composed in order, with a rotation carrying the axis and the
full transform carrying the anchor. It SHALL then apply, as operations
of that node:

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

A joint's operations SHALL always be placed as motion — innermost, after
the node's existing motion and before every rest operation — and marked
as motion, WHATEVER lifecycle phase is current, because the axis and
anchor were carried into the node's own frame and an operation appended
after the rest placement would be read in the parent's frame instead.
Under a `simulate()` phase they SHALL additionally be tagged with that
assembly and swept before its next run, exactly as a hand-written
rotation there is — the assembly whose `simulate()` bound it owns the
tag, whether the joint is its own or a child's. Bound outside any
lifecycle phase — a test binding a joint directly, a script posing a
tree — they SHALL be untagged, so no sweep removes them, and they SHALL
persist until that same joint is bound again.

Joint motion and hand-written motion SHALL coexist on one node: both are
motion, and they apply in the order they were applied. A node's rest
placement SHALL be unaffected: it is what the joint motion is composed
inside.

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

- **WHEN** an assembly's `simulate()` binds a child's joint and also
  rotates the same child by hand
- **THEN** the child carries both motions, in the order they were
  applied, and both are swept before the next run

#### Scenario: A joint bound by the node's own simulate moves it

- **WHEN** an assembly declaring its own joint binds it in its own
  `simulate()` from a port it was handed
- **THEN** the assembly itself carries the joint motion, tagged with
  itself, and it is swept before its own next run

#### Scenario: An unresolvable rest placement is refused

- **WHEN** a node whose rest placement carries a symbolic value has a
  joint bound
- **THEN** the framework raises naming the node, the joint and the
  operation it could not invert

### Requirement: Joint arguments resolve against the instance at realization

The system SHALL resolve a joint's `axis`, `at` and `range` for each
realized instance of the declaring class, at realization, once its
parameters are resolved. Each component MAY be a plain number, a
declared-parameter token, or a derived formula over such tokens,
resolved against that instance's values exactly as a child
declaration's arguments are; `axis`, `at` or `range` as a whole MAY
instead be a callable of one argument, which the framework SHALL call
with the realized node and which SHALL return the components as plain
numbers — the case of a position that comes out of a library object the
node builds from its parameters rather than out of a formula.

Resolved joint arguments SHALL NOT enter the node's identity: a joint
states where a body may move, not what geometry is built, and two
instances differing only in a joint argument SHALL share their
artifacts.

An argument that cannot resolve SHALL fail at realization, naming the
class, the joint and the argument: a token that is not a declared
parameter of the class, an `axis` or `at` that is not three numbers, an
`axis` of zero length, or a `range` that is not a `(lo, hi)` pair with
`lo <= hi`.

#### Scenario: A joint sized by a parameter

- **WHEN** a class declares `reach = Length(160.0)` and
  `elbow = Revolute(axis=(0, 0, 1), at=(0, reach, 68), unit='deg')`, and
  is realized with `reach=180.0`
- **THEN** that instance's joint anchor is `(0, 180.0, 68)` and another
  instance realized with the default is anchored at `(0, 160.0, 68)`

#### Scenario: A joint anchored on a built position

- **WHEN** an arbor class declares
  `turn = Revolute(axis=(0, 0, 1), at=lambda node: node.built.arbors[node.index].bearing_position, unit='deg')`
- **THEN** each realized arbor's anchor is the bearing position its own
  built movement gives for its own index, resolved once at realization

#### Scenario: An unresolvable argument fails by name

- **WHEN** a class declares a joint whose anchor names a token the class
  does not declare, or whose axis is `(0, 0)`, or whose axis is
  `(0, 0, 0)`, or whose range is `(10, 0)`
- **THEN** realization raises naming the class, the joint and the
  argument at fault, before any child of the instance is realized

#### Scenario: A joint argument is not identity

- **WHEN** two instances of one leaf class are realized with equal
  declared parameters and joint anchors that differ
- **THEN** both carry the same `uniq_id` and one artifact set, and each
  moves about its own anchor

### Requirement: A declared range refuses a binding outside it

The system SHALL refuse, at the moment of binding, a plain numeric value
outside a joint's declared `range`, raising an error of a kind exported
from the joints module and naming the joint, the value, the range, the
unit and the node — by its path in the tree when the node is linked
under a root, and otherwise by its name and class, because a node bound
before any walker linked it has no path to name. A binding that is not a plain
number — a symbolic expression, a driver token — SHALL NOT be checked at
bind time, because its value is not known there; a joint with no
declared range SHALL accept any binding. A `Driver` bound to a joint
SHALL keep its own declared range, which is presentation metadata and
never a clamp, and the joint's range SHALL apply to the value that
reaches the joint.

#### Scenario: An out-of-range angle is refused by name

- **WHEN** a joint declaring `range=(-135, 135)` in degrees is bound to
  `170`
- **THEN** the binding raises an error naming the node's path, the
  joint, `170`, the range and `deg`, and the node carries no motion from
  that binding

#### Scenario: A symbolic binding is not checked

- **WHEN** the same joint is bound from an expression in the animation
  time whose values pass outside the range
- **THEN** the binding succeeds and publishes the expression, because
  the value is not known at bind time

#### Scenario: A binding inside the range is placed

- **WHEN** the same joint is bound to `-135` and then to `135`
- **THEN** both bindings succeed, the bounds being inclusive
