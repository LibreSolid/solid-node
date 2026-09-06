## 1. The fixture project (no binary committed)

- [ ] 1.1 `tests/step_project/`, in the shape of `tests/stl_project/`: a
      module that authors every fixture with `cadquery.Assembly` (names and
      colours set) and saves it to STEP into a temporary build directory,
      plus the wrapper modules declaring the `StepNode` subclasses. The
      fixtures the rest of this list needs, each proved authorable in
      design facts 5–8: a two-product assembly (a named, coloured part and
      an uncoloured one); a single-product file written with
      `cq.exporters.export`; a file placing one product at two occurrences
      far apart; a file with a sub-assembly; a file with two distinct
      products of one name (two assembly levels, since
      `cadquery.Assembly` refuses duplicate sibling names); a file with a
      face-only product (a `cq.Shell`); and a file in which an assembly
      root wraps exactly one part — the shape an exporter most often
      produces, and the case the candidate rule (design D3) must select by
      omission.
- [ ] 1.2 A wrapper module for the declaration tests that imports a
      sibling constant module, so the source-closure scenario has something
      to edit (as `stl_project/dimensions.py` serves the STL tests).

## 2. Declaration, freshness and selection (red first)

- [ ] 2.1 Red: `tests/test_step_node.py` — `step_source` resolves relative
      to the wrapper module's directory and an absolute path resolves to
      itself; the artifacts mirror that source location; a subclass
      declaring no `step_source` fails at construction naming the class.
- [ ] 2.2 Red: editing the STEP file makes the artifacts stale; editing the
      wrapper module does too; a module the wrapper imports is tracked; a
      current artifact is not rewritten and the document is not read for
      it.
- [ ] 2.3 Red: a file holding one part alone needs no `part`; a file whose
      assembly root wraps exactly one part needs none either and selects
      the part, not the root; a file with several candidates and `part`
      unset fails with the inventory rather than selecting its root, while
      naming that root explicitly still selects it; a `part` naming no
      product of the file fails with the inventory; the inventory carries
      one line per product with name, kind, occurrence count, solid count,
      bounding box and volume, and reports an unnamed product as unnamed;
      two products of one name fail naming the ambiguity and describing
      both; a product placed at several occurrences is one inventory line
      with that occurrence count.
- [ ] 2.4 Implement: `solid_node/node/adapters/step.py` — the reader, the
      product index over `ShapeTool.GetShapes()` with occurrence counts
      from every assembly's components, the candidate rule (every product
      except a root that is itself an assembly; a root that is a single
      part is its own candidate), the inventory (bounding boxes
      through `BRepBndLib.Add_s(..., useTriangulation=False)`, design D3),
      selection, and the `StepNode` class deriving `ExactLeafNode` with
      `namespace = 'cadquery.cq'` (design D2) and `__init__` resolving the
      path and adding `source_closure(wrapper)` to `self.files` (design
      D8). Add `'StepNode': 'adapters.step'` to `_EXPORTS` in
      `solid_node/node/__init__.py`. Turn 2.1–2.3 green.

## 3. Frame, correction and admission (red first)

- [ ] 3.1 Red: a product placed at two occurrences far apart yields one
      unplaced artifact carrying neither occurrence's translation; a
      selected sub-assembly holds its components at their internal
      placements and not its parent's placement.
- [ ] 3.2 Red: an `adjust` hook's correction reaches the artifact, the
      `.brep` and `shape()`; a subclass without the hook gets the product
      verbatim; the adapter offers no scale, unit, recenter or sew
      constructor parameter.
- [ ] 3.3 Red: a face-only product fails admission naming the node, the
      file, the part and the shells and faces it does hold, and writes no
      artifact; the same product sewn in an `adjust` hook by
      `solids_from_faces` is admitted and builds; an `adjust` that returns
      geometry with no solid still fails.
- [ ] 3.4 Implement: `GetShape_s` on the product label (design D4), the
      `adjust` hook around it, the admission gate after it, and
      `solids_from_faces(shape, tolerance)` with a docstring stating what
      it does and what it does not guarantee (design D5). Turn 3.1–3.3
      green.

## 4. Colour (red first)

- [ ] 4.1 Red: a product written at a given colour reads back as that
      colour — `#RRGGBB`, matching the value the fixture was authored with,
      which fails against a raw hex-encoding of the linear components
      XCAF returns (design D7, fact 5); an uncoloured product gives the
      node no colour; a declared `color` wins; a subclass that declares
      `color` never opens the document (patch the reader to raise).
- [ ] 4.2 Red: a subclass declaring nothing still gets the document's
      colour after ordinary construction as a child of an assembly — the
      framework's own node initialisation, or a `self.color = None` in a
      subclass `__init__`, must not be recorded as a declaration (design
      D7).
- [ ] 4.3 Red: a node whose artifacts are all current and which declares
      its own `color` builds without the document being read at all.
