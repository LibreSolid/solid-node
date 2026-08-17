# Build Pipeline Specification

## Purpose

How source files become STL artifacts: path-based node loading, the build
artifact layout, mtime-equality caching, concurrent render locking, and the
watch-rebuild loop. Encodes ADR-005 (path-based dynamic module loading),
ADR-006 (mtime-based STL caching), ADR-007 (watchdog filesystem monitoring),
ADR-018 (file-based error propagation, superseding the broker of
ADR-016/017), and the loader rules of ADR-026.

Code: `solid_node/core/loader.py`, `solid_node/core/builder.py`,
`solid_node/node/base.py` (artifact/caching layer).
## Requirements
### Requirement: Project root discovery and model reference

The system SHALL determine a project's root by walking upward from a discovery
origin to the nearest ancestor `pyproject.toml` containing a
`[tool.solid-node]` table, and SHALL treat the directory holding that file as
the project root. That table's `model` key SHALL hold an entry-point object
reference naming the project's model node, in the form
`package.module:ClassName`.

The discovery origin SHALL be the referenced file when the reference names a
path, because a path identifies a project as surely as it identifies a file.
It SHALL be the working directory when there is no reference, or when the
reference is a qualifier, which carries no location.

The discovered root — never the working directory — SHALL anchor the import
path used to load project modules, the dotted module name computed for a file
loaded by path, the boundary of a node's tracked source closure, and the
project's build directory. A command SHALL therefore resolve the same node, the
same source closure, and the same artifact paths from any directory.

When no ancestor `pyproject.toml` carries the table, a command that needs a
node SHALL fail with an actionable error naming the origin it searched from.

#### Scenario: Command run from a subdirectory

- **WHEN** a user runs a node-scoped command from a subdirectory of a project
  whose `pyproject.toml` declares `[tool.solid-node] model`
- **THEN** the project root is discovered from that manifest
- **AND** the node's tracked source closure is the same set it would be from
  the project root

#### Scenario: A path outside the working directory's project

- **WHEN** a user names a path in a different project from the one containing
  the working directory
- **THEN** the root is discovered from that path, and the node is resolved
  against its own project

#### Scenario: No manifest above the origin

- **WHEN** a node-scoped command runs with no argument and no ancestor
  `pyproject.toml` carries a `[tool.solid-node]` table
- **THEN** the command exits nonzero with an error naming the search origin

### Requirement: Path-based node loading

The system SHALL load a node from a reference in one of three interchangeable
spellings: a qualifier `package.module:ClassName`, a filesystem path to a `.py`
file, and a hybrid `path/to/file.py:ClassName`. A reference SHALL be parsed by
splitting on its last `:`, treating the left side as a path when it ends in
`.py` or names an existing file and as a dotted module otherwise.

A path with no class part SHALL resolve to the single `AbstractBaseNode`
subclass defined in that file, and SHALL raise `AmbiguousNodeError` naming the
candidates when the file defines several. Implicit discovery SHALL consider only
classes defined in the loaded file, never imported ones. A reference naming a
class SHALL reject a target that is not an `AbstractBaseNode` subclass, and
SHALL reject one defined outside the discovered project root.

All spellings of one node SHALL resolve to the same class object through a
single imported module, so that a file is never imported under two module names.

The loaded file and the selected class's project-local implementation and
import closure SHALL all contribute to the node's tracked source set.

Companion tests are discovered as `test_<file>.py` for module nodes and
`test.py` for package nodes. The system SHALL NOT consult a module-level `NODE`
marker; a file never declares which of its classes is a node.

#### Scenario: Ambiguous file

- **WHEN** a reference is a bare path to a file defining two node classes
- **THEN** loading raises `AmbiguousNodeError` naming both candidates and
  directing the caller to name a class

#### Scenario: Imported classes are ignored implicitly

- **WHEN** a bare path names a file that imports node classes and defines
  exactly one of its own
