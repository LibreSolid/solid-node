## 1. The fixtures the walk needs (no binary committed)

- [ ] 1.1 Extend `tests/step_project/` in the shape it already has — every
      fixture authored with `cadquery.Assembly` and saved to STEP into a
      temporary build directory, no binary committed. The fixtures this
      cycle needs and cycle B did not, each proved authorable in design
      fact 6: a two-level nest (a part placed inside a sub-assembly that
      is itself placed at a non-identity transform in the root); the same
      product placed both inside that sub-assembly and directly at the
      root; an occurrence whose component label the writer leaves unnamed
      (which `cadquery.Assembly` produces by itself — design fact 3, so
      this needs no special authoring, only an assertion); a placement
      that is a pure translation; a placement that is a 180° turn; and a
      product placed through a mirrored transform and one through a
      scaled transform, for the propriety gate.
- [ ] 1.2 A fixture whose product names carry the shapes design fact 10
      records — a leading digit, a space, an embedded `x`-dimension, a
      trailing digit meeting a leading digit — so the class-name and
      attribute-name rules are tested on the names that actually occur,
      plus two products whose names derive the same class name, for the
      collision suffix.

## 2. The occurrence walk (red first)

- [ ] 2.1 Red: `tests/test_step_assembly.py` — `StepAssembly(path)` reports
      one product entry per product with name, kind, occurrence count,
      solid count and colour; a product placed several times appears once
      with that count; the reader writes no artifact and adds no tracked
      source file; constructing it over a file a `StepNode` has already
      read performs no further read or transfer (count
      `STEPCAFControl_Reader` invocations, as cycle B's task 5.1 does).
- [ ] 2.2 Red: `occurrences` reports one entry per placement, walked
      through nested sub-assemblies; each entry carries the product name,
      the parent product or the root, the placement matrix in the parent's
      frame and the world matrix composed outward; the two-level fixture's
      inner part reports a placement translation of `(10, 0, 0)` and a
      world translation of `(10, 20, 0)` (design fact 6); a product placed
      at two depths gives two entries with different parents and one
      product entry with occurrence count two; an unnamed component still
      yields a distinguishable occurrence whose reported label name is
      empty; a file holding one part and no assembly yields one occurrence
      at the identity.
- [ ] 2.3 Red: an occurrence carrying no colour of its own reports none
      even when its product is coloured (design fact 9).
- [ ] 2.4 Implement: the `StepAssembly` section of
      `solid_node/node/adapters/step.py` (design D1) — the walk over every
      assembly label's components through `GetReferredShape_s`, occurrence
      identity as the chain of `_entry` labels from the root (design D3),
      `GetLocation_s(component).Transformation()` read into a 4x4,
      `world = parent_world @ local`, and solid counts taken from
      `GetShape_s` directly rather than through `_Document.shape()`
      (design D4, fact 8). Turn 2.1–2.3 green.

## 3. The decomposition (red first)

- [ ] 3.1 Red: for every occurrence of every fixture, composing
      `Rotation(angle, axis).matrix()` then `Translation(translation)
      .matrix()` the framework's way (later operation outermost —
      `solid_node/node/base.py`, `operations.py`) reproduces the
      occurrence's placement matrix to within 1e-9; a 180° turn
      (`diag(-1, 1, -1)`) round-trips; a pure translation reports a zero
      angle with a unit axis and the occurrence's own translation; reading
      the same document twice gives identical angles, axes and
      translations.
- [ ] 3.2 Red: the same round trip over all **55** occurrences of
      `projects/Internal-Cycloidal-Actuator/simulation/actuator/vendor/Internal
      Cycloidal Actuator.stp`, to within 1e-9 — the test skipped when that
      file is absent, since it is not in this repository. Assert the
      expected worst error is the 4.4e-16 order, not the 3.0e-8 the trace
      route gives (design fact 5), so a regression to the naive extraction
      fails here rather than in a project.
- [ ] 3.3 Red: a cross-check of the reader's decomposition against an
      independent Shepperd-method implementation in the test module, over
      every fixture occurrence, agreeing to 1e-12 as rotations (compare
      the matrices, not the literals — the two conventions may differ in
      sign).
