## Why

A rigid printed part is meant to be one connected solid, and nothing in the
framework could tell whether it was.

Watertightness is a per-shell property. A mesh of several disjoint closed
shells is watertight, has a positive volume, exports a valid STL, and renders
in the viewer looking like a part. So a component whose features never actually
reached each other passes every check the framework offers. Three shop projects
shipped parts in pieces through that gap — a windmill fan whose four blades stop
3mm short of their hub (4 bodies), a selector fork whose neck reaches neither
the ring nor the carriage (2 bodies), a selector gate whose label bars float off
the plate (14 bodies) — all watertight, all green.

The geometric pressure a project can express was also one-sided. Adjacency
discipline (`assertNoPairwiseIntersections`) pushes parts apart, and a part that
has fallen into fragments satisfies every non-interference contract there is.
Nothing pulled the other way.

## What Changes

- Connectivity assertions over the number of connected solids in a node's
  world-space mesh: `assertOneBody`, `assertBodyCount`, `assertJoined`
  (with an optional minimum weld volume — the one case where two features are
  *required* to share volume), and `assertNoDisconnectedParts` as the tree-wide
  counterpart of the pairwise adjacency sweep.
- Components are counted by splitting the mesh without filtering to watertight
  components, because a fragment that is itself closed is exactly the case
  worth catching.
- Nodes MAY declare a `bodies` count. `verify_bodies()` raises
  `DisconnectedBodyError` naming the node, the declared count and the actual
  one. The default is `None`, so a project that does not ask for the check
  never loads its meshes on account of it.
- `FusionNode` declares `bodies = 1`, making "a single, inseparable unit" a
  checked property rather than a docstring promise.
- The builder verifies declared counts before publishing, on both publication
  paths — including the one that finds the artifact set already current, so a
  fragmented model cannot reach the maker by that route either. A violation
  prevents publication and is reported through the ordinary error channel.

## Capabilities

### New Capabilities

None. This adds contracts to the existing test framework, node model, and build
pipeline.

### Modified Capabilities

- `test-framework`: the connectivity assertions, how bodies are counted, and
  the statement that watertightness is not evidence of connectedness.
- `node-model`: the `bodies` declaration, its unchecked default, the
  `FusionNode` count, and what `verify_bodies()` raises and skips.
- `build-pipeline`: verification before publication on both publishing paths, a
  violation reported through the ordinary error channel, and no mesh read for a
  project that declares nothing.

## Impact

- `solid_node/test.py` — `_body_count` helper and the four assertions.
- `solid_node/node/base.py` — the `bodies` attribute, `verify_bodies()`, and
  `DisconnectedBodyError`.
- `solid_node/node/fusion.py` — `bodies = 1`.
- `solid_node/core/builder.py` — `_verify_declared_bodies()` called on both
  publication paths.
- `tests/test_connectivity.py` — new; `tests/test_builder_lifecycle.py` —
  extended for the publication paths.
- Existing projects are unaffected until they declare a count or write a
  connectivity contract: the default leaves every node unchecked.

## Record note

This record was reconstructed after the fact. The implementation
(`ba6ff1e`) shipped without an OpenSpec cycle, and the baseline specs were
brought level with the code in a follow-up (`77c3970`) that still left the
change record missing. This change directory carries the proposal, design, and
delta specs the cycle should have produced before implementation; the delta
specs state exactly what those two commits landed, and are archived with
`--skip-specs` because the baseline already carries them. Nothing here
describes an intention that was not implemented.