- **THEN** the loader picks the locally defined class

#### Scenario: Qualifier and hybrid name the same node

- **WHEN** the same node is loaded as `pkg.module:Sail` and as
  `pkg/module.py:Sail`
- **THEN** both resolve to the same class object from one entry in the module
  table

#### Scenario: Reference target is outside the project

- **WHEN** a reference names a class defined outside the discovered project root
- **THEN** loading raises an actionable error and no node is instantiated

#### Scenario: A marker no longer selects a class

- **WHEN** a file defines two node classes and sets a module-level `NODE`
  variable naming one of them
- **THEN** a bare path to that file still raises `AmbiguousNodeError`

### Requirement: Build artifact layout

The system SHALL write build artifacts under `$SOLID_BUILD_DIR` (default
`_build`), mirroring the source file's directory, with basename
`<script-name>-<uniq_id>`. A relative `$SOLID_BUILD_DIR`, and the default,
SHALL resolve against the discovered project root and never against the working
directory, so that a project has one build directory and — because the build
lock is derived from it — one build lock, whichever directory a command was run
from. An absolute `$SOLID_BUILD_DIR` SHALL be used as given.
Artifacts per node: `.scad` (base geometry,
no transforms), `.stl` (rendered), and `.stl.lock` during rendering. A node
that is exact under the `exact-geometry` capability SHALL additionally write
`.brep`, holding that node's unplaced exact geometry under the same basename.
World-space spatial math does not use on-disk artifacts — the `mesh`
property loads the plain `.stl` and applies operations in memory (the
`.mesh.scad`/`.mesh.stl` path attributes exist but are vestigial; nothing
writes or reads them). The build path SHALL be an ordinary directory that every
builder writes into directly; the system SHALL NOT publish through a symlink, a
versioned sibling directory, or a private candidate copy. A build path left as
a symlink by an earlier layout SHALL be converted to an ordinary directory
holding the artifacts it referenced.

The `.brep` artifact SHALL be private to the build. No viewer snapshot, export
manifest, or other published document SHALL reference it, and its presence
SHALL NOT alter any document's schema.

#### Scenario: Custom build dir

- **WHEN** `SOLID_BUILD_DIR` is set in the environment
- **THEN** all artifacts, and `errors.json`, are written under that
  directory instead of `_build`

#### Scenario: One build directory whatever the working directory

- **WHEN** a project is built from its root and then from a subdirectory
- **THEN** both builds publish into the same build directory and contend for
  the same build lock

#### Scenario: Consumer reads through the build path

- **WHEN** a consumer opens the published viewer snapshot at the build path
- **THEN** it reads the snapshot without resolving a symlink or naming any
  other directory

#### Scenario: Project published under the previous layout

- **WHEN** a project whose build path is a symlink to a versioned directory is
  built
- **THEN** the build path becomes an ordinary directory holding those
  artifacts, and the versioned siblings are removed

#### Scenario: An exact node writes exact geometry beside its mesh

- **WHEN** an exact rigid node is built
- **THEN** a `.brep` artifact sits beside its `.stl` under the same basename

#### Scenario: A faceted node writes no exact artifact

- **WHEN** a rigid node that is not exact is built
- **THEN** no `.brep` artifact is written for it

#### Scenario: Published documents do not name exact geometry

- **WHEN** a build publishes its viewer snapshot for a project of exact nodes
- **THEN** the document references only `.stl` models and names no `.brep`

### Requirement: Mtime-equality caching

The system SHALL treat an artifact as up to date iff it exists AND its mtime
equals the node's `mtime`, where `node.mtime` is the maximum source-file
mtime across all files tracked for the node (`node.files`, aggregated
recursively from children). After generating an artifact the system SHALL
back-date its mtime to the source mtime via `os.utime` so the equality holds.
A change to any contributing source file invalidates all ancestor artifacts.

