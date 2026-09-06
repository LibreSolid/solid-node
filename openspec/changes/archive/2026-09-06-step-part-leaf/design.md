## Context

`StlNode` (ADR-054, ADR-055) is the framework's one external-file part: a
committed mesh, admitted by a watertight gate, selected out of a pack by
index, corrected in an `adjust` hook, materialized into the node's own
artifact. It is faceted by settled doctrine.

STEP is the other file a project actually has, and it is not a mesh. A
STEP product is a B-rep, so it belongs on the exact side of the framework:
`ExactLeafNode` already holds the whole exact-adapter contract (`exact`,
`shape()`, the `.brep`, `as_scad` writing both artifacts at the node's
declared deflections), and a STEP leaf that derives it inherits all of it.
That is why this leaf is a new adapter and not a variant of `StlNode`.

Two projects have written the reader by hand. Both reach XCAF the same
way: `STEPCAFControl_Reader` with name and colour modes into a
`TDocStd_Document`, `XCAFDoc_DocumentTool.ShapeTool_s`, then a walk of the
root free shape's components to find the product a name belongs to, and
`GetShape_s` on the *referred* label so the shape arrives unplaced. The
actuator's design states the frame decision in the words this cycle
adopts: "Parts are selected by product name, from the referred shape, not
the located one … Rejected: reading the located component shape and
placing nothing — it would work at rest and be useless the moment anything
turns."

**Empirical facts this design rests on.** All were confirmed in this
worktree against the workspace venv (OCCT 7.8 through `cadquery-ocp`),
either on assemblies authored with `cadquery.Assembly` and saved to STEP,
or on the actuator's own 35 MB document:

1. `ShapeTool.GetShapes()` returns every top-level label in the document —
   the root assembly, every sub-assembly, and every part — one label per
   *product*, not per occurrence. On the actuator file it returns **21**
   labels: the 20 products of the design record's table plus the root
   assembly `Internal Cycloidal Actuator`.
2. Two occurrences of one part share one product label; the *component*
   labels (children of an assembly label) carry the occurrence and refer to
   the product through `GetReferredShape_s`. Summing components across
   every assembly label reproduces the document's **55 occurrences**
   exactly.
3. `GetShape_s` on an assembly label returns its components composed at
   their internal placements, and not the assembly's own placement in its
   parent. A sub-assembly is therefore selectable as a part with no extra
   work.
4. Colour is on the product label (`GetColor_s(label,
   XCAFDoc_ColorSurf)`); in the authored fixtures no component label
   carried one. On the actuator file 8 of the 21 labels carry a surface
   colour, including `Fixed_Ring` at (0.905, 0.905, 0.905) — the value its
   project quotes.
5. **The colour XCAF hands back is linear RGB, not the number in the
   file.** A part written with `cq.Color(0.9, 0.1, 0.1)` is
   `COLOUR_RGB('', 0.899999998185, 0.0999999999, 0.0999999999)` in the STEP
   text and reads back as **(0.787, 0.010, 0.010)**;
   `Quantity_Color.Convert_LinearRGB_To_sRGB_s(0.787) = 0.8998`. Both
   originating projects hex-encode the raw values and so publish parts
   about 12% darker than the CAD package drew them.
6. A product can hold no solid: a `cq.Shell` added to an assembly comes
   back as a product with 0 solids and 5 faces — openvmp's hook and battery
   in miniature, and authorable as a test fixture.
7. Two products of one name are authorable: two sub-assemblies each holding
   a differently-shaped part named `Pin` produce two distinct product
   labels both named `Pin`. (`cadquery.Assembly` refuses two children of one
   parent with the same name, so the fixture needs the two levels.)
8. A file written by `cq.exporters.export` holds exactly one product, named
   by the translator (`Open CASCADE STEP translator 7.8 2`). A one-child
   `cadquery.Assembly` holds **two**: the root assembly and the part.
9. Reading the actuator file costs **11.79 s** (`ReadFile` + `Transfer`),
   confirming the project's measured 11.6 s.
10. Inventory cost on that file: names, occurrence counts, solid counts and
    colours for all 21 products together cost **0.02 s**; bounding boxes
    through `BRepBndLib.Add_s(..., useTriangulation=False)` cost **0.21 s**
    for all 21; volumes cost **7.70 s** for all 21. `Shape.BoundingBox()`
    meshes by default — one call on the root assembly cost **10.78 s**.
11. `import OCP.STEPCAFControl` in a fresh interpreter costs **0.84 s** (it
    is the monolithic `OCP.OCP` extension), and **0.000 s** once `cadquery`
    has been imported.

## Goals / Non-Goals

