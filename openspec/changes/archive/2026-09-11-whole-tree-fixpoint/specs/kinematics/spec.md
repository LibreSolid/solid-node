## MODIFIED Requirements

### Requirement: Render at rest, simulate per instant

The system SHALL split an assembly's lifecycle into a rest build and a
per-instant motion. `render()` SHALL build the machine at rest — structure,
`omit()`, and the placement of every part that does not move — and SHALL
read no driver, no animation time and no port. `AssemblyNode.simulate()`, a
no-op in the base, SHALL be run by the framework after `render()` ONCE
PER ENUMERATION of the tree the assembly hangs in, under whatever
binding is current: symbolic `$t` when nothing is bound, plain numbers under
`set_state`, `set_keyframe`, the test runner, the snapshot tool and the
simulator. Drivers, time and ports SHALL be read and bound in `simulate()`,
and a joint's coordinate is a port for this purpose.

An operation applied during `simulate()` SHALL compose innermost: it is
inserted before every operation `render()` or construction applied to the
node, so the node moves in its own frame and is then carried by its rest
placement. Operations applied during `simulate()` SHALL be tagged with the
simulating assembly and swept before that assembly's next `simulate()`, so
poses are absolute and never accumulate; two assemblies simulating one node
SHALL keep their operations apart. A joint bound during `simulate()` SHALL
apply its motion as operations of the node the joint is declared on,
tagged with the assembly whose `simulate()` is running and swept with the
rest of that assembly's motion, whether the joint is that assembly's own or
one of a node below it.

The simulate phase of one assembly SHALL run in a fixed order: FIRST
the framework clears the value and the binder record of every
coordinate this assembly bound during its PREVIOUS simulate phase —
whatever bound it there, the author's own `simulate()` included — in the
same moment as the sweep that drops the operations it applied, so a
coordinate never goes on holding a value whose motion has been swept and
the run that follows sees only values bound in the current enumeration;
THEN the author's `simulate()` runs; THEN the wirings and the relations
the class declared are attempted together, each wiring binding once its
source is bound and each relation applied from whichever of its ends is.
All of it happens while the phase is still that assembly's, so every
motion it causes carries that assembly's tag and is swept before its
next run. A binding made outside any simulate phase — in `__init__`, in
a test, through a `render()` no walker drove — SHALL NOT be cleared,
exactly as an operation applied outside a phase is never swept.

The simulate phases of ONE ENUMERATION SHALL run as one pass, owned by
the assembly whose `render()` began it: it drives every assembly's phase
in its subtree, parents before children and in declaration order among
siblings, before that `render()` returns, and each assembly's phase runs
ONCE. Because each class attempts its own relations in its own
instance's phase, a relation stated on an ancestor and reaching a
descendant's coordinate by path SHALL be solved before that descendant's
`simulate()` runs and before that descendant's own relations are
attempted. What an assembly's own attempt cannot reach SHALL be deferred
to that pass's own fixpoint, which runs once every phase has run, and
refused only then — the couplings capability states the deferral, the
propagation order and the refusals.

An assembly whose first `render()` read nothing SHALL run that `render()`
once per instance: later calls SHALL return the same children and SHALL NOT
re-run the author's `render()`, and the operations it applied SHALL persist
unswept. `omit()` called during `simulate()` SHALL raise `StructureError`.

#### Scenario: Motion composes innermost

- **WHEN** an assembly's `render()` translates a child to `[10, 0, 0]` and
  its `simulate()` rotates the child by `90` degrees about z
- **THEN** the child's operations are the rotation then the translation,
  and its origin lands at `[10, 0, 0]` rather than `[0, 10, 0]`

#### Scenario: Rest render runs once

- **WHEN** an assembly whose `render()` reads nothing is rendered under
  three successive `set_state` bindings
- **THEN** the author's `render()` ran once, the placement operation
  objects are the same objects each time, and the `simulate()` operation
  holds the current binding's value with no accumulation

#### Scenario: Symbolic simulate in the build path

- **WHEN** an assembly is rendered with nothing bound
- **THEN** the operation `simulate()` applied carries the symbolic `$t`
  expression, `set_keyframe(0.25)` makes it numeric, and `clear_keyframe()`
  restores the symbolic form

#### Scenario: Two simulators of one node

- **WHEN** two assemblies each simulate the same node and one re-simulates
- **THEN** only that assembly's operation is replaced and the other's is
  untouched

#### Scenario: Joint motion is swept like any motion

- **WHEN** an assembly binds a child's joint in its `simulate()` and the
  tree is enumerated twice at different instants
- **THEN** the child carries one joint motion for the current instant,
  tagged with that assembly, and the rest placement its parent applied is
  untouched

#### Scenario: The phase solves the wirings and the relations together

- **WHEN** an assembly binds one joint in `simulate()`, declares a
  wiring whose source another relation of the same class solves, and
  states that relation
- **THEN** the relation is applied and the wiring binds from its solved
  source in the same solve, all the motion is tagged with that
  assembly, and all of it is swept before its next run

