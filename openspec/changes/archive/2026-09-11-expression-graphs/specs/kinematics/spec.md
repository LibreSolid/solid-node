## MODIFIED Requirements

### Requirement: Tri-consumer operation objects

The system SHALL represent transforms as first-class operation objects
(`Rotation(angle, axis, node)`, `Translation(vector, node)`) that each render
for three consumers: `.scad(obj)` (OpenSCAD wrap), `.mesh(mesh)` (trimesh
transform with animated values resolved to floats; rotation applied in
radians), and `.serialized` (standalone form `['r', angle, axis]` / `['t',
vector]`, with expression strings for scalar values). Each operation SHALL also
provide `.reversed`, and `.matrix()` — its 4×4 homogeneous world matrix, with
animated values resolved through `as_number()` at access time and never cached,
so a keyframe change is always reflected. The registry plus `unserialize()`
SHALL round-trip the standalone form. A new operation type MUST implement all
of these surfaces and register itself.

A standalone shared scalar SHALL be self-contained and compact rather than
requiring its fully expanded spelling or relying on bindings from a previous
publication. Its textual representation need not match the former expanded
string. Node-tree document producers SHALL translate such scalars into the
document's existing expression language and bindings; standalone serialization
SHALL NOT introduce a new grammar into published viewer documents.

Generating SCAD and publishing a document SHALL leave the live operation's
value unchanged. Numeric placement, operation order, reversal and keyframe
updates SHALL retain their existing behavior.

#### Scenario: Wire round-trip

- **WHEN** an operation is serialized and passed through `unserialize()`
- **THEN** an equivalent operation object is reconstructed

#### Scenario: Shared standalone scalar round-trip

- **WHEN** a rotation or translation with a shared scalar is serialized,
  reconstructed and published under the same declared inputs
- **THEN** it evaluates to the original operation's value without requiring
  external bindings from an earlier document

#### Scenario: SCAD expression is complete by itself

- **WHEN** a shared motion scalar is emitted in a SCAD operation
- **THEN** OpenSCAD can resolve it under its original input environment without
  document-global generated bindings or expanded descendant duplication

#### Scenario: Publishing does not change SCAD meaning

- **WHEN** a tree is published and its SCAD is generated again
- **THEN** publication has not mutated the operation values or their meaning

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
token SHALL produce deferred values that preserve shared operands and
serialize to well-formed expressions. The degree-convention dual-mode math
functions SHALL accept it in symbolic mode without project-code changes.

Qualification SHALL fail loudly, naming the node and the cure, when it
would pass through a segment that is not computable (an unlinked
child) or not a legal expression identifier (a list-held child's
derived `<attr>-<index>` name). It SHALL NOT fall back to the bare
local name and SHALL NOT sanitize.

#### Scenario: Two instances of one class qualify distinctly

- **WHEN** one assembly class declaring driver `motor` is instantiated
  as attributes `x_axis` and `y_axis` of a parent, and a linked pass
  reads each instance's driver symbolically
- **THEN** the resulting expressions reference `x_axis.motor`
  and `y_axis.motor` respectively

#### Scenario: Token rides ordinary arithmetic and symbolic trig

- **WHEN** a render computes `asin(0.25 * sin(token * 0.1125))` from a
  driver token in symbolic mode
- **THEN** the deferred value publishes a well-formed expression with the
  qualified id embedded, with no operator or math-function changes in project code

#### Scenario: Illegal id segment fails loudly

- **WHEN** a driver would qualify through a child held in a list
  (derived name `axes-0`)
- **THEN** the operation fails naming the node and the illegal
  segment, rather than emitting an expression that parses as
  subtraction or colliding on the bare name
