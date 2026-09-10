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

For a pair of EXACT solids a SECOND exact-negative tier MAY run after that
broad phase and before any boolean: a FACE-BOX tier with a containment guard.
It SHALL report the pair exactly empty with zero volume, on the exact path,
only when both of the following hold:

- no bounding box of any face of either solid meets any bounding box of any
  face of the other, the two solids' face boxes being compared in one common
  frame, boxes that touch without overlapping counting as meeting rather than
  as separated; and
- one representative point of EVERY solid of each shape is classified strictly
  OUTSIDE every solid of the other shape's placed geometry, each classification
  being of one point against one solid rather than against a shape as a whole.

Each face's bounding box SHALL enclose that face's exact surface, and a box
carried into the common frame MAY be enlarged by a fixed absolute margin
absorbing the arithmetic of that frame change; enlargement SHALL only make the
tier decline, never make it decide. Both classification directions SHALL be
required, because two closed solids whose boundaries do not meet are either
disjoint or one lies wholly inside the other, and only the representative
points of the CONTAINED shape reveal containment. A shape carrying no faces or
no solids, a solid carrying no representative point, a non-finite relative
placement, and any classification that is not strictly outside — inside, on
the boundary, unknown, or refused by the classifier — SHALL each make the tier
DECLINE, and a declined pair SHALL be settled by the boolean exactly as it is
without the tier. The tier SHALL therefore be capable of removing boolean
work only, and SHALL NOT change any verdict, volume, message, or epsilon
semantics: a flush contact's face boxes touch, so it reaches the kernel and
still returns non-empty at exactly 0.0 mm³; a solid wholly inside another is
caught by the containment guard and reaches the kernel; a solid inside another
solid's cavity shares no material with it and is reported empty, which is the
verdict the kernel reports for it too. The tier SHALL run inside the memoized
computation, so its verdict is cached and served under the same identity any
boolean verdict is. The margin, the comparison frame and any internal chunking
of the comparison are internal tuning values and SHALL NOT be exposed as an
assertion argument, flag, or environment variable. The faceted path SHALL NOT
have this tier: a faceted verdict is read from cached Manifolds, which carry
no faces, and a faceted run reads no solid's exact geometry at all.

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

#### Scenario: An enclosed exact pair skips the boolean

- **WHEN** two exact solids' whole-solid bounds overlap — one solid lying
  inside the region the other spans — while no face of either comes near any
  face of the other
- **THEN** the helper reports the pair empty with zero volume on the exact
  path without running any boolean

#### Scenario: Containment is not mistaken for separation

- **WHEN** one exact solid lies wholly inside another, so their boundaries do
  not meet at all
- **THEN** the containment guard finds a representative point inside the
  partner, the boolean runs, and the helper reports the positive intersection
  volume

#### Scenario: A solid in a cavity is empty

- **WHEN** one exact solid lies wholly inside a cavity of another, touching no
  face of it
- **THEN** the helper reports the pair empty with zero volume, the same
  verdict the boundary-representation kernel reports for it

#### Scenario: Flush contact still reaches the kernel

- **WHEN** two exact solids meet on a coincident face, their touching face
  boxes overlapping
- **THEN** the face-box tier declines, the boolean runs, and the verdict is
  the kernel's own — empty with zero volume for coincident exact faces, as it
  is without the tier

#### Scenario: A compound whose components straddle the partner

- **WHEN** one exact shape is a compound of two solids, one of them wholly
  inside the other shape and one wholly outside it, and no boundaries meet
- **THEN** the per-solid containment guard, classifying each shape's solids
  against each solid of the other, finds the inside component, the boolean
  runs, and the pair is reported with its positive volume

#### Scenario: A shape the tier cannot represent falls through

- **WHEN** an exact shape presented to the tier carries no faces, or a solid
  of it carries no representative point, or the pair's relative placement is
  not finite
- **THEN** the tier decides nothing and the pair is settled by the boolean
  exactly as it is without the tier

