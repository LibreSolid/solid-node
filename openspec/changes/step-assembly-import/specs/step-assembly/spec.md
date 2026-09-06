## ADDED Requirements

### Requirement: The document's assembly structure is readable

The system SHALL provide `StepAssembly(path)`, a plain object over a STEP
document that reports the document's structure and reads nothing else. It
SHALL NOT be a node: it declares no geometry, writes no artifact, joins no
tracked source set, and takes no part in a build.

It SHALL read the document through the same per-file cache `StepNode` uses,
so a process that has already read the file pays nothing to read its
structure, and a process that has not pays the read exactly once.

It SHALL report `products`, one entry per product of the document — every
top-level shape, counted once however many times it is placed — carrying
the product's name, its kind (`part`, `sub-assembly` or `root assembly`),
its occurrence count, its solid count and its colour, the same facts the
`StepNode` inventory reports.

#### Scenario: The products of an assembly document are reported

- **WHEN** a `StepAssembly` is constructed over a document holding a root
  assembly, a sub-assembly and several parts
- **THEN** `products` holds one entry per product with its name, kind,
  occurrence count, solid count and colour, and a product placed several
  times appears once with that occurrence count

#### Scenario: The reader is not a node

- **WHEN** a project builds a model that constructs a `StepAssembly`
- **THEN** the reader contributes no artifact and no tracked source file,
  and the model's artifacts are the ones its nodes declare

#### Scenario: The document is read once

- **WHEN** a `StepNode` over a file has already been built in a process and
  a `StepAssembly` is then constructed over the same file
- **THEN** no further read or transfer of the document is performed

### Requirement: Every occurrence of the document is walked

`StepAssembly` SHALL report `occurrences`, one entry per *placement* in the
document, walking nested sub-assemblies to any depth. Each entry SHALL
carry:

- the occurrence's identity within the document, stable whether or not the
  writing CAD package named the component label — the occurrence's label
  name SHALL be reported when the file carries one and SHALL NOT be the
  entry's only identity;
- the name of the product placed;
- the name of the product it is placed in, or the document's root;
- its **placement matrix**, the 4x4 transform of the occurrence in its
  parent product's frame, as the document states it;
- its **world matrix**, the composition of its own placement matrix with
  those of its parents, the parent's matrix on the left;
- its colour when the occurrence's own label carries one, and none
  otherwise — an occurrence SHALL NOT inherit its product's colour, which
  is already reported on the product.

A document whose root free shape holds no components — a file that is one
part — SHALL report that part as a single occurrence at the identity
placement.

#### Scenario: Nested placements compose outward

- **WHEN** a document places a part at `(10, 0, 0)` inside a sub-assembly
  that is itself turned 90° about X and carried to `(0, 20, 0)`
- **THEN** the part's occurrence reports the placement matrix stating
  `(10, 0, 0)` in the sub-assembly's frame, and a world matrix placing it
  at `(10, 20, 0)`

#### Scenario: A product placed at two depths is two occurrences

- **WHEN** a product is placed once inside a sub-assembly and once directly
  in the root
- **THEN** two occurrence entries are reported, naming the same product and
  different parents, each with its own placement and world matrices, and
  the product appears once in `products` with an occurrence count of two

#### Scenario: An unnamed component still has an identity

- **WHEN** the document's writer left a component label unnamed
- **THEN** the occurrence is still reported, distinguishable from every
  other occurrence, and its reported label name is empty rather than
  standing in as its identity

#### Scenario: A one-part file is one occurrence

- **WHEN** a `StepAssembly` is constructed over a file holding a single
  part and no assembly
- **THEN** one occurrence is reported, at the identity placement

### Requirement: A placement is decomposed into the framework's two operations

For every occurrence whose placement is a proper rigid transform, the
reader SHALL derive the pair the framework can express: an angle in degrees
with a unit axis, and a translation vector, such that applying `rotate` and
then `translate` to a node reproduces the placement matrix exactly.

