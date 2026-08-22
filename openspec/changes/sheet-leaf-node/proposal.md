## Why

The upcoming `metamaquina-rebuild` project needs to model a laser-cut
printer frame — the Metamaquina2 reference builds its structure entirely
from parametric 6 mm MDF panels joined by t-slots — and the framework has
no way to express a sheet part. A flat part modelled as a generic solid
carries no cut profile: nothing guarantees it is actually manufacturable
on a laser cutter, and there is no artifact a cutter could consume. The
part a maker previews and the file a laser cuts must derive from one
authored profile, or they will drift apart.

## What Changes

- A new abstract leaf kind, `SheetLeafNode`, under `ExactLeafNode`: a
  part authored as a 2D profile plus a declared `thickness`. The base
  owns `render()` — the extrusion of the profile — so the solid in the
  tree and the cut profile can never diverge; subclasses implement
  `profile()` instead and overriding `render()` is not an extension
  point.
- A v1 concrete implementation, `Build123dSheetNode`, whose `profile()`
  returns a build123d planar sketch/face.
- A nominal (kerf-free) DXF artifact per sheet leaf, written at build
  time beside the STL/BREP through the existing `as_scad()` artifact
  path and covered by the same freshness guard, exported from the exact
  profile with arcs preserved.
- Profile validation with errors naming the node: exactly one planar
  face — one outer boundary, holes strictly inside — one part per leaf.
- Documentation: `docs/leaf-nodes.rst` gains the sheet leaf kind.

Out of scope, deferred to their own evidence: SVG profile import, kerf
compensation, engraving/marking, material/process metadata, nesting, and
any production-export CLI command. The nominal DXF plus the persisted
exact profile leave all of these additive.

## Capabilities

### New Capabilities
- `sheet-parts`: authoring a part as a 2D profile plus thickness, the
  profile contract and its validation, the derived extruded solid, and
  the build-time nominal DXF artifact.

### Modified Capabilities
- `node-model`: the multi-backend leaf adapter roster gains the sheet
  leaf kind and its v1 build123d implementation; the distinct-types rule
  and the produce-only-when-stale artifact rule extend to it and its DXF
  artifact.
- `exact-geometry`: the enumeration of exact leaf adapters gains the
  sheet leaf; its `exact` is true by adapter type and its `shape()` is
  the extruded solid.

## Impact

- `solid_node/node/`: new module for the sheet base and its build123d
  adapter; `solid_node/node/__init__.py` exports.
- `solid_node/node/leaf.py` / `exact_leaf.py`: untouched or minimally
  extended — the sheet base plugs into the existing artifact and
  skip-guard machinery (`_render_can_be_skipped`, `as_scad`).
- Dependencies: none added. DXF export uses build123d's exporter; ezdxf
  arrives transitively with the already-pinned build123d 0.10.
- Docs: `docs/leaf-nodes.rst`.
- Empirical grounding: the `metamaquina-rebuild` frame (Metamaquina2 as
  dimensional reference) is the originating project; its side/bottom/arc
  panels are the representative callers this change exists to serve.
