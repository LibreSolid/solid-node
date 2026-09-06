## Context

Every exact STL artifact in the framework is written by one function.
`solid_node/exact.py`:

```python
def write_stl(shape, path, mtime_ns, digest=None):
    def export(temporary):
        shape.exportStl(temporary, tolerance=0.1, angularTolerance=0.1)
        ...
```

with the docstring "The tessellation tolerances are the historical
`cq.exporters.export` defaults." It has exactly two callers:
`ExactLeafNode.as_scad()` (`solid_node/node/exact_leaf.py:59`) and
`FusionNode.generate_stl()` (`solid_node/node/fusion.py:69`). Nothing else
in the framework tessellates a B-rep: the faceted adapters arrive with a
mesh already, and `MolejoNode` is a `FlexibleNode` whose geometry molejo's
evaluator produces.

`Shape.exportStl` reuses a triangulation already stored on the shape rather
than meshing again. That implementation detail is the whole of the lever
two projects have: call `BRepMesh_IncrementalMesh` on the shape inside
`render()` and the export writes that mesh instead of its own. openvmp's
`simulation/don1/parts.py` does it in a `premesh()` helper at 0.1 mm / 0.5
rad; Internal-Cycloidal-Actuator does the same at the same values and
measured what it buys — `Output_Shaft` at 19.9 MB / 398,184 triangles under
the framework's default against 1.8 MB / 35,776 triangles at 0.5 rad. Its
design record calls the lever "a trick, not an interface" and records the
failure mode it depends on: "if the framework's export ever meshes
unconditionally, every part in this project silently grows by 10×."

Two constraints frame the design. First, ADR-071 made currency
node-scoped: a node's digest is its own class's text within its source file
plus the closure of what it imports, so a value written in a node's class
body already invalidates that node and nothing else. Second, ADR-026/063
key an artifact by the node's resolved declared values, and `SheetLeafNode`
shows both sides of that line — `thickness` passed as a constructor kwarg
reaches `uniq_id` and makes two artifacts, while `thickness` declared as a
class attribute rides the source-set path instead. Tessellation precision
belongs unambiguously on the second side: it is not a different part.

## Goals / Non-Goals

**Goals:**

- One declaration per node, in the class body, that decides the tolerances
  of that node's own STL artifact.
- The framework's historical values as the defaults, so no existing
  artifact and no existing project changes.
- `write_stl` stops holding a policy it has no business holding: it becomes
  a function that writes the mesh it is told to write.
- The declaration reaches the artifact through the currency path that
  already exists, adding no new staleness rule to get wrong.
- A `StepNode` project, which will have no `render()` to premesh in, keeps
  the lever the two originating projects have today.

**Non-Goals:**

- Precision as artifact identity. Two tessellations of one solid are one
  node at two times.
- A constructor parameter, a `--set` knob, or a project- or run-level
  precision setting. Precision is a property of the part, declared where
  the part is declared; a run-level override would make one project's
  artifacts depend on how they were built.
- Any change to `shape()`, the `.brep` artifact, or exactness.
- Deflection for `MolejoNode`. Its mesh comes from molejo's evaluator under
  the `flexible-parts` capability, and a tolerance for it is that
  capability's question, not this one.
- Deflection attributes on the faceted adapters.
- The other tessellation knobs OCCT exposes (relative deflection, parallel
  meshing, `theInParallel`). Two quantities cover both originating projects
  and both were measured; more can be added when one is asked for.
- Editing the shop's `shop-skills/solid-node-api/SKILL.md`. It is a shop
  file, changed in the shop's own repository.

## Decisions

### D1. Two class attributes named `linear_deflection` and `angular_deflection`

The names are OCCT's own. `BRepMesh_IncrementalMesh`'s parameters are
`theLinDeflection` and `theAngDeflection`, and the OCCT meshing
documentation calls the two quantities linear deflection and angular
deflection throughout. A project author who wants to know what 0.5 means
searches those words and finds the kernel's own explanation: linear
deflection bounds the distance between the mesh and the surface, angular
deflection bounds the angle between adjacent facet normals.

