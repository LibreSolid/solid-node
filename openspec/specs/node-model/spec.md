# Node Model Specification

## Purpose

The core composite node tree that models a mechanical project: base classes,
the render lifecycle, rigid/non-rigid semantics, multi-backend leaf adapters,
and node identity/naming. Encodes ADR-001 (composite pattern), ADR-002
(template-method lifecycle), ADR-003 (rigid vs non-rigid), ADR-004 (multi-CAD
backend adapters), and ADR-026 (parameter-hashed artifact keys vs tree names).

Code: `solid_node/node/` (`base.py`, `internal.py`, `leaf.py`, `fusion.py`,
`assembly.py`, `declarative.py`, `adapters/`).
## Requirements
### Requirement: Composite node tree

The system SHALL model a project as a tree of nodes rooted in
`AbstractBaseNode`, where `InternalNode` subclasses compose children and
`LeafNode` subclasses generate geometry. An `InternalNode.render()` SHALL
return a list or tuple of node instances, or `None` on a class with
declared children under the `declarative-nodes` capability, in which case
the framework substitutes the realized declared children minus the omitted
ones before any consumer sees the result. A `LeafNode.render()` SHALL
return a single geometry object, never a list and never `None`. Validation
runs during framework preparation before geometry production or SCAD
presentation. Public `assemble()` uses that same preparation and retains its
SCAD result; neutral consumers compose the tree without a SCAD union.

#### Scenario: Internal node returns children

- **WHEN** an `InternalNode` subclass's `render()` returns a list of
  `AbstractBaseNode` instances
- **THEN** preparation links and prepares each child; `assemble()` presents
  the assembly's children together, or the canonical fused geometry for a
  fusion, preserving their placements

#### Scenario: Internal node returns nothing

- **WHEN** an `InternalNode` subclass with declared children defines a
  `render()` that positions them and returns nothing
- **THEN** `assemble()` links, prepares and presents the declared children
  exactly as if `render()` had returned them in declaration order

#### Scenario: Structural contract violations are rejected

- **WHEN** an `InternalNode.render()` returns a non-list that is not the
  declarative `None`, returns an element that is not an `AbstractBaseNode`,
  or returns an instance of its own type
- **THEN** validation raises an error during `assemble()`
- **WHEN** a `LeafNode.render()` returns a list, returns `None`, or returns
  an object whose module does not start with the adapter's declared
  `namespace`
- **THEN** validation raises an error during `assemble()`
### Requirement: Template-method render lifecycle

The system SHALL control preparation, validation, native artifact production
and placement through a framework-owned lifecycle. Users SHALL NOT override
that lifecycle. Native geometry consumers SHALL NOT require `as_scad()` or
SCAD generation to prepare the tree or produce its native artifacts.
Public `assemble()` SHALL remain a SCAD compatibility entry point over the
same prepared tree: it requests SCAD presentation, preserves optimized imports
and colours, and applies queued operations in their existing order.
`assemble()` SHALL be idempotent — the result is memoized and `render()` is
called at most once per instance. On an assembly the framework SHALL run
`simulate()` after `render()` ONCE PER ENUMERATION of the tree, under the
current binding: the `render()` that begins an enumeration drives the
simulate phase of every assembly in the subtree it renders, parents
before children, before it returns, and a later `render()` reached by the
walk's own descent within that same enumeration SHALL return the
children at rest without running that assembly's phase again. Every
assembly's motion is therefore in place before the walk reads any of the
tree's geometry. Users override `render()` and `simulate()`, never
`assemble()` or the framework's preparation lifecycle. The same simulation
ordering SHALL hold for native preparation and SCAD compatibility consumers.

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

#### Scenario: Simulate follows render

- **WHEN** an assembly defining both `render()` and `simulate()` is
  assembled
- **THEN** `render()` has run before `simulate()`, and the queued
  operations applied include those `simulate()` produced

#### Scenario: Every phase precedes the first geometry read

- **WHEN** a root with two subtrees is assembled
- **THEN** both subtrees' `simulate()` methods ran before the first
  subtree's geometry was composed, so a coordinate bound while the
  second subtree simulated still moves a body in the first

#### Scenario: Native preparation is independent of SCAD presentation

- **WHEN** an assembly of native artifact-owning leaves is exported or built
  for geometry tests and its SCAD presentation methods are unavailable
- **THEN** structure, validation, motion, geometry and publication succeed
  without invoking those presentation methods
