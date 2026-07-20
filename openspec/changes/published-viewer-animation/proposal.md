## Why

Sprint 001 Story 5 consumes the `solid build` viewer snapshot from a browser
that deliberately never loads project Python. The snapshot preserves raw `$t`
operations but omits their animation cadence, preventing a complete static
viewer from reproducing the established solid-node viewer behavior.

## What Changes

- Publish the model animation cadence (`fps` and `frames`) with the versioned
  viewer snapshot in the atomically replaced build directory.
- Make that metadata available to snapshot-backed viewer hosts without source
  imports.
- Add contract and lifecycle coverage for animated and static build snapshots.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `build-viewer-artifacts`: Published viewer snapshots carry the animation
  cadence required to evaluate their raw operations in a static browser host.

## Impact

- `solid_node/core/builder.py` snapshot serialization and its build tests.
- The private snapshot-backed viewer contract used by the shop floor.
- Originating evidence: Sprint 001 Story 5 V8 engine inspection, which needs
  the existing viewer’s animated controls without project execution.
