# kinematics delta: instance-qualified drivers

## ADDED Requirements

### Requirement: Instance-qualified driver identity

The system SHALL identify a driver instance by a qualified id: the
dotted instance path from the addressing root to the declaring node,
joined with the class-local driver name (`x_axis.motor`); a driver
declared on the root itself SHALL keep its bare local name. The id
SHALL be computed from the parent-derived linked child names — the
same names the serialized document publishes for nodes — during a walk
that links parents to children before recursing, and SHALL never be
stored on the node or the declaration.

A symbolic driver reference SHALL be represented by a token whose
string form is exactly the qualified id, interoperating with the
existing symbolic expression machinery: ordinary arithmetic on the
token SHALL produce well-formed expression strings, and the
degree-convention dual-mode math functions SHALL accept it in symbolic
mode unchanged.

Qualification SHALL fail loudly, naming the node and the cure, when it
would pass through a segment that is not computable (an unlinked
child) or not a legal expression identifier (a list-held child's
derived `<attr>-<index>` name). It SHALL NOT fall back to the bare
local name and SHALL NOT sanitize.

#### Scenario: Two instances of one class qualify distinctly

- **WHEN** one assembly class declaring driver `motor` is instantiated
  as attributes `x_axis` and `y_axis` of a parent, and a linked pass
  reads each instance's driver symbolically
- **THEN** the resulting expression strings reference `x_axis.motor`
  and `y_axis.motor` respectively

#### Scenario: Token rides ordinary arithmetic and symbolic trig

- **WHEN** a render computes `asin(0.25 * sin(token * 0.1125))` from a
  driver token in symbolic mode
- **THEN** the expression string is well-formed with the qualified id
  embedded, with no operator or math-function changes in project code

#### Scenario: Illegal id segment fails loudly

- **WHEN** a driver would qualify through a child held in a list
  (derived name `axes-0`)
- **THEN** the operation fails naming the node and the illegal
  segment, rather than emitting an expression that parses as
  subtraction or colliding on the bare name

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

`render()` SHALL read the bound snapshot through a `state` mapping on
the assembly, by the driver's local name as declared on that node.
Reading a name that is not bound SHALL raise an error that names the
missing entry and `set_state`, so a state-consuming assembly rendered
without a snapshot fails loudly rather than guessing. The `time` name
is the exception: it participates in the snapshot but falls back to
symbolic `$t` through the `time` property when unbound, preserving the
ADR-008 animation path.

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

#### Scenario: Two named drivers bind numerically

- **WHEN** `set_state(motor=4000, lift=2.5)` is called on an assembly
  whose `render()` derives operations from `self.state['motor']` and
  `self.state['lift']`
- **THEN** the assembly re-renders with both values as plain numbers
  and `node.mesh` reflects the resulting pose absolutely

#### Scenario: Merging preserves unrelated entries

- **WHEN** `set_state(motor=4000)` is followed by `set_state(lift=1.0)`
- **THEN** the snapshot holds both `motor=4000` and `lift=1.0`

#### Scenario: Sibling instances bind independently

- **WHEN** a parent holding `x_axis` and `y_axis` instances of one
  `motor`-declaring class binds `{'x_axis.motor': 8000,
  'y_axis.motor': 2000}`
- **THEN** each instance renders with its own value and the two poses
  differ accordingly

#### Scenario: Ambiguous bare name fails loudly

- **WHEN** `set_state(motor=1234)` is called on a tree where two
  sibling instances both declare `motor`
- **THEN** binding fails listing `x_axis.motor` and `y_axis.motor`,
  and neither instance's state changes

#### Scenario: Time stays global

- **WHEN** `set_state(time=0.25)` is called on a tree with colliding
  project-driver names
- **THEN** every descendant receives `time=0.25` flat, with no
  qualification required

#### Scenario: Unbound state access fails loudly

- **WHEN** an assembly whose `render()` reads `self.state['motor']` is
  rendered with no snapshot bound
- **THEN** an error is raised naming `motor` and `set_state`

#### Scenario: State cycles do not accumulate operations

- **WHEN** `set_state` is called many times in sequence on the same
  assembly (as a stepping loop does every tick)
- **THEN** each driven child holds exactly the operations one render
  applies, and static placement applied outside any assembly render is
  still present

#### Scenario: Clearing state restores symbolic time

- **WHEN** `set_state(time=0.5, motor=100)` is followed by
  `clear_state()`
- **THEN** the assembly's `time` reports symbolic `$t` again and the
  snapshot is empty

#### Scenario: Leaf tolerance

- **WHEN** `set_state(motor=10)` propagation reaches a leaf node
- **THEN** the call is a no-op on that leaf
