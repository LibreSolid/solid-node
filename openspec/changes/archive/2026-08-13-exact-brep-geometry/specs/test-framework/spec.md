## MODIFIED Requirements

### Requirement: Mesh assertions

The system SHALL provide assertions operating on world-space geometry, each
raising `AssertionError` naming the offending nodes (with quantitative
measurements where one is computed, e.g. intersection volume):
`assertNotIntersecting`, `assertIntersecting`, `assertInside`,
`assertClose(max_distance)`, `assertFar(min_distance)`,
`assertIntersectVolumeAbove(min_volume)`, and
`assertIntersectVolumeBelow(max_volume)`. Standard `unittest` assertions
remain available.

Every assertion whose question is the VOLUME of an intersection SHALL obtain
that volume from the one shared evaluation helper, so no two assertions can
disagree about the same pair. This includes
`assertIntersectVolumeAbove` and `assertIntersectVolumeBelow`, which SHALL NOT
compute a separate trimesh intersection of their own.

`assertInside`, `assertClose` and `assertFar` are distance and containment
questions rather than volume questions. They SHALL continue to sample one
node's mesh vertices against the other's mesh surface, unchanged, whether or
not the nodes are exact.

#### Scenario: Intersection detected

- **WHEN** `assertNotIntersecting(a, b)` is called and the parts overlap
- **THEN** an `AssertionError` reports the node names and intersection volume

#### Scenario: Volume assertions agree with emptiness assertions

- **WHEN** `assertNotIntersecting` and `assertIntersectVolumeBelow` are called
  on the same pair in the same test
- **THEN** both read the same measured volume from the shared helper and
  cannot reach contradictory verdicts

#### Scenario: Distance assertions are unaffected by exactness

- **WHEN** `assertClose` or `assertFar` is called on two exact nodes
- **THEN** it measures mesh vertices against a mesh surface exactly as it does
  for faceted nodes

### Requirement: Accelerated intersection evaluation

All intersection-volume assertions (`assertNotIntersecting`,
`assertIntersecting`, `assertIntersectVolumeAbove`,
`assertIntersectVolumeBelow`, the perturbation assertions, and the pairwise
sweep) SHALL route through one shared `(is_empty, volume)` helper.

The helper SHALL select its evaluation path from the compared nodes:

- When BOTH nodes are exact, it SHALL use the EXACT path: each node's
  `shape()` is placed by its composed matrix and the two are intersected by
  the boundary-representation kernel. The result is empty when it contains no
  solid — boundary contact between coincident faces yields no solid and is
  therefore exactly empty with zero volume — and otherwise its volume is the
  summed volume of the solids it contains. A kernel failure raises under the
  `exact-geometry` capability rather than falling back.
- Otherwise, when both nodes expose an `stl_file`, it SHALL use the faceted
  fast path, unchanged.
- Otherwise (e.g. test doubles implementing only `.mesh`) it falls back to a
  plain trimesh boolean over `.mesh` with identical verdict semantics.

The AABB broad-phase SHALL run ahead of every path: each part's local
bounding-box corners are transformed by its composed world matrix into a
conservative world AABB, and if the two boxes are disjoint the intersection is
reported as exactly empty without running any boolean. This is an
exact-negative shortcut that never changes a verdict, and it is what keeps the
exact path's cost proportional to interacting pairs.

The faceted fast path:

- caches one `manifold3d.Manifold` per `(stl_file, mtime)` (module-level,
  stale entries evicted on rebuild), built from the same cached base mesh
  the `mesh` property uses, with watertightness validated once at cache
  fill — a non-watertight STL raises a `ValueError` naming the file rather
  than failing inside the boolean engine;
- places the cached Manifolds with a lazy `transform()` and intersects them
  directly, reading `is_empty()` and `volume()` off the result with no
  conversion back to trimesh, reading `volume` only when non-empty.

