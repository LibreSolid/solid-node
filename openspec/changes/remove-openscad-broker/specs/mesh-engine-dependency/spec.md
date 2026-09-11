## MODIFIED Requirements

### Requirement: The mesh engine is required only by the paths that use it

The system SHALL treat the `manifold3d` mesh engine as a conditional dependency
of the paths that construct or read a `Manifold`, not as a blanket import-time
requirement of the assertion module.

Importing `solid_node.test`, declaring a `TestCase`, binding a node to it, and
running the test runner SHALL NOT require the mesh engine.

The paths that require it are exactly:

- producing a stale non-exact `FusionNode` artifact by directly unioning its
  children's meshes;

- evaluating an intersection between two nodes that do not both carry exact
  geometry — the faceted fast path and the `.mesh` fallback of the shared
  intersection helper, and therefore `assertNotIntersecting`,
  `assertIntersecting`, `assertIntersectVolumeAbove`,
  `assertIntersectVolumeBelow`, `assertBlockedBeyond`, `assertFreeWithin`,
  `assertJoined` and `assertNoPairwiseIntersections` whenever the pair they
  compare is not a pair of exact nodes;
- evaluating a candidate pair of `assertNoSolidInterference` in which at least
  one of the two solids is not exact;
- `assertAssemblySupported` over two or more selected solids, whose
  frictionless-statics phase extracts contact patches from meshed intersections
  for every body — exact solids included — and builds a meshed virtual floor.

No other operation SHALL require it. In particular, a project whose model is
entirely exact under the `exact-geometry` capability SHALL run
`assertNoSolidInterference`, `assertNoDisconnectedSolids`, `assertJoined`, and
every intersection-volume and perturbation assertion with no `manifold3d`
installed.

Adding faceted fusion to this requiring set SHALL NOT change existing
assertion behavior when the mesh engine is present: same verdicts, same
messages, same broad-phase candidate sets. Exact fusion and assembly grouping
SHALL NOT resolve the mesh engine merely to prepare or produce geometry.

The system SHALL NOT substitute a different engine, degrade a verdict, skip an
assertion, or emit a warning in place of a result when the mesh engine is
unavailable. An unavailable mesh engine means the operation cannot be performed.

Assertions whose geometry is reached through libraries that select their own
backends — `trimesh.boolean` in `assertJoined`'s faceted union, and the
proximity queries behind `assertInside`, `assertClose` and `assertFar` — SHALL
report through those libraries' own dependency contracts. This capability does
not describe them.

#### Scenario: An all-exact project asserts with no mesh engine installed

- **WHEN** a project whose every selected solid is exact is tested on a machine
  where `manifold3d` cannot be imported
- **THEN** `solid_node.test` imports, the runner starts, and
  `assertNoSolidInterference` reaches the same verdict it reaches with the mesh
  engine installed

#### Scenario: The assertion module imports without the mesh engine

- **WHEN** `solid_node.test` is imported in an interpreter where `manifold3d`
  cannot be imported
- **THEN** the import succeeds and no error is raised until an operation that
  needs the mesh engine is reached

#### Scenario: A faceted comparison still requires it

- **WHEN** an assertion compares a pair in which at least one node is not exact
  and the mesh engine is available
- **THEN** the comparison is evaluated through the cached Manifolds exactly as
  before

#### Scenario: Faceted fusion names its missing engine

- **WHEN** a non-exact fusion needs to produce its artifact and `manifold3d`
  cannot be imported
- **THEN** it fails naming the engine and the fusion operation, without trying
  OpenSCAD, publishing concatenated geometry, or silently retaining a stale STL

#### Scenario: Current fusion does not resolve its engine

- **WHEN** a fusion's artifact and producer recipe are current
- **THEN** artifact reuse performs no mesh-engine resolution or new union
