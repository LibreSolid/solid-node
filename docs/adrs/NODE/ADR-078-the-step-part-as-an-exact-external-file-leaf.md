# ADR-078: The STEP part as an exact external-file leaf

**Status:** Accepted

**Date:** 2026-09-06

**Change:** `step-part-leaf`

**Extends:**
- [ADR-054: An imported mesh is admitted, selected and corrected
  explicitly](ADR-054-imported-meshes-admitted-selected-and-corrected-explicitly.md)
- [ADR-055: The wrapper module joins an imported part's tracked source
  set](ADR-055-wrapper-module-in-the-imported-part-source-set.md)

**Depends on:**
- [ADR-047: One shared OCCT currency for every exact
  backend](ADR-047-shared-occt-currency-for-exact-backends.md)
- [ADR-050: Nanosecond-fidelity artifact
  freshness](ADR-050-nanosecond-fidelity-artifact-freshness.md)
- [ADR-071: Node-Scoped Content Currency](ADR-071-node-scoped-content-currency.md)
- [ADR-077: Declared tessellation
  precision](ADR-077-declared-tessellation-precision.md)

## Context and Problem Statement

STEP is the format every CAD package and every vendor publishes, and
0.6 has no leaf that reads one. Two projects wrote the same reader by
hand for the same reason: `Internal-Cycloidal-Actuator` wraps a
35,107,597-byte Inventor STEP assembly (one root free shape, 55
occurrences of 20 products, about 800 solids), and `openvmp`
(`simulation/don1/parts.py`, `StepPart`) does the same over 67 vendor
STEP files. Both reach XCAF the same way — `STEPCAFControl_Reader` with
name and colour modes into a `TDocStd_Document`,
`XCAFDoc_DocumentTool.ShapeTool_s`, a walk of the root free shape's
components to find a product by name, `GetShape_s` on the *referred*
label so the shape arrives unplaced — and both had to build their own
module-level document cache, because a full read-and-transfer of the
actuator's file costs 11.79 s and the project needed six to twenty
leaves over the one file.

Unlike an imported mesh, a STEP product is a boundary representation
the moment it is read. `ExactLeafNode` (ADR-047) already holds the
whole exact-adapter contract — `exact`, `shape()`, the `.brep`,
`as_scad()` writing both artifacts at the node's declared deflections
(ADR-077) — so a STEP leaf that derives it inherits all of it. The
question this ADR settles is everything ADR-054/055 settled for a
mesh, now for a document: how a product is selected, what frame it
arrives in, how it is corrected, when it is admitted, where its colour
comes from, and how its cost is paid once instead of once per node.

## Decision Drivers

- Delete two hand-written readers without losing anything they got
  right: name selection, the unplaced product frame, sewing for a
  face-only part, colour from the file, one read per file.
- A wrong or missing selection must teach, the way `StlNode`'s pack
  inventory does: the failure is the discovery tool, not a separate
  command.
- Nothing is repaired silently. A product with no solid fails; sewing
  is a call the project makes knowingly.
- The read cost (11.79 s measured) must be paid once per file per
  process, not once per node, without introducing a second staleness
  rule for a derived document cache written to disk.
- The leaf is exact by construction — no faceted fallback, no `sew=`
  or `unit=` constructor vocabulary to invent.

## Considered Options

1. **A new adapter, `StepNode(ExactLeafNode)`, mirroring `stl.py`'s
   three rules over a solid instead of a mesh** (chosen)
2. A `format=` parameter on `StlNode`
3. A project-facing `StepDocument` object with `StepNode` built on top
   of it
4. Sew a face-only product automatically when no solid is found

## Decision Outcome

Chosen option: **`StepNode(ExactLeafNode)`**, structured after
`adapters/stl.py` deliberately — module-level helpers for reading and
selection, a class whose `__init__` resolves the declared path against
the wrapper module's directory and adds `source_closure(wrapper)` to
`self.files` (ADR-055's reason verbatim: `part` and `adjust` decide the
part as much as the document does), `get_source_file()` returning the
resolved file, and a materialization path of *select → adjust →
admit*. What it does **not** copy is `StlNode.as_scad`: a STEP product
already has an exact form, so `render()` returns the geometry and
`ExactLeafNode.as_scad` writes the `.brep` and then the `.stl` at the
node's declared deflection — the one inherited method that makes this
leaf exact "for free".

