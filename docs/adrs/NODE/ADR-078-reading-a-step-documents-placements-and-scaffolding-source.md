# ADR-078: Reading a STEP document's placements, and scaffolding declarative source from them

**Status:** Accepted

**Date:** 2026-09-06

**Change:** `step-assembly-import`

**Extends:**
- [ADR-077: The STEP part as an exact external-file
  leaf](ADR-077-the-step-part-as-an-exact-external-file-leaf.md)

**Depends on:**
- [ADR-076: Declared tessellation
  precision](ADR-076-declared-tessellation-precision.md)

## Context and Problem Statement

ADR-077 gives the framework one product of a STEP document, in the
product's own frame, deliberately: "The file's placements are the
assembly's business; a later cycle may read them." A vendor STEP file
is not a bag of parts, though — where each part sits is the larger half
of what the file says, and until this change that half is retyped by
hand. `Internal-Cycloidal-Actuator`'s design record: the document holds
55 placements, six of which are typed into `machine.py` as angle/axis/
translation literals, plus a project-written test that recomposes each
placement from the document, existing only because the typing is by
hand. One of the six, `Eccentric_Shaft`, shows the hazard directly: the
axis sign is not visible in the matrix at a glance, and a naive
axis-angle extraction reports −79.0959° about +Y where the document's
own CAD package would show +79.0959° about −Y — the same rotation,
easy to get backwards by hand.

`openvmp` wrote the same walk against a different format, in project
code (`simulation/don1/blueprints.py`): a PartCAD `.assy` location
`[[x, y, z], [ax, ay, az], angle]` is "exactly a solid-node `rotate`
followed by a `translate`", composed outward through nested groups.
Two projects, two file formats, one job — read the placements a
document already carries and hand them to the framework as its own two
operations — and neither project's copy is reusable by the other or by
a third project that meets a vendor assembly.

The framework already has everything needed to *state* a placement: a
node's rest placement is an ordered list of `Rotation` and `Translation`
operations, premultiplied in declaration order (`solid_node/node/base.py`,
`operations.py`), so `rotate(angle, axis)` then `translate(vector)` is
exactly `T · R` — the canonical `[R | t]` form of a rigid placement. The
question this ADR settles is how to walk a document's occurrences, pull
that block out of each, and turn it back into that pair without losing
anything — and how to turn the answer into source a pilot can read.

## Decision Drivers

