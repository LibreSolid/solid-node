## 1. Red evidence first

- [ ] 1.1 Add a `tests/meta_project/` fixture holding two `CadQueryNode`
      solids at a zero-clearance round fit with one rotated relative to the
      other (a shaft in a bore of equal diameter, rotated ~7°), asserting
      `assertNoSolidInterference`. Confirm it FAILS today with a small
      positive volume, and record the measured volume in the task notes — this
      is the contract the cycle turns green.
- [ ] 1.2 Add a red fixture for the inverse direction: two exact solids with a
      real interference smaller than one facet chord, asserting
      `assertNoSolidInterference` must fail. Confirm the current behaviour and
      record it, so the exact path is shown to be stricter and not merely
      looser.
- [ ] 1.3 Add a framework test asserting `exact` on one instance of each leaf
      adapter and on a fusion of each kind. Confirm it fails (no property yet).

## 2. Exactness capability

- [ ] 2.1 Add the read-only `exact` property to `AbstractBaseNode`
      (`solid_node/node/base.py`), defaulting to False.
- [ ] 2.2 Make it type-derived on the leaf adapters: True on `CadQueryNode`
      (`solid_node/node/adapters/cadquery.py`), False on `Solid2Node`,
      `OpenScadNode`, `JScadNode`.
- [ ] 2.3 Compose it on `InternalNode` (`solid_node/node/internal.py`) as
      all-children, raising when children have not been linked yet. Verify the
      raise with an unassembled `FusionNode` of `Solid2Node` leaves, which
      would otherwise report True from an empty collection.
- [ ] 2.4 Turn 1.3 green.

## 3. Exact geometry accessor and artifact

- [ ] 3.1 Add `shape()` to `CadQueryNode`, returning the rendered CadQuery
      object's OCCT shape in the node's local frame, several solids as one
      compound. Raise on any node whose `exact` is False, naming the node.
- [ ] 3.2 Add the `.brep` path to the artifact basenames in
      `AbstractBaseNode.__init__`, alongside `.scad`/`.stl`.
- [ ] 3.3 Write the `.brep` where `CadQueryNode` already writes its STL, under
      the same not-up-to-date guard and the same `os.utime` mtime stamping.
- [ ] 3.4 Add a module-level shape cache keyed on `(brep_file, mtime)` with
      stale-entry eviction, in the shape of `cached_base_mesh` and
      `_cached_manifold`; have `shape()` read through it.
- [ ] 3.5 Require the `.brep` in `LeafNode._render_can_be_skipped`
      (`solid_node/node/leaf.py`) and in `Builder._artifacts_are_current`
      (`solid_node/core/builder.py`) for exact nodes only.
- [ ] 3.6 Spare `.brep` in `Builder._sweep_unreferenced_artifacts` beside
      `.scad`. Verify a build of exact nodes leaves its `.brep` files in place
      and its `viewer.json` names none of them.
- [ ] 3.7 Verify a rebuilt artifact evicts the shape cached under its previous
      mtime.

## 4. Exact composition of a fusion

- [ ] 4.1 Add `shape()` to `FusionNode` (`solid_node/node/fusion.py`) as the
      OCCT fuse of children's shapes, each placed by the operations
      positioning it within the fusion. Cover the exactly-coincident-face case
      (shaft fused into an equal-diameter bore) with a test requiring one
      solid.
- [ ] 4.2 Produce an exact fusion's `.stl` by tessellating its own fuse, in
      process, at the same deflection `CadQueryNode` uses for leaf export.
      Stamp the mtime as other producers do; do not raise `StlRenderStart`.
- [ ] 4.3 Verify a fusion with any non-exact descendant still renders through
      the OpenSCAD subprocess protocol unchanged.
- [ ] 4.4 Verify `build_stls()` completes for an exact fusion without waiting
      on a render job for that node, and that the builder's currency and
      publication checks are satisfied.

## 5. Exact routing in the assertions