For an exact node the `.brep` artifact SHALL participate in this rule exactly
as the `.stl` does: the node's artifacts are current only when both are, so a
node whose mesh is current but whose exact geometry is absent or stale SHALL
be rendered rather than skipped. A build directory produced before the node
became exact therefore reports not-current once and is rebuilt.

A node's tracked files SHALL include its own source together with the
project-local modules that source imports, transitively. Modules outside the
project tree SHALL NOT be tracked. Where the contributing set cannot be
determined exactly, the system SHALL track more files rather than fewer, so
that an uncertain dependency causes an unnecessary rebuild rather than a stale
artifact.

#### Scenario: Source edit invalidates ancestors

- **WHEN** a leaf's source file is modified
- **THEN** the leaf's STL and every ancestor STL report not-up-to-date and
  are regenerated on the next build

#### Scenario: Imported project module edit invalidates dependants

- **WHEN** a node's source imports a project module that defines no node, and
  that module is modified
- **THEN** the node's artifact reports not-up-to-date and is regenerated with
  the new values on the next build

#### Scenario: A library change does not invalidate

- **WHEN** a node imports a module from outside the project tree
- **THEN** that module is not part of the node's tracked files

#### Scenario: Unchanged sources skip rendering

- **WHEN** `generate_stl` runs and the STL mtime equals `node.mtime`
- **THEN** no OpenSCAD process is launched

#### Scenario: Missing exact geometry is not current

- **WHEN** an exact node's `.stl` and `.scad` are current but its `.brep` is
  absent
- **THEN** the node reports not-up-to-date and is rendered, producing both

### Requirement: Concurrent render locking

The system SHALL guard STL generation with a `.stl.lock` file containing the
rendering process PID, and SHALL treat a lock as stale when that PID is no
longer alive (`os.kill(pid, 0)` fails). A locked node skips generation.

Because the published manifest references every rigid node's STL by path, a
build that finishes with any rigid artifact still absent SHALL be reported as
an incomplete render rather than publishing, so a node whose lock another
builder holds makes the supervisor retry instead of advertising a file that is
not there. This requirement rests on manifest integrity alone and does not
depend on any geometric check.

#### Scenario: A locked node leaves the build incomplete

- **WHEN** a builder finishes triggering renders but a rigid node's STL is
  still absent because another process holds its lock
- **THEN** the build reports an incomplete render and nothing is published

#### Scenario: Stale lock

- **WHEN** a lock file references a dead PID
- **THEN** the node is not considered locked and rendering proceeds

### Requirement: Project build mutual exclusion

The system SHALL serialise builds of the same project across processes with an
advisory exclusive lock (`fcntl.flock`) on a lock file held beside the project's
published build directory. Every framework entry point that renders artifacts
for a project — the development watch loop, the one-shot build, the test
runner's build phase, and export — SHALL acquire that lock before rendering or
publishing and SHALL release it as soon as that work is finished. Acquisition
SHALL block until the lock is available rather than fail or skip, and a wait
that does not resolve immediately SHALL be logged. The lock SHALL NOT be held
while a builder waits for a source change, and the lock file SHALL be excluded
from version control by the same rule that excludes published artifacts.

A holder that dies SHALL release the lock without any recovery step, because
the kernel releases it when the holding process ends.

#### Scenario: A second builder waits for the first

- **WHEN** a build is rendering a project and another process starts a build of
  the same project
- **THEN** the second process does not render or publish until the first has
  finished, and both report their own build outcome

#### Scenario: Watching does not hold the lock

- **WHEN** a development watch loop has published a build and is waiting for the
  next source change
- **THEN** another process can acquire the project build lock immediately

#### Scenario: A killed builder leaves nothing to reap

- **WHEN** a process holding the build lock is killed
- **THEN** the next builder acquires the lock with no stale-lock detection and
  no manual cleanup

#### Scenario: Independent projects do not serialise

- **WHEN** two projects with different build directories are built at the same
  time
