## Context

Sprint 002 cycle F1 starts from framework commit `6f8a5ae` and owns validation
rows V1, V2, the serializer portion of V18, and F1's preservation proof for
V19. The current producers duplicate a recursive walk:

- `solid_node/core/export.py::_serialize_tree` writes `manifest.json`, copies
  and deduplicates rigid meshes under `models/`, but does not call
  `_link_child` before serializing children.
- `solid_node/core/builder.py::_viewer_state` writes `viewer.json`, roots rigid
  model paths at the published build directory, and does call `_link_child`.
- `solid_node/viewers/web/viewer.py::NodeAPI` performs the third walk and also
  links children; it remains until cycle F4 replaces the development viewer.

Normal assembly masks the omission when repeated `render()` calls return the
same child objects, because assembly has already linked them in place. The
observable base defect requires a node whose `render()` recreates and rebinds a
child. Exercising independent instances through `export_node` and
`Builder._write_viewer_snapshot` at `6f8a5ae` produced
`manifest.json == ['Cube']` and `viewer.json == ['gear']`. The implementation
test creates that fixture in `tests/test_export.py` and captures the red with:

```bash
PYTHONPATH="$PWD" ../../../.venv/bin/python -m pytest \
  tests/test_export.py::ExportBuildSnapshotParityTest::test_recreated_rebound_child_names_match -q
```

Hermes obtained the observation with a throwaway stdin Python script run from
the cycle worktree. It called both real producers with independent instances
and an auto-cleaned `TemporaryDirectory`; it wrote no tracked or retained
artifact. The named test makes the same reproduction durable before production
edits.

The accepted boundaries constrain the repair. ADR-020 makes `manifest.json` a
versioned portable export contract, while ADR-031 makes `viewer.json` a private
build-root-relative interface. Sharing `format: "solid-node-export"` extends the
format beyond ADR-020's original three-consumer account without making the
private snapshot portable. A new ADR records schema identity versus portability
and amends ADR-020/031's implications. ADR-026 remains the source of
attribute-derived names; ADR-030/032 retain atomic publication.

## Goals / Non-Goals

**Goals:**

- Use one framework-owned recursive serializer for export and normal-build
  viewer documents.
- Apply `_link_child` before every child is serialized, preserving explicit,
  attribute, list/tuple, and fallback naming rules.
- Emit the same node fields from both producers: `name`, `type`, `color`,
  `mtime`, raw serialized `operations`, and exactly one of `model` or the
  applicable `children` collection.
- Add `format: "solid-node-export"` to `viewer.json` and per-node `mtime` to
  `manifest.json`, retaining `version: 1` and existing animation metadata.
- Prove the change red-first through the actual export and builder producers,
  then retain their canonical focused and full-suite coverage.

**Non-Goals:**

- Renaming `manifest.json`, `viewer.json`, `solid-widget.js`,
  `data-solid-widget`, or `SolidNodeWidget`.
- Changing export model deduplication or its portable `models/` rooting.
- Copying models into a build publication, changing its build-root-relative
  paths, or otherwise making `viewer.json` portable or self-contained.
- Retiring live `NodeAPI`, `SnapshotNodeAPI`, or the development renderer;
  cycle F4 owns those removals.
- Changing viewer behavior, package layout, distribution, registry
  publication, CLI surfaces, or Sphinx embedding behavior.

## Decisions

### One tree serializer with a producer-supplied rigid-model mapper

Add a narrow shared module under `solid_node/core/` with a recursive function
that accepts a node and a callable mapping each rigid node to its document
model path. The shared function owns node fields, rigid short-circuiting,
list/tuple recursion, child linking, and raw operation serialization.

The export mapper keeps the existing `models.setdefault(node.stl_file,
portable_path)` side effect, which is later consumed by `export_node` to copy
each distinct STL once. The builder mapper remains pure and returns
`os.path.relpath(node.stl_file, build_dir)`. Thus serialization is unified
without pretending that copying/deduplication and build publication are the
same operation.

Alternatives rejected:

- Parameterizing the serializer with a mode flag couples it to two producers
  and makes future callers branch inside the common walk.
