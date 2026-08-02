## 1. Red first: the development page cannot show a colour

- [ ] 1.1 Add a browser test that builds the `spinner_project` fixture, serves
      it through `WebViewer` in static mode, opens the page in headless
      chromium and asserts the model renders in its declared colour — skipping
      on the same conditions `tests/test_widget_e2e.py` already uses (bundle,
      chromium, Pillow). Confirm it fails against today's renderer.
- [ ] 1.2 Add failing tests for the new routes: `GET /build/viewer.json`
      returns the published snapshot, a model path named inside it resolves
      under `/build/`, and `GET /_viewer` reports availability and API version.

## 2. Serve the snapshot and the bundle

- [ ] 2.1 Stop loading the project model in `WebViewer.__init__`; remove the
      `/node` mount and the `load_node` call, keeping the reload socket and
      `/_build_error` as they are.
- [ ] 2.2 Serve the build directory under `/build/`, resolved per request and
      tolerant of a directory that does not exist yet; report an absent
      snapshot rather than failing to start.
- [ ] 2.3 Add `GET /_viewer` returning `{available, apiVersion, remedy}` and
      `GET /_viewer/bundle.js` serving `solid_node.viewers.bundle.bundle_path()`,
      with the remedy reported when no bundle is installed.
- [ ] 2.4 Register both before the `--web-dev` proxy routes and before the
      static frontend mount, and confirm they are reachable in both modes.
- [ ] 2.5 Add a test that serving a snapshot never imports project source
      (a fixture whose module raises on import).

## 3. Retire the per-node API

- [ ] 3.1 Delete `NodeAPI`, `NodeAPI.from_build` and `SnapshotNodeAPI` from
      `solid_node/viewers/web/viewer.py`.
- [ ] 3.2 Rewrite `tests/test_web_viewer.py` around the snapshot, bundle and
      absence cases; remove the tests that only covered the deleted API.
- [ ] 3.3 Confirm no other framework code or test constructs the deleted
      classes, and that `solid develop --no-web --callback` is untouched.

## 4. Rebuild the development app on the shared package

- [ ] 4.1 Add a shell module that fetches `/_viewer`, injects
      `/_viewer/bundle.js`, mounts `SolidNodeWidget.mount('#…',
      '/build/viewer.json', { animation: 'inline', autoplay: true })`, and
      exposes reload and dispose. Cover it with jest against a stubbed global.
- [ ] 4.2 Reduce `App.tsx` to that shell plus the error pane, and set the tab
      title from the snapshot root's name.
- [ ] 4.3 Point the reloader's reload callback at the mount handle's `reload()`
      and retarget `reloader.test.ts` / `reload.test.ts` at the shell, keeping
      the socket-lifecycle, offline-banner and build-error coverage.
- [ ] 4.4 Show the reported remedy in the error pane when the bundle is
      unavailable, with a jest test for that path.
- [ ] 4.5 Delete `node.ts`, `evaluator.ts`, `animator.ts`, `operations.d.ts`,
      `viewer/STLViewer.tsx`, `viewer/ControlCube.tsx`, `viewer/viewer.d.ts`,
      `NavigationTree.tsx` and the jest tests that encode the flat-scene
      architecture (`node.test.ts`, `composeOperations.test.ts`,
      `evaluator.test.ts`).
- [ ] 4.6 Remove the CSS rules that belonged to the deleted panes, keeping the
      offline banner and error styles.

## 5. Evidence

- [ ] 5.1 Run the framework suite; the browser test from 1.1 now passes with
      colours, lights and a fitted camera.
- [ ] 5.2 Run the app's jest suite and its production build; run the widget
      package's `npm test`, `npm run typecheck` and `npm run build`
      unchanged.
- [ ] 5.3 Open `solid develop` on a real project from this bench, confirm the
      model renders in colour, animation controls appear for an animated
      model, a rebuild refreshes while preserving the camera, stopping
      `solid develop` shows the offline banner, and a syntax error shows the
      build-error pane.
- [ ] 5.4 Confirm `--web-dev` still serves the page through the npm dev server
      with the snapshot and bundle routes coming from the backend.

## 6. Dependencies, records and documentation

- [ ] 6.1 Remove `three`, `@types/three`, `jokenizer`, `re-resizable`,
      `react-ace`, `ace-builds` and `react-router-dom` from
      `solid_node/viewers/web/app/package.json`, regenerating
      `package-lock.json` in the primary framework checkout — never inside this
      worktree — then rerun 5.2.
- [ ] 6.2 Update `docs/architecture.md`'s web-viewer synthesis to describe a
      snapshot-served shell around the shared viewer.
- [ ] 6.3 Extract the ADRs the implementation confirms (supersede ADR-014,
      supersede or narrow ADR-027, amend ADR-013) and update the ADR index.
- [ ] 6.4 Synchronize the `web-viewer` and `build-viewer-artifacts` specs,
      archive the change, and run `openspec validate --all --strict`.
