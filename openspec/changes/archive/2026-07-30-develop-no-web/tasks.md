## 1. Red: argument surface

- [x] 1.1 In `tests/test_cli.py`, add a failing test that
      `solid develop model.py --no-web --callback http://listener` parses and
      dispatches to `Develop.handle` without an argument error.
- [x] 1.2 In `tests/test_cli.py`, add failing tests that
      `solid develop model.py --no-web --web-dev`, `--no-web --web`, and
      `--no-web --debug-web` each exit with code 2 before dispatching.
- [x] 1.3 Run the new tests and observe them fail on the unknown `--no-web`
      argument.

## 2. Red: process selection

- [x] 2.1 Add `no_web=False` to `default_args()` in
      `tests/test_manager_develop.py`.
- [x] 2.2 Add a failing test that `handle(default_args(no_web=True))`
      constructs no `Process(target=develop.web)` and still constructs the
      builder Process, using the existing `KeyboardInterrupt`-on-join pattern
      to end the loop.
- [x] 2.3 Add a failing test that `handle(default_args(no_web=True,
      callback='http://listener'))` passes that callback through to the
      builder call.
- [x] 2.4 Run the new tests and observe them fail.

## 3. Implement

- [x] 3.1 Register `--no-web` in `Develop.add_arguments` with help text naming
      the external-viewer-host use.
- [x] 3.2 In `Develop.handle`, reject `--no-web` combined with `--web`,
      `--web-dev`, or `--debug-web` via `self.parser.error()`, before any
      process starts.
- [x] 3.3 Relax the `--callback` validation so it is accepted in no-web mode
      and still rejected with `--openscad` and `--web-dev`.
- [x] 3.4 Rewrite the viewer-mode condition so the `--openscad`-alone rule and
      the `--no-web` rule are explicit and side by side, per the design.
- [x] 3.5 Confirm the rebuild loop's web-restart block stays inert when no
      viewer process exists.

## 4. Green and regression

- [x] 4.1 Run `tests/test_cli.py`, `tests/test_manager_develop.py`, and
      `tests/test_builder_lifecycle.py` green.
- [x] 4.2 Run the full framework suite and report the result.
- [x] 4.3 Verify by hand from this worktree that `solid develop <node>
      --no-web` runs the watch loop and that nothing is listening on this
      worktree's `SOLID_NODE_PORT` (8002), then that a source edit triggers a
      rebuild.

## 5. Records

- [x] 5.1 Document `--no-web` in the develop section of `docs/cli.rst`.
- [x] 5.2 Assess whether this change warrants an ADR under `docs/adrs/`; it is
      an additive CLI flag with no new boundary, so record the assessment
      rather than assuming one is needed.
- [x] 5.3 Sync the `cli` and `one-shot-build-and-notification` baseline specs
      and archive the change.
