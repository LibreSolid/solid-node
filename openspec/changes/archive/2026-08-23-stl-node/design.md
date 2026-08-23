## Context

Many published mechanical designs exist only as STL meshes (motivating
reference: Dragon R1, printables.com/model/240045). The framework's
leaves all author geometry in a CAD backend; nothing imports a foreign
mesh. `JScadNode` is the structural precedent for a leaf whose source
is an external non-Python file: it resolves the declared file against
the wrapper module's directory, overrides `get_source_file()` so the
external file's mtime drives freshness, declares no `namespace`, and
owns its artifact inside `as_scad()` behind the up-to-date guard, with
the artifact back-stamped to the source mtime so `generate_stl()` never
launches OpenSCAD (`solid_node/node/adapters/jscad.py`, ADR-033).

Every design decision below was settled explicitly with the pilot.

## Goals / Non-Goals

**Goals:**

- A faceted `StlNode` leaf wrapping a committed STL file, assembling
  and fusing with the existing node structure.
- Fusion participation from day one — the design-a-piece-that-fits use
  case justifies the accepted OpenSCAD/CGAL mesh-union cost (ADR-045).
- Honest admission: fail fast on non-watertight meshes with
  `require_watertight = False` as the knowing escape hatch.
- Multi-body files treated as part packs with explicit, deterministic
  body selection and a self-describing inventory error.
- Normalization as code (`adjust` hook), not constructor knobs.

**Non-Goals (pilot-recorded):**

- No exact or faceted-B-rep STL import route — mesh-only is settled
  doctrine, not an open question.
- No provenance metadata (source URL, license) on the node API;
  provenance belongs to project/assembly documentation.
- No tooling that decomposes or reverse-engineers STL sets into
  assembly source; assemblies are authored normally.
- No scale/units/recenter constructor parameters.

## Decisions

### D1: JScadNode-shaped external-file leaf

`StlNode(LeafNode)` in `solid_node/node/adapters/stl.py`: `stl_source`
class attribute resolved via
`sys.modules[cls.__module__].__file__`'s directory, `get_source_file()`
returning the resolved path, `namespace = None`, `render()` returning
`self`. This inherits the whole freshness, artifact-path, and
skip-guard machinery unchanged. *Alternative rejected:* constructor
path argument — the class-attribute idiom is the established
external-file pattern and keeps one part = one named class.

### D2: The wrapper module joins the tracked source set

For a non-`.py` source, `source_closure()` returns only the file
itself (`solid_node/node/sources.py:73-76`), so JScad-style tracking
would leave `adjust` and `body` edits invisible to freshness.
`StlNode.__init__` therefore extends `self.files` with
`source_closure(<wrapper module file>)` — the wrapper and its
project-local imports, transitively, so a constant imported into an
`adjust` hook is tracked too. This is the over-approximation posture
`sources.py` already documents: an extra tracked file costs a rebuild,
a missing one serves stale geometry. *Alternative rejected:* teaching
`_parse_project_imports` about wrappers — the parser cannot know which
Python module wraps a given mesh; the node can.

### D3: `as_scad()` always materializes the node's own artifact

One code path: when the artifact is stale, load the source with
trimesh, select the body, apply `adjust`, gate on watertightness,
export binary STL to `self.stl_file` (temp-file-then-rename, following
`exact.write_stl`), back-stamp with
`os.utime(..., ns=(time.time_ns(), self.mtime_ns))`, and return
`import_stl(self.local_stl)`; when current, return the import
directly. No import-in-place special case for the trivial
single-body/no-hook file — it would buy one skipped copy at the cost
of a second code path, and downstream consumers (`import_optimized`,
piece identity, export, fusion) all expect the node-owned artifact.
The back-stamp keeps `generate_stl()`'s early return, so no external
tool ever runs for the leaf.

### D4: Fail-fast watertight gate with a declared escape hatch

Admission is judged at materialization time on the final mesh — the
selected body, after `adjust` — so a hook cannot smuggle a defect past
the gate and a broken neighbour in a pack cannot condemn a sound part.
`require_watertight = False` admits knowingly; it governs admission
only, never geometry, so it stays out of `uniq_id`. Because the
wrapper module is tracked (D2), flipping the flag touches the wrapper,
the artifact goes stale, and validation re-runs on the next build —
materialization-time checking is therefore sufficient; no live-path
re-validation is needed. *Alternatives rejected:* auto-repair
(silently machines geometry the user did not author), admit-anything
(CGAL's failure modes downstream are opaque), validate-and-warn
(pilot chose the stricter default).

### D5: Multi-body packs select with `body`, discovered via the error

A multi-body STL is a pack of separately printed parts, so each node
selects one: `body` class attribute, 0-based index into connected
components (`mesh.split(only_watertight=False)`) sorted by centroid,
lexicographic on x, then y, then z — deterministic because the
committed file's bytes are fixed, and human-guessable as plate reading
order. `body` unset on a multi-body file raises an error carrying the
count and per-body inventory (index, centroid, bounding box, volume):
the failure is the discovery tool, no CLI needed. Extraction preserves
file coordinates; reframing belongs to `adjust` or placement
operations. *Alternatives rejected:* reject multi-body outright
(defeats the pack use case), admit as one rigid part (parts packed
together are not one part), geometric selectors like body-at-point
(clumsier to author than an index read off the inventory).

### D6: `adjust(self, mesh)` — normalization is code, not knobs

An optional hook receiving the selected local-frame trimesh before the
artifact is written, returning the corrected mesh. Full trimesh power
(scale, mirror, recenter, arbitrary transforms) with no knob
vocabulary to invent; the correction is baked into the artifact so
every consumer sees one geometry. *Alternative rejected:* mutating
`self.mesh` from `render()` — `node.mesh` is a derived world-frame
view computed from the built artifact; it is downstream of the
artifact, not an input channel, and nothing that builds geometry
consumes it.

### D7: Validation by framework-generated round-trip fixtures

Tests author simple CadQuery nodes, export their STLs, then rebuild
the same parts through `StlNode` and assert equivalence — volume,
bounding box, near-zero boolean difference via manifold3d. Multi-body
fixtures concatenate known solids at distinct centroids. No binary
fixtures are committed to the framework repository; Dragon R1 remains
a named reference, deliberately not a test subject.

## Risks / Trade-offs

- [Fusion over dense meshes is slow] → Accepted by the pilot; CGAL
  union cost is inherent to ADR-045's faceted path.
  `docs/leaf-nodes.rst` states the consequence honestly instead of
  hiding it.
- [Large binary STLs committed to project repositories] → Accepted:
  the STL is project source. Projects with huge meshes can adopt their
  own storage discipline; the framework only requires the file inside
  the project root (the build mirror depends on it).
- [Body indices shift if the source file is replaced] → Accepted: the
  ordering is deterministic for fixed bytes, and replacing the file is
  an authored change reviewed like any other; the inventory error
  re-describes the pack on the next failure.
- [trimesh load semantics vary (Scene vs Trimesh)] → Load with
  `force='mesh'` and split into components explicitly, covered by
  multi-body tests.
- [`mesh.split()` component ordering is library-internal] → Never rely
  on it: always re-sort by the centroid rule before indexing.

## Migration Plan

Purely additive — a new adapter, a source-set extension local to it,
docs, and exports. No existing adapter, artifact, or project changes
behavior. Rollback is removal.

## Open Questions

None. All decisions above were settled explicitly with the pilot.
