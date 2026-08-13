## ADDED Requirements

### Requirement: OpenSCAD is required only by the paths that invoke it

The system SHALL treat the OpenSCAD binary as a conditional dependency of the
paths that use it, not as a blanket installation requirement.

The paths that require it are exactly:

- rendering the STL of a `Solid2Node` or `OpenScadNode` leaf, whose
  `as_scad()` emits SCAD for OpenSCAD to render;
- rendering the STL of a `FusionNode` that is not exact;
- evaluating a `Solid2Node` symbolic value through `as_number()`;
- opening the OpenSCAD GUI viewer with `solid develop --openscad`;
- rendering an image with `solid snapshot --renderer openscad`.

No other operation SHALL require it. In particular, a project whose model is
entirely exact under the `exact-geometry` capability SHALL build, test, and
publish with no OpenSCAD binary on the PATH.

`JScadNode` is deliberately NOT among the requiring paths. It writes its own
STL through the separate `jscad` binary inside `as_scad()` and stamps the
mtime, so the render protocol finds that artifact current and never launches
OpenSCAD for it. A `JScadNode` therefore carries an external-binary
dependency of its own, on `jscad`, which this capability does not describe.
Giving that binary the same conditional-dependency treatment — enumeration,
guarantee, and actionable failure — is deferred to a later cycle; until then
a missing `jscad` still fails at its subprocess launch.

Declaring the dependency conditional SHALL NOT change what any of those paths
does when the binary is present.

#### Scenario: An all-exact project needs no OpenSCAD

- **WHEN** a project whose every node is exact is built, tested and published
  on a machine with no `openscad` on the PATH
- **THEN** the build, the test run and the publication all succeed

#### Scenario: A mesh-backend project still requires it

- **WHEN** a project with `Solid2Node` leaves is built
- **THEN** OpenSCAD renders each of those leaves as before

#### Scenario: A JSCAD leaf does not require OpenSCAD

- **WHEN** a project of `JScadNode` leaves is built with `jscad` available
- **THEN** each leaf's STL is produced by `jscad`, the render protocol finds
  it current, and OpenSCAD is never launched for it

#### Scenario: The deferred binary still fails at its launch

- **WHEN** a `JScadNode` must be rendered and no `jscad` is on the PATH
- **THEN** the failure is the subprocess launch error, because `jscad` is not
  yet covered by this capability

#### Scenario: Presence changes nothing

- **WHEN** any of the listed paths runs on a machine where OpenSCAD is
  installed
- **THEN** its behaviour and output are what they were before the dependency
  was declared conditional

### Requirement: A missing OpenSCAD binary is reported actionably

When a path listed above requires the OpenSCAD binary and it cannot be found,
the system SHALL fail with an error that names what needed it, why that path
needs it, and what the user can do — installing OpenSCAD, or, for the snapshot
renderer, selecting the web renderer instead. The error SHALL NOT be a bare
subprocess launch failure.

The system SHALL NOT substitute a different renderer, a different geometry
path, or a cached artifact for the operation that could not run. This is the
same no-silent-substitution rule the web-snapshot capability already applies
in the opposite direction.

The check SHALL be made where the operation is attempted, so a project that
never reaches a requiring path is never asked for the binary.

#### Scenario: A mesh leaf cannot be rendered

- **WHEN** a `Solid2Node` leaf must be rendered and no `openscad` is on the
  PATH
- **THEN** the build fails with an error naming that node, stating that its
  backend renders through OpenSCAD, and pointing at installation — not with a
  bare `FileNotFoundError`

#### Scenario: The GUI viewer cannot open

- **WHEN** `solid develop --openscad` runs and no `openscad` is on the PATH
- **THEN** it reports that the OpenSCAD viewer was requested and the binary is
  missing

#### Scenario: The OpenSCAD renderer cannot run

- **WHEN** `solid snapshot --renderer openscad` runs and no `openscad` is on
  the PATH
- **THEN** it fails naming the missing binary and `--renderer web` as the
  alternative, and renders no image through the web renderer on its own

#### Scenario: A symbolic value cannot be evaluated

- **WHEN** a `Solid2Node` symbolic value must be resolved through `as_number()`
  and no `openscad` is on the PATH
- **THEN** it fails naming the node and the reason the evaluation needs
  OpenSCAD

#### Scenario: An unreached path is never checked

- **WHEN** an all-exact project is built on a machine with no `openscad`
- **THEN** no availability check fails, because no requiring path is reached