### Selection: by product name over every top-level label, and the inventory is the failure

`ShapeTool.GetShapes()` returns every top-level label the document
holds — the root assembly, every sub-assembly, and every part — one
label per *product*, not per occurrence (confirmed empirically: 21
labels on the actuator's file, the 20 products of its design record's
table plus the root). `part` matches a label's `TDataStd_Name`.

The candidates a node may select **by omission** are every product
except a root that is itself an assembly; a root that is itself a
single part is its own candidate. That covers both a bare single-part
file and the far commoner file in which an exporter wraps one part in
an assembly root (fact: `cq.exporters.export` produces one product with
no assembly root at all; a one-child `cadquery.Assembly` produces two —
the root and the part). The excluded case is exactly the dangerous one:
an assembly root is never selected by omission, so a project that
forgot to select can never be handed a multi-component root as if it
were one part — it stays selectable *by name*.

A document with more candidates and `part` unset, or a `part` naming no
product of the file, fails with the document's own inventory — one
line per product, carrying its name, kind (part / sub-assembly / root
assembly), occurrence count, solid count, bounding box and volume — so
a developer or an agent learns the document's contents from the
failure itself, exactly as `StlNode`'s pack inventory does. Two
products of one name fail naming the ambiguity and describing both
(confirmed authorable: two sub-assemblies each holding a differently
named-shaped part named identically produce two distinct product
labels, since `cadquery.Assembly` refuses two same-named siblings — the
duplication needs two levels).

Bounding boxes in the inventory use `BRepBndLib.Add_s(...,
useTriangulation=False)` rather than `Shape.BoundingBox()`, which calls
`BRepBndLib.AddOptimal_s` and meshes first: 0.21 s against 10.78 s for
one call on the worst product of the actuator's file. Volume stays
expensive (`Shape.Volume()`, 7.70 s for all 21 products) because the
inventory is a failure path already stopping the build, and volume is
what tells a reader which of two same-named products is the one they
meant.

### Frame: the product's own, never an occurrence's

