## MODIFIED Requirements

### Requirement: Node backend exports resolve on first use

The system SHALL expose from `solid_node.node` the node classes and the
declarative structure helpers, each resolved when it is first
accessed rather than when the package is imported. It SHALL NOT expose the
build-parameter kinds, the `Quantity` base or the parameter enumerator;
those belong to the dedicated build-parameter module and SHALL be reachable
only from there. It SHALL NOT expose the port kinds, the port declaration
enumerator or the time-base declaration; those belong to the dedicated
motion module and SHALL be reachable only from there. Importing
`solid_node.node`, or any module beneath it,
SHALL NOT import a backend the caller has not named.

In particular, importing `solid_node.node` SHALL NOT import `cadquery`, and
SHALL NOT import the boundary-representation kernel's STEP reader. The
exact-geometry stack SHALL be imported when a name that depends on it —
`FusionNode`, `CadQueryNode`, `Build123dNode`, `Build123dSheetNode`,
`StepNode`, or a
module reached through them — is first accessed, and the STEP reader when
`StepNode` is.

Attribute access SHALL resolve submodules of `solid_node.node` as well as the
exported classes, so a consumer reading `solid_node.node.<submodule>` after
importing only the package keeps working.

A name that is not exported SHALL raise `AttributeError`, as it does today.
A name that has moved to another module SHALL raise `ImportError` whose
message names the module that now answers for it: an `ImportError` rather
than an `AttributeError` because `from solid_node.node import <name>`
discards an `AttributeError`'s message and substitutes its own generic
text, so only an `ImportError` carries the redirect to the failing import
line.

#### Scenario: An OpenSCAD-only project imports no exact stack

- **WHEN** a project whose model uses only `Solid2Node` is built
- **THEN** the build produces the same artifacts as before and `cadquery` is
  absent from the build process's imported modules

#### Scenario: A named backend is resolved

- **WHEN** a module runs `from solid_node.node import CadQueryNode`
- **THEN** it receives the same class it receives today, and `cadquery` is
  imported

#### Scenario: The STEP reader is not imported by the node package

- **WHEN** `solid_node.node` is imported in a fresh interpreter
- **THEN** the kernel's STEP reader is absent from the process's imported
  modules, and it is imported when `StepNode` is first accessed

#### Scenario: A submodule is reached through the package

- **WHEN** a consumer imports `solid_node.node` and then reads
  `solid_node.node.assembly`
- **THEN** the submodule is returned

#### Scenario: An unknown name still fails

- **WHEN** a consumer reads a name `solid_node.node` does not export
- **THEN** `AttributeError` is raised

#### Scenario: A parameter kind is not a node export

- **WHEN** a consumer reads a build-parameter name off `solid_node.node`
- **THEN** `AttributeError` is raised naming it, so
  `from solid_node.node import Length` fails at the import, and the
  package's export list carries no build-parameter name

#### Scenario: A port kind is not a node export

- **WHEN** a consumer reads `RotationalPort`, `SignalPort`,
  `TranslationalPort`, `Port`, `declared_ports` or `Time` off
  `solid_node.node`
- **THEN** `ImportError` is raised naming `solid_node.motion.ports`, so
  `from solid_node.node import RotationalPort` fails at the import with
  that message, and the package's export list carries no port or time-base
  name

## ADDED Requirements

### Requirement: The motion package is cheap to import

The system SHALL keep `solid_node.motion` free of geometry. Importing
`solid_node.motion`, `solid_node.motion.joints` or
`solid_node.motion.couplings` SHALL import no `solid_node` module other
than the top-level `solid_node` package itself — their parent, which the
import machinery necessarily creates and whose `__init__` carries version
metadata only — and no CAD backend. Importing `solid_node.motion.ports` SHALL import no
CAD backend and no exact-geometry stack: it reaches into
`solid_node.node` only for the render-phase reporter, and the node
classes it needs to validate and read a time base SHALL be imported
inside the methods that need them, never at module scope.

Neither `solid_node.motion.ports` nor any module beneath
`solid_node.motion` SHALL be imported as a side effect of importing
`solid_node.motion`.

#### Scenario: The empty submodules cost nothing

- **WHEN** `solid_node.motion`, `solid_node.motion.joints` and
  `solid_node.motion.couplings` are imported in a fresh interpreter
- **THEN** no `solid_node` module other than the top-level `solid_node`
  package itself, and no CAD backend, appears among the process's
  imported modules

#### Scenario: Ports pull no geometry backend

- **WHEN** `solid_node.motion.ports` is imported in a fresh interpreter
- **THEN** `cadquery`, the boundary-representation kernel and the STEP
  reader are absent from the process's imported modules

#### Scenario: Either import order works

- **WHEN** `solid_node.motion.ports` is imported first in one fresh
  interpreter and `solid_node.node.internal` is imported first in
  another
- **THEN** both interpreters complete the import, and a node class
  declaring a port behaves identically in each
