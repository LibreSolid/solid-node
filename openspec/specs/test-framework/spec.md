# Test Framework Specification

## Purpose

Test-driven CAD: how node tests are declared and run, the trimesh-based mesh
assertions, the connectivity assertions, the perturbation-based kinematic fit
assertions, and the animation-instant decorators. Encodes ADR-009 (trimesh mesh assertions),
ADR-010 (TestCaseMixin embedded tests), ADR-011 (animation testing
decorators), ADR-025 (perturbation-based kinematic fit assertions), and
ADR-029 (Manifold cache and AABB broad-phase for intersection assertions).

Code: `solid_node/test.py`, `solid_node/manager/test.py`. The framework's own
regression net is `tests/test_meta.py` over fixtures in `tests/meta_project/`
(paired green/red contracts run through `solid test` end-to-end).

## Requirements

### Requirement: Test declaration and binding

The system SHALL support two test styles run by the same command: a companion
`TestCase` file (package node `root/__init__.py` → `root/test.py`; module
node `gear.py` → `test_gear.py`), and tests embedded on the node via
`TestCaseMixin`. A companion `TestCase` receives the built node as
`self.node` and as a snake_case alias derived from the test class name with
the `Test` suffix stripped (e.g. `SimpleClockTest` → `self.simple_clock`).

#### Scenario: Companion test binding

- **WHEN** `solid test` runs a `GearTest(TestCase)` next to `gear.py`
- **THEN** test methods can reference the node as both `self.node` and
  `self.gear`

### Requirement: Test runner lifecycle

The system SHALL build the node before testing (load, `set_keyframe(0)`,
render, assemble, `build_stls`), then run all `test_`-prefixed methods found
on both the node and the companion test case. The build SHALL hold the project
build lock and SHALL release it before the first test method runs, so a test
sweep never blocks another build of the same project. Each method runs once per
declared testing instant (default `[0]`), with the keyframe set per instant,
a colored pass/fail dot printed per instant, and each child's operations
checkpoint restored between instants and between tests. The run SHALL print
`Ran N tests in X seconds: P passed, F failed` and exit 1 if any failed;
`--failfast` stops at the first failure.

#### Scenario: Failing contract fails the run

- **WHEN** any assertion raises across any instant
- **THEN** the summary counts the failure and the process exits 1

#### Scenario: A test sweep does not block a rebuild

- **WHEN** a test run has finished building the node and is running test methods
- **THEN** another process can acquire the project build lock and rebuild the
  same project

### Requirement: Mesh assertions

The system SHALL provide trimesh-based assertions operating on world-space
meshes (`node.mesh`), each raising `AssertionError` naming the offending
nodes (with quantitative measurements where one is computed, e.g.
intersection volume): `assertNotIntersecting`, `assertIntersecting`,
`assertInside`, `assertClose(max_distance)`, `assertFar(min_distance)`,
`assertIntersectVolumeAbove(min_volume)`, and
`assertIntersectVolumeBelow(max_volume)`. Standard `unittest` assertions
remain available.

#### Scenario: Intersection detected

- **WHEN** `assertNotIntersecting(a, b)` is called and the parts overlap
- **THEN** an `AssertionError` reports the node names and intersection volume

### Requirement: Perturbation-based fit assertions

The system SHALL provide `assertBlockedBeyond(node, magnitude, against, ...)`
and `assertFreeWithin(...)` (same signature), which temporarily inject one
perturbation operation into `node.operations` immediately before the node's
first pre-existing `Translation` (appended if none), measure fouling against
`against` via trimesh boolean intersection in world coordinates, and ALWAYS
remove the injected operation in a `finally` — `node.operations` is left
exactly as found. Two mutually exclusive modes: rotational via `axis`
(default `(0,0,1)` when neither is given) and translational via `along` (a
local pre-placement direction, normalized to unit, magnitude in mm). Passing
both `axis` and `along`, a zero `along` vector, or a `directions` value other
than `'both'`/`'forward'` SHALL raise `ValueError`. `directions='both'`
(default) checks both signs; `'forward'` only the positive.
`assertFreeWithin` accepts a list of magnitudes to sweep. `volume_epsilon`
(mm³, default 0.0 = exact emptiness) counts an intersection as fouling only
when `abs(volume) > volume_epsilon`, filtering flush-contact boolean noise.

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

### Requirement: Accelerated intersection evaluation

All intersection-based assertions (`assertNotIntersecting`,
`assertIntersecting`, the perturbation assertions, and the pairwise sweep)
SHALL route through one shared `(is_empty, volume)` helper. When both nodes
expose an `stl_file`, it SHALL use a fast path; otherwise (e.g. test doubles
implementing only `.mesh`) it falls back to a plain trimesh boolean over
`.mesh` with identical verdict semantics. The fast path:

- caches one `manifold3d.Manifold` per `(stl_file, mtime)` (module-level,
  stale entries evicted on rebuild), built from the same cached base mesh
  the `mesh` property uses, with watertightness validated once at cache
  fill — a non-watertight STL raises a `ValueError` naming the file rather
  than failing inside the boolean engine;
- runs an AABB broad-phase first: each part's local bounding-box corners are
  transformed by its composed world matrix into a conservative world AABB,
  and if the two boxes are disjoint the intersection is reported as exactly
  empty without running a boolean (an exact-negative shortcut that never
  changes a verdict);
- otherwise places the cached Manifolds with a lazy `transform()` and
  intersects them directly, reading `is_empty()` and `volume()` off the
  result with no conversion back to trimesh, reading `volume` only when
  non-empty.

Verdict semantics SHALL be preserved exactly: `is_empty` is the boolean
engine's own emptiness — a non-empty result with exactly 0.0 mm³ volume
(real flush contact) still counts as fouling at the strict
`volume_epsilon=0` default, and only a `volume_epsilon > 0` comparison may
treat it as clear (the volume-epsilon contract of ADR-025 depends on this;
folding zero volume into emptiness is explicitly rejected — ADR-029).

#### Scenario: Distant parts skip the boolean

- **WHEN** `assertNoPairwiseIntersections` sweeps an assembly where most
  leaf pairs are far apart
- **THEN** disjoint-box pairs are culled without any exact boolean and the
  verdicts are identical to the unculled computation

#### Scenario: Flush contact still strict

- **WHEN** two parts share a flush face producing a non-empty,
  zero-volume intersection and `volume_epsilon` is 0
- **THEN** the assertion reports a foul, forcing an explicit
  `volume_epsilon` opt-in

#### Scenario: Non-watertight part

- **WHEN** a fast-path assertion touches an STL that is not watertight
- **THEN** it raises a `ValueError` naming that STL file

### Requirement: Pairwise adjacency sweep

The system SHALL provide `assertNoPairwiseIntersections(node,
volume_epsilon=0.0)`, walking the assembled tree to its leaves and asserting
every leaf pair non-intersecting, with `volume_epsilon` filtering
flush-contact noise.

#### Scenario: Assembly-wide clearance

- **WHEN** the sweep runs on an assembly where two leaves overlap by more
  than the epsilon
- **THEN** an `AssertionError` names the offending pair

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

### Requirement: Animation-instant decorators

The system SHALL provide `@testing_instant(instant)` and
`@testing_steps(steps, start=0, end=1)` setting `testing_instants` on a test
method; the runner executes the method once per instant with the keyframe
set. `testing_steps` requires `steps >= 2` and forces the final instant to
exactly `end`.

#### Scenario: Sweeping a rotation

- **WHEN** a method is decorated `@testing_steps(10)`
- **THEN** it runs at 10 evenly spaced instants from 0 to 1 inclusive
