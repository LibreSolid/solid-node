## 1. Red evidence first

- [x] 1.1 Add a `tests/meta_project/` fixture holding two `CadQueryNode`
      solids at a zero-clearance round fit with one rotated relative to the
      other (a shaft in a bore of equal diameter, rotated ~7°), asserting
      `assertNoSolidInterference`. Confirm it FAILS today with a small
      positive volume, and record the measured volume in the task notes — this
      is the contract the cycle turns green.
      Baseline: the rotated d=10 shaft in the d=10 bore failed with a faceted
      intersection volume of `0.12080618894740745 mm³`.
- [x] 1.2 Add a red fixture for the inverse direction: two exact solids with a
      real interference smaller than one facet chord, asserting
      `assertNoSolidInterference` must fail. Confirm the current behaviour and
      record it, so the exact path is shown to be stricter and not merely
      looser.
      Baseline: two r=5 cylinders whose axes are `9.999 mm` apart, with one
      tessellation rotated 7°, passed the faceted assertion despite their
      real `0.001 mm` radial overlap.
- [x] 1.3 Add a framework test asserting `exact` on one instance of each leaf
      adapter and on a fusion of each kind. Confirm it fails (no property yet).
      Baseline: all three framework tests failed with `AttributeError` on the
      missing `exact` property.

## 2. Exactness capability

- [x] 2.1 Add the read-only `exact` property to `AbstractBaseNode`
      (`solid_node/node/base.py`), defaulting to False.
- [x] 2.2 Make it type-derived on the leaf adapters: True on `CadQueryNode`
      (`solid_node/node/adapters/cadquery.py`), False on `Solid2Node`,
      `OpenScadNode`, `JScadNode`.
- [x] 2.3 Compose it on `InternalNode` (`solid_node/node/internal.py`) as
      all-children, raising when children have not been linked yet. Verify the
      raise with an unassembled `FusionNode` of `Solid2Node` leaves, which
      would otherwise report True from an empty collection.
- [x] 2.4 Turn 1.3 green.

## 3. Exact geometry accessor and artifact

- [x] 3.1 Add `shape()` to `CadQueryNode`, returning the rendered CadQuery
      object's OCCT shape in the node's local frame, several solids as one
      compound. Raise on any node whose `exact` is False, naming the node.
- [x] 3.2 Add the `.brep` path to the artifact basenames in
      `AbstractBaseNode.__init__`, alongside `.scad`/`.stl`.
- [x] 3.3 Write the `.brep` where `CadQueryNode` already writes its STL, under
      the same not-up-to-date guard and the same `os.utime` mtime stamping.
- [x] 3.4 Add a module-level shape cache keyed on `(brep_file, mtime)` with
      stale-entry eviction, in the shape of `cached_base_mesh` and
      `_cached_manifold`; have `shape()` read through it.
- [x] 3.5 Require the `.brep` in `LeafNode._render_can_be_skipped`
      (`solid_node/node/leaf.py`) and in `Builder._artifacts_are_current`
      (`solid_node/core/builder.py`) for exact nodes only.
- [x] 3.6 Spare `.brep` in `Builder._sweep_unreferenced_artifacts` beside
      `.scad`. Verify a build of exact nodes leaves its `.brep` files in place
      and its `viewer.json` names none of them.
- [x] 3.7 Verify a rebuilt artifact evicts the shape cached under its previous
      mtime.

## 4. Exact composition of a fusion

- [x] 4.1 Add `shape()` to `FusionNode` (`solid_node/node/fusion.py`) as the
      OCCT fuse of children's shapes, each placed by the operations
      positioning it within the fusion. Cover the exactly-coincident-face case
      (shaft fused into an equal-diameter bore) with a test requiring one
      solid.
- [x] 4.2 Produce an exact fusion's `.stl` by tessellating its own fuse, in
      process, at the same deflection `CadQueryNode` uses for leaf export.
      Stamp the mtime as other producers do; do not raise `StlRenderStart`.
- [x] 4.3 Verify a fusion with any non-exact descendant still renders through
      the OpenSCAD subprocess protocol unchanged.
- [x] 4.4 Verify `build_stls()` completes for an exact fusion without waiting
      on a render job for that node, and that the builder's currency and
      publication checks are satisfied.

## 5. Exact routing in the assertions

- [x] 5.1 Add the exact tier to `_intersection_stats` in `solid_node/test.py`:
      when both nodes are exact, place each node's `shape()` by its composed
      matrix (`gp_Trsf.SetValues` from the existing `_compose_world_matrix` /
      `_compose_solid_matrix`) and intersect through the kernel. Report empty
      when the result contains no `TopAbs_SOLID`; otherwise sum the volumes of
      the solids it contains.
- [x] 5.2 Keep the AABB broad phase ahead of every path, unchanged.
- [x] 5.3 Raise on a kernel operation that reports not-done or errors, naming
      both nodes. Add a test proving no mesh verdict is produced in its place.
