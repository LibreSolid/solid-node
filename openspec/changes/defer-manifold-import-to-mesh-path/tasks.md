## 1. Red first: prove the defect at both layers

- [ ] 1.1 Add `tests/mesh_engine_absent.py`: a helper that runs a callable in a
      subprocess whose `sys.meta_path` refuses `manifold3d` *after* `trimesh` is
      imported (trimesh treats `manifold3d` as one optional engine and copes; the
      framework is what does not). This is the honest simulation of a runtime
      with no `manifold3d` wheel, and it is how the defect reproduced at base.
- [ ] 1.2 Add `tests/test_mesh_engine_dependency.py::test_assertion_module_imports_without_the_mesh_engine`:
      import `solid_node.test` under 1.1's blocker. Record it red — expected
      `ModuleNotFoundError: No module named 'manifold3d'` raised from
      `solid_node/test.py:13`, before any assertion exists.
- [ ] 1.3 Add `tests/test_mesh_engine_dependency.py::test_exact_assembly_asserts_without_the_mesh_engine`:
      under the blocker, run `solid test tests/meta_project/exact_tight_fit.py`
      through the `tests/test_meta.py` subprocess harness and require
      `1 passed, 0 failed`, matching the recorded green verdict with the mesh
      engine present. Record it red — today the run dies at import.
- [ ] 1.4 Add `tests/test_mesh_engine_dependency.py::test_faceted_interference_names_the_missing_mesh_engine`:
      under the blocker, run a faceted `assertNoSolidInterference` fixture and
      require the failure text to name `manifold3d`, the assertion, and the
      reason. Record it red — today it fails at import with no such text.
- [ ] 1.5 Add `tests/test_mesh_engine_dependency.py::test_gravity_support_names_the_missing_mesh_engine`:
      under the blocker, run `tests/meta_project/assembly_supported_exact.py` —
      an ALL-EXACT assembly that passes today only because Manifolds are built
      for it — and require the same named error. Record it red.
- [ ] 1.6 Add `tests/test_manifold_cache.py::test_no_manifold_is_built_for_an_exact_assembly`:
      in-process, patch `solid_node.test._cached_manifold` to raise, build two
      exact fake solids with disjoint-free bounds, and require
      `assertNoSolidInterference` to pass. This is the fast unit proof of the
      "no faceted work on the exact path" property. Record it red — today it
      raises from `_solid_geometry`.
- [ ] 1.7 Add `tests/test_manifold_cache.py::test_a_mixed_assembly_builds_one_manifold_per_faceted_comparison`:
      count `_cached_manifold` calls over an assembly with one exact and one
      faceted solid and require exactly one build per solid the faceted pair
      reads, and none for a solid no faceted pair reads. Record it red.
- [ ] 1.8 Record every red transcript in the change record before implementing.

## 2. Introduce the conditional mesh-engine dependency

- [ ] 2.1 Add `solid_node/mesh_engine.py`, mirroring `solid_node/openscad.py`:
      `MeshEngineUnavailable(RuntimeError)` carrying `needed_by` and `reason`
      with a remedy, one `@lru_cache(maxsize=1)` resolver, and
      `require_mesh_engine(needed_by, reason)` returning the `(Manifold, Mesh)`
      handles.
- [ ] 2.2 Remove `from manifold3d import Manifold, Mesh` from
      `solid_node/test.py` and route `_cached_manifold` and `_virtual_floor`
      through `require_mesh_engine`, each naming its own `needed_by`/`reason`.
- [ ] 2.3 Run 1.2 green. Confirm the error text of 1.4/1.5 names the dependency,
      the operation and the reason.

## 3. Build the Manifold only where a faceted comparison reads it

- [ ] 3.1 Split the per-STL cache: add `_cached_local_bounds(stl_file)` doing the
      mtime keying, stale eviction, `cached_base_mesh` load and the
      watertightness `ValueError`, with no mesh engine. Leave `_cached_manifold`
      with its existing name, signature and `(manifold, bounds)` return so the
      existing doubles in `tests/test_manifold_cache.py` and
      `tests/test_assembly_supported.py` keep working.
- [ ] 3.2 Change `_solid_geometry` to read bounds from `_cached_local_bounds` and
      to carry what a later Manifold build needs, instead of building one.
- [ ] 3.3 Change `_place_solid` to record a deferred placed Manifold in slot 1,
      preserving the four-slot record shape every consumer unpacks.
- [ ] 3.4 Force the deferred placed Manifold at exactly its four consumers: the
      faceted branch of `_placed_intersection`, `_statics_body`, and the
      `dropped[...][1]` / `lifted[...][1]` arguments to `_interface_contacts`.
      Leave `_fast_geometry` and `_intersection_stats` untouched — they are
      reached only when at least one compared node is faceted.
- [ ] 3.5 Confirm the bounds source is unchanged for every solid, exact or
      faceted, so no candidate set, grounded seed or virtual floor moves.
- [ ] 3.6 Run 1.3, 1.6 and 1.7 green.

## 4. Prove nothing else moved

- [ ] 4.1 Run `tests/test_manifold_cache.py` in full and confirm
      `test_repeated_assertions_build_the_manifold_once` still holds: deferring
      construction must not increase the number of Manifolds built.
- [ ] 4.2 Run `tests/test_assembly_integrity.py`, `tests/test_assembly_supported.py`,
      `tests/test_broad_phase_culling.py`, `tests/test_assertions.py`,
      `tests/test_connectivity.py`, `tests/test_exact_geometry.py`.
- [ ] 4.3 Run `tests/test_meta.py` in full: every green fixture green, every
      deliberately red fixture red *with its existing message*. Pay particular
      attention to `flush_strict` / `flush_keyed_strict` (the zero-volume
      non-empty contract) and to the `assembly_supported*` family.
- [ ] 4.4 Re-run the originating reproduction end to end — an all-exact assembly
      under a genuinely absent `manifold3d` — and record the transcript beside
      the base transcript in the change record.
- [ ] 4.5 Run the full suite and compare against this cycle's recorded base
      result at `a1dd7b3`: 689 passed, 44 subtests passed, 0 failed, in 222.69s
      (`/home/asa/devel/libresolid-studio/.venv`, `manifold3d`, `build123d`
      0.10.0 and `rtree` 1.4.1 all present).

## 5. Document and complete

- [ ] 5.1 Document the conditional mesh-engine dependency where the OpenSCAD one
      is documented, naming the exact requiring paths and the all-exact
      guarantee.
- [ ] 5.2 Assess ADR need after implementation. The candidate is a
      conditional-`manifold3d` decision extending ADR-046's pattern from an
      external binary to a compiled wheel, and recording why
      `assertAssemblySupported` stays a requiring path under ADR-049. Record it
      only if the implemented design confirms it as architectural, and update
      `docs/architecture.md` if the synthesis moved.
- [ ] 5.3 Sync baseline specs and archive the change.
