# Remove-OpenSCAD-broker implementation evidence

Status: implementation, framework, Curta and OpenSCAD-free 3DPrintedClocks
acceptance validation complete; specs synchronized and change archived.

## Tested content and tools

- Framework base `5e591474b5cf54c2b41f223400d2b6ee3cbb97ae`, planning commit
  `5256319`; final measured Python-source SHA-256
  `1e353da68f895366b63233767073cffe93e38f6511ae30026b290d44c2911154`.
- Curta HEAD `d80e7bf71da130295bacc1bd72971e1029e29f9d`, with pilot-owned dirty
  changes. The tracked binary diff SHA-256 before and after both accepted runs
  was `6ece71111f17ff4fe2cad3ab174acd20d87460366e14a030e70b94a5d824fb15`.
  The two untracked inputs were `simulation/cover_fits.py`
  (`19ba545d...5874d0f`) and `simulation/tools/cover_neighbors.py`
  (`2351f9c9...b99400`). No project source was changed by this cycle.
- 3DPrintedClocks HEAD `2c456d9202a170cecebf746913a2dd749061bf9c`,
  with pilot-owned dirty changes, and the clean adjacent declared dependency
  `solid-node-mechanics` at
  `c69467f408d26ba2ee8efd7fece8d4370c8bb840`. The clock project's tracked
  binary diff SHA-256 remained
  `4b964d3e050efd208a02c3f386def17eeeaa4b7bd2a422091ff71be14ff3d38f`.
- Python 3.12.3; solidpython2 2.1.3; CadQuery 2.7.0; build123d 0.10.0;
  trimesh 4.4.9; manifold3d 3.5.2; molejo 0.2.0; pytest 9.1.1;
  OpenSCAD 2021.01 at `/usr/bin/openscad`; temporary `@jscad/cli` install for
  the integration probe.

## Red-first boundary and lifecycle evidence

The initial three-test reproducer failed at `build_stls -> trigger_stl ->
assemble -> as_scad`: native mesh fusion and both export paths constructed
SCAD before reaching native artifacts. OpenSCAD was patched to fail, making
that dependency explicit. The same tests pass after preparation was split
from presentation.

Regression coverage now includes a native leaf with no `as_scad` override;
legacy overrides on a built-in CadQuery subclass; native export with all SCAD
hooks blocked; flexible export with its snapshot hook blocked; source closure,
builder locks and retained source generations; warm native skips; old/missing
fusion recipes; missing Manifold; invalid mesh input naming the child; exact
fusion with both external engines blocked; and OpenSCAD-positive paths.

The JSCAD CLI was installed into a temporary prefix for the real subprocess
fixture. That probe exposed that the CLI selects its exporter from the final
extension and rejected the adapter's historical `.tmp` output. The native
producer now uses a private `.tmp.stl`; the actual CLI produced the 5 mm cube
fixture at 125 mm³ with bounds `[-2.5,-2.5,-2.5]..[2.5,2.5,2.5]`. Controlled
failure/source-replacement tests still prove atomic preservation.

## Faceted fusion geometry

Predeclared elementary tolerances were 1e-4 mm³ for analytic volume and 1e-5
mm for bounds, matching the 0.1 mm/rad tessellation scale without admitting a
visible dimensional change. The direct-Manifold tests cover overlapping,
contained, identical, disjoint, face-touching, edge-touching, 0.0001 mm
near-coincident and operation-transformed boxes. Volumes and bounds meet those
tolerances; expected body counts are 1,1,1,2,1,2,1,1 respectively; every output
has consistent winding. Invalid/non-manifold input is refused without repair
or OpenSCAD fallback.

OpenSCAD 2021.01 and Manifold 3.5.2 outputs were also generated independently
for those cases plus a three-box nested union. Contained, identical, disjoint,
face-touching, edge-touching, overlapping, transformed and nested cases have
zero symmetric-difference volume. The 0.0001 mm near-coincident case differs
by 3.3378601075e-06 mm³; its maximum corresponding bound difference is
8.35e-07 mm. Body count, volume, bounds and winding agree in every case;
triangulation vertex/face counts intentionally differ.

The retained old OpenSCAD/CGAL `PostedBracket` artifact has 512 vertices,
1,020 faces, volume 1125.6115653038069 mm³, bounds
`[-10,-5,-7.5]..[10,5,7.5]`, one body. The new Manifold artifact has 512
vertices, 1,028 faces, volume 1125.611631155026 mm³, identical bounds, one
body. Symmetric-difference volume is 1.1477876476985616e-05 mm³. The
6.59e-05 mm³ volume difference is 5.85e-8 relative and within the declared
tessellation comparison. The analytic matrix, nested/exact routing tests and
this real mixed imported/exact fixture supplied the acceptance evidence.