### Requirement: Rigid vs non-rigid distinction

The system SHALL distinguish rigid nodes (`rigid = True`; can produce a cached
STL) from non-rigid nodes. Rigidity SHALL be determined by node type and SHALL
NOT be recomputed from a node's children: `LeafNode` and `FusionNode` are
rigid, `AssemblyNode` is non-rigid, and a flexible leaf (`FlexibleNode`, the
`flexible-parts` capability) is the one non-rigid leaf kind — its geometry is
a function of bound state, so it makes no time-invariance promise. Only rigid
nodes generate cached STL files.

A `FusionNode` SHALL reject a non-rigid child. Fusion combines solids into one
solid; an assembled thing cannot be fused, and neither can a part whose shape
varies with machine state. The rejection SHALL name the fusion and the
offending child and SHALL happen during render validation, before any
geometry is produced.

A **topmost rigid node** is a rigid node whose parent is non-rigid, or the root
node when the root is itself rigid. Because a fusion cannot contain an
assembly or a flexible leaf, every rigid node is either a topmost rigid node
or a descendant of exactly one. A topmost rigid node is the boundary of one
printed solid and the unit selected by whole-solid assertions; this definition
does not itself run an assertion or guarantee that the solid's geometry is
connected. A flexible leaf is never a topmost rigid node.

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

#### Scenario: A flexible leaf is a non-rigid leaf

- **WHEN** `rigid` is read on a flexible leaf
- **THEN** it reports `False` while the node remains a leaf, and a
  `FusionNode` rendering it raises naming both nodes

### Requirement: Animation-time access restrictions

The system SHALL restrict the `time` property to `AssemblyNode`. `LeafNode`
and `FusionNode` SHALL raise on `time` access, preserving the invariant that
rigid geometry is time-invariant (precondition for STL caching, ADR-003/008).

#### Scenario: Fusion cannot animate

- **WHEN** a `FusionNode` subclass reads `self.time` during `render()`
- **THEN** an exception is raised directing the user to `AssemblyNode`

### Requirement: Multi-backend leaf adapters

The system SHALL provide leaf adapters for multiple CAD backends —
`Solid2Node` (solid2/SolidPython2), `CadQueryNode`, `Build123dNode`,
`OpenScadNode` (with `scad_source` and optional `module_name`), and `JScadNode`
(with `jscad_source`) — one sheet leaf kind, `Build123dSheetNode`, whose
part is authored as a profile plus thickness under the `sheet-parts`
capability, one mesh-import leaf, `StlNode` (with `stl_source`), whose
part is a committed STL mesh under the `stl-import` capability, one
solid-import leaf, `StepNode` (with `step_source` and `part`), whose part is
one product of a STEP document under the `step-import`
capability, and one
flexible leaf kind, `MolejoNode`, whose part is a molejo shape spec fed by
ports under the `flexible-parts` capability. Native adapters SHALL provide
geometry through their artifact/evaluation capability without requiring a
custom `as_scad()` implementation. SCAD output SHALL remain available through
the compatibility presentation layer. Existing SCAD-only adapter overrides
SHALL remain usable through the explicit legacy boundary; adapters
declaring a `namespace` (`Solid2Node`, `CadQueryNode`, `Build123dNode`,
`OpenScadNode`, `Build123dSheetNode`, `StepNode`, `MolejoNode`) get
namespace-based render
validation, while `JScadNode` and `StlNode` declare none and skip that check.

`Build123dNode` SHALL accept as a render result a build123d solid — a `Part`,
`Solid` or `Compound` — or a `BuildPart` builder, from which the finished
`.part` is taken. Because build123d's one- and two-dimensional objects share
the `build123d` namespace with its solids, namespace validation alone does not
distinguish them; the adapter SHALL therefore reject a render result that is
not a solid, naming the node and the type it produced. This rule is specific
to this adapter and SHALL NOT constrain the results of the other adapters.

`Build123dSheetNode` is not a `Build123dNode`: its extension point is
`profile()` rather than `render()`, and what its `profile()` must produce —
one planar build123d face — is specified by the `sheet-parts` capability.

`MolejoNode` is a flexible leaf, not a rigid adapter: its `render()` returns
a molejo `Shape`, its per-instant parameter values arrive through declared
ports rather than constructor arguments, and its rigidity, artifact, and
document behavior are specified by the `flexible-parts` capability.

