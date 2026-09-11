## MODIFIED Requirements

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

The ordinary `solid build` and SCAD presentation path SHALL retain `.scad`
(base geometry, no transforms) deliverables. Geometry/document-only consumers
under `backend-neutral-materialization` SHALL NOT require or generate assembly
SCAD deliverables, but SHALL still produce SCAD source when a selected backend
needs it. Other artifacts remain `.stl` (rendered) and `.stl.lock` during
external rendering. A node that is exact under the `exact-geometry` capability
SHALL additionally write
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

Subject to the producer recipe identity requirement below, the system SHALL
treat an artifact as up to date on its metadata-only path iff it exists,
its mtime equals the node's `mtime`, and its recorded source-set
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

When the producer recipe is compatible but artifact mtime equality or
source-set fingerprint equality fails, the system SHALL consult a
content-verified fallback before rebuilding. A mismatched producer recipe
SHALL NOT enter that fallback. The fallback SHALL compare a digest of the
node's tracked sources, as they are on disk now,
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
it keeps and SHALL NOT leave one behind for an artifact it removes. For a
producer whose recipe is unchanged, the reader
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

- **WHEN** the producer recipe is unchanged and every source file's mtime is
  rewritten with no byte changed, as a
  clone, branch switch, stash pop, or copy can do
- **THEN** the digest match prevents geometry from being re-derived, every
  artifact is restamped and records the current fingerprint, and the published
  document differs only in its recorded source mtimes

#### Scenario: A rewritten source with different content still rebuilds

- **WHEN** a source file is rewritten with different content
- **THEN** its fingerprint leaves the metadata-only path, its digest disagrees,
  and the artifact is re-derived

#### Scenario: The fast path is not slowed

- **WHEN** the producer recipe is compatible and an artifact's mtime and
  recorded source-set fingerprint match the node's current source state
- **THEN** currency is decided without reading source bytes for a digest or
  parsing Python source

#### Scenario: A legacy digest-only record upgrades safely

- **WHEN** the producer recipe is unchanged and an artifact's mtime equals the
  node mtime but its sidecar contains a valid legacy digest with no source-set
  fingerprint
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

- **WHEN** `generate_stl` runs, the producer recipe is compatible, and both
  the STL mtime and source-set fingerprint match
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
raising `StlRenderStart`. A fusion with any non-exact descendant SHALL
produce its artifact through direct mesh composition under
`backend-neutral-materialization`, not this OpenSCAD subprocess protocol.
Its OpenSCAD-authored children still use this protocol where required.

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

#### Scenario: A faceted fusion composes current child meshes

- **WHEN** a `FusionNode` holding a non-exact descendant is built
- **THEN** its child artifacts become current before the fusion unions them
  directly, and no OpenSCAD render job is launched for the fusion itself

#### Scenario: The renderer is missing for a node that needs it

- **WHEN** a stale OpenSCAD-backed leaf must be rendered and no `openscad` is on
  the PATH
- **THEN** the build fails naming that node and the reason its backend needs
  OpenSCAD, and no subprocess launch error surfaces in its place

#### Scenario: An all-exact build makes no availability check

- **WHEN** `build_stls()` completes for a tree whose every rigid node is exact
- **THEN** no OpenSCAD availability check is performed and the absence of the
  binary is never reported

## ADDED Requirements

### Requirement: Producer recipe identity qualifies artifact currency

The system SHALL distinguish artifacts made by different geometry or
presentation recipes even when their project sources and parameter identity
are unchanged. A producer recipe change SHALL invalidate the affected
artifact before metadata or content-restamp reuse can certify it. A missing
legacy recipe record SHALL be incompatible for a producer changed by this
cycle, while unchanged producer recipes SHALL retain legacy source-record
compatibility.

A faceted fusion SHALL incorporate the current direct-mesh recipe and the
relevant recipes of its child geometry into its currency. Nested fusions
SHALL NOT reuse an enclosing artifact produced using superseded child
geometry recipes. Recipe identity SHALL NOT change node names, parameter
identity or artifact paths. Printed-piece identity SHALL continue to derive
from the actual produced STL bytes.

Recipe records SHALL remain private build metadata, published atomically
with the existing source-currency discipline. This qualification SHALL NOT
relax source checks, generation checks, artifact observations or publication
ordering, and SHALL NOT turn every framework edit into an all-project rebuild.

#### Scenario: An old fusion cache does not mask the new producer

- **WHEN** a project's sources are unchanged but its fusion STL was produced
  through the old OpenSCAD fusion recipe
- **THEN** the first new build recomputes that fusion by direct mesh union and
  records its new recipe, and the next unchanged build reuses it

#### Scenario: A nested fusion follows its child's recipe

- **WHEN** an enclosing fusion has a source-current artifact but a nested
  fusion's production recipe has changed
- **THEN** both affected fusion artifacts are rebuilt in dependency order

#### Scenario: Unchanged exact geometry stays cached

- **WHEN** exact leaf and exact fusion artifacts have unchanged source state
  and unchanged production recipes
- **THEN** upgrading this cycle does not re-derive their geometry merely
  because the framework version changed

#### Scenario: Content equality cannot bless the wrong recipe

- **WHEN** an artifact's project-source digest matches but its recorded
  producer recipe does not
- **THEN** the artifact is rebuilt rather than restamped as current
