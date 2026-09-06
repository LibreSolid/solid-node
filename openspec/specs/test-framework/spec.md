# Test Framework Specification

## Purpose

Test-driven CAD: how node tests are declared and run, the trimesh-based mesh
assertions, the connectivity assertions, the perturbation-based kinematic fit
assertions, and the animation-instant decorators. Encodes ADR-009 (trimesh mesh assertions),
ADR-010 (TestCaseMixin embedded tests), ADR-011 (animation testing
decorators), ADR-025 (perturbation-based kinematic fit assertions), and
ADR-029 (Manifold cache and AABB broad-phase for intersection assertions),
ADR-039 (topmost-rigid solid integrity), ADR-040 (topmost-rigid assembly
integrity certificate), and ADR-073 (the comparison kernel as a property of
the test run).

Code: `solid_node/test.py`, `solid_node/manager/test.py`. The framework's own
regression net is `tests/test_meta.py` over fixtures in `tests/meta_project/`
(paired green/red contracts run through `solid test` end-to-end).
## Requirements
### Requirement: Test declaration and binding

The system SHALL support two test styles run by the same command: companion
`TestCase` classes in a test file (package node `pkg/__init__.py` →
`pkg/test.py`; module node `gear.py` → `test_gear.py`), and tests embedded on
the node via `TestCaseMixin`.

The system SHALL load **every** `TestCase` defined in a companion file, never
only the first. A `TestCase` MAY declare the node it exercises with a
class-level `node = <NodeClass>` attribute. An undeclared `TestCase` SHALL bind
to the node module's single node class; when that module defines several node
classes, an undeclared `TestCase` SHALL fail the run with an error naming it and
listing the candidate node classes, and SHALL NOT be silently skipped.

A companion `TestCase` receives its bound node as `self.node` and as a
snake_case alias derived from the test class name with the `Test` suffix
stripped (e.g. `SimpleClockTest` → `self.simple_clock`).

#### Scenario: Companion test binding

- **WHEN** `solid test` runs a `GearTest(TestCase)` next to `gear.py`
- **THEN** test methods can reference the node as both `self.node` and
  `self.gear`

#### Scenario: Several test cases in one companion file

- **WHEN** a companion file defines `WindmillTest` and `SailTest`, each
  declaring its node
- **THEN** both run, each bound to the node it declares

#### Scenario: An undeclared test case cannot be bound

- **WHEN** a companion file defines a `TestCase` with no `node` declaration and
  its node module defines two node classes
- **THEN** the run fails with an error naming the test case and the candidate
  node classes

### Requirement: Test runner lifecycle

The system SHALL build each node under test before testing it (load,
`set_keyframe(0)`, render, assemble, `build_stls`), then run all
`test_`-prefixed methods found on the node and on every companion test case
bound to it. The build SHALL hold the project build lock and SHALL release it
before the first test method runs, so a test sweep never blocks another build of
the same project.

When the reference names a single node, the run covers that node and the test
cases bound to it. When the reference names a file, the run covers every node
class defined in that file and every test case in its companion. No test case in
a companion file SHALL be excluded from a run that covers its node.

Each method runs once per declared testing instant (default `[0]`), with the
keyframe set per instant, a colored pass/fail dot printed per instant, and each
child's operations checkpoint restored between instants and between tests. The
run SHALL print `Ran N tests in X seconds: P passed, F failed` and exit 1 if any
failed; `--failfast` stops at the first failure. Under the faceted comparison
kernel that summary line SHALL continue with ` (faceted kernel, volume epsilon
E mm³)`, and the run SHALL announce the kernel and epsilon on a line of its
own before the first node is built; under the exact kernel the run's output is
unchanged.

#### Scenario: Failing contract fails the run

- **WHEN** any assertion raises across any instant
- **THEN** the summary counts the failure and the process exits 1

#### Scenario: A test sweep does not block a rebuild

- **WHEN** a test run has finished building the node and is running test methods
- **THEN** another process can acquire the project build lock and rebuild the
  same project

#### Scenario: A file reference runs every node in the file

- **WHEN** a user runs `solid test windmill/model.py` on a file defining two
  node classes, each with a companion test case
- **THEN** both nodes are built and the test methods of both test cases are
  counted in the summary

#### Scenario: A faceted run is labelled as one

