## ADDED Requirements

### Requirement: A joint declared where a child is placed

The system SHALL accept a joint declaration passed as a KEYWORD ARGUMENT
where a node class body declares a child, and SHALL treat it as a
declaration of a freedom ON THAT CHILD, contributed by the site:

    screw = ZScrew(turn=Revolute(axis=(0, 0, 1), unit='deg'))
    disks = CycloidalDisk(orbit=Orbit(axis=AXIS, unit='deg')).repeat(2)

Such a keyword SHALL NOT be a wiring and SHALL NOT be a parameter. It
SHALL NOT be resolved as a parameter, SHALL NOT be passed to the child's
construction, and SHALL NOT enter the child's identity. A keyword whose
value is a coordinate DECLARED ON THE CLASS whose body holds the
declaration SHALL keep the meaning it has today — a wiring — and a
keyword whose value is a joint declared on NO class SHALL be a site
declaration; a keyword whose value is a joint declared on some OTHER
class SHALL be refused, because one declaration object belongs to one
class.

**The child such a declaration realizes SHALL carry that joint as
ordinary class metadata.** The declaration SHALL realize its children as
instances of a SPECIALIZATION of the declared class — a class derived
from it carrying the site's joints — created once per declaration site
and shared by every child that site realizes, including every copy of a
`.repeat()`. The specialization SHALL be indistinguishable from the
declared class in every respect but the joints it adds:

- `isinstance` against the declared class SHALL hold;
- the child's build identity SHALL be the identity it would have without
  the joint keyword, so two children of one class differing only in the
  joints their sites passed SHALL share one build identity and one set of
  artifacts — a joint states where a body may move, not what geometry is
  built;
- the class's name, qualified name, defining module and source file SHALL
  be the declared class's, which is what makes that identity hold and
  what every message, artifact path and source digest reads;
- it SHALL NOT be discoverable as a node class defined by any module, so
  nothing that enumerates a project's models can reach it.

Consequently the joint SHALL be reported by the enumerators that read a
class: the joints of the realized child's class, in composition order,
and its declared ports — so a consumer of a node's freedoms or connection
points sees a site-declared joint without knowing what a declaration site
is, and every name so reported SHALL be readable back and bindable by
name exactly as any other coordinate's is.

The joint SHALL be stated in the DECLARING PARENT's frame and its
arguments SHALL resolve against the realized declaring parent, as "A
joint is stated in the frame of whoever declares it" and "Joint arguments
resolve against the instance at realization" state. Its operations SHALL
be carried into the child's own frame and placed innermost at its
position in the child's joint order, as "Binding a joint places the body"
states.

The coordinate a site-declared joint owns SHALL answer to its keyword on
the CHILD by every route a class-declared joint's does: a class body
declaring the site MAY read it as a PATH — `screw.turn`, and
`screws.turn` through a repeated declaration, which is a broadcast — and
the child SHALL read it as an attribute and bind it by assignment, which
SHALL bind through the one binding path every binder takes and place the
body.

A site-declared joint whose name the child's class ALSO declares as a
joint SHALL REPLACE that declaration for that child, wholly: it takes its
own axis, anchor, further points, range and unit, and inherits nothing
from the declaration it replaces. It SHALL keep the position that name
holds in the class's declaration order, by the rule a subclass
redeclaring an inherited joint already follows.

A site-declared joint MAY be passed on a `.repeat()` declaration and on a
declaration held in a literal list. One declaration SHALL then give the
freedom to every child it realizes, all of them resolving identical
arguments against the same declaring parent, and each one's operations
being carried through ITS OWN rest placement — so one declaration serves
children the parent places at different points and at opposed attitudes.

The system SHALL refuse, at class definition, a site-declared joint whose
keyword names anything the child already answers to other than a joint: a
port or a derived coordinate the child's class declares; a parameter the
child's class declares, or a named parameter of the child's constructor,
because the keyword is withheld from construction and the child would
otherwise be built without it; or any other attribute of the child's
class, because reading the joint on the node would hide it. It SHALL
refuse two site-declared joints of one name on one declaration, and a
site-declared joint whose name collides with a coordinate another site
joint of the same declaration owns. Every refusal SHALL name the child
class, the keyword and what the child does declare, and SHALL name the
declaring class and the attribute where the declaration carries one.

