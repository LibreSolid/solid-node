## Context

`StepNode` gives the framework one product of a STEP document in the
product's **own frame**, and deliberately stops there: "The geometry is the
product's own prototype shape, never an occurrence's placed copy. The
file's placements are the assembly's business; a later cycle may read
them." A vendor STEP file is not a bag of parts, though; it is an assembly,
and where each part sits is the larger half of what the file says. Today
that half is retyped by hand: six placements in the actuator's
`machine.py`, and a project-written test that recomposes each from the
document only because the typing is by hand.

The framework already has everything needed to *state* a placement. A
node's rest placement is an ordered list of `Rotation` and `Translation`
operations, composed by premultiplication (`solid_node/node/base.py`,
`operations.py`, and the shop's `docs/4D-transformation-matrix.md`):
operations run in declaration order with each later one outermost, so
`rotate(angle, axis)` then `translate(vector)` is exactly `T · R` — the
canonical `[R | t]` form of a rigid placement. openvmp's `.assy` reader
says the same in its own docstring: "the part is turned by `angle` degrees
about the axis through its own origin, then carried to `[x, y, z]` —
exactly a solid-node `rotate` followed by a `translate`." So the whole job
is: walk the document's occurrences, pull the 4x4 out of each, and turn it
back into that pair without losing anything.

**Empirical facts this design rests on.** Established in this worktree
against the workspace venv (OCCT 7.8 through `cadquery-ocp`), on the
actuator's 35 MB document
(`projects/Internal-Cycloidal-Actuator/simulation/actuator/vendor/Internal
Cycloidal Actuator.stp`) and on assemblies authored with
`cadquery.Assembly` and saved to STEP.

1. The occurrence is the *component* label; its transform is
   `XCAFDoc_ShapeTool.GetLocation_s(component).Transformation()`, a
   `gp_Trsf` whose `Value(i, j)` for `i` in 1..3 and `j` in 1..4 is the
   placement's 3x4 rigid block. Walking every assembly label's components
   and recursing through `GetReferredShape_s` into a target that is itself
   an assembly reproduces the actuator's **55 occurrences of 20 products**
   exactly, matching the design record's table.
2. The actuator's tree is **flat**: its one free shape is the root
   assembly and all 55 occurrences are its direct children (max depth 0).
   The document therefore proves nothing about nesting, and the nested
   case must come from an authored fixture (fact 6).
3. **Occurrence label names are writer-dependent.** Inventor writes
   `M4_12mm_Screw:1` … `:14`; `cadquery.Assembly` writes the child's name
   onto the *product* label and leaves the component label named `2`, i.e.
   effectively unnamed. An occurrence's identity therefore cannot be its
   label name.
4. **Every one of the actuator's 55 placements is proper.** Rotation-part
   determinants are exactly `1.000000000000000` (min = max), scale factors
   are exactly `1.0`, `gp_Trsf.Form()` is `CompoundTrsf` for all of them,
   and the worst orthogonality residual `max|R·Rᵀ − I|` over all 55 is
   **2.2e-16**.
5. **Angle/axis extraction must be quaternion-based.** Round-tripping each
   placement through `Translation(t).matrix() @ Rotation(angle,
   axis).matrix()` and comparing element-wise with the document's matrix,
   over all 55 occurrences:
   - recovering the angle from the trace (`acos((tr−1)/2)`, with a
     special-cased 180° branch taking the axis from the largest diagonal
     of `(R+I)/2`): worst error **3.0e-8**, and the worst case *is* a 180°
     occurrence (`M4_12mm_Screw:8`);
   - recovering a quaternion from the matrix by Shepperd's
     branch-on-largest-component method, then `angle = 2·atan2(|v|, w)`:
     worst error **1.3e-15**;
   - asking OCCT: `gp_Trsf.GetRotation()` → `gp_Quaternion`, then
     `GetVectorAndAngle(gp_Vec)`: worst error **4.4e-16**.

   27 of the 55 are exactly 180° and 2 are the identity, so this is not a
   corner case in this document — it is half of it. The 1e-9 the spec asks
   for is reachable by either quaternion route and by neither trace route.
   `GetVectorAndAngle` reports the angle signed in `[−π, +π]` preserving
   the axis direction (`Encoder_Holder:1` comes back as −179.99999999999997°
   about `(0.9561, 0, 0.2932)`), and for a zero rotation it returns an
   arbitrary axis (`Bottom_Housing:1`: 0° about `(0.360, 0.918, −0.166)`),
   so a zero angle must be given a stated axis by the reader.
11. **`GetVectorAndAngle`'s OCP binding returns a one-element tuple**,
    `(angle,) = q.GetVectorAndAngle(vec)`, writing the axis into the
    `gp_Vec` argument. Treating the return value as a float, or as a
    `(vec, angle)` pair, fails at runtime; this cost a debugging round in
    this session and is the kind of thing a test pins.
6. Nesting composes as expected, on an authored fixture: a part at
   `(10, 0, 0)` inside a sub-assembly turned 90° about X and carried to
   `(0, 20, 0)` reports a world translation of `(10, 20, 0)` under
   `world = parent_world @ local`. The same fixture places the same
   product a second time at the root, giving a product with two
   occurrences at two depths.
7. **Cost, after the cached read** (which cycle B measured at 11.79 s and
   which measured 13.9–15.3 s in this session's runs). On the actuator
   document: names, kinds, occurrence counts and colours for all 21
   products, **0.0014 s**; solid counts for all 21, **0.016 s**; the walk
   of all 55 occurrences with their `gp_Trsf` matrices, **0.002 s**. Total
   structure: **0.02 s**.
8. **Solid counts must not go through `_Document.shape()`.** That method
   returns `Shape.copy()` so two `StepNode`s meshing the same product
   cannot contaminate each other (cycle B's task 6.4 finding). The copy is
   the entire cost: solid counts for the 21 products cost **2.602 s**
   through `shape()` and **0.016 s** through `GetShape_s` directly —
   163×. The reader counts topology and never meshes, so it reads the
   shared shape.
9. Colour lives on the product label: **0 of the actuator's 55 component
   labels** carry a surface colour, while 8 of its 21 product labels do.
   An occurrence's colour is therefore normally absent, and the product's
   colour — which `StepNode` already resolves — is the one that matters.
10. The actuator's product names include `10010 Stator`,
    `40x50x6mm_Bearing`, `M4_12mm_Screw`, `ODrive_S1` and
    `Cycloidal_Disk_1`: leading digits, embedded `x`-dimensions, spaces
    and mixed case, none of them a Python identifier.

## Goals / Non-Goals

**Goals:**

- Read a STEP document's assembly structure — products, occurrences,
  placements, nesting — without loading a node or writing an artifact.
- Hand every proper placement back as the exact `rotate`-then-`translate`
  pair the framework composes, to 1e-9, including 180° turns.
- Refuse, loudly and specifically, a placement the framework's two
  operations cannot express.
- Turn a document into readable, editable, project-owned declarative
  source in one command, and never overwrite what the pilot has edited.
- Make the actuator's hand-written recomposition contract a framework
  test on generated source.

**Non-Goals:**

- Deciding what moves. The scaffold writes a machine at rest; which
  joints are driven is the pilot's design decision, and `simulate()` is
  where it belongs.
- Re-running the scaffold over edited source, or any merge, diff or
  update mode.
- The document's up axis and unit handling. The actuator's Y-up reframing
  is a project decision its own design already records as such.
- A `StepAssembly` node, or any build-time use of the reader.
- Any import format other than STEP.

## Decisions

### D1. The reader lives in `solid_node/node/adapters/step.py`, not a new `solid_node/step.py`

The specification offered a sibling module. Rejected, for three reasons.
First, everything the reader needs already exists in the adapter module and
is private to it: `_Document`, `_entry`, `_label_name`, `_srgb_hex`, the
`_document_cache` and `cached_document`. A sibling module would either
re-implement the index or import private names across a module boundary,
which is how one document reader becomes two. Second, the reader's whole
point is to be the *same read* a `StepNode` pays for; sharing the cache is
sharing the module. Third, "adapters" already names the place where a
foreign file format meets the framework, and this is the second half of
that adaptation, not a different subject.

The one cost is that `solid_node.node.adapters.step` grows a section that
is not a node. That is bounded — the module keeps its "reading and
indexing" / "the node" sections and gains an "assembly structure" one —
and it is cheaper than a split. If a third subject appears the module can
be split later, with `StepAssembly` and `StepNode` both re-exported.

`StepAssembly` is *not* added to `solid_node.node._EXPORTS`: it is not a
node class, and the export table is what `from solid_node.node import X`
serves. It is imported from the adapter module by the one caller that
needs it, `solid_node/manager/import_step.py`.

### D2. Quaternion decomposition through OCCT, not trace-and-acos

Fact 5 decides this, and the margin is not subtle: 4.4e-16 against 3.0e-8,
with the trace route's failures landing on the 180° turns that are half of
this document.

The decomposition is OCCT's own: `gp_Trsf.GetRotation()` gives a
`gp_Quaternion`, and `GetVectorAndAngle(gp_Vec)` gives the axis and the
signed angle. The reader already holds the `gp_Trsf` — it is where the
matrix came from — so this asks the same library that wrote the placement
what the placement is, rather than re-deriving it from numbers it printed.
Fact 11 is the one trap: the binding returns the angle as a one-element
tuple.

Rejected: deriving the quaternion from the 3x3 block in Python by
Shepperd's method (branch on the largest of `trace`, `R₀₀`, `R₁₁`, `R₂₂`,
then `angle = 2·atan2(|v|, w)`). It is accurate enough — 1.3e-15, fact 5 —
but it is a dozen lines of numerics reimplementing what OCCT already
exposes, and it would be the only place in the reader that works from the
extracted matrix rather than from the document's own objects. It stays as
the reference implementation the tests can cross-check against.

Rejected: the trace route, at 3.0e-8. It is the naive extraction the
actuator's design record warns about, and it fails exactly where this
document is densest.

Two conventions the reader fixes on top of OCCT. A rotation whose angle is
zero comes back with an arbitrary axis (fact 5), so the reader reports a
stated unit axis for it and the generator omits the call entirely (D8).
And the angle is left signed in `[−180°, +180°]` as OCCT reports it, not
folded into `[0°, 360°)`: it is deterministic for a given matrix either
way, and the signed form is what the vendor's CAD package shows. This is
the resolution of the actuator's complaint that
"`Eccentric_Shaft` is −79.0959° about +Y, not +79.0959° about −Y as an
axis-angle extraction naively reports" — the two statements are the same
rotation, and the point is no longer which one is "right". OCCT reports
that occurrence as **+79.0959° about (0, −1, 0)**, the form the design
record calls naive; the round-trip test (D11 and the spec's
first scenario) proves it reproduces the document's matrix, and the pilot
never has to reconcile a sign by eye again.

Ratification note: the pilot's reviewer fixed the sign convention the
specification left open — the stated axis is the one whose
largest-magnitude component is positive, angle negated to match — so the
generated literal for `Eccentric_Shaft` reads `-79.0959` about `(0, 1, 0)`,
the form the actuator's own record uses; and the scaffold declares
`angular_deflection = 0.5` on every generated part (spec, "Generated part
source"), the one knob every vendor document has wanted.

### D3. `world = parent_world @ local`, and identity is by path, not by name

Fact 6 confirms the composition. Occurrence identity is the chain of
component labels from the root — each label's `TDF_Tool` entry, which cycle
B's `_entry` already provides — because fact 3 shows label *names* are
absent or meaningless depending on who wrote the file. The label name is
reported as a field for a human to read; it is never the key.

### D4. The reader counts solids on the shared shape, not on a copy

Fact 8. `_Document.shape()`'s copy exists so meshing cannot leak between
nodes; the reader never meshes, so it reads `GetShape_s` directly and pays
0.016 s instead of 2.6 s. This keeps the whole structure inside the 0.02 s
of fact 7, and it is a read-only traversal of topology, which is exactly
what the copy was not protecting against.

(Noted, not fixed here: cycle B's `_Document.describe()` — the inventory a
`StepNode` prints when selection fails — goes through `shape()` and so
pays the same 2.6 s on this document, plus `Volume()`. It is a failure
path, it is already documented as costed, and changing it is not this
cycle's business.)

### D5. Propriety is a report, not an exception

An improper placement does not raise from the reader. `StepAssembly` is a
description of a file, and a file that describes a mirror is still
describable — the occurrence simply carries no decomposition, and carries
the determinant and scale factor that explain why. The *command* is what
refuses (D9): it cannot write source for a placement it cannot state.

Rejected: raising at read time. It would make one bad occurrence hide the
other 54, and it would make the reader useless for exactly the
investigation a pilot needs when a file surprises them.

The test is `|det − 1| > 1e-9` on the rotation block, or
`|scale − 1| > 1e-9`; fact 4 shows the actuator sits at the exact values,
so the tolerance is not load-bearing for the real file.

### D6. The scaffold is a command, not an API

`solid import-step` follows `solid new` (writes project source; `needs_node
= False`) and `solid models` (loads no node). It is registered in
`cli.COMMANDS` as one row, so the existing lazy-dispatch contract carries
it: the command's module — and therefore the STEP reader — is imported
only when the command runs.

Unlike `solid new`, the generated source is not a template with a name
substituted; it is composed from the document. So the generator emits
source text directly rather than through
`solid_node/manager/templates/`. A template would have to be a loop over
document structure anyway, which is a program, not a template.

### D7. Names: readable class names, with `part` as the record

Fact 10 shows the names that must be handled. The rule is stated in the
spec; the design point is *why it need not be injective*. A generated class
always declares `part = '<exact product name>'`, so the document's own name
is present in the generated file, verbatim, on every class. A genuinely
invertible mangling (percent- or hex-escaping every separator) would give
class names like `Part10010_20Stator`, which no pilot wants to read or
type, in exchange for recovering information that is already on the next
line. Collisions get a `_2`, `_3` suffix in document order, so the mapping
stays one-to-one within a generated file even though the rule is not
injective in general.

This is a departure from the specification's "reversible rule", made
deliberately: the reversible record is `part`, not the identifier.

### D8. One declaration per occurrence; `.repeat()` is never generated

The specification asked for a decision. `.repeat(count)` declares
count-many **identical** children named `<attr>-<index>`, reachable only as
a list. Every occurrence here needs its own `rotate`/`translate`, so a
`.repeat()` generation would have to pair `self.screws[i]` against a
generated table of placements — a loop over a literal list of 14 rows,
which is harder to read and harder to edit than 14 named attributes, and
which the pilot cannot annotate per screw.

The usual reason to prefer `.repeat()` — cost — does not apply:
`uniq_id` is derived from the class and its resolved parameter values, so
fourteen declarations of one parameterless `StepNode` subclass share one
`uniq_id` and therefore one artifact, exactly as `.repeat(14)` would. The
choice is purely about the readability of source the pilot owns, and
separate declarations win.

Identity operations are omitted rather than emitted as `rotate(0, ...)` or
`translate([0, 0, 0])`: two of the actuator's 55 occurrences are the
identity and a generated no-op invites a reader to wonder what it is for.

### D9. The command writes both files or neither

Three gates, all checked before anything is written: the kernel imports,
the document reads, and every placement is proper. Then both files are
checked for existence, and only then is either written. A half-scaffolded
package — `parts.py` present, `assembly.py` refused — is worse than none,
because the pilot cannot tell whether the parts file is complete.

Refusing to overwrite (rather than prompting, backing up, or writing
`parts.py.new`) is the same rule `solid new` applies to its target
directory, for the same reason: the generated file is a starting point the
pilot immediately edits, and losing those edits is the one unrecoverable
failure this command could have.

### D10. The manifest is printed, never edited

`solid import-step` does not know whether the pilot wants this model to be
the project's default, one of several named models, or a scratch import;
and `pyproject.toml` may carry anything else. Following `solid models`,
which reads the manifest and never writes it, the command prints the lines
and lets the pilot place them.

### D11. The faithfulness test is the actuator's own contract, promoted

The actuator wrote `test_machine.py` to recompose each placement from the
document, and its design says that contract "exists only because the
typing is by hand; with a reader it would be tautology". It becomes a
framework test on *generated* source instead: scaffold the actuator
document into a scratchpad project, build it against this worktree, and
compare each leaf's composed world placement against the reader's world
matrix at the product's bounding-box centre, within 0.01 mm. That is not a
tautology, because the two sides come from different code — one from the
generator's emitted literals through the framework's operation
composition, the other from the reader's matrix product.

The scratchpad location matters: the generated project is written to a
temporary directory, never into the actuator's repository.

## Risks / Trade-offs

- **The reader grows the adapter module past comfort (D1).** → The module
  keeps explicit sections and the reader is one of them; a split into
  `adapters/step/` stays available and costs only re-exports, since
  nothing outside imports the private names.
- **A decomposition that is exact to 1e-9 is still not the file's own
  literals.** A pilot diffing generated source against the vendor's CAD
  will see `79.0959° about (0, −1, 0)` where the CAD package shows
  `−79.0959° about (0, 1, 0)`. → The generated comment names the
  occurrence and the source document, the round-trip test proves the pair
  reproduces the matrix, and D2 states the convention once.
- **Nesting is proved only on authored fixtures (facts 2, 6).** The one
  real vendor document available is flat. → The fixtures cover nesting to
  two levels, a product placed at two depths, and a sub-assembly placed at
  a non-identity transform; the actuator covers scale (55 occurrences, 20
  products) and the 180°/identity cases.
- **No real improper placement is available to test against.** → The
  fixtures author one by placing a mirrored shape, and the gate is tested
  on determinant and scale factor independently.
- **Generated source is a snapshot.** If the vendor ships a new revision of
  the STEP file, the scaffold cannot update edited source. → Out of scope
  and stated as such; the command's refusal to overwrite makes the
  limitation visible rather than dangerous, and the pilot can scaffold
  into a fresh directory and diff.
- **`import-step` is the first command whose module imports the
  exact-geometry kernel unconditionally.** → It is still lazy at the CLI
  level (D6), so `solid -h`'s "may import every command module" clause is
  the only path that pays it, exactly as for the other exact commands, and
  the missing-kernel message is a checked failure rather than a traceback.

## Migration Plan

Nothing to migrate. Both pieces are additive: no existing node, artifact,
currency rule or command changes behaviour, and a project that never runs
`import-step` and never constructs a `StepAssembly` is unaffected. The
originating projects adopt the generated source in their own repositories
on their own schedule.

## Open Questions

- Should `import-step` gain a `--products`/inventory mode that prints the
  structure without writing source? The reader makes it nearly free, and
  it would replace the "provoke a `StepNode` selection failure to see the
  inventory" idiom. Not proposed here; it is a second command shape and
  wants its own evidence that a pilot wants it.
- The generated root class currently has no parameters. A document whose
  placements are visibly a pattern (the actuator's 14 M4 screws are on a
  bolt circle) could be scaffolded with a `Count` and a comprehension, but
  detecting a pattern in placements is a guess about design intent, and a
  wrong guess is worse than 14 explicit rows. Left to the pilot's editing.
