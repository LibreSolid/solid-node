# ADR-054: An imported mesh is admitted, selected and corrected explicitly

**Status:** Accepted

**Date:** 2026-08-23

**Change:** `stl-node`

**Depends on:**
- [ADR-004: Multi-CAD Backend Adapter Pattern](ADR-004-multi-cad-backend-adapter-pattern.md)
- [ADR-006: Mtime-based STL caching](ADR-006-mtime-based-stl-caching-strategy.md)
- [ADR-044: Derived exact-geometry capability](ADR-044-derived-exact-geometry-capability.md)
- [ADR-045: Exact fusion composition](ADR-045-exact-fusion-composition.md)
- [ADR-046: Conditional OpenSCAD dependency](ADR-046-conditional-openscad-dependency.md)
- [ADR-050: Nanosecond-fidelity artifact freshness](ADR-050-nanosecond-fidelity-artifact-freshness.md)

## Context and Problem Statement

Many worthwhile mechanical designs are published only as STL meshes. The
motivating reference is the Dragon R1 open-source RC car
(printables.com/model/240045): a maker who wants to build it, or to design a
new bracket that bolts onto it, has a folder of `.stl` files and no CAD
source at all.

Every leaf the framework had authors its geometry in a backend, and
`import_stl` appeared only as the way a node re-imports *its own* build
artifact. So a downloaded part could not enter a project: not as a child of
an assembly, not as a neighbour in a fusion, not as something to test a new
part against.

Making a mesh into a part is easy to do credulously and hard to do honestly.
A published mesh is not a CAD model: it may not be a closed solid, it may
hold a whole print plate of unrelated parts, it may be in inches, and it
carries no design intent to recover. Each of those is a place where the
framework can either state a rule or silently guess.

## Decision Drivers

- A part is a part: an imported mesh must assemble, fuse, export, cache and
  test like every other leaf, or it is a second-class citizen and every
  downstream subsystem grows a special case.
- Downstream consumers are entitled to a closed solid. CGAL, `manifold3d`,
  volume assertions and slicers all assume one, and their failure modes when
  it is absent are opaque and far from the cause.
- A guess the framework makes silently is a defect the maker cannot see.
  Repairing a mesh, picking a body, or scaling by a heuristic all change
  geometry nobody authored.
- Normalization needs are open-ended (scale, mirror, reframe, decimate,
  arbitrary transforms). A knob vocabulary for them would be invented
  speculatively and would never be complete.
- The build's artifact rules are already settled (produce only when stale,
  stamp with the source mtime, one artifact per node); a new leaf should
  inherit them rather than invent a parallel lifecycle.

## Considered Options

1. **A faceted `StlNode` leaf that materializes its own artifact, gates
   admission, selects bodies by index and normalizes through a code hook**
   (Chosen)
2. Import the committed file in place when nothing needs changing, and
   materialize an artifact only when it does
3. Admit any mesh, repairing what can be repaired, and let downstream tools
   report whatever they report
