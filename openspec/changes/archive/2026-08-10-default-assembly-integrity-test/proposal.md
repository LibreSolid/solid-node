## Why

New projects prove that each printed solid is connected, but they do not prove
that the assembled solids avoid occupying the same material. The existing
`assertNoPairwiseIntersections` safety net walks leaf pairs quadratically and
checks the wrong unit after topmost rigid nodes became the framework's printed
part boundary, so it is unsuitable as the default whole-project contract.

## What Changes

- Add `TestCase.assertNoSolidInterference(node)`, an ordinary assembly test
  assertion that selects the topmost rigid nodes in the supplied subtree and
  checks their world-space geometry at the current testing instant.
- Make the assertion pass vacuously for zero or one selected solid, so the same
  generated test remains valid while a project evolves from a leaf or fusion
  into an assembly.
- Detect positive-volume interference with a scalable whole-assembly volume
  certificate and use a spatially indexed candidate search to identify an
  offending solid pair when the certificate reports interference or is within
  numerical uncertainty.
- Give the assertion no public overlap epsilon. Numerical uncertainty may
  require further verification but SHALL NOT itself excuse interference;
  exact zero-volume boundary contact remains distinct from positive-volume
  overlap. Production clearance remains a separate, length-based project
  contract rather than a tolerated overlap volume.
- Extend `solid new` to scaffold `test_assembly_integrity` beside
  `test_solid_integrity`, giving every new project explicit root-level solid
  connectivity and assembly-interference safety tests. The ordinary test
  runner supplies the current keyframe and animation decorators can sweep
  additional instants.
- Deprecate `assertNoPairwiseIntersections` in favor of
  `assertNoSolidInterference`. Keep it available for compatibility in this
  change, warn callers about its leaf-based quadratic behavior, and remove it
  from current guidance; removal is deferred to a later breaking change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-framework`: Add the topmost-rigid assembly-interference assertion,
  define its numerical/contact and diagnostic behavior, and deprecate the old
  leaf-pair sweep.
- `cli`: Generate the assembly-integrity test alongside the existing
  solid-integrity test in every `solid new` project.

## Impact

- Public test API: `solid_node/test.py` gains
  `assertNoSolidInterference`; `assertNoPairwiseIntersections` becomes
  deprecated but remains callable.
- Node traversal and geometry: reuse `_topmost_rigid_nodes`, cached Manifolds,
  and current world-matrix semantics; add scalable batch-union and spatial
  candidate evaluation without a new project dependency.
- Project scaffolding: the companion test template and `solid new` expectations
  grow from one generated test to two.
- Tests and documentation: add unit and end-to-end coverage for leaf, fusion,
  nested/static/animated assembly, contact, interference, numerical
  uncertainty, diagnostic, scale, and deprecation behavior; update testing and
  architecture documentation after implementation evidence confirms the
  design.
