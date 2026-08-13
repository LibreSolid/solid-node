## ADDED Requirements

### Requirement: Node exactness capability

Every node SHALL expose a read-only `exact` property stating whether its
geometry is available as an exact boundary representation rather than only as
a triangle mesh.

For a leaf, `exact` SHALL be determined by its adapter type and SHALL NOT be
recomputed from rendered content: `CadQueryNode` is exact; `Solid2Node`,
`OpenScadNode` and `JScadNode` are not.

For an internal node, `exact` SHALL be true when every child is exact. This
composition rule is deliberately the opposite of `rigid`, which is fixed by
node type and never derived from children. The two answer different kinds of
question: rigidity is a promise the node makes about what it produces — a
fusion is one solid whatever lies beneath it — whereas exactness is a
capability that genuinely depends on what lies beneath, because one faceted
child makes an exact composition impossible.

Because an internal node's children are linked during `assemble()` and the
default is an empty collection, reading `exact` on an internal node that has
not yet linked its children SHALL raise rather than answer vacuously true.

The property SHALL be read-only. A project SHALL NOT be able to declare a node
exact.

#### Scenario: An exact leaf

- **WHEN** `exact` is read on a `CadQueryNode`
- **THEN** it is true, without rendering the node

#### Scenario: A faceted leaf

- **WHEN** `exact` is read on a `Solid2Node`, `OpenScadNode` or `JScadNode`
- **THEN** it is false

#### Scenario: A fusion of exact children

- **WHEN** `exact` is read on an assembled `FusionNode` whose every descendant
  is a `CadQueryNode`
- **THEN** it is true

#### Scenario: One faceted child makes the composition faceted

- **WHEN** an assembled `FusionNode` holds one `CadQueryNode` and one
  `Solid2Node`
- **THEN** its `exact` is false

#### Scenario: Exactness cannot be read before children are linked

- **WHEN** `exact` is read on an internal node that has not been assembled, so
  its children collection is still empty
- **THEN** it raises, rather than reporting true from an empty collection

### Requirement: Exact geometry accessor

An exact node SHALL provide `shape()`, returning its geometry as an OCCT shape
in the node's own local frame — the same frame its `.stl` and its cached base
mesh use, with neither its own operations nor any ancestor's composed into it.
A node whose geometry comprises several solids SHALL return them as one
compound.

Reading `shape()` on a node that is not exact SHALL raise, naming the node.

Placement SHALL remain the caller's responsibility and SHALL use the same
composed matrices the mesh path uses, so an exact comparison and a mesh
comparison place the same node identically: world composition for collision
questions, enclosing-solid composition for connectivity questions.

#### Scenario: The accessor returns unplaced geometry

- **WHEN** `shape()` is read on an exact leaf carrying placement operations
- **THEN** the returned shape is in the node's local frame, with no operation
  applied

#### Scenario: A faceted node has no exact geometry

- **WHEN** `shape()` is called on a node whose `exact` is false
- **THEN** it raises naming that node

#### Scenario: Exact and mesh placement agree

- **WHEN** the same node is placed for an exact comparison and for a mesh
  comparison at one testing instant
- **THEN** both use the same composed matrix and describe the same pose

### Requirement: Exact composition of a fused solid

A `FusionNode` whose subtree is exact SHALL compose its `shape()` as the OCCT
fuse of its children's shapes, each placed by the operations that position it
within the fusion. The fuse is the printed solid the fusion represents.

The fuse SHALL succeed for children that meet on exactly coincident faces — a
zero-clearance fit is a normal modelling result and is the case a mesh union
handles least reliably.

#### Scenario: Children are fused into one solid

- **WHEN** an exact `FusionNode` fuses two overlapping children
- **THEN** its shape is a single solid whose volume is the union of theirs

#### Scenario: Exactly coincident faces fuse

- **WHEN** an exact `FusionNode` fuses a shaft into a bore of exactly equal
  diameter, so their cylindrical faces coincide
- **THEN** the fuse yields one solid rather than failing or leaving two

### Requirement: Exact geometry is persisted and reloaded

An exact rigid node's shape SHALL be persisted as a build artifact and
reloaded from it, so that consumers do not re-run the project's geometry
backend to obtain it. A shape reloaded from a current artifact SHALL be
equivalent to the shape the node would render.

Loaded shapes SHALL be cached in memory per artifact and modification time,
evicting a stale entry for the same artifact, in the manner of the existing
base-mesh and Manifold caches.

#### Scenario: A current artifact is reused

- **WHEN** an exact node's shape is requested and its artifact is current
- **THEN** the shape is read from the artifact and the geometry backend does
  not render the node

#### Scenario: A rebuilt artifact replaces its cached shape

- **WHEN** an exact node's source changes and its artifact is rebuilt
- **THEN** the next request returns the new shape and the entry cached under
  the previous modification time is evicted

### Requirement: Boolean kernel failures are reported, never masked

When the exact Boolean kernel reports that an operation did not complete or
produced errors, the framework SHALL raise, naming the operation and the nodes
involved. It SHALL NOT substitute a mesh result for the failed exact one.

A silent fallback would return a verdict from the representation whose
imprecision this capability exists to remove, and would do so precisely on the
geometry the kernel found hardest — the case most likely to be a real defect.

#### Scenario: A failed exact Boolean is not answered by the mesh path

- **WHEN** an exact intersection is requested for two solids and the kernel
  reports failure
- **THEN** the framework raises naming both nodes, and no mesh Boolean is run
  to produce a verdict in its place
