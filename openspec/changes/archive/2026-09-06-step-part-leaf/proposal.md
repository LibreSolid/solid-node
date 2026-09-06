## Why

STEP is the format every CAD package and every vendor publishes, and the
framework cannot read one. `StlNode` brings in a committed mesh; nothing
brings in a committed solid. So a project that wants a vendor part writes
the OCP itself — and two projects now have, the same code twice:

- **Internal-Cycloidal-Actuator** wraps a 35,107,597-byte Inventor STEP
  assembly: one root free shape, **55 occurrences of 20 products**, about
  800 solids (`ODrive_S1` alone is 545). Its design record's "What the
  framework made this project do by hand" opens with it:

  > **No STEP leaf.** solid-node 0.6 has `CadQueryNode`, `Build123dNode`,
  > `StlNode` and the rest, and nothing that imports a STEP file.
  > Selecting one product out of an assembly document by name therefore
  > needs hand-written OCP: `STEPCAFControl_Reader` with name and colour
  > modes, `XCAFDoc_DocumentTool.ShapeTool_s`, `GetFreeShapes`,
  > `GetComponents_s`, `GetReferredShape_s`, `TDataStd_Name`, plus sewing
  > for a product that comes back as faces. **The same code already exists
  > in `openvmp`** (`simulation/don1/parts.py`, `StepPart`), written for
  > the same reason; this project is the second to write it. A
  > `StepNode(file=..., part=...)` leaf would delete both copies.

  It also had to build its own document cache, and says why:

  > **No document cache.** Measured above: 11.6 s per read+transfer, six
  > uncached nodes ≈ 70 s per build pass against ≈ 12 s cached. The
  > framework tracks source files for staleness but has no notion of an
  > expensive shared source that many nodes read, so the project carries
  > its own module-level dict keyed on (path, mtime) — and carries the
  > risk the framework's own docs warn about, that geometry depending on a
  > data file read at runtime can look current when it is not.

- **openvmp** (`simulation/don1/parts.py`) does the same over **67 vendor
  STEP files**: `import_step` with a missing-file message naming the fetch
  command, `solids_from_faces` sewing the two face-only files (the hook and
  the battery) into solids, `self.color = materials.colour(part)` from a
  project table, and `self.files = self.files | {self.path}` to put the
  STEP file into the tracked source set by hand.

And the leaf is worth having beyond deleting duplicated code: unlike a
mesh, a STEP part is **exact**. `StlNode` is faceted by doctrine (ADR-054),
so an imported mesh makes every fusion above it faceted and answers every
spatial question on triangles. A STEP part is a B-rep, so it can be an
`ExactLeafNode`: exact fusion with a printed bracket, exact intersection
and clearance verdicts, a `.brep` artifact, `shape()`.

## What Changes

- A new leaf adapter `StepNode` (`solid_node/node/adapters/step.py`,
  exported from `solid_node.node`), deriving `ExactLeafNode`. It carries
  over `StlNode`'s three rules — admitted not assumed, selected not
  guessed, corrected in code — over a solid instead of a mesh.
- **Declaration.** `step_source`, a path resolved relative to the directory
  of the module defining the subclass, exactly as `stl_source` is. The
  resolved file is the node's source file for freshness, and the wrapper
  module joins the tracked source set for ADR-055's reason: `part` and
  `adjust` decide the part as much as the file does. A subclass without
  `step_source` fails at construction naming the class.
- **Selection by name.** `part` names the product the node is, as the file
  carries it (the `PRODUCT` name, which XCAF exposes as the shape label's
  name). A file with exactly one candidate product needs no `part` — the
  candidates being every product except a root that is itself an assembly,
  so both a bare one-part file and the commoner file wrapping one part in an
  assembly select themselves, while a multi-component root is never handed
  to a node by omission. A file with more candidates, with `part` unset or
  naming a product the file does not have, fails
  with the file's inventory — one line per product: name, kind, occurrence
  count, solid count, bounding box, volume — so the failure is the
  discovery tool, as `StlNode`'s is. Two products of one name fail naming
  the ambiguity. Any product may be named, a part or a sub-assembly.
- **Own frame.** The geometry is the product's own prototype shape, never
  an occurrence's placed copy. The file's placements are the assembly's
  business; a later cycle may read them.