- [x] 5.4 Route `assertIntersectVolumeAbove` and `assertIntersectVolumeBelow`
      through `_intersection_stats` instead of their own
      `node1.mesh.intersection(...)`. Add a test that they cannot disagree
      with `assertNotIntersecting` on the same pair.
- [x] 5.5 Route `assertNoSolidInterference` candidate evaluation through the
      exact path for exact pairs, keeping `_placed_assembly_solids` and the
      spatial index otherwise unchanged. Verify a mixed assembly evaluates
      each pair by what it has.
- [x] 5.6 Turn 1.1 green and confirm 1.2 still fails as specified.
- [x] 5.7 Leave `assertInside`, `assertClose` and `assertFar` untouched; add a
      test pinning that they behave identically for exact and faceted nodes.

## 6. Connectivity on the exact path

- [x] 6.1 Make `assertNoDisconnectedSolids` count solids in an exact solid's
      shape, keeping the STL split for non-exact solids. Verify with an exact
      solid comprising two disjoint solids.
- [x] 6.2 Make `assertJoined` fuse the two shapes in the enclosing-solid frame
      and require one solid, taking the weld volume from their exact
      intersection; keep the trimesh union path for non-exact nodes. Verify
      the existing same-solid guard, tangential-contact and
      `min_weld_volume` contracts all still hold on both paths.

## 7. The epsilon rule

- [x] 7.1 Have `_intersection_stats` report which path produced a verdict so
      callers can tell exact from faceted.
- [x] 7.2 In `assertBlockedBeyond`, `assertFreeWithin` and
      `assertNoPairwiseIntersections`, ignore `volume_epsilon` for a
      comparison that routed exact, and warn naming the assertion when an
      epsilon was supplied and every comparison in that call routed exact.
- [x] 7.3 Verify no warning is emitted, and the epsilon stays live, when any
      comparison in the call routed faceted.
- [x] 7.4 Verify the ignored epsilon is verdict-neutral: a real block and a
      flush contact reach the same verdicts with and without it on the exact
      path.

## 8. Validating callers

- [x] 8.1 Run the full framework suite plus `tests/test_meta.py`. All green.
      Final result: 529 tests passed with 24 subtests; the suite includes the
      exact meta fixtures through `tests/test_meta.py`.
- [x] 8.2 Build and test `projects/v8-engine` (`root:Engine`). Record the
      whole-assembly interference timing per instant against the 6.15 s
      pre-change baseline, and report any test whose verdict changed, with the
      reason.
      Result: 31/31 project tests passed. The three exact all-leaf adjacency
      instants measured 14.342, 14.461 and 14.527 s (2.33–2.36× the 6.15 s
      faceted baseline). No project-test verdict changed; supplied
      `volume_epsilon=1e-6` values now warn and are ignored on all-exact calls.
- [x] 8.3 Build and test `projects/snowman` (`root.snowman:Snowman`), the one
      CadQuery project with a `FusionNode`. Compare the fused STL produced by
      the OCCT fuse against the CGAL one — volume, bounds, watertightness,
      body count — and report it as equivalent-or-better. Record the new
      printed-piece id for the fused solid.
      Result: 7/7 project tests passed. CGAL -> exact: volume
      148819.191868121 -> 148824.06642339742 mm³; bounds
      [[-27.996439,-27.979385,0],[27.992195,27.979385,122.64]] ->
      [[-27.991949,-27.974897,0],[27.993752,27.974897,122.64]];
      watertight true -> true; bodies 1 -> 1; faces 21,140 -> 20,024.
      The result is equivalent within tessellation deflection and retains the
      one-body contract with fewer faces. Piece id changed from
      `21591f853132` to `d0a600876a4c`.
- [x] 8.4 Build and test one `Solid2Node` project (`projects/snowman-3` or
      `projects/dutch-windmill-3`) and confirm nothing changed: no `.brep`
      written, OpenSCAD still invoked, verdicts identical.
      Result: `snowman-3` passed 3/3 project tests; OpenSCAD subprocess output
      was observed for leaves and its fusion, and the isolated build contained
      no `.brep` files.

## 9. Records

- [x] 9.1 Extract ADRs for the two architectural decisions the implementation
      confirms: exactness as a derived per-node capability with a
      representation-level accessor, and exact composition replacing mesh
      union inside a fusion. Update `docs/adrs/README.md`.
- [x] 9.2 Update `docs/architecture.md` where the synthesis changed.
- [x] 9.3 Note in the change record that ADR-004's accepted cost ("OpenSCAD's
      CSG limitations prevent using advanced NURBS/BREP features from
      CadQuery") is partially addressed here, and fully only by the following
      cycle.
      ADR-044 records that exact composition and assertions partially address
      the cost; OpenSCAD remains the faceted composition/delivery path until
      the following conditional-dependency cycle.