OpenSCAD SHALL be the compilation target for the adapters that emit SCAD for
it to render: `Solid2Node` and `OpenScadNode` have their STL rendered by
OpenSCAD from the SCAD each emits. An adapter that produces its own artifact
through another tool SHALL NOT additionally require OpenSCAD to do so —
`CadQueryNode`, `Build123dNode`, `Build123dSheetNode` and `StepNode` through
their own
kernel, `JScadNode` through the `jscad` binary, `MolejoNode` through molejo's
Python evaluator, and `StlNode` through no
external tool at all: its artifact is materialized from the committed mesh.
`StepNode` needs no external tool either: the kernel that reads its document
is the one that writes its artifacts.
Every adapter SHALL remain representable on the SCAD output path, so the
assembled document retains its existing coverage, including the flexible-part
snapshot limitations. SCAD presentation does not imply OpenSCAD artifact
production and SHALL NOT be a prerequisite for a native adapter's geometry.

An adapter's native artifact producer SHALL produce an artifact only when it
is not up to date. A compatibility `as_scad()` request SHALL reuse that same
producer when needed and SHALL return equivalent SCAD presentation whether the
artifact was already current or just materialized. This covers every artifact
the adapter owns; the sheet adapter's
DXF is produced and guarded under the same rule, and the flexible adapter's
snapshot artifact is guarded per binding as the `flexible-parts` capability
specifies.

An adapter whose backend is a boundary-representation kernel SHALL additionally
expose its geometry exactly, under the `exact-geometry` capability.
`CadQueryNode`, `Build123dNode`, `Build123dSheetNode`, `StepNode` and
`MolejoNode` are
such adapters: each is exact and provides `shape()`.
`Solid2Node`, `OpenScadNode`, `JScadNode` and `StlNode` produce geometry only
as meshes and are not exact. Exposing exact geometry SHALL NOT change an
adapter's SCAD output or its mesh artifact, so a project that never asks an
exact question is unaffected.

#### Scenario: OpenSCAD source adapter

- **WHEN** an `OpenScadNode` subclass declares `scad_source` and is
  instantiated with args/kwargs
- **THEN** the referenced `.scad` module is called with those args in the
  generated SCAD, with `module_name` defaulting to the file's basename

#### Scenario: CadQuery adapter routes through STL

- **WHEN** a `CadQueryNode` is assembled
- **THEN** the CadQuery object is exported to STL and re-imported via
  `import_stl` in the SCAD output

#### Scenario: build123d adapter routes through STL

- **WHEN** a `Build123dNode` is assembled
- **THEN** the build123d object is exported to STL and re-imported via
  `import_stl` in the SCAD output

#### Scenario: Sheet adapter routes through STL

- **WHEN** a `Build123dSheetNode` is assembled
- **THEN** its extruded solid is exported to STL and re-imported via
  `import_stl` in the SCAD output, as for the other kernel-owned adapters

#### Scenario: STEP adapter routes through its own artifact

- **WHEN** a `StepNode` is assembled
- **THEN** the product it selected is exported to STL and re-imported via
  `import_stl` in the SCAD output, as for the other kernel-owned adapters,
  and no external tool is required to produce it

#### Scenario: STL adapter routes through its materialized artifact

- **WHEN** an `StlNode` is assembled
- **THEN** its materialized artifact is imported via `import_stl` in the
  SCAD output, as for the other artifact-owning adapters

#### Scenario: Flexible adapter routes through its snapshot

- **WHEN** a `MolejoNode` is assembled at a bound numeric snapshot
- **THEN** its per-binding snapshot STL is imported via `import_stl` in the
  SCAD output, as the `flexible-parts` capability specifies

#### Scenario: A builder result is accepted

- **WHEN** a `Build123dNode.render()` returns a `BuildPart` builder rather
  than its finished part
- **THEN** the builder's `.part` is taken as the rendered solid and the node
  assembles as if that part had been returned

#### Scenario: A non-solid build123d result is rejected

- **WHEN** a `Build123dNode.render()` returns a build123d sketch or curve,
  which passes namespace validation
- **THEN** validation raises an error naming the node and the type it
  produced, and no geometry is produced

#### Scenario: An adapter does not rewrite a current artifact

- **WHEN** `as_scad()` runs on a `CadQueryNode`, `Build123dNode`,
  `Build123dSheetNode`, `JScadNode`, `StlNode` or `MolejoNode` whose
  artifacts are up to date (for the flexible adapter: current for the
  unchanged binding)
- **THEN** no export or external renderer runs, and the returned SCAD output
  is unchanged