## Framework validation

Final post-archive command:

```text
PYTHONPATH=$PWD /home/asa/devel/libresolid-studio/.venv/bin/python -m pytest \
  tests -q --disable-warnings --junitxml=/tmp/remove-openscad-broker-framework-tests-final.xml
```

Result: **2,274 passed, 4 skipped, 50 warnings, 894 subtests passed in
295.09 seconds**. The skips are the opt-in browser snapshot E2E, opt-in actual
JSCAD CLI integration and two absent vendor STEP fixtures. This final run
includes the flexible-leaf classification fix and the actual-JSCAD private
temporary-suffix fix. The latter was separately exercised against the real
CLI as recorded above.

The documentation built successfully with Sphinx 9.1.0 and
sphinx-rtd-theme 3.1.0. It retained six known non-fatal warnings, including
two missing generated example export directories; no changed documentation
source failed. `openspec validate --all --strict` passed all 32 baseline
specifications after synchronization and archival.

## Curta result and actual memory

Both accepted exports used a systemd user-service cgroup with
`MemoryMax=8000000000` and `MemorySwapMax=0`; the wrapper read kernel
`memory.peak` while keeping the cgroup alive, including descendants and charged
cache/kernel memory. The safety cap is not a hardware requirement.

| Run | Peak bytes | MiB | GiB | Elapsed | Headroom |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fresh geometry cache | 1,036,214,272 | 988.211 | 0.9650 | 68.425 s | 6,963,785,728 |
| Warm geometry cache | 803,786,752 | 766.551 | 0.7486 | 29.693 s | 7,196,213,248 |

Both completed with zero swap and zero `max`, OOM or OOM-kill events. The
largest actual peak is **0.965 GiB**, 12.95% of the cap, leaving 87.05% unused.
The preceding expression-graph cycle measured 1.098 GiB fresh and 0.774 GiB
warm; run variation and changed Curta geometry prevent causal attribution from
the difference. Earlier runs from this cycle are retained in project evidence
but are not final-source results.

The fresh and warm manifests are byte-identical, SHA-256
`08624e3edf90dfeec0f8f8557b896a5fe53031625f5544c0bec4bff1cfb1a002`,
1,670,616 bytes. Each export directory is 25,029,894 bytes; the fresh geometry
directory is 55,070,316 bytes with 190 STLs, 184 BREPs and **zero SCAD files**.
The log contains no SCAD generation, OpenSCAD job or Manifold fusion invocation
(Curta has no faceted fusion in this tree).

The unchanged independent check compared 33,254 values across 13 poses with
2,558 scalar slots, 9,969 bindings, 44,718 native graph nodes and 11,027
canonical nodes. Browser capture under Chromium 151/API 7 reported no page
errors. Inspection of the whole machine and isolated carry spring at 0.7 turn
shows complete geometry and the expected continuous spread spring.

Raw final-source reports and logs are project-owned under `_build_evidence/` as
`remove-openscad-broker-release-{cold,warm}.{json,log}`; parity and browser
evidence use the same prefix.

## Requested OpenSCAD-free clock acceptance

For 3DPrintedClocks HEAD `2c456d9202a170cecebf746913a2dd749061bf9c`,
the accepted environment set PATH to the workspace virtualenv only and proved
`shutil.which('openscad') is None`. With the pilot-authorized, project-declared
`solid-node-mechanics` dependency loaded from its clean adjacent checkout, a
fresh `solid build wall_clock_02` completed successfully against framework
source SHA-256
`1e353da68f895366b63233767073cffe93e38f6511ae30026b290d44c2911154`.

The build took 51.180 seconds and peaked at 977,829,888 bytes (932.531 MiB,
0.9107 GiB) under `MemoryMax=8000000000` and `MemorySwapMax=0`, leaving
7,022,170,112 bytes of cap headroom. Swap and every cgroup max/OOM event were
zero. It published 53 BREP and 53 STL artifacts plus 70 optional SCAD
presentation files. The successful SCAD generation demonstrates retained
OpenSCAD output support; the restricted PATH and absence of an OpenSCAD render
or availability error demonstrate that those files were not brokered through
the binary. The 42,200-byte viewer manifest has SHA-256
`1b4174c792482de3079b9392f4ad92db06c5f4be8bfbf0447d377b43742ef1ec`.
The published model directory occupies 17,491,854 bytes.

Raw report and log are project-owned as
`_build_no_openscad_validated.{json,log}`; generated geometry is under
`_build_no_openscad_validated/wall_clock_02/`. The earlier failed dependency
probe remains separately recorded as `_build_no_openscad_acceptance.{json,log}`
and is not counted as geometry or OpenSCAD evidence.
