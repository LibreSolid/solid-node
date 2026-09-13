## MODIFIED Requirements

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

For a candidate evaluated on the faceted representation, a finite negative
intersection volume SHALL NOT count as positive-volume interference and the
assertion SHALL continue to the remaining candidates. This rule SHALL NOT
alter the engine's raw emptiness or measured volume, apply a magnitude cutoff,
or change the shared verdict consumed by pairwise or fit assertions. The
representation of the candidate, not only the run's selected kernel, SHALL
determine whether this rule applies. Non-empty candidates with non-finite
volume SHALL still fail; exact-representation candidate behavior SHALL remain
unchanged.

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

#### Scenario: Negative faceted volume is not positive shared material

- **WHEN** a non-empty faceted candidate reports a finite negative volume,
  including −9.947598300641403e−14 mm³, at zero run epsilon
- **THEN** the assembly assertion passes that candidate without rewriting
  its raw measurement or emptiness and continues checking the assembly

#### Scenario: A later positive candidate still fails

- **WHEN** a negative-volume faceted candidate is followed by a positive-volume
  candidate at zero run epsilon
- **THEN** the assertion fails naming the positive pair and its volume

#### Scenario: No positive-volume allowance is introduced

- **WHEN** a candidate reports the smallest representable positive volume
  at zero run epsilon
- **THEN** the assembly assertion fails without any absolute-value or
  magnitude-based forgiveness

#### Scenario: Mixed assembly preserves the representation boundary

- **WHEN** a pair involving a faceted solid is evaluated on meshes during
  an exact run and reports a finite negative volume
- **THEN** the assembly assertion passes that candidate, while an
  exact-representation non-empty negative result retains its failure

#### Scenario: Non-finite volume is not a passing measurement

- **WHEN** a non-empty candidate reports NaN, positive infinity or negative
  infinity
- **THEN** the assembly assertion fails naming the pair and measurement

#### Scenario: Strict pairwise contact remains strict

- **WHEN** the faceted engine reports a non-empty negative or zero-volume
  result at zero run epsilon and the caller uses `assertNotIntersecting`
- **THEN** that pairwise assertion still fails under its engine-emptiness
  contract, even when the assembly integrity assertion passes the same pair
