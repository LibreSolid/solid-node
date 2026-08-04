## ADDED Requirements

### Requirement: Project root discovery and model reference

The system SHALL determine a project's root by walking upward from the working
directory to the nearest ancestor `pyproject.toml` containing a
`[tool.solid-node]` table, and SHALL treat the directory holding that file as
the project root. That table's `model` key SHALL hold an entry-point object
reference naming the project's model node, in the form
`package.module:ClassName`.

The discovered root — never the working directory — SHALL anchor the import
path used to load project modules, the dotted module name computed for a file
loaded by path, and the boundary of a node's tracked source closure. A command
SHALL therefore resolve the same node and the same source closure from any
directory inside the project.

When no ancestor `pyproject.toml` carries the table, a command that needs a
node SHALL fail with an actionable error naming the directory it searched from.

#### Scenario: Command run from a subdirectory

- **WHEN** a user runs a node-scoped command from a subdirectory of a project
  whose `pyproject.toml` declares `[tool.solid-node] model`
- **THEN** the project root is discovered from that manifest
- **AND** the node's tracked source closure is the same set it would be from
  the project root

#### Scenario: No manifest above the working directory

- **WHEN** a node-scoped command runs with no argument and no ancestor
  `pyproject.toml` carries a `[tool.solid-node]` table
- **THEN** the command exits nonzero with an error naming the search origin

## MODIFIED Requirements

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
