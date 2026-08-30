## ADDED Requirements

### Requirement: The tracked source set is unchanged

The system SHALL produce, for every node in a loaded tree, exactly the source
closure it produces today: the same set of project-local files, the same
`mtime_ns` derived from them, and therefore the same artifact paths and the
same up-to-date decisions.

Changing how the package of a file is looked up SHALL NOT change which files a
node tracks, in either direction. A file that contributes today SHALL still
contribute; a file that does not SHALL still not.

#### Scenario: A real tree is byte-for-byte the same

- **WHEN** a project of several hundred nodes is loaded and assembled under the
  indexed lookup and under a linear rescan of `sys.modules`
- **THEN** every node in both trees carries the same source closure, the same
  `mtime_ns`, and the same artifact path

#### Scenario: Relative imports still resolve

- **WHEN** a node's module reaches a sibling module through a relative import
- **THEN** that sibling is in the node's tracked source set, as it is today

#### Scenario: A file outside the project is still excluded

- **WHEN** a node's module imports a module that is not project-local
- **THEN** that module's file is absent from the node's tracked source set

### Requirement: Resolution does not scale with the loaded module set

The system SHALL resolve the package a project file was imported as without
performing filesystem path resolution proportional to the number of modules the
interpreter has loaded.

Loading the same project in an interpreter that has imported many more
unrelated modules SHALL NOT multiply the filesystem work performed while
building its source closures. In particular, the system SHALL NOT call
`os.path.realpath` once per loaded module on every lookup.

#### Scenario: More loaded modules do not cost more path resolution

- **WHEN** the same project is loaded twice, the second time in an interpreter
  that has imported a substantially larger set of unrelated modules
- **THEN** the number of filesystem path-resolution calls made while building
  the source closures does not grow in proportion to the number of loaded
  modules

#### Scenario: One project file is resolved once

- **WHEN** many nodes are constructed from the same project file
- **THEN** the package that file was imported as is resolved without repeating
  a scan of the loaded module set for each node

### Requirement: A late import is still resolved

The system SHALL NOT let a stale index change an answer. When a module is
imported after the lookup has already been used, a subsequent lookup for that
module's file SHALL resolve it exactly as a fresh scan would.

Correctness SHALL NOT depend on the index being warm, on load order, or on any
caller priming it.

#### Scenario: A module imported after the first lookup

- **WHEN** a project file's package is looked up, another project module is
  then imported, and that new module's file is looked up
- **THEN** the second lookup returns the package the new module was imported
  as, not `None`

#### Scenario: A file belonging to no loaded module

- **WHEN** the package is looked up for a path that no loaded module was
  imported from
- **THEN** the result is `None`, as it is today, and no error is raised
