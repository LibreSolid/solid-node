## MODIFIED Requirements

### Requirement: Mtime-equality caching

The system SHALL treat an artifact as up to date iff it exists AND its mtime
equals the node's `mtime`, where `node.mtime` is the maximum source-file
mtime across all files tracked for the node (`node.files`, aggregated
recursively from children). After generating an artifact the system SHALL
back-date its mtime to the source mtime via `os.utime` so the equality holds.
A change to any contributing source file invalidates all ancestor artifacts.

The comparison SHALL be exact equality of integer nanoseconds, and the system
SHALL read source and artifact timestamps, and stamp artifacts, in integer
nanoseconds. It SHALL NOT decide currency from a floating-point timestamp, and
it SHALL NOT accept an artifact whose stamp merely approximates the node
mtime. No tolerance window exists: an artifact carrying any value other than
the one the system stamped is not current.

The back-date SHALL therefore be a fixed point wherever the filesystem holding
the artifacts stores timestamps at the same resolution as the filesystem
holding the sources, whatever that resolution is. A project whose source files
carry sub-second mtimes SHALL cache its artifacts normally on a
coarse-resolution filesystem — including one that stores timestamps to the
millisecond — rather than rebuilding every node on every build.

Where the system cannot store the exact stamp — an artifact filesystem coarser
than the source filesystem — the artifact SHALL report not current and be
rebuilt. Currency SHALL fail only in this direction: a source that has changed
SHALL NOT be reported current under any timestamp resolution.

When, and only when, mtime equality fails, the system SHALL consult a
content-verified fallback before rebuilding. It SHALL compare a digest of the
node's tracked sources, as they are on disk now, against the digest recorded
for that artifact when the artifact was produced. When the two agree, the
sources that produced the artifact are byte-identical to the sources present,
so the system SHALL restamp the artifact to the current `node.mtime` and treat
it as current rather than re-deriving it. When they disagree, when no digest
was recorded, or when any tracked source cannot be read, the artifact SHALL be
rebuilt exactly as it is today.

The digest SHALL be scoped to the node, not to the file. A tracked source file
that defines more than one node class contributes to a node's digest only the
text that node can depend on: the file with the class bodies of the *other*
node classes defined at its top level removed. Everything else in the file —
imports, module-level statements, constants, functions and classes that are
not node classes — SHALL remain in every node's digest, so an edit to code the
nodes share still invalidates all of them. A node class whose name the
retained text refers to, as an identifier or as a string literal, SHALL NOT be
removed from that node's digest, so a node that reaches a sibling — as a base
class, through a helper, or by name — is still rebuilt when the sibling
changes. An internal node's digest SHALL cover the union of its children's
scopes, as its tracked file set already covers the union of their files, so a
fusion whose children share its file rebuilds when any of them changes.

Only a node class defined as a top-level statement of the file SHALL be
removable. Where the system cannot determine which top-level classes are node
classes, or cannot parse the file, it SHALL digest the whole file. A file that
defines exactly one node class, a file that defines none, and a source that is
not Python SHALL digest exactly as they would without scoping, byte for byte,
so a digest recorded for such a file before this rule remains valid under it.
The scope is not recorded beside the artifact: a node whose scope changes
rebuilds once.

One node per file is not a requirement or a recommendation of this rule. The
system SHALL NOT need a project to be laid out one node class per file to
rebuild only what an edit changed.

The fallback SHALL NOT run when mtime equality succeeds, so the cost of the
common path is unchanged. It SHALL read only the node's own tracked source
files, never its artifacts. Recording the digest SHALL happen wherever the
artifact is stamped, so an artifact and the digest that vouches for it are
written together or not at all.

The fallback SHALL preserve the direction-of-failure guarantee: it can only
report current an artifact whose sources are identical, which is a stricter
condition than the mtime equality it stands behind. It SHALL NOT report current
an artifact whose sources differ, and SHALL NOT weaken any case in which the
mtime rule already rebuilds for a genuine content change. Where a restamp
cannot achieve equality — the coarse-filesystem case above — the artifact SHALL
still be treated as current for this build on the strength of the digest, and
the fallback SHALL simply be consulted again next time rather than looping.

The recorded digest SHALL live inside the build directory, SHALL NOT be
referenced by the published viewer document, and SHALL NOT change what
publication means. A successful build's sweep of unreferenced artifacts SHALL
keep the digest belonging to an artifact it keeps, and SHALL NOT leave a digest
behind for an artifact it removes.

For an exact node the `.brep` artifact SHALL participate in this rule exactly
as the `.stl` does: the node's artifacts are current only when both are, so a
node whose mesh is current but whose exact geometry is absent or stale SHALL
be rendered rather than skipped. A build directory produced before the node
became exact therefore reports not-current once and is rebuilt.

Mtime equality decides source currency, never binding currency. A flexible
leaf's snapshot artifact (the `flexible-parts` capability) is addressed by a
name that includes a hash of the bound parameter values, so a changed binding
selects a different artifact rather than defeating this rule; within one
binding the snapshot participates in mtime currency exactly as any
adapter-owned artifact does.

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