*Rejected: `tolerance` / `angular_tolerance`* — CadQuery's `exportStl`
parameter names, which the current `write_stl` passes through. "Tolerance"
alone says nothing about what it bounds, and the pair reads as though one
is a special case of the other. They are also camelCase in the API they
come from, so borrowing them buys no continuity for the reader.

*Rejected: `mesh_deflection` / `mesh_angle`* — what openvmp's module
constants are called. `mesh_angle` loses the unit and the meaning: it is
not the angle of anything, it is the deflection bound between two normals.

*Rejected: `deflection` / `angle`, or a single `deflection` tuple* — a bare
`deflection` is ambiguous exactly where the reader needs it not to be, and
a tuple makes "declare one and keep the other's default" impossible to
express.

*Rejected: one declaration object, `tessellation = Tessellation(linear=…,
angular=…)`, in the `Time(loop=…)` / `Driver(…)` idiom (ADR-072, ADR-061).*
That idiom exists for declarations the framework must enumerate off a class,
bind per instance, refuse assignment to, or publish into a document — none
of which applies here. Two plain numbers read once at export time need no
descriptor, and adding one would put a third kind of thing in a class body
for no behaviour. `SheetLeafNode.thickness` is the precedent: a plain class
attribute is the framework's existing idiom for a scalar that shapes the
artifact and rides the source set.

### D2. Declared on `ExactLeafNode` and `FusionNode`, not on `AbstractBaseNode`

The attributes are defined with their defaults on the two classes that call
`write_stl`. Defining them further up would put them on every node,
including the faceted adapters, where a project could declare one and watch
it do nothing — the worst kind of interface, one that accepts a value and
ignores it. `SheetLeafNode` and the adapters inherit them from
`ExactLeafNode` without restating anything.

For the faceted adapters the spec's rule is simply that the attributes are
not defined there. Nothing detects and refuses them: a class attribute a
framework never reads is the ordinary Python state of affairs, and
inventing a metaclass check for one would be a new failure mode built to
guard a mistake nobody has made. This is a deliberate asymmetry with the
`Time` declaration, which *is* refused on the wrong owner — `Time` has a
descriptor already, and a stray time base silently scales a subtree,
whereas a stray deflection does nothing at all.

### D3. One resolver, reading at the point of export

A module-level helper in `exact.py` — `deflections(node)` — reads the two
attributes off the node, validates each, and returns the pair. Both call
sites use it immediately before `write_stl`.

Reading at export rather than at construction is what the spec's "at the
point it is read" means, and it matters for two reasons. A node whose
artifacts are current never writes an STL at all, so a validation at
construction would be work done on every node of every build to catch a
mistake that only matters when a mesh is written. And validation at
construction would have to live in `__init__`, where the declarative node
API deliberately put nothing (ADR-061): `check()` is the declarative
validation hook and it is about parameters, not about export policy.

The cost is that a bad value is reported on the build that writes the
artifact rather than on the one that loads the class. Since a bad value can
only be a typo in a class body, and any build that would have caught it at
construction also writes the artifact, the difference is not observable in
practice.

Validation is: a real number (`bool` excluded — `True` is not a
deflection), finite, strictly positive. The error names the node and the
attribute, in the manner of the framework's other declaration errors.

### D4. `write_stl` takes the tolerances as arguments

```python
def write_stl(shape, path, mtime_ns, linear_deflection, angular_deflection,
              digest=None):
```

Required positional parameters rather than defaulted ones. A default of
0.1 in `write_stl` would be a second place where the framework's historical
values live, and the one place they should live is the class attribute
declaration on `ExactLeafNode`, where a reader of the public class finds
them. Every caller passes them; `tests/test_exact_geometry.py`'s direct
call to `write_stl` is updated with the rest.

Note that the degenerate-triangle pass (ADR-074's neighbour, the existing
requirement) is untouched by this: it runs on whatever mesh `exportStl`
wrote, which is now the mesh the node asked for.

### D5. Currency by the declaring module, not by identity

