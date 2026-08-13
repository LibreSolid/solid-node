## MODIFIED Requirements

### Requirement: Multi-backend leaf adapters

The system SHALL provide leaf adapters for multiple CAD backends —
`Solid2Node` (solid2/SolidPython2), `CadQueryNode`, `OpenScadNode` (with
`scad_source` and optional `module_name`), and `JScadNode` (with
`jscad_source`). Each adapter SHALL implement `as_scad()`; adapters declaring
a `namespace` (`Solid2Node`, `CadQueryNode`, `OpenScadNode`) get
namespace-based render validation, while `JScadNode` declares none and skips
that check.

OpenSCAD SHALL be the compilation target for the adapters that emit SCAD for
it to render: `Solid2Node` and `OpenScadNode` have their STL rendered by
OpenSCAD from the SCAD each emits. An adapter that produces its own artifact
through another tool SHALL NOT additionally require OpenSCAD to do so —
`CadQueryNode` through its own kernel, `JScadNode` through the `jscad` binary.
Every adapter still emits SCAD, so the assembled document remains complete and
the OpenSCAD GUI viewer can still open any project; emitting it does not imply
that OpenSCAD renders it.

An adapter that produces its artifact inside `as_scad()` SHALL produce it only
when that artifact is not up to date, and SHALL return the same SCAD output in
either case.

An adapter whose backend is a boundary-representation kernel SHALL additionally
expose its geometry exactly, under the `exact-geometry` capability.
`CadQueryNode` is the only such adapter: it is exact and provides `shape()`.
`Solid2Node`, `OpenScadNode` and `JScadNode` produce geometry only as meshes
and are not exact. Exposing exact geometry SHALL NOT change an adapter's SCAD
output or its mesh artifact, so a project that never asks an exact question is
unaffected.

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

#### Scenario: Only the B-rep backend is exact

- **WHEN** `exact` is read across one instance of each adapter
- **THEN** the `CadQueryNode` reports true and the `Solid2Node`,
  `OpenScadNode` and `JScadNode` report false

#### Scenario: Exactness does not disturb the SCAD path

- **WHEN** a `CadQueryNode` is assembled in a project that asks no exact
  question
- **THEN** its SCAD output and STL artifact are what they were before the
  adapter became exact

#### Scenario: A B-rep adapter compiles without OpenSCAD

- **WHEN** a project of `CadQueryNode` leaves is built with no `openscad` on
  the PATH
- **THEN** every leaf's STL is produced through its own kernel and the build
  succeeds

#### Scenario: An adapter with its own external tool does not need OpenSCAD

- **WHEN** a project of `JScadNode` leaves is built with `jscad` available and
  no `openscad` on the PATH
- **THEN** every leaf's STL is produced by `jscad` and the build succeeds

#### Scenario: SCAD is still emitted by every adapter

- **WHEN** a `CadQueryNode` project is assembled
- **THEN** its `.scad` artifacts are written as before, so the OpenSCAD GUI
  viewer can open the project when the binary is available