**Goals:**

- One leaf that deletes both hand-written readers, keeping every behaviour
  they justified: name selection, the unplaced product frame, sewing for a
  face-only part, colour from the file, one read per file.
- The STEP part is an ordinary exact part: fusible with a `CadQueryNode`,
  answerable to the spatial assertions, carrying a `.brep`.
- A failure that teaches. A wrong or missing `part` prints the file's
  inventory, so no separate inspection tool has to exist — `StlNode`'s rule
  applied to a document instead of a pack.
- Nothing repaired silently. A product with no solid fails; sewing is a
  call the project makes knowingly.

**Non-Goals:**

- An assembly reader. The 55 placements the actuator types by hand stay
  hand-typed after this change; reading them is a later cycle, and the
  unplaced-frame rule here is what makes that cycle possible.
- Units, up-axis, or any other document-level normalization. `adjust` and
  placement operations are where a project corrects a file, as for
  `StlNode`.
- Constructor knobs: no `scale=`, `unit=`, `recenter=`, `sew=`.
- Other exchange formats (IGES, 3MF, glTF). The reader is XCAF's STEP
  reader specifically, and the selection vocabulary is STEP's `PRODUCT`.
- Writing STEP. `solid export` is unaffected.
- Reading occurrence transforms, even though the document holds them and
  the cached document could serve them cheaply. Exposing them without an
  assembly design would invite projects to invent one.

## Decisions

### D1. A new adapter deriving `ExactLeafNode`, mirroring `stl.py` line by line

`solid_node/node/adapters/step.py`, one `_EXPORTS` row
(`'StepNode': 'adapters.step'`). Structure follows `adapters/stl.py`
deliberately: module-level helpers for reading and selection, a class whose
`__init__` resolves the declared path against the wrapper module's
directory and adds `source_closure(wrapper)` to `self.files`,
`get_source_file()` returning the resolved file, and a materialization path
of *select → adjust → admit*.

What it does **not** copy is `StlNode.as_scad`. `StlNode` writes its own
artifact because a mesh has no exact form; a STEP part has one, so
`render()` returns the geometry and `ExactLeafNode.as_scad` writes the
`.brep` and then the `.stl` at the node's declared deflections. That single
inherited method is the whole reason this leaf is exact "for free".

*Rejected: a `format=` parameter on `StlNode`.* The two share three rules
and no code: different reader, different selector, different admission
gate, different exactness. One class doing both would have two disjoint
halves and a doctrine (`StlNode` is faceted) that holds for only one.

*Rejected: a project-facing `StepDocument` object with `StepNode` built on
it.* A second public type to explain, when what a project wants is a part.
The document is a private cache detail (D6).

### D2. `render()` returns a `cadquery.Workplane`; the namespace is `cadquery.cq`

`LeafNode.validate` compares `type(rendered).__module__` against the
adapter's declared `namespace`. A bare `cq.Shape` lives in
`cadquery.occ_impl.shapes`, so returning one would force `namespace =
'cadquery'` — broader than `CadQueryNode`'s, and it would then admit a
`Workplane` too. Wrapping in `cq.Workplane(obj=shape)` — what both
originating projects already do — lets the adapter declare exactly
`CadQueryNode`'s `'cadquery.cq'`, and `exact.shape_from_rendered` unwraps
it through `vals()` as it does for every CadQuery leaf.

`adjust` receives and returns the `Shape`, not the `Workplane`: the hook is
about geometry, and a project reaching for `cq.Workplane(obj=shape)` inside
its own hook is free to return `.val()`.

### D3. Selection is by product name over `GetShapes()`, and the inventory is the failure

The candidate set is every top-level label (fact 1), which is what "the
products of this file" means to a person reading the file in a CAD package:
parts and sub-assemblies alike, each once however many times it is placed.
`part` matches a label's `TDataStd_Name`.

Consequences, each deliberate:

- **A file with exactly one candidate product needs no `part`.** The
  candidates are the document's products *other than a root that is itself
  an assembly*; a root that is a single part is its own candidate. So a
  single-part STEP written by `cq.exporters.export` (one product, no
  assembly root — fact 8) needs no name, and so does the far commoner file
  in which an exporter wraps one part in an assembly (two products, of
  which the root is the wrapper — fact 8 again): one candidate, no name
  needed. The actuator's file still demands one, because dropping its root
  leaves 20 candidates.

  The excluded thing is precisely the dangerous one. An assembly root is
  never selected by omission, so a project that forgot to select can never
  be handed a multi-component root — the actuator's 781-solid, 55-occurrence
  assembly — as if it were a part. It stays *selectable by name*, for a
  project that genuinely wants the whole document as one part; it is only
  never the default. `StlNode`'s "a single-body file needs no `body`" is the
  same rule with the same exclusion, since a mesh pack has no wrapper to
  exclude.
