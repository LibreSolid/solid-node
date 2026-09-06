## MODIFIED Requirements

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