Nothing new is built for staleness. The attribute is text in the node's own
class body; ADR-071 digests exactly that text as the node's scope within its
file, so editing `angular_deflection = 0.5` to `0.4` changes the node's
digest, fails the content-currency check, and rebuilds that node's
artifacts and every fusion above it — and nothing else in the project. A
value taken from a constant in an imported project module travels the same
way, because that module is in the node's source closure (ADR-033/058).

Keeping it out of `uniq_id` (ADR-026/063) is the deliberate half. If
precision entered identity, changing it would leave the old artifact on
disk under the old key, and a project sweeping precision downward while
tuning would accumulate a build directory full of meshes of the same part.
Precision is not what the part *is*; it is how finely this build wrote it
down.

### D6. A fusion declares for its own fused solid

`FusionNode.generate_stl()` tessellates the fuse of its children's shapes —
a shape none of the children has. Inheriting a child's declaration would
mean asking which child wins, and any answer is arbitrary: a fusion of a
coarse vendor STEP part and a fine printed bracket has no defensible
inherited value. Each declaration shapes the artifact of the node that
declares it, and a project that wants a coarse fusion says so on the
fusion. This is stated in the spec because the opposite is a reasonable
expectation.

### D7. The consequences of the mesh changing are consequences, not new rules

Four things read the STL artifact: the viewer, the export, the faceted
comparison path in the test framework, and printed-piece identity. None of
them needs a rule added.

The one worth stating in the spec — and the one a project author must know
— is piece identity. ADR-043 makes a printed piece's id a fingerprint of
its artifact's content, so redeclaring precision gives the node a new piece
id. That is correct (the file a maker would print is a different file) and
surprising (the part did not change), so the requirement says it rather
than leaving it to be discovered from a diff of `viewer.json`.

The faceted test kernel is the second consequence: under `solid test
--faceted` every verdict is read off these meshes, so a coarse declaration
can move a clearance verdict. The `test-framework` capability already says
faceted questions are answered "from the compared nodes' meshes", which is
true at any precision, so it needs no delta; the exact-geometry requirement
names the consequence, and the leaf-node documentation warns about it where
a project author choosing a value will read it.

## Risks / Trade-offs

- [A project coarsens a part and a faceted `solid test` run silently starts
  passing a clearance it used to fail] → the documentation states the
  coupling at the point of declaration, and the exact kernel — the default
  — is unaffected because `shape()` and the `.brep` are untouched. A
  project whose clearances are close should test on the exact kernel, which
  is what it does today.
- [Redeclaring precision changes every affected printed-piece id] → stated
  as a scenario in the spec and in the changelog entry, so it is a
  documented consequence rather than a surprise in a diff.
- [Validation at export means a typo survives until an artifact is
  written] → accepted, D3; a build that would catch it earlier writes the
  artifact anyway.
- [`exportStl` reusing a stored triangulation is still an implementation
  detail the originating projects' current workaround rests on] → this
  change removes their need to rest on it. Until they drop the workaround,
  a shape they premeshed is exported at their stored precision and the
  declaration is not consulted, which is the behaviour they have today and
  no worse.
- [Two more class attributes on the exact adapters is more public surface]
  → they are two numbers with framework defaults, and the alternative is a
  documented instruction to reach into OCCT.

## Migration Plan

Nothing to migrate. An undeclared node is tessellated at the values
`write_stl` fixes today, so every existing artifact is unchanged and no
rebuild is triggered by this change alone.

The two originating projects migrate on their own schedule, in their own
repositories: delete the `premesh()` helper and the
`BRepMesh_IncrementalMesh` import, declare `angular_deflection = 0.5` on
the STEP-backed leaves. Their artifacts change content at that point — the
same content they have today via the workaround — and so do their piece
ids.

## Open Questions

- Whether `relative` deflection (OCCT's `theRelative`, which scales the
  linear bound by each edge's size) is worth exposing later. Neither
  originating project asked for it; both wanted the angular bound only.
- Whether a future `StepNode` should default to something coarser than
  0.1 rad, given that every project reading vendor STEP has wanted 0.5.
  That is the `StepNode` cycle's question, not this one's: this change
  gives it the attribute to set.