#### Scenario: Only the B-rep backends are exact

- **WHEN** `exact` is read across one instance of each adapter
- **THEN** the `CadQueryNode`, `Build123dNode`, `Build123dSheetNode`,
  `StepNode` and
  `MolejoNode` report true and the `Solid2Node`, `OpenScadNode`,
  `JScadNode` and `StlNode` report false

#### Scenario: Exactness does not disturb the SCAD path

- **WHEN** a `CadQueryNode` is assembled in a project that asks no exact
  question
- **THEN** its SCAD output and STL artifact are what they were before the
  adapter became exact

#### Scenario: A B-rep adapter compiles without OpenSCAD

- **WHEN** a project of `CadQueryNode`, `Build123dNode` or
  `Build123dSheetNode` leaves is built with no `openscad` on the PATH
- **THEN** every leaf's STL is produced through its own kernel and the build
  succeeds

#### Scenario: An adapter with its own external tool does not need OpenSCAD

- **WHEN** a project of `JScadNode` leaves is built with `jscad` available and
  no `openscad` on the PATH
- **THEN** every leaf's STL is produced by `jscad` and the build succeeds

#### Scenario: The mesh-import adapter needs no renderer at all

- **WHEN** a project of `StlNode` leaves with no fusion is built with neither
  `openscad` nor any other CAD tool on the PATH
- **THEN** every leaf's STL artifact is materialized from its committed mesh
  and the build succeeds

#### Scenario: SCAD is still emitted by every adapter

- **WHEN** a `CadQueryNode` project is assembled
- **THEN** its `.scad` artifacts are written as before, so the OpenSCAD GUI
  viewer can open the project when the binary is available

#### Scenario: Native adapter participation needs no SCAD hook

- **WHEN** a native adapter provides its validated local mesh artifact but no
  custom SCAD conversion method
- **THEN** it participates in assembly, export and geometry tests, and explicit
  SCAD presentation can import that artifact through the compatibility layer

#### Scenario: A legacy adapter override is honored

- **WHEN** a project supplies geometry by overriding only the historical
  `as_scad()` hook, including on a built-in adapter subclass
- **THEN** the legacy boundary honors that override rather than silently using
  an inherited native producer that would return different geometry
### Requirement: Parameter-hashed artifact identity

The system SHALL give each node instance a `uniq_id` of the form
`<readable-prefix>-<12-hex-sha256>`, hashed over a canonical serialization of
the class `__qualname__` and the node's parameters. For a class that declares
no parameters and no children under the `declarative-nodes` capability, the
parameters are the positional args in order and the kwargs sorted by key that
reach `AbstractBaseNode.__init__`, exactly as before. For a declarative
class, the parameters are the resolved, coerced values of its declared
parameters sorted by name, derived by the framework and never forwarded by
hand. The readable prefix is sanitized and truncated to 60 characters; the
hash is computed over the full untruncated serialization. Build artifact
basenames are always `<script-name>-<uniq_id>`. The `name=` kwarg SHALL
never influence `uniq_id`.

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

#### Scenario: A declarative class cannot forget a parameter

- **WHEN** a class declares six parameters and is realized twice with one
  value differing
- **THEN** the two `uniq_id`s differ without the class forwarding anything
  to `super().__init__()`

#### Scenario: A migrated class keeps its key

- **WHEN** a class that forwarded all of its kwargs to `super().__init__()`
  with float defaults is rewritten to declare exactly those parameters with
  the same defaults
- **THEN** an instance realized with defaults has the same `uniq_id` as
  before the rewrite

### Requirement: Tree naming from parent attributes

The system SHALL derive a child's tree name when it is linked: an explicit `name=` always wins; otherwise the parent attribute holding the child is used (a plain attribute wins over list membership; list members become `<attr>-<index>`; `_`-prefixed attributes and `children`, the framework's own linked list, are skipped; class name is the fallback). Where the same child is reachable through several direct attributes, the first public direct attribute in insertion order SHALL win; only when no direct attribute holds it SHALL the first public list/tuple membership in attribute and element order name it.

Naming SHALL be idempotent and used consistently by the test runner, simulation/driver enumeration, the web/document serializer, and STL child linking. A framework traversal SHALL inspect a parent's attributes and sequence contents at most once, SHALL link and name all returned siblings from that traversal-entry snapshot before recursing into any child's user code, and SHALL then perform constant-time name lookup per child. It SHALL NOT rescan a wide list once per child.

