# exact-geometry Specification

## Purpose
TBD - created by archiving change exact-brep-geometry. Update Purpose after archive.
## Requirements
### Requirement: Node exactness capability

Every node SHALL expose a read-only `exact` property stating whether its
geometry is available as an exact boundary representation rather than only as
a triangle mesh.

For a leaf, `exact` SHALL be determined by its adapter type and SHALL NOT be
recomputed from rendered content: `CadQueryNode`, `Build123dNode`,
`Build123dSheetNode`, `StepNode` and `MolejoNode` are exact; `Solid2Node`,
`OpenScadNode` and `JScadNode` are not. `StepNode`'s geometry is
a boundary representation the moment it is read — the document it selects a
product from is itself exact — which is the whole difference between
importing a solid and importing a mesh. `MolejoNode`'s exact geometry is
per-instant — the solid molejo's B-rep evaluator constructs at the bound
snapshot, under the `flexible-parts` capability — and its exactness is fixed
by type like every other adapter's, not by installation state or binding.

For an internal node, `exact` SHALL be true when every child is exact. This
composition rule is deliberately the opposite of `rigid`, which is fixed by
node type and never derived from children. The two answer different kinds of
question: rigidity is a promise the node makes about what it produces — a
fusion is one solid whatever lies beneath it — whereas exactness is a
capability that genuinely depends on what lies beneath, because one faceted
child makes an exact composition impossible.

Exactness SHALL NOT require the children to share one backend. Every exact
adapter yields geometry in the same boundary representation, so a subtree
mixing exact backends is exact by the same rule, with no backend-agreement
condition beyond it.

Because an internal node's children are linked during `assemble()` and the
default is an empty collection, reading `exact` on an internal node that has
not yet linked its children SHALL raise rather than answer vacuously true.

The property SHALL be read-only. A project SHALL NOT be able to declare a node
exact.

#### Scenario: An exact leaf

- **WHEN** `exact` is read on a `CadQueryNode`, a `Build123dNode`, a
  `Build123dSheetNode`, a `StepNode` or a `MolejoNode`
- **THEN** it is true, without rendering the node

#### Scenario: An imported solid is exact where an imported mesh is not

- **WHEN** `exact` is read on a `StepNode` and on an `StlNode`
- **THEN** the `StepNode` reports true and the `StlNode` reports false, and
  a fusion over the `StepNode` composes exactly while one over the
  `StlNode` does not

#### Scenario: A faceted leaf

- **WHEN** `exact` is read on a `Solid2Node`, `OpenScadNode` or `JScadNode`
- **THEN** it is false

#### Scenario: A fusion of exact children

- **WHEN** `exact` is read on an assembled `FusionNode` whose every descendant
  is a `CadQueryNode`
- **THEN** it is true

#### Scenario: A fusion mixing exact backends

- **WHEN** `exact` is read on an assembled `FusionNode` holding one
  `CadQueryNode` and one `Build123dNode`
- **THEN** it is true

#### Scenario: A sheet leaf composes exactly

- **WHEN** `exact` is read on an assembled `FusionNode` holding one
  `Build123dSheetNode` and one `CadQueryNode`
- **THEN** it is true, and the fusion's `shape()` fuses the sheet's extruded
  solid with the other child

#### Scenario: A flexible leaf composes exactly under an assembly

- **WHEN** `exact` is read on an assembled `AssemblyNode` holding one
  `MolejoNode` and one `CadQueryNode`
- **THEN** it is true, and an exact question at a bound snapshot decides on
  the B-rep solids of both children

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

The fuse SHALL be performed identically whichever exact adapters produced the
children, and its result SHALL be one solid when the children overlap, so a
part modelled partly in CadQuery and partly in build123d composes as one
printed solid.

#### Scenario: Children are fused into one solid

- **WHEN** an exact `FusionNode` fuses two overlapping children
- **THEN** its shape is a single solid whose volume is the union of theirs

#### Scenario: Exactly coincident faces fuse

- **WHEN** an exact `FusionNode` fuses a shaft into a bore of exactly equal
  diameter, so their cylindrical faces coincide
- **THEN** the fuse yields one solid rather than failing or leaving two

#### Scenario: Children from different exact backends fuse

- **WHEN** an exact `FusionNode` fuses an overlapping `CadQueryNode` child and
  `Build123dNode` child
- **THEN** its shape is a single solid, as it is for two children of one
  backend

### Requirement: Exact geometry is persisted and reloaded

