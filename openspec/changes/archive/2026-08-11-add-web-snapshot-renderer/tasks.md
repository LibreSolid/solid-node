## 1. Resolve the widget build constraint

- [x] 1.1 Confirm with the pilot how the widget bundle is rebuilt for this
      cycle, given that `scripts/dev-env` symlinks
      `solid_node/viewers/widget/dist` into the primary checkout and the shop
      contract forbids building it inside a worktree
- [x] 1.2 Record the agreed approach before any TypeScript change

      The pilot authorized a dedicated npm environment for this worktree.
      Replace this worktree's ignored `node_modules` and `dist` symlinks with
      worktree-local directories, install from `package-lock.json`, and build
      only into the local `dist`. The primary checkout's dependencies and
      bundle remain untouched.

## 2. Camera conversion (no browser, no I/O)

- [x] 2.1 Red: unit tests for `solid_node/core/camera.py` covering the vector
      form (eye/target passthrough), the gimbal form with a single non-zero
      rotation, and the gimbal form with all three rotations non-zero
- [x] 2.2 Red: unit tests asserting the emitted field of view matches
      OpenSCAD's and that a malformed specification (wrong number count,
      non-numeric) raises a clear error
- [x] 2.3 Implement `solid_node/core/camera.py`: parse either OpenSCAD form and
      return eye, target, up, and field of view
- [x] 2.4 Green: all camera unit tests pass

## 3. Viewer widget options

- [x] 3.1 Red: vitest cases for `up` and `fov` in `options.ts` — supplied
      values resolve, absent values preserve today's Z-up and 50° defaults
- [x] 3.2 Red: vitest cases for `frameBounds`/`viewer.ts` honouring a supplied
      up direction and field of view without disturbing near/far derivation
- [x] 3.3 Red: update `version.test.ts` for `solidNodeViewerApi: 3`
- [x] 3.4 Implement `up` and `fov` through `options.ts`, `camera.ts`, and
      `viewer.ts`; bump `package.json` to API version 3
- [x] 3.5 Green: vitest suite passes; rebuild the bundle by the approach agreed
      in task 1

## 4. Renderer split and option validation

- [x] 4.1 Red: CLI tests that `--renderer` defaults to `openscad`, that each of
      `--projection`, `--colorscheme`, `--view`, `--render`, `--preview` with
      `--renderer web` exits non-zero naming the offending option, and that
      none of them is rejected when merely defaulted
- [x] 4.2 Change `--projection` and `--colorscheme` to `default=None` and apply
      the OpenSCAD defaults after parsing, leaving OpenSCAD behaviour identical
- [x] 4.3 Move OpenSCAD command construction and the xvfb wrapper from
      `manager/snapshot.py` to `solid_node/viewers/openscad.py`
- [x] 4.4 Reduce `manager/snapshot.py` to shared validation plus renderer
      dispatch
- [x] 4.5 Green: existing snapshot tests plus the new validation tests pass,
      with no behavioural change to the OpenSCAD path

## 5. Staging from the published build

- [x] 5.1 Red: a test that staging hardlinks (not copies) every artifact named
      by `viewer.json`, and that the staged files survive deletion of the
      originals
- [x] 5.2 Red: a test that the build lock is released before capture begins and
      is not held for the browser's lifetime
- [x] 5.3 Implement staging in `solid_node/viewers/browser.py`: acquire
      `project_build_lock()`, build stale artifacts, read `viewer.json`,
      hardlink meshes into a staging directory beside `_build`, release
- [x] 5.4 Implement cleanup of the staging directory in a `finally`, including
      on capture failure
- [x] 5.5 Green: staging tests pass

## 6. Serving and capture

- [x] 6.1 Red: a test of the served layout — manifest, meshes, widget bundle,
      and generated mount page all resolve over the loopback server
- [x] 6.2 Implement the ephemeral `127.0.0.1:0` static server and the generated
      mount page that mounts the widget with the requested time and camera
- [x] 6.3 Implement the Playwright capture: Chromium with SwiftShader flags,
      viewport from `--imgsize`, device scale factor 1, canvas screenshot with
      `omit_background=True`
- [x] 6.4 Green: capture produces a PNG

## 7. Dependency and failure modes

- [x] 7.1 Red: tests that a missing Playwright import, a missing Chromium
      binary, a missing widget bundle, and `uid 0` each exit non-zero with the
      specific remedy, and that none of them falls back to OpenSCAD
- [x] 7.2 Add the `web-snapshot` extra to `pyproject.toml` depending on
      `playwright`
- [x] 7.3 Implement the four guarded failures, reusing `WidgetBundleMissing`'s
      existing remedy text for the bundle case
- [x] 7.4 Green: failure-mode tests pass

## 8. End-to-end proof

- [x] 8.1 Red: mandatory end-to-end test asserting border pixels have alpha 0
      and model pixels alpha 255 on a real capture
- [x] 8.2 Red: mandatory differential test rendering one asymmetric model with
      the same `--camera` under both renderers and comparing silhouettes by
      intersection-over-union above a threshold, with at least one case having
      all three gimbal rotations non-zero
- [x] 8.3 Ensure the tests fail with an actionable message — naming Chromium
      installation — rather than an internal Playwright error when the browser
      is absent
- [x] 8.4 Green: both end-to-end tests pass, pinning the gimbal convention and
      the field of view

## 9. Documentation and completion

- [x] 9.1 Update `docs/cli.rst` for `--renderer` and its per-renderer option
      constraints
- [x] 9.2 Update the viewer/embedding documentation for the `up` and `fov`
      mount options and API version 3
- [x] 9.3 Document the `web-snapshot` extra and the separate browser download
      in the installation documentation
- [x] 9.4 Run the full framework suite
- [x] 9.5 Extract the ADR for the accepted architecture, update
      `docs/adrs/README.md` and `docs/architecture.md`, sync specs, and archive
      the change
