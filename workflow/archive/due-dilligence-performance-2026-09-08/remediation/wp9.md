# WP9 — Sparse-equivalent static equilibrium

## Scope

This package changes only the storage representation inside
`solid_node.test._unbalanced_bodies`.  It retains one global coupled program,
the existing body/contact/declared-wrench and six-row ordering, weight and
torque targets, per-row tolerance scaling, variable bounds, L1 elastic-slack
objective, `method='highs'`, and failure classification.

Each coefficient is accumulated in a dictionary one addition at a time in the
planning implementation's exact contact/body/component and
edge/body/axis/component loop order.  Only after those floating additions are
complete is one value per nonzero cell emitted into a SciPy COO matrix and
converted to CSR.  Duplicate COO coordinates are never created or coalesced.
The two elastic-slack blocks use sparse identities and sparse horizontal
stacking; targets, tolerances, objectives and solver results remain 1D.

## Red/green proof

[wp9-red.log](wp9-red.log) records the red production path: 5 tests and 10
fixture subtests already passed, while the two representation tests observed a
dense coefficient matrix and intercepted `np.zeros((6000, 0))` before the
legacy path could allocate its 576 MB pair of dense identities.

[wp9-green.log](wp9-green.log) records 7 dedicated tests with 10 paired
real-geometry subtests, 96 combined support/broad-phase/integrity tests, all 6
support meta tests through the CLI/builder/kernel, and all 7 conditional mesh
dependency tests.  The test-only dense reference is extracted from planning
HEAD and separately invokes HiGHS on the same inputs.  Generated and existing
fixture comparisons cover feasibility, coefficient equality, objective,
optimized slack, targets/tolerances, ordered body names and force-versus-torque
diagnosis, including cancellation, repeated determinism and both sides of the
existing tolerance boundary.

## Construction measurement

[wp9-memory.log](wp9-memory.log) is produced by the checked-in
[wp9_probe.py](wp9_probe.py).  A representative 1,000-free-body, 1,000-contact
system constructed a 6,000×13,000 equality matrix with 13,000 nonzeros.  Its
CSR arrays occupy 180,004 bytes and the objective/target vectors 152,000 bytes,
against the historical representation's 48,000,000-byte coefficient matrix
and 576,000,000-byte pair of dense slack identities.  The observed construction
peak was 2,014,128 traced bytes and max RSS did not rise above the process's
prior high-water mark.  Those runtime readings are observations; matrix type,
shape, nnz and array sizes prove the sparse scaling.

## Provenance and limits

- Planning source is `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c` on
  `performance-analysis`; the dense reference names that commit in code.
- Tests and measurements used the workspace Python 3.12.3 environment with
  SciPy 1.18.1 on Linux x86-64.
- HiGHS still owns solver workspace, presolve and numerical behavior; this
  package bounds the framework's avoidable matrix construction, not the
  solver's internal memory.
- No independent bodywise solve, solver/method change, tolerance change,
  dependency change, public API, historical audit file, project, OpenSpec
  artifact, task checkbox, ADR, or progress record is part of WP9.
