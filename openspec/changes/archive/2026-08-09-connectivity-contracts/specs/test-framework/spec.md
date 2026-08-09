## ADDED Requirements

### Requirement: Connectivity assertions

The system SHALL provide assertions over the number of connected solids in a
node's world-space mesh, counted by splitting the mesh without filtering to
watertight components — a fragment that is itself closed still counts as a
body. Watertightness SHALL NOT be treated as evidence of connectedness: a mesh
of several disjoint closed shells is watertight, has positive volume, and
exports a valid STL.

- `assertOneBody(node)` — the node is a single connected solid.
- `assertBodyCount(node, expected)` — the node has exactly `expected`
  connected components; the failure names the node, the expected count, and
  the actual one.
- `assertJoined(node1, node2, min_weld_volume=0.0)` — the union of the two
  nodes' meshes is exactly one connected component, so the two features are
  genuinely the same printed part. `min_weld_volume` (mm³) additionally
  requires the volume they share to reach that value. Solids that only touch
  tangentially SHALL NOT count as joined.
- `assertNoDisconnectedParts(node)` — the connectivity counterpart of the
  pairwise adjacency sweep: it walks the assembled tree to its leaves and
  holds every leaf to the count its `bodies` attribute declares, defaulting
  to one body when it declares none.

#### Scenario: A part in pieces is caught

- **WHEN** `assertOneBody` runs on a node whose features never reached each
  other, producing a watertight mesh of several closed shells
- **THEN** an `AssertionError` names the node and the number of bodies its
  mesh has

#### Scenario: Tangential contact is not a join

- **WHEN** `assertJoined` runs on two solids that meet exactly on a face
  without overlapping
- **THEN** the assertion fails, because their union is still two components

#### Scenario: A weld below the stated minimum

- **WHEN** two features overlap, but by less than `min_weld_volume`
- **THEN** the assertion fails naming the weld volume and the required one

#### Scenario: Assembly-wide connectivity

- **WHEN** `assertNoDisconnectedParts` sweeps an assembly in which one leaf
  anywhere in the tree has fallen into fragments
- **THEN** an `AssertionError` names that leaf

#### Scenario: A leaf that is deliberately several bodies

- **WHEN** a leaf declares `bodies = 2` and its mesh has two components
- **THEN** the sweep passes for that leaf, and fails it if the mesh has any
  other number
