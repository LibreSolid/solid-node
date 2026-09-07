# Build Pipeline Specification

## Purpose

How source files become STL artifacts: path-based node loading, the build
artifact layout, mtime-equality caching, concurrent render locking, and the
watch-rebuild loop. Encodes ADR-005 (path-based dynamic module loading),
ADR-006 (mtime-based STL caching), ADR-007 (watchdog filesystem monitoring),
ADR-018 (file-based error propagation, superseding the broker of
ADR-016/017), the loader rules of ADR-026, and ADR-067 (fresh-interpreter
build subprocesses).

Code: `solid_node/core/loader.py`, `solid_node/core/builder.py`,
`solid_node/core/processes.py`, `solid_node/node/base.py` (artifact/caching
layer).
## Requirements
### Requirement: Project root discovery and model reference

The system SHALL determine a project's root by walking upward from a discovery
origin to the nearest ancestor `pyproject.toml` containing a
`[tool.solid-node]` table, and SHALL treat the directory holding that file as
the project root.

When the table has no `models` sub-table, its `model` key SHALL hold an
entry-point object reference naming the project's model node, in the form
`package.module:ClassName`, and the project SHALL have that one model.

When the table has a `models` sub-table (`[tool.solid-node.models]`), each of
its keys SHALL be a model name and each value an entry-point object reference
in the form `package.module:ClassName`. A model name SHALL be one word of
letters, digits, underscores and hyphens, starting with a letter or underscore,
and SHALL NOT equal the name of a directory at the project root, because that
directory's artifacts mirror into the same place. The table SHALL NOT be
empty. The `model` key MAY then name the project's default model and, when
present, SHALL equal one of the table's keys; a manifest whose `model` holds
anything else beside a `models` table is malformed. A project with the table
and no `model` key has no default model.

A manifest that violates any of these rules SHALL cause a command that needs a
node to fail with an actionable error naming the manifest and the rule.

The discovery origin SHALL be the referenced file when the reference names a
path, because a path identifies a project as surely as it identifies a file.
It SHALL be the working directory when there is no reference, or when the
reference is a qualifier or a declared model name, which carry no location.

The discovered root — never the working directory — SHALL anchor the import
path used to load project modules, the dotted module name computed for a file
loaded by path, the boundary of a node's tracked source closure, and the
project's build root. A command SHALL therefore resolve the same node, the
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

#### Scenario: A manifest declares several models and a default

- **WHEN** a manifest declares `[tool.solid-node.models]` with
  `wall_clock_01 = "design.wall_clock_01.clock:WallClock01"` and
  `wall_clock_02 = "design.wall_clock_02.clock:WallClock02"`, and
  `model = "wall_clock_01"`
- **THEN** the project has two models named `wall_clock_01` and
  `wall_clock_02`, and its default model is `wall_clock_01`

#### Scenario: The default must be a declared name

- **WHEN** a manifest declares a `models` table and
  `model = "design.wall_clock_01.clock:WallClock01"`
- **THEN** a command that needs a node fails naming the manifest and stating
  that `model` must name one of the declared models

#### Scenario: A model name that shadows a source directory

- **WHEN** a manifest declares a model named `design` and the project root
  contains a directory `design/`
- **THEN** a command that needs a node fails naming the manifest, the name and
  the directory

#### Scenario: A single-model manifest is unchanged

- **WHEN** a manifest declares only `model = "windmill.windmill:Windmill"`
- **THEN** the project has one model, that reference, exactly as before

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

The system SHALL write build artifacts under a build directory, mirroring the
source file's directory, with basename `<script-name>-<uniq_id>`. The
project's **build root** is `$SOLID_BUILD_DIR` (default `_build`): a relative
value, and the default, SHALL resolve against the discovered project root and
never against the working directory, and an absolute value SHALL be used as
given.

For a project that declares no models, the build directory SHALL be the build
root itself, exactly as today. For a declared model, the build directory SHALL
be `<build root>/<name>/`, so that each declared model has its own published
`viewer.json`, its own `errors.json`, its own build lock and its own artifact
sweep, and publishing one model neither replaces nor removes another's
artifacts. A reference that is not a declared model — a sub-node named by
qualifier or path — SHALL build in the build root, as it does today, and the
build root's artifact sweep SHALL NOT descend into a declared model's
directory. A build lock file that lies inside a build directory SHALL be spared
by that directory's sweep.

