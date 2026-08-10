## ADDED Requirements

### Requirement: Whole-assembly solid interference assertion

The system SHALL provide `TestCase.assertNoSolidInterference(node)` as an
ordinary project assertion. Starting at `node`, it SHALL descend through
non-rigid nodes, select the first rigid node on each branch, and stop below each
selected node. These topmost rigid nodes are the printed solids whose assembled
world-space geometry SHALL be evaluated at the testing instant already set by
the runner. Rigid descendants inside a selected fusion SHALL NOT be evaluated
as separate assembly parts.

The assertion SHALL pass without geometric work when selection contains zero
or one solid. With multiple solids, it SHALL compare the sum of their volumes
with the volume of their batch Boolean union using the same cached Manifold
representation and world transforms. It SHALL also use a spatial index over
conservative world bounds to evaluate only potentially interacting solid pairs,
without first materializing every pairwise combination.

Positive-volume overlap SHALL fail. Empty intersection and non-empty
zero-volume boundary contact SHALL pass. The assertion SHALL expose no overlap
epsilon. A private numerical uncertainty bound MAY decide whether the global
volume result requires pair verification, but SHALL NOT by itself cause a
small positive result to pass. Candidate verification SHALL treat every
positive intersection volume reported by the kernel as interference. If a
clearly positive global deficit cannot be reconciled to a candidate pair, the
assertion SHALL fail with the aggregate deficit and identify the numerical
inconsistency rather than silently pass.

When an offending candidate is found, the assertion SHALL raise
`AssertionError` naming both topmost rigid solids and their measured
intersection volume. The framework SHALL run the assertion only when ordinary
project test code calls it; builders and non-test commands SHALL NOT invoke it.

#### Scenario: A leaf project passes throughout early evolution

- **WHEN** `assertNoSolidInterference(self.node)` is called on a leaf root or a
  fusion root containing only one topmost rigid solid
- **THEN** the assertion passes without performing a Boolean union or candidate
  intersection

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

- **WHEN** floating-point accumulation leaves the global volume deficit within
  its private numerical uncertainty bound
- **THEN** the assertion verifies spatially indexed candidates rather than
  treating the uncertainty as permission for overlap

#### Scenario: Current keyframe controls assembled placement

- **WHEN** the assertion is run under two testing instants that place the same
  selected solids first apart and then overlapping
- **THEN** the first instant passes and the second fails without the assertion
  accepting or setting a keyframe argument itself

#### Scenario: Sparse assembly avoids exhaustive pair construction

- **WHEN** most selected solids have disjoint world bounds
- **THEN** the spatial index emits only bounds-overlapping candidates and the
  assertion does not construct all `N * (N - 1) / 2` pairs

## MODIFIED Requirements

### Requirement: Pairwise adjacency sweep

The system SHALL retain the deprecated
`assertNoPairwiseIntersections(node, volume_epsilon=0.0)` compatibility API.
It SHALL preserve its historical behavior of walking the assembled tree to
its leaves, checking every leaf pair, and using `volume_epsilon` to filter
flush-contact noise. Each call SHALL emit a standard deprecation warning that
points to `assertNoSolidInterference` and explains that the replacement checks
topmost rigid solids without a public overlap epsilon. Current documentation
SHALL NOT recommend the deprecated sweep for new tests.

#### Scenario: Existing caller keeps its historical verdict

- **WHEN** an existing project calls the deprecated sweep on an assembly where
  two leaves overlap by more than its supplied epsilon
- **THEN** an `AssertionError` still names the offending leaf pair

#### Scenario: Caller receives migration guidance

- **WHEN** a test invokes `assertNoPairwiseIntersections`
- **THEN** an explicitly captured deprecation warning points to
  `assertNoSolidInterference` and states the topmost-rigid scope difference
