# ADR-053: The authored profile is a sheet part's single source of truth

**Status:** Accepted

**Date:** 2026-08-22

**Change:** `sheet-leaf-node`

**Depends on:**
- [ADR-004: Multi-CAD Backend Adapter Pattern](ADR-004-multi-cad-backend-adapter-pattern.md)
- [ADR-026: Node identity — parameter-hashed artifact keys vs tree names](ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md)
- [ADR-033: Import-closure source set and the up-to-date leaf path](ADR-033-import-closure-source-set-and-up-to-date-leaf-path.md)
- [ADR-047: One shared OCCT currency for every exact backend](ADR-047-shared-occt-currency-for-exact-backends.md)
- [ADR-050: Nanosecond-fidelity artifact freshness](ADR-050-nanosecond-fidelity-artifact-freshness.md)

## Context and Problem Statement

The originating project, `metamaquina-rebuild`, models a printer frame built
entirely from laser-cut MDF panels joined by t-slots. Every leaf kind the
framework had authors a *solid*. A flat part modelled as a generic solid
carries no cut profile: nothing in it promises the part is a constant
thickness of sheet stock, and the build produces nothing a cutter can
consume.

The framework therefore had to answer two coupled questions. Which of the
part's two representations — the solid a maker previews and tests against,
and the 2D profile a machine cuts — is authored, and which is derived? And
where does the cut file live in a build whose artifact lifecycle is already
fully specified?

The two representations must never disagree. A panel whose solid and cut
file were written down separately would drift the first time one was edited,
and the cutter would faithfully cut the drift.

## Decision Drivers

- One of the two representations has to be derived from the other; keeping
  both authored is the failure mode the type exists to prevent.
- Deriving 3D from 2D is a projection. Deriving 2D from 3D is an inverse
  problem: which plane to slice on, whether the thickness is even constant,
  how to reconstruct a curve from a slice.
- A sheet part must remain an ordinary leaf: assemblies, fusions, exactness,
  the pieces inventory, the viewer and caching must all work on it unchanged.
- The build's artifact rules are already settled (produce only when stale,
  stamp with the source mtime, skip a leaf only while every artifact of it is
  current). A new artifact should join those rules, not invent its own.
- `exact.py` is deliberately backend-neutral (ADR-047): everything after the
  adapter boundary trades in one OCCT type and knows no backend.

## Considered Options

1. **Author the profile; derive the solid; write the DXF in the adapter**
   (Chosen)
2. Author the solid, declare the part "laser-cut", and recover the profile by
   slicing it
3. Author the profile, but export the DXF from the shared OCCT shape in
   `exact.py`

## Decision Outcome

Chosen option: **the authored profile is the source of truth, and the cut
file is written by the adapter that owns the profile's backend.**

`SheetLeafNode`, a framework-internal base under `ExactLeafNode`, owns
`render()`: it takes `profile()`, validates it, and extrudes it from the XY
plane along +Z by `thickness`. The subclass's extension point is `profile()`
and only `profile()`; overriding `render()` is unsupported, because a
subclass that did so could describe a different part from the one it cuts.
`Build123dSheetNode` is the v1 adapter, accepting a build123d `Sketch`, a
`Face`, or a `BuildSketch` builder and normalising it to one `Face`.

Four consequences follow.

- **The solid enters the exact pipeline exactly where every other exact
  adapter enters it.** The extrusion is an ordinary build123d `Part`, so
  namespace validation, the `.wrapped` rewrap of ADR-047, the STL and BREP
  writes, and the SCAD emission are the ones already in `ExactLeafNode`.
  `exact.py` needed no change at all, and a fusion may mix a sheet part with
  a CadQuery or build123d child and fuse exactly.

- **The DXF is an artifact of the node, under the existing lifecycle.** It is
  written in `as_scad()` beside the `.stl` and `.brep`, under the same
  basename, only when it is not already current, stamped with the same
  integer-nanosecond source mtime (ADR-050). `_render_can_be_skipped()` is
  extended to require it, so a lost cut file alone brings the part back — the
  same reasoning that already put the SCAD in that guard beside the STL.