Whichever directory a command was run from, a project therefore has one build
directory per model and — because the build lock is derived from it — one
build lock per model.

Artifacts per node: `.scad` (base geometry,
no transforms), `.stl` (rendered), and `.stl.lock` during rendering. A node
that is exact under the `exact-geometry` capability SHALL additionally write
`.brep`, holding that node's unplaced exact geometry under the same basename.
World-space spatial math does not use on-disk artifacts — the `mesh`
property loads the plain `.stl` and applies operations in memory (the
`.mesh.scad`/`.mesh.stl` path attributes exist but are vestigial; nothing
writes or reads them). Every build directory SHALL be an ordinary directory
that every builder writes into directly; the system SHALL NOT publish through
a symlink, a versioned sibling directory, or a private candidate copy. A build
path left as a symlink by an earlier layout SHALL be converted by moving the
directory that symlink references into the ordinary build path. Build
preparation SHALL NOT remove any other path merely because its name begins
with the build directory's name and a dot.

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
- **THEN** the build path becomes an ordinary directory holding the artifacts
  from the referenced directory, that referenced sibling is consumed, and
  every other sibling remains untouched

#### Scenario: Ordinary preparation preserves siblings

- **WHEN** a real build directory has sibling files or directories whose names
  begin with the build directory's name and a dot
- **THEN** preparing the build directory leaves every sibling unchanged

#### Scenario: Browser snapshot staging overlaps a build

- **WHEN** a browser snapshot stage beside the build directory remains in use
  after releasing the project build lock and another build prepares its
  directory
- **THEN** the stage and every artifact linked into it remain available to the
  capture process

#### Scenario: An exact node writes exact geometry beside its mesh

- **WHEN** an exact rigid node is built
- **THEN** a `.brep` artifact sits beside its `.stl` under the same basename

#### Scenario: A faceted node writes no exact artifact

- **WHEN** a rigid node that is not exact is built
- **THEN** no `.brep` artifact is written for it

#### Scenario: Published documents do not name exact geometry

- **WHEN** a build publishes its viewer snapshot for a project of exact nodes
- **THEN** the document references only `.stl` models and names no `.brep`

#### Scenario: Two declared models publish side by side

- **WHEN** a project declares models `wall_clock_01` and `wall_clock_02` and
  both are built
- **THEN** `_build/wall_clock_01/viewer.json` and
  `_build/wall_clock_02/viewer.json` both exist, each naming only artifacts
  under its own directory, and building the second removed nothing from the
  first

#### Scenario: Declared models do not share a lock

- **WHEN** a build of `wall_clock_01` is rendering
- **THEN** a build of `wall_clock_02` in the same project acquires its own
  lock and does not wait

#### Scenario: A sub-node build does not sweep the models

- **WHEN** a project declaring models builds a sub-node by qualifier, and its
  publication into the build root sweeps unreferenced artifacts
- **THEN** every artifact under the declared models' directories is still
  there

#### Scenario: A single-model project's directory is unchanged

- **WHEN** a project that declares no models is built
- **THEN** its artifacts, `viewer.json` and `errors.json` are written in the
  build root itself, at the paths they have today

### Requirement: Mtime-equality caching

The system SHALL treat an artifact as up to date on its metadata-only path iff
it exists, its mtime equals the node's `mtime`, and its recorded source-set
fingerprint equals the current fingerprint of every file tracked for the node
(`node.files`, aggregated recursively from children). `node.mtime` remains the
maximum source-file mtime across that set. After generating an artifact the
system SHALL back-date its mtime to the source mtime via `os.utime`. A change
observable in any contributing source's recorded metadata SHALL invalidate the
metadata-only path and all ancestor artifacts even when the maximum source
mtime is unchanged.

The source-set fingerprint SHALL cover a deterministic, sorted sequence of
project-relative real path, filesystem identity, byte size, integer-nanosecond
mtime, and integer-nanosecond change time for every tracked source. It SHALL
detect ordinary replacement, same-size rewrites, and content rewrites whose
mtime is restored. A filesystem or privileged external operation that changes
bytes while exposing the same path identity, size, mtime, and change time is
outside the guarantees of the metadata-only path; callers operating under that
condition MUST explicitly invalidate the artifact or its currency record.

