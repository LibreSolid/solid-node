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
