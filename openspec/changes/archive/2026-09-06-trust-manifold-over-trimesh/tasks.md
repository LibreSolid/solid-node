## 1. Red

- [x] 1.1 Rewrite `WatertightValidationTest` in `tests/test_manifold_cache.py`: the holey box raises `ValueError` naming the file and the engine status; a mesh built with an edge shared by four faces (two boxes sharing one edge, exported as one STL) is compared with no error and reaches the engine's verdict.
- [x] 1.2 Add tests that an exact-kernel comparison of two exact solids, and an `assertNoSolidInterference` sweep whose candidate pairs never route faceted, complete with an STL the engine would refuse on one solid.
- [x] 1.3 Add a `write_stl` test in `tests/test_exact_geometry.py`: a shape whose `exportStl` writes a degenerate triangle yields an artifact without it and with no unreferenced vertex.
- [x] 1.4 Run the new tests and confirm each fails for the intended reason on the base.

## 2. Green

- [x] 2.1 `solid_node/test.py`: drop the `is_volume` gate from `_cached_local_bounds`; judge `manifold.status()` in `_cached_manifold` and `_flexible_manifold`, raising `ValueError` with file (or node), status and trimesh watertightness, without caching the refused Manifold.
- [x] 2.2 `solid_node/exact.py`: `write_stl` always removes degenerate triangles; drop the keyword and its use in `solid_node/node/fusion.py`.
- [x] 2.3 Framework suite green; run snappy-reprap's suite from the bench with the framework's `assertNotIntersecting` on one four-face-edge pair as the caller check.

## 3. Records

- [x] 3.1 ADR in `docs/adrs/TEST-FRAMEWORK/`: the mesh engine's own status is the admissibility verdict; amends ADR-029; update `docs/adrs/README.md` and `docs/architecture.md`.
- [x] 3.2 Sync delta specs, archive the change, final validation.