- **WHEN** `solid test --faceted --volume-epsilon 0.5` runs a project
- **THEN** a line before the first build names the faceted kernel and the
  epsilon, and the summary line ends with `(faceted kernel, volume epsilon
  0.5 mm³)`

#### Scenario: An exact run reads as it always did

- **WHEN** `solid test` runs without a kernel selection and without
  `SOLID_TEST_KERNEL` in the environment
- **THEN** no kernel line is printed and the summary line is exactly
  `Ran N tests in X seconds: P passed, F failed`

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
emitted. Under the faceted comparison kernel no comparison routes exact, so
`volume_epsilon` is live for every comparison and the warning never fires;
the run's own volume epsilon has already been applied to each verdict the
assertion reads, so the two compose as a floor and a filter.

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

#### Scenario: A faceted run keeps every epsilon live

- **WHEN** a perturbation assertion is given `volume_epsilon=1e-6` on two
  exact nodes and the run's kernel is faceted
- **THEN** the epsilon filters the faceted verdict and no warning is emitted

### Requirement: Accelerated intersection evaluation

All intersection-volume assertions (`assertNotIntersecting`,
`assertIntersecting`, `assertIntersectVolumeAbove`,
`assertIntersectVolumeBelow`, the perturbation assertions, and the pairwise
sweep) SHALL route through one shared `(is_empty, volume)` helper.

The helper SHALL select its evaluation path from the compared nodes and from
the run's comparison kernel:

- When the run's kernel is exact and BOTH nodes are exact, it SHALL use the
  EXACT path: each node's
  `shape()` is placed by its composed matrix and the two are intersected by
  the boundary-representation kernel. The result is empty when it contains no
  solid — boundary contact between coincident faces yields no solid and is
  therefore exactly empty with zero volume — and otherwise its volume is the
  summed volume of the solids it contains. A kernel failure raises under the
  `exact-geometry` capability rather than falling back.
- Otherwise, when both nodes expose an `stl_file`, it SHALL use the faceted
  fast path, unchanged. Under the faceted kernel this is the path every pair
  of built solids takes, exact or not: a node's `shape()` is never read, and
  the exact-geometry stack is not imported by the test framework.
- Otherwise (e.g. test doubles implementing only `.mesh`) it falls back to a
  plain trimesh boolean over `.mesh` with identical verdict semantics.

The AABB broad-phase SHALL run ahead of every path: each part's local
bounding-box corners are transformed by its composed world matrix into a
conservative world AABB, and if the two boxes are disjoint the intersection is
reported as exactly empty without running any boolean. This is an
exact-negative shortcut that never changes a verdict, and it is what keeps the
exact path's cost proportional to interacting pairs.

The per-STL cache SHALL be split by what each part of it needs:

- a solid's local bounding box is read from the same cached base mesh the
  `mesh` property uses, keyed by `(stl_file, mtime)` with stale entries
  evicted on rebuild, whenever a solid is selected. This half SHALL NOT
  require the mesh engine and SHALL NOT judge the mesh: selecting a solid,
  placing it in the broad phase, or comparing it on the exact kernel never
  raises for the state of its mesh;
- one `manifold3d.Manifold` per `(stl_file, mtime)` (module-level, stale
  entries evicted on rebuild) is built from that same cached base mesh at the
  FIRST comparison that actually reads it, and never for a solid whose every
  comparison is decided by the boundary-representation kernel. Repeated reads
  SHALL reuse the one cached Manifold, so deferring construction SHALL NOT
  increase the number of Manifolds built for any assembly. The mesh engine's
  own construction status is the admissibility verdict: a Manifold whose
  `status()` is not `NoError` SHALL raise a `ValueError` naming the STL file
  and the engine's status, with trimesh's watertightness verdict as a
  diagnostic, and SHALL NOT be cached; a mesh the engine accepts
  is compared whatever trimesh says of it. A flexible leaf's Manifold, built
  from its evaluated mesh at the current binding, is judged the same way and
  the error names the node.

The faceted fast path SHALL then place the cached Manifolds with a lazy
`transform()` and intersect them directly, reading `is_empty()` and `volume()`
off the result with no conversion back to trimesh, reading `volume` only when
non-empty.

Under the faceted kernel the helper SHALL apply the run's volume epsilon to
every verdict it returns, on either faceted path: a result whose volume does
not exceed the epsilon is reported as empty with zero volume. At the default
epsilon of 0.0 this changes nothing.

