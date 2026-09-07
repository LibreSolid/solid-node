## Why

Due-diligence finding F06 reproduced `solid develop` ignoring modifications to
explicitly tracked `.scad`, `.js`, `.stl`, and `.step` geometry sources because
the shared event handler accepts only `.py`. The precise watcher already knows
these files affect the model, so filtering them leaves the published build
stale until an unrelated Python edit or restart.

## What Changes

- Distinguish events from the successful build's precise tracked-source watch
  from events produced by the broad recursive recovery watch.
- Trigger a rebuild for a modification to any explicitly tracked source,
  regardless of extension.
- Retain the broad recovery watch's Python-only and `__pycache__` noise filter
  when loading or assembly failed before a reliable source set was available.
- Add dispatch coverage for Python and non-Python tracked sources, ignored
  untracked noise, duplicate events, and a real watcher cycle over an imported
  geometry source.
- Keep moved-event/atomic-save policy outside this change because F06 confirmed
  only modification dispatch and watchdog platforms differ in how replacement
  saves are reported.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `build-pipeline`: make the watch-rebuild contract apply to every explicitly
  tracked source while retaining narrow filtering for broad error recovery.

## Impact

- `solid_node/core/builder.py`: record normalized precisely watched paths and
  make event filtering depend on whether the changed path is one of them.
- Builder lifecycle/reload tests: cover precise non-Python events and broad
  recovery filtering, including one real observer cycle.
- `workflow/archive/due-dilligence-2026-09-07/probe_build.py`: model precise
  watch registration before dispatching its saved event matrix.
- `docs/changelog.rst` and the due-diligence records will describe the fix.
- No dependency, public API, artifact-format, or viewer change is required.