- **THEN** neither build waits for the other

### Requirement: Superseded and redundant builds do not publish

Having acquired the build lock, a builder SHALL re-evaluate whether its work is
still needed before rendering or publishing, using the mtime-equality rule
already governing artifact currency.

- When the node's tracked source files on disk are newer than the source state
  the builder loaded, the builder SHALL publish nothing and SHALL report the
  same source-changed outcome an ordinary edit produces, so its lifecycle loop
  rebuilds from current source.
- When the published artifact set is already current for the loaded node, the
  builder SHALL publish nothing. A one-shot build SHALL report the model
  current; a watching builder SHALL go on waiting for the next source change
  rather than ending.

Currency SHALL be judged where a consumer reads artifacts — the build directory
itself, which is now the only place a builder writes. This decision SHALL be
derived from source and artifact mtimes; the system SHALL NOT record build
state, generation counters, or source identity inside published artifacts for
this purpose.

#### Scenario: The newest source wins

- **WHEN** a build against older source finishes after a build against newer
  source has published the same project
- **THEN** the older build publishes nothing and the published model matches the
  newer source

#### Scenario: A redundant build publishes nothing

- **WHEN** a builder acquires the lock and the published artifact set is already
  current for its sources
- **THEN** no artifact is rendered, no publication occurs, and the outcome
  reports the model current

#### Scenario: A watching builder finds nothing to do

- **WHEN** a builder that watches for source changes acquires the lock and the
  published set is already current
- **THEN** it publishes nothing and keeps watching, and the development loop
  does not respawn it

#### Scenario: An ordinary change still builds

- **WHEN** a builder acquires the lock, its sources are the newest on disk, and
  the published set is not current for them
- **THEN** it renders and publishes exactly as it does without contention

### Requirement: Publication runs no project geometry assertion

The build and publication pipeline SHALL NOT count connected components, read
an STL to evaluate a geometric contract, or invoke
`assertNoDisconnectedSolids`. A disconnected solid SHALL NOT by itself be a
build or publication failure.

The pipeline remains responsible for build mechanics and model validity —
render failures, missing artifacts, and structurally invalid trees such as a
fusion containing an assembly. Those are properties of a well-formed model,
not geometric contracts a project selected, and they SHALL continue to fail
the build.

#### Scenario: A fragmented solid publishes

- **WHEN** a build completes rendering and a topmost rigid node's STL has more
  than one connected solid, with no other failure
- **THEN** the viewer snapshot is published normally and no connectivity error
  is written

#### Scenario: The already-current path checks nothing either

- **WHEN** a builder finds the artifact set already current for a tree
  containing a fragmented solid
- **THEN** it publishes on its ordinary terms and reports no connectivity
  failure

#### Scenario: A declared test does not change build behavior

- **WHEN** a project declares a test method calling
  `assertNoDisconnectedSolids`
- **THEN** `solid build`, `solid develop` and `solid snapshot` neither discover
  nor execute it

### Requirement: Asynchronous STL render protocol

The system SHALL launch OpenSCAD renders as subprocesses
(`openscad <scad> -o <stl> --export-format binstl`) signalled by raising
`StlRenderStart`, which carries the process, target file, mtime, and lock
file. `build_stls()` SHALL loop, waiting on each started render
(`job.wait()`), until no renders remain; finishing a render stamps the STL
mtime and removes the lock. Non-rigid nodes SHALL be skipped.

This protocol is one of the paths that require the OpenSCAD binary under the
`openscad-dependency` capability. Before launching the subprocess for a node
the system SHALL confirm the binary is available and, when it is not, SHALL
fail naming that node and why its backend needs OpenSCAD, rather than letting
the subprocess launch fail. A build that reaches no such node SHALL make no
availability check.