Verdict semantics on the FACETED path SHALL be preserved exactly: `is_empty`
is the boolean engine's own emptiness — a non-empty result with exactly
0.0 mm³ volume (real flush contact) still counts as fouling at the strict
`volume_epsilon=0` default, and only a `volume_epsilon > 0` comparison may
treat it as clear (the volume-epsilon contract of ADR-025 depends on this;
folding zero volume into emptiness is explicitly rejected — ADR-029). On the
EXACT path that construction does not arise: flush contact produces no solid
and is genuinely empty, so there is no float-noise sliver for an epsilon to
absorb.

The bounding boxes the broad phase transforms SHALL come from the cached base
mesh for every solid, exact or faceted. The candidate pairs a given assembly
emits SHALL NOT depend on whether its solids carry exact geometry.

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

- **WHEN** a faceted fast-path assertion reads an STL from which the mesh
  engine builds a Manifold whose status is not `NoError` (a box missing a
  triangle, say)
- **THEN** it raises a `ValueError` naming that STL file and the engine's
  status, and the Manifold is not cached

#### Scenario: A mesh trimesh doubts and the engine accepts

- **WHEN** a faceted fast-path assertion reads an STL whose edges are shared
  by four faces, so trimesh reports it non-watertight, and the mesh engine
  builds it with `NoError`
- **THEN** the assertion compares the part and reaches the engine's verdict,
  with no error

#### Scenario: An exact run never judges a mesh

- **WHEN** the run's kernel is exact, two exact solids are compared, and one
  of them has an STL the mesh engine would refuse
- **THEN** the verdict is the boundary-representation kernel's, no Manifold
  is built, and the STL's state raises nothing

#### Scenario: The broad phase does not judge a mesh

- **WHEN** `assertNoSolidInterference` selects a solid whose STL the mesh
  engine would refuse and no candidate pair compares it faceted
- **THEN** the sweep completes with the kernel's verdicts and the solid's
  bounding box culls its pairs as any other's does

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

#### Scenario: An exact assembly builds no Manifold

- **WHEN** `assertNoSolidInterference` verifies an assembly whose every selected
  solid is exact
- **THEN** no `manifold3d.Manifold` is constructed for any of those solids, and
  the verdict is the one the kernel reaches

#### Scenario: A mixed assembly builds a Manifold only for the solids it compares faceted

- **WHEN** an assembly's selected solids include exact and faceted parts and only
  some candidate pairs route faceted
- **THEN** a Manifold is built for each solid a faceted comparison reads, once
  each, and for no other solid

#### Scenario: A faceted run compares exact parts on their meshes

- **WHEN** the run's kernel is faceted and both compared nodes are exact
- **THEN** the helper uses the faceted fast path over the nodes' built STLs,
  reads neither node's `shape()`, and the verdict semantics are those of the
  faceted path

#### Scenario: The run's epsilon absorbs tessellation contact

- **WHEN** the run's kernel is faceted with a volume epsilon of 0.5 mm³ and
  two parts' meshes share 0.2 mm³ where their exact solids only touch
- **THEN** the helper reports the pair empty with zero volume, and
  `assertNotIntersecting` passes

#### Scenario: A real overlap survives the run's epsilon

- **WHEN** the run's kernel is faceted with a volume epsilon of 0.5 mm³ and
  two parts share 12 mm³
- **THEN** the helper reports the measured volume and the assertion fails as
  it does on the exact kernel

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
solids placed by their composed world transforms. Under the exact comparison
kernel a pair of exact solids SHALL be evaluated by the boundary-representation
kernel and any other pair by the cached Manifolds as before; under the faceted
kernel every pair SHALL be evaluated by the cached Manifolds and no solid's
exact geometry is read. The assertion SHALL NOT compute an
aggregate volume, Boolean union, or other whole-assembly measurement of the
selected solids.

Placing a solid for the spatial index SHALL NOT of itself construct that solid's
faceted representation. A solid's Manifold SHALL be built only when a candidate
pair it belongs to is actually evaluated by the mesh engine, so an assembly whose
every selected solid is exact SHALL require no mesh engine at all — see the
`mesh-engine-dependency` capability.

Positive-volume overlap SHALL fail. Empty intersection and non-empty
zero-volume boundary contact SHALL pass. The assertion SHALL expose no overlap
epsilon and SHALL apply no numerical tolerance of its own: every positive
intersection volume reported by the kernel is interference. Under the faceted
kernel the verdicts it reads have already had the run's volume epsilon
applied, like every other volume question in that run; the assertion adds
nothing to it.

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

