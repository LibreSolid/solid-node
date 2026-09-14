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

The system SHALL answer `solid viewer` from the installed viewer package's
entry point alone. The invocation SHALL NOT import `cadquery`, `trimesh`,
`solid2`, or any node module, because none of them contributes to the bundle
path or its API version; and it SHALL NOT import the viewer package's server,
capture or rendering code, because the entry point answers without them.

#### Scenario: Reporting the bundle imports no CAD library

- **WHEN** `solid viewer` runs against an installation with `solid-node-viewer`
- **THEN** it prints the same single JSON object with the bundle path, export
  page, integer API version and package version, exits 0, and `cadquery` and
  `trimesh` are absent from the process's imported modules

#### Scenario: Reporting the bundle runs no viewer code

- **WHEN** `solid viewer` runs against an installation with `solid-node-viewer`
- **THEN** the viewer's server and capture modules are absent from the
  process's imported modules

#### Scenario: The missing-bundle path is unchanged

- **WHEN** `solid viewer` runs in an installation without `solid-node-viewer`
- **THEN** it prints nothing on standard output, names the extra on standard
  error, and exits 1

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

### Requirement: The test framework does not import the exact-geometry stack

The system SHALL import `solid_node.exact`, and through it the
boundary-representation stack, at the exact path's first use rather than at
`solid_node.test` module scope. Importing `solid_node.test` in a fresh
interpreter SHALL NOT import `cadquery`.

This completes the deferral the loader requirement already states from the
other side: loading a node imports neither the test framework nor cadquery,
and now importing the test framework does not import cadquery either. A
project that models entirely in solid2 and asserts entirely over meshes
therefore runs its tests without ever loading the exact stack.

The deferral SHALL NOT make exact geometry optional or change any exact
verdict. A comparison between two exact nodes SHALL import the same stack it
imports today and produce the same result; only the moment of the import
moves. The names `solid_node.test` resolves from `solid_node.exact` today
SHALL remain resolvable as attributes of `solid_node.test`, so a caller that
patches one keeps working whether or not an exact comparison has yet run.

A failure of the deferred import SHALL surface under the existing
deferred-import requirement: the underlying error is raised at first use,
naming the name, never swallowed or substituted.

#### Scenario: Importing the test framework loads no exact stack

- **WHEN** `solid_node.test` is imported in a fresh interpreter
- **THEN** `cadquery` is absent from `sys.modules`

#### Scenario: A faceted project's test run loads no exact stack

- **WHEN** a project whose nodes are all faceted runs its tests to completion
- **THEN** the run reports the same results as today and `cadquery` is absent
  from `sys.modules`

#### Scenario: An exact comparison still loads the stack

- **WHEN** two exact nodes are compared by an intersection assertion
- **THEN** the exact stack is imported and the comparison returns the verdict
  it returns today

#### Scenario: A patched name still resolves

- **WHEN** a caller patches an exact-kernel name on `solid_node.test` before
  any exact comparison has run
- **THEN** the exact path uses the patched object

### Requirement: The motion package is cheap to import

The system SHALL keep `solid_node.motion` free of geometry. Importing
`solid_node.motion` SHALL import no `solid_node` module other than the
top-level `solid_node` package itself — its parent, which the import
machinery necessarily creates and whose `__init__` carries version
metadata only — and no CAD backend.
Importing `solid_node.motion.ports` SHALL import no
CAD backend and no exact-geometry stack: it reaches into
`solid_node.node` only for the render-phase reporter, and the node
classes it needs to validate and read a time base SHALL be imported
inside the methods that need them, never at module scope.

Importing `solid_node.motion.joints` or `solid_node.motion.couplings`
SHALL cost what importing `solid_node.motion.ports` costs and no more:
a joint owns a port as its coordinate and a relation relates two ports,
so the ports module is imported at their module scope, and everything
else they need from the node package — the tree, the operations, the
lifecycle phase, the declaring namespace, the driver declaration —
SHALL be imported inside the methods that need them, never at module
scope. Importing either SHALL import no CAD backend and no
exact-geometry stack.

Neither `solid_node.motion.ports` nor any module beneath
`solid_node.motion` SHALL be imported as a side effect of importing
`solid_node.motion`.

#### Scenario: The package itself costs nothing

- **WHEN** `solid_node.motion` is imported in a fresh interpreter
- **THEN** no `solid_node` module other than the top-level `solid_node`
  package itself, and no CAD backend, appears among the process's
  imported modules

#### Scenario: Ports pull no geometry backend

- **WHEN** `solid_node.motion.ports` is imported in a fresh interpreter
- **THEN** `cadquery`, the boundary-representation kernel and the STEP
  reader are absent from the process's imported modules

#### Scenario: Joints and couplings cost what ports cost

- **WHEN** `solid_node.motion.joints` is imported in a fresh
  interpreter, and `solid_node.motion.couplings` in another, and each
  one's imported `solid_node` modules are compared with those of an
  interpreter that imported only `solid_node.motion.ports`
- **THEN** each set is the same but for the module itself, and
  `cadquery`, the boundary-representation kernel and the STEP reader
  are absent from all three

#### Scenario: Either import order works

- **WHEN** `solid_node.motion.ports` is imported first in one fresh
  interpreter and `solid_node.node.internal` is imported first in
  another
- **THEN** both interpreters complete the import, and a node class
  declaring a port behaves identically in each

### Requirement: The running engine costs nothing to a model that declares no running time

The system SHALL import the running simulation's modules — the compile
step and the engine beneath `solid_node.simulation` — only when a `Sim`
is constructed over a root declaring `Time.running()`. Importing
`solid_node.simulation`, constructing a `Sim` over an untimed or looping
root, building or publishing any model, and importing
`solid_node.motion.ports` or `solid_node.motion.couplings` SHALL NOT import
them. The running time base and the run-binder marker SHALL live in
`solid_node.motion.ports` with no import of their own, so the motion
package's import cost is unchanged, and the couplings module's recognition
of a run binder SHALL add no import to it.

#### Scenario: A looping root's simulation imports no running engine

- **WHEN** a fresh interpreter constructs a `Sim` over a root declaring
  `Time(loop=...)` and runs it
- **THEN** the compile step and the engine modules are absent from the
  process's imported modules

#### Scenario: Ports and couplings cost what they cost

- **WHEN** `solid_node.motion.ports` and `solid_node.motion.couplings` are
  imported in fresh interpreters
- **THEN** their imported `solid_node` modules are the sets the "The motion
  package is cheap to import" requirement already states, with nothing
  from `solid_node.simulation` among them

#### Scenario: A running root's simulation imports the engine on construction

- **WHEN** a `Sim` is constructed over a root declaring `Time.running()`
- **THEN** the compile step and the engine are imported then, and no CAD
  backend and no exact-geometry stack with them
