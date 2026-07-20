## Why

The development viewer uses a colorful normal material for models without a
specified color, while the exported widget renders those models gray.

## What Changes

- Render exported models without an explicit or inherited color with the
  development viewer's normal-based material.
- Add focused coverage for that material selection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `export`: Exported widgets use the development viewer's normal-based material
  for models that do not supply node colors.

## Impact

- `solid_node/viewers/widget/src/tree.ts` material selection and its focused
  tests.
- The `export` behavioral specification; no manifest-version or Python API
  change.