#### Scenario: An exact assembly is verified without the mesh engine

- **WHEN** every selected solid in the assembly is exact and `manifold3d` cannot
  be imported
- **THEN** the assertion reaches the same verdict it reaches with the mesh
  engine installed

#### Scenario: A mixed assembly verifies each pair by what it has

- **WHEN** some selected solids are exact and others are not
- **THEN** pairs of exact solids are evaluated exactly, pairs involving a
  faceted solid are evaluated by the cached Manifolds, and one assertion
  reports over both

#### Scenario: A faceted run verifies an exact assembly on its meshes

- **WHEN** every selected solid is exact and the run's kernel is faceted
- **THEN** each candidate pair is evaluated by the cached Manifolds, no
  solid's `shape()` is read, and a pair whose meshes share no more than the
  run's volume epsilon passes

### Requirement: Whole-assembly gravity support assertion

The system SHALL provide
`TestCase.assertAssemblySupported(node, gravity=(0, 0, -1), max_drop=1.0, ground=None, supports=None, stability_margin=0.0)`
as an ordinary project assertion. Starting at `node`, it SHALL select topmost
rigid solids exactly as `assertNoSolidInterference` does, and SHALL evaluate
their assembled world-space geometry at the testing instant already set by the
runner. Selection of zero or one solid SHALL pass without geometric work.

The assertion SHALL prove that every selected solid is transitively supported
against gravity. A solid `A` is directly supported by a solid `B` when `A`,
displaced by `max_drop` along the normalized `gravity` vector in the world
frame, intersects `B` with positive volume; non-empty zero-volume boundary
contact after the displacement SHALL NOT count as support. The assertion SHALL
build the directed support graph of those relations, seed a grounded set, and
require every selected solid to reach the grounded set through support edges;
mutual-support cycles SHALL be grounded exactly when some member is
transitively supported by a grounded solid.

When support reachability holds, the assertion SHALL additionally prove
frictionless static equilibrium: there SHALL exist an assignment of
non-negative (push-only) normal contact forces over the detected contact
interfaces that simultaneously balances gravity's force and torque on every
non-anchored selected solid, decided by a deterministic linear feasibility
program. Contact interfaces SHALL be extracted from the displaced-intersection
geometry of detected contacts in both displacement directions: the drop
(`+max_drop` along gravity) and a lift (`−max_drop` against gravity), so
overhead restraints can complete force couples. Each interface's contact
points and outward normals SHALL lie on the undisplaced surface of the
supporting solid. Lift-detected contacts SHALL contribute contact interfaces
only; they SHALL NOT add support-graph edges. Contact extraction and mass
properties SHALL be evaluated on the placed faceted geometry at uniform
density; support-edge existence keeps its exact-kernel routing.

When `ground` is `None`, the grounded seeds SHALL be the selected solids whose
conservative world extent along gravity comes within `max_drop` of the
assembly's furthest extent along gravity, and the equilibrium phase SHALL
anchor only a virtual floor whose top plane lies at that furthest extent and
which spans the assembly laterally: default-seeded solids SHALL balance on
their detected floor contacts rather than being exempt. When `ground` is a
node or sequence of nodes, each SHALL be resolved to its selected topmost
rigid solid, those solids SHALL be the only seeds and the only anchored
bodies, no virtual floor SHALL exist, and a `ground` entry that resolves to no
selected solid SHALL raise an error rather than pass silently.

`supports`, when given, SHALL be an iterable of `(supported, supporter)` node
pairs, each resolved to selected topmost rigid solids, adding an explicit
support edge; an unresolvable pair SHALL raise an error. A declared edge SHALL
NOT ground a solid whose supporter is not itself transitively grounded. In the
equilibrium phase a declared edge SHALL transmit an unrestricted wrench —
force and torque in both signs — between its pair, exempting that hold from
frictionless statics while keeping the exemption visible in the test.

`stability_margin` (millimetres, default `0.0`) SHALL shrink each contact
interface toward its own centroid by the given distance before the
equilibrium decision, so a positive margin rejects balances that depend on
the boundary of a contact patch; at the default the check SHALL be pure
feasibility. A negative `stability_margin` SHALL raise an error.

