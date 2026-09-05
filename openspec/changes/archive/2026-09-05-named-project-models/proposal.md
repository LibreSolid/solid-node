## Why

A project manifest names exactly one model, and a project has exactly one
build directory whose `viewer.json` publication sweeps every artifact it does
not name. That is the right shape for a machine, and the wrong shape for a
family of them: `projects/3DPrintedClocks` is one repository holding one
shared `clocks` library and, under `design/`, one solid-node model per clock —
today `design.wall_clock_01.clock:WallClock01`, with the author's other ~130
clock scripts waiting to be rebuilt the same way. The clocks cannot be split
into one repository each, because the library they share lives at the
repository root and the loader anchors the import path on the manifest's
directory; and they cannot share one build directory, because building the
second clock replaces the first clock's publication and deletes its STLs. The
project can name its clocks only one at a time, and nothing can list them.

## What Changes

- A manifest MAY declare several models by name in a
  `[tool.solid-node.models]` table, `name = "package.module:Class"`. When it
  does, `model` names the default among them by its key rather than holding a
  reference; a manifest without the table is unchanged.
- A declared name is a fourth node-reference spelling, accepted by every
  node-scoped command: `solid build wall_clock_02`. A bare word that is a
  declared name is the model; otherwise the reference is read as today.
- Each declared model has its own build directory, `<build root>/<name>/`,
  with its own `viewer.json`, `errors.json`, lock and sweep, so publishing one
  model never disturbs another. The build root is `$SOLID_BUILD_DIR` anchored
  on the project root as today, and a project that declares no models keeps
  its flat build directory.
- `solid models` lists the project's models — name, reference, whether it is
  the default, its build directory, and whether it is unbuilt, published or
  failed — as text or, with `--json`, as one document a host can read without
  importing project code. A single-model project lists its one model.
- `solid build --all` and `solid test --all` walk every declared model in
  declaration order. A model that fails does not stop the walk; the command
  reports each outcome and exits nonzero when any failed.
- A project that declares models but no default refuses a node-scoped command
  given no reference, listing the names, rather than guessing.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `build-pipeline`: the *Project root discovery and model reference*
  requirement admits a declared-models table and a default name; the *Build
  artifact layout* requirement gives each declared model its own build
  directory under the project build root and keeps the flat directory's sweep
  out of them.
- `cli`: the *Node path resolution* requirement admits a declared name as a
  reference spelling and defines the no-reference behaviour of a project with
  and without a default; the *Build command* and *Test command* requirements
  gain `--all`; a *Models command* requirement is added.

## Impact

- `solid_node/core/loader.py` — project discovery returns the declared models
  and the default beside the root; reference resolution recognises a declared
  name; a selection step names the build directory a resolved model owns.
- `solid_node/core/builder.py` — `get_build_dir` anchors a selected model's
  directory; the artifact sweep does not descend into declared model
  directories and spares lock files that live inside the build root.
- `solid_node/manager/build.py`, `test.py`, `develop.py`, `snapshot.py`,
  `export.py` — each command anchors the selected model's build directory
  before loading the node; `build` and `test` gain `--all`.
- `solid_node/manager/models.py`, `solid_node/cli.py` — the `models` command.
- `docs/cli.rst`, `docs/node-tree.rst`, `docs/changelog.rst` — the manifest
  table, the fourth spelling, the new command and flags.
- `docs/adrs/` — one ADR for the manifest shape and per-model build
  directories; `docs/architecture.md` build-pipeline and CLI sections.
- Originating project: `projects/3DPrintedClocks`, whose manifest will declare
  its clocks once this integrates. No dependency, artifact-naming (ADR-026),
  publication (ADR-038) or viewer-document change; a single-model project's
  behaviour and build directory are byte-for-byte what they are today.

## Explicitly out of scope

- **The studio.** Showing a multi-model repository as a folder in the hub, a
  model switcher in the workspace, per-model screenshots and the session's
  artifact root are a libresolid-studio change that depends on this one and
  reads `solid models --json`.
- **Parallel `--all`.** Per-model directories give each model its own lock,
  so models could build concurrently; this cycle walks them sequentially.
- **Sharing artifacts between models.** Two models that contain the same node
  at the same parameters render it twice, once per directory.
- **Nested or per-directory manifests.** The project root and its import path
  stay where the one manifest is.
