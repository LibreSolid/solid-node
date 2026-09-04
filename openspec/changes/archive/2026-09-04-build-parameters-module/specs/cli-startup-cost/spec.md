## MODIFIED Requirements

### Requirement: Node backend exports resolve on first use

The system SHALL expose from `solid_node.node` the node classes, the ports
and the declarative structure helpers, each resolved when it is first
accessed rather than when the package is imported. It SHALL NOT expose the
build-parameter kinds, the `Quantity` base or the parameter enumerator;
those belong to the dedicated build-parameter module and SHALL be reachable
only from there. Importing `solid_node.node`, or any module beneath it,
SHALL NOT import a backend the caller has not named.

In particular, importing `solid_node.node` SHALL NOT import `cadquery`. The
exact-geometry stack SHALL be imported when a name that depends on it —
`FusionNode`, `CadQueryNode`, `Build123dNode`, `Build123dSheetNode`, or a
module reached through them — is first accessed.

Attribute access SHALL resolve submodules of `solid_node.node` as well as the
exported classes, so a consumer reading `solid_node.node.<submodule>` after
importing only the package keeps working.

A name that is not exported SHALL raise `AttributeError`, as it does today.

#### Scenario: An OpenSCAD-only project imports no exact stack

- **WHEN** a project whose model uses only `Solid2Node` is built
- **THEN** the build produces the same artifacts as before and `cadquery` is
  absent from the build process's imported modules

#### Scenario: A named backend is resolved

- **WHEN** a module runs `from solid_node.node import CadQueryNode`
- **THEN** it receives the same class it receives today, and `cadquery` is
  imported

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

## ADDED Requirements

### Requirement: The build-parameter module costs nothing to import

The build-parameter module is on the import path of every node module in
every project, so the system SHALL keep it free of framework dependencies:
importing it SHALL import no other `solid_node` module, no CAD backend and
no third-party package. Its names SHALL be bound eagerly rather than through
a deferred accessor, because there is no expensive import to defer.

#### Scenario: Importing parameters pulls in nothing else

- **WHEN** a fresh interpreter imports the build-parameter module alone
- **THEN** no other `solid_node` module and no CAD backend appear among the
  imported modules

#### Scenario: The kinds are bound at import

- **WHEN** the module is imported
- **THEN** each exported name is already an attribute of the module object,
  resolved without a module-level accessor