A pair of exact solids SHALL be evaluated by the boundary-representation
kernel; any other pair SHALL be evaluated by the cached Manifolds placed by
composed world transforms with the displacement applied as a world-frame
translation. Only pairs whose conservative displaced-versus-placed world
bounds overlap SHALL be evaluated by Boolean intersection, in the drop and
lift sweeps alike. A zero `gravity` vector or a non-positive `max_drop` SHALL
raise an error.

On reachability failure the assertion SHALL raise `AssertionError` naming
every selected solid that is not transitively grounded, together with the
drop distance and gravity direction used. On equilibrium failure it SHALL
raise `AssertionError` naming every solid whose balance cannot be satisfied
and whether force or torque balance fails, and SHALL point at `supports` as
the declared-hold escape. A solid whose reachability rests on edges yielding
no extractable contact interface SHALL fail the equilibrium phase rather than
pass silently. The framework SHALL run the assertion only when ordinary
project test code calls it; builders and non-test commands SHALL NOT invoke
it. The assertion's documentation SHALL state its physical claims and
exclusions: support reachability, force balance, torque balance, and toppling
over detected contacts ARE claimed; friction, adhesion, purely lateral
(gravity-parallel) wall reactions, single-solid floor toppling, and all
dynamic effects are NOT.

#### Scenario: A single-solid project passes trivially

- **WHEN** `assertAssemblySupported(self.node)` is called on a leaf root or a
  fusion root containing only one topmost rigid solid
- **THEN** the assertion passes without performing any drop intersection

#### Scenario: A floating solid fails diagnostically

- **WHEN** a selected solid, displaced by `max_drop` along gravity, intersects
  no other selected solid and is not a grounded seed
- **THEN** the assertion fails naming that solid, the drop distance, and the
  gravity direction

#### Scenario: A balanced resting stack on the lowest solid passes

- **WHEN** solid `A` rests centred on solid `B`, `B` holds the assembly's
  furthest extent along gravity with `ground=None`, and each solid's weight
  is balanced by its detected contacts
- **THEN** `B` is a grounded seed, `A` is supported through its drop edge onto
  `B`, the equilibrium program is feasible, and the assertion passes

#### Scenario: Support through a floating supporter does not ground

- **WHEN** solid `A` rests on solid `B`, and `B` neither rests on anything nor
  is a grounded seed
- **THEN** the assertion fails naming every solid that is not transitively
  grounded

#### Scenario: A hanging solid held by balanced engagement passes

- **WHEN** a solid hangs below a grounded solid such that displacing it by
  `max_drop` along gravity makes the two intersect with positive volume, and
  the engagement's contact interfaces balance its hanging weight and torque
- **THEN** the hanging solid is supported, the equilibrium program is
  feasible, and the assertion passes

#### Scenario: Clearance play below the drop distance is not floating

- **WHEN** a solid sits above its seat by a clearance smaller than `max_drop`
- **THEN** its drop intersects the seat with positive volume and the solid
  counts as supported

#### Scenario: An explicit ground replaces the default seeds and anchors

- **WHEN** `ground` names a node whose topmost rigid solid is not at the
  assembly's furthest extent along gravity
- **THEN** only that solid seeds the grounded set and only that solid is
  anchored in the equilibrium phase; the default lowest-extent seeding and the
  virtual floor are not applied

#### Scenario: A declared support edge holds a friction-fit solid

- **WHEN** a solid held only by a press or friction fit is declared in
  `supports` with a transitively grounded supporter
- **THEN** the assertion passes: the declared edge grounds the solid without a
  drop intersection and transmits the unrestricted wrench that balances it

#### Scenario: Invalid knobs raise loud errors

- **WHEN** `gravity` is the zero vector, `max_drop` is not positive,
  `stability_margin` is negative, or a `ground` or `supports` entry resolves
  to no selected solid
- **THEN** the assertion raises an error instead of passing or silently
  ignoring the argument

#### Scenario: An exact assembly is verified exactly

- **WHEN** every selected solid in the assembly is exact
- **THEN** each evaluated drop pair's support-edge existence is decided by the
  boundary-representation kernel, while contact interfaces and mass
  properties come from the placed faceted geometry

#### Scenario: Sparse assembly avoids exhaustive pair booleans

- **WHEN** most selected solids' displaced world bounds are disjoint from the
  others' placed bounds
- **THEN** only bounds-overlapping pairs are evaluated by Boolean
  intersection, in the drop and lift sweeps alike