The artifact mtime comparison SHALL be exact equality of integer nanoseconds,
and the system SHALL read source and artifact timestamps, and stamp artifacts,
in integer nanoseconds. It SHALL NOT decide currency from a floating-point
timestamp, and SHALL NOT accept an artifact whose stamp merely approximates
the node mtime. No tolerance window exists.

The back-date SHALL be a fixed point wherever the filesystem holding the
artifacts stores timestamps at the same resolution as the filesystem holding
the sources. A project whose source files carry sub-second mtimes SHALL cache
its artifacts normally on a coarse-resolution filesystem, including one that
stores timestamps to the millisecond.

Where the system cannot store the exact stamp, the artifact SHALL fail the
metadata-only path and enter content verification. Currency SHALL fail only in
the safe direction for every observable source change.

Whenever artifact mtime equality or source-set fingerprint equality fails, the
system SHALL consult a content-verified fallback before rebuilding. It SHALL
compare a digest of the node's tracked sources, as they are on disk now,
against the digest recorded for that artifact when it was produced. When they
agree, the system SHALL restamp the artifact to the current `node.mtime`,
record the current source-set fingerprint with the digest, and treat it as
current. When they disagree, when no digest was recorded, or when any tracked
source cannot be read, the artifact SHALL be rebuilt.

The digest SHALL be scoped to the node, not to the file. A tracked source file
that defines more than one node class contributes only the text that node can
depend on: the file with the class bodies of the other top-level node classes
removed. Imports, module-level statements, constants, functions, and non-node
classes SHALL remain in every node's digest. A node class whose name the
retained text refers to, as an identifier or string literal, SHALL remain. An
internal node's digest SHALL cover the union of its children's scopes.

Only a node class defined as a top-level statement SHALL be removable. Where
the system cannot determine which classes are node classes, or cannot parse
the file, it SHALL digest the whole file. A single-node file, a file defining
no node, and a non-Python source SHALL digest byte for byte as without scoping.
The scope is not recorded beside the artifact; a changed scope rebuilds once.
The system SHALL NOT require or recommend one node per file for currency.

The metadata-only path SHALL stat tracked sources and read the artifact's
currency record, but SHALL NOT read source contents or parse them. Content
verification SHALL read only the node's tracked source files, never its
artifacts. Recording the digest and fingerprint SHALL happen wherever the
artifact is stamped, so an artifact and the record that vouches for it are
written together or not at all.

The fallback SHALL preserve the direction-of-failure guarantee: it SHALL NOT
report current an artifact whose scoped source contents differ, and SHALL NOT
weaken any case in which a genuine observable content change already rebuilds.
Where a restamp cannot achieve equality because the artifact filesystem is
coarser, the artifact SHALL still be current for that build on the strength of
the matching digest, and the fallback SHALL be consulted again next time
rather than looping.

The currency record SHALL live inside the build directory, SHALL NOT be
referenced by the published viewer document, and SHALL NOT change publication
semantics. A successful sweep SHALL keep the record belonging to an artifact
it keeps and SHALL NOT leave one behind for an artifact it removes. The reader
SHALL accept a legacy digest-only record as having no fingerprint, validate it
through the content fallback even when artifact mtime equality succeeds, and
upgrade a matching record without re-deriving geometry. An unknown or malformed
record SHALL NOT certify an artifact.

For an exact node the `.brep` artifact SHALL participate exactly as the `.stl`
does: the node's artifacts are current only when both are. A build directory
produced before the node became exact therefore rebuilds once.

Mtime and source fingerprint decide source currency, never binding currency. A
flexible leaf's snapshot artifact is addressed by a name containing a hash of
its bound parameter values; within one binding it participates in this rule as
any adapter-owned artifact does.

A node's tracked files SHALL include its own source together with project-local
modules it imports transitively. Modules outside the project tree SHALL NOT be
tracked. Where the contributing set cannot be determined exactly, the system
SHALL track more files rather than fewer.

#### Scenario: Source edit invalidates ancestors

- **WHEN** a leaf's source file is modified
- **THEN** the leaf's STL and every ancestor STL report not-up-to-date and are
  regenerated on the next build