An exact rigid node's shape SHALL be persisted as a build artifact and
reloaded from it, so that consumers do not re-run the project's geometry
backend to obtain it. A shape reloaded from a current artifact SHALL be
equivalent to the shape the node would render.

Loaded shapes SHALL be cached in memory per artifact and modification time,
evicting a stale entry for the same artifact, in the manner of the existing
base-mesh and Manifold caches.

Measurements DERIVED from a loaded shape and independent of where it is
placed — its own bounding box, and the bounding boxes of its faces — SHALL be
cached under that same shape identity, computed at most once per identity, and
evicted with it when its artifact is rebuilt. A shape with no such identity —
one composed for a single comparison, or read from a node whose artifact is
not current — SHALL be measured directly and SHALL NOT be cached, so a stale
identity can never serve another shape's measurement.

Because such a measurement is served under an identity that names only the
artifact and its modification time, it SHALL be a function of the shape's
EXACT geometry alone. A face's cached bounding box SHALL enclose that face's
exact surface and SHALL NOT be derived from any triangulation the shape may
carry, so that attaching, replacing or discarding a tessellation cannot change
a measurement already served under that identity.

#### Scenario: A current artifact is reused

- **WHEN** an exact node's shape is requested and its artifact is current
- **THEN** the shape is read from the artifact and the geometry backend does
  not render the node

#### Scenario: A rebuilt artifact replaces its cached shape

- **WHEN** an exact node's source changes and its artifact is rebuilt
- **THEN** the next request returns the new shape and the entry cached under
  the previous modification time is evicted

#### Scenario: A shape's face bounds are measured once and evicted with it

- **WHEN** the bounding boxes of a loaded shape's faces are requested
  repeatedly, and then its artifact is rebuilt
- **THEN** they are computed once for that identity and served from the cache
  afterwards, and the rebuild drops the entry so the next request measures the
  new shape

#### Scenario: A shape with no identity is measured directly

- **WHEN** the bounding boxes of the faces of a shape with no cache identity
  are requested
- **THEN** they are computed from that shape and no cache entry is created

#### Scenario: A triangulation does not shrink a face's bounds

- **WHEN** a curved exact shape carries a triangulation whose vertices lie on
  its surface, and its faces' bounding boxes are requested
- **THEN** each box still encloses the exact surface, reaching the true extent
  of the curved face rather than the tessellation's inscribed extent

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

### Requirement: An exact artifact's mesh carries no degenerate triangles

The STL artifact written for an exact node — a leaf's tessellation or a
fused solid's — SHALL contain no degenerate (zero-area) triangles and no
vertex left unreferenced by their removal. Removal SHALL happen after
tessellation, at whatever precision the node declares, and SHALL be the
only thing that changes the triangles OCCT produced: the artifact's volume
and the surface it encloses are those of the tessellation at the node's
declared linear and angular deflection.

#### Scenario: A leaf whose tessellation emits degenerate triangles

- **WHEN** an exact leaf's shape tessellates to a mesh containing zero-area
  triangles and its STL artifact is written
- **THEN** the artifact holds every non-degenerate triangle of that mesh,
  none of the degenerate ones, and no vertex only they referenced

#### Scenario: A fused solid's export is unchanged

- **WHEN** a fused exact solid's STL artifact is written
- **THEN** it carries no degenerate triangles, as before

#### Scenario: Degenerate removal follows a declared precision

- **WHEN** an exact node declaring a coarse `angular_deflection`
  tessellates to a mesh containing zero-area triangles
- **THEN** its artifact is that coarse tessellation with the degenerate
  triangles and their orphaned vertices removed, and nothing else

### Requirement: Declared tessellation precision

A node that writes an exact STL artifact — an `ExactLeafNode` and every
adapter beneath it (`CadQueryNode`, `Build123dNode`, `Build123dSheetNode`,
`StepNode`),
and a `FusionNode` whose subtree is exact — SHALL take the tolerances of
that artifact's tessellation from two class attributes it MAY declare,
named after the OCCT quantities they set:

- `linear_deflection` — the maximum distance, in millimetres, between the
  mesh and the surface it approximates;
- `angular_deflection` — the maximum angle, in radians, between the
  normals of two adjacent facets.

A node that declares neither SHALL be tessellated at `linear_deflection =
0.1` and `angular_deflection = 0.1`, the values the framework has always
used, so an existing project's artifacts are byte-for-byte what they were.
A node MAY declare either attribute alone; the other keeps its default.
The defaults SHALL be the same for every exact adapter: no adapter SHALL
carry a default of its own, so what precision a part is written at is
readable from the project's own source rather than from which backend the
part came from.