`GetShape_s` on a product's own (*referred*) label returns its
prototype shape composed from its own internal placements, never the
placement its parent gives it (confirmed: a product placed at two
occurrences 200 mm and 500 mm from a shared, centred-on-origin frame
selects the shape centred at the origin, carrying neither occurrence's
translation; a sub-assembly placed 100 mm from its parent's origin,
itself holding a part offset 3 mm internally, selects a shape centred
on that 3 mm offset — the parent's 100 mm is not composed in). This is
the decision that keeps a later assembly-reader cycle possible: a
project's own placement operations are where an occurrence's location
belongs, in `machine.py` today, in a future reader of the document's
own occurrence transforms later.

### Correction and admission: `adjust` is code, `solids_from_faces` is explicit, and only a solid is admitted

`adjust(self, shape)` receives the selected CadQuery `Shape` and
returns the corrected one; no scale, unit, recenter or sew constructor
parameter. The geometry after `adjust` must hold at least one solid, or
the build fails naming the node, the file, the part and what the
geometry does hold (shells, faces), and writes nothing — there is no
`require_solid = False` escape hatch the way `require_watertight =
False` is one for `StlNode`, because a face-only B-rep admitted here
would break `shape()`, fusion and every volume assertion outright, not
merely disappoint a watertight check. The escape is a documented,
explicit correction instead: `solids_from_faces(shape, tolerance)`
(openvmp's helper, promoted), sewing within `tolerance` into one solid
per closed shell, its docstring stating what it does and does not
guarantee — that the shells actually close, that the tolerance is
right, that the result is watertight or manifold.

### Colour: from the file, converted to sRGB, resolved lazily

A subclass that declares no `color` takes it from the product's own
surface colour, else the colour every occurrence of it agrees on, else
none. XCAF hands back **linear** RGB; the number a CAD package wrote is
sRGB — confirmed empirically: a part authored at `cq.Color(0.9, 0.1,
0.1)` is `COLOUR_RGB('', 0.899999998185, ...)` in the STEP text and
reads back linear as (0.787, 0.010, 0.010); hex-encoding that raw value
publishes a colour about 12% darker than the file says.
`Quantity_Color.Convert_LinearRGB_To_sRGB_s` is the correct inverse
(confirmed: converting 0.787 back gives 0.8999999981853642).

`color` is a property resolved on first access, not in `__init__`,
because every build path reads `node.color` — to colourize the SCAD and
to publish `viewer.json` — even when the node's artifacts are current
and never render. Resolving eagerly would pay the document's read cost
on every build regardless of currency. The property's setter records
only a **non-`None`** assignment as a declaration: a naive setter would
record whatever is assigned, and the framework's own node
initialisation (or a subclass `__init__` writing `self.color = None`)
would then be mistaken for "this part has no colour", permanently
hiding the document's own colour. A subclass that assigns `color =
'#hex'` in its own class body shadows the property entirely — ordinary
Python attribute resolution finds the subclass's plain attribute before
the parent class's descriptor — so a declared colour is also
structurally guaranteed to never invoke the property, and therefore
never open the document.

### One document per `(path, mtime_ns)`, and one shape copy per caller

A module-level dict keyed on `(path, mtime_ns)`, evicting every entry
for a path on a key miss, in the shape of `solid_node.exact
._shape_cache`: twenty nodes over one file cost one read (measured:
11.79 s cached against 70.7 s uncached for the actuator's six leaves,
236 s projected for twenty). The document object is held alive for the
life of the cache entry because every label is a reference into it.

**Unplanned finding, fixed under this change:** `ShapeTool.GetShape_s`
hands back a reference into the shared, cached document, and OCCT's
mesher attaches a triangulation directly onto a face's underlying
TShape. Two `StepNode`s selecting the *same* product from the *same*
cached document therefore shared mutable mesh state: whichever node's
`exportStl` ran first (at whatever precision it declared) left a
triangulation the second treated as already fine enough and reused,
silently discarding its own declared `angular_deflection` — the same
relative/absolute-mode meshing hazard ADR-077 documents for a project's
own `premesh()`, arriving here through this leaf's own document cache
instead of a project's hand-written one. Confirmed directly: without
isolation, a node declaring `angular_deflection = 0.5` built after a
default node came out at the *default*'s fine triangle count (and vice
versa, depending on build order); a curved test fixture went from 8002
triangles (both nodes, wrong) to 8002 against 306 (right) once fixed.
`_Document.shape()` now returns `Shape.copy(mesh=False)` —
`BRepBuilderAPI_Copy`, deliberately not copying any existing
triangulation — so each caller meshes independent topology on its own
terms. This is internal to the new module's own document cache, not a
change to `solid_node.exact` or `ExactLeafNode`: no other adapter
shares one OCCT shape object across separate node instances the way a
per-file document cache does.

### `StepNode` keeps the inherited 0.1 rad angular deflection (D9)

ADR-077 left this open for this leaf's own cycle to answer, and the
answer is **no**: `StepNode` inherits `linear_deflection = 0.1` and
`angular_deflection = 0.1` from `ExactLeafNode` and redeclares neither,
so what precision a part is tessellated at is readable from a project's
own source rather than from which adapter it came from, and a STEP
round trip of a project's own printed bracket does not silently
coarsen it fivefold. The one-line cost to a project that wants coarser
falls on the project that asked for it.

Measured through this leaf, on the real `Output_Shaft` product the
cycle originates from (a scratchpad project run against this
worktree, never inside the actuator's own repository): the inherited
default writes **19.91 MB** (398,184 triangles); declaring
`angular_deflection = 0.5` writes **1.76 MB** (35,240 triangles), with
a byte-for-byte identical `.brep` between the two (`cmp` confirms).
This is a **better** number than either figure previously on record —
smaller than the 3.35 MB the actuator's own `premesh()` trick achieved
running through the framework's *pre*-ADR-077 export (inflated by the
relative/absolute mesh-mode mismatch that trick depended on), and
closely matching the actuator's own direct `BRepMesh_IncrementalMesh`
figure of 1.8 MB / 35,776 triangles — with no premesh trick and no
mismatch hazard, because this leaf meshes once, directly, at the node's
own declared value. Nothing here contradicts D9.

## Pros and Cons of the Options

### `StepNode(ExactLeafNode)`, `stl.py`'s three rules over a solid

- **Good**: Deletes both hand-written readers without losing anything
  they got right
- **Good**: Exact "for free" — inherits `shape()`, the `.brep`, exact
  fusion and declared tessellation precision from `ExactLeafNode`
- **Good**: The inventory failure is the discovery tool; no separate
  command
- **Bad**: A one-part assembly file demands a `part` name that can look
  redundant until the inventory explains why (deliberate — see D3 in
  the change's design)

### A `format=` parameter on `StlNode`

- **Bad**: The two share three rules and no code — different reader,
  different selector, different admission gate, different exactness —
  and a doctrine (`StlNode` is faceted) that would then hold for only
  one branch

### A project-facing `StepDocument` object with `StepNode` built on it

- **Bad**: A second public type to explain, when what a project wants
  is a part; the document is a private cache detail

### Sew a face-only product automatically when no solid is found

- **Bad**: Repairs geometry the project never inspected, at a tolerance
  the framework chose for a file it has never seen — exactly the silent
  machining ADR-054 already refused for a mesh

## Consequences

- New: `solid_node/node/adapters/step.py` (`StepNode`,
  `solids_from_faces`, the document cache), `tests/test_step_node.py`,
  `tests/step_project/` (fixtures authored in CadQuery and saved to
  STEP in a temporary build directory — no vendor file is committed, as
  for `tests/stl_project/`).
- `solid_node/node/__init__.py` gains one `_EXPORTS` row; the STEP
  reader (`OCP.STEPCAFControl`) is imported only when `StepNode` is
  first accessed, preserving `cli-startup-cost`'s deferral — measured
  at 0.84 s in a fresh interpreter and 0.000 s once `cadquery` is
  already imported, which every project using `StepNode` has done
  anyway by deriving `ExactLeafNode`.
- `exact-geometry`'s "Node exactness capability" and "Declared
  tessellation precision" requirements, and `node-model`'s
  "Multi-backend leaf adapters" requirement, each add `StepNode` to
  their adapter enumerations; no existing adapter's behaviour changes.
- Nothing existing changes behaviour. No adapter, artifact, or currency
  rule is modified; `StlNode` is untouched and stays faceted by
  doctrine.
- Not built here: reading the document's own occurrence placements (an
  assembly reader — the frame decision above is what keeps that cycle
  possible), units or up-axis normalization (a project's own `adjust`,
  as for `StlNode`), any exchange format beyond STEP, or writing STEP.
- The two originating projects migrate their own hand-written readers
  away on their own schedule, in their own repositories; neither is
  done in this cycle.

## References

- `solid_node/node/adapters/step.py` — `StepNode`, `_Document`,
  `solids_from_faces`, `cached_document`
- `solid_node/node/exact_leaf.py` — the inherited exact-adapter
  contract this leaf supplies nothing beyond `namespace` and its own
  reading and selection for
- `tests/test_step_node.py` — declaration and freshness, selection and
  the inventory, frame, `adjust` and admission, colour, the document
  cache, exactness and the deferred import
- `tests/step_project/` — the fixtures, authored in CadQuery with no
  vendor file committed
- `docs/leaf-nodes.rst` — the STEP leaf kind, `:ref:`step-import``
- `projects/Internal-Cycloidal-Actuator` and `openvmp` — the two
  originating projects' hand-written readers this leaf replaces
- OpenSpec change `step-part-leaf`, capability `step-import`