Direct reassignment, alias changes, replacement, append/removal, and same-length in-place reordering SHALL be visible on the next traversal. A mutation performed by one child during recursive user code SHALL NOT change how a later sibling is named in the parent traversal already in progress; all siblings use the same entry snapshot, and the mutation is visible when another traversal begins. Every link SHALL update the child's current parent even when its explicit name prevents derivation.

#### Scenario: Attribute-derived name

- **WHEN** a parent stores a child as `self.wheel` and returns it from `render()`
- **THEN** the child's tree name is `wheel`

#### Scenario: A direct alias wins over list membership

- **WHEN** one unnamed child appears in a public list and is also held by a public direct attribute declared later
- **THEN** the direct attribute names it, and linking does not depend on the list scan encountering it first

#### Scenario: A wide list is indexed once per traversal

- **WHEN** one traversal links thousands of children held in a public list
- **THEN** the list is scanned once for that parent and each returned child is named by constant-time lookup, producing the same `<attr>-<index>` names as the unindexed contract

#### Scenario: Same-length mutable reorder is visible

- **WHEN** a legacy model reverses or swaps elements of a public child list without changing its length and the tree is traversed again
- **THEN** each unnamed child's derived `<attr>-<index>` name reflects its new position and each parent link is current

#### Scenario: Mid-traversal mutation waits for the next traversal

- **WHEN** the first child mutates or reorders its parent's public child list during recursive render or simulate work
- **THEN** every sibling in the current traversal keeps the name derived from the common traversal-entry snapshot, and a subsequent traversal reflects the mutated order

#### Scenario: The linked list never names

- **WHEN** an assembly's once-only `render()` returns fresh unnamed children and the tree is linked, assembled and serialized more than once
- **THEN** every link derives the same class-name fallback, never `children-<index>` from the list `as_scad` keeps

### Requirement: Color declaration

The system SHALL accept a class-level `color` in `#RRGGBB` form and reject
any other non-None value with `ValueError` during colorization.

#### Scenario: Invalid color

- **WHEN** a node declares `color = 'red'`
- **THEN** assembling it raises `ValueError`

### Requirement: Leaf adapters are distinct types

Each leaf adapter SHALL be a distinct type, and no adapter SHALL be an
instance of another. Adapters that share an implementation base SHALL NOT
thereby become interchangeable to a type test: a project or a framework path
that distinguishes backends by `isinstance` or by walking the method
resolution order SHALL get the same answer whatever bases the adapters
happen to share.

This constrains how shared adapter behaviour may be factored. It does not
require any particular factoring, and it does not make a shared base part of
the public interface.

#### Scenario: Adapters sharing a base stay distinct

- **WHEN** the exact adapters `CadQueryNode` and `Build123dNode` are tested
  against each other with `isinstance`
- **THEN** neither is an instance of the other, and each remains its own type

#### Scenario: The sheet adapter is not its backend's solid adapter

- **WHEN** `Build123dSheetNode` and `Build123dNode` are tested against each
  other with `isinstance`
- **THEN** neither is an instance of the other, though both drive build123d

#### Scenario: The backend lookup is not confused by a shared ancestor

- **WHEN** a node's STL generation resolves the backend name by walking the
  method resolution order for adapter class names
- **THEN** an exact adapter resolves to no mesh-rendering backend, as it did
  before any base was shared, and never launches OpenSCAD

### Requirement: Empty internal composition

The system SHALL allow a non-rigid `AssemblyNode` to render an empty list or
tuple. Its ordinary assembly lifecycle SHALL complete with an empty SCAD
grouping, its linked `children` SHALL be empty, it SHALL generate no STL of its
own, and serialization SHALL include `children: []`.

A rigid `FusionNode` SHALL require at least one selected child because it
represents one solid and has no valid rigid geometry when its membership is
empty. A zero-child fusion SHALL fail during validation with a diagnostic
naming the fusion, before SCAD, BREP, or STL publication.

#### Scenario: Explicit empty assembly

- **WHEN** an `AssemblyNode.render()` explicitly returns `[]`
- **THEN** `assemble()` succeeds, the node has no linked children, and its
  serialized document contains an empty `children` array

#### Scenario: Empty fusion is refused

- **WHEN** a `FusionNode` returns an empty list or declarative selection
  removes every child
- **THEN** validation raises naming the fusion and explaining that a fusion
  requires at least one rigid child
- **AND** no SCAD, BREP, or STL artifact for that fusion is published
