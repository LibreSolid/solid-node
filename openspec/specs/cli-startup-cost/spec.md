# cli-startup-cost Specification

## Purpose
TBD - created by archiving change fast-cli-startup. Update Purpose after archive.
## Requirements
### Requirement: A command loads only its own implementation

The system SHALL import the implementation module of exactly the command being
run. Importing `solid_node.cli` SHALL NOT import any command implementation
module, and dispatching one command SHALL NOT import another command's module.

The command names, the command-first grammar, and the pre-0.4 migration guard
SHALL be derived from the command registry without importing any command
implementation module, because all three need only names.

An unknown command name SHALL be reported with an error that names the valid
commands and exits nonzero, as it does today.

#### Scenario: Importing the CLI loads no command

- **WHEN** `solid_node.cli` is imported in a fresh interpreter
- **THEN** no `solid_node.manager.*` command implementation module is present
  in `sys.modules`

#### Scenario: One command does not load another

- **WHEN** `solid viewer` runs to completion
- **THEN** the process has imported the `viewer` command's module and has
  imported no other command's module

#### Scenario: The legacy grammar is still recognised

- **WHEN** a user runs `solid mynode.py develop`
- **THEN** the CLI exits with code 2 and prints the migration hint, without
  importing any command implementation module

### Requirement: Top-level help still describes every command

The system SHALL keep `solid -h` and the no-subcommand invocation listing every
command with the help derived from that command's docstring, unchanged from
today. This is the one invocation whose output depends on every command, and it
alone MAY import every command module.

#### Scenario: Help lists the full command set

- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `build`, `develop`, `test`, `snapshot`,
  `new`, `export`, and `viewer`, each with its docstring help

#### Scenario: Per-command help is complete

- **WHEN** a user runs `solid <command> -h` for any command
- **THEN** every option that command accepts is listed, as it is today

### Requirement: The viewer command loads no geometry stack

The system SHALL answer `solid viewer` from the installed viewer bundle alone.
The invocation SHALL NOT import `cadquery`, `trimesh`, `solid2`, or any node
module, because none of them contributes to the bundle path or its API version.

#### Scenario: Reporting the bundle imports no CAD library

- **WHEN** `solid viewer` runs against an installation with a built bundle
- **THEN** it prints the same single JSON object with the bundle path and
  integer API version, exits 0, and `cadquery` and `trimesh` are absent from
  the process's imported modules

#### Scenario: The missing-bundle path is unchanged

- **WHEN** `solid viewer` runs in an installation with no built bundle
- **THEN** it prints nothing on standard output, names the remedy on standard
  error, and exits 1

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

### Requirement: The test framework is imported by the paths that run tests

The system SHALL import `solid_node.test` where tests are discovered or run,
not at the module scope of the loader that every node-scoped command goes
through. Importing `solid_node.core.loader` SHALL NOT import
`solid_node.test`, and therefore SHALL NOT import the exact-geometry stack.

The system SHALL likewise resolve `solid_node.simulation`'s exports on first
access rather than at package import, so reaching
`solid_node.simulation.enumeration` — which the serializer does on every
publication — does not import the scenario module and through it the test
framework.

Neither deferral makes the test framework optional. Discovering or running a
test SHALL import it exactly as it does today, and every name either package
exports today SHALL remain importable and identical.

#### Scenario: Loading a node does not import the test framework

- **WHEN** `solid_node.core.loader` is imported in a fresh interpreter
- **THEN** `solid_node.test` and `cadquery` are absent from `sys.modules`

#### Scenario: Discovering companion tests still works

- **WHEN** a node's companion tests are discovered
- **THEN** the same `TestCase` subclasses are returned as today, and the test
  framework is imported

#### Scenario: Publishing does not import the scenario module

- **WHEN** a build serializes its viewer document
- **THEN** the driver enumeration it needs is available and
  `solid_node.simulation.scenario` is not imported

#### Scenario: The simulation package still exports its names

- **WHEN** a consumer imports a name from `solid_node.simulation`
- **THEN** it receives the same object it receives today

### Requirement: The mesh library is imported by the path that reads meshes

The system SHALL import `trimesh` in the cached-base-mesh path that loads an
STL, not at `solid_node.node.base` module scope. Importing
`solid_node.node.base` SHALL NOT import `trimesh`.

The system SHALL also keep `trimesh` out of `solid_node.node.base` by way of
`solid_node.node.operations`, which imports it at its own module scope.

This SHALL NOT change what any mesh-reading path does: the same cache keyed on
`(stl_file, mtime)`, the same stale-entry eviction, and the same values
returned. Publishing a build still reads every piece's mesh through that path,
so the process that publishes still imports `trimesh`; the deferral serves every
path that never reaches it, including the CLI parent of a build whose model
needs no mesh read.

The name `trimesh` SHALL remain resolvable as an attribute of
`solid_node.node.base`, so a caller that patches it keeps working whether or
not a mesh has yet been read.

#### Scenario: Importing the node base loads no mesh library

- **WHEN** `solid_node.node.base` is imported in a fresh interpreter
- **THEN** `trimesh` is absent from `sys.modules`

#### Scenario: The mesh cache behaves identically

- **WHEN** the same STL is read twice through the cached base mesh and then
  rebuilt and read again
- **THEN** the first two reads share one cached mesh, the entry under the old
  mtime is evicted, and the values returned are those returned today

### Requirement: Deferred imports do not hide a broken installation

When a deferred import fails, the system SHALL raise the underlying import
error at the point the deferred name is first used, naming that name. It SHALL
NOT be swallowed, retried against a substitute, or reported as a missing
attribute.

#### Scenario: A broken backend reports its own failure

- **WHEN** a name whose backend cannot be imported is accessed from
  `solid_node.node`
- **THEN** the underlying import error is raised, naming the requested name,
  rather than an `AttributeError`

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