#### Scenario: A timestamp moves but no content changes

- **WHEN** every source file's mtime is rewritten with no byte changed — as a
  fresh clone, a branch switch, a stash pop or a copy does — and the project is
  rebuilt
- **THEN** no geometry is re-derived, every artifact is restamped to the new
  source mtime and is byte-identical to the one already published, and the
  published document names the same tree and the same artifacts — differing
  only in the source mtimes it records per node, which a timestamp rewrite
  genuinely moves and which no build has ever held stable across one

#### Scenario: A rewritten source with different content still rebuilds

- **WHEN** a source file is rewritten with different content
- **THEN** the digest disagrees, the artifact is re-derived, and the fallback
  does not report it current

#### Scenario: The fast path is not slowed

- **WHEN** an artifact's mtime already equals the node mtime
- **THEN** currency is decided from that alone, and no source file is read for
  a digest

#### Scenario: An artifact with no recorded digest

- **WHEN** an artifact produced before this rule existed reports a stale mtime
- **THEN** it is rebuilt as it is today, and gains a digest when it is written

#### Scenario: A library change does not invalidate

- **WHEN** a node imports a module from outside the project tree
- **THEN** that module is not part of the node's tracked files

#### Scenario: Two node classes in one file rebuild independently

- **WHEN** a file defines two leaf node classes, both artifacts are current,
  and the body of one class is edited
- **THEN** the edited node's artifacts are re-derived and the other node's
  artifacts are restamped to the new source mtime and not re-derived

#### Scenario: Shared code in a shared file invalidates every node in it

- **WHEN** a file defines two node classes and a module-level constant,
  function or non-node class they can both see is edited
- **THEN** both nodes' artifacts are re-derived

#### Scenario: A node that refers to a sibling follows it

- **WHEN** a file defines two node classes and one of them reaches the other —
  as a base class, through a module-level helper that names it, or by its name
  as a string — and the other's body is edited
- **THEN** the referring node's artifacts are re-derived as well

#### Scenario: A fusion sharing its children's file follows them

- **WHEN** a file defines a fusion and the leaves it is built from, and one
  leaf's body is edited
- **THEN** the fusion's artifacts and that leaf's artifacts are re-derived, and
  the other leaf's are not

#### Scenario: A single-class file digests as it always has

- **WHEN** a digest is computed for a node whose tracked files each define one
  node class or none
- **THEN** every entry of the digest is the sha256 of that file's bytes, so a
  digest recorded before scoping existed still matches

#### Scenario: A multi-node file rebuilds once after upgrading

- **WHEN** a build directory whose sidecars were recorded with whole-file
  digests is built by the current version and a file defining several node
  classes has been touched
- **THEN** the nodes in that file are re-derived once, and report current on
  the next build

#### Scenario: Unchanged sources skip rendering

- **WHEN** `generate_stl` runs and the STL mtime equals `node.mtime`
- **THEN** no OpenSCAD process is launched

#### Scenario: Missing exact geometry is not current

- **WHEN** an exact node's `.stl` and `.scad` are current but its `.brep` is
  absent
- **THEN** the node reports not-up-to-date and is rendered, producing both

#### Scenario: Sub-second source mtimes cache on a coarse-resolution filesystem

- **WHEN** a project whose source files carry arbitrary sub-second mtimes is
  built twice with no edit between the builds, on a filesystem that stores
  timestamps to the millisecond
- **THEN** the second build reports every artifact current and renders nothing

#### Scenario: Exact artifacts cache on a coarse-resolution filesystem

- **WHEN** an exact rigid node is built twice with no edit between the builds,
  on a filesystem that stores timestamps to the millisecond
- **THEN** both its `.stl` and its `.brep` report current on the second build
  and neither is rewritten

#### Scenario: A coarse filesystem never makes a changed source look current

- **WHEN** a source file is modified after a build, on a filesystem that
  stores timestamps to the millisecond
- **THEN** the node's artifacts report not-up-to-date and are regenerated,
  whatever the sub-millisecond remainder of either timestamp

#### Scenario: Artifacts stamped by an earlier version rebuild once

- **WHEN** a build directory whose artifacts were stamped through the previous
  floating-point back-date is built by the current version
- **THEN** those artifacts report not-up-to-date and are regenerated once,
  after which they report current

#### Scenario: A source edit invalidates a flexible snapshot

- **WHEN** a flexible leaf's source file is modified after its snapshot
  artifact was written and the node is re-assembled at the same binding
- **THEN** the snapshot reports not-up-to-date and is re-evaluated

#### Scenario: A binding change selects a different snapshot

- **WHEN** a flexible leaf is re-assembled at a different bound snapshot with
  unmodified sources
- **THEN** a differently named snapshot artifact is produced, and the prior
  one's currency is untouched until the sweep collects it
