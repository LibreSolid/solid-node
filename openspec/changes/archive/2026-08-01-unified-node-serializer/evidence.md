# Implementation evidence

## Red-first producer proof

Before production changes, the real export and build snapshot writers were
called with independent `RecreatedAndReboundAssembly` instances. Each
`render()` recreated and rebound its child as `self.gear`. The required command
failed at the ratified base plus planning commit:

```text
PYTHONPATH="$PWD" ../../../.venv/bin/python -m pytest \
  tests/test_export.py::ExportBuildSnapshotParityTest::test_recreated_rebound_child_names_match -q

AssertionError: Lists differ: ['Cube'] != ['gear']
```

The export-local `_serialize_tree` did not link the new child and retained the
class fallback `Cube`; the builder-local `_viewer_state` linked it and emitted
`gear`. Before production edits, the added common-field assertions also expose
the missing export `mtime` and build `format`, while the list/tuple and
`children-<index>` export assertions expose the same missing linking step.
The focused pre-edit boundary run reported those three naming assertion groups,
the missing `viewer.json` format, and the builder lifecycle format assertion
red; explicit-name and class-fallback boundaries remained green as expected.

## Ownership boundary

S2 owns the additive `viewer.json` format update in
`shop-skills/solid-node-api/SKILL.md` and the one ordinary first-rebuild watcher
hash change. F1 does not modify shop-owned files.

## Green verification and inventory

- Focused parity and node-naming proof: 13 passed (five subtests).
- Export, build lifecycle, Sphinx, snapshot serving, and publication proof:
  50 passed (five subtests).
- V19 proof: 29 passed, 3 expected widget-E2E skips; the canonical widget host
  remains `solid_node/viewers/widget/index.html` and the publication-config
  diff from `6f8a5ae` is empty.
- Full framework suite: 363 passed, 3 skipped, 22 warnings (five subtests).
- V18 has no retired producer definition or call site. The allowed remaining
  linker matches are `core/serializer.py`, `node/internal.py`, and the
  F4-owned live `NodeAPI`; `NodeAPI`, `SnapshotNodeAPI`, and development
  `node.ts` remain explicit F4 debt.
- The final paired-validation inventory commands are retained in task 4.4;
  F1's framework disposition is shared `core/serializer.py`, while S2/F4 own
  the other removals.
- Canonical parity documents are retained, uncommitted, under
  `/home/asa/.cache/hermes/verification/sprint-002/20260801T000000Z-unified-node-serializer/`:
  `manifest.json`, `viewer.json`, and `rolling-manifest.json`. The rolling
  manifest records the focused and full-suite commands and will carry this
  cycle's implementation commit after it is created.

## Architecture and migration disposition

ADR-034 records shared schema identity versus producer portability, and
amendments reconcile ADR-020 and ADR-031. `mtime` is accepted additive churn:
regenerated committed export manifests and their Sphinx dependencies may change
without a schema-version bump.

## Completion

The supported archive operation completed noninteractively at
`openspec/changes/archive/2026-08-01-unified-node-serializer/`. Strict
post-archive validation passed for all 11 baseline specifications with zero
failures. This archival is cycle completion only; it does not authorize sprint
or primary-branch integration.
