## ADDED Requirements

### Requirement: Declared tessellation precision

A node that writes an exact STL artifact — an `ExactLeafNode` and every
adapter beneath it (`CadQueryNode`, `Build123dNode`, `Build123dSheetNode`),
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

## MODIFIED Requirements

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
