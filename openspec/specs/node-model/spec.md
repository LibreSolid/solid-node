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

#### Scenario: Assemble is memoized

- **WHEN** `assemble()` is called twice on the same instance
- **THEN** `render()` runs only once and the cached result is returned

#### Scenario: Optimized import of cached STL

- **WHEN** a node has `optimize = True`, is rigid, and its STL is up to date
- **THEN** `assemble()` imports the STL (`import_stl`) instead of inlining
  the SCAD model, and queued operations are applied after the import

### Requirement: Rigid vs non-rigid distinction

The system SHALL distinguish rigid nodes (default `rigid = True`; can produce
a cached STL) from non-rigid nodes. `AssemblyNode` is non-rigid; rigidity
SHALL propagate upward as `parent.rigid = parent.rigid AND child.rigid`, so
any non-rigid descendant makes all ancestors non-rigid. Only rigid nodes
generate STL files.

#### Scenario: Non-rigid child makes parent non-rigid

- **WHEN** a `FusionNode` renders a child subtree containing an
  `AssemblyNode`
- **THEN** the fusion's effective `rigid` is False and no STL is generated
  for it

#### Scenario: STL access on non-rigid node

- **WHEN** the `stl` property is read on a non-rigid node
- **THEN** an exception is raised

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

#### Scenario: OpenSCAD source adapter

- **WHEN** an `OpenScadNode` subclass declares `scad_source` and is
  instantiated with args/kwargs
- **THEN** the referenced `.scad` module is called with those args in the
  generated SCAD, with `module_name` defaulting to the file's basename

#### Scenario: CadQuery adapter routes through STL

- **WHEN** a `CadQueryNode` is assembled
- **THEN** the CadQuery object is exported to STL and re-imported via
  `import_stl` in the SCAD output

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
