# Test Framework Specification

## Purpose

Test-driven CAD: how node tests are declared and run, the trimesh-based mesh
assertions, the perturbation-based kinematic fit assertions, and the
animation-instant decorators. Encodes ADR-009 (trimesh mesh assertions),
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
on both the node and the companion test case. Each method runs once per
declared testing instant (default `[0]`), with the keyframe set per instant,
a colored pass/fail dot printed per instant, and each child's operations
checkpoint restored between instants and between tests. The run SHALL print
`Ran N tests in X seconds: P passed, F failed` and exit 1 if any failed;
`--failfast` stops at the first failure.

#### Scenario: Failing contract fails the run

- **WHEN** any assertion raises across any instant
- **THEN** the summary counts the failure and the process exits 1

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

### Requirement: Animation-instant decorators

The system SHALL provide `@testing_instant(instant)` and
`@testing_steps(steps, start=0, end=1)` setting `testing_instants` on a test
method; the runner executes the method once per instant with the keyframe
set. `testing_steps` requires `steps >= 2` and forces the final instant to
exactly `end`.

#### Scenario: Sweeping a rotation

- **WHEN** a method is decorated `@testing_steps(10)`
- **THEN** it runs at 10 evenly spaced instants from 0 to 1 inclusive
