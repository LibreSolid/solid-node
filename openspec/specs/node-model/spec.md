# Node Model Specification

## Purpose

The core composite node tree that models a mechanical project: base classes,
the render lifecycle, rigid/non-rigid semantics, multi-backend leaf adapters,
and node identity/naming. Encodes ADR-001 (composite pattern), ADR-002
(template-method lifecycle), ADR-003 (rigid vs non-rigid), ADR-004 (multi-CAD
backend adapters), and ADR-026 (parameter-hashed artifact keys vs tree names).

Code: `solid_node/node/` (`base.py`, `internal.py`, `leaf.py`, `fusion.py`,
`assembly.py`, `adapters/`).

## Requirements

### Requirement: Composite node tree

The system SHALL model a project as a tree of nodes rooted in
`AbstractBaseNode`, where `InternalNode` subclasses compose children and
`LeafNode` subclasses generate geometry. An `InternalNode.render()` SHALL
return a list or tuple of node instances; a `LeafNode.render()` SHALL return a
single geometry object, never a list. Validation runs on every `assemble()`
and enforces these contracts before any SCAD generation.

#### Scenario: Internal node returns children

- **WHEN** an `InternalNode` subclass's `render()` returns a list of
  `AbstractBaseNode` instances
- **THEN** `assemble()` links each child, assembles it, and unions the
  results (union applied only when there is more than one child)

#### Scenario: Structural contract violations are rejected

- **WHEN** an `InternalNode.render()` returns a non-list, returns an element
  that is not an `AbstractBaseNode`, or returns an instance of its own type
- **THEN** validation raises an error during `assemble()`
- **WHEN** a `LeafNode.render()` returns a list, or returns an object whose
  module does not start with the adapter's declared `namespace`
- **THEN** validation raises an error during `assemble()`

### Requirement: Template-method render lifecycle

The system SHALL control the node lifecycle through `assemble()`, which users
do not override: render → validate → `as_scad` → `generate_scad` → optional
optimized STL import → apply queued operations. `assemble()` SHALL be
idempotent — the result is memoized and `render()` is called at most once per
instance.

When a leaf node is rigid, has `optimize = True`, and its artifact is up to
date, `assemble()` SHALL import that artifact without rendering it: `render()`
and `as_scad()` SHALL NOT run. Queued operations SHALL still be applied, and
the assembled result SHALL be the same as if the node had been rendered. A node
whose artifact is absent or stale SHALL follow the full lifecycle above.

#### Scenario: Assemble is memoized

- **WHEN** `assemble()` is called twice on the same instance
- **THEN** `render()` runs only once and the cached result is returned

#### Scenario: Optimized import of cached STL

- **WHEN** a node has `optimize = True`, is rigid, and its STL is up to date
- **THEN** `assemble()` imports the STL (`import_stl`) instead of inlining
  the SCAD model, and queued operations are applied after the import

#### Scenario: An up-to-date leaf is not rendered

- **WHEN** a rigid optimizing leaf's artifact is up to date and `assemble()` runs
- **THEN** the node's `render()` is not called and no CAD geometry is computed

#### Scenario: A stale leaf is rendered

- **WHEN** any file tracked for that leaf has changed since its artifact was written
- **THEN** `assemble()` renders the node and regenerates the artifact

### Requirement: Rigid vs non-rigid distinction

The system SHALL distinguish rigid nodes (`rigid = True`; can produce a cached
STL) from non-rigid nodes. Rigidity SHALL be determined by node type and SHALL
NOT be recomputed from a node's children: `LeafNode` and `FusionNode` are
rigid, `AssemblyNode` is non-rigid. Only rigid nodes generate STL files.

A `FusionNode` SHALL reject a non-rigid child. Fusion combines solids into one
solid; an assembled thing cannot be fused. The rejection SHALL name the fusion
and the offending child and SHALL happen during render validation, before any
geometry is produced.

A **topmost rigid node** is a rigid node whose parent is non-rigid, or the root
node when the root is itself rigid. Because a fusion cannot contain an
assembly, every rigid node is either a topmost rigid node or a descendant of
exactly one. A topmost rigid node is the boundary of one printed solid and the
unit selected by whole-solid assertions; this definition does not itself run
an assertion or guarantee that the solid's geometry is connected.

#### Scenario: An assembly cannot be fused

- **WHEN** a `FusionNode` renders a child that is an `AssemblyNode`, or any
  other non-rigid node
- **THEN** an exception is raised naming the fusion and that child, and no
  geometry is produced

#### Scenario: Rigidity is not recomputed from children

- **WHEN** a `FusionNode` renders a subtree of leaves and nested fusions
- **THEN** it remains rigid, and its rigidity is its type's, not derived by
  combining its children's