- **The profile has a contract of its own, enforced before anything is
  written.** Exactly one planar face, one outer boundary with holes strictly
  inside it, on the XY plane: one sheet leaf is one part. Rejections name the
  node and the type it produced. This is the sheet base's rule rather than
  the adapter's, so a second sheet backend rejects the same mistakes with the
  same wording; the adapter supplies only the backend introspection. A solid
  is the rejection worth naming: `Build123dNode` would accept it happily, and
  its six planar faces would otherwise read as six parts.

- **`thickness` is a declared node parameter, required and positive at
  construction.** As a constructor argument it flows into `uniq_id`
  unchanged (ADR-026), so two thicknesses of one panel are two parts with two
  sets of artifacts for free; as a class attribute, changing it edits the
  source file, which the source-set freshness path already rebuilds on
  (ADR-033). Because it is a declared number rather than a dimension buried
  in geometry, a profile can be derived from it — a t-slot sized to receive a
  tab of the same stock is written once.

The DXF is **nominal**: the authored profile at model scale in millimeters,
with no kerf or other machine compensation. Compensation is a property of a
machine and a material, not of a part, and the persisted BREP keeps the exact
profile available to a future offsetting exporter. Arcs are preserved as arc
entities rather than tessellated, which is a manufacturing requirement and
not a fidelity preference: a polygonised hole cuts tight.

`Build123dSheetNode` subclasses `SheetLeafNode`, not `Build123dNode`, so no
adapter appears in another's method resolution order and ADR-047's
distinct-types obligation is met by construction.

## Pros and Cons of the Options

### Author the profile; derive the solid; write the DXF in the adapter

- **Good**: The solid and the cut file cannot disagree, because there is only
  one authored thing
- **Good**: The derivation is a projection with no choices to get wrong
- **Good**: A sheet part is an ordinary exact leaf everywhere else in the
  framework
- **Good**: The cut file inherits the whole artifact lifecycle rather than a
  parallel one
- **Bad**: A part that is genuinely easier to think about as a solid must be
  re-thought as a profile
- **Bad**: The DXF export is backend-specific code outside `exact.py`, so a
  second sheet backend will need its own

### Author the solid and recover the profile by slicing

- **Good**: No new authoring style; any existing leaf could be declared
  laser-cut
- **Bad**: Deriving 2D from 3D is an inverse problem — slicing plane,
  thickness verification, curve reconstruction — each a place to be silently
  wrong
- **Bad**: Nothing guarantees the authored solid *is* constant-thickness
  stock, so the promise the type exists to make cannot be kept
- **Bad**: A tessellated or trimmed solid yields a tessellated profile

### Export the DXF from the shared OCCT shape in `exact.py`

- **Good**: One exporter for every present and future sheet backend
- **Good**: No backend-specific code in an adapter
- **Bad**: Pushes 2D, backend-specific export into a layer whose whole point
  is that it knows no backend (ADR-047)
- **Bad**: The profile is already available in build123d form in the only
  adapter that exists, so the indirection buys nothing today
- **Bad**: The exact layer trades in solids; the profile would have to be
  recovered from one, reintroducing the inverse problem this ADR rejects

## Consequences

The framework can now express a manufacturing method, not only a modelling
backend, and the build produces a file a machine consumes rather than only a
mesh a viewer draws. Adding a second sheet backend costs one adapter: three
backend hooks and its own DXF function. The validated-face-to-DXF step is
kept a private, single-purpose function precisely so a later change can lift
it behind a conversion at the adapter boundary, as ADR-047 did for solids.

Nothing surfaces "this is a sheet part" to a consumer: in the viewer and the
pieces inventory a sheet part is just a solid. That is accepted for v1 — the
DXF on disk is the consumer-facing evidence, and richer metadata is deferred
with the production-export design.

Kerf compensation, SVG profile import, engraving, material and process
metadata, nesting, and a production-export CLI command are all deliberately
out of scope, each awaiting its own project evidence. The nominal DXF plus
the persisted exact profile leave every one of them additive.

## References

- `solid_node/node/sheet_leaf.py` — `SheetLeafNode`
- `solid_node/node/adapters/build123d_sheet.py` — `Build123dSheetNode`,
  `_export_dxf()`
- `tests/test_sheet_leaf.py` — profile contract, thickness identity, DXF
  lifecycle and arc preservation, adapter distinctness
- `tests/sheet_project/frame_panel.py` — the representative caller
- `docs/leaf-nodes.rst` — the sheet leaf kind
- `openspec/changes/sheet-leaf-node/`
