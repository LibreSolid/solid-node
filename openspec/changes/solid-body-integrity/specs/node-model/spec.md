## MODIFIED Requirements

### Requirement: Rigid vs non-rigid distinction

The system SHALL distinguish rigid nodes (`rigid = True`; can produce a cached
STL) from non-rigid nodes. Rigidity SHALL be determined by node type and SHALL
NOT be recomputed from a node's children: `LeafNode` and `FusionNode` are
rigid, `AssemblyNode` is non-rigid. Only rigid nodes generate STL files.

A `FusionNode` SHALL reject a non-rigid child. Fusion combines solids into one
solid; an assembled thing cannot be fused. The rejection SHALL name the fusion
and the offending child and SHALL happen during render validation, before any
geometry is produced.

A **topmost rigid node** is a rigid node whose parent is non-rigid, or the root
node when the root is itself rigid. Because a fusion cannot contain an
assembly, every rigid node is either a topmost rigid node or a descendant of
exactly one.

#### Scenario: An assembly cannot be fused

- **WHEN** a `FusionNode` renders a child that is an `AssemblyNode`, or any
  other non-rigid node
- **THEN** an exception is raised naming the fusion and that child, and no
  geometry is produced

#### Scenario: Rigidity is not recomputed from children

- **WHEN** a `FusionNode` renders a subtree of leaves and nested fusions
- **THEN** it remains rigid, and its rigidity is its type's, not derived by
  combining its children's

#### Scenario: STL access on non-rigid node

- **WHEN** the `stl` property is read on a non-rigid node
- **THEN** an exception is raised

#### Scenario: The topmost rigid node under an assembly

- **WHEN** an `AssemblyNode` holds a `FusionNode` that itself holds leaves and
  a nested fusion
- **THEN** the outer `FusionNode` is the topmost rigid node of that branch, and
  the leaves and nested fusion are not

## REMOVED Requirements

### Requirement: Declared connected-body count

**Reason**: A per-node body-count declaration answers the wrong question. It
invites parts to be designed as several disconnected solids, when the only
sound contract for a printed solid is that it is exactly one body. The
declaration also made the contract opt-in, so the default was no contract at
all. Its verification counted components on the node's world mesh, composing
operations owned by enclosing assemblies; those carry the animated `$t`
expression, so the check raised a type error for every leaf any assembly
animates. Connected-component count is invariant under rigid transform, so the
composition could never have changed the answer it broke.

**Migration**: Delete every `bodies` declaration; there is no replacement
attribute and its presence is not an error the framework reports. `FusionNode`
no longer declares `bodies = 1`. The guarantee it expressed is now
unconditional and structural: see "Every topmost rigid node is one connected
body" in `build-pipeline`. A part that genuinely comprises several separated
pieces SHALL be expressed as separate solids under an `AssemblyNode`, not as
one solid with a declared count.