Verdict semantics on the FACETED path SHALL be preserved exactly: `is_empty`
is the boolean engine's own emptiness — a non-empty result with exactly
0.0 mm³ volume (real flush contact) still counts as fouling at the strict
`volume_epsilon=0` default, and only a `volume_epsilon > 0` comparison may
treat it as clear (the volume-epsilon contract of ADR-025 depends on this;
folding zero volume into emptiness is explicitly rejected — ADR-029). On the
EXACT path that construction does not arise: flush contact produces no solid
and is genuinely empty, so there is no float-noise sliver for an epsilon to
absorb.

#### Scenario: Distant parts skip the boolean

- **WHEN** `assertNoPairwiseIntersections` sweeps an assembly where most
  leaf pairs are far apart
- **THEN** disjoint-box pairs are culled without any exact boolean and the
  verdicts are identical to the unculled computation

#### Scenario: Flush contact still strict

- **WHEN** two FACETED parts share a flush face producing a non-empty,
  zero-volume intersection and `volume_epsilon` is 0
- **THEN** the assertion reports a foul, forcing an explicit
  `volume_epsilon` opt-in

#### Scenario: Non-watertight part

- **WHEN** a faceted fast-path assertion touches an STL that is not watertight
- **THEN** it raises a `ValueError` naming that STL file

#### Scenario: An exact tight fit is not interference

- **WHEN** two exact solids meet on coincident cylindrical faces at zero
  nominal clearance, and one is rotated relative to the other
- **THEN** the exact intersection contains no solid, the helper reports empty
  with zero volume, and the facet phase of either part is irrelevant to the
  verdict

#### Scenario: A mixed pair uses the faceted path

- **WHEN** one compared node is exact and the other is not
- **THEN** the helper uses the faceted path and its verdict semantics are
  those of that path

### Requirement: Perturbation-based fit assertions

The system SHALL provide `assertBlockedBeyond(node, magnitude, against, ...)`
and `assertFreeWithin(...)` (same signature), which temporarily inject one
perturbation operation into `node.operations` immediately before the node's
first pre-existing `Translation` (appended if none), measure fouling against
`against` through the shared intersection helper in world coordinates, and
ALWAYS remove the injected operation in a `finally` — `node.operations` is
left exactly as found. Two mutually exclusive modes: rotational via `axis`
(default `(0,0,1)` when neither is given) and translational via `along` (a
local pre-placement direction, normalized to unit, magnitude in mm). Passing
both `axis` and `along`, a zero `along` vector, or a `directions` value other
than `'both'`/`'forward'` SHALL raise `ValueError`. `directions='both'`
(default) checks both signs; `'forward'` only the positive.
`assertFreeWithin` accepts a list of magnitudes to sweep. `volume_epsilon`
(mm³, default 0.0 = exact emptiness) counts an intersection as fouling only
when `abs(volume) > volume_epsilon`, filtering flush-contact boolean noise.

`volume_epsilon` applies only where flush-contact noise can arise, which is
the faceted path. When a comparison routes exact, the assertion SHALL ignore
`volume_epsilon` and apply the strict verdict. When `volume_epsilon` was
supplied and EVERY comparison the call performed routed exact, the assertion
SHALL emit a warning naming the assertion, so a test does not silently keep
recording a tolerance it no longer applies. When any comparison routed
faceted, the epsilon remains live for those comparisons and no warning is
emitted.

Fit SHALL be certified by the paired contract — Blocked beyond the play
limit AND Free within it; `assertBlockedBeyond` alone is insufficient
(anti-gaming, ADR-025).

#### Scenario: Keyed shaft fit

- **WHEN** a test asserts `assertFreeWithin(gear, 1.5, shaft,
  volume_epsilon=1e-6)` and `assertBlockedBeyond(gear, 3, shaft,
  volume_epsilon=1e-6)`
- **THEN** the pair passes only if the gear rotates freely within 1.5° of
  play and fouls the key beyond 3° in both directions

#### Scenario: Operations restored on failure