#### Scenario: A phase clears what it bound last run

- **WHEN** an assembly whose relations solve a train from one binding
  in `simulate()` is enumerated at three successive instants
- **THEN** each run cleared the coordinates it had bound in the
  previous one before the author's `simulate()` ran, and each run's
  solve produced that instant's angles rather than refusing or
  repeating the first instant's

#### Scenario: An ancestor's relation binds before the descendant solves

- **WHEN** a root states a relation reaching a joint declared two levels
  down, and that level's own class states relations over the same joint's
  neighbours
- **THEN** the root's relation bound the joint before the descendant's
  relations were solved, and the descendant solved against that value

#### Scenario: Structure cannot move

- **WHEN** `simulate()` calls `omit()` on a declared child
- **THEN** `StructureError` is raised naming the node


#### Scenario: A phase is not re-run by the walk that follows it

- **WHEN** a three-level tree is assembled
- **THEN** each assembly's `simulate()` ran once, before any of the
  tree's geometry was read, and the walker's descent into each child
  re-ran no phase

#### Scenario: What a hand binding leaves behind is cleared

- **WHEN** an assembly's `simulate()` binds a child's joint only when
  the coordinate is unbound, and the tree is enumerated three times
- **THEN** every run rebinds it and the child holds one joint motion for
  the current instant, instead of standing at rest from the second run
  on while the coordinate still reads the first run's number

### Requirement: Multi-driver state binding

The system SHALL let an `AssemblyNode` bind a snapshot of named numeric
driver values with `set_state(**states)`. Binding SHALL merge the given
entries into the assembly's current snapshot (an entry is replaced when
re-given, preserved otherwise), deliver every entry to the node it is
addressed to across the whole subtree BEFORE any of it is enumerated,
and then enumerate the subtree ONCE — so that every node's snapshot is
current for the whole of that enumeration, and no node simulates against
the snapshot of a previous binding. The delivery walk SHALL use the
children each node holds at rest and SHALL link them as it descends, so
qualification is computed against the same names every linked pass
derives, and SHALL tolerate a `render()` result that is not a list or
tuple by descending into no children. Snapshot values SHALL be plain
numbers.

Entries SHALL be addressable by qualified id: an entry named with a
dotted instance path (`x_axis.motor`) SHALL be delivered only to the
addressed instance's subtree, with the consumed leading segment
stripped as propagation descends, so sibling instances of one class
hold independent values for a same-named driver. The `time` entry
SHALL remain global: it propagates flat and unmodified to every
descendant. A bare (unqualified) entry for a project driver SHALL
remain valid while exactly one declared driver in the subtree bears
that local name; when the bare name is ambiguous, binding SHALL fail
loudly listing the colliding qualified ids rather than delivering one
value to all of them.

Every bound name SHALL name a declared driver. A bare name that no
declared driver in the tree bears, and a dotted name that is not a
qualified id the tree publishes, SHALL both fail loudly naming the
rejected entry and the declared ids, because nothing can read an entry
with no declaration behind it. `time` is the one exception: it is a
snapshot entry with no declaration and SHALL remain bindable. A
refused binding SHALL leave the tree's snapshot exactly as it was, in
the same way an ambiguous binding does.

`render()` SHALL read a driver DECLARED on that node as an attribute of
the node, under the name the declaration was made with: a node
declaring `x = Driver(...)` reads its bound value as `self.x`. This
SHALL be the only surface for reading a driver value off a node; no
mapping view of the bound snapshot is exposed. The read SHALL yield
exactly the entry bound for that node under that local name, in
whichever binding mode is active — the plain number under a numeric
snapshot, the symbolic token under the document's symbolic mode.
Reading a declared driver whose entry is not bound SHALL raise an
error naming the driver and `set_state`, so a state-consuming assembly
rendered without a snapshot fails loudly rather than guessing.

Assigning to a declared driver on an instance SHALL raise an error
naming the driver and `set_state`. A driver's value belongs to the
bound snapshot, and an instance attribute of the same name would
shadow the declaration silently for every later read.

Declaring a driver under a name already carried by the node class from
any base SHALL raise at class-definition time, naming the collision, so
a driver cannot silently displace a node member such as `render` or
`time`. Redeclaring a driver inherited from a base SHALL remain legal,
which is how a subclass overrides an inherited declaration.

Animation time SHALL be read through the `time` property, which
returns the bound `time` entry and falls back to symbolic `$t` when
none is bound, preserving the ADR-008 animation path.

`clear_state(*names)` SHALL remove the named entries from the snapshot
— all entries when called with no names, accepting qualified names the
same way `set_state` does — deliver and enumerate the same way, and
restore symbolic `$t` behavior for `time`. Because re-renders sweep
only the operations the assembly drove, repeated
`set_state`/`clear_state` cycles SHALL NOT accumulate operations, and
static placement applied outside any assembly render SHALL survive,
exactly as the idempotent-render requirement already guarantees.

