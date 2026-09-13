## MODIFIED Requirements

### Requirement: Declared time base

A root assembly MAY declare its time base as a class attribute named `time`
holding one of two declarations exported from `solid_node.motion.ports` —
the module that answers what moves, alongside the port kinds — and no
longer from `solid_node.node`: `Time(loop=<seconds>)`, the LOOPING base,
or `Time.running()`, the RUNNING base. Under the looping base `loop` SHALL
be a positive finite number of seconds: the span of machine time one turn
of the animation timeline covers. Under the running base `loop` SHALL be
`None`, because elapsed simulation seconds never wrap. `Time()` with
neither SHALL be refused naming both spellings. The declaration SHALL be
frozen class metadata readable off the class (`Root.time.loop`, and
`Root.time.mode` reading `'loop'` or `'running'`); assigning `self.time`
SHALL fail naming `set_keyframe`.

A `Time` declaration of either base SHALL be refused at class-definition
time when it is bound to any attribute name other than `time`, or when the
declaring class is not an `AssemblyNode`, each with an error naming the
rule.

Under the RUNNING base `self.time` SHALL read elapsed simulation seconds
when bound — by a running simulation, which binds `k*dt` as the
`simulation` capability states, or by `set_keyframe`/`set_state(time=)`,
which callers state in seconds — and, unbound, bare `$t` exactly as an
undeclared root reads, because elapsed seconds have no symbolic form until
a compiled program is published. Every producer that reads the declaration
SHALL treat a `loop` of `None` as no loop: the document's `animation`
object SHALL carry no `loop` key, a snapshot at a fraction of the timeline
SHALL keyframe the fraction as it does for an undeclared root, and a
running root's document SHALL therefore be the document an undeclared root
publishes. What the running base changes is what a simulation over the
root owns and integrates, stated by the `simulation` capability; nothing
else about the tree changes.

Under the LOOPING base `self.time` SHALL read machine time in seconds on
every path:

- unbound, it SHALL be the symbolic expression `$t * loop`, so the normalized
  0..1 `$t` timeline is unchanged and published expressions carry the
  multiplication verbatim (`(360 * ($t * 43200))` rather than a constant);
- bound by `set_keyframe(t)` or `set_state(time=t)`, it SHALL be exactly the
  bound number, which callers state in seconds;
- under a stepped simulation, it SHALL be the simulation clock in seconds
  exactly as the `simulation` capability already states.

The time base is a property of the root: every assembly below it SHALL read
the root's time base, whether or not it declares one itself. Reading `time`
on a linked descendant whose own class declares a `Time` SHALL fail naming
the descendant and the root, so a stray declaration can never silently scale
one subtree differently. An assembly that is itself the root of the tree it
is read in — including a sub-assembly loaded on its own — uses its own
declaration.

A root that declares no time base SHALL keep the normalized 0..1 behaviour
of the "Normalized animation time" requirement unchanged.

#### Scenario: Symbolic time carries the loop

- **WHEN** a root declares `time = Time(loop=43200)` and a nested assembly
  rotates a child by `360 * self.time / 3600`
- **THEN** the nested assembly reads the same `$t * 43200` expression as the
  root, and the serialized operation names `$t` with the loop inside the
  expression rather than a constant

#### Scenario: Keyframes bind seconds

- **WHEN** `set_keyframe(2700)` is called on a root declaring
  `Time(loop=43200)` containing a nested assembly
- **THEN** both assemblies read `time == 2700` as a float and their meshes
  resolve at the pose 2700 seconds into the loop

#### Scenario: Clearing restores the loop expression

- **WHEN** a root declaring a time base is keyframed and then cleared
- **THEN** `time` reads the symbolic `$t * loop` expression again and the
  nested child's operations serialize to the same strings a never-keyframed
  render produces

#### Scenario: A misnamed declaration is refused

- **WHEN** a class body binds `clock = Time(loop=60)`
- **THEN** class definition fails with an error naming `time` as the only
  name a time base may be bound to

#### Scenario: A declaration below the root is refused

- **WHEN** a root without a declaration links a child assembly whose class
  declares `time = Time(loop=60)` and that child's `simulate()` reads
  `self.time`
- **THEN** the read fails naming the child and the root

#### Scenario: A sub-assembly loaded alone uses its own declaration

