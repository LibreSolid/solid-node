## 1. Red-first tests

- [ ] 1.1 Create `tests/test_stl_node.py` with a module docstring
  stating the invariant: a committed STL is a first-class part —
  admitted honestly, selected explicitly, corrected in code — and its
  artifact is the node's own. Build fixture helpers that author simple
  CadQuery nodes, export their STLs into the test project, and define
  `StlNode` subclasses wrapping them (round-trip pattern, design D7).
- [ ] 1.2 Write failing tests for source declaration and freshness:
  file resolves relative to the wrapper module; missing `stl_source`
  raises naming the class; editing the `.stl` invalidates; editing the
  wrapper `.py` (e.g. its `adjust`) invalidates (D2).
- [ ] 1.3 Write failing tests for artifact materialization: round-trip
  equivalence vs the originating CadQuery part (volume, bounding box,
  near-zero manifold3d boolean difference); binary output; current
  artifact not rewritten (mock the writer and assert not called);
  missing artifact regenerates; artifact back-stamped so
  `generate_stl()` launches no OpenSCAD (patch `require_openscad`
  with `side_effect=AssertionError`, as `tests/test_openscad_dependency.py`
  does for JScad).
- [ ] 1.4 Write failing tests for the watertight gate: non-watertight
  fixture raises naming file and defect with no artifact written;
  `require_watertight = False` admits it; gate judges the post-`adjust`
  selected body.
- [ ] 1.5 Write failing tests for multi-body packs: a three-body
  fixture with distinct centroids; unset `body` raises with count and
  per-body inventory (index, centroid, bbox, volume); `body = 0` and
  `body = 2` yield distinct artifacts each holding only its component
  in file coordinates; single-body file needs no `body`; out-of-range
  `body` raises the inventory error; ordering follows the centroid
  (x, y, z) rule regardless of `mesh.split()` internal order.
- [ ] 1.6 Write failing tests for `adjust`: a scaling hook reaches the
  artifact (volume reflects it); a node without the hook imports
  verbatim.
- [ ] 1.7 Write failing adapter-contract tests: `exact` is False and
  `shape()` raises (uninitialized-instance pattern in
  `tests/test_exact_geometry.py`); `StlNode` is `isinstance`-distinct
  from every other adapter; the MRO backend walk resolves it to no
  mesh-rendering backend; a `FusionNode` over an `StlNode` plus an
  exact leaf reports not exact and unions through the mesh path.
- [ ] 1.8 Run the new test module and record the red evidence (every
  test fails for want of `StlNode`, not for fixture bugs).

## 2. Implementation

- [ ] 2.1 Implement `solid_node/node/adapters/stl.py`: `StlNode(LeafNode)`
  with `stl_source`, `body`, `require_watertight = True`,
  `namespace = None`; `__init__` resolves the source against the
  wrapper module directory, validates the declaration, calls
  `super().__init__()`, then extends `self.files` with
  `source_closure(<wrapper module file>)` (D2); `get_source_file()`
  returns the resolved `.stl`; `render()` returns `self`.
- [ ] 2.2 Implement materialization in `as_scad()` (D3): up-to-date
  short-circuit; trimesh load with `force='mesh'`; component split and
  centroid-ordered selection with the inventory error (D5); optional
  `adjust` application (D6); watertight gate on the final mesh (D4);
  binary export via temp-file-then-rename; back-stamp with
  `os.utime(..., ns=(time.time_ns(), self.mtime_ns))`; return
  `import_stl(self.local_stl)`.
- [ ] 2.3 Export `StlNode` from `solid_node/node/__init__.py`.
- [ ] 2.4 Run the full framework test suite; make the new module green
  without disturbing existing tests.

## 3. Representative caller

- [ ] 3.1 Add a meta-project (or equivalent end-to-end) fixture
  assembling two `StlNode` parts with placement operations, proving
  the launcher-visible path: assemble, artifact generation, SCAD
  import of the materialized artifacts.
- [ ] 3.2 Verify the fusion path end to end once: a `FusionNode`
  subtracting a primitive from an `StlNode` part builds through the
  OpenSCAD mesh union (the design-a-piece-that-fits case).

## 4. Documentation and architecture record

- [ ] 4.1 Add the STL leaf kind to `docs/leaf-nodes.rst`: declaration,
  freshness including wrapper tracking, watertight gate and escape
  hatch, pack selection and the inventory error, `adjust`, and an
  honest statement of the faceted-fusion cost and the mesh-only
  doctrine.
- [ ] 4.2 Update the adapter roster in `docs/architecture.md`.
- [ ] 4.3 Extract ADR(s) for the accepted architectural choices —
  wrapper-module source-set extension and the mesh-import admission
  doctrine (fail-fast gate, pack selection, adjust-not-knobs,
  mesh-only) — into `docs/adrs/`, update the ADR index, and link the
  change.

## 5. Completion

- [ ] 5.1 Sync delta specs to the baseline specs and archive the
  change (OpenSpec sync + archive workflows).
- [ ] 5.2 Run final full test suite and `openspec validate`; confirm
  the two-commit cycle shape before the completion commit.
