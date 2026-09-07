## MODIFIED Requirements

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
