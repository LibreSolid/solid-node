## ADDED Requirements

### Requirement: A free joint owns six coordinates and floats a body

The system SHALL provide `Free(at=(0, 0, 0), angle_unit='deg',
length_unit='mm')`, exported from `solid_node.motion.joints` beside the
one-coordinate pairs, for a body with no parent to be jointed to: a
walking robot's chassis, a floating platform, anything whose pose against
the world is stated rather than constrained. It SHALL be declared as a
class attribute of the node it moves, exactly as every other joint is,
and SHALL occupy ONE position in the declaration order the joints
enumerator reports.

A `Free` SHALL own SIX coordinates: `roll`, `pitch` and `yaw`, each a
ROTATIONAL coordinate carrying `angle_unit`, and `x`, `y` and `z`, each a
TRANSLATIONAL coordinate carrying `length_unit`. Read on an instance, a
`Free` SHALL yield a view of those six from which each coordinate is
reachable by its own name, so `chassis.pose.roll` is that coordinate's
bound value slot exactly as `wheel.turn` is a `Revolute`'s. Assigning to
one of the six SHALL bind it through the one binding path every other
coordinate is bound through, and SHALL place the body. Assigning to the
`Free` itself SHALL be refused, naming the node, the joint and the six
coordinates.

A `Free` SHALL take NO `axis`: a free body turns about the three
directions of the frame it is stated in, which are not an author's
choice. A `Free` SHALL take NO `range`: a floating body has no travel to
bound. `at` SHALL mean what it means on every other joint — a point of
three components in the PARENT's frame, defaulting to that frame's
origin, resolved against the instance at realization — and SHALL be the
point the three rotations pass through.

Each of the six SHALL be an ORDINARY coordinate in every other respect:
reported by the port enumerator, bindable by hand, nameable as either end
of `drives`, readable by a driver or an expression, and published as an
ordinary operation value. A `Free` coordinate SHALL differ from any other
coordinate only in the NAME it is reached by, and in that it SHALL NOT be
reachable as a wiring keyword; see "A joint owns one or more coordinates,
and each is a port".

#### Scenario: A floating body is declared with one joint

- **WHEN** a chassis class declares
  `pose = Free(angle_unit='deg', length_unit='mm')`
- **THEN** the class carries that joint by name, the joints enumerator
  reports it as one entry, the port enumerator reports six coordinates,
  and no instance was constructed

#### Scenario: The six coordinates are read and bound by name

- **WHEN** a realized chassis binds `chassis.pose.roll = 12.0` and
  `chassis.pose.z = 165.0`
- **THEN** `chassis.pose.roll.value` reads `12.0` with the rotational
  domain and the declared angle unit, `chassis.pose.z.value` reads
  `165.0` with the translational domain and the declared length unit,
  `chassis.pose.x.value` is unbound, and a second instance reads its own
  six slots

#### Scenario: Binding the joint as a whole is refused

- **WHEN** a `simulate()` executes `self.chassis.pose = 12.0`
- **THEN** the binding is refused naming the node, the joint and the six
  coordinates, and the node carries no motion from it

#### Scenario: A free joint declares no axis and no range

- **WHEN** a class body writes `Free(axis=(0, 0, 1))` or
  `Free(range=(-10, 10))`
- **THEN** the declaration is refused, because a free body turns about
  three directions and has no travel to bound

### Requirement: A free joint places a floating body by a fixed composition

The system SHALL place the body a `Free` is declared on from the values
of its six coordinates, composing INNERMOST FIRST, about the carried
anchor:

`R(roll, x̂) · R(pitch, ŷ) · R(yaw, ẑ) · T(x, y, z)`

read as an APPLICATION order — the roll closest to the body, the
translation outermost — which as a matrix product acting on a point of
the body is `T(x, y, z) · R(yaw, ẑ) · R(pitch, ŷ) · R(roll, x̂)`. That
order SHALL be fixed by this contract and SHALL NOT be an argument of the
declaration.