#### Scenario: STL access on non-rigid node

- **WHEN** the `stl` property is read on a non-rigid node
- **THEN** an exception is raised

#### Scenario: The topmost rigid node under an assembly

- **WHEN** an `AssemblyNode` holds a `FusionNode` that itself holds leaves and
  a nested fusion
- **THEN** the outer `FusionNode` is the topmost rigid node of that branch, and
  the leaves and nested fusion are not

#### Scenario: The solid boundary does not imply a test

- **WHEN** a topmost rigid node's STL contains disconnected geometry and no
  project test calls `assertNoDisconnectedSolids`
- **THEN** its status as a topmost rigid node neither rejects the model nor
  causes a connectivity assertion to run

### Requirement: Animation-time access restrictions

The system SHALL restrict the `time` property to `AssemblyNode`. `LeafNode`
and `FusionNode` SHALL raise on `time` access, preserving the invariant that
rigid geometry is time-invariant (precondition for STL caching, ADR-003/008).

#### Scenario: Fusion cannot animate

- **WHEN** a `FusionNode` subclass reads `self.time` during `render()`
- **THEN** an exception is raised directing the user to `AssemblyNode`

### Requirement: Multi-backend leaf adapters

The system SHALL provide leaf adapters for multiple CAD backends —
`Solid2Node` (solid2/SolidPython2), `CadQueryNode`, `OpenScadNode` (with
`scad_source` and optional `module_name`), and `JScadNode` (with
`jscad_source`) — all compiled through OpenSCAD as the universal target.
Each adapter SHALL implement `as_scad()`; adapters declaring a `namespace`
(`Solid2Node`, `CadQueryNode`, `OpenScadNode`) get namespace-based render
validation, while `JScadNode` declares none and skips that check.

An adapter that produces its artifact inside `as_scad()` SHALL produce it only
when that artifact is not up to date, and SHALL return the same SCAD output in
either case.

#### Scenario: OpenSCAD source adapter

- **WHEN** an `OpenScadNode` subclass declares `scad_source` and is
  instantiated with args/kwargs
- **THEN** the referenced `.scad` module is called with those args in the
  generated SCAD, with `module_name` defaulting to the file's basename

#### Scenario: CadQuery adapter routes through STL

- **WHEN** a `CadQueryNode` is assembled
- **THEN** the CadQuery object is exported to STL and re-imported via
  `import_stl` in the SCAD output

#### Scenario: An adapter does not rewrite a current artifact

- **WHEN** `as_scad()` runs on a `CadQueryNode` or `JScadNode` whose artifact is up to date
- **THEN** no export or external renderer runs, and the returned SCAD output is unchanged

### Requirement: Parameter-hashed artifact identity

The system SHALL give each node instance a `uniq_id` of the form
`<readable-prefix>-<12-hex-sha256>`, hashed over a canonical serialization of
the class `__qualname__`, positional args in order, and kwargs sorted by key.
The readable prefix is sanitized and truncated to 60 characters; the hash is
computed over the full untruncated serialization. Build artifact basenames are
always `<script-name>-<uniq_id>`. The `name=` kwarg SHALL never influence
`uniq_id`.

#### Scenario: Parameter change invalidates artifact key

- **WHEN** the same node class is instantiated with any differing parameter
  value
- **THEN** the two instances have different `uniq_id`s and separate build
  artifacts

#### Scenario: Identical instances share artifacts

- **WHEN** the same class is instantiated twice with identical args
- **THEN** both instances share one `uniq_id` and one cached artifact set

#### Scenario: Distinct no-arg classes never collide

- **WHEN** two different no-arg node classes are built
- **THEN** their `uniq_id`s differ because the class qualname is part of the
  serialization

### Requirement: Tree naming from parent attributes

The system SHALL derive a child's tree name when it is linked: an explicit
`name=` always wins; otherwise the parent attribute holding the child is used
(a plain attribute wins over list membership; list members become
`<attr>-<index>`; `_`-prefixed attributes are skipped; class name is the
fallback). Naming SHALL be idempotent and used consistently by the test
runner, the web NodeAPI, and STL child linking.

#### Scenario: Attribute-derived name

- **WHEN** a parent stores a child as `self.wheel` and returns it from
  `render()`
- **THEN** the child's tree name is `wheel`

### Requirement: Color declaration

The system SHALL accept a class-level `color` in `#RRGGBB` form and reject
any other non-None value with `ValueError` during colorization.

#### Scenario: Invalid color

- **WHEN** a node declares `color = 'red'`
- **THEN** assembling it raises `ValueError`
