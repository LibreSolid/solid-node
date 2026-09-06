## ADDED Requirements

### Requirement: STEP source declaration and freshness

A `StepNode` subclass SHALL declare its part with a `step_source` class
attribute naming a STEP file, resolved relative to the directory of the
Python module defining the subclass; an absolute path SHALL resolve to
itself. The resolved file SHALL be the node's source file for freshness:
its modification time drives artifact currency exactly as an `StlNode`'s
`.stl` and a `JScadNode`'s `.js` do. The wrapper Python module itself SHALL
also be part of the node's tracked file set, transitively with the
project-local modules it imports, because it carries geometry-affecting
code — the `part` selection and the `adjust` hook — so editing the wrapper
SHALL invalidate the node's artifacts. A subclass without `step_source`
SHALL fail at construction with an error naming the class.

#### Scenario: The declared file resolves beside the wrapper module

- **WHEN** a `StepNode` subclass in `parts/gearbox.py` declares
  `step_source = 'gearbox.step'`
- **THEN** the node reads `parts/gearbox.step`, and its build artifacts
  mirror that source location

#### Scenario: Editing the STEP file invalidates the artifacts

- **WHEN** the declared STEP file is modified after a build
- **THEN** the node's artifacts report not-up-to-date and are regenerated
  on the next build

#### Scenario: Editing the wrapper module invalidates the artifacts

- **WHEN** the wrapper `.py` defining the subclass is modified after a
  build — for example its `part` selection or its `adjust` hook changes
- **THEN** the node's artifacts report not-up-to-date and are regenerated
  on the next build

#### Scenario: A missing declaration fails at construction

- **WHEN** a `StepNode` subclass declaring no `step_source` is instantiated
- **THEN** an error is raised naming the class and the missing attribute

### Requirement: One part selected out of the document by product name

A STEP file SHALL be treated as a document of products, one of which a
`StepNode` subclass selects with a `part` class attribute naming the
product as the file carries it. A product is any top-level shape the
document holds — a part or a sub-assembly — counted once however many times
it is placed.

The products a node may select by omission are the document's candidates:
every product except a root that is itself an assembly. A root that is
itself a single part SHALL be its own candidate. When a document has
exactly one candidate, `part` MAY be omitted and that product SHALL be the
node's part — which covers both a file holding one part alone and a file in
which an exporter wraps one part in an assembly. An assembly root SHALL
never be selected by omission, so a document of several components SHALL
NOT be handed to a node as one part unless the node names it; naming it
SHALL still select it.

When a document has more than one candidate and `part` is unset, or when
`part` names a
product the file does not hold, the build SHALL fail with the file's
inventory: one line per product carrying its name, whether it is a part, a
sub-assembly, or the document's root, how many occurrences of it the
document places, how many solids its shape holds, its bounding box and its
volume — so a developer or an agent learns the document's contents from the
failure itself and no separate inspection tool has to exist. A product the
file leaves unnamed SHALL appear in that inventory as unnamed.

When two products of one name are present, selecting that name SHALL fail
naming the ambiguity and describing both, rather than choosing one.

#### Scenario: A file holding one part alone needs no selection

- **WHEN** a `StepNode` wraps a STEP file holding one part and no assembly,
  and declares no `part`
- **THEN** that product is the part and the build succeeds

#### Scenario: One part wrapped in an assembly needs no selection

- **WHEN** a `StepNode` wraps a STEP file in which an assembly root holds
  exactly one part, and declares no `part`
- **THEN** the part is selected — not the assembly root — and the build
  succeeds

#### Scenario: A multi-component root is never selected by omission

- **WHEN** a `StepNode` wraps a document whose assembly root holds several
  products and declares no `part`
- **THEN** the build fails with the inventory rather than selecting the
  root, and naming the root explicitly still selects it

#### Scenario: An unselected multi-product file reports its inventory

- **WHEN** a `StepNode` wrapping a file of several candidate products
  declares no `part`
- **THEN** the build fails with an error listing every product's name,
  kind, occurrence count, solid count, bounding box and volume