The three directions x̂, ŷ and ẑ SHALL be the unit directions of the
PARENT's frame, carried into the node's own frame through the SAME single
inversion of the rest placement the anchor rides, and snapped to exact
`0`, `1` or `-1` within `1e-9` as every carried axis is. The three
rotations SHALL therefore be about FIXED directions rather than about the
body's own turning axes, which is the extrinsic x-y-z sequence — the same
rotation the aircraft convention states as intrinsic yaw, then pitch,
then roll.

The operations SHALL be, in list order:

- `translate(-anchor)`, OMITTED when every component of the carried
  anchor is zero within `1e-9`, exactly as a `Revolute`'s centring
  translation is;
- `rotate(roll, x̂)`, `rotate(pitch, ŷ)`, `rotate(yaw, ẑ)`, each OMITTED
  when its coordinate is unbound;
- `translate(anchor)`, omitted with its pair;
- `translate([x, y, z])`, OMITTED when all three translational
  coordinates are unbound, and otherwise carrying a plain numeric `0` for
  each component whose coordinate is unbound, rather than an expression
  multiplied by zero.

An UNBOUND coordinate of a `Free` SHALL contribute NO motion — no
rotation, and a plain zero offset — while still READING as unbound. That
is the same rule every joint already obeys, stated per coordinate instead
of per joint: an unbound coordinate places nothing. It SHALL NOT make the
coordinate read as zero, and the port enumerator SHALL still report it as
an unbound port.

Binding ANY of the six SHALL re-place the whole joint from the values the
six then hold, dropping the operations the previous placement applied, so
the composition never depends on the order the six were bound in. The
whole placement SHALL be ONE contiguous run at the joint's own
declaration slot, so a `Free` composes with a `Revolute`, a `Prismatic`
or an `Orbit` on the same body by declaration order like any other joint.

#### Scenario: The composition is the one a floating chassis hand-inverts

- **WHEN** a body declaring `pose = Free()` is bound at a set of poses
  including a quarter turn in pitch, and its composed world matrix is
  compared with the product `T(x, y, z) · Rz(yaw) · Ry(pitch) · Rx(roll)`
- **THEN** the two agree at every pose within the tolerance the fixture
  states, and the inverse of that product returns a point of the world to
  the body's frame

#### Scenario: Two of six coordinates left unbound place nothing

- **WHEN** a body binds `roll`, `pitch`, `yaw` and `z` and leaves `x` and
  `y` unbound
- **THEN** the placement carries no sideways offset, `pose.x.value` and
  `pose.y.value` read as unbound, the published translation carries the
  plain `0` in those two components, and the composed matrix equals the
  same pose with `x` and `y` bound to zero

#### Scenario: The binding order of the six changes nothing

- **WHEN** one body binds the six in declaration order and another binds
  them in the reverse order, from the same values
- **THEN** both carry the same operations in the same order and the same
  composed matrix

#### Scenario: A free joint composes with a sibling joint by declaration order

- **WHEN** a class declares `pose = Free()` then `lift = Prismatic(...)`,
  and another declares them the other way round, both bound to the same
  values
- **THEN** each body is placed with the first-declared joint's operations
  innermost, the free joint's operations one unbroken run, and the two
  bodies land in different places

#### Scenario: An anchored free joint turns about its anchor

- **WHEN** a body placed by its parent away from the origin declares
  `pose = Free(at=<a point of the parent's frame>)` and binds `yaw`
- **THEN** the body turns about the line through that point, the two
  centring translations appear in the run, and a `Free` at the default
  anchor on the same body produces neither

#### Scenario: A free joint's placement stays symbolic

- **WHEN** the six coordinates are bound from expressions in the
  animation time and the tree is serialized with nothing keyframed
- **THEN** the published operations are three ordinary rotations and one
  ordinary translation carrying those expressions unresolved, the
  document gains no new key and no new operation kind, and `set_keyframe`
  makes them numeric

## MODIFIED Requirements

### Requirement: Binding a joint places the body

