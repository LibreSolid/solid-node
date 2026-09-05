## 1. Establish the red

- [ ] 1.1 Rewrite `tests/test_viewer_bundle.py` for the entry-point lookup: `installed()` is `None` without an entry, returns the entry's mapping with one, imports only the standard library, and the remedy names the extra; a viewer whose entry raises reports the viewer's own remedy.
- [ ] 1.2 Extend `tests/test_manager_develop.py`: default selects web when the lookup answers and OpenSCAD when it does not; `--web` without the viewer errors naming the extra; the web viewer is a `Popen` of `[sys.executable, '-m', 'solid_node_viewer', 'serve', '--build-dir', ...]` restarted per cycle; `--web-dev` adds `--start-frontend`; neither viewer available fails before any process starts; `--debug-web` is no longer accepted.
- [ ] 1.3 Reduce `tests/test_browser_renderer.py` to staging and delegation: staging unchanged, capture is a subprocess with `--imgsize`, `--time` and the resolved camera, a missing viewer names the extra, a non-zero capture surfaces the viewer's message, the stage is removed either way, OpenSCAD is never substituted. Drop the Playwright end-to-end cases, which now live in the viewer.
- [ ] 1.4 Update `tests/test_manager_viewer.py`, `tests/test_cli_lazy_imports.py`, `tests/test_export.py`, `tests/test_sphinx_ext.py` and `tests/test_snapshot.py` for the new remedy text, the four-field report, and the viewer-code import ban.
- [ ] 1.5 Delete `tests/test_widget_e2e.py`, `tests/test_web_viewer.py` and `tests/test_packaging.py` with the code they tested; update `tests/test_docs_exports.py` for the workflow and Read the Docs steps that install the viewer instead of building the widget.
- [ ] 1.6 Confirm every new case fails for the intended reason.

## 2. Remove the viewer

- [ ] 2.1 `git rm` `solid_node/viewers/widget/`, `solid_node/viewers/web/`, `solid_node/packaging.py`; move `widget/tools/generate_parity_fixture.py` to `tools/generate_parity_fixture.py` taking its output path on the command line.
- [ ] 2.2 `pyproject.toml`: drop the cmdclass hooks; add `viewer = ["solid-node-viewer"]`; point `web-snapshot` at `solid-node-viewer[snapshot]`. `MANIFEST.in` loses the frontend lines. `requirements.txt` unchanged (the viewer is optional).
- [ ] 2.3 `.github/workflows/python-app.yml` and `.readthedocs.yaml`: remove the npm jobs and steps; install `solid-node-viewer` from its Git repository where the docs build and the release build need the widget.

## 3. The process boundary

- [ ] 3.1 `solid_node/viewers/bundle.py`: `installed()` through `importlib.metadata.entry_points(group='solid_node.viewer')`; `has_bundle()`, `bundle_path()`, `index_path()`, `api_version()` over it; `missing_bundle_remedy()` names the extra; `viewer_command()` returns `[sys.executable, '-m', 'solid_node_viewer']`.
- [ ] 3.2 `solid_node/manager/develop.py`: default viewer from `has_bundle()`; `--web` requires it; web process via `subprocess.Popen` on `get_build_dir(path)`; `--web-dev` passes `--start-frontend`; remove `--debug-web`; fail early when neither viewer can open.
- [ ] 3.3 `solid_node/viewers/browser.py`: keep `stage()`; replace `write_mount_page`/`serve`/`capture`/`playwright`/`launch` with `capture()` that runs the viewer's `capture` on the staging directory with the resolved camera; `BrowserSnapshotError` for a missing viewer and for a failed capture.
- [ ] 3.4 `solid_node/manager/viewer.py`: print the lookup's four fields. `solid_node/core/export.py` and `solid_node/sphinx.py`: unchanged call sites, new remedy.

## 4. Records and documentation

- [ ] 4.1 Retire `openspec/specs/{viewer-package,viewer-assembly-navigation,web-viewer}` at archive; sync the modified capabilities.
- [ ] 4.2 ADR-067 "Optional viewer package behind a process boundary" under `docs/adrs/EXPORT/`; mark ADR-012, 013, 014, 027, 036, 037, 020, 035, 042 *Relocated to solid-node-viewer* in the index; update `docs/architecture.md` (viewer section, dependency map, component table).
- [ ] 4.3 User docs: `docs/viewer.rst`, `docs/embedding.rst`, `docs/cli.rst`, `docs/quickstart.rst`, `docs/index.rst`, `docs/status-and-roadmap.rst`, `README.rst`, `docs/contributor-briefing.md`, `HISTORY.rst` (Unreleased, breaking).
- [ ] 4.4 Green: full pytest suite, `-W` documentation build with the viewer installed, and `solid develop`/`solid snapshot --renderer web` exercised against solid-node-viewer 0.1.0 from the workspace.
