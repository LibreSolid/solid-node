## Why

`StepNode` (the previous cycle) reads one product out of a STEP document
in the product's **own frame**, and says so deliberately: "The file's
placements are the assembly's business; a later cycle may read them."
This is that cycle. Until it lands, every placement a vendor document
already states has to be typed into project source by hand.

**Internal-Cycloidal-Actuator**, archived change
`2026-09-06-simulate-the-internal-cycloidal-actuator` (`design.md`, "What
the framework made this project do by hand"):

> **No assembly reader.** The document holds **55 placements**. **Six**
> are typed into `machine.py` by hand as angle/axis/translation literals.
> Each hand decomposition is a place to make an error that the file
> itself could have prevented: the axis sign is not visible in the matrix
> at a glance (`Eccentric_Shaft` is −79.0959° about +Y, not +79.0959°
> about −Y as an axis-angle extraction naively reports), and the disks'
> translations are not purely axial — (0.8974, −5.25, 3.8954) and
> (−0.1187, 2.75, −3.9470) mm — so a transposed component looks
> plausible. The contract in `test_machine.py` that recomposes each
> placement from the document exists only because the typing is by hand;
> with a reader it would be tautology. Modelling the whole actuator
> instead of the drive train would mean typing 55 of these, of which 41
> are fasteners.

**openvmp** wrote the same reader against a different source format,
in project code (`simulation/don1/blueprints.py`):

> The OpenVMP project describes each robot as PartCAD assemblies: YAML
> files (`robots/don1/*.assy`, templated with Jinja) that place catalogue
> parts and other assemblies by a PartCAD `location`. This module does
> not replace those files; it reads them. […] A location is
> `[[x, y, z], [ax, ay, az], angle]`: the part is turned by `angle`
> degrees about the axis through its own origin, then carried to
> `[x, y, z]` — exactly a solid-node `rotate` followed by a `translate`.
> Nested unnamed groups compose the same way, and a nested `assembly` is
> another `.assy` file with its own parameters.

Two projects, two file formats, one job: read the placements a document
already carries and hand them to the framework as `rotate` then
`translate`. openvmp's module even composes nested groups by matrix and
re-extracts a rotation vector — the walk this change makes framework
code. Neither project's copy is reusable by the other, and neither is
reusable by the third project that meets a vendor assembly.

## What Changes

Two pieces, a reader and a scaffold. Both are one-shot: neither is a
node, neither runs at build time, and nothing in the build path changes.

- **`StepAssembly(path)`, a reader, not a node**, in the existing adapter
  module `solid_node/node/adapters/step.py` (design D1). It reads the
  document through the previous cycle's `(path, mtime_ns)` cache and
  reports the document's structure:
  - **`products`** — one entry per product: name, kind (`part`,
    `sub-assembly`, `root assembly`), occurrence count, solid count and
    colour, the same facts `StepNode`'s inventory already knows.
  - **`occurrences`** — one entry per *placement*, walked through nested
    sub-assemblies: the occurrence's own identity, its product, its
    parent product (or the root), its **placement matrix in the parent's
    frame**, its **world matrix** composed through its parents, its
    colour when the occurrence carries one, and — derived — the exact
    `(angle_deg, axis)` and `translation` pair that reproduces the
    placement matrix through the framework's own `Rotation` then
    `Translation`.
  - **A propriety gate.** A placement that is not a proper rigid
    transform — determinant ≠ +1, or a scale factor ≠ 1 — is reported as
    improper with its determinant and scale factor and is **not**
    decomposed, because the framework's two operations cannot express a
    mirror or a scale. (All 55 of the actuator's placements are proper:
    determinant exactly 1.0, scale factor exactly 1.0, orthogonality
    residual 2.2e-16 — design fact 4.)
  - **Exactness.** The angle/axis extraction goes through the kernel's own
    quaternion, not through the trace and an `acos`, so the round trip
    holds for every proper rotation including the 180° turns and the
    identity. Measured over all 55 placements of the actuator (27 of them
    exactly 180°, 2 of them the identity): the quaternion route reproduces
    each matrix to **4.4e-16**, the `acos` route to only **3.0e-8** —
    thirty times outside the 1e-9 the contract asks for, and it fails
    precisely on the 180° cases (design fact 5).
  - **Cost.** After the cached read, the whole structure of the 35 MB
    actuator document — 21 products with solid counts and colours, 55
    occurrences with matrices and decompositions — costs **0.02 s**
    (design fact 7).

- **`solid import-step FILE [--into PACKAGE_DIR] [--model NAME]`**, a
  one-shot scaffold that writes **project-owned source the pilot then
  edits**, in the declarative class-body idiom of `docs/declaring.rst`:
  - `parts.py` — one `StepNode` subclass per product that is a part,
    declaring `step_source` (the file, relative to the package
    directory) and `part` (the exact product name), and no colour, so
    the document's colour flows through the leaf.
  - `assembly.py` — one `AssemblyNode` per assembly product, declaring
    one child per occurrence in the class body, and a `render()` placing
    each child by `rotate(angle, axis)` then `translate(vector)`, each
    placement preceded by a comment naming the occurrence and the
    document it came from. Nothing moves: no drivers, no `simulate()`.
  - **It never overwrites.** An existing `parts.py` or `assembly.py`
    stops the command naming the file, so a pilot's edits can never be
    lost.
  - **It writes nothing when a placement is improper**, and says which.
  - It **does not load a node** and **does not touch `pyproject.toml`**:
    it prints the manifest lines to add. It needs `cadquery`/OCP, like
    every exact path, and says so when they are absent.

Nothing existing changes behaviour. `StepNode` is untouched; no artifact,
currency or build rule moves.

## Capabilities

### New Capabilities

- `step-assembly`: reading a STEP document's assembly structure — the
  products, the occurrence walk through nested sub-assemblies, the
  placement and world matrices, the propriety gate, the exact angle/axis
  decomposition into the framework's own two operations, and the content
  of the source the scaffold generates from it.

### Modified Capabilities

- `cli`: gains the `import-step` command — its grammar, its flags, its
  refusal to overwrite, the manifest lines it prints, its missing-kernel
  message, and its exit statuses. (`solid new` is the precedent for a
  command that writes project source from templates; `solid models` for
  one that loads no node.)

## Impact

- New: `solid_node/manager/import_step.py`, `tests/test_step_assembly.py`,
  `tests/test_import_step.py`, and fixtures added to the existing
  `tests/step_project/` — authored in CadQuery and exported to STEP in a
  temporary build directory, as that package already does; **no binary
  fixture is committed.** The fixtures this change needs and the previous
  cycle does not: a nested sub-assembly, and a product placed both inside
  a sub-assembly and at the root (design fact 6).
- Changed: `solid_node/node/adapters/step.py` gains `StepAssembly` and
  the placement walk; `solid_node/cli.py` gains one `COMMANDS` row.
- Documentation: `docs/cli.rst` gains an `import-step` section;
  `docs/leaf-nodes.rst` cross-references it from the `StepNode` section;
  `docs/changelog.rst` "Unreleased" gains an entry naming both
  originating projects.
- Consumers: none change. A project that never runs `import-step` and
  never constructs a `StepAssembly` builds identically.
- Originating projects, in their own repositories, on their own schedule:
  `Internal-Cycloidal-Actuator` replaces its six hand-typed placements —
  and the `test_machine.py` contract that exists only to check the
  typing — with generated source, and can then model all 55; `openvmp`
  keeps its `.assy` reader, which reads a different format, but stops
  being the only place the walk exists. Neither is done in this cycle.
- The shop's `shop-skills/solid-node-api/SKILL.md` will need the command
  and the reader; that is a shop file and a separate change.
- Not in this change: any placement the generated source *animates* (the
  scaffold writes a machine at rest, and which joints move is the
  pilot's design decision, not the document's); the document's up axis
  and unit handling; re-running the scaffold to merge into edited source;
  and any import format other than STEP.
