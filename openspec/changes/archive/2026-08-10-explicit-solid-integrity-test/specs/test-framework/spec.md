## ADDED Requirements

### Requirement: Explicit whole-solid connectivity assertion

The system SHALL provide `assertNoDisconnectedSolids(node)` as an ordinary
`TestCase` assertion.

Starting from `node`, the assertion SHALL descend through non-rigid nodes and
SHALL stop at the first rigid node on each branch, so each selected node is one
printed solid. The assertion SHALL read that node's own built STL, split it
without filtering to watertight components, and require exactly one connected
component. A rigid node passed directly SHALL be its own only selected solid,
and rigid ingredients inside a selected solid SHALL NOT be checked
independently.

The assertion SHALL NOT compose node or ancestor operations and SHALL NOT read
a world-framed mesh. Connected-component count is invariant under rigid
placement, so assembly placement, animation instant, and unresolved `$t`
expressions SHALL have no effect on its verdict.

On violation the assertion SHALL raise `AssertionError` naming the solid and
the number of bodies found, and MAY fail at the first disconnected solid.

The framework SHALL execute this assertion only when project test code calls
it. The test runner, builder, node base classes, and scaffold SHALL NOT
register, schedule, or invoke it automatically, and no declaration attribute,
mixin, decorator, or registry SHALL cause it to run.

#### Scenario: A declared integrity test passes

- **WHEN** a test method calls `assertNoDisconnectedSolids(self.node)` and every
  selected solid's STL has one connected component
- **THEN** it passes as one ordinary counted test

#### Scenario: A declared integrity test fails

- **WHEN** a test method calls the assertion and a selected solid's STL has
  three components
- **THEN** the test fails with an `AssertionError` naming that solid and the
  three bodies, and the run's summary counts the failure

#### Scenario: An undeclared contract does not run

- **WHEN** a project whose geometry is disconnected declares no test calling
  `assertNoDisconnectedSolids`
- **THEN** `solid test` adds no integrity test to its count and reports no
  connectivity failure

#### Scenario: An animated solid is asserted like a static one

- **WHEN** the assertion runs over an assembly that drives a selected solid's
  placement with an operation holding `$t`
- **THEN** it reads that solid's STL directly, resolves no operation value, and
  reaches the same verdict at every animation instant

#### Scenario: Pieces inside a solid are permitted

- **WHEN** a `FusionNode` joins ingredients that are each several separated
  solids, and the fused STL is one connected body
- **THEN** the fusion passes and its ingredients are not checked independently

#### Scenario: The assertion is scoped to the node it is given

- **WHEN** the assertion is called on one subassembly of a larger model
- **THEN** only the solids within that subtree are selected and checked

## MODIFIED Requirements

### Requirement: Connectivity assertions

The system SHALL provide two connectivity assertions:

- `assertJoined(node1, node2, min_weld_volume=0.0)` — the union of the two
  nodes' meshes is exactly one connected component, so the two features are
  genuinely the same printed part. `min_weld_volume` (mm³) additionally
  requires the volume they share to reach that value. Solids that only touch
  tangentially SHALL NOT count as joined.
- `assertNoDisconnectedSolids(node)` — every printed solid in the selected
  subtree is one connected body, specified above.

Neither SHALL be invoked by the framework; both run only when project test code
calls them.

`assertOneBody`, `assertBodyCount` and `assertNoDisconnectedParts` SHALL NOT be
provided. `assertBodyCount` expressed the removed `bodies` declaration's
mistake that a solid may legitimately be several disconnected pieces, and
`assertNoDisconnectedParts` swept leaves, holding a leaf to a contract that
belongs to the solid enclosing it.

Components SHALL be counted by splitting without filtering to watertight
components — a fragment that is itself closed still counts as a body.
Watertightness SHALL NOT be treated as evidence of connectedness: a mesh of
several disjoint closed shells is watertight, has positive volume, and exports
a valid STL.

Connectivity is a property of geometry inside one solid, so `assertJoined`
SHALL place both nodes in the frame of their nearest enclosing rigid node,
composing operations up to that node and no further. It SHALL NOT compose
operations at or above the topmost rigid node, which are placement of a whole
body and cannot change whether two features within it meet. Collision
assertions are unaffected and continue to operate on world-space meshes,
because whether two separately placed parts clash is a world-framed,
time-dependent question.

Both nodes SHALL belong to the same solid. When two assembled nodes resolve to
different topmost rigid ancestors, `assertJoined` SHALL fail naming both nodes
and both solids, rather than comparing them: each would be placed at its own
part's origin, discarding the distance the assembly holds between the parts and
reporting two features that share nothing as welded. A node not linked into a
tree SHALL NOT be treated as evidence of a second solid, so plain mesh geometry
remains comparable.

The two assertions answer different questions and neither implies the other. A
solid can be one connected component while the two features the designer cared
about reach each other only by a detour through others; and no body count can
express a required weld volume.

#### Scenario: Features of two different parts are refused

- **WHEN** `assertJoined` runs on two nodes whose enclosing solids differ,
  however far apart the assembly holds those solids
- **THEN** the assertion fails naming both nodes and both solids, and no
  geometric comparison is made

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