The composition SHALL be the framework's own: a node's operations are
applied in declaration order and premultiplied, so `rotate(angle, axis)`
followed by `translate(vector)` composes to `Translation(vector).matrix()`
times `Rotation(angle, axis).matrix()`. Reproduction SHALL hold to within
1e-9 in every element of the matrix, for every proper rotation the document
can state — including the identity and a 180° turn, where an angle
recovered from the trace alone is not accurate enough.

Where a rotation admits two equivalent statements (an angle about an axis,
or its negation about the negated axis), the reader SHALL state the one
whose axis has a positive largest-magnitude component, so the same
document always yields the same literals and a turn about a principal axis
is stated about the positive axis (`-79.0959` about `(0, 1, 0)`, never
`79.0959` about `(0, -1, 0)`).

#### Scenario: Every placement of a vendor assembly round-trips

- **WHEN** the reader decomposes each of the 55 placements of the
  Internal-Cycloidal-Actuator document
- **THEN** composing `Rotation(angle, axis).matrix()` and then
  `Translation(translation).matrix()` the framework's way reproduces each
  placement matrix to within 1e-9

#### Scenario: A half turn round-trips

- **WHEN** an occurrence's rotation is a 180° turn, such as
  `diag(-1, 1, -1)`
- **THEN** the reported angle is 180° about a unit axis that reproduces the
  matrix to within 1e-9, and not an axis recovered from a vanishing sine

#### Scenario: An unrotated placement is a zero angle

- **WHEN** an occurrence carries a translation and no rotation
- **THEN** the reported angle is zero, the axis is a unit vector, and the
  reported translation is the occurrence's own

#### Scenario: The decomposition is deterministic

- **WHEN** the same document is read twice
- **THEN** each occurrence reports the same angle, the same axis and the
  same translation

### Requirement: An improper placement is reported, not decomposed

A placement that is not a proper rigid transform — a rotation part whose
determinant is not +1, or a transform carrying a scale factor other than 1
— SHALL be reported as improper, carrying its determinant and its scale
factor, and SHALL NOT be decomposed into an angle, an axis and a
translation. The framework's `Rotation` and `Translation` cannot express a
mirror or a scale, and the reader SHALL say so rather than return a pair
that silently loses the transform.

An improper placement SHALL NOT prevent the rest of the document from being
read: the products and every other occurrence are still reported.

#### Scenario: A mirrored placement is refused a decomposition

- **WHEN** a document places a product through a transform whose rotation
  part has determinant −1
- **THEN** the occurrence is reported as improper with that determinant,
  carries no angle/axis/translation pair, and the document's other
  occurrences are unaffected

#### Scenario: A scaled placement is refused a decomposition

- **WHEN** a document places a product through a transform carrying a scale
  factor other than 1
- **THEN** the occurrence is reported as improper with that scale factor
  and carries no angle/axis/translation pair

#### Scenario: A vendor assembly's placements are all proper

- **WHEN** the Internal-Cycloidal-Actuator document is read
- **THEN** none of its 55 occurrences is reported improper

### Requirement: Generated part source

The scaffold SHALL write a `parts.py` holding one `StepNode` subclass per
product of the document that is a part — never for a sub-assembly or the
root — in the declarative class-body idiom.

Each class SHALL declare `step_source`, the path of the STEP file relative
to the directory the module is written into, and `part`, the product's name
exactly as the document carries it. It SHALL declare no colour, so the
document's colour reaches the model through the leaf. It SHALL declare
`angular_deflection = 0.5` under a comment saying why — a vendor document
is fillets and threads, and the framework's 0.1 rad default costs an order
of magnitude in artifact size (19.91 MB against 1.76 MB measured on one
part) — so the generated source builds at a sane size and the pilot sees
the one knob to change, in the file they own.

