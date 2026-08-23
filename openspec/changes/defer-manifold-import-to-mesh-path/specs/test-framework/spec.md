## MODIFIED Requirements

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

The per-STL cache SHALL be split by what each part of it needs:

- a solid's local bounding box and its watertightness validation are read from
  the same cached base mesh the `mesh` property uses, keyed by
  `(stl_file, mtime)` with stale entries evicted on rebuild, and SHALL be
  performed whenever a solid is selected — a non-watertight STL raises a
  `ValueError` naming the file rather than failing inside the boolean engine.
  This half SHALL NOT require the mesh engine;
- one `manifold3d.Manifold` per `(stl_file, mtime)` (module-level, stale
  entries evicted on rebuild) is built from that same cached base mesh at the
  FIRST comparison that actually reads it, and never for a solid whose every
  comparison is decided by the boundary-representation kernel. Repeated reads
  SHALL reuse the one cached Manifold, so deferring construction SHALL NOT
  increase the number of Manifolds built for any assembly.

The faceted fast path SHALL then place the cached Manifolds with a lazy
`transform()` and intersect them directly, reading `is_empty()` and `volume()`
off the result with no conversion back to trimesh, reading `volume` only when
non-empty.

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

Placing a solid for the spatial index SHALL NOT of itself construct that solid's
faceted representation. A solid's Manifold SHALL be built only when a candidate
pair it belongs to is actually evaluated by the mesh engine, so an assembly whose
every selected solid is exact SHALL require no mesh engine at all — see the
`mesh-engine-dependency` capability.

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