The system SHALL move the node a joint is declared on when that joint's
coordinate is bound, composing the motion onto the node's rest
placement. Because motion composes innermost — in the node's own frame,
before the placement its parent's `render()` applied — the framework
SHALL carry the parent-frame `axis` and `at` into the node's own frame
by inverting that rest placement: the operations on the node that are
not motion, composed in order, with a rotation carrying the axis and the
full transform carrying the anchor. A joint declaring further
parent-frame POINTS — an `Orbit`'s `carries` — SHALL have each of them
carried the same way the anchor is, through the same single inversion,
and a joint turning about several parent-frame DIRECTIONS — a `Free`'s
three — SHALL have each of them carried the way the axis is, through that
same single inversion. A
joint's axis, anchor and carried points SHALL be carried through the
node's REST placement only, and never through the motion another joint of
the same node applied, so that a joint's line is the line the parent's
frame stated whatever the body's other freedoms are doing. It SHALL then
apply, as operations of that node:

- for a `Revolute`, `translate(-anchor)`, `rotate(value, axis)`,
  `translate(anchor)` in the node's own frame, in that order, the two
  centring translations OMITTED when every component of the local anchor
  is zero within `1e-9`, so a joint through the node's placed origin
  produces one rotation and nothing else;
- for a `Prismatic`, `translate(value * axis)` along the unit axis in
  the node's own frame, each component of the translation being a plain
  numeric `0` where the corresponding axis component is zero, rather
  than an expression multiplied by zero;
- for an `Orbit`, ONE translation in the node's own frame, being the
  displacement the carried point undergoes when it is turned by the bound
  value about the carried line. Writing `n` for the carried unit axis,
  `a` for the carried anchor, `p` for the carried point, `v` for the
  component of `p - a` across the line and `b` for `n` crossed with `v`,
  that displacement SHALL be `(cos(value) - 1) * v + sin(value) * b`,
  computed in DEGREES through the framework's own trigonometry so a
  symbolic value publishes an expression the viewer already evaluates.
  Each component whose `v` and `b` entries are both zero within `1e-9`
  SHALL be a plain numeric `0`, for the reason a `Prismatic`'s are. The
  operation SHALL carry no rotation at all: the composed transform's
  rotation block SHALL be unchanged by the binding, at every value, which
  is what it means for an orbit to carry a body without turning it;
- for a `Free`, up to SIX operations in the node's own frame — the
  centring pair around three rotations about the carried unit directions,
  and one translation outermost — as "A free joint places a floating body
  by a fixed composition" states.

A joint owning SEVERAL coordinates SHALL be re-placed in full whenever
ANY of them is bound, from the values its coordinates then hold, so its
composition never depends on the order they were bound in; an unbound
coordinate of such a joint SHALL contribute no motion while still reading
as unbound.

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
produces several operations occupies exactly one position in that order,
and a joint whose placement produces ONE operation occupies exactly one
position in it too. A joint owning several coordinates SHALL occupy ONE
position as well, however many operations its placement produces and
however many of its coordinates are bound. Hand-written motion SHALL sit
OUTSIDE the whole joint block, keeping its call order among itself.
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

#### Scenario: A carried body moves without turning

- **WHEN** a disk placed away from the parent's origin declares
  `orbit = Orbit(axis=(0, 0, 1), unit='deg')` and the coordinate is bound
  to a series of angles
- **THEN** the disk carries exactly one translation at each binding, the
  composed transform's rotation block is unchanged from the rest
  placement's at every one of them, and the disk's placed origin lies at
  each angle where turning it about the parent's axis would put it

#### Scenario: An orbit composes with a turn of the same body

- **WHEN** a disk declares `spin = Revolute(...)` about its own centre
  and then `orbit = Orbit(...)` about the parent's axis, and both
  coordinates are bound in either order
- **THEN** the spin's run is innermost and the orbit's single
  translation outermost, the body spins about its own moving centre, and
  the pose is the same whichever order the two were bound in

#### Scenario: The bound value stays symbolic

- **WHEN** a joint is bound from an expression in the animation time and
  the tree is serialized with nothing bound
- **THEN** the published operation carries that expression as its angle,
  and `set_keyframe` makes it numeric and `clear_keyframe` symbolic
  again, exactly as a hand-written rotation does

#### Scenario: An orbit's translation stays symbolic

- **WHEN** an orbit is bound from an expression in the animation time and
  the tree is serialized with nothing bound
