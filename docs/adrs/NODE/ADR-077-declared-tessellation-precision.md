# ADR-077: Declared tessellation precision

**Status:** Accepted

**Date:** 2026-09-06

**Change:** `declared-tessellation-precision`

**Depends on:**
- [ADR-071: Node-Scoped Content Currency](./ADR-071-node-scoped-content-currency.md)
- [ADR-026: Node Identity — Parameter-Hashed Artifact Keys vs Tree Names](./ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md)
- [ADR-063: Identity From Resolved Declared Values](./ADR-063-identity-from-resolved-declared-values.md)
- [ADR-044: Derived exact-geometry capability](./ADR-044-derived-exact-geometry-capability.md)
- [ADR-045: Exact fusion composition](./ADR-045-exact-fusion-composition.md)
- [ADR-047: One shared OCCT currency for every exact backend](./ADR-047-shared-occt-currency-for-exact-backends.md)

## Context and Problem Statement

A node cannot say how finely its solid should be tessellated. Every exact
STL artifact the framework writes — a leaf's and a fused solid's alike —
went through `solid_node/exact.py`'s `write_stl`, which fixed
`tolerance=0.1, angularTolerance=0.1` (CadQuery's historical
`cq.exporters.export` defaults) in its own body, with no way for a node
to ask for anything else.

Vendor STEP geometry is overwhelmingly fillets and threads, where 0.1
rad of angular deflection costs an order of magnitude in artifact size
for surface a viewer cannot see. Two projects reached around the
framework for the same lever, at the same values: `openvmp`
(`simulation/don1/parts.py`) calls `BRepMesh_IncrementalMesh` directly
inside `render()` to premesh a vendor shape at 0.1 mm / 0.5 rad before
returning it, relying on the fact that `Shape.exportStl` reuses a
triangulation already stored on the shape rather than meshing again;
Internal-Cycloidal-Actuator does the same and measured the cost on a 35
MB Inventor STEP assembly — `Output_Shaft` at 19.9 MB (398,184 triangles)
under the framework's default against 1.8 MB (35,776 triangles) at the
premeshed value, calling the lever "a trick, not an interface" and
recording the failure mode it depends on: "if the framework's export
ever meshes unconditionally, every part in this project silently grows
by 10x." `docs/warts.md` had deferred a fix until a second project
asked; it has. And the lever is about to disappear: a `StepNode` project
reading a STEP file itself has no `render()` in which to premesh.

Two prior decisions frame the design. ADR-071 made currency node-scoped:
a node's digest is its own class's text within its source file plus the
closure of what it imports, so a value written in a node's class body
already invalidates that node and nothing else. ADR-026/063 key an
artifact by the node's resolved declared values, and
`SheetLeafNode.thickness` shows both sides of that line — passed as a
constructor kwarg it reaches `uniq_id` and makes two artifacts; declared
as a class attribute it rides the source-set path instead. Tessellation
precision belongs unambiguously on the second side: two tessellations of
one solid are one node at two times, not two nodes.

## Decision Drivers

- The framework's historical values must remain the default, so no
  existing artifact and no existing project changes.
- The declaration must reach the artifact through a currency path that
  already exists, adding no new staleness rule to get wrong.
- A future `StepNode` project, which will have no `render()` to premesh
  in, needs the lever the two originating projects have today.
- Precision is a property of the part, not of one build or one run: no
  constructor parameter, no `--set` knob, no project- or run-level
  override.
- `write_stl` should not keep holding a policy it has no business
  holding.

## Considered Options

1. **Two class attributes, `linear_deflection` and `angular_deflection`,
   read and validated at export time by a resolver in `exact.py`**
   (chosen)
2. `tolerance` / `angular_tolerance`, CadQuery's own `exportStl` parameter
   names
3. `mesh_deflection` / `mesh_angle`, openvmp's own module-constant names
4. One declaration object, `Tessellation(linear=…, angular=…)`, in the
   `Time(loop=…)` / `Driver(…)` idiom (ADR-072, ADR-061)
5. A constructor parameter or a run-level `--set`/CLI override

## Decision Outcome

Chosen: **two plain class attributes named after OCCT's own quantities**,
declared with the framework's historical defaults on the two classes that
call `write_stl` — `ExactLeafNode` and `FusionNode` — and resolved by one
helper, `deflections(node)`, at the point each writes its artifact.

- `linear_deflection` (mm) — OCCT's `theLinDeflection`, the maximum
  distance between the mesh and the surface it approximates.
- `angular_deflection` (rad) — OCCT's `theAngDeflection`, the maximum
  angle between the normals of two adjacent facets.

A node declaring neither is tessellated at `linear_deflection = 0.1`,
`angular_deflection = 0.1`, byte-for-byte what the framework has always
written. A node may declare either alone; the other keeps its default.
Each is validated where it is read — a real number, `bool` excluded,
finite, strictly positive — naming the node and the attribute when it is
not. `write_stl(shape, path, mtime_ns, linear_deflection,
angular_deflection, digest=None)` takes both as required positional
arguments rather than defaulting them, so the framework's historical
values live in exactly one place a reader can find: the class attribute
declarations, not a second default buried in the writer.

The declaration is **not** a constructor parameter and **not** artifact
identity. It lives in the module declaring the node class, which the
node already tracks in its source set, so editing it makes the node's
artifacts stale through the ordinary content-currency path (ADR-071) —
the same route `SheetLeafNode.thickness` takes when declared rather than
passed — and does not enter `uniq_id` (ADR-026/063): a project sweeping
precision while tuning gets one artifact rewritten in place, not a build
directory accumulating meshes of the same part.

`FusionNode` declares its own pair for the solid it fuses, and does not
inherit either from a child: the fused solid is a different shape than
any child's, so there is no defensible way to pick a winner among
disagreeing children. A fusion that wants a coarse fused solid says so on
itself.