- **WHEN** a perturbation assertion raises
- **THEN** the injected operation has already been removed and
  `node.operations` is unchanged

#### Scenario: Translational mode

- **WHEN** `assertBlockedBeyond(pin, 2.0, housing, along=[0, 0, 1])` runs on
  a pin whose placement rotates it onto a bank
- **THEN** the perturbation translates the pin 2 mm along its local axis as
  carried by the placement rotations, not the world Z axis

#### Scenario: An epsilon with nothing to absorb is reported

- **WHEN** a perturbation assertion is given `volume_epsilon=1e-6` and both
  compared nodes are exact
- **THEN** the verdict is the strict one and a warning names the assertion
  whose epsilon was ignored

#### Scenario: An epsilon still applies to a faceted comparison

- **WHEN** a perturbation assertion is given `volume_epsilon` and the
  comparison routes faceted
- **THEN** the epsilon filters the verdict as before and no warning is emitted

### Requirement: Whole-assembly solid interference assertion

The system SHALL provide `TestCase.assertNoSolidInterference(node)` as an
ordinary project assertion. Starting at `node`, it SHALL descend through
non-rigid nodes, select the first rigid node on each branch, and stop below each
selected node. These topmost rigid nodes are the printed solids whose assembled
world-space geometry SHALL be evaluated at the testing instant already set by
the runner. Rigid descendants inside a selected fusion SHALL NOT be evaluated
as separate assembly parts.

The assertion SHALL pass without geometric work when selection contains zero
or one solid. With multiple solids, a spatial index over conservative world
bounds SHALL be the sole verification path: it emits every potentially
interacting solid pair without first materializing every pairwise combination,
and each emitted pair is evaluated by exact Boolean intersection of the two
solids placed by their composed world transforms. A pair of exact solids SHALL
be evaluated by the boundary-representation kernel; any other pair SHALL be
evaluated by the cached Manifolds as before. The assertion SHALL NOT compute an
aggregate volume, Boolean union, or other whole-assembly measurement of the
selected solids.

Positive-volume overlap SHALL fail. Empty intersection and non-empty
zero-volume boundary contact SHALL pass. The assertion SHALL expose no overlap
epsilon and SHALL apply no numerical tolerance of its own: every positive
intersection volume reported by the kernel is interference.

When an offending candidate is found, the assertion SHALL raise
`AssertionError` naming both topmost rigid solids and their measured
intersection volume. The framework SHALL run the assertion only when ordinary
project test code calls it; builders and non-test commands SHALL NOT invoke it.

#### Scenario: A leaf project passes throughout early evolution

- **WHEN** `assertNoSolidInterference(self.node)` is called on a leaf root or a
  fusion root containing only one topmost rigid solid
- **THEN** the assertion passes without performing any candidate intersection

#### Scenario: Nested fusion ingredients are not assembly parts

- **WHEN** an assembly contains a fusion whose rigid ingredients overlap as
  part of forming that one printed solid
- **THEN** only the outer fusion is selected on that branch and its ingredients
  are not compared with one another

#### Scenario: Positive-volume assembly interference fails diagnostically

- **WHEN** two topmost rigid solids overlap by positive volume at the current
  testing instant
- **THEN** the assertion fails naming those solids and their intersection
  volume

#### Scenario: Exact boundary contact is not material interference

- **WHEN** two topmost rigid solids meet only on a boundary and the kernel
  reports zero shared volume
- **THEN** the assertion passes that candidate without requiring a public
  epsilon

#### Scenario: Numerical uncertainty receives further verification

- **WHEN** a candidate pair's exact intersection is non-empty with a volume
  small enough to be indistinguishable from floating-point noise
- **THEN** the assertion fails on that candidate, applying no tolerance of its
  own that could turn numerical slack into permitted overlap

#### Scenario: No whole-assembly measurement is computed

