## 1. Establish the red

- [ ] 1.1 Add `vitest.config.ts` applying the `define` that injects the API
      version, so the suite and the bundle read one source.
- [ ] 1.2 Write failing vitest cases for the pure option surface: `resolveOptions`
      defaults reproducing today's published behavior, and `resolveBaseUrl`
      deriving the mesh base from the source URL and preferring a host-supplied
      one.
- [ ] 1.3 Write failing vitest cases for the remaining pure decisions:
      `controlPlan(mode, animated)` naming which controls each presentation mode
      builds and whether they are inline-styled or class-named, `frameBounds`
      producing camera position, orbit target, and near/far from a `Box3`, and
      the declared API version equalling `package.json`'s `solidNodeViewerApi`.
- [ ] 1.4 Add failing Playwright cases to `tests/test_widget_e2e.py`, skipping
      when Playwright is absent as the module already skips on Pillow and
      chromium: mount through the bundle's global against the served export and
      assert that `dispose()` empties the container, `view()` round-trips into a
      remount, `reload()` preserves the camera, the canvas carries a
      host-supplied class and ARIA attributes, and the toggle presentation
      starts collapsed and expands on click. Leave the existing pixel tests
      untouched.
- [ ] 1.5 Confirm every new case fails for the intended reason, recording which
      Playwright cases ran rather than skipped, and that the existing export,
      Sphinx, and widget suites still pass.

## 2. Extract the reusable core

- [ ] 2.1 Create `src/viewer.ts` from the mounting body of `src/widget.ts`,
      exporting `mount()`, the option type, the handle type, and the view type,
      with no module-level document access. Keep the decisions in dependency-free
      modules the mount path calls rather than inlining them into DOM assembly:
      `src/options.ts` for `resolveOptions`, `resolveBaseUrl`, and `controlPlan`,
      `src/camera.ts` for `frameBounds`, and `src/version.ts` for the declared
      API version — none of them importing `OrbitControls`, so vitest reaches
      them in node.
- [ ] 2.2 Declare `solidNodeViewerApi` in `package.json` and read it in
      `build.mjs` through esbuild's `define`.
- [ ] 2.3 Reduce `src/widget.ts` to the auto-mount entry over the core,
      preserving `[data-solid-widget]` mounting, the `?t=` and `?autoplay=0`
      query parameters, and the error text written into a failed container; keep
      it as `build.mjs`'s entry point and re-export `mount` and the API version
      onto the global.

## 3. Implement the interface

- [ ] 3.1 Add `baseUrl`, defaulting to the source document's own directory, and
      resolve model references through it for both published documents.
- [ ] 3.2 Add the `animation` presentation modes: `inline` keeping today's
      inline-styled bar, `toggle` emitting `animation-controls` and a
      `timeline-toggle` reporting `aria-expanded`, `none`, and `external`
      creating no controls.
- [ ] 3.3 Add `view` restoration alongside bounds-derived clipping, and
      `className`, `role`, and `ariaLabel` on the canvas.
- [ ] 3.4 Return the handle: `dispose()` releasing the animation loop, resize
      observer, controls, renderer, geometries, and materials and emptying the
      container; `view()`; `reload()` rebuilding the tree and recomputing only
      clipping; `setTime()`; and `apiVersion`.
- [ ] 3.5 Run the vitest suite and the headless-chromium cases to green,
      recording whether the browser cases ran or skipped.

## 4. Prove the consumers are unaffected

- [ ] 4.1 Build the bundle from the bench and confirm `dist/solid-widget.js`
      still declares `SolidNodeWidget` and auto-mounts a published export.
- [ ] 4.2 Run `tests/test_export.py`, `tests/test_sphinx_ext.py`, and
      `tests/test_widget_e2e.py`, then the full framework suite.
- [ ] 4.3 Run the documentation build with `-W`, including its V8 example
      export embed.

## 5. Record the design

- [ ] 5.1 Extract an ADR for the viewer-core-and-entry split and the declared
      API version, link the change, and update its index.
- [ ] 5.2 Update `docs/architecture.md` where the widget is described as an
      export-only renderer, and amend ADR-020's renderer section to point at the
      shared package.
- [ ] 5.3 Update `docs/embedding.rst` only if a documented published name or
      parameter would otherwise be described inaccurately.

## 6. Complete the cycle

- [ ] 6.1 Synchronize the `viewer-package` and `export` specs into
      `openspec/specs/` through the supported OpenSpec workflow.
- [ ] 6.2 Archive the change and run OpenSpec validation.
- [ ] 6.3 Create the single implementation commit and verify the branch is
      exactly two commits ahead of `db59935`.
