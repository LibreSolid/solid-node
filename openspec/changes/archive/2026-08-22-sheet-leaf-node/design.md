## Context

The `metamaquina-rebuild` project will model a laser-cut printer frame:
parametric MDF panels sharing one `thickness` knob, joined by t-slots. The
framework's leaf kinds all author a solid; none can promise a part is a
constant-thickness profile cut from sheet stock, and none produces an
artifact a laser cutter consumes.

The pieces already on the board:

- `LeafNode` → `ExactLeafNode` (ADR-047): every exact backend converts its
  render result to one shared OCCT currency (`cq.Shape`) at the adapter
  boundary; `ExactLeafNode` owns `exact`, `shape()` and `as_scad()`, which
  writes the STL and BREP when stale.
- `LeafNode._render_can_be_skipped()` enumerates the artifacts that must be
  current for a leaf's build work to be skipped.
- `node-model` requires adapters to remain distinct types even when they
  share a base, because `generate_stl` resolves backends by walking the MRO
  for adapter class names.
- build123d 0.10 is already pinned (`pyproject.toml`), ships `ExportDXF`,
  and brings `ezdxf` transitively.

## Goals / Non-Goals

**Goals:**

- One authored profile from which both the solid (tree, viewer, tests) and
  the nominal cut file derive, with no path for them to diverge.
- A sheet leaf that participates in every existing capability untouched:
  assemblies, fusions (exact), pieces inventory, viewer, caching.
- The DXF as a first-class build artifact under the existing freshness
  machinery.

**Non-Goals:**

- SVG profile import, kerf compensation, engraving, material/process
  metadata, nesting, and any production-export CLI command. Each waits for
  its own project evidence. The persisted exact BREP already preserves the
  profile for a future kerf-offsetting exporter.
- A CadQuery sheet adapter. The conversion seam exists (any planar face can
  be rewrapped), but no caller needs it.

## Decisions

**1. `SheetLeafNode` is an abstract base under `ExactLeafNode`; the concrete
v1 adapter is `Build123dSheetNode`.**

The sheet base owns `render()`: it calls `self.profile()`, validates the
result, and extrudes it by `thickness` along +Z from the XY plane. The
subclass's extension point is `profile()` only. Overriding `render()` is
unsupported — it would break the single-source invariant the type exists
for. Alternative rejected: letting any leaf declare "laser-cut" and
recovering the profile by slicing its solid; deriving 2D from authored 3D
is an inverse problem (slicing plane choice, thickness verification, curve
reconstruction), while authoring 2D and deriving 3D is a projection.

**2. The extrusion happens in build123d terms; the exact pipeline is
entered exactly where every other exact adapter enters it.**

`Build123dSheetNode.render()` (inherited from the sheet base, parameterised
by the adapter) returns `build123d.extrude(profile, amount=thickness)` — a
build123d `Part`. From there `ExactLeafNode`'s existing machinery does
everything: namespace validation (`namespace = 'build123d'`),
`shape_from_rendered()` rewrap, STL/BREP writes, SCAD emission. No change
to `exact.py` is needed; the module-name recognition of build123d results
already covers the extruded part.

**3. The DXF is written in `as_scad()` beside the STL and BREP, and joins
the skip guard.**

`SheetLeafNode` overrides `as_scad()` to call the inherited implementation
and additionally write `self.dxf_file` (same naming scheme as `stl_file`/
`brep_file`, extension `.dxf`) when not `_up_to_date`, from the validated
profile via build123d's `ExportDXF` — arcs preserved, model units,
millimeters. `_render_can_be_skipped()` is extended in the sheet base to
require the DXF current as well. The write uses the same atomic-write and
mtime conventions the other artifacts use (ADR-050 nanosecond freshness).
Alternative rejected: exporting DXF from the shared `cq.Shape` currency in
`exact.py` — it would push backend-specific 2D export into the deliberately
backend-neutral exact layer, and the profile is available in build123d
form in the only adapter that exists.

**4. Profile validation is the sheet base's, phrased per adapter.**

The base demands exactly one planar face (one outer wire, holes inside,
one part per leaf) and raises naming the node and the offending type. The
build123d adapter accepts a `Sketch`, a `Face`, or a `BuildSketch` builder
(mirroring `Build123dNode`'s acceptance of `BuildPart`), normalising to one
`Face`; two disjoint faces are rejected even though they share the
`build123d` namespace.

**5. `thickness` is a required node parameter.**

Class attribute or constructor kwarg, validated positive at construction.
As a constructor argument it flows into `uniq_id` (ADR-026) unchanged, so
two thicknesses of one panel are distinct artifacts for free; as a class
attribute a change touches the source file, which the source-set freshness
path (ADR-033) already turns into a rebuild.

**6. Type distinctness is preserved by construction.**

`Build123dSheetNode` subclasses `SheetLeafNode`, not `Build123dNode`; no
adapter appears in another's MRO, so the `generate_stl` backend walk and
`isinstance` checks are undisturbed. A test pins this, as
`test_build123d_adapter.py` pins it for the existing pair.

## Risks / Trade-offs

- [The workspace venv is stale: cadquery 2.5.2, no build123d, so the
  existing build123d adapter tests cannot even collect there] → The bench
  environment must be brought to the framework's pins (`pip install -e .`
  resolving cadquery 2.7 + build123d 0.10) before red-first work; this is
  an environment update to the pilot's shared venv and is reported before
  implementation, not silently performed.
- [build123d 0.10's `ExportDXF` API may differ from current docs] →
  Exercise it in the red-first test against the pinned version; the
  fallback within the same design is writing entities through `ezdxf`
  directly from the same validated face.
- [A future second sheet backend (e.g. CadQuery) could tempt per-backend
  DXF exporters] → The validated-face-to-DXF step is kept a private,
  single-purpose function so a later change can lift it behind a
  conversion at the adapter boundary, per ADR-047's pattern.
- [Sheet parts in the viewer/pieces inventory are just solids; nothing
  surfaces "this is a sheet part" to a consumer] → Accepted for v1; the
  DXF artifact on disk is the consumer-facing evidence, and richer
  metadata is deferred with the production-export design.

## Migration Plan

Purely additive: no existing adapter, artifact, spec behavior, or project
changes. Rollback is removing the new module and exports.

## Open Questions

None blocking. Deferred questions (SVG import, kerf, engraving, nesting,
production export command) are recorded in the proposal as out of scope.
