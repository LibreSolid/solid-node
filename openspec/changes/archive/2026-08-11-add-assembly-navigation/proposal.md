## Why

The published tree already defines an assembly's names, hierarchy, models, and
inherited colours, but hosts can only mount or refresh the whole document.
Studio needs a maker-facing assembly navigator whose focus and visibility
actions actually affect the shared renderer without duplicating the viewer's
tree traversal or Three.js scene ownership.

## What Changes

- Add a versioned viewer-handle capability that exposes the current published
  assembly tree in host-safe metadata form.
- Add handle operations to focus a node's subtree as the displayed root and
  hide or show any node's subtree while retaining the loaded document and
  camera lifecycle guarantees.
- Preserve independent focus and visibility state across targeted document and
  artifact updates when the named nodes remain; clear unavailable state when
  a replacement document removes those nodes.
- Increase the viewer API version and make the contract available to all
  framework hosts; no producer schema or project source changes are required.

## Capabilities

### New Capabilities

- `viewer-assembly-navigation`: Host-visible assembly metadata and session
  controls for focusing and showing or hiding published model subtrees.

### Modified Capabilities

- `viewer-package`: The reusable viewer handle gains an API-versioned
  assembly-navigation contract.

## Impact

- `solid_node/viewers/widget/src/` gains viewer-handle, tree, and focused
  browser tests; the package API version advances.
- Browser shells and external hosts can consume the feature after their
  existing API compatibility check is updated.
- The originating caller is SolidNode Studio's Model-panel assembly navigator;
  it must not mutate the CAD project or published build artifacts.