- **THEN** its published translation carries the two trigonometric
  expressions in that value, in degrees, through the same builtins the
  viewer already evaluates, with a plain numeric zero in any component
  the circle does not reach; and `set_keyframe` makes them numeric and
  `clear_keyframe` symbolic again

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

#### Scenario: A six-coordinate joint is one unbroken run at its own slot

- **WHEN** a class declares `slide = Prismatic(...)`, `pose = Free()` and
  `spin = Revolute(...)` at an off-origin anchor, and an assembly binds
  their coordinates in a scrambled order with a hand-written rotation in
  between
- **THEN** the node's operations read the slide, then every operation the
  free joint placed unbroken, then the revolute's three, then the
  hand-written rotation, then the rest placement — and re-binding one
  coordinate of the free joint returns its whole run to that same
  position

### Requirement: Joint arguments resolve against the instance at realization

The system SHALL resolve a joint's `axis`, `at`, `range` and, where the
joint declares one, its further points such as an `Orbit`'s `carries`,
for each realized instance of the declaring class, at realization, once
its parameters are resolved. Each component MAY be a plain number, a
declared-parameter token, or a derived formula over such tokens,
resolved against that instance's values exactly as a child
declaration's arguments are; `axis`, `at`, `carries` or `range` as a
whole MAY instead be a callable of one argument, which the framework
SHALL call with the realized node and which SHALL return the components
as plain numbers — the case of a position that comes out of a library
object the node builds from its parameters rather than out of a formula.
An `Orbit`'s `carries` left unstated SHALL resolve to nothing at
realization: it names the node's own placed origin, which is not known
until the node has been placed, and is settled at binding instead. A
`Free`'s `at` SHALL resolve by exactly the same path as every other
joint's; a `Free` declares no `axis` and no `range`, so it resolves
neither.

Resolved joint arguments SHALL NOT enter the node's identity: a joint
states where a body may move, not what geometry is built, and two
instances differing only in a joint argument SHALL share their
artifacts.

An argument that cannot resolve SHALL fail at realization, naming the
class, the joint and the argument: a token that is not a declared
parameter of the class, an `axis`, `at` or `carries` that is not three
numbers, an `axis` of zero length, or a `range` that is not a `(lo, hi)`
pair with `lo <= hi`.

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
  `(0, 0, 0)`, or whose range is `(10, 0)`, or an orbit whose `carries`
  is two components
- **THEN** realization raises naming the class, the joint and the
  argument at fault, before any child of the instance is realized

#### Scenario: A joint argument is not identity

- **WHEN** two instances of one leaf class are realized with equal
  declared parameters and joint anchors that differ
- **THEN** both carry the same `uniq_id` and one artifact set, and each
  moves about its own anchor

### Requirement: A joint takes part in a relation

The system SHALL give every joint declaration the verb that states a
relation between two coordinates, so a class body may write
`anchor.turn.drives(pendulum.swing)` and
`centre.turn.drives(motion_works.cannon.turn, offset=hand_setting)`. A
joint owning ONE coordinate and named in a relation SHALL stand for that
coordinate, exactly as reading the joint on an instance yields it.

A joint owning SEVERAL coordinates SHALL NOT stand for any of them: named
as an end of a relation, by its own name or at the end of a path, it
SHALL be refused at class definition naming the joint and listing its
coordinates, with the advice to name one. A relation has one end and such
a joint is several, so there is nothing to choose from silently.

Each coordinate of such a joint SHALL take part in a relation like any
other, named by the dotted name of the naming rule: `pose.roll.drives(…)`
on the class that declares it, `chassis.pose.roll` from the class that
declares the child.

A NODE named as an end of a relation SHALL stand for the ONE joint of
that node's class: an arbor is one body turning at one bearing, and
`power.drives(centre)` between two such nodes SHALL relate their
coordinates. A node whose class declares no joint, or more than one,
SHALL be refused at class definition naming the node, its class and the
joints that class declares, with the advice to name the coordinate. A
node whose class declares exactly one joint, and that joint owns several
coordinates, SHALL be refused the same way, listing the coordinates of
that joint: the node stands for its one joint and the joint stands for no
single coordinate.

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