- **A sub-assembly is selectable** (fact 3), which is what a project wants
  when a vendor ships a gearbox as one shippable unit inside a bigger file.
  Its geometry is its components at their internal placements, as XCAF hands
  it back, and it is still unplaced in its own parent (D4).
- **Two products of one name fail** (fact 7), naming the ambiguity and the
  two products' solid counts and bounding boxes, rather than picking the
  first. There is no second selector to fall back to: an XCAF label entry
  string is not stable vocabulary for a project to type.
- **An unnamed product** cannot be selected by name; it appears in the
  inventory as `(unnamed)`, and it is selectable only by being the file's
  only product.

The inventory line carries name, kind (part / sub-assembly / root
assembly), occurrence count, solid count, bounding box and volume — the
same shape of answer `StlNode._inventory` gives for a pack, extended by the
two facts a document has that a pack does not (kind and occurrences).
Bounding boxes use `BRepBndLib.Add_s(..., useTriangulation=False)` because
`Shape.BoundingBox()` tessellates: 0.21 s against 10.78 s for one call on
the worst known product (fact 10). Volume stays in, at 7.70 s for the whole
actuator file, because the inventory is a failure path — a build that
prints it is already stopping, and the number is what tells a reader which
of two same-named products is the one they meant.

### D4. The product's own frame, never the occurrence's

`GetShape_s(product_label)`. The node's geometry is the prototype, exactly
as `StlNode` refuses to reframe a body it extracts from a pack. Placement
is the assembly's job — in `machine.py` today, in a future assembly reader
later — and baking an occurrence transform into the part would make the
node's own frame the world's, which is wrong the moment the part moves.
This is the decision that keeps a later assembly-reader cycle possible.

### D5. Admission: at least one solid, and sewing is the project's call

A STEP product that carries only faces is not a part: it has no volume, the
exact kernel cannot fuse or intersect it, and the STL written from it
encloses nothing. So the gate is "the geometry after `adjust` holds at
least one solid", judged after the hook exactly as `StlNode`'s watertight
gate is, and the failure names the node, the file, the part and what the
geometry does hold (shells, faces).

There is no `require_solid = False` escape hatch, and this is the one place
this leaf is *stricter* than `StlNode`. `require_watertight = False`
admits a mesh that still describes a surface every downstream consumer can
read; a face-only B-rep admitted here would break `shape()`, the fuse and
every volume assertion. The escape is instead a documented, explicit
correction: `solids_from_faces(shape, tolerance)` in the adapter module,
openvmp's helper promoted, called from an `adjust` hook. Its docstring
states what it does (sew within a tolerance, one solid per closed shell)
and what it does not guarantee (that the shells close, that the tolerance
is right for this file, that the result is watertight or manifold) — a
project sewing a vendor surface is making a judgement, and the framework
records that it was made rather than making it silently.

*Rejected: sewing automatically when no solid is found* — what openvmp's
`StepPart.render` does today. It repairs geometry the project never
inspected, and a tolerance chosen by the framework for a file it has never
seen is exactly the silent machining ADR-054 refuses.

### D6. One document per `(path, mtime_ns)`, in the shape of `exact._shape_cache`

A module-level dict keyed on `(path, mtime_ns)` holding the transferred
`TDocStd_Document` and the derived product index, with the same eviction
rule `exact._shape_cache` uses: a key miss for a path drops every entry for
that path before reading. Twenty nodes over one file cost one read.

The measurement is the whole argument (fact 9): 11.79 s per read+transfer
of the actuator file. Six leaves cost 11.79 s cached against 70.7 s
uncached — the project's own measured 70 s — and the twenty leaves a
project modelling the whole actuator would have cost **236 s** uncached, on
every build pass, against the same 11.79 s.

Keyed on `mtime_ns` rather than `mtime` for ADR-050's reason: the framework
already decided that seconds are not enough resolution to notice an edit.

The document object must stay alive because the labels are references into
it, so the cache holds the document for the life of the process. On the
actuator file that is a 35 MB document's worth of OCCT memory for one
entry, which is the same order as the shapes the build holds anyway, and
the process is a single build pass (ADR-067 gives each pass a fresh
interpreter). A cap or an LRU would be machinery for a bound nobody has
hit.

*Rejected: caching the transferred document to disk as BREP*, which the
actuator's design also rejected: "it would be faster still and would put a
derived copy of a vendor document into the build directory, with a
staleness rule of its own to get wrong."