- [ ] 4.4 Implement: colour as a lazily resolved property whose setter
      records only a non-`None` assignment as a declaration, so an
      assignment of `None` leaves the document as the source (design D7),
      reading the product label's surface colour, else the colour every
      occurrence agrees on, else none, converted with
      `Quantity_Color.Convert_LinearRGB_To_sRGB_s` before rounding to
      bytes. Turn 4.1–4.3 green.

## 5. One read per file per process (red first)

- [ ] 5.1 Red: several nodes over one file cause exactly one reader
      invocation in the process (count `STEPCAFControl_Reader` calls);
      replacing the file evicts the entry and causes exactly one more; two
      different files are two entries.
- [ ] 5.2 Implement: the module-level cache keyed on `(path, mtime_ns)`
      with `exact._shape_cache`'s eviction shape (design D6). Turn 5.1
      green.

## 6. Exactness and the deferred import (red first)

- [ ] 6.1 Red: `exact` is true on a `StepNode` and `shape()` returns the
      selected, adjusted geometry in the node's own frame; a `FusionNode`
      over a `StepNode` and an overlapping `CadQueryNode` is exact and
      fuses to one solid; the `.brep` is written and reloaded; a project of
      `StepNode` leaves builds with no `openscad` on the PATH.
- [ ] 6.2 Red: a `StepNode` declaring `angular_deflection = 0.5` writes
      strictly fewer triangles than the same node declaring nothing, and
      its `.brep` is unchanged between the two (the ADR-076 path, inherited
      and not redeclared — design D9).
- [ ] 6.3 Red: `import solid_node.node` in a fresh interpreter leaves
      `OCP` out of `sys.modules`, and accessing `StepNode` imports the STEP
      reader (design D10).
- [ ] 6.4 Confirm 6.1–6.3 pass on the section 2–5 implementation alone; if
      any needs a framework change, implement it and record why here.

## 7. Documentation and records

- [ ] 7.1 Measure the leaf on its own originating part, and quote nothing
      that was not measured. The published figures for `Output_Shaft`
      (19.9 MB at the default, 1.8 MB at 0.5 rad) are not what a project
      gets: the actuator's design record now records that a stored
      triangulation reaches only **3.35 MB** through the framework's
      export, and no figure at all exists for this leaf, which meshes once
      at the declared value. So, in a scratchpad project run against this
      worktree (never inside the actuator's repository), wrap
      `Output_Shaft` from the real document —
      `projects/Internal-Cycloidal-Actuator/simulation/actuator/vendor/Internal Cycloidal Actuator.stp`,
      already extracted — in a `StepNode` twice: once declaring nothing and
      once declaring `angular_deflection = 0.5`. Record both artifact sizes
      and triangle counts, and the read time, and use those numbers as the
      leaf's caller evidence in 7.2, 7.3 and 7.4. If they contradict D9,
      stop and return the decision to the pilot rather than restating it.
- [ ] 7.2 `docs/leaf-nodes.rst`: a `StepNode` section beside `StlNode`'s —
      the declaration, selection by product name (and the candidate rule
      that lets a one-part file omit it) with the inventory failure,
      the product's own frame, the `adjust` hook and `solids_from_faces`,
      the solid-admission gate, colour from the document, one read per
      file, and that it is exact where `StlNode` is faceted. Add it to the
      adapter list at the top of the page, and cross-reference the
      "Tessellation precision" section with the two figures measured in
      7.1 and the one-line `angular_deflection = 0.5` a vendor-STEP
      project will want.
- [ ] 7.3 `docs/changelog.rst` "Unreleased": an entry in the style of the
      existing ones, naming `Internal-Cycloidal-Actuator` and `openvmp` as
      the originating projects, quoting the 7.1 measurement, and stating
      that the leaf is exact.
- [ ] 7.4 ADR in `docs/adrs/NODE/` — the STEP part as an exact
      external-file leaf: selection by product name with the inventory as
      the failure, the product's own frame, one document read per file per
      process — extending ADR-054 and ADR-055 and depending on ADR-047,
      ADR-050, ADR-071 and ADR-076, and carrying the 7.1 measurement as
      the originating caller's evidence. Index it in `docs/adrs/README.md`
      and update `docs/architecture.md` where it describes the leaf
      adapters.

## 8. Close the cycle

- [ ] 8.1 Full framework suite green from this worktree with the workspace
      venv; record the result here.
- [ ] 8.2 `openspec validate step-part-leaf --strict`, sync the baseline
      `step-import`, `node-model`, `exact-geometry` and `cli-startup-cost`
      specs, archive the change, and commit the implementation record.
- [ ] 8.3 Report the follow-ups to the pilot: the shop's
      `shop-skills/solid-node-api/SKILL.md` gains the leaf (a shop change),
      and the two originating projects delete their hand-written readers in
      their own repositories. None is done in this cycle.
