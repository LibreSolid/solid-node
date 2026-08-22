# Tasks: add `assertAssemblySupported`

## 1. Red-first fixtures and tests

- [x] 1.1 Study `tests/test_assembly_integrity.py` and its
      `tests/meta_project/` fixtures; add support fixtures in the same
      pattern: floating solid, resting stack, chain on a floating supporter,
      hanging solid held by engagement, mutual-lean cycle (grounded and
      ungrounded variants), clearance play below `max_drop`, explicit ground
      anchor, friction-fit solid for `supports`, and an exact-geometry
      assembly variant.
- [x] 1.2 Write `tests/test_assembly_supported.py` covering every delta-spec
      scenario, including loud-error knobs (zero gravity, non-positive
      `max_drop`, unresolvable `ground`/`supports`), lowest-extent default
      seeding, keyframe-controlled placement, and broad-phase culling
      (no boolean for bounds-disjoint pairs). Run it and confirm every test
      fails red for the right reason (missing assertion), not by collection
      error.

## 2. Implementation

- [x] 2.1 Add private support-graph helpers to `solid_node/test.py`:
      world-frame drop placement over `_placed_assembly_solids` output,
      displaced-vs-placed AABB candidate culling, per-pair dropped
      intersection routing (exact pair via kernel, otherwise cached
      Manifolds), seed resolution (lowest-extent default within `max_drop`,
      explicit `ground` override), `supports` edge resolution, and BFS
      grounded propagation.
- [x] 2.2 Add `TestCase.assertAssemblySupported(node, gravity=(0, 0, -1),
      max_drop=1.0, ground=None, supports=None)` using those helpers, with
      the failure message naming every ungrounded solid plus the drop
      distance and gravity direction, and a docstring stating the physical
      exclusions and the `max_drop` selection rule (above vertical clearance,
      below thinnest support thickness plus gap).
- [x] 2.3 Turn the whole new suite green; run the existing framework test
      suite to confirm no regression (at minimum
      `tests/test_assembly_integrity.py`, `tests/test_assertions.py`,
      `tests/test_broad_phase_culling.py`, `tests/test_meta.py`).

## 3. Documentation

- [x] 3.1 Document the assertion in `docs/testing.rst` beside
      `assertNoSolidInterference`: contract, knobs, default seeding, the
      `supports` escape hatch, and the stated exclusions (no toppling,
      friction, force balance, or lateral restraint).

## 4. ADR and records

- [x] 4.1 After implementation is green, extract one ADR under
      `docs/adrs/TEST-FRAMEWORK/` for the support-graph decision (drop test
      over proximity, transitive grounding, lowest-extent default seeds,
      declared `supports` edges), update `docs/adrs/README.md`, and update
      `docs/architecture.md`'s test-framework section.
