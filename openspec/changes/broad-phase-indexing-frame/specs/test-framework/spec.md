## MODIFIED Requirements

### Requirement: Broad-phase completeness

The conservative bounds and the spatial index that emits candidate pairs SHALL
be complete: for any placement of any two solids whose exact Boolean
intersection is non-empty, the spatial index SHALL emit that pair. A bound
SHALL enclose its solid's placed geometry expressed in the frame the index
took it in — the world frame, or the INDEXING FRAME the index chose — under
any composed world matrix, and bounds that touch without overlapping SHALL be
treated as a candidate rather than culled.

The index MAY take its bounds in an indexing frame other than the world frame.
A bound in an indexing frame `F` is the axis-aligned box of a solid's local
bounds' eight corners under `inv(F)` composed with the solid's world matrix. A
bound taken in an indexing frame MAY be enlarged by a fixed absolute margin
absorbing the arithmetic of the frame change, and remains a superset of the
solid's placed geometry in that frame. Enlargement SHALL only add candidate
pairs, never remove one, so a pair whose bounds meet or touch in that frame —
including two solids in exact flush contact, whose intersection is non-empty
with zero volume — SHALL still be emitted. A bound taken on world axes SHALL
NOT be enlarged, so an index that chooses the world frame produces exactly the
bounds it produces with no indexing frame at all.
Completeness is preserved in any invertible frame, because such a frame
carries each solid inside its own transformed bound and preserves
intersection: two solids whose bounds are disjoint in ONE common frame cannot
share material in any frame. The choice of frame SHALL therefore be capable of
changing only WHICH candidate pairs are emitted and in what order, and SHALL
NOT change any assertion's verdict, message, or epsilon semantics.

Where an indexing frame is chosen, it SHALL be chosen by a deterministic rule
from a bounded candidate set: the world frame, and the placement frames of a
bounded number of the largest selected solids measured by their own local
bounds. The rule SHALL score each candidate by a cheap frame-comparable
measure of the bounds it would actually hand the sweep, enlargement included,
SHALL resolve ties to the earliest candidate with the world frame first, and
SHALL fall back to the world frame
for any candidate whose frame cannot be inverted or whose bounds are not
finite. The same selected solids in the same placements SHALL therefore choose
the same frame and emit the same ordered candidate pairs on every run. The
number of candidate frames, the scoring measure and the enlargement margin are
internal tuning values and SHALL NOT be exposed as an assertion argument,
flag, or environment variable.

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

#### Scenario: Completeness holds in the chosen indexing frame

- **WHEN** the same enumerated boundary table and exhaustive lattice are
  indexed through the whole-assembly assertion's own index, which has chosen
  an indexing frame
- **THEN** every pair whose exact intersection is non-empty still appears in
  the emitted candidates, compared against the same exhaustive evaluation

#### Scenario: Rotated placement stays enclosed

- **WHEN** a solid is placed by a world matrix that rotates it
- **THEN** its conservative world bound encloses the rotated geometry, being a
  superset of the true placed footprint rather than the untransformed box

#### Scenario: A bound in an indexing frame stays enclosed

- **WHEN** a solid's bound is taken in an indexing frame that is not the world
  frame
- **THEN** that bound encloses the solid's placed geometry expressed in that
  same frame, being a superset of its true footprint there

#### Scenario: A common rigid turn does not cost candidates

- **WHEN** an assembly whose largest solid is axis-aligned and whose solids
  are separated by gaps far exceeding the enlargement margin is indexed, and
  then every one of its solids is placed by one additional common rigid turn
  and indexed again
- **THEN** the turned assembly's index, having chosen the largest solid's
  frame, emits exactly the candidate pairs the un-turned assembly's world-axis
  index emitted, while a world-axis index of the turned assembly emits further
  pairs whose solids never meet

#### Scenario: Flush contact under a common turn stays a candidate

- **WHEN** an assembly containing an axis-aligned face-contact pair and an
  axis-aligned edge-contact pair is placed by one common rigid turn applied to
  every solid, and indexed in a frame that is not the world frame
- **THEN** both pairs are emitted as candidates, the arithmetic of the frame
  change having been absorbed by the enlargement rather than separating bounds
  that touch

#### Scenario: The frame choice is deterministic

- **WHEN** the same selected solids in the same placements are indexed twice
  in one run
- **THEN** the same indexing frame is chosen and the same candidate pairs are
  emitted in the same order

#### Scenario: The frame choice never changes a verdict

- **WHEN** an assembly is verified through the chosen-frame index and through
  a world-axis index of the same placements
- **THEN** both reach the same verdict with the same message, differing only
  in how many candidate pairs were settled by a Boolean

#### Scenario: Gravity support keeps its world bounds

- **WHEN** the gravity support assertion computes its gravity extents,
  grounded seeds, virtual floor and directed drop candidates
- **THEN** it reads bounds taken on world axes, so that a projection along the
  world gravity vector remains meaningful, and no indexing frame is applied to
  them

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
