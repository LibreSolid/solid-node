## 1. Red: the bundle is absent from distributions and unreportable

- [ ] 1.1 Add `tests/test_packaging.py` driving the `sdist` and `build_py`
      hooks with the frontend build replaced by a recorder: assert the sdist
      hook builds both the development app and the widget, and that the wheel
      hook builds a frontend only when its output is missing. Red today: the
      widget is never built.
- [ ] 1.2 Extend that test to assert the widget's built bundle is selected by
      the distribution's file rules when present in the tree.
- [ ] 1.3 Add `tests/test_manager_viewer.py` asserting `solid viewer` reports
      the bundle path and API version as JSON and exits 0, and exits 1 with a
      remedy on stderr and empty stdout when the bundle is absent. Red today:
      no such command.
- [ ] 1.4 Add a test asserting `solid -h` lists `viewer` and that invoking it
      requires no node path.

## 2. The accessor

- [ ] 2.1 Add `solid_node/viewers/bundle.py` with standard-library imports
      only: bundle path, index path, presence, declared API version read from
      the widget's `package.json`, and the shared missing-bundle remedy.
- [ ] 2.2 Add its unit tests, including that the reported API version equals
      `solidNodeViewerApi` and that importing the module pulls in no CAD
      runtime.
- [ ] 2.3 Point `solid_node/core/export.py` at the accessor, keeping
      `WidgetBundleMissing` and its message behavior.
- [ ] 2.4 Point `solid_node/sphinx.py` at the accessor and confirm the
      documentation extension still imports without the CAD stack.

## 3. The command

- [ ] 3.1 Add `solid_node/manager/viewer.py` with `needs_node = False`,
      printing one JSON object and exiting 1 with the remedy when absent.
- [ ] 3.2 Register it in `solid_node/cli.py`.

## 4. Packaging

- [ ] 4.1 Teach `solid_node/packaging.py` a second frontend directory: build
      the widget during sdist, and during wheel build when its bundle is
      missing.
- [ ] 4.2 Update `MANIFEST.in` so the built bundle is included and its comment
      states that packaging builds it.

## 5. Evidence and completion

- [ ] 5.1 Run the framework suite; run the widget's `npm test`, `typecheck` and
      `build` if any package file changed.
- [ ] 5.2 Run a documentation build with `-W` and the export and Sphinx tests.
- [ ] 5.4 Extract an ADR if the accessor or the CLI report proves to be a
      consequential architectural decision; update `docs/architecture.md` if
      its synthesis changed.
- [ ] 5.5 Synchronize specs, archive the change, and create the completion
      commit.

## Post-integration sprint evidence

- After F3 is integrated into framework `sprint-002`, build a distribution
  from that exact integrated content commit in a disposable checkout outside
  every worktree and assert that it contains the viewer bundle. Record the
  result in the sprint evidence; it is not a cycle-completion task because it
  depends on the integration that follows archive.
