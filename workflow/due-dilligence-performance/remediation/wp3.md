# WP3 — verified persistent printed-piece facts

Date: 2026-09-07  
Planning/apply HEAD: `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c`  
Environment: Python 3.12.3, Linux 6.8.0-139-generic, x86_64

## Legacy red proof

The red proof exported planning HEAD with `git archive HEAD` into a fresh
temporary directory, wrote one valid box STL, and launched two fresh Python
interpreters against that isolated source. Each interpreter patched
`trimesh.load` only to append one marker before delegating to the real decoder,
then registered the same current artifact through `PieceInventory`.

Expected persistent behavior was one decode across the two processes. Planning
HEAD produced:

```text
planning_HEAD_fresh_process_decodes=2 expected=1
child_statuses=[0, 0]
```

The proof command exited 1 because both successful fresh processes decoded the
unchanged STL. This demonstrates the legacy repeated work, not absence of a new
API. The isolated export and artifact lived under a disposable `wp3-red-*`
temporary directory; no catalogue project or historical evidence was touched.

## Implemented boundary

- `solid_node/_artifact.py` owns the private open-file snapshot and the strong
  `(realpath, device, inode, size, mtime_ns, ctime_ns)` observation.
- `solid_node/core/pieces.py` persists only full SHA-256, printable extents,
  volume, and watertightness in a version-1 sidecar. Missing, malformed,
  incomplete, unknown-version, boolean-version, negative-extent, or mismatched
  observations recompute. Records publish by temporary-file replacement.
- Piece inventories keep snapshots open until their manifest/document and any
  exported or staged bytes are complete. A fact hit retains no STL payload.
  Hash and mesh decode share one payload on a miss.
- Builder, export, and browser staging make at most three coherent attempts
  when an artifact path changes. Builder validates after the existing WP1
  source-generation checkpoint and before clearing an error or replacing
  `viewer.json`. Export and staging copy from the pinned descriptor, never by
  resolving the source path again.
- Browser staging uses the metadata-only settled currency branch and
  `publish_facts=False`, so it neither restamps artifacts/currency nor creates
  or repairs fact records. Its private staged model is a coherent copy rather
  than a hard link; this avoids changing the source artifact ctime that guards
  the fact record.
- Base-mesh, local-bounds, rigid-Manifold, and faceted-verdict identities use
  the same strong observation. Bounds and Manifold construction pass their
  exact observed identity into the mesh cache rather than observing twice and
  risking a mixed cache entry.
- The public id remains the first 12 hexadecimal characters. Inventory merging
  compares the complete hashes and raises a deterministic diagnostic containing
  the two sorted full digests if distinct hashes share the public prefix.
- Fact sidecars are private, absent from documents, and mapped to their STL by
  the build sweep so each lives and dies with that artifact. Every publication
  still rebuilds names, sources, models, counts, tree hierarchy, placements,
  drivers, expressions, and document version from the live model.

## Green proof

Focused WP3 and lower-cache tests:

```text
pytest -q tests/test_persistent_piece_facts.py tests/test_node_mesh_cache.py \
  tests/test_mesh_import_deferred.py tests/test_manifold_cache.py \
  tests/test_intersection_memo.py
50 passed, 7 subtests passed in 6.37s
```

Source-generation/builder integration after the private sidecars were added:

```text
pytest -q tests/test_builder_lifecycle.py tests/test_builder_reload_resilience.py \
  tests/test_source_generation.py tests/test_source_census.py \
  tests/test_source_set.py tests/test_openscad_dependency.py \
  tests/test_content_verified_currency.py tests/test_persistent_piece_facts.py
115 passed, 4 warnings, 14 subtests passed in 12.00s
```

Final WP3 package matrix:

```text
pytest -q tests/test_persistent_piece_facts.py tests/test_pieces.py \
  tests/test_export.py tests/test_browser_renderer.py \
  tests/test_builder_lifecycle.py tests/test_build_publication.py \
  tests/test_build_lock.py tests/test_content_verified_currency.py \
  tests/test_node_scoped_currency.py tests/test_node_mesh_cache.py \
  tests/test_mesh_import_deferred.py tests/test_manifold_cache.py \
  tests/test_intersection_memo.py tests/test_tessellation_precision.py \
  tests/test_exact_geometry.py tests/test_stl_node.py
306 passed, 1 skipped, 1 warning, 31 subtests passed in 33.02s
```

The skip is the existing optional viewer-bundle condition. The warning is the
existing legacy-render `FutureWarning` in `ExportAnimationTest`; neither is a
WP3 failure. An immediately preceding run of this same ordered matrix reached
305 passes and then failed
`ExactIntersectionTest.test_volume_assertions_share_the_exact_helper`; that
test passed alone, passed after the three nearest preceding suite groups, and
the complete identical matrix passed on rerun as recorded above. This
order-dependent exact-cache observation has been handed to the independent
review rather than hidden by the green rerun.

## Limits

The observation guarantee has ADR-081's explicit filesystem boundary: a
privileged external operation that changes bytes while preserving real path,
device, inode, size, mtime and ctime must explicitly remove the artifact or its
fact record. Three consecutive identity changes fail the producer rather than
looping without bound; builder failure occurs before prior error clearance or
manifest replacement. Browser staging now copies each model once instead of
hard-linking it: that extra private I/O is the deliberate cost of copying from
the same pinned descriptor as the published facts without changing the source
artifact's ctime. No shared-host timing in these correctness runs is
claimed as a performance threshold; WP10 owns current-project measurement.
