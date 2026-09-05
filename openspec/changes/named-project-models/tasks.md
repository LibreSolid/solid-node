## 1. Red tests on a two-model project

- [ ] 1.1 Add a scratch-project fixture, on the pattern of
      `tests/test_loader_references.py`, whose manifest declares two models
      by name with a default, a top-level `design/` package holding a node
      module per model, and a shared sibling module both import.
- [ ] 1.2 Red (loader): `discover_project` reports both names, their
      references and the default; a declared name resolves to its class;
      a bare word that is not a name still reads as a qualifier; `model`
      naming a non-key, an empty table, a malformed name and a name equal
      to a root directory each fail naming the manifest and the rule.
- [ ] 1.3 Red (loader): the selection step returns `<build root>/<name>`
      for a declared name and for the default, the root for a sub-node
      reference, and refuses no-reference in a project with the table and no
      `model`, listing the names.
- [ ] 1.4 Red (build): building each model publishes `viewer.json` under its
      own directory; building the second leaves the first's STLs and
      document untouched; the two hold distinct locks; a sub-node build into
      the root sweeps nothing beneath the model directories and spares
      `.lock` files.
- [ ] 1.5 Red (cli): `solid build <name>` and `solid build` (default) run the
      builder on the model's reference and directory; `solid build --all`
      walks both in order, continues past a failing model, reports each and
      exits nonzero; `--all` with a reference is an argument error; `--all`
      in a single-model project is refused.
- [ ] 1.6 Red (test): `solid test --all` runs both models' companion tests as
      one reported run, each built in its own directory.
- [ ] 1.7 Red (models): `solid models` and `--json` list both models in order
      with `unbuilt`, `published` and `failed` judged from the directories,
      and a single-model project lists one entry with `name` null; the
      command imports no project module.
- [ ] 1.8 Guard: the existing single-model fixtures build into the flat root
      at unchanged paths; `test_loader_references`, `test_build_publication`,
      `test_build_lock` and `test_cli` stay green unchanged.

## 2. Manifest and loader

- [ ] 2.1 `discover_project` parses the `models` table: name pattern, non-empty,
      reference values, `model` as a key, no name equal to a root directory;
      returns the root, the models in order and the default alongside the
      existing `(root, model_reference)` contract for single-model projects.
- [ ] 2.2 A selection step in the loader maps a reference or none to the
      concrete reference and its build directory; `resolve_node` looks a bare
      word up as a name before reading it as a qualifier.

## 3. Build directories

- [ ] 3.1 `Builder` takes the selection's directory; `build_once` carries it
      to the fresh interpreter.
- [ ] 3.2 The build-root sweep prunes immediate children that are declared
      model names and spares `.lock` by extension.
- [ ] 3.3 `develop` serves the selection's directory; `test`, `snapshot` and
      `export` anchor it before loading the node.

## 4. Commands

- [ ] 4.1 `solid_node/manager/models.py`: the `models` command, text and
      `--json`, registered in `cli.COMMANDS` with `needs_node = False`.
- [ ] 4.2 `solid build --all`: walk, per-model report, exit status.
- [ ] 4.3 `solid test --all`: every declared model as one run.

## 5. Verification

- [ ] 5.1 Turn every red and guard test from group 1 green.
- [ ] 5.2 Full framework suite.
- [ ] 5.3 On the originating project (`projects/3DPrintedClocks`, on a scratch
      branch, not committed by this cycle): declare `wall_clock_01` and a
      second model, run `solid models`, `solid build --all`, `solid build
      wall_clock_01`, `solid test wall_clock_01` and `solid develop
      wall_clock_01`; confirm the two directories, the untouched first
      publication after the second build, and the viewer serving the
      selected model.
- [ ] 5.4 On a single-model project (v8-engine): confirm a settled rebuild
      re-derives nothing and every path is unchanged.

## 6. Records

- [ ] 6.1 ADR in `docs/adrs/BUILD/`: named project models and per-model build
      directories; amends ADR-005/ADR-024 (reference spellings) and
      ADR-038 (per-directory publication and lock); names the
      originating project.
- [ ] 6.2 Update `docs/adrs/README.md` and the build-pipeline and CLI
      sections of `docs/architecture.md`.
- [ ] 6.3 `docs/cli.rst` (`models`, `--all`, the fourth spelling),
      `docs/node-tree.rst` (the manifest table), changelog entry; sync the
      `build-pipeline` and `cli` specs; archive the change.
