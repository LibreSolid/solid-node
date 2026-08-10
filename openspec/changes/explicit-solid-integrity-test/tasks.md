## 1. One home for the solid traversal

- [ ] 1.1 Red: `_topmost_rigid_nodes` is importable from `solid_node.node.base`
      and yields the outer fusion only for an assembly holding a fusion of
      leaves and a nested fusion; a rigid root is its own topmost rigid node.
- [ ] 1.2 Move `_topmost_rigid_nodes` from `core/builder.py:31` to
      `node/base.py`, beside `_topmost_rigid_ancestor`.
- [ ] 1.3 Green 1.1; confirm no remaining caller imports it from the builder.

## 2. The explicit assertion

- [ ] 2.1 Red: `assertNoDisconnectedSolids(node)` fails naming the solid and
      the count when a topmost rigid node's STL has more than one component.
- [ ] 2.2 Red: it passes when every selected solid is one component.
- [ ] 2.3 Red: it stops at an enclosing fusion — fragmented rigid ingredients
      joined into one body by the fusion are not rejected.
- [ ] 2.4 Red: called on a subtree, it checks only that subtree's solids.
- [ ] 2.5 Red — the originating defect, restated at the assertion: a solid whose
      placement an assembly animates is checked without resolving any operation
      value. Assert no operation matrix is composed.
- [ ] 2.6 Implement `assertNoDisconnectedSolids` in `solid_node/test.py`, in the
      Connectivity section beside `assertJoined`: traverse via
      `_topmost_rigid_nodes`, read `_cached_base_mesh(node.stl_file)`, split
      with `only_watertight=False`, require exactly 1, fail fast on the first
      violation.
- [ ] 2.7 Green 2.1–2.5.

## 3. Remove implicit build verification

- [ ] 3.1 Red: a build whose topmost rigid node's STL has two components
      publishes normally and writes no error, on BOTH publication paths.
- [ ] 3.2 Remove `_verify_solid_bodies` (`builder.py:392`) and its call sites
      (`:266`, `:280`).
- [ ] 3.3 Remove the now-unused `_cached_base_mesh` import from the builder.
- [ ] 3.4 Remove or convert the builder-lifecycle tests asserting publication
      rejects a fragmented solid (`tests/test_builder_lifecycle.py`), keeping
      the traversal cases that moved to 1.1.
- [ ] 3.5 Keep `_artifacts_are_current` and the incomplete-render guard; retest
      them on manifest-integrity grounds — publishing must not reference an
      absent STL — with no reference to connectivity.
- [ ] 3.6 Green 3.1; full builder lifecycle suite green.

## 4. End-to-end through the runner

- [ ] 4.1 Meta-project fixture pair in `tests/meta_project/`, in the style of
      `welded`/`unwelded`: one whole solid (green) and one fragmented solid
      (red), each with a companion test declaring the assertion.
- [ ] 4.2 Red fixture: `solid test` exits 1, counts exactly one failed test, and
      names the solid and its body count.
- [ ] 4.3 Green fixture: `solid test` exits 0 and counts the test as passed.
- [ ] 4.4 Prove the negative: the same fragmented fixture with the declaration
      removed adds no test to the count and no failure — `solid test` is silent
      about connectivity nobody asked about.
- [ ] 4.5 Wire 4.1–4.4 into `tests/test_meta.py`.

## 5. Scaffold the first test

- [ ] 5.1 Red: `solid new <name>` creates `<name>/<name>/test_<name>.py`
      containing a `TestCase` whose single test calls
      `assertNoDisconnectedSolids(self.node)`.
- [ ] 5.2 Add the template under `solid_node/manager/templates/project/`, with
      the same `DemoProject` class-name substitution `new.py` already performs.
- [ ] 5.3 Emit it from `manager/new.py` beside the node module, named from the
      normalized package slug so module and companion always match.
- [ ] 5.4 Red: `solid test` in a freshly scaffolded project discovers and passes
      exactly one test, with no new loader convention introduced.
- [ ] 5.5 Green 5.1 and 5.4; confirm `solid build` on the same project does not
      execute the generated test.
- [ ] 5.6 Update the scaffold's printed next steps if they change.

## 6. Records

- [ ] 6.1 Sync the four spec deltas into `openspec/specs/`.
- [ ] 6.2 Amend ADR-039 with a dated section: supersede "Verification stays in
      the builder, on both publication paths"; retain the topmost-rigid-node
      unit, the local-STL measurement, and the connectivity/collision table.
      Link this change.
- [ ] 6.3 Update `docs/architecture.md` where the synthesis claimed publication
      guarantees connectivity.
- [ ] 6.4 Document `assertNoDisconnectedSolids` in `docs/testing.rst` beside
      `assertJoined` and the adjacency sweep, including the connectivity vs
      collision framing and that it is never run automatically.
- [ ] 6.5 Correct the `New command` requirement to the shipped scaffold layout
      and its new companion test.
- [ ] 6.6 Run the full framework suite and OpenSpec validation; archive.