#### Scenario: A parent gives a shared catalogue class a freedom

- **WHEN** an assembly declares
  `axle = Bolt(length=L, diameter=D, turn=Revolute(axis=(0, 0, 1), unit='deg'))`
  and places the bolt, and the coordinate is bound
- **THEN** the bolt turns about the line the assembly stated, the `Bolt`
  class itself declares no joint, and every other bolt in the machine is
  unaffected

#### Scenario: The realized child is the class the author wrote, carrying one more joint

- **WHEN** a consumer enumerates the joints and the declared ports of a
  realized child's class, the child having been declared with
  `orbit=Orbit(...)` at its site, and asks whether it is an instance of
  the class the author wrote
- **THEN** both enumerations report `orbit` beside whatever the written
  class declares, in composition order, the `isinstance` check holds, and
  the class reports the written class's name, module and source file

#### Scenario: A site joint is not a parameter and not identity

- **WHEN** a class declaring a positional `filename` and no parameters is
  declared as a child with `travel=Prismatic(axis=(0, 1, 0), at=SEAT, unit='mm')`
- **THEN** the child is constructed with `filename` alone, its build
  identity is the one it has without the keyword, and a sibling of the
  same class declared with a different joint shares that identity and its
  artifacts

#### Scenario: A site joint replaces a class joint of the same name

- **WHEN** a child class declares `turn = Revolute(axis=(1, 0, 0), at=(0, 5, 0), unit='deg')`
  and its declaration site passes `turn=Revolute(axis=(0, 0, 1), unit='deg')`
- **THEN** the realized child's `turn` is the site's, axis and anchor
  together, nothing of the class's declaration survives in it, and it
  occupies the position the class's declaration order gave that name

#### Scenario: A relation names a site-declared coordinate by path

- **WHEN** a class body declares two children with site joints and states
  `left.travel.drives(right.travel)`
- **THEN** the relation resolves against the realized children and binds
  the second from the first, and a path naming a keyword neither the site
  passed nor the child's class declares is refused at class definition

#### Scenario: A site joint on a repeat gives every copy the freedom

- **WHEN** a class body declares
  `pins = Pin(orbit=Orbit(axis=(0, 0, 1), unit='deg')).repeat(6)` and a
  relation broadcasts one angle to `pins.orbit`
- **THEN** six copies each carry the freedom, all six are instances of one
  specialization and resolved identical arguments, and each was placed
  through its own rest placement

#### Scenario: A site keyword naming something the child already answers to is refused

- **WHEN** a declaration passes a joint under a keyword that is a port
  the child declares, a parameter the child declares, a named parameter
  of the child's constructor, or any other attribute of the child's class
- **THEN** class definition raises naming the child class, the keyword
  and what the child does declare, and no child is realized

## MODIFIED Requirements


### Requirement: A joint is stated in the frame of whoever declares it


A joint's `axis`, its anchor `at` and every further point or direction it
declares SHALL be read in the frame of the DECLARER: the site the joint
declaration is written at decides the frame its arguments mean.

A joint declared in a CLASS BODY, as a class attribute of the node it
moves, SHALL be stated in the REST FRAME of THAT BODY: the frame the
body's own `render()` states its geometry in, which differs from the
frame its parent places it in by exactly the rest placement and by
nothing else. Because a joint's operations are placed INNERMOST, before
every rest operation, the rest frame is the frame every joint operation
of that body is read in, whatever other motion is composed outside them;
a joint's line SHALL therefore be unaffected by the body's other
freedoms and by any hand-written motion applied to it.

Its `at` SHALL default to `(0, 0, 0)`, the body's OWN ORIGIN, so a joint
whose line runs through the body's origin is written with no anchor at
all and turns that body where its parent put it. The framework SHALL NOT
transform a class-declared joint's arguments in any way before using
them: they are already in the frame the joint's operations are placed in.

A body its parent ROTATES therefore carries its joint line WITH it: the
line a class-body joint states is fixed in the body, so one class placed
at several sites, or at different attitudes, states one joint and gets
the right line at every site.

