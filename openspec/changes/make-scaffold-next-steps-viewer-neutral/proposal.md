## Why

Due-diligence item C04 found that every successful `solid new` claims the
project will be available at `http://localhost:8000`. The actual `solid
develop` command may use a different port from `SOLID_NODE_PORT`, open the
OpenSCAD GUI instead, or refuse because neither optional viewer is available.

## What Changes

- Keep the scaffold's useful next steps for entering the project and running
  `solid develop`.
- Stop predicting a browser endpoint or viewer from `solid new`; viewer
  selection, diagnostics, and endpoint output belong to `solid develop`.
- Add a regression over the public success output and update the audit record.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `cli`: require new-project next steps to remain valid across configured
  ports and browser/OpenSCAD viewer availability.

## Impact

- `solid_node/manager/new.py`: remove the unconditional browser URL from its
  success guidance.
- `tests/test_manager_new.py`: pin viewer-neutral next-step output.
- CLI baseline specification and due-diligence records: state the corrected
  ownership boundary.
- No scaffold files, viewer selection, port configuration, or development
  process behavior changes.