- **Correction in code.** `adjust(self, shape)` receives the selected
  geometry as a CadQuery `Shape` and returns the corrected one. No scale,
  unit, recenter or sew knobs. The module exports `solids_from_faces(shape,
  tolerance)` — openvmp's sewing, promoted — for an `adjust` hook to call
  knowingly.
- **Admission.** The geometry after `adjust` must hold at least one solid,
  or the build fails naming the node, the file, the part and what the
  geometry does hold, and writes nothing. Nothing is repaired silently.
- **Colour.** A subclass that declares no `color` takes the part's colour
  from the file, converted to the `#RRGGBB` string the framework's `color`
  attribute already is. Resolved lazily, so a project that declares its own
  colours never reads the document for one, and only an actual declaration
  counts as one — an assignment of no colour during construction leaves the
  document as the source.
- **One read per file per process.** The XCAF document is read once and
  cached on `(path, mtime_ns)`, evicting on change, in the shape of
  `exact._shape_cache`. Measured on the actuator file: **11.79 s** for one
  read+transfer, so its six leaves cost 11.79 s cached against **70.7 s**
  uncached, and twenty leaves over one file would cost **236 s** uncached
  against the same 11.79 s.
- **Exact leaf.** `exact` is true; `shape()`, the `.brep`, exact fusion and
  the spatial assertions work as for `CadQueryNode`, and the STL artifact
  is written by `ExactLeafNode.as_scad` and so honours the
  `linear_deflection` / `angular_deflection` declaration of
  `declared-tessellation-precision` (ADR-076). `StepNode` inherits those
  defaults unchanged (0.1 mm, 0.1 rad); see design D9.
- **Deferred reader import.** The OCP STEP reader is imported by the
  adapter module, which `solid_node.node` resolves only when `StepNode` is
  first accessed. Measured: importing `OCP.STEPCAFControl` in a fresh
  interpreter costs **0.84 s**, and 0.000 s once `cadquery` is imported.

Nothing existing changes behaviour. No adapter, artifact, or currency rule
is modified; `StlNode` is untouched and stays faceted by doctrine.

## Capabilities

### New Capabilities

- `step-import`: the STEP part leaf — declaration and freshness, selection
  of a product by name with the file's inventory as the failure, the
  product's own frame, the `adjust` correction hook and the sewing helper,
  the solid-admission gate, colour from the file, one document read per
  file per process, and the leaf's exactness.

### Modified Capabilities

- `node-model`: its "Multi-backend leaf adapters" requirement enumerates
  every adapter, which declares a `namespace`, which needs no external
  tool, and which are exact. `StepNode` is added to each of those lists.
- `exact-geometry`: its "Node exactness capability" requirement enumerates
  the exact and the faceted leaf adapters; `StepNode` joins the exact ones.
  Its "Declared tessellation precision" requirement enumerates the adapters
  beneath `ExactLeafNode` that the declaration reaches; `StepNode` joins
  them, at the same defaults.
- `cli-startup-cost`: its "Node backend exports resolve on first use"
  requirement names the exports whose backend import is deferred; the STEP
  reader is added, so `import solid_node.node` still imports no `OCP`.

## Impact

- New: `solid_node/node/adapters/step.py`, `tests/test_step_node.py`,
  `tests/step_project/` (fixtures authored in CadQuery and saved to STEP in
  a temporary build directory — no binary fixture is committed, as for
  `tests/stl_project/`).
- Changed: `solid_node/node/__init__.py` — one `_EXPORTS` row.
- Documentation: `docs/leaf-nodes.rst` gains a `StepNode` section beside
  `StlNode`'s and a row in its adapter list; `docs/changelog.rst`
  "Unreleased" gains an entry naming both originating projects.
- Consumers: none change. A project with no `StepNode` builds identically
  and imports no STEP reader.
- Originating projects, in their own repositories, on their own schedule:
  `Internal-Cycloidal-Actuator` deletes its `Document`, `get_document`,
  `premesh` and `solids_from_faces` and declares six `StepNode`s;
  `openvmp` deletes its `import_step`, `premesh` and `solids_from_faces`
  and its by-hand `self.files` union. Neither is done in this cycle.
- The shop's `shop-skills/solid-node-api/SKILL.md` will need the new leaf;
  that is a shop file and a separate change, not part of this cycle.
- Not in this change: reading the file's placements (an assembly reader),
  the document's up axis, unit handling, and any import format other than
  STEP.
