## ADDED Requirements

### Requirement: Declared connected-body count

A node MAY declare, through a class-level `bodies` attribute, how many
connected solids its own built mesh must have. The default SHALL be `None`,
leaving the node unchecked so that a project which does not ask for the check
never loads its meshes on account of it. `FusionNode` SHALL declare
`bodies = 1`, making "a single, inseparable unit" a checked property rather
than a docstring promise.

`verify_bodies()` SHALL raise `DisconnectedBodyError`, naming the node, the
declared count, and the actual one, when a declared count does not match the
number of connected components of the node's mesh. A node that declares no
count, and a node that is not rigid, SHALL be skipped without its mesh being
read.

#### Scenario: A fusion arrives in pieces

- **WHEN** `verify_bodies()` runs on a `FusionNode` whose children do not
  actually overlap
- **THEN** it raises `DisconnectedBodyError` naming the node and its body
  count

#### Scenario: An undeclared node is not checked

- **WHEN** `verify_bodies()` runs on a node that leaves `bodies` at its
  default
- **THEN** it returns without reading the node's mesh

#### Scenario: A non-rigid node is not checked

- **WHEN** `verify_bodies()` runs on a non-rigid node that declares a count
- **THEN** it returns without reading the node's mesh