- **WHEN** the assertion evaluates two or more topmost rigid solids
- **THEN** it performs no Boolean union, aggregate volume, or other
  whole-assembly measurement, and reaches its verdict from the spatial index's
  candidate pairs alone

#### Scenario: Overlap hidden from a global volume comparison still fails

- **WHEN** three or more topmost rigid solids share material, or one solid lies
  wholly inside another
- **THEN** the assertion fails naming an offending pair, established from that
  pair's own exact intersection rather than from any assembly-wide measurement

#### Scenario: Current keyframe controls assembled placement

- **WHEN** the assertion is run under two testing instants that place the same
  selected solids first apart and then overlapping
- **THEN** the first instant passes and the second fails without the assertion
  accepting or setting a keyframe argument itself

#### Scenario: Sparse assembly avoids exhaustive pair construction

- **WHEN** most selected solids have disjoint world bounds
- **THEN** the spatial index emits only bounds-overlapping candidates and the
  assertion does not construct all `N * (N - 1) / 2` pairs

#### Scenario: Assembly cost tracks interacting pairs, not total geometry

- **WHEN** the selected solids are numerous and detailed but pairwise separated
- **THEN** the assertion performs no work proportional to the assembly's total
  triangle count beyond building one conservative world bound per solid

#### Scenario: An exact assembly is verified exactly

- **WHEN** every selected solid in the assembly is exact
- **THEN** each candidate pair is evaluated by the boundary-representation
  kernel, and a nominally exact fit between two of them does not register as
  interference

#### Scenario: A mixed assembly verifies each pair by what it has

- **WHEN** some selected solids are exact and others are not
- **THEN** pairs of exact solids are evaluated exactly, pairs involving a
  faceted solid are evaluated by the cached Manifolds, and one assertion
  reports over both

### Requirement: Pairwise adjacency sweep

The system SHALL retain the deprecated
`assertNoPairwiseIntersections(node, volume_epsilon=0.0)` compatibility API.
It SHALL preserve its historical behavior of walking the assembled tree to
its leaves, checking every leaf pair, and using `volume_epsilon` to filter
flush-contact noise on faceted comparisons. As with the perturbation
assertions, `volume_epsilon` SHALL be ignored for a pair that routes exact,
and a warning SHALL be emitted when an epsilon was supplied and every pair the
sweep evaluated routed exact. Each call SHALL emit a standard deprecation
warning that points to `assertNoSolidInterference` and explains that the
replacement checks topmost rigid solids without a public overlap epsilon.
Current documentation SHALL NOT recommend the deprecated sweep for new tests.

#### Scenario: Existing caller keeps its historical verdict

- **WHEN** an existing project calls the deprecated sweep on an assembly where
  two faceted leaves overlap by more than its supplied epsilon
- **THEN** an `AssertionError` still names the offending leaf pair

#### Scenario: Caller receives migration guidance

- **WHEN** a test invokes `assertNoPairwiseIntersections`
- **THEN** an explicitly captured deprecation warning points to
  `assertNoSolidInterference` and states the topmost-rigid scope difference

#### Scenario: An all-exact sweep reports its ignored epsilon

- **WHEN** the deprecated sweep is given an epsilon and every leaf pair it
  evaluates is exact
- **THEN** the epsilon is ignored and a warning says so, alongside the
  deprecation warning

### Requirement: Explicit whole-solid connectivity assertion

The system SHALL provide `assertNoDisconnectedSolids(node)` as an ordinary
`TestCase` assertion.

Starting from `node`, the assertion SHALL descend through non-rigid nodes and
SHALL stop at the first rigid node on each branch, so each selected node is one
printed solid. For an exact solid the assertion SHALL count the solids in that
node's exact geometry and require exactly one. For a solid that is not exact it
SHALL read that node's own built STL, split it without filtering to watertight
components, and require exactly one connected component. A rigid node passed
directly SHALL be its own only selected solid, and rigid ingredients inside a
selected solid SHALL NOT be checked independently.

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
  selected solid is one body