- [ ] 5.1 Add the exact tier to `_intersection_stats` in `solid_node/test.py`:
      when both nodes are exact, place each node's `shape()` by its composed
      matrix (`gp_Trsf.SetValues` from the existing `_compose_world_matrix` /
      `_compose_solid_matrix`) and intersect through the kernel. Report empty
      when the result contains no `TopAbs_SOLID`; otherwise sum the volumes of
      the solids it contains.
- [ ] 5.2 Keep the AABB broad phase ahead of every path, unchanged.
- [ ] 5.3 Raise on a kernel operation that reports not-done or errors, naming
      both nodes. Add a test proving no mesh verdict is produced in its place.
- [ ] 5.4 Route `assertIntersectVolumeAbove` and `assertIntersectVolumeBelow`
      through `_intersection_stats` instead of their own
      `node1.mesh.intersection(...)`. Add a test that they cannot disagree
      with `assertNotIntersecting` on the same pair.
- [ ] 5.5 Route `assertNoSolidInterference` candidate evaluation through the
      exact path for exact pairs, keeping `_placed_assembly_solids` and the
      spatial index otherwise unchanged. Verify a mixed assembly evaluates
      each pair by what it has.
- [ ] 5.6 Turn 1.1 green and confirm 1.2 still fails as specified.
- [ ] 5.7 Leave `assertInside`, `assertClose` and `assertFar` untouched; add a
      test pinning that they behave identically for exact and faceted nodes.

## 6. Connectivity on the exact path

- [ ] 6.1 Make `assertNoDisconnectedSolids` count solids in an exact solid's
      shape, keeping the STL split for non-exact solids. Verify with an exact
      solid comprising two disjoint solids.
- [ ] 6.2 Make `assertJoined` fuse the two shapes in the enclosing-solid frame
      and require one solid, taking the weld volume from their exact
      intersection; keep the trimesh union path for non-exact nodes. Verify
      the existing same-solid guard, tangential-contact and
      `min_weld_volume` contracts all still hold on both paths.

## 7. The epsilon rule

- [ ] 7.1 Have `_intersection_stats` report which path produced a verdict so
      callers can tell exact from faceted.
- [ ] 7.2 In `assertBlockedBeyond`, `assertFreeWithin` and
      `assertNoPairwiseIntersections`, ignore `volume_epsilon` for a
      comparison that routed exact, and warn naming the assertion when an
      epsilon was supplied and every comparison in that call routed exact.
- [ ] 7.3 Verify no warning is emitted, and the epsilon stays live, when any
      comparison in the call routed faceted.
- [ ] 7.4 Verify the ignored epsilon is verdict-neutral: a real block and a
      flush contact reach the same verdicts with and without it on the exact
      path.

## 8. Validating callers

- [ ] 8.1 Run the full framework suite plus `tests/test_meta.py`. All green.
- [ ] 8.2 Build and test `projects/v8-engine` (`root:Engine`). Record the
      whole-assembly interference timing per instant against the 6.15 s
      pre-change baseline, and report any test whose verdict changed, with the
      reason.
- [ ] 8.3 Build and test `projects/snowman` (`root.snowman:Snowman`), the one
      CadQuery project with a `FusionNode`. Compare the fused STL produced by
      the OCCT fuse against the CGAL one — volume, bounds, watertightness,
      body count — and report it as equivalent-or-better. Record the new
      printed-piece id for the fused solid.
- [ ] 8.4 Build and test one `Solid2Node` project (`projects/snowman-3` or
      `projects/dutch-windmill-3`) and confirm nothing changed: no `.brep`
      written, OpenSCAD still invoked, verdicts identical.

## 9. Records

- [ ] 9.1 Extract ADRs for the two architectural decisions the implementation
      confirms: exactness as a derived per-node capability with a
      representation-level accessor, and exact composition replacing mesh
      union inside a fusion. Update `docs/adrs/README.md`.
- [ ] 9.2 Update `docs/architecture.md` where the synthesis changed.
- [ ] 9.3 Note in the change record that ADR-004's accepted cost ("OpenSCAD's
      CSG limitations prevent using advanced NURBS/BREP features from
      CadQuery") is partially addressed here, and fully only by the following
      cycle.