A CLASS-declared joint's arguments SHALL NOT depend on the node's rest
placement in any way: such a joint SHALL be placeable on a body whose
rest placement carries a value the framework cannot evaluate numerically,
and two instances of one class placed differently SHALL resolve identical
arguments for it.

A joint declared at a DECLARATION SITE — passed as a keyword where a
parent declares a child, see "A joint declared where a child is placed" —
SHALL be stated in the frame of the DECLARING PARENT: the frame that
parent's own `render()` states its geometry in, which is the frame the
parent's `translate` and `rotate` on that child are written in. URDF's
rule, where a `<joint><origin>` is stated in the parent link's frame.

Its `at` SHALL default to `(0, 0, 0)`, the DECLARING PARENT's own origin,
which is the same sentence as a class-declared joint's default read at
the other site. For a child the parent TRANSLATES, that default names a
line through the PARENT's origin and not through the child's, so such a
child SWINGS about the parent's origin rather than turning on its own
centre; that is the case a parent states when it declares a joint on a
child it has placed off the line.

An `Orbit` declared at a declaration site SHALL be the one exception, and
only for its `carries`, which names a point OF THE BODY rather than a
point of the line: a WRITTEN `carries` SHALL be a point of the declaring
parent's frame like `at`, and a DEFAULTED `carries` SHALL be the CHILD's
own origin. A `Free` declared at a declaration site SHALL float against
the declaring parent's frame: its three rotational directions are that
parent's x̂, ŷ, ẑ and its three translational coordinates displace along
those same directions.

The framework SHALL carry a site-declared joint's resolved directions and
points into the child's own rest frame, by inverting the child's rest
placement, at the moment of binding — because a joint's operations are
placed innermost and the arguments are stated one placement out. Where
that rest placement carries a value the framework cannot evaluate
numerically, the binding SHALL be refused by name, naming the node, the
joint and the operation at fault; a CLASS-declared joint on the same body
is unaffected, because nothing about it is carried.

The framework SHALL normalize a declared `axis` to unit length and SHALL
snap each component of the normalized axis within `1e-9` of `0`, `1` or
`-1` to that exact value, so the normalization's floating-point residue
never reaches the published document as an axis of `(0, 1, 6e-17)`. An
anchor SHALL NOT be adjusted: it is published as the author stated it.

#### Scenario: A joint through the body's own origin needs no anchor

- **WHEN** a pinion class declares `turn = Revolute(axis=(0, 0, 1),
  unit='deg')`, its parent's `render()` places it with
  `translate([40, 25, 0])`, and the coordinate is bound to an angle
- **THEN** the pinion's motion is ONE rotation about `[0, 0, 1]` in its
  own frame with no centring translations, and the pinion spins on its
  own bearing where the parent put it rather than swinging about the
  parent's origin

#### Scenario: One class, several placements, one declaration

- **WHEN** one gear class declaring `turn = Revolute(axis=(0, 0, 1),
  unit='deg')` is instantiated four times and its parent places each copy
  at a different point, and all four coordinates are bound to the same
  angle
- **THEN** every copy spins about the line through its own placed origin,
  the four resolve the same joint arguments, and no copy needed an anchor
  its class could not know

#### Scenario: The line turns with the body

- **WHEN** a body whose parent places it with `rotate(90, [1, 0, 0])`
  declares `turn = Revolute(axis=(0, 0, 1), unit='deg')` and is bound
- **THEN** the published rotation's axis is `[0, 0, 1]` exactly, and the
  body turns about the direction its own frame calls `z`, which the
  parent's placement has carried onto the parent's `-y`

#### Scenario: A rest placement the framework cannot evaluate no longer prevents a joint

- **WHEN** a node whose rest placement carries a symbolic value has a
  CLASS-declared joint bound
- **THEN** the body is placed about the line its own frame states, and
  nothing is refused

#### Scenario: A joint stated where the child is placed anchors on the parent's origin

- **WHEN** a motor drive declares
  `screws = LockScrew(orbit=Revolute(axis=(0, 0, 1), unit='deg')).repeat(2)`
  and its `render()` places the two copies at `[0, +3.9, z]` and
  `[0, -3.9, z]`, and both coordinates are bound to the same angle
