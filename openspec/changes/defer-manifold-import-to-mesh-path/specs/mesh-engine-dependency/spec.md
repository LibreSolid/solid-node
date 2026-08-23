## ADDED Requirements

### Requirement: The mesh engine is required only by the paths that use it

The system SHALL treat the `manifold3d` mesh engine as a conditional dependency
of the paths that construct or read a `Manifold`, not as a blanket import-time
requirement of the assertion module.

Importing `solid_node.test`, declaring a `TestCase`, binding a node to it, and
running the test runner SHALL NOT require the mesh engine.

The paths that require it are exactly:

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

Declaring the dependency conditional SHALL NOT change what any of those paths
does when the mesh engine is present: same verdicts, same messages, same
broad-phase candidate sets.

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

### Requirement: An unavailable mesh engine fails actionably at the point of use

When a requiring path is reached and `manifold3d` cannot be imported, the system
SHALL raise one error that names the mesh engine, the operation that needed it,
and why that operation needs it, before any geometry work is attempted. The
error SHALL be raised at the requiring operation, not at module import, and it
SHALL NOT surface as a bare `ModuleNotFoundError` from framework internals.

The system SHALL resolve the mesh engine at most once per process and reuse that
resolution for every requiring path.

Availability of the mesh engine SHALL be decided by the mesh engine alone.
Checks that do not need it — a solid's local bounding box, and the
watertightness validation that raises a `ValueError` naming a non-watertight
STL — SHALL continue to be performed from the cached base mesh whether or not
the mesh engine is present, and SHALL keep the timing and message they have
today.

#### Scenario: A faceted interference check names the missing dependency

- **WHEN** `assertNoSolidInterference` evaluates a candidate pair in which a
  solid is not exact and `manifold3d` cannot be imported
- **THEN** the assertion raises an error naming `manifold3d`, the assertion that
  needed it, and the reason, rather than a bare import error

#### Scenario: The gravity support assertion names the missing dependency

- **WHEN** `assertAssemblySupported` is called on two or more selected solids,
  every one of them exact, and `manifold3d` cannot be imported
- **THEN** the assertion raises an error naming `manifold3d` and stating that
  contact extraction for the statics phase is faceted, rather than a bare import
  error or a passing verdict

#### Scenario: A non-watertight STL is still reported by name

- **WHEN** an assertion selects a solid whose STL is not watertight
- **THEN** it raises a `ValueError` naming that STL file, whether or not the
  mesh engine is installed and whether or not that solid is ever compared