The `.brep` artifact and `shape()` are unaffected by either declaration —
exactness is a property of the geometry, a mesh tolerance is a property
of one derived representation of it. Everything that reads the mesh
afterward — the viewer, the export, a faceted `solid test --faceted`
comparison, and printed-piece identity (ADR-043, a fingerprint of built
artifact content) — sees the declared precision as a consequence of that
fact, not as a rule of its own; a node redeclared at a new precision is a
different piece from the one built before.

The faceted adapters (`Solid2Node`, `OpenScadNode`, `JScadNode`,
`StlNode`) do not carry the attributes: the framework never tessellates
their geometry, so there is nothing for a deflection to shape.
`MolejoNode` is tessellated by molejo's own evaluator and is out of
scope.

### Why not option 2 (`tolerance` / `angular_tolerance`)

CadQuery's own `exportStl` parameter names, camelCase in their own API,
buy no continuity for the reader here, and "tolerance" alone says nothing
about what it bounds — the pair reads as though one is a special case of
the other.

### Why not option 3 (`mesh_deflection` / `mesh_angle`)

`mesh_angle` loses the unit and the meaning: it is not the angle of
anything, it is the deflection bound between two facet normals. OCCT's
own vocabulary — linear deflection, angular deflection — is what a
project author searches and finds explained in the kernel's own
documentation.

### Why not option 4 (a declaration object)

That idiom exists for declarations the framework must enumerate off a
class, bind per instance, refuse assignment to, or publish into a
document — none of which applies here. Two plain numbers read once at
export time need no descriptor; `SheetLeafNode.thickness` is the
precedent for a scalar that shapes the artifact and rides the source set
as a bare class attribute.

### Why not option 5 (a parameter or run-level override)

Precision is a property of the part, declared where the part is
declared. A run-level override would make one project's artifacts depend
on how they happened to be built, and a constructor parameter would put
precision in `uniq_id`, contradicting the very claim this ADR makes:
two tessellations of one solid are one node at two times.

### Validating at export, not at construction

`deflections(node)` is read immediately before each `write_stl` call
site (`ExactLeafNode.as_scad`, `FusionNode.generate_stl`), not in
`__init__`. A node whose artifacts are current never writes an STL, so
validating at construction would do work on every node of every build to
catch a mistake that only matters when a mesh is written; it would also
have to live in `__init__`, where the declarative node API deliberately
put nothing (ADR-061) — `check()` is about parameters, not export
policy. The cost is that a bad value is reported on the build that writes
the artifact rather than the one that loads the class, which is not
observable in practice: any build that would have caught it at
construction also writes the artifact.

## Consequences

- `solid_node/exact.py` gains `deflections(node)` and `write_stl` takes
  two required positional arguments instead of fixing them; every caller
  (`ExactLeafNode.as_scad`, `FusionNode.generate_stl`, and the direct call
  in `tests/test_exact_geometry.py`) was updated.
- `ExactLeafNode` and `FusionNode` each declare
  `linear_deflection = 0.1` and `angular_deflection = 0.1`. `SheetLeafNode`
  and every OCCT-backed leaf inherit them unchanged.
- **Unplanned finding, fixed under this change:** `ExactLeafNode.as_scad`
  used to write the STL before the BREP. `Shape.exportStl` calls
  `BRepMesh_IncrementalMesh`, which stores its triangulation ON the
  shape object, and `Shape.exportBrep` serialises whatever triangulation
  a shape is carrying alongside its topology — so two builds of one
  solid at different declared precision produced byte-different `.brep`
  files despite identical topology, contradicting this ADR's own claim
  that `.brep` and `shape()` are unaffected. Writing the BREP first, from
  the not-yet-meshed shape, removed the coupling; `FusionNode` already
  wrote its BREP before its STL and needed no change. Confirmed
  empirically (a BREP written after `exportStl` differs from one written
  before it; two written before differ from neither).
- A project author who declares a coarse `angular_deflection` and then
  runs `solid test --faceted` can see a clearance verdict move, because
  a faceted comparison is answered on the compared nodes' meshes at
  whatever precision they carry; the exact kernel, the default, is
  unaffected because it never reads the mesh. Documented at the point of
  declaration (`docs/leaf-nodes.rst`, `docs/fusion.rst`) rather than left
  to be discovered from a diff.
- Redeclaring precision changes a node's printed-piece id (ADR-043),
  since that id fingerprints built artifact content. Documented as a
  scenario, not a surprise.
- No existing artifact and no existing project changes: an undeclared
  node is tessellated exactly as it always was, and nothing is migrated
  by this change alone. `openvmp` and `Internal-Cycloidal-Actuator`
  migrate their own `premesh()` workaround away on their own schedule, in
  their own repositories.
- Not built here: relative deflection or any other OCCT meshing knob
  (`theRelative`, parallel meshing) — neither originating project asked
  for one; a metaclass refusal of the attributes on the faceted adapters
  — a class attribute the framework never reads is ordinary Python, not a
  new failure mode to guard; and the shop's
  `shop-skills/solid-node-api/SKILL.md` documentation of the declaration,
  which is a shop file changed in the shop's own repository.

## References

- `solid_node/exact.py` — `deflections`, `write_stl`
- `solid_node/node/exact_leaf.py` — `linear_deflection`,
  `angular_deflection`, `as_scad`
- `solid_node/node/fusion.py` — `linear_deflection`, `angular_deflection`,
  `generate_stl`
- `tests/test_tessellation_precision.py`
- `docs/leaf-nodes.rst` — "Tessellation precision"
- `docs/fusion.rst` — "Tessellation precision"
- OpenSpec change `declared-tessellation-precision`, capability
  `exact-geometry`