- **THEN** both screws are carried round the line through the MOTOR
  DRIVE's own origin at a radius of 3.9, not turned on their own centres,
  and the declaration wrote no anchor, no sign and no index

#### Scenario: One site declaration serves opposed placements

- **WHEN** a winch declares
  `rollers = RollerBearing(spin=Revolute(axis=(0, 1, 0), at=SHAFT_POINT, unit='deg')).repeat(2)`
  and places the copies with `rotate(90, [1, 0, 0])` and
  `rotate(-90, [1, 0, 0])`, and both are bound to the same angle
- **THEN** each copy turns about the winch-frame line the declaration
  states, the two copies' own-frame axes being opposite, and one
  declaration served both placements

#### Scenario: A defaulted carried point at a site is the child's own origin

- **WHEN** a drive declares
  `disk = CycloidalDisk(orbit=Orbit(axis=(0, 0, 1), unit='deg'))` and
  places the disk at `translate([0, -2.5, 0])`, and the coordinate is
  bound
- **THEN** the disk's own origin travels the circle of radius 2.5 about
  the line through the DRIVE's origin, its attitude unchanged, and
  neither the radius nor the phase was written

#### Scenario: A site joint on a rest placement the framework cannot evaluate is refused

- **WHEN** a parent places a child with a translation carrying a symbolic
  value and binds a joint it declared at that child's declaration site
- **THEN** the binding raises naming the node, the joint and the
  operation whose value is not a number, and a class-declared joint on
  the same body still binds


### Requirement: Binding a joint places the body


The system SHALL move the node a joint is declared on when that joint's
coordinate is bound, composing the motion onto the node's rest
placement. Motion composes innermost — in the node's own frame, before
the placement its parent's `render()` applied — and a class-declared
joint's `axis`, `at` and further points are ALREADY stated in that frame
(see "A joint is stated in the frame of whoever declares it"), so the
framework SHALL use them as they resolved, without transforming them
through the rest placement or through anything else. A SITE-declared
joint's are stated one placement out, in the declaring parent's frame,
and the framework SHALL carry every one of its directions and every one
of its points into the node's own frame through the inverse of the node's
rest placement — the node's non-motion operations composed in list order
— before using them, so that its operations too are placed innermost. It
SHALL apply, as operations of that node:

- for a `Revolute`, `translate(-anchor)`, `rotate(value, axis)`,
  `translate(anchor)` in the node's own frame, in that order, the two
  centring translations OMITTED when every component of the anchor
  is zero within `1e-9`, so a joint through the node's own origin
  produces one rotation and nothing else;
- for a `Prismatic`, `translate(value * axis)` along the unit axis in
  the node's own frame, each component of the translation being a plain
  numeric `0` where the corresponding axis component is zero, rather
  than an expression multiplied by zero;
- for an `Orbit`, ONE translation in the node's own frame, being the
  displacement the carried point undergoes when it is turned by the bound
  value about the line. Writing `n` for the unit axis,
  `a` for the anchor, `p` for the carried point, `v` for the
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
  centring pair around three rotations about the node's own three unit
  directions, and one translation outermost — as "A free joint places a
  floating body by a fixed composition" states.

A joint owning SEVERAL coordinates SHALL be re-placed in full whenever
ANY of them is bound, from the values its coordinates then hold, so its
composition never depends on the order they were bound in; an unbound
coordinate of such a joint SHALL contribute no motion while still reading
as unbound.

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
phase is current, because by the time they are placed they are stated in
the node's own frame and an operation appended after the rest placement
would be read in the parent's frame instead. That holds for a
site-declared joint as much as for a class-declared one: its arguments
were carried into the node's own frame first, so its run occupies its own
position in the one composition order above rather than a second position
outside the rest placement. Under a `simulate()` phase they
SHALL additionally be tagged with that assembly and swept before its next
run, exactly as a hand-written rotation there is — the assembly whose
`simulate()` bound it owns the tag, whether the joint is its own or a
child's. Bound outside any lifecycle phase — a test binding a joint
directly, a script posing a tree — they SHALL be untagged, so no sweep
removes them, and they SHALL persist until that same joint is bound
again.