#### Scenario: A relation drives one coordinate of a free joint

- **WHEN** a root states `tilt.drives(chassis.pose.pitch)` from a driver
  and `lift.drives(chassis.pose.z, ratio=2.0)`
- **THEN** the chassis is placed from those two values with its other
  four coordinates unbound, the relations invert as they do for any
  rotational and translational coordinate, and the motion is tagged with
  the assembly that solved them

#### Scenario: A free joint cannot be a relation end

- **WHEN** a class body states `tilt.drives(chassis.pose)`, or names as
  an end a child whose class declares one `Free` and nothing else
- **THEN** class definition raises naming the joint and listing its six
  coordinates, with the advice to name one of them

## RENAMED Requirements

- FROM: `### Requirement: One-coordinate joint declarations`
- TO: `### Requirement: Joint declarations`

- FROM: `### Requirement: A joint owns one coordinate, and that coordinate is a port`
- TO: `### Requirement: A joint owns one or more coordinates, and each is a port`

## MODIFIED Requirements (continued)

### Requirement: Joint declarations

The system SHALL provide the one-coordinate lower pairs as declarations
exported from `solid_node.motion.joints`: `Revolute(axis, at=(0, 0, 0),
range=None, unit='deg')`, which turns a body about a line;
`Prismatic(axis, at=(0, 0, 0), range=None, unit='mm')`, which slides a
body along one; and `Orbit(axis, at=(0, 0, 0), carries=None, range=None,
unit='deg')`, which carries a point of a body round one while the body's
attitude stays fixed. It SHALL provide, from the same module, the one
joint that is not a lower pair: `Free(at=(0, 0, 0), angle_unit='deg',
length_unit='mm')`, the six freedoms of a body with no parent to be
jointed to, which takes no `axis` and no `range` and owns six
coordinates; see "A free joint owns six coordinates and floats a body".
A joint SHALL be declared as a class attribute of
the node it moves — an assembly or a leaf — and SHALL be stateless class
metadata shared by every instance of that class, exactly as a port
declaration is.

`axis` SHALL be a direction of three components and `at` an anchor point
of three components, both stated in the PARENT's frame: the frame the
parent's `render()` places the declaring node in. `axis` SHALL have no
named constants; it is written as a tuple. `at` SHALL default to the
origin of that frame, which is the case of a joint whose line passes
through the node's own placed origin. `range` SHALL be a `(lo, hi)` pair
in `unit`, and `unit` SHALL be the label the coordinate carries; a joint
that owns coordinates in two domains SHALL declare one unit label for
each domain instead, as a `Free`'s `angle_unit` and `length_unit` do. An
`Orbit`'s `axis` and `at` SHALL mean exactly what a `Revolute`'s mean — a
direction and a point ON the line — and its `carries` SHALL be the point
of the body that travels round that line, stated in the same frame; see
"An orbit's radius and phase are derived, never declared".

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
definition naming the name and both declarations. That refusal SHALL hold
for a joint owning ANY number of coordinates, so a `Free` and a port
sharing a name is refused where a `Revolute` and a port are.

A joint that owns SEVERAL coordinates SHALL still occupy exactly ONE
position in that enumeration, under the joint's own name: how many
freedoms a joint carries is a property of the joint, and how the joints
of a class stack is a property of their declaration order.

#### Scenario: A joint is declared where the body is

- **WHEN** a forearm class declares
  `elbow = Revolute(axis=(0, 0, 1), at=(0, 160, 68), range=(-135, 135), unit='deg')`
- **THEN** the class carries that joint by name with its axis, anchor,
  range and unit readable off the class, no instance was constructed,
  and the axis and anchor are understood in the frame its parent places
  it in

#### Scenario: An orbit is declared where the carried body is

- **WHEN** a connecting rod class declares
  `orbit = Orbit(axis=(1, 0, 0), carries=(0, 0, 15), unit='deg')`
- **THEN** the class carries that joint by name with its axis, its
  anchor at the parent frame's origin, its carried point, its unit and no
  radius or phase readable off the class, and no instance was constructed

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

