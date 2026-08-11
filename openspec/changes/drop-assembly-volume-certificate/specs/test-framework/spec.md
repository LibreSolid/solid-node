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
or one solid. With multiple solids, a spatial index over conservative world
bounds SHALL be the sole verification path: it emits every potentially
interacting solid pair without first materializing every pairwise combination,
and each emitted pair is evaluated by exact Boolean intersection of the cached
Manifolds placed by their composed world transforms. The assertion SHALL NOT
compute an aggregate volume, Boolean union, or other whole-assembly measurement
of the selected solids.

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

## ADDED Requirements

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