**A node's motion SHALL compose innermost-first as the operations of its
joints in that node's joint order, each joint's own operations contiguous
and in the order that joint's placement produces them, followed by every
hand-written motion in the order it was applied.** A node's joint order
SHALL be its class's declaration order with the declaration site's
contribution folded in: a site-declared joint whose name the class also
declares REPLACES that declaration and keeps its position, exactly as a
subclass redeclaring an inherited joint does, and a site-declared joint
of a new name follows every class-declared joint, in the order the
keywords were written. That is: the FIRST joint of that order is applied
closest to the body and the last is outermost, WHATEVER order the
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

#### Scenario: A pivot away from the origin turns as Thor turns it

- **WHEN** a parent's `render()` places a forearm with
  `rotate(90, [1, 0, 0])` then `translate([0, 241.5, 68])`, the forearm
  declares `elbow = Revolute(axis=(0, 1, 0), at=(0, 0, 81.5),
  unit='deg')` — its own frame's statement of the line Thor's `art2.py`
  calls `ELBOW_PIVOT_AXIS` through `ELBOW_PIVOT` — and the parent's
  `simulate()` binds `elbow` to `30`
- **THEN** the forearm's operations begin with
  `translate([0, 0, -81.5])`, `rotate(30, [0, 1, 0])`,
  `translate([0, 0, 81.5])`, followed by the two rest operations
  unchanged, and nothing was inverted to get there

#### Scenario: A joint through the placed origin needs no anchor

- **WHEN** an arbor placed by `translate([x, y, 0])` declares
  `turn = Revolute(axis=(0, 0, 1), unit='deg')` with no `at` and is
  bound to an angle
- **THEN** its motion is one rotation about `[0, 0, 1]` in its own
  frame, with no centring translations, and the whole body turns at its
  bearing

#### Scenario: A joint bound outside any lifecycle phase still moves the body

- **WHEN** a test realizes a node, places it by hand and binds its joint
  with no `render()` or `simulate()` running
- **THEN** the joint's operations sit before the rest placement, marked
  as motion and tagged with no animator, the body is placed about the
  line its own frame stated, and binding the joint again replaces
  them rather than adding to them

#### Scenario: A slide moves along its axis

- **WHEN** a carriage declaring
  `travel = Prismatic(axis=(1, 0, 0), range=(0, 200), unit='mm')` is
  bound to `120`, its parent having placed it with
  `rotate(90, [0, 0, 1])`
- **THEN** the carriage carries one translation of 120 along its OWN `x`,
  published as `['120', '0', '0']` with plain numeric zeros in the two
  idle components, and its declared `at` changed nothing

#### Scenario: A carried body moves without turning

- **WHEN** a disk placed away from the parent's origin declares
  `orbit = Orbit(axis=(0, 0, 1), carries=(0, 2.5, 0), unit='deg')` and
  the coordinate is bound to a series of angles
- **THEN** the disk carries exactly one translation at each binding, the
  composed transform's rotation block is unchanged from the rest
  placement's at every one of them, and the carried point lies at each
  angle where turning it about the joint's line would put it

#### Scenario: An orbit composes with a turn of the same body

- **WHEN** a disk declares `spin = Revolute(...)` about its own centre
  and then `orbit = Orbit(...)` about a line of its own frame, and both
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
  from its own origin and then `slide = Prismatic(...)` along an axis
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
  outermost, and `a` moves about the subclass's anchor, read in the
  subclass's own body frame like every other class-declared joint

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

#### Scenario: A joint's line does not move when the rest placement changes

- **WHEN** two instances of one class declaring
  `turn = Revolute(axis=(0, 0, 1), at=(0, 10, 0), unit='deg')` are placed
  by their parents with two different rotations and translations, and both
  are bound to the same angle
- **THEN** both carry identical joint operations, and each body turns
  about the line its own frame states

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

#### Scenario: A site joint's run sits at its own slot, inside the rest placement

- **WHEN** a drive declares `disk = CycloidalDisk(orbit=Orbit(axis=(0, 0, 1), unit='deg'))`,
  the disk's own class declares `spin = Revolute(axis=(0, 0, 1), unit='deg')`,
  the drive places the disk with a translation, and both coordinates are
  bound