A `FusionNode` whose subtree is exact SHALL NOT use this protocol. It composes
its own geometry under the `exact-geometry` capability and SHALL produce its
`.stl` by tessellating that composition in process, stamping the mtime as any
other artifact producer does, without launching a subprocess and without
raising `StlRenderStart`. A fusion with any non-exact descendant keeps the
subprocess protocol unchanged.

Tessellation of an exact composition SHALL use the same deflection the
`CadQueryNode` adapter already uses for leaf STL export, so a fused solid's
mesh is of the same quality as the leaves around it.

#### Scenario: Full build

- **WHEN** `build_stls()` runs on a tree with several stale rigid nodes
- **THEN** each stale STL is rendered exactly once and the call returns with
  all locks removed and mtimes stamped

#### Scenario: An exact fusion renders in process

- **WHEN** a `FusionNode` whose subtree is exact is built
- **THEN** its `.stl` is produced by tessellating its own composition, no
  OpenSCAD subprocess is launched for it, and `build_stls()` returns without
  waiting on a render job for that node

#### Scenario: A faceted fusion keeps the subprocess protocol

- **WHEN** a `FusionNode` holding a non-exact descendant is built
- **THEN** its STL is rendered by an OpenSCAD subprocess signalled by
  `StlRenderStart`, as before

#### Scenario: The renderer is missing for a node that needs it

- **WHEN** a stale mesh-backend node must be rendered and no `openscad` is on
  the PATH
- **THEN** the build fails naming that node and the reason its backend needs
  OpenSCAD, and no subprocess launch error surfaces in its place

#### Scenario: An all-exact build makes no availability check

- **WHEN** `build_stls()` completes for a tree whose every rigid node is exact
- **THEN** no OpenSCAD availability check is performed and the absence of the
  binary is never reported

### Requirement: Watch-rebuild loop

The system SHALL rebuild on change via a single-shot builder: it loads and
assembles the node, watches each file in `node.files` individually
(non-recursive, via watchdog), renders pending STLs, and exits when a watched
`.py` file changes — the develop loop respawns it. Directory events and
`__pycache__` changes are ignored.

#### Scenario: Edit triggers rebuild cycle

- **WHEN** a watched source file is saved during `solid develop`
- **THEN** the builder logs the change, exits, and is respawned to rebuild
  with the new source

### Requirement: File-based build error propagation

The system SHALL report build errors by writing `{"error": ..., "tstamp":
...}` to `errors.json` in the build dir (no broker or socket IPC — ADR-018).
On a successful load the errors file is cleared. An initial-launch failure
SHALL exit non-zero (develop terminates); a failure during reload SHALL NOT
kill the loop — the builder falls back to watching the project directory
recursively, writes the traceback to `errors.json`, and exits cleanly on the
next save so development continues.

#### Scenario: Syntax error during development

- **WHEN** a reload hits a SyntaxError in the edited file
- **THEN** the traceback lands in `errors.json`, the web viewer can surface
  it, and fixing the file resumes building without restarting `solid develop`

#### Scenario: Broken project at launch

- **WHEN** the first build after `solid develop` fails to load the node
- **THEN** develop tears down its child processes and exits non-zero

### Requirement: Build completion is observable

The build pipeline SHALL distinguish a complete successful model publication
from an intermediate render pass, a watched source change, and a failed build.
Command and development lifecycle consumers SHALL use only complete successful
publication as the ready boundary for external observation. A complete
publication SHALL include the viewer snapshot and every model artifact it
references.

#### Scenario: A model needs multiple render passes

- **WHEN** generating a model requires more than one render pass
- **THEN** the pipeline does not report a complete successful publication
  until all current model artifacts and the current viewer snapshot are
  available

### Requirement: Uninterrupted build path for readers

The system SHALL publish each artifact by writing a temporary file in the
artifact's own directory and atomically replacing the target, so a reader
observes an artifact either complete or absent, never partially written, and a
reader that has already opened an artifact SHALL be able to read it to
completion after it is replaced. Publication SHALL use only operations that are
atomic on POSIX platforms, so the same behavior holds wherever the framework
runs. The system SHALL NOT guarantee that concurrently readable artifacts come
from a single build.