### D7. Colour: from the file, converted to sRGB, resolved lazily

The framework's `color` is a `#RRGGBB` string (`base.py::_colorize` splits
it into three bytes; `serializer.py` publishes the same string into
`viewer.json`). So "the part's colour from the file" means: read the
product label's `XCAFDoc_ColorSurf` colour, else the colour every
occurrence of it agrees on, else none — and hex-encode it.

Encoding it needs one conversion neither originating project makes (fact
5). XCAF hands back OCCT's `Quantity_Color`, whose components are **linear**
RGB; the number in the STEP file is sRGB. Hex-encoding the raw components
publishes a part visibly darker than the file says (0.9 → 0.787 → `c9`
instead of `e6`). The adapter therefore converts with
`Quantity_Color.Convert_LinearRGB_To_sRGB_s` before rounding to bytes. The
spec states the round trip rather than the function: a file whose part is
written at a colour reads back as that colour.

**The declaration must be distinguishable from an assignment of `None`.**
A property with a naive setter would record whatever is assigned, and a
base-class initialisation assigning `self.color = None` — nothing in
`solid_node` does today, but `AbstractBaseNode.__init__` and `_colorize` are
where such an assignment would live, and a subclass's own `__init__` may do
it — would be recorded as a declared colour of "none", so the file's colour
would never be reached. The rule is therefore: the property answers from the
document unless a value has actually been declared, and only a non-`None`
assignment counts as declaring one. Assigning `None` restores "take it from
the document" rather than recording a decision. The cost is that
`color = None` cannot mean "this part has deliberately no colour"; it is
indistinguishable from the inherited default and is documented as meaning
the document's colour, if the document has one.

**Lazily**, because of a currency interaction worth stating. A leaf whose
artifacts are current never renders (`base.assemble` →
`_render_can_be_skipped` → `import_optimized`), so it never reads the STEP
file — but every build path still reads `node.color`, to colourize the SCAD
and to publish `viewer.json`. If `color` were resolved in `__init__` (what
both projects do), every build would pay the 11.79 s read even with every
artifact current. So `color` is a property that resolves on first access:
a project that declares `color = '#8b93a0'` on the class overrides the
property in the ordinary Python way and never opens the file, and one that
wants the file's colour pays one cached read. A setter is provided so that
`self.color = …` in a subclass `__init__` keeps working.

*Rejected: recording the resolved colour beside the artifact* — a second
currency rule, for a string.

*Rejected: no colour from the file at all.* 8 of the actuator's 21 products
carry one and 43 of its 55 occurrences do; dropping them would make the
leaf worse than the hand-written code it replaces.

### D8. Freshness is `StlNode`'s, unchanged

`get_source_file()` returns the resolved STEP path, so its mtime drives
currency exactly as a `.js` does for `JScadNode`; and the wrapper module
joins `self.files` through `source_closure`, for ADR-055's reason verbatim
— `part` and `adjust` live in the Python file and decide the part as much
as the document does. Nothing new is built: editing the STEP file or the
wrapper makes the artifacts stale, a current artifact is not rewritten, and
the content-verified fallback (ADR-060/071) applies as it does to every
node.

### D9. `StepNode` keeps the inherited 0.1 rad angular deflection

ADR-078 left this open — "Whether a future `StepNode` should default to
something coarser than 0.1 rad, given that every project reading vendor
STEP has wanted 0.5. That is the `StepNode` cycle's question" — and the
answer here is **no**: `StepNode` inherits `linear_deflection = 0.1` and
`angular_deflection = 0.1` from `ExactLeafNode` and redeclares neither.

The evidence for 0.5 is real — the actuator's `Output_Shaft` is **19.9 MB**
of STL at 0.1 rad, and openvmp's robot came to 200 MB — but it is evidence
about *those files*, not about the format. It is also evidence whose second
number nobody has yet measured through this leaf. The actuator's design
record now distinguishes three figures for `Output_Shaft` at 0.5 rad: 1.8 MB
exporting the stored triangulation directly, **3.35 MB** through the
framework's export as it stands (because that export asks OCCT for 0.1 rad
unconditionally and the mesher re-tessellates every face where the request
is finer than the stored mesh), and 6.30 MB when the stored mesh's
relative/absolute mode does not match the export's. Under ADR-078 the
export asks for the declared value, so a `StepNode` declaring
`angular_deflection = 0.5` stores nothing and meshes once at 0.5 — a fourth
number, which task 7.1 measures on this very part before any of it is
written down. Against that background:

1. `declared-tessellation-precision` was ratified one commit ago with the
   requirement that a node declaring neither attribute is tessellated at
   0.1 mm and 0.1 rad, "the values the framework has always used". Forking
   that rule per adapter in the very next cycle would mean a reader of a
   project's source can no longer tell what precision a part is at without
   knowing which adapter it came from.
2. Coarseness is a property of the geometry, not of the file format. A STEP
   of a printed bracket, exported from the same CadQuery model, would come
   in 5× coarser than the original for no reason the project stated — and a
   STEP round trip silently degrading a part is a bad promise.
3. The failure modes are asymmetric. An over-fine artifact announces itself
   (a 19.9 MB STL, a slow viewer); an over-coarse one is silent, and under
   `solid test --faceted` it moves clearance verdicts (ADR-078's own risk).
4. The cost of the decision to the projects that want 0.5 is one line —
   `angular_deflection = 0.5` in the class body — which the `StepNode`
   documentation tells them to write, with the numbers task 7.1 measures
   beside it.

Recorded here so the pilot can overrule it cheaply: the change is a
two-line class-attribute declaration on `StepNode` plus a MODIFIED scenario
in `exact-geometry`.

### D10. The reader import stays inside the adapter module

`from OCP.STEPCAFControl import STEPCAFControl_Reader` at
`adapters/step.py` module scope, which `solid_node.node`'s `_EXPORTS`
deferral resolves only when `StepNode` is first accessed — the mechanism
`cli-startup-cost` exists to preserve. Measured (fact 11): 0.84 s in a
fresh interpreter, 0.000 s once `cadquery` is imported. Since `StepNode`
derives `ExactLeafNode` and so pulls `cadquery` in anyway, the marginal
cost of the STEP reader to a project that uses one is nil; the cost that
matters is the one the deferral already avoids — a solid2-only project, or
`solid viewer`, importing no `OCP` at all.

### D11. Tests author their fixtures in CadQuery and read them back

No binary STEP is committed, following `tests/stl_project/` (the `stl-node`
change's design D7): every fixture is a `cadquery.Assembly` with names and
colours set, saved to STEP into a temporary directory, and wrapped by a
`StepNode` — so the round trip itself is the evidence, and the test suite
does not carry a vendor file's licence. Facts 5–8 above were established
precisely to prove every case in this change is authorable that way:
duplicate names need two assembly levels, a face-only product is a
`cq.Shell`, and a single-product file needs `cq.exporters.export` rather
than an assembly.

## Risks / Trade-offs

- [A one-part assembly file demands a `part` name that looks redundant]
  → D3, deliberate; the inventory failure names the two products and the
  fix is one line. Guessing the root instead would silently hand a project
  a whole assembly as one part.
- [The cached document holds a large OCCT document for the life of the
  build process] → D6; one entry per file, evicted on change, in a
  fresh-interpreter build pass (ADR-067). The alternative costs 236 s per
  pass on the file that motivated the cycle.
- [Colour resolution reads the document on a build whose artifacts are all
  current] → D7; a project that declares its colours never triggers it, the
  read is cached, and this is strictly better than the by-hand code, which
  reads at construction unconditionally.
- [A project sews a face-only vendor part with a tolerance that closes a
  gap it should not] → the helper is explicit, its docstring states what it
  does not guarantee, and admission still judges the sewn result: a sewing
  that produces no solid fails.
- [`StepNode` at 0.1 rad gives an unprepared project a 19.9 MB artifact on
  its first build] → D9; the leaf's documentation carries the numbers
  measured on that very part through this leaf (task 7.1) and the one-line
  fix, at the point a project author is choosing.
- [XCAF's product model may not survive every exporter's dialect — a file
  with several free shapes, or with no names at all] → the inventory is the
  answer to both: an unnamed product is listed as such, and several free
  shapes are simply several products among which one must be named. Nothing
  in this design requires exactly one root.

## Migration Plan

Nothing to migrate: this is a new adapter, and no existing behaviour
changes. The two originating projects migrate on their own schedule, in
their own repositories, and their artifacts change content when they do —
because both currently premesh at 0.5 rad and will, under D9, declare
`angular_deflection = 0.5` to keep exactly the mesh they have today.

## Open Questions

- Whether a later cycle exposes the document's occurrence transforms as an
  assembly reader (the actuator types 55 placements by hand, of which 41
  are fasteners). This change deliberately keeps the part frame that such a
  cycle needs, and settles nothing else about it.
- Whether the same selection vocabulary should serve other XCAF-readable
  formats (IGES). Not asked for by any project.
- Whether `part` should eventually accept a path through nested assemblies
  (`'Gearbox/Pin'`) for a file where a name is ambiguous. Deferred until a
  real file forces it; today an ambiguity is a failure, not a guess.
