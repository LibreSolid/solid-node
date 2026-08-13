# printed-pieces Specification

## Purpose

Which solids in an assembled model are the same thing to print, and how many of
each. Piece identity derives from built artifact content, not from the node
class or its constructor parameters, so solids factored into different classes
but building identical geometry are one piece while handed variants are two.
Encodes ADR-043 (content-derived printed-piece identity), which extends ADR-026
(parameter-hashed artifact keys) rather than replacing it: the artifact key
answers "rebuild needed?", a piece id answers "same thing to print?".

The published inventory belongs to the shared tree document (ADR-034), so the
`build-viewer-artifacts` and `export` capabilities each state how their own
producer carries it.

Code: `solid_node/core/pieces.py`, `solid_node/core/serializer.py`,
`solid_node/core/builder.py`, `solid_node/core/export.py`,
`solid_node/viewers/browser.py`.
## Requirements
### Requirement: Printed piece identity is content-derived

A **printed piece** is one distinct solid to manufacture. The system SHALL
identify a piece by a fingerprint of the built artifact's content, never by the
node class, its constructor parameters, its tree name, or its artifact path.

Two rigid nodes whose built artifacts have identical content SHALL be reported
as the same piece even when they come from different classes, different
parameters, or different source files. Rigid nodes whose artifacts differ in
content SHALL be reported as different pieces, including mirrored or otherwise
handed variants of the same shape.

Placement operations are applied outside the built artifact, so they SHALL NOT
affect piece identity: the same solid positioned differently, or animated by
`$t`, remains one piece.

#### Scenario: A repeated part is one piece

- **WHEN** an assembly instantiates the same parameterized part sixteen times at
  sixteen different poses
- **THEN** the published document reports one piece with a count of sixteen, and
  all sixteen tree nodes reference that piece

#### Scenario: Identical geometry from different classes is one piece

- **WHEN** two node classes with different names produce artifacts with
  identical content
- **THEN** both are reported as a single piece whose contributing sources and
  model references include both

#### Scenario: Handed variants stay distinct

- **WHEN** two nodes produce artifacts whose content differs, such as a
  left-handed and a right-handed variant of one shape
- **THEN** they are reported as two pieces

### Requirement: Pieces carry the facts a print layout needs

Each piece entry SHALL carry, derived from the built artifact in the artifact's
own frame with placement excluded: a content-derived `id`; a `name` for
display; `sources`, the project-relative source files of the nodes contributing
to it; `models`, the document-relative model references contributing to it;
`count`, the number of rigid node instances in the tree that resolve to it;
`size`, its bounding extents in millimetres as `[x, y, z]`; `volume`, its
enclosed volume in cubic millimetres; and `watertight`, whether its mesh is
closed.

#### Scenario: A piece reports its printable extents

- **WHEN** a piece's built artifact occupies a 40 × 20 × 238 mm bounding box
- **THEN** its entry reports `size` as those three extents, so a consumer can
  decide whether it fits a given build volume without loading the mesh itself

#### Scenario: An unreadable artifact borrows no identity

- **WHEN** a document walk reaches a rigid node whose built artifact cannot be
  read
- **THEN** no piece is published for it and the read failure is raised, rather
  than identifying the piece by the node's class, parameters, or artifact path

#### Scenario: An unclosed mesh is reported honestly

- **WHEN** a piece's built artifact is not a closed mesh
- **THEN** its entry reports `watertight` as false rather than omitting the
  piece or failing publication

### Requirement: Piece identity is stable and document-independent

A piece id SHALL depend only on the content of its built artifact. It SHALL NOT
depend on tree order, on the artifact's path, on which document publishes it,
or on the run that produced it. Republishing an unchanged model SHALL produce
an identical inventory.

#### Scenario: The same model published two ways agrees

- **WHEN** one model is published both as a normal build snapshot and as a
  static export
- **THEN** both documents report the same piece ids and the same counts, while
  keeping their own distinct model reference roots

#### Scenario: Rebuilding an unchanged model changes nothing

- **WHEN** a build runs again with no source change
- **THEN** the published document is byte-identical to the previous one and no
  consumer is notified of new work

### Requirement: The inventory is additive to the published document

The inventory SHALL be published as a top-level `pieces` list beside `root`,
ordered by first encounter in the document tree, and every rigid node in the
tree SHALL carry a `piece` field holding its piece id. Existing node fields,
including `model`, SHALL keep their current meaning, and the document SHALL
keep declaring its current format and version: this growth is additive, so a
consumer reading only previously published fields is unaffected.

#### Scenario: An existing consumer keeps working

- **WHEN** a consumer written against the previous document reads a document
  containing the inventory
- **THEN** it finds the same `format`, `version`, `animation`, and `root` tree,
  with every previously published node field unchanged

#### Scenario: A tree node resolves to its piece

- **WHEN** a consumer reads a rigid node from the tree
- **THEN** the node's `piece` id matches exactly one entry in the top-level
  `pieces` list

