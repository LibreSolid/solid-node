# Kinematics Delta: driver-attribute-reads

## MODIFIED Requirements

### Requirement: Multi-driver state binding

The system SHALL let an `AssemblyNode` bind a snapshot of named numeric
driver values with `set_state(**states)`. Binding SHALL merge the given
entries into the assembly's current snapshot (an entry is replaced when
re-given, preserved otherwise), re-render the assembly, and recurse into
rendered children exactly as `set_keyframe` does — including tolerating
a `render()` result that is not a list or tuple by recursing into no
children. Snapshot values SHALL be plain numbers.

Entries SHALL be addressable by qualified id: an entry named with a
dotted instance path (`x_axis.motor`) SHALL be delivered only to the
addressed instance's subtree, with the consumed leading segment
stripped as propagation descends, so sibling instances of one class
hold independent values for a same-named driver. The propagation walk
SHALL link children before recursing, so qualification is computed
against the same names every linked pass derives. The `time` entry
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
same way `set_state` does — re-render, and recurse the same way,
restoring symbolic `$t` behavior for `time`. Because re-renders sweep
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
