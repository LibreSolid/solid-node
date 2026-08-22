## MODIFIED Requirements

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
publish with no OpenSCAD binary on the PATH. Adding an exact backend SHALL NOT
extend this list: `Build123dNode` writes its own STL and BREP through the same
OCCT kernel `CadQueryNode` uses, so a project of `Build123dNode` leaves — or
of `CadQueryNode` and `Build123dNode` leaves mixed — carries no OpenSCAD
dependency.

`JScadNode` is deliberately NOT among the requiring paths. It writes its own
STL through the separate `jscad` binary inside `as_scad()` and stamps the
mtime, so the render protocol finds that artifact current and never launches
OpenSCAD for it. A `JScadNode` therefore carries an external-binary dependency
of its own, on `jscad`, which this capability does not describe. Giving that
binary the same conditional-dependency treatment — enumeration, guarantee,
and actionable failure — is deferred to a later cycle; until then a missing
`jscad` still fails at its subprocess launch.

Declaring the dependency conditional SHALL NOT change what any of those paths
does when the binary is present.

#### Scenario: An all-exact project needs no OpenSCAD

- **WHEN** a project whose every node is exact is built, tested and published
  on a machine with no `openscad` on the PATH
- **THEN** the build, the test run and the publication all succeed

#### Scenario: A build123d project needs no OpenSCAD

- **WHEN** a project of `Build123dNode` leaves, or of `Build123dNode` and
  `CadQueryNode` leaves mixed under a fusion, is built with no `openscad` on
  the PATH
- **THEN** every leaf's STL is produced through the OCCT kernel and the build
  succeeds

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