- Making the shared serializer copy files gives an otherwise data-only walk
  filesystem side effects and wrongly pushes export portability into builds.
- Making builder call the export serializer directly would root paths under
  `models/` and make build output accidentally portable, violating scope.

### Link children in the shared walk before recursive serialization

For a non-rigid node whose `render()` returns exactly a list or tuple, call
`node._link_child(child)` for every child before recursing. This is the same
established rule used by `InternalNode.as_scad`, builder serialization, and
live `NodeAPI`, and it is idempotent. A non-rigid render result of another type
retains current serializer behavior: emit the node fields without `model` or
`children`; normal build/export lifecycle validation remains responsible for
rejecting invalid project models before publication.

Alternatives rejected:

- Serializing `child.name` without linking preserves the demonstrated drift.
- Deriving names independently in the serializer duplicates ADR-026 and risks
  diverging from tests and `NodeAPI` again.

### Converge fields additively, not publication semantics

Both top-level documents carry `format: "solid-node-export"`, `version: 1`,
the existing `animation` object, and a root produced by the shared serializer.
Every node carries `mtime`; this preserves the builder field and adds it to
exports. Additive fields do not change the existing manifest tree shape or raw
operation representation, so the public format version does not bump.

The shared format denotes the versioned tree-document schema. It does not imply
that every producer creates a self-contained directory. The new ADR, ADR index,
and architecture update make that distinction durable and reconcile the
accepted export and build-snapshot decisions.

The producers remain responsible for their document names and path mappers:

- `manifest.json`: portable export; rigid paths begin with `models/`; files are
  copied and deduplicated into the export.
- `viewer.json`: non-portable build snapshot; rigid paths are relative to the
  build root; no export-style mesh copy is introduced.

Alternatives rejected:

- Renaming either document erases the meaningful portable-export versus
  build-publication distinction and is explicitly excluded by the sprint.
- Omitting `format` from the build snapshot or `mtime` from the manifest leaves
  dual source shapes for downstream cycle F2.
- Bumping the manifest version would misclassify an additive change as a
  breaking tree or operation change under ADR-020.

### Preserve the remaining live walk as explicit F4 debt

F1 removes `_serialize_tree` and `_viewer_state` as production definitions.
It does not opportunistically move `NodeAPI` or `SnapshotNodeAPI` onto the new
document loader because F4 is already ratified to retire the per-node API and
`SnapshotNodeAPI`. F1 records these as allowed remaining matches so a search is
evidence rather than an inaccurate zero-duplicate claim.

### Validation maps directly to the sprint matrix

All commands run from this cycle worktree unless another working directory is
stated.

- **V1 red/green home:** add
  `tests/test_export.py::ExportBuildSnapshotParityTest`, using independent
  export/build instances of the re-created-and-rebound child fixture through
  the actual document writers. Cover explicit, attribute, list, tuple, class
  fallback, exact `self.children` indexed derivation, operations, colour, rigid
  short-circuiting, non-list non-rigid behavior, and producer-specific rooting.
  Required red command:
  `PYTHONPATH="$PWD" ../../../.venv/bin/python -m pytest
  tests/test_export.py::ExportBuildSnapshotParityTest::test_recreated_rebound_child_names_match
  -q`; it must fail with the current name mismatch before production edits.
  Green focused command:
  `PYTHONPATH="$PWD" ../../../.venv/bin/python -m pytest
  tests/test_export.py::ExportBuildSnapshotParityTest
  tests/test_node_naming.py -q`.
- **V2 homes:** extend
  `tests/test_builder_lifecycle.py::BuilderLifecycleTest::test_complete_build_writes_viewer_snapshot_before_publishing`
  for exact `viewer.json` fields/rooting; use the parity class for exact
  `manifest.json` fields/rooting; retain Sphinx recognition in
  `tests/test_sphinx_ext.py`, snapshot serving in
  `tests/test_web_viewer.py::StlEndpointTest::test_snapshot_node_api_serves_without_loading_project`,
  and atomic publication in `tests/test_build_publication.py`. The builder
  lifecycle test also asserts no export-style `models/` tree or copied mesh is
  introduced. Command:
  `PYTHONPATH="$PWD" ../../../.venv/bin/python -m pytest tests/test_export.py
  tests/test_builder_lifecycle.py tests/test_sphinx_ext.py
  tests/test_web_viewer.py::StlEndpointTest::test_snapshot_node_api_serves_without_loading_project
  tests/test_build_publication.py -q`.