- **WHEN** an assembly declaring `Time(loop=60)` is loaded as the root
- **THEN** its `time` reads `$t * 60`

#### Scenario: The declaration is readable off the class

- **WHEN** a producer reads `type(root).time` on a root declaring
  `Time(loop=43200)`
- **THEN** it gets the declaration and `loop == 43200.0`, without
  constructing the node

#### Scenario: An undeclared root is unchanged

- **WHEN** a root declares no time base
- **THEN** `self.time` is bare `$t` unbound and the keyframed fraction when
  bound, exactly as before

#### Scenario: The time base is imported from the motion package

- **WHEN** a root's module writes
  `from solid_node.motion.ports import Time` and declares
  `time = Time(loop=43200)`
- **THEN** the declaration behaves exactly as it did when `Time` came from
  `solid_node.node`, and `from solid_node.node import Time` raises
  `ImportError` naming `solid_node.motion.ports`

#### Scenario: The running base is declared and readable off the class

- **WHEN** a root declares `time = Time.running()`
- **THEN** `type(root).time.mode` reads `'running'`, `type(root).time.loop`
  reads `None`, `declared_time(type(root))` returns that declaration, and
  `Time()` with no argument raises naming `Time(loop=...)` and
  `Time.running()`

#### Scenario: Under the running base unbound time reads bare $t

- **WHEN** a root declaring `Time.running()` is rendered with nothing bound
- **THEN** `self.time` on the root and on a nested assembly reads `$t`,
  `set_keyframe(2.5)` makes both read `2.5`, and clearing restores `$t`

#### Scenario: The running base obeys the declaration rules

- **WHEN** a leaf class declares `time = Time.running()`, a class body binds
  `clock = Time.running()`, or a linked child assembly declares it under a
  root and its `simulate()` reads `self.time`
- **THEN** the first two fail at class definition naming the rule and the
  third fails at the read naming the child and the root, exactly as
  `Time(loop=...)` does

#### Scenario: A running root publishes no loop

- **WHEN** a root declaring `Time.running()` is exported and snapshotted at
  a fraction of the timeline
- **THEN** the document's `animation` object carries no `loop` key and is
  byte-identical to an undeclared root's, and the snapshot keyframes the
  fraction

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

Under a root declaring `Time.running()` a bound name MAY instead be the
qualified id of a JOINT COORDINATE the tree publishes — `first.turn`,
`chassis.pose.roll` — the same id the port enumeration reports under the
owning node's instance path. Such an entry SHALL be delivered to the node
that owns the coordinate, a leaf included, and bound through the one
binding path a coordinate assignment takes, so the joint's declared range
and placement apply as for any binding and the binder that called
`set_state` is recorded; a name of several segments SHALL reach the joint
that owns it and never set an attribute of that name. The ambiguity rule
and the rollback rule SHALL cover such an entry as they cover a driver's.
Under any other root a joint coordinate id SHALL be refused exactly as an
undeclared name is.

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
`clear_state` SHALL be no-ops, mirroring `set_keyframe` — except that,
under a running root, an entry addressed to a leaf's own joint coordinate
SHALL bind it as stated above.

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

#### Scenario: A joint coordinate id binds under a running root

- **WHEN** `set_state(**{'first.turn': 12.0, 'chassis.pose.roll': 3.0})` is
  called on a root declaring `Time.running()`, `first` being a leaf owning
  the joint `turn` and `chassis` an assembly owning a six-coordinate joint
- **THEN** `first.turn` reads `12.0` and `chassis.pose.roll` reads `3.0`
  on their owning nodes, both bodies are placed by the values, and no
  attribute named `pose.roll` was set anywhere

#### Scenario: A joint coordinate id is refused under a looping root

- **WHEN** `set_state(**{'first.turn': 12.0})` is called on a root
  declaring `Time(loop=2.0)` or no time base
- **THEN** binding fails naming `first.turn` and listing the declared
  driver ids, and no entry is left bound anywhere in the tree

#### Scenario: A refused binding restores coordinates too

- **WHEN** `set_state(**{'first.turn': 12.0, 'nobody.turn': 1.0})` is called
  on a running root
- **THEN** binding fails naming `nobody.turn` and `first.turn` reads what
  it read before the call