- Read the placements without retyping them: every occurrence's matrix,
  world-composed through nested sub-assemblies, decomposed to the
  1e-9 the framework's own reproduction demands — including the 180°
  turns that are not a corner case in a real document (27 of the
  actuator's 55 are exactly 180°, 2 are the identity).
- Never state a placement the framework's two operations cannot
  express. A mirror or a scale is a fact about the file, not something
  to approximate or silently drop.
- Turn a document into source a pilot immediately owns and edits, never
  into a black box the framework keeps regenerating.
- Do not touch what already works: `StepNode`'s frame, selection,
  admission and colour rules are untouched; nothing in the build path
  changes for a project that never runs the new command.

## Considered Options

1. **A reader (`StepAssembly`) sharing `StepNode`'s adapter module and
   cache, plus a scaffold command (`solid import-step`) that generates
   declarative source once** (chosen)
2. A new sibling module (`solid_node/step.py`) for the reader
3. Trace-and-`acos` angle/axis extraction, matching the naive form the
   actuator's design record already warns about
4. Generate `.repeat(count)` for a product placed more than once
5. Raise on an improper placement instead of reporting it
6. Prompt, back up, or write a `.new` file instead of refusing to
   overwrite generated source

## Decision Outcome

Chosen option: **`StepAssembly`, a reader added to the existing
`solid_node/node/adapters/step.py`, and `solid import-step`, a one-shot
CLI scaffold.** Neither is a node; neither runs at build time; nothing
existing changes behaviour.

### `StepAssembly` lives beside `StepNode`, not in a new module

Everything the reader needs — `_Document`, `_entry`, `_label_name`,
`_srgb_hex`, `_document_cache`, `cached_document` — already exists in
the adapter module and is private to it. A sibling module would either
re-implement the index or import private names across a module
boundary, which is how one document reader becomes two, and the
reader's whole point is to be the *same read* a `StepNode` pays for —
sharing the cache is sharing the module. `StepAssembly` is not added to
`solid_node.node._EXPORTS`: it is not a node class, and the export
table is what `from solid_node.node import X` serves; it is imported
directly from the adapter module by the one caller that needs it,
`solid_node/manager/import_step.py`.

### Occurrence identity is the component label's own entry, never a name

`TDF_Tool.Entry_s` reports a label's full tag chain from the document
root (`"0:1:3:2"`), already unique within the document regardless of
nesting depth — no manual path-chaining is needed on top of it.
Occurrence *names* are writer-dependent and sometimes absent: Inventor
writes `M4_12mm_Screw:1` … `:14`, while `cadquery.Assembly` writes the
child's name onto the *product* label and leaves the *component* label
effectively unnamed. An occurrence's reported label name is therefore
`''` rather than `None` when the writer left it blank — spelled out
because "empty" and "absent" must never be confused with "this is the
occurrence's identity", which the label name never is.

### `world = parent_world @ local`, walked from every free product

The walk starts at each of the document's free (unreferenced) labels —
normally one root — and recurses into `GetComponents_s` of every
assembly product, composing each component's own `gp_Trsf` onto the
running world matrix its container already carries. A part at
`(10, 0, 0)` inside a sub-assembly turned 90° about X and carried to
`(0, 20, 0)` reports a world translation of `(10, 20, 0)` — confirmed on
an authored fixture, since the one real vendor document available is a
flat tree (55 occurrences, all direct children of the root). Solid
counts for the `products` report read `GetShape_s` directly rather than
through `_Document.shape()`'s protective copy: the copy exists so two
`StepNode`s meshing the same product cannot contaminate each other
(ADR-077's own fix), and counting topology never meshes, so paying for
the copy would cost 163× for nothing it protects here (2.602 s against
0.016 s for the actuator's 21 products).

### Decomposition is OCCT's own quaternion, never trace-and-`acos`

`gp_Trsf.GetRotation()` gives a `gp_Quaternion`; `GetVectorAndAngle
(gp_Vec)` gives the signed angle and axis — the one OCP-binding trap
being that it returns the angle as a **one-element tuple**,
`(angle,) = q.GetVectorAndAngle(vec)`, writing the axis into `vec`.
Measured over all 55 placements of the actuator (27 of them exactly
180°, 2 the identity), reconstructing `Translation(t).matrix() @
Rotation(angle, axis).matrix()` and comparing element-wise against the
document's own matrix:

| route | worst error |
|---|---|
| trace, `acos((tr−1)/2)`, largest-diagonal axis at 180° | 3.0e-8 |
| Shepperd quaternion from the matrix (reference only) | 1.3e-15 |
| `gp_Trsf.GetRotation().GetVectorAndAngle()` (chosen) | 4.4e-16 |

The trace route is thirty times outside the 1e-9 the framework's own
reproduction test asks for, and it is wrong exactly on the 180° turns —
half of this document, not a corner case. The Shepperd branch-on-
largest-component method is accurate enough but reimplements in Python
what OCCT already exposes on the object the matrix came from in the
first place; it stays in the test suite as an independent cross-check,
never as the implementation.

Two conventions sit on top of OCCT's answer. A zero rotation carries an
arbitrary axis (OCCT's own quaternion has no preferred one at the
identity), so the reader states a fixed unit axis for it and the
generator omits the call entirely. And the angle stays signed in
`[−180°, +180°]` rather than folded into `[0°, 360°)` — deterministic
either way — with the axis whose largest-magnitude component is
positive, negating the angle to match: the same document always yields
the same literals, and `Eccentric_Shaft` reads `-79.0959` about
`(0, 1, 0)`, the form the actuator's own design record uses, rather
than the equally-correct `79.0959` about `(0, -1, 0)` a naive
extraction reports. This is a pilot-reviewer refinement over the
specification, which left the sign convention open.

### An improper placement is reported, never raised

A rotation block whose determinant is not `+1`, or a transform whose
scale factor is not `1`, is reported with both raw values and carries
no angle/axis/translation — the framework's `Rotation` and
`Translation` cannot state a mirror or a scale, and pretending
otherwise would silently lose the transform. The reader itself never
raises: one bad occurrence must not hide the other fifty-four, and the
reader is exactly the tool a pilot needs when a file surprises them.
The *command* is what refuses, because it is the one that would
otherwise have to lie about what it wrote.

**Implementation finding, this session:** no mirrored or scaled
occurrence placement proved authorable through this toolchain, on
either of two independent routes — `cadquery.Assembly.add(shape,
loc=cq.Location(trsf))` and raw `XCAFDoc_ShapeTool.AddComponent` with a
`TopLoc_Location`, both built from a `gp_Trsf` with `SetMirror` or
`SetScale`. `STEPCAFControl_Writer` resets the component's transform to
the identity on write in both cases; `STEPCAFControl_Reader` reads the
identity back. This is not an OCCT writer gap so much as a structural
fact about the mechanism a `NEXT_ASSEMBLY_USAGE_OCCURRENCE` occurrence
uses: its placement is the relative transform between two
`AXIS2_PLACEMENT_3D` frames, each right-handed by construction (its
second axis is always the cross product of the two it states), so the
relative transform between any two such frames is always proper — a
mirror or a scale cannot be expressed through this mechanism at all,
regardless of what the writer intends. The gate is still real: a
document written through STEP's other, less common assembly mechanism
(`CARTESIAN_TRANSFORMATION_OPERATOR_3D`/`MAPPED_ITEM`, which does carry
an explicit reflection) could still present one, and this toolchain's
own reader would still test it correctly. The gate is proved directly —
on constructed `gp_Trsf`s, and by forcing the gate's own function to
report one occurrence of an all-proper fixture improper — rather than
on an authored file, which the design and the specification both
describe as achievable and neither is, in this session's evidence.

### The scaffold: one declaration per occurrence, never `.repeat()`, and never overwritten

`solid import-step FILE [--into PACKAGE_DIR] [--model NAME]` follows
`solid new` (writes project source, `needs_node = False`) and `solid
models` (loads no node, never touches `pyproject.toml`). Generated
source is composed as text rather than through `manager/templates/`,
because it is a loop over document structure, not a name substituted
into a fixed shape.

`.repeat(count)` declares *identical* children reachable only by index;
every occurrence here needs its own `rotate`/`translate`, so repeating
would pair indexed children against a generated table of placements —
harder to read and impossible to annotate per instance. The cost
`.repeat()` usually buys does not apply either: fourteen declarations of
one parameterless `StepNode` subclass already share one `uniq_id` and
therefore one artifact, since `uniq_id` is derived from the class and
its resolved parameters, not from how many times a line is written.

Class names are a readable, non-injective rule (split on non-
alphanumeric runs, upper-case each piece's first letter, prefix `Part`
when the result would not start with one, suffix `_2`/`_3` on
collision) — `10010 Stator` → `Part10010Stator`, `M4_12mm_Screw` →
`M4_12mmScrew`. The reversible record is `part`, declared verbatim on
every generated class, not the identifier: a genuinely invertible
mangling would produce names no pilot wants to read or type, in
exchange for information already on the next line.

The command writes `parts.py` and `assembly.py` together or neither.
Both files existing is checked before either is written, and an
existing file stops the command naming it and writing nothing — the
same rule `solid new` applies to its target directory, because the
generated file is a starting point the pilot immediately edits, and
losing those edits is the one unrecoverable failure this command could
cause. The manifest lines are printed, never written: the command
cannot know whether this model should be the project's default, one of
several named models, or a scratch import, and `pyproject.toml` may
already carry anything else.

### Faithfulness is proved on generated source, not asserted on the reader alone

The actuator's own `test_machine.py` recomposed each hand-typed
placement from the document, existing only because the typing was by
hand. It becomes a framework test instead: the document is scaffolded
into a scratch project, built against this worktree, and each leaf's
composed world placement (`base.py`'s own `_compose_world_matrix`) is
compared against the reader's world matrix at the product's bounding-
box centre, within 0.01 mm — not a tautology, because the two sides
come from different code paths: one from the generator's emitted
literals through the framework's operation composition, the other from
the reader's own matrix product.

Measured on the actuator, scaffolded into a scratchpad project never
inside the actuator's own repository: `solid build` succeeds in 21.5 s
cold, writing 20 distinct part artifacts (the other 35 of the 55
occurrences are repeated placements of these, sharing an artifact
exactly as design D8 predicts) totalling 11.74 MiB of STL — against the
19.91 MB `Output_Shaft` alone would cost at the framework's inherited
default; this build's own `Output_Shaft` STL is 1.76 MB, matching
ADR-077's own `angular_deflection = 0.5` figure exactly. Every one of
the 55 generated leaves matched one of the reader's 55 occurrences, and
the worst placement deviation over all of them is 4.93e-10 mm — about
twenty million times inside the 0.01 mm asked. The structure extraction
itself costs 0.042 s after the document's own 11.10 s read is warm,
confirming design fact 7's order of magnitude on the final
implementation.

## Pros and Cons of the Options

### `StepAssembly` + `solid import-step` (chosen)

- **Good**: Deletes the reason both originating projects wrote their
  own occurrence walk, without moving `StepNode`'s frame decision
- **Good**: Exact to 1e-9 including the 180° turns that are half of a
  real document
- **Good**: Generated source is the pilot's from the moment it is
  written — readable, editable, never silently regenerated
- **Bad**: The adapter module grows a section that is not a node
  (accepted — a bounded cost against re-implementing or exposing
  private internals from a second module)

### A new sibling module for the reader

- **Bad**: Either re-implements `_Document`'s index or reaches across
  a module boundary for private names — the second copy of the reader
  this change exists to prevent

### Trace-and-`acos` extraction

- **Bad**: 3.0e-8 worst case, thirty times outside the 1e-9 contract,
  wrong exactly at the 180° turns that are half of the actuator's
  document — the naive extraction the originating project's own design
  record already named as a hazard

### Generate `.repeat(count)` for a repeated product

- **Bad**: Pairs indexed children against a generated placement table
  instead of named attributes; harder to read, impossible to annotate
  per instance, and buys no cost saving `uniq_id` does not already give

### Raise on an improper placement

- **Bad**: One bad occurrence would hide the other fifty-four and make
  the reader useless for the inspection a pilot needs when a file
  surprises them

### Prompt, back up, or write a `.new` file on an existing generated file

- **Bad**: Every alternative to refusing risks the one unrecoverable
  failure this command can cause — losing a pilot's edits to generated
  source

## Consequences

- New: `solid_node/manager/import_step.py`; `tests/test_step_assembly.py`
  and `tests/test_import_step.py`; fixtures added to
  `tests/step_project/` (authored in CadQuery, exported to STEP in a
  temporary build directory — no binary fixture committed).
- Changed: `solid_node/node/adapters/step.py` gains `StepAssembly`,
  `ProductInfo`, `Occurrence` and the placement walk; `solid_node/cli.py`
  gains one `COMMANDS` row (`import-step`); `tests/test_cli_lazy_imports.py`
  extends its command inventory and its class/name conformance check to
  admit a hyphenated command name.
- `step-assembly`, a new capability: reading a document's structure,
  the occurrence walk, the propriety gate, the exact decomposition, and
  the content of the source the scaffold generates from it.
  `cli` gains the `import-step` command's grammar, flags, refusal to
  overwrite, printed manifest, missing-kernel message and exit
  statuses.
- Nothing existing changes behaviour: `StepNode`'s frame, selection,
  admission and colour rules are untouched, and a project that never
  runs `import-step` and never constructs a `StepAssembly` builds
  identically.
- Not built here: any placement the generated source *animates* (the
  scaffold writes a machine at rest); the document's up-axis and unit
  handling; re-running the scaffold to merge into edited source; any
  import format other than STEP.
- The two originating projects adopt the generated source in their own
  repositories on their own schedule: `Internal-Cycloidal-Actuator` can
  replace its six hand-typed placements and the recomposition test that
  existed only to check them; `openvmp` keeps its `.assy` reader, which
  reads a different format, but stops being the only place the walk
  exists.

## References

- `solid_node/node/adapters/step.py` — `StepAssembly`, `ProductInfo`,
  `Occurrence`, `_decompose`, `_propriety`, `_trsf_matrix`
- `solid_node/manager/import_step.py` — the generator and the
  `ImportStep` command
- `solid_node/node/base.py` — `_compose_world_matrix`, the operation
  composition this reader's decomposition reproduces
- `tests/test_step_assembly.py` — the occurrence walk, the
  decomposition and its Shepperd cross-check, the propriety gate
- `tests/test_import_step.py` — the naming rules, generated source
  content, the faithfulness proof, and the command
- `docs/cli.rst`, `:ref:`import-step`` — the command reference
- `docs/leaf-nodes.rst`, `:ref:`step-import`` — cross-referenced from
  the `StepNode` section
- `projects/Internal-Cycloidal-Actuator` and `openvmp` — the two
  originating projects' hand-written occurrence walks this reader
  replaces
- OpenSpec change `step-assembly-import`, capability `step-assembly`
