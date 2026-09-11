## 1. Establish the breaking CLI boundary red-first

- [ ] 1.1 Add develop-manager and CLI tests proving that the default and
  `--web` require the browser viewer even when OpenSCAD is installed, that no
  development process starts when it is absent, and that `--openscad` is no
  longer accepted; run them against the base and record the expected failures.
- [ ] 1.2 Add tests proving `--no-web`, callbacks, `--web-dev`, browser-process
  restart, and browser/viewerless `scad_output=False` behavior remain coherent;
  record any newly introduced failures before implementation.
- [ ] 1.3 Update the OpenSCAD dependency tests red-first so their complete
  requiring set excludes GUI viewing while retaining modelling, legacy
  evaluation, and the OpenSCAD snapshot renderer.

## 2. Remove the OpenSCAD GUI viewer

- [ ] 2.1 Simplify `solid_node.manager.develop` to its browser and `--no-web`
  modes, fail early with the installed-viewer remedy, remove `--openscad` and
  the GUI child process, and preserve the existing browser process contract.
- [ ] 2.2 Remove `OpenScadViewer`, `.openscad.pid`, GUI-only imports and PID
  tests while leaving `OpenScadRenderer` and the snapshot manager's use of it
  intact.
- [ ] 2.3 Reconcile focused CLI, develop, dependency, snapshot, build-lifecycle,
  and viewer-boundary tests until the red cases and retained behavior are
  green.

## 3. Explain the v0.7 transition

- [ ] 3.1 Update README/quickstart, CLI and viewer documentation, package-extra
  comments, and other current prose to require `solid-node[viewer]` for
  interactive development and distinguish the retained fixed-pose OpenSCAD
  snapshot renderer from a viewer.
- [ ] 3.2 Add the unreleased v0.7 changelog account: OpenSCAD was the first
  reliable viewer, the browser viewer became the faithful machine surface as
  simulation developed, the GUI/fallback became roadmap burden, and modelling,
  SolidPython/OpenSCAD nodes, SCAD output, and OpenSCAD snapshots remain.
- [ ] 3.3 After implementation and tests confirm the design, add one ADR
  amending ADR-046/068/102, update the ADR index, and rewrite the affected
  architecture synthesis rather than altering historical ADRs or old release
  notes.

## 4. Prove removal and retained compatibility

- [ ] 4.1 Run the focused framework suites for CLI/develop, OpenSCAD dependency,
  snapshots, build lifecycle, viewer distribution, and documentation; record
  commands, counts, skips, and failures in `evidence.md`.
- [ ] 4.2 Run an actual fixed-pose OpenSCAD PNG snapshot and representative
  OpenSCAD/Solid2 geometry production after the GUI class is gone; inspect the
  image and record the OpenSCAD version, command, artifact result, and limits.
- [ ] 4.3 Exercise an installed browser viewer through the default development
  selection and exercise an installation-without-viewer failure plus
  `--no-web`; record exact package/framework identities without claiming the
  viewer is published.
- [ ] 4.4 Build the documentation with warning-level failures enabled and
  search current source/spec/documentation for stale GUI/fallback claims,
  explicitly excluding immutable archives, superseded ADR text, and historical
  release notes.
- [ ] 4.5 Run the full framework suite and `openspec validate --all --strict`,
  then record the final results and any environmental skips honestly before
  synchronization, archival, and the implementation commit.
