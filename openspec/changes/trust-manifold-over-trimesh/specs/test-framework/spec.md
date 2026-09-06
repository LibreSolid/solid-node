## MODIFIED Requirements

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
