# Implementation evidence

## Identity and red boundary

- Framework base: `748d6d9450169336d09065b1134c7febb743b4ab` (`main`).
- Ratified planning commit:
  `92838738e51bd6e6bf8803f6492027931af3f41f`.
- Worktree:
  `/home/asa/devel/libresolid-studio/solid-node/WTs/remove-openscad-viewer`.
- Red command:

  ```text
  /home/asa/devel/libresolid-studio/.venv/bin/pytest -q \
    tests/test_manager_develop.py tests/test_cli.py \
    tests/test_openscad_dependency.py tests/test_pid_robustness.py
  ```

  Against the planning commit plus tests: **3 failed, 45 passed, 10
  subtests passed**. The three failures showed precisely that the default
  still fell back, `--openscad` still parsed, and `OpenScadViewer` still
  existed. Retained callback, `--no-web`, `--web-dev`, restart, modelling and
  snapshot cases stayed green.

## Focused framework proof

The focused CLI/develop, dependency, snapshot, build-lifecycle, viewer
distribution and documentation command covered these files:

```text
tests/test_cli.py tests/test_cli_lazy_imports.py tests/test_declarative_cli.py
tests/test_manager_develop.py tests/test_manager_viewer.py
tests/test_openscad_dependency.py tests/test_snapshot.py
tests/test_browser_renderer.py tests/test_builder_lifecycle.py
tests/test_builder_reload_resilience.py tests/test_retained_builder_generation.py
tests/test_backend_neutral_materialization.py tests/test_viewer_bundle.py
tests/test_docs_exports.py
```

Result: **243 passed, 1 skipped, 13 warnings, 74 subtests passed** in 45.18s.
The skip is the opt-in browser snapshot end-to-end case; the viewer process
itself is exercised below.

## Retained real OpenSCAD paths

- Environment: OpenSCAD 2021.01, `/usr/bin/xvfb-run`, no `DISPLAY` required.
- `solid snapshot tests/flat_project/simple_cylinder.py --renderer openscad
  --imgsize 640x480 --viewall` exited 0 and wrote a 2,896-byte, 640x480 RGB
  PNG. Visual inspection found the expected centered yellow cylinder on the
  Cornfield background with no clipping or corruption.
- A normal build of the same `Solid2Node` exited 0 and produced a 25-byte SCAD
  presentation plus an 884-byte STL through OpenSCAD.
- A temporary raw `OpenScadNode` wrapping a cube-with-bore module exited 0 and
  produced a 158-byte SCAD presentation plus a 7,284-byte STL through
  OpenSCAD. The first invocation exposed that the temporary fixture lacked
  the project manifest required by the loader (exit 66); after
  adding `[tool.solid-node]`, the representative build passed. No fixture or
  generated artefact is committed.

## Development modes

- Installed viewer: `solid-node-viewer` 0.1.0, AGPL-3.0-only, editable from
  `/home/asa/devel/libresolid-studio/solid-node-viewer`. This is the founded
  local package, not evidence of publication. `solid viewer` reported API 7.
- Default `solid develop` started that package's server on port 18108, built
  the raw OpenSCAD model with `scad_output=False` at the develop boundary,
  and returned HTTP 200 (`text/html`) from `/`. Ctrl-C shut the viewer down
  and the command exited 0. The spawned builder printed its existing
  `KeyboardInterrupt` traceback while stopping.
- For a no-viewer installation, a hard-linked copy of the workspace virtual
  environment had only the viewer's editable `.pth`, finder and distribution
  metadata removed. Default `solid develop` exited 1 before a build with the
  exact `pip install "solid-node[viewer]"` remedy.
- The same no-viewer environment ran `solid develop --no-web`, built the raw
  OpenSCAD model, and left port 18109 closed (`curl` exit 7). Ctrl-C exited 0,
  with the same retained builder traceback noted above.

## Documentation and stale-claim audit

```text
sphinx-build -W --keep-going -b html docs <temporary-output>
```

The warning-strict build read and rendered all 23 pages, then exited 1 with
six existing problems: one `Orbit` docstring warning, three
`docs/api-reference.rst` title/markup diagnostics, and absent generated
exports for the Metamaquina2 and V8 examples. Running the identical command
at untouched base `748d6d9` produced the identical six diagnostics. No warning
names a file or line changed by this cycle. The missing example exports are an
unavailable worktree fixture, not a generated artefact to commit.

Current source and documentation were searched for `OpenScadViewer`,
`run_openscad_viewer`, `.openscad.pid`, `args.openscad`, `--openscad`, GUI and
fallback claims. The removed code names are absent. Remaining prose matches
one of: the v0.7 migration/removal explanation, the retained snapshot
renderer, the ratified memorandum, or an explicitly preserved historical
ADR/release record. The final audit is repeated after baseline-spec sync.

After sync, the same audit found no removed implementation name in source and
no stale current claim. The only baseline-spec occurrences of `--openscad`
are the normative unknown-option scenario and the v0.7 migration scenario;
historical ADRs and release records remain preserved as such.

The optional `flake8` and `black` entry points are not installed in the
workspace virtual environment, so those non-required style commands could not
run. `git diff --check` passes.

## Full suite and OpenSpec

- The first full run found one stale, directly related test which patched the
  removed OpenSCAD check in the develop subprocess-isolation scenario:
  **1 failed, 2,269 passed, 4 skipped, 50 warnings, 892 subtests passed**.
  Updating it to exercise the retained `--no-web` builder subprocess made its
  focused rerun pass.
- Final pre-sync full suite: **2,270 passed, 4 skipped, 50 warnings, 893
  subtests passed** in 271.04s. Skips are environmental/opt-in cases already
  present in the suite; warnings are existing dependency, compatibility and
  multiprocessing warnings.
- `openspec validate --all --strict`: **33 passed, 0 failed**.

## Completion

The five deltas were merged into the baseline specs and verified, and the
completed change was archived at
`openspec/changes/archive/2026-09-11-remove-openscad-viewer/`. Post-archive
focused verification passed with **246 passed, 1 skipped, 13 warnings, 76
subtests passed** in 47.43s. Post-archive
`openspec validate --all --strict` passed all **32** active baseline specs.