#### Scenario: A name the file does not carry reports the inventory

- **WHEN** a `StepNode` declares a `part` that is not a product of its file
- **THEN** the build fails naming the requested part and listing the
  document's products in the same inventory

#### Scenario: A repeated part is one product

- **WHEN** a document places one part at fourteen occurrences and a
  `StepNode` names it
- **THEN** it is one product in the inventory, reported with fourteen
  occurrences, and the node selects it without ambiguity

#### Scenario: An ambiguous name is refused

- **WHEN** a document holds two distinct products of the same name and a
  `StepNode` names it
- **THEN** the build fails naming the ambiguity and describing both
  products, and no artifact is written

#### Scenario: A sub-assembly is a selectable product

- **WHEN** a `StepNode` names a sub-assembly of the document
- **THEN** its geometry is that sub-assembly's components composed at their
  placements within it, as the document holds them

### Requirement: The part arrives in the product's own frame

The geometry a `StepNode` takes from the document SHALL be the product's
own shape in the product's own coordinates, never an occurrence's placed
copy. The document's occurrence placements are the assembly's business and
SHALL NOT be composed into a part's geometry. Bringing a part into a usable
frame belongs to the `adjust` hook or to the node's placement operations,
as it does for an imported mesh.

#### Scenario: Two occurrences yield one unplaced part

- **WHEN** a document places one product twice, far apart, and a `StepNode`
  names that product
- **THEN** the node's artifact holds the product's own unplaced geometry,
  identical whichever occurrence a reader has in mind, and carries neither
  occurrence's translation

#### Scenario: A selected sub-assembly is unplaced in its parent

- **WHEN** a `StepNode` names a sub-assembly that its parent places away
  from the origin
- **THEN** the artifact holds the sub-assembly in its own frame, with its
  components at their internal placements and without its parent's

### Requirement: Correction is code, not knobs

A `StepNode` subclass MAY implement `adjust(self, shape)`, receiving the
selected geometry as a CadQuery `Shape` before admission and returning the
corrected one; what it returns SHALL be what the artifacts hold, so fusion,
tests, export and the viewer all see one geometry. `StepNode` SHALL NOT
offer scale, unit, recenter, or sew constructor parameters.

The adapter module SHALL export a `solids_from_faces(shape, tolerance)`
helper that sews a face-carrying shape into one solid per closed shell, for
an `adjust` hook to call knowingly on a part a vendor published as
surfaces. The helper SHALL state in its documentation what it does and what
it does not guarantee, and it SHALL NOT be applied automatically: a
face-only part fails admission unless the project's own hook sewed it.

#### Scenario: A hook correction reaches the artifact

- **WHEN** a subclass's `adjust` scales the selected shape and the node is
  built
- **THEN** the artifacts hold the scaled geometry, and the node's shape,
  volume and any fusion consuming it reflect the corrected size

#### Scenario: A node without the hook imports the product verbatim

- **WHEN** a subclass defines no `adjust`
- **THEN** its geometry equals the selected product's shape unchanged

#### Scenario: A sewn face-only part is admitted

- **WHEN** a subclass whose product carries only faces implements `adjust`
  by calling `solids_from_faces`
- **THEN** the sewn solid is admitted and built as an ordinary part

### Requirement: Only a solid is admitted

The geometry a `StepNode` holds after `adjust` SHALL contain at least one
solid. When it does not, the build SHALL fail with an error naming the
node, the file, the selected part and what the geometry does hold — its
shells and faces — and SHALL write no artifact. Nothing SHALL be repaired
silently: the framework SHALL NOT sew, heal, or otherwise alter a product
that arrives without a solid.

Admission is judged after the `adjust` hook, so a hook cannot smuggle a
face-only result past the gate and a project may correct a product the
document published as surfaces.

#### Scenario: A face-only product is rejected with what it holds

- **WHEN** a `StepNode` selects a product whose shape carries only faces
  and its subclass defines no `adjust`
- **THEN** the build fails naming the node, the file and the part, and
  stating that the geometry holds no solid but a number of shells and
  faces, and no artifact is written