- **THEN** the disk's operations read, innermost first, the `spin` run,
  then the `orbit` run, then the rest placement — the class's joint
  closest to the body and the site's outside it — and the composed pose
  is the one the same two joints produced when both were declared on the
  class

#### Scenario: A site joint of a name the class declares keeps that slot

- **WHEN** a class declares `pip` then `mcp` and a parent's declaration
  site redeclares both with its own arguments, and both are bound
- **THEN** `pip`'s run is still innermost of the two, the site's
  arguments are the ones used, and no other freedom of that body changed
  position

#### Scenario: One declaration, one set of arguments, one carry per copy

- **WHEN** a parent declares `bearings = Bearing(orbit=Orbit(axis=(0, 0, 1), unit='deg')).repeat(4)`
  and places the four copies at four different points, and a relation
  broadcasts one angle to all four
- **THEN** the four copies resolved identical joint arguments, each was
  carried through its OWN rest placement, and each travels its own circle
  at its own radius and phase


### Requirement: Joint arguments resolve against the instance at realization


The system SHALL resolve a joint's `axis`, `at`, `range` and, where the
joint declares one, its further points such as an `Orbit`'s `carries`,
against the DECLARER: for a class-declared joint, each realized instance
of the declaring class, at realization, once its parameters are resolved;
for a SITE-declared joint, the realized DECLARING PARENT, at the moment
the child is realized, once that parent's parameters are resolved and its
`check()` has run. Each component MAY be a plain number, a
declared-parameter token, or a derived formula over such tokens,
resolved against that declarer's values exactly as a child
declaration's arguments are; `axis`, `at`, `carries` or `range` as a
whole MAY instead be a callable of ONE argument, which the framework
SHALL call with the realized DECLARER — the node itself for a
class-declared joint, the declaring parent for a site-declared one — and
which SHALL return the components as plain numbers. A site-declared
joint's callable SHALL be able to read the declaring parent's resolved
parameters and flags and anything that parent's own `__init__` has set,
and SHALL NOT be able to read the child's placement, which does not exist
yet, or anything the parent's `render()` produces. A joint on a
`.repeat()` declaration SHALL be resolved once per copy against the same
declaring parent, so every copy carries identical resolved arguments; a
copy's own position SHALL NOT be handed to the callable.
Every one of these resolutions SHALL yield a value in the DECLARER's
frame, and SHALL be complete at realization: no joint argument
of a class-declared joint SHALL depend on the node's placement, so an
`Orbit`'s `carries` left unstated on a CLASS declaration SHALL resolve at
realization to `(0, 0, 0)`, the body's own origin, like any other
defaulted vector; left unstated on a SITE declaration it names the
child's own origin, which is not a number until the body is placed and is
resolved when the joint is carried. A
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
  two instances are realized with different `reach`
- **THEN** each instance's joint anchor carries its own resolved number,
  read in that instance's own frame

#### Scenario: A joint anchored on a built position

- **WHEN** a class declares
  `turn = Revolute(axis=(0, 0, 1), at=lambda node: node.built.bearings[node.index])`,
  where `built` is a library object the node constructs from its
  parameters
- **THEN** the callable is called once with the realized node and its
  three numbers become that instance's anchor, read in that instance's
  own frame

#### Scenario: An unresolvable argument fails by name

- **WHEN** a joint declares an `at` naming a token the class does not
  declare, or an `axis` of two components, or a zero-length `axis`, or a
  reversed `range`
- **THEN** realization raises naming the class, the joint and the
  argument at fault, and the instance realized no child

#### Scenario: A joint argument is not identity

- **WHEN** two instances of one class differ only in the resolved value
  of a joint anchor
- **THEN** they share one build identity and one set of artifacts

#### Scenario: A defaulted carried point resolves at realization

- **WHEN** an `Orbit` is declared with no `carries` and the instance is
  realized
- **THEN** its resolved carried point is `(0, 0, 0)`, the body's own
  origin, available before the body has been placed

#### Scenario: A site joint's callable is handed the declaring parent

- **WHEN** an assembly declares `dir` and `side` as parameters and
  `camera = Link('link-camera', tilt=Revolute(axis=lambda parent: (0.0, -parent.side, 0.0), at=lambda parent: (parent.dir * parent.side * X, Y, Z), unit='deg'))`,
  and two instances are realized with different `dir` and `side`
