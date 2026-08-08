## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Build artifact layout

The system SHALL write build artifacts under `$SOLID_BUILD_DIR` (default
`_build`), mirroring the source file's directory, with basename
`<script-name>-<uniq_id>`. A relative `$SOLID_BUILD_DIR`, and the default,
SHALL resolve against the discovered project root and never against the working
directory, so that a project has one build directory and — because the build
lock is derived from it — one build lock, whichever directory a command was run
from. An absolute `$SOLID_BUILD_DIR` SHALL be used as given. Artifacts per node:
`.scad` (base geometry, no transforms), `.stl` (rendered), and `.stl.lock`
during rendering. World-space spatial math does not use on-disk artifacts — the
`mesh` property loads the plain `.stl` and applies operations in memory (the
`.mesh.scad`/`.mesh.stl` path attributes exist but are vestigial; nothing
writes or reads them). The build path SHALL be an ordinary directory that every
builder writes into directly; the system SHALL NOT publish through a symlink, a
versioned sibling directory, or a private candidate copy. A build path left as
a symlink by an earlier layout SHALL be converted to an ordinary directory
holding the artifacts it referenced.

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