- [ ] 3.4 Implement: decomposition through `gp_Trsf.GetRotation()` and
      `gp_Quaternion.GetVectorAndAngle(gp_Vec)` (design D2), unpacking the
      one-element tuple the OCP binding returns (design fact 11),
      substituting a stated unit axis when the angle is zero, keeping
      the angle signed in `[−180°, +180°]`, and flipping axis and angle
      together when the axis's largest-magnitude component is negative
      (the spec's determinism rule). Turn 3.1–3.3 green.

## 4. The propriety gate (red first)

- [ ] 4.1 Red: a mirrored placement is reported improper with its
      determinant and carries no angle/axis/translation; a scaled
      placement is reported improper with its scale factor and carries
      none; in both cases the document's other occurrences and all its
      products are still reported, and the reader raises nothing (design
      D5).
- [ ] 4.2 Red: none of the actuator document's 55 occurrences is reported
      improper (skipped when the file is absent) — design fact 4.
- [ ] 4.3 Implement: the gate on `|det(R) − 1| > 1e-9` or
      `|gp_Trsf.ScaleFactor() − 1| > 1e-9`, reported on the occurrence.
      Turn 4.1–4.2 green.

## 5. The generated source (red first)

- [ ] 5.1 Red: `tests/test_import_step.py` — the class-name rule on the
      fact-10 names: `10010 Stator` → `Part10010Stator`,
      `40x50x6mm_Bearing` → `Part40x50x6mmBearing`, `M4_12mm_Screw` →
      `M4_12mmScrew`, `ODrive_S1` → `ODriveS1`; two products deriving one
      class name get `_2` in document order; every generated class carries
      `part` set to the exact product name, including in a one-product
      document (design D7).
- [ ] 5.2 Red: `parts.py` holds one `StepNode` subclass per part and none
      for a sub-assembly or the root; each declares `step_source` as the
      STEP file's path relative to the written directory and declares no
      colour.
- [ ] 5.3 Red: `assembly.py` holds one `AssemblyNode` subclass per
      assembly product; each declares one child per occurrence with the
      attribute-name rule (snake case, `p_` prefix when it would not start
      with a letter, `_1`/`_2` suffixes only when that assembly places the
      product more than once); a product placed fourteen times gives
      fourteen declarations and no `.repeat()` (design D8); a
      sub-assembly is declared as a child of its parent's class and
      declares its own children in its own frame.
- [ ] 5.4 Red: each class's `render()` places every child by
      `rotate(angle, axis)` then `translate(vector)` from that
      occurrence's decomposition, omits an identity rotation and an
      identity translation, and precedes each placement with a comment
      naming the occurrence and the source document; the generated module
      declares no `Driver` and defines no `simulate()`.
- [ ] 5.5 Red: the generated modules import cleanly, the root class
      constructs, and every leaf's composed world matrix agrees with the
      reader's world matrix for its occurrence to within 0.01 mm at the
      product's bounding-box centre — on the fixtures, including the
      two-level nest.
- [ ] 5.6 Implement: `solid_node/manager/import_step.py`'s source
      generation (design D6): the name rules, the emitted `parts.py` and
      `assembly.py`, both composed as text rather than through
      `manager/templates/`. Turn 5.1–5.5 green.

## 6. The command (red first)

- [ ] 6.1 Red: `solid -h` lists `import-step` with its docstring; the
      command takes no node reference and loads no node (assert the
      project's modules are absent from `sys.modules` after a run, as the
      `models` command's tests do).
- [ ] 6.2 Red: `--into` defaults to the current directory, creates the
      directory when absent and writes an `__init__.py` when the directory
      holds none; `--model` defaults to a name derived from the root
      product, or from the file's stem when the root product is unnamed.
- [ ] 6.3 Red: a second run into a directory already holding `parts.py`
      writes neither file, names `parts.py`, and exits 1; the same for
      `assembly.py` alone (design D9 — both files or neither).
- [ ] 6.4 Red: a document with a mirrored or scaled placement writes
      nothing, names the occurrence with its determinant and scale factor,
      and exits 1.
- [ ] 6.5 Red: `pyproject.toml` is unchanged on disk and the manifest
      lines declaring the model are printed (design D10); a missing or
      untransferable `FILE` reports on stderr, writes nothing and exits 1;
      an installation without the kernel reports that `import-step` needs
      it, names the extra, exits 1 and writes nothing (patch the import to
      raise `ImportError`).
- [ ] 6.6 Implement: the `Import Step` command class with
      `needs_node = False`, its arguments, the three pre-write gates, and
      the `'import-step': ('solid_node.manager.import_step', ...)` row in
      `cli.COMMANDS`. Turn 6.1–6.5 green. Confirm the existing
      `tests/test_cli_lazy_imports.py` still passes, so the new row is
      walked and the command's module is not imported by the CLI.

## 7. The faithfulness proof on the real document

- [ ] 7.1 Scaffold the actuator document into a scratchpad directory —
      never inside the actuator's repository — with this worktree on
      `PYTHONPATH` and the workspace venv; add the printed manifest lines;
      run `solid build` from that directory. Record: whether it builds,
      how long, how many artifacts, and the STL total. Note that the
      document's parts at the framework's default tessellation are large
      (cycle B measured `Output_Shaft` alone at 19.9 MB); the generated
      classes declare `angular_deflection = 0.5` by the spec's rule, so
      record the resulting STL total against what the default would have
      cost.
- [ ] 7.2 Compare, for each of the 55 occurrences, the built model's leaf
      world placement against the `StepAssembly` world matrix at the
      product's bounding-box centre, within 0.01 mm — the contract
      `Internal-Cycloidal-Actuator`'s `test_machine.py` wrote by hand,
      now a framework test on generated source (design D11). Record the
      worst deviation.
- [ ] 7.3 Record the measured costs for the docs and the ADR: the cached
      read, and the structure extraction after it (design fact 7 measured
      0.02 s for 21 products and 55 occurrences; confirm on the final
      implementation).

## 8. Documentation and records

- [ ] 8.1 `docs/cli.rst`: an `import-step` section — the grammar, the two
      flags, what the two generated files contain, that it never
      overwrites, that it prints rather than edits the manifest, and that
      the generated model is a machine at rest whose motion the pilot
      writes in `simulate()`.
- [ ] 8.2 `docs/leaf-nodes.rst`: cross-reference `import-step` from the
      `StepNode` section, so a reader who has just learned to declare one
      leaf by hand learns that a document's worth can be scaffolded.
- [ ] 8.3 `docs/changelog.rst` "Unreleased": an entry in the style of the
      existing ones, naming `Internal-Cycloidal-Actuator` and `openvmp` as
      the originating projects and quoting the 7.1–7.2 measurements.
- [ ] 8.4 ADR in `docs/adrs/NODE/` — reading a STEP document's placements
      and scaffolding declarative source from them: the reader that is not
      a node, the quaternion decomposition and why the trace route is not
      accurate enough (design fact 5), the propriety gate, one declaration
      per occurrence rather than `.repeat()`, and the never-overwrite
      rule. It extends the cycle-B StepNode ADR and depends on ADR-076.
      Index it in `docs/adrs/README.md` and update `docs/architecture.md`
      where it describes the CLI commands and the leaf adapters.

## 9. Close the cycle

- [ ] 9.1 Full framework suite green from this worktree with the workspace
      venv: `PYTHONPATH=$PWD .venv/bin/python -m pytest tests -q`. Record
      the counts and the time, and account for every warning.
- [ ] 9.2 `openspec validate step-assembly-import --strict`, sync the
      baseline `step-assembly` and `cli` specs, archive the change, and
      commit the implementation record.
- [ ] 9.3 Report the follow-ups to the pilot: the shop's
      `shop-skills/solid-node-api/SKILL.md` gains the command and the
      reader (a shop change); `Internal-Cycloidal-Actuator` can replace
      its six hand-typed placements and its recomposition contract with
      generated source, in its own repository; and the two open questions
      in `design.md` (an inventory-only mode, and whether a regular
      placement pattern should ever be scaffolded as a repeat). None is
      done in this cycle.