#### Scenario: Imported project module edit invalidates dependants

- **WHEN** a node imports a project helper, that helper changes, and another
  tracked source retains the unchanged maximum mtime
- **THEN** the node's source-set fingerprint differs and its artifact is
  regenerated with the helper's new values

#### Scenario: Restored mtime does not hide a same-size edit

- **WHEN** a tracked source is rewritten with different same-size bytes and its
  mtime is restored to its previous value
- **THEN** its filesystem change metadata makes the fingerprint differ, content
  verification rejects the old digest, and the artifact is regenerated

#### Scenario: A timestamp moves but no content changes

- **WHEN** every source file's mtime is rewritten with no byte changed, as a
  clone, branch switch, stash pop, or copy can do
- **THEN** the digest match prevents geometry from being re-derived, every
  artifact is restamped and records the current fingerprint, and the published
  document differs only in its recorded source mtimes

#### Scenario: A rewritten source with different content still rebuilds

- **WHEN** a source file is rewritten with different content
- **THEN** its fingerprint leaves the metadata-only path, its digest disagrees,
  and the artifact is re-derived

#### Scenario: The fast path is not slowed

- **WHEN** an artifact's mtime and recorded source-set fingerprint match the
  node's current source state
- **THEN** currency is decided without reading source bytes for a digest or
  parsing Python source

#### Scenario: A legacy digest-only record upgrades safely

- **WHEN** an artifact's mtime equals the node mtime but its sidecar contains a
  valid legacy digest with no source-set fingerprint
- **THEN** the digest is verified and, if it matches, the artifact is not
  re-derived and the sidecar is upgraded with the current fingerprint

#### Scenario: An artifact with no recorded digest

- **WHEN** an artifact has no recorded digest or has a malformed or unknown
  currency record
- **THEN** it is rebuilt and gains a valid current record

#### Scenario: A library change does not invalidate

- **WHEN** a node imports a module from outside the project tree
- **THEN** that module is not part of the node's tracked files or fingerprint

#### Scenario: Two node classes in one file rebuild independently

- **WHEN** a file defines two leaf node classes, both artifacts are current,
  and the body of one class is edited
- **THEN** the edited node's artifacts are re-derived and the other node's
  artifacts use their scoped digest to refresh the fingerprint without being
  re-derived

#### Scenario: Shared code in a shared file invalidates every node in it

- **WHEN** shared module-level code in a file defining two nodes is edited
- **THEN** both nodes' artifacts are re-derived

#### Scenario: A node that refers to a sibling follows it

- **WHEN** one node reaches a sibling as a base, through a helper, or by a
  string name, and the sibling's body is edited
- **THEN** the referring node's artifacts are re-derived as well

#### Scenario: A fusion sharing its children's file follows them

- **WHEN** a file defines a fusion and its leaves and one leaf's body is edited
- **THEN** the fusion and edited leaf are re-derived, while the other leaf uses
  its scoped digest without re-derivation

#### Scenario: A single-class file digests as it always has

- **WHEN** a digest is computed for a node whose tracked files each define one
  node class or none
- **THEN** every digest entry is the sha256 of that file's bytes

#### Scenario: A multi-node file rebuilds once after upgrading

- **WHEN** whole-file legacy digests are checked after touching a file that
  defines several node classes
- **THEN** nodes whose scoped digest differs rebuild once and then report
  current

#### Scenario: Unchanged sources skip rendering

- **WHEN** `generate_stl` runs and both the STL mtime and source-set fingerprint
  match
- **THEN** no OpenSCAD process is launched

#### Scenario: Missing exact geometry is not current

- **WHEN** an exact node's `.stl` and `.scad` are current but its `.brep` is
  absent
- **THEN** the node is rendered and produces both exact artifacts

#### Scenario: Sub-second source mtimes cache on a coarse-resolution filesystem

- **WHEN** a project with arbitrary sub-second source mtimes is built twice on
  a filesystem storing timestamps to the millisecond
- **THEN** the second build reports every artifact current and renders nothing

#### Scenario: Exact artifacts cache on a coarse-resolution filesystem

- **WHEN** an exact rigid node is built twice without edits on a filesystem
  storing timestamps to the millisecond
- **THEN** its `.stl` and `.brep` report current and neither is rewritten

