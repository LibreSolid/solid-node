## MODIFIED Requirements

### Requirement: Connectivity assertions

The system SHALL provide one connectivity assertion, over a pair of named
nodes:

- `assertJoined(node1, node2, min_weld_volume=0.0)` — the union of the two
  nodes' meshes is exactly one connected component, so the two features are
  genuinely the same printed part. `min_weld_volume` (mm³) additionally
  requires the volume they share to reach that value. Solids that only touch
  tangentially SHALL NOT count as joined.

`assertOneBody`, `assertBodyCount` and `assertNoDisconnectedParts` SHALL NOT be
provided. The build guarantees unconditionally that every topmost rigid node is
one connected body, so they assert a state a project can no longer reach;
`assertBodyCount` additionally expressed the removed `bodies` declaration's
mistake that a solid may legitimately be several disconnected pieces, and
`assertNoDisconnectedParts` swept leaves, holding a leaf to a contract that
belongs to the solid enclosing it.

Components SHALL be counted by splitting the union without filtering to
watertight components — a fragment that is itself closed still counts as a
body. Watertightness SHALL NOT be treated as evidence of connectedness: a mesh
of several disjoint closed shells is watertight, has positive volume, and
exports a valid STL.

Connectivity is a property of geometry inside one solid, so `assertJoined`
SHALL place both nodes in the frame of their nearest enclosing rigid node,
composing operations up to that node and no further. It SHALL NOT compose
operations at or above the topmost rigid node, which are placement of a whole
body and cannot change whether two features within it meet. Collision
assertions are unaffected and continue to operate on world-space meshes,
because whether two separately placed parts clash is a world-framed,
time-dependent question.

`assertJoined` remains necessary alongside the build's guarantee: a solid can
be one connected component while the two features the designer cared about
never reach each other, joined only by a detour through others; and no body
count can express a required weld volume.

#### Scenario: Tangential contact is not a join

- **WHEN** `assertJoined` runs on two solids that meet exactly on a face
  without overlapping
- **THEN** the assertion fails, because their union is still two components

#### Scenario: A weld below the stated minimum

- **WHEN** two features overlap, but by less than `min_weld_volume`
- **THEN** the assertion fails naming the weld volume and the required one

#### Scenario: A one-body solid whose named pair is not joined

- **WHEN** `assertJoined` runs on two features of a fusion that is itself a
  single connected body, but which reach each other only through a third
  feature
- **THEN** the assertion fails, because the union of those two alone has two
  components

#### Scenario: An animated part is asserted like a static one

- **WHEN** `assertJoined` runs on two features inside a solid whose enclosing
  assembly drives its placement
- **THEN** the assertion composes only the operations inside that solid and
  reaches the same verdict at every animation instant

#### Scenario: The removed assertions are gone

- **WHEN** a test calls `assertOneBody`, `assertBodyCount` or
  `assertNoDisconnectedParts`
- **THEN** the attribute does not exist on the test case
