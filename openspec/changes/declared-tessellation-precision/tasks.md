## 1. The declaration (red first)

- [ ] 1.1 Red: `tests/test_tessellation_precision.py` — a `CadQueryNode`
      subclass declaring `angular_deflection = 0.5` over a curved solid
      builds an STL with strictly fewer triangles than an identical
      subclass declaring nothing; the undeclared node's artifact is
      byte-identical to the one written before the change (pin the
      triangle count of a fixed solid); a subclass declaring only
      `angular_deflection` keeps the 0.1 mm linear default, and one
      declaring only `linear_deflection` keeps the 0.1 rad angular
      default.
- [ ] 1.2 Red: a declared `linear_deflection` of `0`, `-1`, `float('inf')`,
      `float('nan')`, `True` or `'0.5'` raises on build naming the node and
      the attribute, and no `.stl` is written; the same for
      `angular_deflection`.
- [ ] 1.3 Red: an exact `FusionNode` declaring `angular_deflection = 0.5`
      over children declaring nothing writes a coarse fused artifact while
      each child's own artifact stays at the default; an undeclared fusion
      over a child declaring `0.5` writes a default-precision fused
      artifact.
- [ ] 1.4 Red: `.brep` and `shape()` are identical across a build with a
      coarse declaration and a build without one; only the `.stl` differs.
- [ ] 1.5 Implement: `linear_deflection = 0.1` / `angular_deflection = 0.1`
      as documented class attributes on `ExactLeafNode` and on
      `FusionNode`; `deflections(node)` in `solid_node/exact.py` reading
      and validating both (real, not `bool`, finite, strictly positive) and
      raising named errors; `write_stl(shape, path, mtime_ns,
      linear_deflection, angular_deflection, digest=None)` passing them to
      `exportStl`; both call sites (`exact_leaf.as_scad`,
      `fusion.generate_stl`) resolving through the helper. Update the
      direct `write_stl` call in `tests/test_exact_geometry.py`. Turn
      1.1–1.4 green.

## 2. Currency and identity

- [ ] 2.1 Red: a node built and current, whose declared
      `angular_deflection` is then edited in the module defining the class,
      reports not up to date and its `.stl` is rewritten at the new
      precision on the next build; a sibling node class in the same file
      that declares nothing is not rebuilt (the ADR-071 scope path).
- [ ] 2.2 Red: changing a declared deflection does not change the node's
      `uniq_id` or its artifact path — the same file is rewritten, and no
      second artifact appears in the build directory.
- [ ] 2.3 Red: the printed-piece id of a node changes when its declared
      precision changes, and `viewer.json`'s pieces table reflects it.
- [ ] 2.4 Confirm 2.1–2.3 pass with no framework change beyond section 1;
      if any needs one, implement it and record why here.

## 3. Downstream verdicts

- [ ] 3.1 Red: under `solid test --faceted`, a comparison of two nodes one
      of which declares a coarse `angular_deflection` reaches its verdict
      on the coarse mesh (a clearance that the fine mesh resolves and the
      coarse one does not, or the reverse, asserted explicitly). Confirm
      the `test-framework` spec needs no delta for it; if its wording turns
      out to need one, stop and update the change's specs before
      continuing.
- [ ] 3.2 Run the exact-geometry, sheet-part, build123d, fusion, printed-
      piece and source-set suites (`tests/test_exact_geometry.py`,
      `tests/test_build123d_adapter.py`, `tests/test_source_set.py`, the
      fusion and piece suites) to confirm the undeclared path is untouched.

## 4. Documentation and records

- [ ] 4.1 `docs/leaf-nodes.rst`: a "Tessellation precision" section under
      the exact adapters — the two attributes, their units, their
      defaults, the OCCT quantities they name, that they shape the STL and
      not `shape()` or the `.brep`, that changing one rebuilds the node and
      changes its printed-piece id, and the warning that a faceted test run
      judges on the declared mesh. Cross-reference it from the
      `Build123dSheetNode` and `CadQueryNode` sections.
- [ ] 4.2 `docs/fusion.rst`: a fusion declares precision for its own fused
      solid and does not inherit its children's.
- [ ] 4.3 `docs/api-reference.rst`: the two attributes on the exact leaf
      base and on `FusionNode`, if that page enumerates class attributes.
- [ ] 4.4 `docs/changelog.rst` "Unreleased": an entry in the style of the
      existing ones, naming `openvmp` and `Internal-Cycloidal-Actuator` as
      the originating projects, quoting the measured 19.9 MB → 1.8 MB, and
      stating the piece-id consequence.
- [ ] 4.5 ADR in `docs/adrs/NODE/` — tessellation precision is a node
      declaration, riding the source set rather than identity — depending
      on ADR-071, ADR-026/063 and ADR-044/045/047, indexed in
      `docs/adrs/README.md`; update `docs/architecture.md` where it
      describes the exact artifact path.

## 5. Close the cycle

- [ ] 5.1 Full framework suite green from the worktree with the workspace
      venv; record the result in this file.
- [ ] 5.2 `openspec validate declared-tessellation-precision --strict`,
      sync the baseline `exact-geometry` spec, archive the change, and
      commit the implementation record.
- [ ] 5.3 Report the two project follow-ups (drop `premesh()` in `openvmp`
      and in `Internal-Cycloidal-Actuator`) and the shop follow-up
      (`shop-skills/solid-node-api/SKILL.md` gains the declaration) to the
      pilot; neither is done in this cycle.
