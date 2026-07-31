## MODIFIED Requirements

### Requirement: Path-based node loading

The system SHALL load nodes by filesystem path: the loader imports the `.py`
file and returns the single `AbstractBaseNode` subclass defined in it. When a
file defines multiple node classes, the module MUST set a module-level
`NODE = <Class>` marker naming the intended class; otherwise the loader raises
`AmbiguousNodeError`. An explicit marker MAY name a node class imported from
another project-local module, but MUST reject a non-node value or a class
defined outside the active project. Implicit discovery without a marker SHALL
consider only classes defined in the loaded file. The loaded entry-point file
and the selected class's project-local implementation/import closure SHALL all
contribute to the node's tracked source set. Companion tests are discovered as
`test_<file>.py` for module nodes and `test.py` for package nodes.

#### Scenario: Ambiguous module

- **WHEN** a file defines two node classes and no `NODE` marker
- **THEN** loading raises `AmbiguousNodeError`

#### Scenario: Imported classes are ignored implicitly

- **WHEN** a file imports node classes, defines exactly one of its own, and has
  no `NODE` marker
- **THEN** the loader picks the locally defined class

#### Scenario: Project package re-exports its node

- **WHEN** a project entry-point file sets `NODE` to an
  `AbstractBaseNode` subclass imported from another module in the same project
- **THEN** the loader instantiates the imported class
- **AND** the entry-point file and implementation source are both tracked

#### Scenario: Imported marker target is outside the project

- **WHEN** a project entry-point file sets `NODE` to a class defined outside
  the active project
- **THEN** loading raises an actionable `AmbiguousNodeError`
