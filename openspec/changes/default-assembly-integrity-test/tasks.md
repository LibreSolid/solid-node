## 1. Topmost-rigid assembly contract

- [ ] 1.1 Red: `assertNoSolidInterference(node)` selects only topmost rigid
      nodes, stops at an outer fusion, and scopes selection to the supplied
      subtree.
- [ ] 1.2 Red: a rigid leaf root and a rigid fusion root pass without loading
      geometry or invoking any Boolean operation.
- [ ] 1.3 Red: an animated nested assembly passes at a keyframe where its
      solids are apart and fails at a keyframe where they overlap, proving the
      assertion consumes the runner's current world placement without setting
      time itself.
- [ ] 1.4 Add `assertNoSolidInterference` to `solid_node/test.py` using the
      shared `_topmost_rigid_nodes` traversal and freshly composed world
      matrices; green 1.1–1.3.

## 2. Global same-kernel volume certificate

- [ ] 2.1 Red: separated transformed solids whose summed and union volumes
      differ by floating-point ulps do not fail solely on exact float
      inequality.
- [ ] 2.2 Red: positive overlap produces a positive assembly deficit; triple
      overlap and containment cannot cancel it.
- [ ] 2.3 Red: inputs, individual volumes, batch union, and union volume stay
      in the cached Manifold representation with no Trimesh result round trip
      or mixed volume source.
- [ ] 2.4 Implement stable same-kernel volume summation, lazy world transforms,
      direct Manifold batch union, and a private scale-aware numerical
      uncertainty classification; green 2.1–2.3.
- [ ] 2.5 Red: the public assertion signature has no `volume_epsilon` or other
      permitted-overlap parameter.

## 3. Spatial candidate verification and diagnostics

- [ ] 3.1 Red: the candidate index emits only world-AABB-overlapping topmost
      rigid pairs in a sparse assembly and does not construct
      `itertools.combinations` or visit every possible pair.
- [ ] 3.2 Implement dependency-free sweep-and-prune candidate generation with
      each conservative world AABB computed once.
- [ ] 3.3 Red: a positive-volume candidate intersection fails naming both
      topmost rigid solids and the measured volume; search stops after the
      first offending pair.
- [ ] 3.4 Red: empty and non-empty zero-volume boundary intersections pass,
      while every positive candidate volume reported by Manifold fails without
      a public epsilon.
- [ ] 3.5 Red: a volume deficit inside numerical uncertainty invokes candidate
      verification instead of passing by threshold; a clearly positive global
      deficit with no reconcilable candidate fails with an aggregate numerical
      inconsistency diagnostic.
- [ ] 3.6 Wire the candidate path into `assertNoSolidInterference`; green
      3.1–3.5 and retain cached-Manifold watertightness failures.

## 4. Deprecate the leaf-pair sweep

- [ ] 4.1 Red: calling `assertNoPairwiseIntersections` emits a captured
      deprecation warning at the caller with migration guidance naming
      `assertNoSolidInterference` and the topmost-rigid scope difference.
- [ ] 4.2 Add the warning without changing the deprecated method's leaf
      traversal, `volume_epsilon` argument, failure messages, or historical
      red/green fixture verdicts.
- [ ] 4.3 Green the existing adjacency, volume-epsilon, AABB, and Manifold
      regression suites alongside 4.1.

## 5. End-to-end assembly evidence

- [ ] 5.1 Add meta-project green fixtures for a single rigid root, separated
      nested topmost solids, and exact boundary contact, each declaring
      `test_assembly_integrity`.
- [ ] 5.2 Add a red animated-assembly fixture whose declared test passes at one
      instant and fails at another, naming the offending topmost rigid pair and
      positive volume.
- [ ] 5.3 Wire the fixtures through `solid test` in `tests/test_meta.py` and
      prove ordinary counting, per-instant dots, `--failfast`, and checkpoint
      restoration remain runner-owned.

## 6. Scaffold both initial safety tests

- [ ] 6.1 Red: `solid new <name>` generates a companion case containing
      `test_solid_integrity` and `test_assembly_integrity` in that order, with
      calls to `assertNoDisconnectedSolids(self.node)` and
      `assertNoSolidInterference(self.node)` respectively.
- [ ] 6.2 Update the project test template and exact scaffold expectations;
      keep both tests visible ordinary source with no loader or registration
      change.
- [ ] 6.3 Red: `solid test` in a freshly scaffolded leaf project discovers,
      counts, and passes exactly two tests at the default instant; `solid
      build`, `develop`, and `snapshot` do not execute them.
- [ ] 6.4 Green 6.1 and 6.3.

## 7. Performance and regression validation

- [ ] 7.1 Add deterministic instrumentation proving sparse candidate work is
      output-sensitive rather than quadratic in selected-solid count.
- [ ] 7.2 Benchmark representative separated and interfering assemblies across
      increasing part and triangle counts, comparing the combined batch-union
      plus candidate path with the deprecated sweep; record measured evidence
      and any adverse geometry rather than claiming a universal complexity.
- [ ] 7.3 Run the focused assertion, connectivity, manager-new, Manifold/AABB,
      animation, and meta-project suites.
- [ ] 7.4 Run the full framework suite from the isolated worktree.

## 8. Documentation and durable records

- [ ] 8.1 Update `docs/testing.rst` and API documentation with the two initial
      integrity tests, topmost-rigid/world-keyframe semantics, zero-volume
      contact behavior, absence of a public epsilon, production-margin
      distinction, animation decorators, and old-method deprecation.
- [ ] 8.2 After implementation evidence confirms the design, record the
      accepted assembly-integrity decision in the appropriate TEST-FRAMEWORK
      ADR (new or amended as the final architecture warrants), update
      `docs/adrs/README.md`, and rewrite the affected test-framework synthesis
      in `docs/architecture.md`.
- [ ] 8.3 Sync the `test-framework` and `cli` delta specs into their baselines,
      validate OpenSpec and the final framework state, and archive the change.
