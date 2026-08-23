## Why

Many worthwhile mechanical designs are published only as STL meshes, not
as CAD source — the Dragon R1 open-source RC car
(https://www.printables.com/model/240045-dragon-r1-open-source-rc-car)
is the motivating reference. The framework has no way to bring such a
part into a project: every leaf today authors its geometry in a CAD
backend, and `import_stl` is used only for a node's own build artifact.
Without an STL leaf, a maker cannot assemble downloaded parts under
source control, and cannot design a new part that fits an existing mesh
by subtracting or referencing it in a fusion.

## What Changes

- A new faceted leaf adapter, `StlNode`, wrapping a committed `.stl`
  file declared by a `stl_source` class attribute, following the
  external-file pattern of `JScadNode`: the file resolves relative to
  the wrapper module's directory, `get_source_file()` returns it so its
  mtime drives freshness, `namespace` is `None`, and `exact` is false.
- Unlike the other external-file adapters, the wrapper `.py` module
  joins the node's tracked source set alongside the `.stl`, because the
  wrapper carries geometry-affecting code (`adjust`, `body`).
- `as_scad()` always materializes the node's own STL artifact from the
  source when stale — selected body extracted, `adjust` applied,
  normalized to binary, mtime-stamped like the JSCAD artifact so
  OpenSCAD is never launched for the leaf itself.
- Admission gate: a non-watertight (selected) mesh fails fast at build
  with an error naming the file and defect; `require_watertight = False`
  admits it knowingly. The flag governs admission, not geometry, and
  stays out of artifact identity.
- Multi-body files are part packs: a `body` class attribute selects one
  connected component, 0-based, ordered deterministically by centroid
  (x, then y, then z). With `body` unset on a multi-body file, the
  error reports the body count and an inventory line per body (index,
  centroid, bounding box, volume). Extraction preserves the file's
  coordinates; watertightness is judged on the selected body.
- Normalization is code, not knobs: an optional `adjust(self, mesh)`
  hook receives the local-frame trimesh before the artifact is written
  and returns the corrected mesh (scale, recenter, arbitrary trimesh
  operations). No scale/units/recenter constructor parameters.
- `StlNode` participates in `FusionNode` from day one; the enclosing
  fusion becomes faceted and unions through the OpenSCAD/CGAL mesh path
  (ADR-045), a cost the pilot accepted for the design-a-piece-that-fits
  use case. Documentation states the consequence honestly.
- Documentation: `docs/leaf-nodes.rst` gains the STL leaf kind.

Out of scope, recorded as explicit non-goals: a faceted-B-rep import
route (CadQuery STL import) or any future "exact StlNode" — mesh-only
is settled doctrine; provenance metadata (source URL, license) on the
node API — provenance belongs to project/assembly documentation; any
tooling that decomposes or reverse-engineers STL sets into assembly
source — assemblies are authored the normal way with existing nodes and
operations.

## Capabilities

### New Capabilities
- `stl-import`: wrapping an external STL file as a project part — the
  source declaration and freshness contract, the watertight admission
  gate and its escape hatch, body selection from multi-body packs with
  the inventory error, the `adjust` normalization hook, and the
  materialized artifact.

### Modified Capabilities
- `node-model`: the multi-backend leaf adapter roster gains `StlNode`;
  the distinct-types rule, the produce-only-when-stale artifact rule,
  the no-OpenSCAD-for-own-artifact behavior, and the
  mesh-only/not-exact enumeration extend to it. The wrapper-module
  tracking rule is specified under `stl-import`; it adds files to a
  node's tracked set, which `build-pipeline`'s track-more-rather-
  than-fewer posture already permits, so no `build-pipeline` delta is
  needed.

## Impact

- `solid_node/node/adapters/`: new `stl.py` adapter;
  `solid_node/node/__init__.py` exports.
- `solid_node/core/sources.py`: the non-Python source closure gains the
  StlNode wrapper-module inclusion.
- Dependencies: none added — trimesh is already the mesh currency;
  splitting, watertightness, and binary export are existing trimesh
  operations.
- Docs: `docs/leaf-nodes.rst`, `docs/architecture.md` adapter roster.
- Empirical grounding: Dragon R1 is the motivating reference, too
  complex to serve as a test subject. Validation uses round-trip
  fixtures the framework generates itself: simple CadQuery nodes export
  STLs, `StlNode` rebuilds the same parts, and tests assert equivalence
  (volume, bounding box, near-zero boolean difference).
