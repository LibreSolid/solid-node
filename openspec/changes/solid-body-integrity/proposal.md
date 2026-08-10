## Why

The `bodies` declaration answers the wrong question and cannot answer it
correctly. It asks each node how many disconnected solids its mesh is allowed
to have — inviting parts to be designed as multi-body — when the only sound
contract is that a printed solid is exactly one body. Worse, `verify_bodies()`
counts components on `node.mesh`, the *world* mesh, which composes every
operation from the node to the tree root. Those operations are authored by
enclosing assemblies and carry the animated `$t` expression, so composing them
during a build raises `TypeError: (360 * $t) is not a number` and the build
fails on a check that never looked at the geometry.

Reproduced in `projects/delme-claude` (shop workspace): a `GearPair` assembly
animating two `SpurGear` leaves that declare `bodies = 1`. Both built STLs are
verifiably one body each; the build fails anyway. This is not specific to that
project — build-time body verification currently rejects every leaf that any
assembly animates.

The defect is architectural, not incidental. Connected-component count is
invariant under rigid transform, so applying a placement matrix to answer it is
both unnecessary and the sole source of the failure. Connectivity is a local,
timeless property of a solid; only collision between separately placed parts is
a world-framed, time-dependent question.

## What Changes

- **BREAKING** Remove the `bodies` class attribute, `verify_bodies()`, and
  `DisconnectedBodyError` from the node model. Every solid is one connected
  body, unconditionally and undeclarable.
- **BREAKING** Forbid a non-rigid child under a `FusionNode`. You fuse into a
  solid, then assemble solids; an assembled thing cannot be fused. Today this
  nests without error and silently flips the fusion non-rigid, so a nonsense
  tree builds quietly and produces no STL.
- Make `rigid` a static, type-determined fact. With the hierarchy enforced,
  `InternalNode`'s `self.rigid = self.rigid and child.rigid` propagation can
  never change an outcome and is removed.
- Introduce the **topmost rigid node** as the verified unit: a rigid node whose
  parent is non-rigid, or the root when the root is itself rigid. The build
  verifies exactly these nodes are one connected body and does not descend past
  one. A leaf, or a nested fusion, may legitimately be several disconnected
  pieces so long as the enclosing solid joins them.
- Verify against the node's own STL with **no operations applied**. Geometry
  below the topmost rigid node is already baked into that STL by `as_scad`;
  operations at or above it are placement of the whole body. No world matrix is
  composed, so nothing can be an unresolved `$t` expression.
- **BREAKING** Remove `assertOneBody`, `assertBodyCount`, and
  `assertNoDisconnectedParts` from the test framework. They assert a property
  the build now guarantees structurally.
- Keep `assertJoined`, and reframe it as solid-local: it composes operations
  only up to the enclosing rigid node instead of to the tree root. It remains
  the one connectivity claim the build cannot infer — that two *named* features
  reach each other, with a required weld volume.
- `node.mesh` keeps its world semantics. Collision assertions
  (`assertNoPairwiseIntersections` and the intersection family) genuinely need
  world placement at an instant and are unaffected.

## Capabilities

### New Capabilities

None. This change removes a capability and corrects two existing ones.

### Modified Capabilities

- `node-model`: replace the "Declared connected-body count" requirement with a
  fusion-hierarchy constraint and the topmost-rigid-node definition; state that
  `rigid` is determined by node type.
- `build-pipeline`: replace "A declared body count is verified before
  publication" with verification of the topmost rigid nodes against their own
  local STLs.
- `test-framework`: remove the three body-count assertions and their scenarios;
  restate `assertJoined` as a solid-local, pairwise, quantified claim.

## Impact

Framework source:

- `solid_node/node/base.py` — `bodies` (:216), `verify_bodies()` (:596),
  `DisconnectedBodyError`.
- `solid_node/node/fusion.py` — `bodies = 1` (:19); reject a non-rigid child.
- `solid_node/node/internal.py` — rigidity propagation (:28); hierarchy
  validation in `validate()`.
- `solid_node/core/builder.py` — `_verify_declared_bodies()` (:381) rewritten
  as a topmost-rigid-node sweep.
- `solid_node/test.py` — remove three assertions (:413, :425, :467); rebase
  `assertJoined` (:441) on a solid-local frame.

Records:

- Reverses the ratified outcome of the archived `connectivity-contracts`
  change (2026-08-09) in the parts named above.
- Amends ADR-003 (rigid vs non-rigid): rigidity propagation is superseded by a
  structural hierarchy constraint.
- Adds one NODE ADR for the solid-integrity boundary.
- `tests/test_connectivity.py` — the declared-count tests are removed;
  hierarchy and topmost-rigid-node tests replace them.

Users: any project declaring `bodies` fails to import until the declaration is
deleted. No framework example or shipped project declares one; the only users
are synthetic nodes in `tests/test_connectivity.py`. No project nests a
`FusionNode` over an `AssemblyNode`, so the new hierarchy rule breaks nothing
that exists.