- **V18 inventory:** after F1,
  `rg -n '(_serialize_tree|_viewer_state)' solid_node tests` must find no
  retired production definition, call site, or stale test dependency. These commands record the
  live-development matches explicitly as F4 debt:

  ```bash
  rg -n 'class (NodeAPI|SnapshotNodeAPI)\b' solid_node/viewers/web/viewer.py
  rg -n 'STLLoader|composeOperations|MeshNormalMaterial' solid_node/viewers/web/app/src/node.ts
  ```

  Final paired validation also runs this from the shop sprint worktree:

  ```bash
  rg -n '"(three|@types/three|jokenizer)"|STLLoader|composeOperations|MeshNormalMaterial' floor/frontend
  ```

  and this from the framework sprint worktree:

  ```bash
  rg -n 'class SnapshotNodeAPI\b|def (_serialize_tree|_viewer_state)\b|STLLoader|composeOperations|MeshNormalMaterial' solid_node/viewers/web solid_node/core
  ```

  S2/F4 own the remaining removals.
- **V19 preservation:** run
  `rg -n 'manifest\.json|viewer\.json|solid-widget\.js|data-solid-widget|SolidNodeWidget' solid_node tests openspec/specs docs`
  and review expected canonical matches; run
  `rg -n '"publishConfig"|npm publish|registry\.npmjs\.org' .github Makefile solid_node/viewers/widget/package.json`
  and require no new registry-publication configuration. Require
  `git diff --exit-code 6f8a5ae -- .github Makefile solid_node/viewers/widget/index.html solid_node/viewers/widget/build.mjs solid_node/viewers/widget/package.json`
  to prove F1 did not alter publication configuration or the canonical host
  surfaces. Focused behavior is covered by `tests/test_export.py` and
  `tests/test_sphinx_ext.py`; `tests/test_widget_e2e.py` is expected to report
  skipped in the F1 bench when its ignored bundle, headless Chromium, or Pillow
  prerequisite is absent. F2 and final paired validation own the browser
  assertion. The exact canonical host remains `solid_node/viewers/widget/index.html`.
- **Final F1 framework proof:**
  `PYTHONPATH="$PWD" ../../../.venv/bin/python -m pytest tests/`.

## Risks / Trade-offs

- **[Calling `render()` twice could expose stateful project behavior]** → Keep
  the producer lifecycle unchanged and test through the actual post-build
  writer paths; the shared walk performs no extra traversal relative to each
  current producer.
- **[A generic mapper could obscure path security or portability]** → Keep each
  mapper beside its producer and assert exact roots plus copied-file existence.
- **[`mtime` in portable exports reflects source/build time and can vary]** →
  Treat it as additive metadata, compare field presence and producer parity
  rather than requiring reproducible bytes. Committed documentation exports
  will change when regenerated and Sphinx will rebuild from the changed
  manifest; this ratified churn is accepted and recorded in migration evidence.
- **[A search could overclaim V18 while the live viewer still duplicates the
  traversal]** → Record `NodeAPI`, `SnapshotNodeAPI`, and development
  `node.ts` as explicit allowed F1 matches owned by F4.

## Migration Plan

No user migration is required. Existing consumers continue opening the same
document names and paths and ignore additive fields. Committed exports are
regenerated rather than hand-maintained; their new `mtime` fields may produce
expected diffs and Sphinx rebuilds. Implementation proceeds red-first, switches
both producers to the shared serializer, removes only the two replaced
functions, and runs focused plus complete suites. Rollback restores the two
producer-local walks; no stored-data migration or compatibility alias exists.

## Open Questions

None. The pilot ratified document-level parity, the producer-level red shape,
the schema-identity ADR, accepted `mtime` churn, and the F1/F4 boundary.