On nodes that do not animate (leaves, fusions), `set_state` and
`clear_state` SHALL be no-ops, mirroring `set_keyframe`.

#### Scenario: A declared driver reads as an attribute

- **WHEN** an assembly declaring `motor = Driver(default=0)` is bound
  with `set_state(motor=4000)` and its `render()` derives a
  translation from `self.motor`
- **THEN** `self.motor` reads `4000` and the assembly re-renders at
  the pose that value implies, absolutely

#### Scenario: Sibling instances read their own attribute value

- **WHEN** a parent holding `x_axis` and `y_axis` instances of one
  `motor`-declaring class binds `{'x_axis.motor': 8000,
  'y_axis.motor': 2000}`
- **THEN** `x_axis.motor` reads `8000` and `y_axis.motor` reads
  `2000`, the two poses differ accordingly, and no value is shared
  between the instances

#### Scenario: The declaration is still readable off the class

- **WHEN** a driver declared as `motor = Driver(default=8000, ...)` is
  read from the CLASS rather than from an instance
- **THEN** the declaration object itself is returned, and driver
  discovery, qualification, and the serialized driver table are
  unaffected

#### Scenario: Attribute read under symbolic binding

- **WHEN** a driver-declaring tree is walked in the document's
  symbolic mode and its `render()` reads the driver as an attribute
- **THEN** the read yields the symbolic driver token carrying the
  qualified id, and the restored numeric snapshot reads numbers again
  afterwards

#### Scenario: Unbound attribute read fails loudly

- **WHEN** an assembly whose `render()` reads `self.motor` is rendered
  with no snapshot bound
- **THEN** an error is raised naming `motor` and `set_state`

#### Scenario: Assigning to a driver fails loudly

- **WHEN** code assigns `node.motor = 5` on an instance whose class
  declares `motor` as a driver
- **THEN** an error is raised naming `motor` and `set_state`, and the
  bound snapshot is unchanged

#### Scenario: A shadowing driver name is rejected at declaration

- **WHEN** a node class declares a driver under a name its bases
  already carry, such as `render` or `time`
- **THEN** the class definition fails with an error naming the
  colliding name

#### Scenario: Redeclaring an inherited driver stays legal

- **WHEN** a subclass of a `motor`-declaring assembly redeclares
  `motor` with a different default
- **THEN** the class defines successfully and the subclass's
  declaration is the one discovery finds

#### Scenario: An undeclared bare name is refused

- **WHEN** `set_state(motr=4000)` is called on a tree whose only
  declared driver is `motor`
- **THEN** binding fails naming `motr` and listing the declared ids,
  and no entry is left bound anywhere in the tree

#### Scenario: An unknown qualified id is refused

- **WHEN** `set_state(**{'z_axis.motor': 100})` is called on a tree
  holding only `x_axis` and `y_axis`
- **THEN** binding fails naming `z_axis.motor` and listing the
  declared ids, and no entry is left bound anywhere in the tree

#### Scenario: Two named drivers bind numerically

- **WHEN** `set_state(motor=4000, lift=2.5)` is called on an assembly
  declaring both and deriving operations from `self.motor` and
  `self.lift`
- **THEN** the assembly re-renders with both values as plain numbers
  and `node.mesh` reflects the resulting pose absolutely

#### Scenario: Merging preserves unrelated entries

- **WHEN** `set_state(motor=4000)` is followed by `set_state(lift=1.0)`
- **THEN** the assembly reads `motor` as `4000` and `lift` as `1.0`

#### Scenario: Ambiguous bare name fails loudly

- **WHEN** `set_state(motor=1234)` is called on a tree where two
  sibling instances both declare `motor`
- **THEN** binding fails listing `x_axis.motor` and `y_axis.motor`,
  and neither instance's state changes

#### Scenario: Time stays global

- **WHEN** `set_state(time=0.25)` is called on a tree with colliding
  project-driver names
- **THEN** every descendant's `time` property reads `0.25`, with no
  qualification required

#### Scenario: State cycles do not accumulate operations

- **WHEN** `set_state` is called many times in sequence on the same
  assembly (as a stepping loop does every tick)
- **THEN** each driven child holds exactly the operations one render
  applies, and static placement applied outside any assembly render is
  still present

#### Scenario: Clearing state restores symbolic time and unbinds drivers

- **WHEN** `set_state(time=0.5, motor=100)` is followed by
  `clear_state()`
- **THEN** the assembly's `time` reports symbolic `$t` again and
  reading `self.motor` raises naming `motor` and `set_state`

#### Scenario: Leaf tolerance

- **WHEN** `set_state(motor=10)` propagation reaches a leaf node
- **THEN** the call is a no-op on that leaf


#### Scenario: A descendant simulates against the snapshot just bound

- **WHEN** `set_state(step=90)` is called on a machine whose child axis
  declares `step` and reads it in its own `simulate()`, after an earlier
  `set_state(step=10)`
- **THEN** the child reads `90` throughout that enumeration, including
  while its parent's phase runs, rather than `10`