4. Route the mesh through a B-rep kernel (CadQuery's STL import) so an
   imported part could be exact

## Decision Outcome

Chosen option: **`StlNode(LeafNode)`, a faceted leaf whose part is a
committed STL file, structured like `JScadNode` and honest about what a mesh
is.** Five consequences follow.

- **The node owns its artifact, always.** `stl_source` resolves against the
  wrapper module's directory, `get_source_file()` returns it so its mtime
  drives freshness, and `as_scad()` materializes the node's own `.stl` from
  it whenever that artifact is stale — body selected, `adjust` applied,
  written in binary through a temp-file-then-rename, stamped with the source
  mtime in integer nanoseconds (ADR-050). There is deliberately **no**
  import-in-place path for the trivial file: it would buy one skipped copy at
  the cost of a second code path, and every downstream consumer
  (`import_optimized`, piece identity, export, fusion, the viewer) expects
  the node-owned artifact. Because the artifact is back-stamped, the
  `generate_stl()` guard returns early and *no external tool runs for the
  leaf at all* — this is the first adapter with no backend whatsoever
  (ADR-046).

- **Admission is a gate, not a warning.** A selected mesh that is not
  watertight raises at materialization, naming the file, the selected body
  and the defect (the count of open edges), and writes no artifact.
  `require_watertight = False` admits it knowingly. Nothing is auto-repaired:
  filling holes would machine geometry the project did not author, and the
  maker would never learn it happened. The flag governs admission only — it
  never alters geometry and is not a constructor parameter, so it stays out
  of `uniq_id`. The check runs on the *final* mesh, after body selection and
  after `adjust`, so a hook cannot smuggle a defect past it and a torn
  neighbour in a pack cannot condemn a sound part.

- **A multi-body file is a pack of parts, and a node is one of them.** `body`
  is a 0-based index into the file's connected components, ordered by
  centroid and compared lexicographically on x, then y, then z — plate
  reading order, deterministic for a fixed file. `split()`'s own ordering is
  library-internal and is never relied on; the components are re-sorted
  before anything is indexed, and splitting is done with repair disabled so
  the gate judges the file's real geometry. A node that omits `body` on a
  multi-body file fails with the pack's full inventory — count, and per body
  the index, centroid, bounding box and volume — so **the failure is the
  discovery tool** and no inspection command has to exist. An out-of-range
  index fails the same way. Extraction preserves the file's coordinates: the
  part stays where it sat on the plate, and reframing is a placement
  operation or the hook below.

- **Normalization is code.** An optional `adjust(self, mesh)` receives the
  selected body as a trimesh and returns the corrected mesh. Full trimesh
  power, no knob vocabulary to invent, and the correction is baked into the
  artifact so fusion, tests, export and the viewer all see one geometry. The
  rejected alternative was mutating `self.mesh` from `render()`: `node.mesh`
  is a derived world-frame view computed *from* the built artifact — it is
  downstream of the artifact, not an input channel.

- **Mesh-only is doctrine, not a gap.** `StlNode` is faceted: `exact` is
  false, it exposes no `shape()`, and a fusion containing one is faceted and
  unions through the OpenSCAD/CGAL path (ADR-045). Fusion participation is
  supported from day one because designing a piece that fits a published part
  is the use case the leaf exists for; the CGAL cost on a dense mesh is real,
  was accepted explicitly, and is stated in `docs/leaf-nodes.rst` rather than
  hidden. There will be no exact or faceted-B-rep import route: a triangle
  soup does not carry the intent a B-rep encodes, and reconstructing one
  guesses where a fillet was meant and which faces were one cylinder.

Provenance metadata (source URL, licence) is deliberately not part of the
node API — those obligations are real, but they belong to project and
assembly documentation, not to a class attribute the framework would have to
pretend it can validate. Nor will the framework decompose an STL set into
assembly source; assemblies are authored with the nodes and operations that
already exist.

## Pros and Cons of the Options

### Faceted leaf, own artifact, gated admission, indexed bodies, code hook

- **Good**: An imported part is an ordinary leaf everywhere downstream
- **Good**: Every guess the framework could have made silently is instead a
  declaration the maker writes, or an error that teaches them what to write
- **Good**: One code path in `as_scad()`, inheriting the whole freshness and
  artifact lifecycle unchanged
- **Good**: No new dependency — trimesh is already the framework's mesh
  currency, and splitting, watertightness and binary export are its own
  operations
- **Bad**: A trivial single-body file is copied into an artifact that is
  byte-comparable to its source
- **Bad**: Body indices are positional, so replacing the source file can
  renumber them

### Import the committed file in place when nothing needs changing

- **Good**: Skips one copy for the simplest case
- **Bad**: Two code paths for one behavior, diverging exactly where the
  behaviour is subtlest (freshness, identity, export)
- **Bad**: Downstream consumers would sometimes see a project source file and
  sometimes a build artifact, with different lifetimes and different rules

### Admit anything and let downstream tools complain

- **Good**: Nothing to declare; the leaf is a dozen lines
- **Bad**: CGAL's failure on a non-solid is opaque and arrives far from the
  cause, often as a wrong volume rather than an error
- **Bad**: Auto-repair, the other half of this option, changes geometry
  nobody authored and is invisible in the result

### Route the mesh through a B-rep kernel

- **Good**: An imported part could join exact fusions and expose `shape()`
- **Bad**: The result is a faceted B-rep — thousands of planar faces — which
  is exactness in name only and slower than the mesh path it replaces
- **Bad**: It invites the belief that the framework recovered design intent
  from triangles, which it did not and cannot

## Consequences

A project can now be built from parts nobody in it modelled, and a new part
can be designed against a downloaded one by fusing with it. That is a
genuinely new capability class for the framework, and it is the first leaf
whose build requires no CAD tool at all.

The costs are stated rather than absorbed. A fusion touching an imported mesh
is faceted and pays CGAL's price. Committed meshes are project source and can
be large; the framework requires only that they sit inside the project root
(the build mirror depends on it), leaving storage discipline to the project.
Body indices are positional, so replacing a pack file is an authored change
that must be reviewed — the inventory error re-describes the pack the next
time it is needed.

The validation strategy is worth recording: no binary fixture is committed to
the framework. Tests author parts in CadQuery, export their meshes, and read
them back through `StlNode`, so the round trip itself is the evidence, and
multi-body fixtures concatenate known solids at known centroids. Dragon R1
stays a named motivating reference, deliberately not a test subject.

## References

- `solid_node/node/adapters/stl.py` — `StlNode`, `_bodies()`,
  `_write_binary_stl()`
- `tests/test_stl_node.py` — declaration and freshness, materialization and
  round trip, the watertight gate, pack selection and the inventory, the
  `adjust` hook, adapter distinctness
- `tests/stl_project/` — the representative caller: imported parts placed in
  an assembly, and one fused with a part designed to fit it
- `docs/leaf-nodes.rst` — the STL leaf kind
- [ADR-055: The wrapper module joins an imported part's source
  set](ADR-055-wrapper-module-in-the-imported-part-source-set.md)
- `openspec/changes/stl-node/`