#### Scenario: A hook that returns no solid is still rejected

- **WHEN** a subclass's `adjust` returns geometry holding no solid
- **THEN** the build fails at the same gate, naming the node

### Requirement: A part's colour comes from the document

A `StepNode` subclass that declares no `color` SHALL take the part's colour
from the document: the product's own surface colour when it has one, else
the colour every occurrence of that product agrees on, else none. The
colour SHALL be published in the form the framework's `color` attribute
already takes, so a colour written into a file by a CAD package is the
colour the viewer shows for that part.

A subclass that declares its own `color` SHALL keep it, and its colour
SHALL NOT require the document to be read.

#### Scenario: A coloured product carries its colour into the build

- **WHEN** a `StepNode` selects a product the document gives a surface
  colour and declares no `color` of its own
- **THEN** the node's colour is that colour, published for the viewer, and
  a part written at a given colour reads back as that colour

#### Scenario: An uncoloured product has no colour

- **WHEN** a `StepNode` selects a product the document gives no colour and
  declares none itself
- **THEN** the node has no colour, exactly as an undeclared node of any
  other adapter

#### Scenario: An undeclared colour survives ordinary construction

- **WHEN** a `StepNode` subclass that declares no `color` is constructed and
  assembled as a child of an assembly, so the framework's own node
  initialisation has run over it
- **THEN** its colour is still the document's colour for its product: an
  assignment of no colour during construction does not count as declaring
  one

#### Scenario: A declared colour wins

- **WHEN** a `StepNode` subclass declares a `color` and its product also
  carries one in the document
- **THEN** the declared colour is the node's colour

### Requirement: One document read per file per process

A STEP document SHALL be read and transferred at most once per file per
process, and the result cached keyed on the file's path and modification
time, evicting the entry for a file whose modification time has changed.
Several nodes selecting different parts of one document SHALL cost one
read between them.

A node whose artifacts are current SHALL NOT cause its document to be read
at all for the sake of rebuilding them.

#### Scenario: Many nodes over one file cost one read

- **WHEN** a project builds several `StepNode`s declaring the same
  `step_source`
- **THEN** the document is read and transferred once in that process and
  every node is served from the cached read

#### Scenario: A replaced file is read again

- **WHEN** a STEP file is replaced after it has been read and a node
  selects from it again
- **THEN** the stale cache entry for that path is dropped and the new file
  is read

#### Scenario: A current artifact is not rebuilt from the document

- **WHEN** a `StepNode` whose artifacts are up to date is assembled
- **THEN** its geometry is not re-derived and its artifacts are not
  rewritten

### Requirement: The STEP part is an exact leaf

`StepNode` SHALL be an exact adapter under the `exact-geometry` capability:
`exact` is true, `shape()` returns the selected, adjusted, admitted
geometry in the node's own frame, its `.brep` artifact is persisted and
reloaded like any exact leaf's, it fuses exactly with the other exact
adapters, and the spatial assertions answer on its B-rep. Its STL artifact
SHALL be written by the exact leaf path and SHALL therefore honour the
`linear_deflection` and `angular_deflection` the node declares, at the same
defaults every exact leaf has.

Producing its artifacts SHALL NOT require OpenSCAD or any other external
tool, and reading a STEP file SHALL NOT be a cost paid by a project that
declares no `StepNode`.

#### Scenario: The adapter is exact

- **WHEN** `exact` is read on a `StepNode`
- **THEN** it is true, and `shape()` returns the part's geometry in its own
  frame

#### Scenario: A STEP part fuses exactly with a modelled part

- **WHEN** a `FusionNode` fuses a `StepNode` with an overlapping
  `CadQueryNode`
- **THEN** the fusion is exact and its shape is one solid

#### Scenario: A declared precision shapes the STEP part's mesh

- **WHEN** a `StepNode` declares `angular_deflection = 0.5`
- **THEN** its STL artifact holds strictly fewer triangles than the same
  node declaring nothing, and its `.brep` is unchanged