#### Scenario: Current keyframe controls assembled placement

- **WHEN** the assertion is run under two testing instants that place a solid
  first resting on its support and then apart from it beyond `max_drop`
- **THEN** the first instant passes and the second fails without the assertion
  accepting or setting a keyframe argument itself

#### Scenario: A bar supported at one end fails on torque

- **WHEN** a horizontal bar's only detected contact interface lies under one
  end, so no non-negative normal force distribution cancels the torque of its
  centre of mass about that patch
- **THEN** the assertion fails naming the bar with an unbalanced torque, even
  though the bar transitively reaches ground

#### Scenario: A bar supported at both ends passes

- **WHEN** the same bar gains a second grounded contact interface under its
  other end
- **THEN** the equilibrium program is feasible and the assertion passes

#### Scenario: An offset stack whose cumulative mass leaves the base fails

- **WHEN** each solid in a stack rests stably on the one below, but the
  combined centre of mass of the upper solids passes beyond the lowest
  interface's patch
- **THEN** the assertion fails naming the unbalanced solid(s), although every
  single interface would balance its immediate top solid alone

#### Scenario: A counterweighted assembly passes

- **WHEN** a solid's own centre of mass overhangs its support patch, but a
  counterweight resting on it restores a feasible force distribution over the
  detected contacts
- **THEN** the equilibrium program is feasible and the assertion passes

#### Scenario: A cantilevered pin held by a snug hole passes

- **WHEN** a horizontal pin cantilevers from a grounded block's snug hole, the
  drop detecting the hole's lower-wall contact and the lift detecting its
  upper-wall contact
- **THEN** the two interfaces form the force couple that balances the pin and
  the assertion passes without a `supports` declaration

#### Scenario: A tippy default-seeded solid fails on the virtual floor

- **WHEN** with `ground=None` a default-seeded solid's centre of mass lies
  beyond its own detected contact patch on the virtual floor
- **THEN** the assertion fails naming that solid instead of exempting it as a
  seed

#### Scenario: A stability margin rejects a boundary-exact balance

- **WHEN** an assembly balances only at the boundary of a contact patch and
  the assertion is called with a positive `stability_margin`
- **THEN** the shrunken interfaces make the equilibrium program infeasible and
  the assertion fails, while the same assembly passes at the default margin

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
printed solid. Under the exact comparison kernel, for an exact solid the
assertion SHALL count the solids in that node's exact geometry and require
exactly one. For a solid that is not exact, or for every solid under the
faceted kernel, it SHALL read that node's own built STL, split it without filtering to watertight
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

#### Scenario: A faceted run counts bodies on the STL

- **WHEN** the assertion runs on an exact solid and the run's kernel is
  faceted
- **THEN** the bodies are counted by splitting that solid's own STL and the
  exact geometry is not read

### Requirement: Connectivity assertions

The system SHALL provide two connectivity assertions:

- `assertJoined(node1, node2, min_weld_volume=0.0)` — the two nodes are
  exactly one body, so the two features are genuinely the same printed part.
  Under the exact comparison kernel, for two exact nodes this SHALL be
  established by fusing their shapes and requiring the fuse to yield exactly
  one solid; otherwise, and for every pair under the faceted kernel, by
  requiring the union of their meshes to be exactly one connected component.
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

#### Scenario: A faceted run welds on meshes

- **WHEN** `assertJoined` is called on two exact features and the run's
  kernel is faceted
- **THEN** the verdict comes from the union of their meshes and neither
  shape is fused

### Requirement: Animation-instant decorators

The system SHALL provide `@testing_instant(instant)` and
`@testing_steps(steps, start=0, end=1)` setting `testing_instants` on a test
method; the runner executes the method once per instant with the keyframe
set. `testing_steps` requires `steps >= 2` and forces the final instant to
exactly `end`. An instant is handed to `set_keyframe` unchanged, so it means
what the tested root's time base says: a fraction of the timeline for a root
declaring none, and seconds for a root declaring `Time(loop=...)`. The
decorators' defaults do not change with the declaration; a test over a
declared root states the span it sweeps in seconds.

#### Scenario: Sweeping a rotation

- **WHEN** a method is decorated `@testing_steps(10)`
- **THEN** it runs at 10 evenly spaced instants from 0 to 1 inclusive

#### Scenario: Sweeping seconds under a declared time base