Each value SHALL be read at the point the artifact is written and SHALL be
a positive finite number. A value that is not — zero, negative, infinite,
NaN, or not a number at all — SHALL raise, naming the node and the
attribute, and no artifact SHALL be written.

The declaration SHALL NOT be a constructor parameter and SHALL NOT enter
the node's artifact identity: two tessellations of one solid are one node's
artifact at two times, not two nodes. Currency SHALL follow the ordinary
node-scoped content path instead: the attribute is declared in the module
defining the node class, which the node already tracks in its source set,
so editing the declared value makes the node's artifacts stale and the next
build rewrites them.

The faceted adapters — `Solid2Node`, `OpenScadNode`, `JScadNode` and
`StlNode` — SHALL NOT carry these attributes. The framework does not
tessellate their geometry: their meshes arrive already faceted from a
backend or a file, and there is no tessellation for a deflection to shape.
`MolejoNode` is tessellated by molejo's own evaluator and is outside this
requirement.

#### Scenario: A coarse angular declaration yields a coarser artifact

- **WHEN** two `CadQueryNode` classes render the same curved solid, one
  declaring `angular_deflection = 0.5` and the other declaring nothing
- **THEN** both artifacts are written and the declaring node's artifact
  holds strictly fewer triangles than the default one's

#### Scenario: An imported solid takes the same defaults

- **WHEN** a `StepNode` declaring neither attribute is built
- **THEN** its STL artifact is tessellated at 0.1 mm and 0.1 rad, as every
  other exact leaf's is, and declaring `angular_deflection = 0.5` on it
  coarsens only that node's artifact

#### Scenario: A node that declares nothing is unchanged

- **WHEN** an exact leaf declaring neither attribute is built
- **THEN** its artifact is the one the framework wrote before this
  requirement existed, tessellated at 0.1 mm and 0.1 rad

#### Scenario: One attribute declared alone

- **WHEN** an exact leaf declares `angular_deflection = 0.5` and no
  `linear_deflection`
- **THEN** it is tessellated at 0.5 rad and at the default 0.1 mm

#### Scenario: A value that is not a positive number is refused

- **WHEN** an exact leaf declaring `linear_deflection = 0` (or a negative,
  infinite, or non-numeric value) is built
- **THEN** the build raises naming that node and `linear_deflection`, and
  no STL artifact is written for it

#### Scenario: Editing the declaration rebuilds the artifact

- **WHEN** a built and current node's declared deflection is edited in the
  module that declares the class, and the project is built again
- **THEN** the node reports not up to date and its STL artifact is
  rewritten at the new precision

#### Scenario: The declaration is not artifact identity

- **WHEN** a node's declared deflection is changed
- **THEN** the node's artifact path is the one it had before, rewritten in
  place, rather than a second artifact under a new key

#### Scenario: A fusion declares its own precision

- **WHEN** an exact `FusionNode` declaring `angular_deflection = 0.5` fuses
  children that declare nothing
- **THEN** the fused solid's artifact is tessellated at 0.5 rad, and each
  child's own artifact is tessellated at the default

#### Scenario: A fusion does not inherit its children's precision

- **WHEN** an exact `FusionNode` declaring nothing fuses a child that
  declares `angular_deflection = 0.5`
- **THEN** the fused solid's artifact is tessellated at the default
  0.1 rad, and only the child's own artifact is coarse

### Requirement: Precision shapes the mesh and nothing else

A declared tessellation precision SHALL shape only the node's STL artifact.
The node's `.brep` artifact and its `shape()` SHALL be identical whatever
is declared: exactness is a property of the geometry, and a mesh tolerance
is a property of one derived representation of it.

Everything downstream that reads the mesh SHALL therefore see the declared
precision, and this SHALL be treated as a consequence of the declaration
rather than as a separate contract: the viewer and the export carry the
artifact's triangles; a comparison answered on the faceted path — every
comparison of a run under the faceted kernel — reaches its verdict on those
triangles; and printed-piece identity, which is a fingerprint of the built
artifact's content, changes when the mesh changes, so a node redeclared at
a new precision is a different piece from the one built before.

#### Scenario: The exact geometry is unaffected

- **WHEN** the same exact leaf is built once with a coarse
  `angular_deflection` and once with none
- **THEN** its `.brep` artifact and the shape `shape()` returns are the
  same in both builds, and only the `.stl` differs

#### Scenario: A coarse declaration changes the piece fingerprint

- **WHEN** a node's declared deflection is changed and the project is
  rebuilt
- **THEN** the node's printed-piece id is not the id it had before,
  because piece identity is derived from artifact content
