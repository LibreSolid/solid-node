## 1. Environment

- [x] 1.1 Bring the bench environment to the framework's pins (cadquery
  2.7.*, build123d 0.10.*) and confirm `tests/test_build123d_adapter.py`
  collects and passes before any change, so the baseline is green and the
  stale-venv finding is not conflated with this change

## 2. Red-first tests

- [x] 2.1 Write `tests/test_sheet_leaf.py` covering the `sheet-parts`
  scenarios red: extruded volume = area × thickness from the XY plane;
  missing/non-positive thickness raises naming the node; two thicknesses
  yield distinct artifact identities; profile with holes accepted and
  pierced through; disjoint faces rejected; solid profile rejected naming
  node and type; DXF written beside STL; current artifacts not rewritten;
  missing DXF alone regenerates; circular hole survives as arc/circle
  entity (read back with ezdxf)
- [x] 2.2 Extend adapter-contract coverage red: `Build123dSheetNode.exact`
  true without rendering; not an instance of `Build123dNode` and vice
  versa; MRO backend walk resolves no mesh backend; fusion mixing
  `Build123dSheetNode` with a `CadQueryNode` child is exact and fuses to
  one solid; sheet leaf builds with no `openscad` on PATH

## 3. Implementation

- [x] 3.1 Add `SheetLeafNode` (abstract, under `ExactLeafNode`): owns
  `render()` = validate(profile()) extruded +Z by `thickness`; thickness
  required positive at construction; profile validation (one planar face,
  holes inside) raising with node name and offending type
- [x] 3.2 Add `Build123dSheetNode`: `namespace = 'build123d'`; accepts
  `Sketch`, `Face` or `BuildSketch` builder from `profile()`, normalised
  to one `Face`; extrusion in build123d terms
- [x] 3.3 Add the DXF artifact: `dxf_file` path beside `stl_file`;
  `as_scad()` writes it when stale via build123d `ExportDXF` (atomic
  write, artifact mtime conventions); extend `_render_can_be_skipped()`
  to require it current
- [x] 3.4 Export the new classes from `solid_node.node` without importing
  build123d eagerly beyond what the existing adapters already cost

## 4. Green and validation

- [x] 4.1 Run the new tests green and the full framework suite; confirm
  the pre-existing pass/fail set is otherwise unchanged
- [x] 4.2 Build a representative caller: a minimal panel-with-holes sheet
  project (frame-panel shaped, t-slot-like cutouts) under `tests/` or
  `examples/`, asserting its DXF content and STL volume; inspect a
  snapshot render as pixel evidence

## 5. Documentation and records

- [x] 5.1 Update `docs/leaf-nodes.rst` with the sheet leaf kind: profile
  contract, thickness, the nominal DXF artifact, and what is deliberately
  not yet covered (kerf, SVG, engraving)
- [x] 5.2 After implementation confirms the design, extract the ADR for
  the sheet-leaf architecture decision (authored profile as source of
  truth; DXF in the artifact lifecycle), update `docs/adrs/README.md` and
  `docs/architecture.md`