- **WHEN** a test over a root declaring `Time(loop=43200)` is decorated
  `@testing_steps(48, end=1.5)`
- **THEN** it runs at 48 instants from 0 to 1.5 seconds inclusive, and the
  root reads `time` as those seconds

### Requirement: Broad-phase completeness

The conservative world bounds and the spatial index that emits candidate pairs
SHALL be complete: for any placement of any two solids whose exact Boolean
intersection is non-empty, the spatial index SHALL emit that pair. A world
bound SHALL enclose its solid's placed geometry under any composed world
matrix, and bounds that touch without overlapping SHALL be treated as a
candidate rather than culled.

Completeness SHALL be established by framework tests rather than by a runtime
cross-check inside an assertion, so that a project's assertion cost is not
charged for re-verifying framework code.

#### Scenario: Index agrees with exhaustive comparison

- **WHEN** framework tests evaluate an enumerated set of placements covering
  separation, face, edge and vertex contact, overlap, containment, coincident
  bounds, single-axis separation, zero-extent bounds, and rotation, together
  with an exhaustive lattice of placements at fixed offsets
- **THEN** every pair whose exact intersection is non-empty appears in the
  spatial index's emitted candidates, compared against exhaustive
  `N * (N - 1) / 2` evaluation

#### Scenario: Rotated placement stays enclosed

- **WHEN** a solid is placed by a world matrix that rotates it
- **THEN** its conservative world bound encloses the rotated geometry, being a
  superset of the true placed footprint rather than the untransformed box

### Requirement: An intersection verdict is computed once per run

The shared `(is_empty, volume)` helper SHALL answer from a per-run cache when
it is asked a comparison it has already decided, and SHALL compute a verdict
only for a comparison it has not.

A comparison's cache key SHALL identify everything the verdict depends on and
nothing else:

- the identity of each compared solid's geometry, under the same
  `(file, mtime)` identity the per-STL cache already uses, so a rebuilt part
  is a different key rather than a stale hit;
- the pair's RELATIVE placement — one node's composed world matrix inverted
  and applied to the other's;
- the evaluation path taken (exact, faceted, or the `.mesh` fallback), so a
  pair is never served an exact answer from a faceted entry or the reverse.

The relative placement is sufficient because intersection emptiness and volume
are invariant under a common rigid transform: two solids moved together share
exactly the volume they shared before. A repeated key is therefore provably
the same verdict, and reusing it SHALL NOT change any assertion's outcome,
message, or epsilon semantics. This is a recomputation shortcut of the same
kind as the AABB broad phase, not a new tolerance.

The cache SHALL be keyed independently of which assertion asked, so the
animation sweep, the pairwise sweep, the whole-assembly interference
assertion and the perturbation assertions share one another's answers for the
same pair in the same relative placement.

A node whose geometry has no stable identity — a test double exposing only
`.mesh`, or a flexible leaf evaluating its current binding — SHALL NOT be
cached, and its comparisons SHALL be computed exactly as they are today.

#### Scenario: A repeated comparison is not recomputed

- **WHEN** an assertion compares the same two solids in the same relative
  placement a second time within one run
- **THEN** the verdict returned equals the first verdict exactly, and no
  boolean is run by either kernel

#### Scenario: A moved pair is recomputed

- **WHEN** two solids are compared, then one is placed differently relative
  to the other, and they are compared again
- **THEN** the second comparison runs its boolean and returns the verdict for
  the new placement

#### Scenario: A pair moved together is not recomputed

- **WHEN** two solids are compared, then BOTH are placed by the same
  additional rigid transform and compared again
- **THEN** the verdict is served from the cache and equals the first verdict

#### Scenario: A rebuilt part invalidates its entries

- **WHEN** a solid's geometry file is rebuilt and a comparison that involved
  it is repeated
- **THEN** the comparison is recomputed against the new geometry

#### Scenario: Flush contact keeps its verdict through the cache

- **WHEN** a flush abutment that reports non-empty with exactly 0.0 mm³ is
  compared twice
- **THEN** both comparisons report non-empty with 0.0 mm³, and the strict
  `volume_epsilon=0` default still reports the foul

#### Scenario: A node without stable geometry identity is not cached

- **WHEN** a comparison involves a node exposing only `.mesh`
- **THEN** the comparison is computed as it is today and no cache entry
  serves a later comparison in its place

### Requirement: An exact placement is computed once per shape and matrix

