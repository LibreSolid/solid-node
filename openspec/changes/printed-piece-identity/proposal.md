## Why

A consumer that lays out a print job needs to know which solids in an assembly
are the *same printed piece*, and how many of each to print. Today the only
identity a published document carries is the artifact path (`model`), derived
from `uniq_id` — a hash of the node class plus its constructor arguments
(ADR-026). That key answers "was this built from the same call?", not "is this
the same thing to print", and the two answers diverge in practice.

Empirical evidence from the shop's projects, measured against their published
`viewer.json` documents:

- `v8-engine`: 119 rigid node instances collapse to 24 artifact keys, and all
  24 STLs are byte-distinct. Nominal identity is exactly right here — 16
  valves, 16 retainers, 16 bucket lifters, 10 cam bearing caps, 8 pistons.
- `gearbox`: 24 artifact keys, but only **18** distinct STL contents. Six
  bushing classes (`InputFrontBushing`, `InputRearBushing`, …) with identical
  parameters produce byte-identical geometry under six keys, as do `FrontWall`
  and `RearWall`. A build layout driven by the artifact key would tell the
  maker to print eight distinct parts where two models cover them.

Nothing in a published document exposes a piece count, and nothing exposes the
per-piece facts a print layout needs (bounding extents, volume, watertightness,
originating source file), so a consumer must load and mesh every STL itself to
learn whether a piece even fits on a bed.

## What Changes

- Identify each distinct **printed piece** by a content fingerprint of its
  built STL, so geometrically identical solids are one piece regardless of how
  the code was factored, and mirrored or otherwise handed parts stay distinct.
- Publish a `pieces` inventory alongside `root` in both the normal-build
  `viewer.json` and the static-export `manifest.json`: one entry per distinct
  printed piece, carrying its id, display name, contributing source files and
  model paths, instance count, bounding extents, volume, and watertightness.
- Give every rigid node in the published tree a `piece` reference, so a
  placement in the tree maps to its piece without the consumer re-deriving the
  grouping.
- Leave `uniq_id`, artifact paths, caching, and the `model` field untouched:
  the artifact key remains the build-cache key it was designed to be, and
  piece identity is a separate, geometry-derived fact layered on top.
- Additive only; no existing field changes meaning and no consumer of the
  current schema breaks. Not **BREAKING**.

## Capabilities

### New Capabilities

- `printed-pieces`: identification of the distinct printed solids in an
  assembled model — content-derived piece identity, the per-piece facts a
  print layout needs, and the published inventory's shape and guarantees.

### Modified Capabilities

- `build-viewer-artifacts`: the published normal-build snapshot must carry the
  piece inventory and per-node piece references.
- `export`: the static export manifest must carry the same inventory, with
  piece model references resolving inside the portable `models/` tree.

## Impact

- New `solid_node/core/pieces.py`: fingerprinting, geometry facts, and the
  inventory accumulated during a document walk.
- `solid_node/core/serializer.py`: optional piece mapper on `serialize_node`,
  emitting `piece` on rigid nodes.
- Three producers gain the inventory: `solid_node/core/builder.py`
  (`viewer.json`), `solid_node/core/export.py` (`manifest.json`), and
  `solid_node/viewers/browser.py` (browser snapshot).
- Reuses the existing `trimesh` dependency and the framework's base-mesh cache;
  no new dependency.
- Consumers (widget, web app, Sphinx extension) are unaffected until they
  choose to read the new section.
