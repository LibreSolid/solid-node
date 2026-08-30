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
node's tracked source files, as they are on disk now, against the digest
recorded for that artifact when the artifact was produced. When the two agree,
the sources that produced the artifact are byte-identical to the sources
present, so the system SHALL restamp the artifact to the current `node.mtime`
and treat it as current rather than re-deriving it. When they disagree, when no
digest was recorded, or when any tracked source cannot be read, the artifact
SHALL be rebuilt exactly as it is today.

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