On the exact path, the placed shape and the local bounding box a comparison
needs SHALL each be computed once per `(shape identity, matrix)` and reused,
in the same spirit as the per-STL Manifold cache.

Placement caching SHALL NOT change the geometry any comparison sees: a cached
placed shape SHALL be the shape the kernel would have produced for that
matrix, and a shape rebuilt under a new identity SHALL NOT be served a
placement built from the old one.

#### Scenario: One placement serves repeated comparisons

- **WHEN** the same solid is placed by the same matrix for several
  comparisons in one run
- **THEN** the placement is constructed once and the later comparisons reuse
  it

#### Scenario: A different placement is constructed

- **WHEN** the same solid is placed by a different matrix
- **THEN** a placement for that matrix is constructed and used

### Requirement: Run-level comparison kernel

The test framework SHALL hold one comparison kernel per run, `exact` or
`faceted`, and one volume epsilon in mm³, together the run's comparison
policy. The kernel is a property of the run, never of the model: a node's
`exact` attribute SHALL keep reporting whether its geometry is exact, and
neither the build nor any artifact SHALL depend on the kernel a test run
selects.

`solid test` SHALL resolve the kernel from the mutually exclusive `--exact` /
`--faceted` flags, else from the `SOLID_TEST_KERNEL` environment variable
(`exact` or `faceted`; any other value is an error naming the variable), else
`exact`. It SHALL resolve the epsilon from `--volume-epsilon`, else from
`SOLID_TEST_VOLUME_EPSILON`, else `0.0`; a negative value is an error. The
epsilon exists only for the faceted kernel: `--volume-epsilon` together with
an exact run is an error saying the exact kernel has nothing to absorb, and
`SOLID_TEST_VOLUME_EPSILON` is not read under the exact kernel. The
environment is the project's, loaded through the CLI's `.env` rule, so a
setting in an ignored checkout-local `.env` selects the kernel for every run
in that checkout and nowhere else.

Outside `solid test` — a `ScenarioTest` under pytest, an assertion driven
directly — the framework SHALL resolve the same policy from the environment
at the first comparison of the process, with the same defaults and the same
errors.

Under the exact kernel every assertion behaves as specified elsewhere in
this capability. Under the faceted kernel every intersection, containment,
connectivity and weld question SHALL be answered from the compared nodes'
meshes exactly as it is answered today for a node that is not exact, and the
verdicts of the shared intersection helper SHALL have the run's epsilon
applied before any assertion reads them.

#### Scenario: The default run is the exact run

- **WHEN** `solid test` runs with no kernel flag and no `SOLID_TEST_KERNEL`
- **THEN** every comparison of two exact nodes uses the boundary-representation
  kernel and the run's output is unchanged

#### Scenario: A checkout selects the faceted kernel once

- **WHEN** the project's `.env` contains `SOLID_TEST_KERNEL=faceted` and
  `solid test` runs without a kernel flag
- **THEN** every comparison uses the faceted path and the run says so

#### Scenario: A flag overrides the environment

- **WHEN** `SOLID_TEST_KERNEL=faceted` is set and `solid test --exact` runs
- **THEN** the run uses the exact kernel and prints no kernel line

#### Scenario: An epsilon offered to the exact kernel is refused

- **WHEN** `solid test --exact --volume-epsilon 0.5` or
  `solid test --volume-epsilon 0.5` with no faceted selection is run
- **THEN** the command exits with an error saying the exact kernel has nothing
  for an epsilon to absorb, before any node is built

#### Scenario: An unknown kernel name is refused

- **WHEN** `SOLID_TEST_KERNEL=fast` is set
- **THEN** `solid test` exits with an error naming the variable and the two
  accepted values

#### Scenario: A faceted run of an exact project never reaches the exact stack

- **WHEN** an all-exact project is tested under the faceted kernel in a fresh
  interpreter and its build is current
- **THEN** the test framework imports no `cadquery` and reads no node's
  `shape()`, and the verdicts are those of the faceted path

#### Scenario: The model is unaware of the kernel

- **WHEN** a test reads `node.exact` under the faceted kernel
- **THEN** it reports the geometry's exactness as it does under the exact
  kernel

#### Scenario: A scenario test under pytest reads the environment

- **WHEN** a `ScenarioTest` runs under plain pytest with
  `SOLID_TEST_KERNEL=faceted` in the environment
- **THEN** its geometric assertions use the faceted path with the
  environment's epsilon

