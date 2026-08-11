## 1. Prove broad-phase completeness red-first

- [ ] 1.1 Add the named boundary table to `tests/test_broad_phase_culling.py`:
      fully separated; face, edge, and vertex contact; positive overlap; full
      containment; coincident bounds; separation on exactly one axis for each
      of X, Y, Z; zero-extent bounds; rotated placement. Each case named for
      the condition it pins, asserting the pair is emitted whenever its exact
      intersection is non-empty
- [ ] 1.2 Add the exhaustive lattice: unit boxes at half-integer offsets over a
      bounded grid, asserting `_bounds_candidates` output contains every
      non-empty-intersection pair found by brute-force `itertools.combinations`
- [ ] 1.3 Add a conservativeness test for `_world_bounds` under rotation: the
      bound encloses the placed geometry and is a strict superset of the
      untransformed local box
- [ ] 1.4 Add a differential check over the assemblies the existing tests
      already construct, asserting candidate-set containment with no new
      geometry
- [ ] 1.5 Confirm red twice: the table and lattice fail against a temporarily
      non-strict `_boxes_disjoint`, and the conservativeness test fails against
      a temporarily untransformed `_world_bounds`. Record both failures, then
      restore the real implementations and confirm green

## 2. Move certificate-era coverage onto the public assertion

- [ ] 2.1 Rewrite `test_global_deficit_stays_positive_for_triple_overlap` and
      `test_containment_produces_a_positive_global_deficit` in
      `tests/test_assembly_integrity.py` as public-assertion tests: triple
      overlap and full containment must fail `assertNoSolidInterference`
      naming an offending pair
- [ ] 2.2 Confirm those rewritten tests pass against the current two-path
      implementation before anything is removed, so the coverage is proven
      independent of the removal
- [ ] 2.3 Add two deliberately-red meta fixtures beside the existing
      `assembly_integrity_*` set: three topmost rigid solids sharing a common
      region, and a smaller solid wholly inside a larger one with no surface
      crossing. Register both in `tests/test_meta.py` and assert the failure
      text names both offending solids

## 3. Remove the certificate

- [ ] 3.1 Delete `_assembly_volume_certificate` from `solid_node/test.py`
- [ ] 3.2 Reduce `assertNoSolidInterference` to selection, world bounds,
      sweep-and-prune, and exact pairwise intersection; remove the deficit,
      uncertainty, non-finite, and "certificate is inconsistent" branches
- [ ] 3.3 Delete the certificate-patching tests
      (`test_uncertain_deficit_still_checks_bounds_candidates`,
      `test_unreconciled_positive_certificate_fails`, and the remaining
      `_assembly_volume_certificate` patches) from
      `tests/test_assembly_integrity.py`
- [ ] 3.4 Remove or reword any docstring and comment referring to the
      certificate, the deficit, or the uncertainty bound

## 4. Validate

- [ ] 4.1 Run `tests/test_assembly_integrity.py`,
      `tests/test_broad_phase_culling.py`, `tests/test_connectivity.py`,
      `tests/test_manifold_cache.py`, and `tests/test_assertions.py` green
- [ ] 4.2 Run the meta fixtures `assembly_integrity_nested`,
      `assembly_integrity_contact`, and `assembly_integrity_animated` through
      `tests/test_meta.py` and confirm unchanged green/red outcomes and
      unchanged failure text
- [ ] 4.3 Run the full framework suite and confirm no unrelated regression
- [ ] 4.4 Verify the scaffold acceptance still reports exactly two passing
      tests for a generated leaf project

## 5. Measure

- [ ] 5.1 Reproduce the clean-pass timings under the methodology in
      `docs/performance-improvement.md`, before and after removal, across the
      part counts and triangle densities that file already uses
- [ ] 5.2 Measure the first-offending-pair (failing) case before and after
- [ ] 5.3 Record both, with the deprecated-sweep comparison for continuity,
      in `docs/performance-improvement.md` as bounded observations

## 6. Records

- [ ] 6.1 Revise ADR-040 in place: retitle away from "certificate", rewrite
      Decision and Consequences for the single spatial path, add an
      **Alternatives rejected** section carrying the batch-union certificate
      with its original rationale and the new measurements, add the revision
      date, and add the broad-phase completeness obligation to Evidence
- [ ] 6.2 Update the ADR-040 row in `docs/adrs/README.md` for the new title
- [ ] 6.3 Update `docs/testing.rst` and any other user-facing text that
      describes the union comparison
- [ ] 6.4 Confirm no new ADR is created and ADR-040 keeps its `Accepted`
      status, dependencies, and `Supersedes in part` relationship to ADR-025