#### Scenario: A coarse filesystem never makes a changed source look current

- **WHEN** a source is modified on a filesystem storing millisecond timestamps
- **THEN** the changed contributor's fingerprint or digest invalidates and
  regenerates the node, regardless of sub-millisecond timestamp remainders

#### Scenario: Artifacts stamped by an earlier version rebuild once

- **WHEN** artifacts stamped through the previous floating-point back-date are
  built by the current version
- **THEN** they are validated or regenerated once and then report current

#### Scenario: A source edit invalidates a flexible snapshot

- **WHEN** a flexible leaf's source changes after its snapshot was written and
  the node is re-assembled at the same binding
- **THEN** the snapshot reports not-up-to-date and is re-evaluated

#### Scenario: A binding change selects a different snapshot

- **WHEN** a flexible leaf is re-assembled at a different binding with
  unmodified sources
- **THEN** a differently named snapshot is produced and prior currency remains
  untouched until sweep

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
runner's build phase, and export — SHALL acquire that lock before any lifecycle
phase that can materialize SCAD, BREP, STL, or published documents, including
assembly, and SHALL release it as soon as that work is finished. Acquisition
SHALL block until the lock is available rather than fail or skip, and a wait
that does not resolve immediately SHALL be logged. The lock SHALL NOT be held
while a builder waits for a source change, invokes a completion callback, or
runs project test cases, and the lock file SHALL be excluded from version
control by the same rule that excludes published artifacts.

A holder that dies SHALL release the lock without any recovery step, because
the kernel releases it when the holding process ends.

#### Scenario: A second builder waits for the first

- **WHEN** a build is rendering a project and another process starts a build of
  the same project
- **THEN** the second process does not render or publish until the first has
  finished, and both report their own build outcome

#### Scenario: An assembly-time producer waits

- **WHEN** a cold exact or imported-file node starts through a framework entry
  point while another process holds its project build lock
- **THEN** no SCAD, BREP, or STL artifact is materialized until the lock is
  released, after which the entry point completes normally

#### Scenario: Test setup is locked and test execution is not

- **WHEN** the test runner builds a node and then executes its project test
  cases
- **THEN** keyframing, preliminary render, assembly, and STL generation occur
  while the project lock is held, and test-case execution begins after release

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
(`job.wait()`), until no renders remain. Waiting SHALL inspect the subprocess
exit status before finishing the render. A zero exit status SHALL finish the
render by stamping and atomically replacing the target STL and removing the
lock. A nonzero exit status SHALL remove the temporary output and lock, SHALL
leave any previously published target and its currency record unchanged, and
SHALL raise a build failure. Non-rigid nodes SHALL be skipped.

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

#### Scenario: A cold render fails

- **WHEN** OpenSCAD exits nonzero while rendering a node with no published STL
- **THEN** the build fails, the temporary STL and render lock are removed, and
  no target STL or viewer snapshot is published

#### Scenario: A replacement render fails

- **WHEN** OpenSCAD exits nonzero while rendering a replacement for a
  previously published STL
- **THEN** the build fails, the temporary STL and render lock are removed, and
  the previous target STL and viewer snapshot remain unchanged

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

### Requirement: Build subprocesses are isolated from the parent process

Every subprocess a build command starts to load a node, render an artifact, or
serve a viewer SHALL begin from a fresh interpreter that inherits none of the
parent process's native runtime state — in particular no thread pool, worker
team, or lock belonging to a native library the parent initialised.

A build SHALL therefore always reach an outcome: it publishes its artifacts, or
it fails with a reported error and a non-zero exit. It SHALL NOT stop
indefinitely without progress. What the parent process imported, and whether
that import ran geometry, SHALL NOT change whether a build completes.

Because a subprocess no longer inherits the parent's memory, what a build
command passes to one SHALL be limited to values that survive being reconstructed
in a fresh interpreter.

#### Scenario: The parent has already run geometry

- **WHEN** `solid build` resolves a model whose import runs geometry, leaving
  native worker threads live in the command's own process, and then starts its
  builder subprocess
- **THEN** the subprocess renders and publishes the model and the command exits
  0, rather than blocking forever on a worker team the parent left behind

#### Scenario: A cold build directory for a mesh-engine project

