## ADDED Requirements

### Requirement: Viewer command

The system SHALL provide `solid viewer`, a command that takes no node path and
prints one JSON object on standard output with the absolute path of the
installed viewer bundle and its integer API version. When no built bundle is
installed it SHALL print nothing on standard output, report the remedy on
standard error, and exit 1. Its reported contents are specified in the
viewer-distribution capability.

#### Scenario: Viewer command appears in CLI help

- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `viewer`

#### Scenario: A consumer reads the installed viewer

- **WHEN** a program runs `solid viewer` against an installation with a built
  bundle
- **THEN** it parses one JSON object carrying the bundle path and API version,
  and the command exits 0

#### Scenario: No bundle installed

- **WHEN** a user runs `solid viewer` in an installation with no built bundle
- **THEN** the command exits 1 and standard error names how to obtain one

## MODIFIED Requirements

### Requirement: Node path resolution

The system SHALL require a `path` positional for every command that operates
on a node (all except `new` and `viewer`), and SHALL rewrite a directory path to
`<dir>/__init__.py` before loading.

#### Scenario: Package node

- **WHEN** a user runs `solid develop root` where `root/` is a package
- **THEN** the node is loaded from `root/__init__.py`

#### Scenario: A command that operates on the installation

- **WHEN** a user runs `solid viewer` with no further argument
- **THEN** the command runs and does not require or load a node