- **THEN** it passes as one ordinary counted test

#### Scenario: A declared integrity test fails

- **WHEN** a test method calls the assertion and a selected solid has three
  bodies
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
- **THEN** it reads that solid's own unplaced geometry, resolves no operation
  value, and reaches the same verdict at every animation instant

#### Scenario: Pieces inside a solid are permitted

- **WHEN** a `FusionNode` joins ingredients that are each several separated
  solids, and the fused solid is one body
- **THEN** the fusion passes and its ingredients are not checked independently

#### Scenario: The assertion is scoped to the node it is given

- **WHEN** the assertion is called on one subassembly of a larger model
- **THEN** only the solids within that subtree are selected and checked

#### Scenario: An exact solid is counted exactly

- **WHEN** the assertion runs on an exact solid whose geometry comprises two
  disjoint solids
- **THEN** it fails naming that solid and two bodies, established from the
  exact geometry rather than from a mesh split

### Requirement: Connectivity assertions

The system SHALL provide two connectivity assertions:

- `assertJoined(node1, node2, min_weld_volume=0.0)` — the two nodes are
  exactly one body, so the two features are genuinely the same printed part.
  For two exact nodes this SHALL be established by fusing their shapes and
  requiring the fuse to yield exactly one solid; otherwise by requiring the
  union of their meshes to be exactly one connected component.
  `min_weld_volume` (mm³) additionally requires the volume they share to reach
  that value. Solids that only touch tangentially SHALL NOT count as joined.

- `assertNoDisconnectedSolids(node)` — every printed solid in the selected
  subtree is one connected body, specified above.

Neither SHALL be invoked by the framework; both run only when project test code
calls them.

`assertOneBody`, `assertBodyCount` and `assertNoDisconnectedParts` SHALL NOT be
provided. `assertBodyCount` expressed the removed `bodies` declaration's
mistake that a solid may legitimately be several disconnected pieces, and
`assertNoDisconnectedParts` swept leaves, holding a leaf to a contract that
belongs to the solid enclosing it.

On the mesh path, components SHALL be counted by splitting the union without
filtering to watertight components — a fragment that is itself closed still
counts as a body. Watertightness SHALL NOT be treated as evidence of
connectedness: a mesh of several disjoint closed shells is watertight, has
positive volume, and exports a valid STL.

Connectivity is a property of geometry inside one solid, so `assertJoined`
SHALL place both nodes in the frame of their nearest enclosing rigid node,
composing operations up to that node and no further, on either path. It SHALL
NOT compose operations at or above the topmost rigid node, which are placement
of a whole body and cannot change whether two features within it meet.
Collision assertions are unaffected and continue to operate on world-space
geometry, because whether two separately placed parts clash is a world-framed,
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
- **THEN** the assertion fails, because they are still two bodies

#### Scenario: A weld below the stated minimum

- **WHEN** two features overlap, but by less than `min_weld_volume`
- **THEN** the assertion fails naming the weld volume and the required one

#### Scenario: A one-body solid whose named pair is not joined

- **WHEN** `assertJoined` runs on two features of a fusion that is itself a
  single connected body, but which reach each other only through a third
  feature
- **THEN** the assertion fails, because those two alone are two bodies

#### Scenario: An animated part is asserted like a static one

- **WHEN** `assertJoined` runs on two features inside a solid whose enclosing
  assembly drives its placement
- **THEN** the assertion composes only the operations inside that solid and
  reaches the same verdict at every animation instant

#### Scenario: The removed assertions are gone

- **WHEN** a test calls `assertOneBody`, `assertBodyCount` or
  `assertNoDisconnectedParts`
- **THEN** the attribute does not exist on the test case

#### Scenario: Two exact features are joined by their fuse

- **WHEN** `assertJoined` runs on two overlapping exact features of one solid
- **THEN** the verdict comes from fusing their shapes and finding one solid,
  and the weld volume from their exact intersection