- **WHEN** `solid build` runs against a project whose nodes render through the
  in-process mesh engine and whose build directory holds no current artifacts,
  so every artifact must be tessellated
- **THEN** each artifact is rendered and published and the command exits 0

#### Scenario: The watch loop respawns a builder

- **WHEN** `solid develop` respawns its builder after a watched source file
  changes
- **THEN** the new builder starts from a fresh interpreter, rebuilds from the
  edited source, and the loop continues

### Requirement: Watch-rebuild loop

The system SHALL rebuild on change via a single-shot builder: it loads and
assembles the node, watches each file in `node.files` individually
(non-recursive, via watchdog), renders pending STLs, and exits when any
explicitly tracked source file reports a modification — regardless of filename
extension — so the develop loop can respawn it. Directory events are ignored.

When loading or assembly fails before the builder has a reliable tracked-source
set, the recovery watcher SHALL watch the project directory recursively and
SHALL accept modifications only to Python source outside `__pycache__`. Other
unclassified files SHALL remain filtered as recovery-watch noise.

#### Scenario: Edit triggers rebuild cycle

- **WHEN** a watched source file is saved during `solid develop`
- **THEN** the builder logs the change, exits, and is respawned to rebuild
  with the new source

#### Scenario: Tracked geometry-source edit triggers rebuild

- **WHEN** a successfully assembled node explicitly tracks a `.scad`, `.js`,
  `.stl`, or `.step` source and that file reports a modification
- **THEN** the builder exits its watch and the develop loop rebuilds from the
  changed geometry source without requiring a Python edit

#### Scenario: Broad recovery watch filters unrelated non-Python files

- **WHEN** a load or assembly failure starts the broad recursive recovery watch
  and an unclassified non-Python file reports a modification
- **THEN** the builder keeps waiting, while a Python source modification outside
  `__pycache__` resolves the watch

### Requirement: File-based build error propagation

The system SHALL report build errors by writing `{"error": ..., "tstamp":
...}` to `errors.json` in the build dir (no broker or socket IPC — ADR-018).
A prior error SHALL remain visible until a complete successful build has loaded,
assembled, rendered or verified every artifact, and constructed its complete
viewer document. The successful build SHALL then clear the error even when the
constructed document is byte-identical to the published `viewer.json`. An
initial-launch failure SHALL exit non-zero (develop terminates); a failure
during reload SHALL NOT kill the loop — the builder falls back to watching the
project directory recursively, writes the traceback to `errors.json`, and exits
cleanly on the next save so development continues.

#### Scenario: Syntax error during development

- **WHEN** a reload hits a SyntaxError in the edited file
- **THEN** the traceback lands in `errors.json`, the web viewer can surface
  it, and fixing the file resumes building without restarting `solid develop`

#### Scenario: Broken project at launch

- **WHEN** the first build after `solid develop` fails to load the node
- **THEN** develop tears down its child processes and exits non-zero

#### Scenario: Byte-identical build recovers prior failure state

- **WHEN** a complete successful build constructs the same viewer document
  already on disk while its build directory contains a prior `errors.json`
- **THEN** the error file is removed without rewriting the byte-identical
  viewer document, and directory-derived model status is `published`

#### Scenario: Document construction still fails

- **WHEN** a build with a prior `errors.json` fails while constructing its
  viewer document
- **THEN** the prior error remains visible and the build does not report
  recovery

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

### Requirement: Loading binds declared driver defaults

When the build or test path loads a node whose tree declares drivers,
it SHALL bind every declared driver's default — enumerated across the
whole linked tree by qualified id — before the node's first render, so
a driver-declaring project builds, tests, and serves through the CLI
without binding its own defaults in `__init__` and without a running
simulation. A tree declaring no drivers SHALL load exactly as before.
Default binding SHALL live outside `solid_node/node/`, preserving the
rule that the node layer never imports the simulation layer.

#### Scenario: A driver-declaring project builds without self-binding

- **WHEN** the CLI builds a project whose assembly's `render()` reads
  a declared driver and whose `__init__` binds nothing
- **THEN** the build succeeds with the declared default bound, with no
  unbound-state error

#### Scenario: A driverless project loads unchanged

- **WHEN** the CLI builds a project declaring no drivers (the
  v8-engine path)
- **THEN** loading performs no state binding and behavior is identical
  to before this change
