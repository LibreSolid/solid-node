## MODIFIED Requirements

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

### Requirement: Multi-backend leaf adapters

The system SHALL provide leaf adapters for multiple CAD backends —
`Solid2Node` (solid2/SolidPython2), `CadQueryNode`, `Build123dNode`,
`OpenScadNode` (with `scad_source` and optional `module_name`), and `JScadNode`
(with `jscad_source`) — one sheet leaf kind, `Build123dSheetNode`, whose
part is authored as a profile plus thickness under the `sheet-parts`
capability, one mesh-import leaf, `StlNode` (with `stl_source`), whose
part is a committed STL mesh under the `stl-import` capability, and one
flexible leaf kind, `MolejoNode`, whose part is a molejo shape spec fed by
ports under the `flexible-parts` capability. Each adapter
SHALL implement `as_scad()`; adapters
declaring a `namespace` (`Solid2Node`, `CadQueryNode`, `Build123dNode`,
`OpenScadNode`, `Build123dSheetNode`, `MolejoNode`) get namespace-based render
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
`CadQueryNode`, `Build123dNode` and `Build123dSheetNode` through their own
kernel, `JScadNode` through the `jscad` binary, `MolejoNode` through molejo's
Python evaluator, and `StlNode` through no
external tool at all: its artifact is materialized from the committed mesh.
Every adapter still emits SCAD, so the assembled document remains complete and
the OpenSCAD GUI viewer can still open any project; emitting it does not imply
that OpenSCAD renders it.

An adapter that produces its artifact inside `as_scad()` SHALL produce it only
when that artifact is not up to date, and SHALL return the same SCAD output in
either case. This covers every artifact the adapter owns; the sheet adapter's
DXF is produced and guarded under the same rule, and the flexible adapter's
snapshot artifact is guarded per binding as the `flexible-parts` capability
specifies.

An adapter whose backend is a boundary-representation kernel SHALL additionally
expose its geometry exactly, under the `exact-geometry` capability.
`CadQueryNode`, `Build123dNode`, `Build123dSheetNode` and `MolejoNode` are
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
- **THEN** the `CadQueryNode`, `Build123dNode`, `Build123dSheetNode` and
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