- **THEN** each callable was called once per realized child with the
  realized ASSEMBLY, and each child carries the arguments its own
  parent's handedness produced

#### Scenario: A site joint's arguments are not identity

- **WHEN** two parents declare the same child class at sites differing
  only in the joint they pass
- **THEN** the two realized children share one build identity and one set
  of artifacts, and neither joint reached the child's constructor


### Requirement: An orbit's radius and phase are derived, never declared


The system SHALL derive the radius and the phase of an `Orbit` from its
`axis`, its `at` and its `carries`, and SHALL NOT accept either as a
declared argument. An orbit says WHICH POINT of the body travels round
WHICH LINE; how far that point stands from the line, and where on the
circle it starts, are consequences of those two facts and are computed
from them.

`carries` SHALL be a point of the body, of three components, stated in
the DECLARER's frame and resolved exactly as `at` is — plain numbers,
declared-parameter tokens, derived formulas, or a callable of the
realized declarer. On a CLASS declaration `carries` SHALL default to
`(0, 0, 0)`: in the body's own frame the body's own origin IS the origin,
so the default names that point directly, with no sentinel and no reading
of the placement. On a DECLARATION SITE `carries` SHALL default to the
CHILD's own origin — not the declaring parent's, which is where `at`
defaults and which is not a point of the body at all — so that a site
`Orbit` written with neither argument carries the child's own origin
round the line through the parent's origin, and the radius and phase are
derived from the placement the parent applied. A site `Orbit` SHALL NOT
default its carried point onto its own line.

The derived radius SHALL be the distance from the carried point to the
line, the component along the line being projected out, so which point of
the line `at` names SHALL NOT change the placement. A carried point ON
the line — a derived radius within the module's snapping tolerance of
zero — SHALL be refused at the moment of binding, raising an error naming
the node, the joint, the axis, the anchor, the carried point and the
derived radius, and advising that `carries` name a point off the line: a
body carried at zero radius would not move, and the author meant
something else. The refusal SHALL be made at binding rather than at
realization, because it is the placement of a live body that shows the
author what went wrong, and because a defaulted `carries` on a joint
whose line runs through the body's own origin is exactly this case.

#### Scenario: A carried point is derived from the placement

- **WHEN** a disk declares
  `orbit = Orbit(axis=(0, 0, 1), at=(0, 2.5, 0), unit='deg')` with no
  `carries`, so its own origin is the point that travels, and the
  coordinate is bound to `90`
- **THEN** the disk's own origin has travelled a quarter of the circle of
  radius 2.5 about the line its own frame states, its attitude unchanged,
  and neither the radius nor the starting phase was written anywhere

#### Scenario: A carried point is stated where the body's origin is not the one that travels

- **WHEN** a rod whose own origin lies ON the crank axis declares
  `orbit = Orbit(axis=(1, 0, 0), carries=(0, 0, 15), unit='deg')`, and
  the coordinate is bound
- **THEN** the point 15 mm off the axis travels the circle of radius 15
  about it and the body's origin travels with it, rigidly, with the
  body's attitude unchanged

#### Scenario: A carried point on the axis is refused by name

- **WHEN** a body declares `orbit = Orbit(axis=(1, 0, 0), unit='deg')`,
  so its defaulted carried point `(0, 0, 0)` lies on the line through its
  own origin, and the coordinate is bound
- **THEN** the binding raises naming the node, the joint, the axis, the
  anchor, the carried point and the derived radius of zero, and the node
  carries no motion from that binding

#### Scenario: The anchor may be any point of the line

- **WHEN** one body declares `Orbit(axis=(0, 0, 1), at=(0, 0, 0))` and an
  identically placed body declares `Orbit(axis=(0, 0, 1), at=(0, 0, 40))`
  with the same carried point, and both are bound to the same angle
- **THEN** both bodies are placed identically, the component of the
  carried point along the line having been projected out

#### Scenario: A site orbit written with neither argument derives both numbers

- **WHEN** a drive declares
  `pins = Pin(orbit=Orbit(axis=(0, 0, 1), unit='deg')).repeat(6)` and its
  `render()` places the six copies round a circle at 60 degree spacing,
  and one relation broadcasts the carrier angle to all six