The class name SHALL be derived from the product name by a stated rule: the
name is split on every run of characters that is neither an ASCII letter
nor an ASCII digit; the first character of each piece is upper-cased when
it is a letter and every other character is kept as written; the pieces are
concatenated, with an underscore inserted wherever a piece ending in a
digit would otherwise run into a piece starting with a digit; and the
result is prefixed `Part` when it does not start with a letter. Two
products whose names derive the same class name SHALL be distinguished by
appending `_2`, `_3` and so on in document order.

The rule is not injective, so the class name SHALL NOT be the record of
which product a class is: `part` carries the exact product name on every
generated class, including on a document holding one product only, so the
product is always recoverable from the generated file.

#### Scenario: A part becomes a leaf class

- **WHEN** the scaffold reads a document holding a part named
  `Fixed_Ring` placed once
- **THEN** `parts.py` holds `class FixedRing(StepNode)` declaring
  `step_source`, `part = 'Fixed_Ring'` and `angular_deflection = 0.5`
  under its comment, and no colour

#### Scenario: Awkward product names become legal class names

- **WHEN** the document holds products named `10010 Stator`,
  `40x50x6mm_Bearing` and `M4_12mm_Screw`
- **THEN** the generated classes are `Part10010Stator`,
  `Part40x50x6mmBearing` and `M4_12mmScrew`, each declaring the exact
  product name in `part`

#### Scenario: Assemblies get no leaf class

- **WHEN** the document holds a root assembly and a sub-assembly
- **THEN** `parts.py` holds no class for either

### Requirement: Generated assembly source

The scaffold SHALL write an `assembly.py` holding one `AssemblyNode`
subclass per assembly product of the document, the root's class named from
the model name.

Each class SHALL declare one child per occurrence of that assembly in its
class body — a `StepNode` subclass from `parts.py` for a part, the
generated `AssemblyNode` subclass for a sub-assembly — with one attribute
name per occurrence. Attribute names SHALL be derived from the product name
by the same splitting rule, lower-cased and joined with underscores,
prefixed `p_` when the result does not start with a letter, and suffixed
`_1`, `_2` … in document order when that assembly places the product more
than once.

Repeated occurrences of one product SHALL be repeated declarations, never
`.repeat(count)`: repeated children are identical children reachable only
by index, and each occurrence here needs its own placement. Repeated
declarations of one class with one set of parameters already share a single
`uniq_id` and therefore a single artifact, so nothing is lost by declaring
them separately.

Each class SHALL define a `render()` that places every child by
`rotate(angle, axis)` followed by `translate(vector)`, using the reader's
decomposition of that occurrence's placement matrix in this assembly's
frame, and SHALL emit neither operation when it is the identity. Each
placement SHALL be preceded by a comment naming the occurrence and the
document the matrix came from.

The generated source SHALL describe the machine at rest: it SHALL declare
no driver, define no `simulate()`, and apply no motion.

#### Scenario: A placement becomes a rest operation

- **WHEN** the document places a part turned 79.0959° about −Y and carried
  to `(0, −0.25, 0)`
- **THEN** the generated `render()` calls `rotate(-79.0959, (0, 1, 0))`
  and then `translate` with that vector on that child, under a comment
  naming the occurrence and the document

#### Scenario: The generated model is faithful to the document

- **WHEN** the generated project is built and each leaf's world placement
  is compared with the reader's world matrix for that occurrence
- **THEN** the two agree to within 0.01 mm at the product's bounding-box
  centre, for every occurrence of the document

#### Scenario: A repeated part is repeated declarations

- **WHEN** a product is placed fourteen times in one assembly
- **THEN** the class body holds fourteen declarations with distinct
  attribute names, `render()` places each at its own occurrence's
  operations, and the fourteen children share one artifact

#### Scenario: A sub-assembly becomes a class placed as a child

- **WHEN** the document holds a sub-assembly placed in the root
- **THEN** `assembly.py` holds an `AssemblyNode` subclass for it, declaring
  its own children at their placements in its own frame, and the root class
  declares it as a child placed at the sub-assembly's occurrence

#### Scenario: The generated machine does not move

- **WHEN** the generated source is read
- **THEN** it declares no driver and defines no `simulate()`