#### Scenario: A free joint and a port cannot share a name either

- **WHEN** a class body declares `pose = Free()` and
  `pose = SignalPort(unit='')`
- **THEN** class definition raises naming the class, the name and both
  declarations, rather than keeping whichever was written last

#### Scenario: A free joint is one entry of the declaration order

- **WHEN** a class declares `pose = Free()` and then
  `lift = Prismatic(axis=(0, 0, 1), unit='mm')`
- **THEN** the joints enumerator reads `pose`, `lift` — two entries, the
  six freedoms of the `Free` occupying the first of them

### Requirement: A joint owns one or more coordinates, and each is a port

The system SHALL give every joint at least one coordinate, and every
coordinate of a joint SHALL be a port. The one-coordinate pairs own
exactly one: rotational for a `Revolute` and for an `Orbit`,
translational for a `Prismatic`, carrying the joint's `unit`. A `Free`
owns six, three rotational and three translational, carrying its
`angle_unit` and its `length_unit`. An `Orbit`'s coordinate SHALL
be rotational although its placement is a translation: what the
coordinate measures is an angle round the line, and a relation into it
SHALL therefore invert exactly as a relation into a `Revolute` does.
Read on an instance, a joint owning ONE coordinate SHALL be that
coordinate's bound value slot
— the same per-instance slot a declared port of the same kind yields — so
two instances of one class never share a joint value and an unbound
coordinate reads as unbound rather than as zero. Assigning to such a
joint on
an instance SHALL bind its coordinate exactly as assigning to a port
binds one: from a plain number, a symbolic expression, a driver read, or
another bound port, through the one binding path `connect()` also uses. A
joint SHALL be a data descriptor, so an assignment can never replace the
declaration with a raw attribute.

Read on an instance, a joint owning SEVERAL coordinates SHALL yield a
view from which each of them is reachable by its own short name, each
read giving that coordinate's own per-instance bound value slot and each
assignment binding it through that same one binding path. Assigning to
such a joint as a whole SHALL be refused by name, listing its
coordinates, because there is no one value to bind.

**The naming rule.** A joint owning ONE coordinate SHALL name it after
the joint. A joint owning SEVERAL SHALL name each of them
`<joint name>.<coordinate name>` — the joint's declared attribute name, a
single dot, and the coordinate's own short name. That one name SHALL be
the name the coordinate carries, the name the port enumerator reports it
under, and the tail of a relation path that reaches it. A coordinate
SHALL NOT have a second spelling. A name of more than one segment is not
a Python identifier, so it SHALL NOT be usable as a keyword argument, and
a coordinate of a joint owning several is reached by assignment on the
instance, by relation path, and by a driver or an expression — never by a
wiring keyword.

The port enumerator SHALL report every coordinate of every joint under
that name alongside the class's plain ports, so every consumer that
enumerates a node's connection points — tooling, wiring, later
simulation surfaces — sees a joint's coordinates without knowing about
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

#### Scenario: An orbit's coordinate is an angle

- **WHEN** a consumer enumerates the declared ports of a class declaring
  one `Orbit` with `unit='deg'`, and a relation drives that coordinate
  from a shaft's rotation with a ratio
- **THEN** the entry carries the rotational domain and `'deg'`, and the
  relation inverts as it does for any two rotational coordinates

#### Scenario: A free joint's six coordinates enumerate under dotted names

- **WHEN** a consumer enumerates the declared ports of a class declaring
  `pose = Free(angle_unit='deg', length_unit='mm')` and one plain port
- **THEN** it receives seven entries: the plain port under its own name,
  and `pose.roll`, `pose.pitch`, `pose.yaw` carrying the rotational
  domain and `'deg'` with `pose.x`, `pose.y`, `pose.z` carrying the
  translational domain and `'mm'`, and no entry named `pose`

#### Scenario: A coordinate of a free joint has one spelling

- **WHEN** a class declaring `pose = Free()` alongside a `SignalPort`
  named `roll` is realized
- **THEN** the two are different coordinates, reported as `pose.roll` and
  `roll`, and neither read reaches the other