- **THEN** each pin travels its own circle about the line through the
  drive's own origin at its own derived phase, six phases and one radius
  were derived from six rest placements, and neither a radius, a phase
  nor an anchor was written anywhere

#### Scenario: A site orbit whose carried point is not the child's origin states it

- **WHEN** an actuator declares
  `disk = CycloidalDisk(orbit=Orbit(axis=ACTUATOR_AXIS, carries=BORE_CENTRE, unit='deg'))`,
  `BORE_CENTRE` being a point of the ACTUATOR's frame, and the coordinate
  is bound
- **THEN** the bore centre travels the circle it makes about the actuator
  axis, the disk's own origin travels rigidly with it, and the derived
  radius is the bore centre's distance from that axis rather than the
  disk origin's


### Requirement: Joint declarations


The system SHALL provide the one-coordinate lower pairs as declarations
exported from `solid_node.motion.joints`: `Revolute(axis, at=(0, 0, 0),
range=None, unit='deg')`, which turns a body about a line;
`Prismatic(axis, at=(0, 0, 0), range=None, unit='mm')`, which slides a
body along one; and `Orbit(axis, at=(0, 0, 0), carries=(0, 0, 0),
range=None, unit='deg')`, which carries a point of a body round one while
the body's attitude stays fixed. A joint SHALL be declared in either of two
places: as a CLASS ATTRIBUTE of the node it moves — an assembly or a leaf
— or at a DECLARATION SITE, passed as a keyword where a parent declares
that node as a child, see "A joint declared where a child is placed". In
both cases it SHALL be stateless declaration metadata shared by every
node the declaration realizes, exactly as a port declaration is; a site
declaration is shared by every child that site realizes, including every
copy of a `.repeat()`.

`axis` SHALL be a direction of three components and `at` an anchor point
of three components, both stated in the frame of the body the joint is
declared on; see "A joint is stated in the frame of whoever declares it".
`axis` SHALL have no named constants; it is written as a tuple. `at`
SHALL default to that body's OWN origin, which is the case of a joint
whose line passes through the origin of the body it moves. `range` SHALL
be a `(lo, hi)` pair in `unit`, and `unit` SHALL be the label the
coordinate carries. An `Orbit`'s `axis` and `at` SHALL mean exactly what
a `Revolute`'s mean — a direction and a point ON the line — and its
`carries` SHALL be the point of the body that travels round that line,
stated in the same frame; see "An orbit's radius and phase are derived,
never declared".

A `Prismatic`'s `at` SHALL NOT affect its placement — a translation along
a line is the same wherever the line is taken to pass — and SHALL be
carried as the declared position of the slide, for a reader and for a
later exporter.

A class's joints SHALL be enumerable off the class by name, without
constructing an instance, by an enumerator exported beside the joint
kinds. A joint a DECLARATION SITE passed SHALL be reported by that same
enumerator for the class the site's children are realized as, in the
position "Binding a joint places the body" gives it, so one enumerator
answers for both declaration sites and no consumer needs to know which
site a freedom came from. That enumeration SHALL be ORDERED, and its order SHALL be the
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
  `elbow = Revolute(axis=(0, 1, 0), at=(0, 0, 81.5), range=(-135, 135), unit='deg')`
- **THEN** the class carries that joint by name with its axis, anchor,
  range and unit readable off the class, no instance was constructed,
  and the axis and anchor are understood in the forearm's own frame

#### Scenario: An orbit is declared where the carried body is

- **WHEN** a connecting rod class declares
  `orbit = Orbit(axis=(1, 0, 0), carries=(0, 0, 15), unit='deg')`
- **THEN** the class carries that joint by name with its axis, its
  anchor at its own frame's origin, its carried point, its unit and no
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

#### Scenario: One enumerator answers for both declaration sites

- **WHEN** a consumer enumerates the joints of a class declaring `spin`,
  and then the joints of the class of a realized child whose declaration
  site also passed `orbit=Orbit(...)`
- **THEN** the first reports `spin` alone and the second reports `spin`
  then `orbit`, both read off a class without constructing anything
