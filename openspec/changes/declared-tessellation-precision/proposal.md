## Why

A node cannot say how finely its solid should be tessellated. Every exact
STL artifact the framework writes — a leaf's and a fused solid's alike —
goes through `exact.write_stl`, which fixes `tolerance=0.1,
angularTolerance=0.1` in its own body. Vendor STEP geometry is fillets and
threads, and 0.1 rad of angular deflection over such a part costs an order
of magnitude in artifact size for surface a viewer cannot see.

Two projects have now reached around the framework for the same lever, at
the same values, and the shop's `docs/warts.md` deferred the fix until the
second one asked:

> 5. **Per-node tessellation precision.** openvmp's stored triangulation in
>    render() is a legitimate workaround; one project asks. Propose when a
>    second one does.

- **openvmp** (`simulation/don1/parts.py`) stores a triangulation on every
  vendor shape before returning it, so that the export reuses it:
  `BRepMesh_IncrementalMesh(shape.wrapped, 0.1, False, 0.5, True)`, under a
  comment that states the reason — "Vendor STEP files are all fillets and
  threads, and at 0.1 rad the robot's meshes came to 200 MB; a
  triangulation stored on the shape at the same linear precision is what
  the export writes."
- **Internal-Cycloidal-Actuator** is the second project to ask, and it
  measured the cost. Its design record
  (`openspec/changes/simulate-the-internal-cycloidal-actuator/design.md`,
  "What the framework made this project do by hand") reports, for a 35 MB
  Inventor STEP assembly of 55 occurrences and about 800 solids:

  | part | framework default (0.1 mm, 0.1 rad) | stored (0.1 mm, 0.5 rad) |
  | --- | --- | --- |
  | `Output_Shaft` | **19.9 MB**, 398,184 triangles | **1.8 MB**, 35,776 triangles |
  | `Rotor` | **0.7 MB**, 13,956 triangles | **0.3 MB**, 5,264 triangles |

  and states the conclusion: "The project gets the second number only by
  reaching past the public API into `BRepMesh_IncrementalMesh` and
  exploiting the fact that `exportStl` reuses an existing triangulation.
  That is a trick, not an interface. … **This is the second project to ask,
  and its worst part is 11× over.**" Its own risk register says the trick
  breaks the moment the framework meshes unconditionally: "if the
  framework's export ever meshes unconditionally, every part in this
  project silently grows by 10×."

Why now, beyond the second asking: the workaround lives in `render()`,
which is the project's own code. The `StepNode` leaf proposed next in this
worktree reads a STEP file itself, so a project using it has no `render()`
in which to premesh the shape. The only lever two projects have is about to
be taken away, and the interface has to replace it.

## What Changes

- Every node that writes an exact STL artifact — an `ExactLeafNode` (and so
  `CadQueryNode`, `Build123dNode`, `Build123dSheetNode`, and the coming
  `StepNode`) and a `FusionNode` fusing exact children — MAY declare two
  class attributes, `linear_deflection` (mm) and `angular_deflection`
  (radians), that shape its own STL artifact. Undeclared, they keep the
  values `write_stl` uses today: 0.1 mm and 0.1 rad. Nothing about an
  existing project's artifacts changes.
- A declared value that is not a positive finite number fails at the point
  it is read, naming the node and the attribute.
- `exact.write_stl` takes the two tolerances as arguments instead of fixing
  them. Degenerate-triangle removal is unchanged.
- The declaration is **not** a constructor parameter and **not** artifact
  identity. It lives in the module that declares the node class, which the
  node already tracks in its source set, so editing it makes the artifact
  stale through the ordinary content-currency path (ADR-071) — the same
  route `SheetLeafNode.thickness` takes when it is declared rather than
  passed.
- A `FusionNode` declares precision for the solid it fuses. It does not
  inherit its children's declarations: each child's declaration shaped only
  that child's own artifact, and the fused solid is a different tessellation
  of a different shape.
- The `.brep` artifact and `shape()` are untouched. Precision shapes only
  the mesh — and therefore the viewer, the export, the faceted test
  kernel's verdicts, and printed-piece identity, which is derived from
  artifact content (ADR-043) and so changes when the mesh does.
- The faceted adapters (`Solid2Node`, `OpenScadNode`, `JScadNode`,
  `StlNode`) do not carry the attributes: the framework does not tessellate
  their meshes, so there is nothing for a deflection to shape.
  `MolejoNode` is a `FlexibleNode` whose geometry is tessellated by
  molejo's own evaluator, and is out of scope for this change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `exact-geometry`: a new "Declared tessellation precision" requirement
  states the two attributes, their defaults, their validation, that they
  are neither constructor parameters nor identity but do drive currency,
  that a fusion declares its own, and that the `.brep` and `shape()` are
  unaffected. The existing "An exact artifact's mesh carries no degenerate
  triangles" requirement is modified: its sentence fixing the tolerances as
  unchanged becomes a reference to the declared ones, and degenerate removal
  is stated to happen after tessellation at whatever precision was declared.

`test-framework` needs no delta: its "Run-level comparison kernel"
requirement already answers a faceted question "from the compared nodes'
meshes", whatever precision those meshes carry. The consequence — that a
coarse declaration moves a faceted verdict — is a consequence of the mesh
being the judged artifact, not a new rule, and it is recorded in the design.

`user-documentation` needs no delta: its requirements govern the narrative
framing, the motion surface, the declarative authoring page and the viewer
claims, none of which enumerate a leaf adapter's tessellation attributes.
The leaf-node and fusion pages gain the declaration as ordinary reference
prose.

## Impact

- `solid_node/exact.py` — `write_stl` takes `linear_deflection` and
  `angular_deflection`.
- `solid_node/node/exact_leaf.py` — the two declared attributes with their
  defaults, one resolver that validates and returns them, and the call site
  in `as_scad()`.
- `solid_node/node/fusion.py` — the same two attributes and the same
  resolver at the `generate_stl()` call site.
- Consumers: none change shape. The viewer, the export, the faceted test
  kernel and printed-piece identity read whatever mesh the artifact holds,
  and a project that declares nothing gets the mesh it gets today.
- Originating projects: `openvmp` drops `premesh()` and its
  `BRepMesh_IncrementalMesh` import in favour of
  `angular_deflection = 0.5`; `Internal-Cycloidal-Actuator` drops the same
  trick and declares the same value on its STEP leaves. Both project edits
  are the projects' own, in their own repositories.
- The shop's `shop-skills/solid-node-api/SKILL.md` documents the public API
  for runtime agents and will need the declaration added; that is a shop
  file and a separate change, not part of this cycle.