#### Scenario: Reader polls across a publication

- **WHEN** a consumer repeatedly reads a model artifact while a build
  republishes it
- **THEN** every read returns a complete artifact — the previous one or the new
  one — and never a partial file or a missing path

#### Scenario: A reader holds an artifact being replaced

- **WHEN** an artifact is replaced while a consumer is reading it
- **THEN** the consumer reads the bytes it opened to completion

### Requirement: Artifacts become reachable through the manifest

The system SHALL treat the viewer snapshot as the only thing that makes an
artifact reachable, and SHALL order a publication accordingly: every artifact a
build produces SHALL be in place before the snapshot naming it is written, and
an artifact the new snapshot no longer names SHALL be removed only after that
snapshot is in place.

#### Scenario: A new part appears

- **WHEN** a build adds a node and publishes
- **THEN** the node's artifact is readable before the snapshot naming it
  becomes visible

#### Scenario: A part is removed

- **WHEN** a build removes a node and publishes
- **THEN** the snapshot without that node becomes visible before its artifact
  is removed

### Requirement: A successful build sweeps unreferenced artifacts

After a successful publication the system SHALL remove files in the build
directory that the current viewer snapshot does not reference, other than the
snapshot, the error file, `.scad` inputs, `.brep` exact geometry, live render
lock files, and temporaries belonging to a build in progress. The sweep SHALL
be confined to the build directory.

`.brep` artifacts are spared by kind rather than by reference, because no
published document names them. As with `.scad` inputs, a superseded one is
therefore not removed by the sweep; mtime-equality caching means a superseded
artifact is never read.

#### Scenario: A renamed node leaves nothing behind

- **WHEN** a node is renamed and the project is rebuilt successfully
- **THEN** the artifact under the old name is gone from the build directory and
  the artifact under the new name is present and referenced

#### Scenario: A failed build sweeps nothing

- **WHEN** a build fails
- **THEN** no artifact is removed from the build directory

#### Scenario: Exact geometry survives the sweep

- **WHEN** a build of exact nodes publishes successfully and sweeps
- **THEN** every `.brep` written for a current node is still present, though
  the published snapshot names none of them

### Requirement: Error file lifecycle

The system SHALL write `errors.json` atomically, SHALL remove it after a
successful publication, and SHALL NOT remove it as a side effect of any other
operation. A consumer SHALL never observe a newly published model together with
the error file from the build that preceded it.

#### Scenario: A build succeeds after a failure

- **WHEN** a build succeeds after a previous build wrote `errors.json`
- **THEN** the new artifacts and snapshot are published and `errors.json` is
  gone

#### Scenario: A build fails after a success

- **WHEN** a build fails
- **THEN** `errors.json` describes that failure and no partially written error
  file is ever readable

### Requirement: Build artifacts stay out of version control

The system SHALL keep published build artifacts untracked by Git without
requiring the user to act. A scaffolded project SHALL ignore the build path and
the files the framework keeps beside it. For a project whose ignore rules do not
already cover them, the system SHALL record the exclusion in the repository's
local exclude file rather than in a tracked ignore file, and SHALL do nothing
when it cannot.

#### Scenario: Scaffolded project

- **WHEN** a user creates a project with `solid new` and builds it
- **THEN** neither the build path nor the project build lock appears as an
  untracked file

#### Scenario: Existing project whose ignore rules predate this layout

- **WHEN** a project whose tracked ignore file does not cover the build path is
  built
- **THEN** the exclusion is recorded locally, no tracked file is modified,
  and the working tree does not become dirty

#### Scenario: Ignore rules already cover the artifacts

- **WHEN** the project's tracked ignore file already covers the build path
- **THEN** no local exclusion is recorded
