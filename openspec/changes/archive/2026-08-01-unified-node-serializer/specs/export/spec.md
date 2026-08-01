## MODIFIED Requirements

### Requirement: Manifest contract

The manifest SHALL retain the document name `manifest.json` and SHALL declare
`format: "solid-node-export"`, `version: 1`, `animation: {fps, frames}`, and a
`root` tree with the same observable schema and child-name behavior as the
normal-build `viewer.json`. A rigid node SHALL emit one `model` reference and
stop recursion; a non-rigid node whose render result is a list or tuple SHALL
recurse into its children. Each node SHALL carry `name`, `type`, `color`, `mtime`, and
its operations as raw unevaluated expression strings so `$t` animation is
preserved verbatim. A rigid model reference SHALL remain rooted beneath the
export's `models/` directory and SHALL resolve to a copied artifact so the
export remains portable and self-contained. Changes to the shared tree shape or
operation serialization are breaking and MUST bump `version` and update every
producer and consumer of the shared schema together.

#### Scenario: Animated operations survive export

- **WHEN** an assembly's rotation is `$t * 360`
- **THEN** the manifest stores that expression as a string, not a baked
  numeric pose

#### Scenario: Linked names and additive metadata survive export

- **WHEN** an assembly returns children held by named attributes or list/tuple
  attributes
- **THEN** `manifest.json` uses their established linked names and includes
  each node's `mtime`, matching the shared node fields emitted in `viewer.json`

#### Scenario: A rendered child is recreated and rebound

- **WHEN** an assembly recreates a logical child and stores it on an attribute
  during each render
- **THEN** `manifest.json` and normal-build `viewer.json` publish the same
  attribute-derived child name

#### Scenario: A rendered child is reachable only through internal children state

- **WHEN** a child is reachable only through the parent's public `children`
  list when document serialization links it
- **THEN** both documents publish its established `children-<index>` name

#### Scenario: A rendered child has no parent attribute

- **WHEN** a child is not referenced by any parent attribute
- **THEN** its existing class-name fallback remains unchanged

#### Scenario: Export paths remain portable

- **WHEN** a rigid node is exported
- **THEN** its manifest model path is rooted beneath `models/` and resolves to
  the copied deduplicated STL within the export directory
