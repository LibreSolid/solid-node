## MODIFIED Requirements

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