#### Scenario: A faceted pair has no face-box tier

- **WHEN** a pair is evaluated on the faceted path, whether because a solid is
  faceted or because the run's kernel is faceted
- **THEN** no face bounding box is computed, no solid's exact geometry is
  read, and the verdict is the cached Manifolds' own

### Requirement: Whole-assembly solid interference assertion

The system SHALL provide `TestCase.assertNoSolidInterference(node)` as an
ordinary project assertion. Starting at `node`, it SHALL descend through
non-rigid nodes, select the first rigid node on each branch, and stop below each
selected node. These topmost rigid nodes are the printed solids whose assembled
world-space geometry SHALL be evaluated at the testing instant already set by
the runner. Rigid descendants inside a selected fusion SHALL NOT be evaluated
as separate assembly parts.

The assertion SHALL pass without geometric work when selection contains zero
or one solid. With multiple solids, a spatial index over conservative
bounds — taken on world axes, or in the indexing frame the index chose under
the `Broad-phase completeness` requirement — SHALL be the sole verification
path: it emits every potentially
interacting solid pair without first materializing every pairwise combination,
and each emitted pair is evaluated by exact Boolean intersection of the two
solids placed by their composed world transforms. Under the exact comparison
kernel a pair of exact solids SHALL be evaluated by the boundary-representation
kernel and any other pair by the cached Manifolds as before; under the faceted
kernel every pair SHALL be evaluated by the cached Manifolds and no solid's
exact geometry is read.

An emitted pair of exact solids MAY be decided empty BEFORE any boolean by the
face-box tier of the `Accelerated intersection evaluation` requirement, which
is an exact-negative shortcut of the same kind as the bounds index above it:
it may only remove boolean work, and may not change which pairs are emitted,
which pairs fail, or what a failure says. A pair the tier does not decide
SHALL be settled by the boolean, so the assertion's verdict is identical with
the tier and without it. The assertion SHALL NOT compute an
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

- **WHEN** most selected solids have disjoint bounds in the frame the index
  took them in
- **THEN** the spatial index emits only bounds-overlapping candidates and the
  assertion does not construct all `N * (N - 1) / 2` pairs

#### Scenario: Assembly cost tracks interacting pairs, not total geometry

- **WHEN** the selected solids are numerous and detailed but pairwise separated
- **THEN** the assertion performs no work proportional to the assembly's total
  triangle count beyond building a bounded number of conservative bounds per
  solid — one per candidate indexing frame considered, each from the same
  eight local-bounds corners

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

#### Scenario: A solid enclosed by another's bounds but touching none of its faces

- **WHEN** an exact assembly places a solid inside the region another solid
  spans — a wheel between two plates, say — so their bounds overlap in every
  frame, while no face of one comes near any face of the other
- **THEN** the index emits that pair, the face-box tier decides it empty
  without any boolean, and the assertion passes

#### Scenario: A solid wholly inside another still fails

- **WHEN** one topmost rigid exact solid lies wholly inside another, their
  boundaries not meeting
- **THEN** the assertion fails naming both solids and their intersection
  volume, the containment guard having sent the pair to the boolean

#### Scenario: A solid inside another's cavity passes

- **WHEN** one topmost rigid exact solid lies wholly inside a cavity of
  another, touching none of its faces
- **THEN** the assertion passes that candidate, the two sharing no material

#### Scenario: Flush contact in an exact assembly still reaches the kernel

- **WHEN** two topmost rigid exact solids meet on a coincident face
- **THEN** the boolean runs for that pair and reports it non-empty with
  exactly zero volume, which the assertion passes without a public epsilon

#### Scenario: A compound solid with one component inside the partner fails

- **WHEN** a topmost rigid exact solid comprises two solids, one wholly inside
  another topmost rigid solid and one wholly outside it
- **THEN** the assertion fails naming that pair, the containment guard being
  applied to every solid of a shape rather than to the shape as a whole
