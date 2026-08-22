# Tasks: static equilibrium in `assertAssemblySupported`

## 1. Red-first fixtures and tests

- [x] 1.1 Extend `tests/meta_project/` in the existing pattern with
      equilibrium fixtures: one-end-supported horizontal bar (reaches ground,
      must fail on torque), the same bar with a second end support (must
      pass), offset stack whose cumulative centre of mass leaves the lowest
      patch (fail) with a counterweighted variant (pass), cantilevered pin in
      a grounded block's snug hole (pass through drop+lift couple), tippy
      tall solid on the virtual floor with a squat neighbour (fail naming the
      tippy solid), boundary-exact balance for the `stability_margin`
      scenario, and a friction-dependent hold exempted through `supports`.
- [x] 1.2 Write the new tests (extend `tests/test_assembly_supported.py` or a
      sibling module) covering every delta-spec scenario that changes or adds
      behavior: both bar verdicts with the failure naming the bar and torque;
      offset stack and counterweight; pin couple; virtual-floor tippy seed;
      explicit `ground` anchoring (no virtual floor); `supports` wrench
      exemption; `stability_margin` positive-vs-default verdicts and the
      negative-margin error; lift sweep adding contacts but never
      support-graph edges; broad-phase culling covering the lift sweep;
      deterministic verdict across repeated runs. Run them and confirm each
      fails red for the right reason before implementing.

## 2. Implementation

- [x] 2.1 Contact extraction in `solid_node/test.py`: mesh each detected
      drop/lift displaced intersection from the placed Manifolds, classify
      intersection faces to the supporter's boundary by nearest surface, and
      emit deduplicated contact points with outward normals on the
      supporter's undisplaced surface; apply `stability_margin` shrink toward
      each patch centroid.
- [x] 2.2 The lift sweep: reuse `_dropped_assembly_solids`/`_support_candidates`
      with the negated offset to detect overhead-restraint contacts, feeding
      contact extraction only, never `edges`.
- [x] 2.3 Anchoring: with `ground=None`, build the virtual floor slab in the
      gravity frame (top plane at the assembly's furthest gravity extent,
      lateral bounds plus margin) as an extra resting record for contact
      detection and the sole anchored body; with explicit `ground`, anchor
      exactly the resolved solids and skip the floor.
- [x] 2.4 The equilibrium program: per non-anchored solid, force and torque
      balance about its centre of mass (placed faceted mesh, uniform unit
      density, unit gravity); variables `f_k ≥ 0` per contact point with
      reactions on non-anchored supporters, plus a six-component free wrench
      per declared `supports` edge; solve the L1-relaxed feasibility with
      `scipy.optimize.linprog(method='highs')`; per-body tolerances scaled by
      weight (force rows) and weight times bounding-box diagonal (torque
      rows).
- [x] 2.5 Wire the phase into `assertAssemblySupported` after reachability,
      with the diagnostic failure naming each unbalanced solid and the
      failing balance kind, pointing at `supports=`; fail loudly when a
      needed body's edges yield no extractable contact interface; validate
      `stability_margin >= 0`; update the docstring's claims and exclusions.
- [x] 2.6 Turn the whole new suite green; re-run the existing support suite
      (`tests/test_assembly_supported.py`, `tests/test_meta.py`) and rebalance
      any fixture that previously passed only through the reachability blind
      spot, recording each such change as evidence; then run the wider
      framework suite (`tests/test_assembly_integrity.py`,
      `tests/test_assertions.py`, `tests/test_broad_phase_culling.py`) to
      confirm no regression.

## 3. Documentation

- [x] 3.1 Update `docs/testing.rst`'s gravity-support section and
      `docs/api-reference.rst`: the equilibrium claim, the lift sweep, virtual
      floor vs bolted `ground`, the `supports` wrench semantics,
      `stability_margin`, and the revised exclusions (friction, adhesion,
      lateral wall reactions, single-solid floor toppling, dynamics).

## 4. ADR and records

- [x] 4.1 After implementation is green, extract one ADR under
      `docs/adrs/TEST-FRAMEWORK/` for equilibrium-as-LP-feasibility (rejected
      dynamics engine and COM heuristic, frictionless conservatism, drop+lift
      contact extraction, virtual-floor anchoring, relaxed-LP diagnostics),
      link it from ADR-048's context, update `docs/adrs/README.md`, and
      update `docs/architecture.md`'s test-framework section.
