# Tasks: v0.6 user-documentation overhaul

## 1. New tutorial pages and their model

- [ ] 1.1 Write the two-axis printer demo (two `Axis` instances, one
      machine-level instruction), export it with `solid export`, and commit
      the widget-less export under `docs/_exports/`
- [ ] 1.2 Write `docs/driving.rst`: driver declaration and attribute reads,
      `set_state` and qualified ids, ports and `connect()`, instructions,
      the layered viewer controls (authoritative description), embedding the
      committed export
- [ ] 1.3 Write `docs/scenarios.rst`: `Sim`, `dt` and integer ticks,
      `at`/`every`/`trigger`/`run`, trajectories and stats, `ScenarioTest`
      under pytest and `solid test`
- [ ] 1.4 Add both pages to the `docs/index.rst` toctree per design
      decision 1

## 2. Entry-surface rewrite

- [ ] 2.1 Rewrite the `docs/index.rst` introduction around the machine
      narrative
- [ ] 2.2 Rewrite `docs/why-solid-node.rst` (machine thesis, five backends,
      sheet/STL/flexible leaves, exactness, tests, Open Source)
- [ ] 2.3 Rewrite `docs/quickstart.rst`: tiered requirements (conditional
      OpenSCAD), artifact inventory (`.stl`/`.brep`/`.dxf`), a first driver
      as the payoff, upgrade/reinstall note
- [ ] 2.4 Update `README.rst` user-facing section: tagline, capability
      paragraph, `solid_node/simulation/` in the layout, reinstall note
- [ ] 2.5 Update `docs/status-and-roadmap.rst`: 0.6 as released, upgrade
      warning, roadmap rebuilt from the changelog's deliberate deferrals
- [ ] 2.6 Rewrite `docs/examples.rst` around both example projects: the V8
      engine (motion, cross-runtime parity, and now its flexible valve
      springs) and Metamaquina2 (a driven machine: X/Y/Z drivers, root
      instructions, flexible spring/belt/filament, legacy OpenSCAD sources
      wrapped), plus an index of the committed demo exports

## 3. Guide and tutorial corrections

- [ ] 3.1 `docs/animation.rst`: context-dependent `self.time`, placement
      from time *and* drivers, trim the driver section to a pointer to
      `driving.rst`; keep the keyframe section
- [ ] 3.2 `docs/assemblies.rst`: introduce drivers where they are declared,
      `connect()` at the assembly layer, control-scoping guidance, pointer
      to `assertAssemblySupported`
- [ ] 3.3 `docs/fusion.rst`: exact vs faceted fusion, "mesh" → "solid"
      sweep, mixed-backend exact fusion, `StlNode` faceted downgrade,
      flexible-child refusal
- [ ] 3.4 `docs/node-tree.rst`: qualified driver ids in "Node names",
      `.brep`/`.dxf` and integer-nanosecond exact-equality freshness,
      ports outside the cache key, the `StlNode` wrapper-module exception
- [ ] 3.5 `docs/leaf-nodes.rst`: delete "Installing molejo", molejo links to
      PyPI/readthedocs, `SheetLeafNode`/`FlexibleNode` base taxonomy, OCCT
      `fn` sentence, schema-v3 note, trim ports vocabulary to a reference
- [ ] 3.6 `docs/viewer.rst`: "Driving the model" section linking
      `driving.rst`, OpenSCAD-path caveat for driven machines
- [ ] 3.7 `docs/embedding.rst`: API version 5, schema versions 1/2/3 and
      emission rule, manifest key inventory, full mount-handle surface,
      `driverControls: 'none'`, the pinned-bundle warning, stated
      limitations (URL/`snapshot`/Sphinx pose only via `$t`)
- [ ] 3.8 `docs/cli.rst`: scenario note under `solid test`, driver tables
      under `solid export`, `$t`-only caveats on `--time`/`--fps`, add the
      port environment variables
- [ ] 3.9 `docs/api-reference.rst`: Ports and Simulation sections, the
      three missing leaf adapters, `set_state` in `:members:`, resolve the
      accumulate/reset contradiction, fix the `fn` family sentence

## 4. Example projects

- [ ] 4.1 Bump the `docs/examples/v8-engine` submodule to `ef0b046`
      (increment 9, flexible valve springs) and verify its export runs
      against this framework checkout
- [ ] 4.2 Add `docs/examples/metamaquina2` as a submodule of
      `github.com/LibreSolid/Metamaquina2` and verify its export runs with
      the OpenSCAD binary and molejo present
- [ ] 4.3 Extend `.readthedocs.yaml`: `pre_build` export for Metamaquina2,
      `build.apt_packages` for OpenSCAD, and molejo available to the export
      environment; time both exports locally and return to the pilot if the
      cost is unreasonable for the RTD job

## 5. Release record and build

- [ ] 5.1 Author the 0.6.0 entry in `docs/changelog.rst` from the release
      branch's `HISTORY.rst` text
- [ ] 5.2 Write `docs/releases/release-0.6.md` on the `release-0.5.md`
      template
- [ ] 5.3 Refresh `conf.py` `autodoc_mock_imports` for the 0.6 dependency
      set, preserving the bumpversion-managed `release` line

## 6. Verify the record

- [ ] 6.1 Run a full `sphinx-build` treating warnings as errors, on
      committed exports only, and fix what it reports
- [ ] 6.2 Review the built HTML against every scenario of the
      `user-documentation` spec and the four audit reports; validate the
      OpenSpec record
