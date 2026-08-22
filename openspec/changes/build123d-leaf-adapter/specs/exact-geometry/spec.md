## MODIFIED Requirements

### Requirement: Node exactness capability

Every node SHALL expose a read-only `exact` property stating whether its
geometry is available as an exact boundary representation rather than only as
a triangle mesh.

For a leaf, `exact` SHALL be determined by its adapter type and SHALL NOT be
recomputed from rendered content: `CadQueryNode` and `Build123dNode` are
exact; `Solid2Node`, `OpenScadNode` and `JScadNode` are not.

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

- **WHEN** `exact` is read on a `CadQueryNode` or a `Build123dNode`
- **THEN** it is true, without rendering the node

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

#### Scenario: One faceted child makes the composition faceted

- **WHEN** an assembled `FusionNode` holds one `CadQueryNode` and one
  `Solid2Node`
- **THEN** its `exact` is false

#### Scenario: Exactness cannot be read before children are linked

- **WHEN** `exact` is read on an internal node that has not been assembled, so
  its children collection is still empty
- **THEN** it raises, rather than reporting true from an empty collection

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
