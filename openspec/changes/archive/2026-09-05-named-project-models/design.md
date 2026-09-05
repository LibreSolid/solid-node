## Context

A project is the nearest ancestor `pyproject.toml` carrying
`[tool.solid-node]`; its `model` key is one reference, and every node-scoped
command falls back to it (`build-pipeline`, `cli`; ADR-005, ADR-024). The
project has one build directory — `$SOLID_BUILD_DIR`, default `_build`,
anchored on the discovered root — and `get_build_dir(origin)` is read at node
construction (`node/base.py`) to place every artifact, by the builder to place
`viewer.json`, `errors.json` and the lock beside it, and by `solid develop` to
tell the viewer's server where to serve from. The builder already sets
`SOLID_BUILD_DIR` in its own process to the absolute directory it is building
into, so a subprocess built for it places artifacts where the parent expects.

Publication is per artifact and atomic (ADR-038): `viewer.json` is written
last, and the sweep that follows removes every file in the build directory
the new document does not name, sparing `.scad`, `.brep`, `.stl.lock` and
`.tmp` by extension and the two documents by name. The lock is
`<build dir>.lock`, beside the directory (ADR-038). One directory, one
document, one sweep: a second model built into the same directory replaces
the first's publication and deletes its STLs.

The originating project, `projects/3DPrintedClocks`, is one Git repository
with one shared `clocks` library at its root and one solid-node model per
clock under `design/`. It cannot become one repository per clock (the loader
anchors the import path on the manifest's directory, and the library is
above every clock) and cannot share one build directory. The framework has
no way to say "this project has these models".

## Goals / Non-Goals

**Goals:**

- A manifest can declare several named models and, optionally, a default.
- A declared name works everywhere a reference does.
- Each declared model publishes into a directory of its own, with its own
  document, errors, lock and sweep, so models never disturb each other.
- The models can be listed, with their build state, by a host that imports
  no project code.
- `solid build --all` and `solid test --all` walk every declared model and
  report each outcome.
- A project that declares no models behaves, and lays out its build
  directory, byte-for-byte as today.

**Non-Goals:**

- Concurrent `--all`. Per-model locks make it possible later; this cycle
  walks sequentially.
- Sharing artifacts between models, or a common cache across directories.
- Per-directory or nested manifests; the project root is still where the one
  manifest is.
- Any studio behaviour (folder card, model switcher, per-model screenshots);
  the studio consumes `solid models --json` in its own change.
- Changing publication, artifact naming, the viewer document, or currency.

## Decisions

### D1. Names in a `models` table; `model` becomes the default's name

```toml
[tool.solid-node]
model = "wall_clock_01"

[tool.solid-node.models]
wall_clock_01 = "design.wall_clock_01.clock:WallClock01"
wall_clock_02 = "design.wall_clock_02.clock:WallClock02"
```

A single-model manifest keeps `model = "package.module:Class"`; the table is
the only signal that a project has several, so no existing manifest changes
meaning. Beside the table, `model` must equal a key: one key, one rule, no
guessing whether a string is a name or a reference. Names are restricted to
one word (`[A-Za-z_][A-Za-z0-9_-]*`) so they can never be confused with a
qualifier (which contains `.` or `:`) or a path.

*Alternatives.* A list of references without names — nothing to call a model
by, nothing to name a directory after. Letting `model` stay a reference beside
the table and matching it against the values — a second way to say the same
thing, and a manifest whose default is not in the table. A `default = true`
flag inside the table — the manifest already has a `model` key, and one
default expressed in two places drifts.

### D2. A declared model owns `<build root>/<name>/`

The build root is what `$SOLID_BUILD_DIR` resolves to today. A declared
model's build directory is the root's child named after it, and everything
that is "per build directory" — `viewer.json`, `errors.json`, the lock, the
sweep, the symlink-to-directory migration, git exclusion — is unchanged and
now simply happens per model. A project without the table keeps the flat
root, so no existing project's artifacts move.

Two consequences need rules:

- A name must not equal a directory at the project root, because artifacts
  mirror the source tree and `design/` would mirror into `_build/design/`.
  This is checked when the manifest is read and refused with the manifest,
  the name and the directory named; it costs one `isdir` per model.
- An undeclared reference — a sub-node by qualifier or path — still builds
  in the flat root, as it does today. Its sweep walks the root and would
  descend into the model directories and delete their STLs; the sweep is
  therefore pruned at any immediate child that is a declared model name. And
  because a model's lock is `<build root>/<name>.lock`, which now lies
  *inside* the root, the sweep spares `.lock` by extension: removing a lock
  file's path while another process holds it would let the next acquirer
  open a fresh inode and lock nothing.

*Alternatives.* One flat directory with one document per model
(`<name>.viewer.json`) — the sweep would have to union every model's
document, the lock would be shared, and a host reading "the build directory"
would need to learn the naming; per-directory keeps every consumer's reading
of `viewer.json` unchanged. A sibling root per model (`_build-<name>`) —
scatters the project's artifacts across the root and the gitignore rule.
Placing model directories under `<build root>/models/` — trades one collision
(`design/`) for another (`models/`) and adds a level for no gain.

### D3. Selection anchors the build directory before the node is loaded

Every artifact path is computed when a node is constructed, from
`get_build_dir(self.src)`, which reads `SOLID_BUILD_DIR` and the project
root. The loader gains a selection step: given a reference (or none), it
returns the reference to load and the build directory it owns — the model's
directory for a declared name or the default, the root otherwise. Each
command performs that step first and anchors the directory in the process
that will load the node — by handing it to `Builder(build_dir=...)`, which
already sets the environment in its build pass, and by setting the same
absolute `SOLID_BUILD_DIR` in the in-process paths (`test`, `snapshot`,
`export`) — before `load_node` runs. `solid develop` passes the selection's
directory to the viewer's `serve`.

`resolve_node` keeps its `(klass, path, root)` contract for existing
callers; the name is looked up before the qualifier reading, so a declared
name shadows a bare top-level module of the same spelling, which the project
chose when it named the model. The `path` a builder is handed is the
selection's concrete reference, so `Builder`'s watch loop and reload never
see a name.

*Alternatives.* Making `get_build_dir` take the model — every node would
have to know which model it is being built for, which a sub-node shared by
two models cannot. A module-level "current selection" in the loader — an
implicit global in a resolver; the environment is already the mechanism the
builder uses for exactly this, and it is inherited by the fresh interpreters
(ADR-067) the commands spawn.

### D4. `solid models` reads the manifest and the directories, nothing else

Listing must be cheap enough for a host to call on every hub refresh, so it
never imports project code and judges state from files: `errors.json` →
`failed`, else `viewer.json` → `published`, else `unbuilt`. Currency (is the
publication behind the sources?) needs the node loaded and is deliberately
not reported; a host that wants it runs a build, which reports `current`.
The JSON shape mirrors `solid viewer`: one object, exact keys, and a
single-model project yields one entry with `name: null` so a host has one
code path for both shapes. The command registers with `needs_node = False`
like `viewer` and `new`, and lives in its own module under the lazy command
table (`cli-startup-cost`).

### D5. `--all` walks in declaration order and never stops early

`solid build --all` runs the existing one-model loop once per declared
model, in table order, each with its own directory; a failure is reported
and the walk continues, so one broken clock does not hide the others. That
includes a model whose module does not import: the single-model command
lets such an error keep its traceback, but in a walk it is one model's
failure, written to that model's `errors.json` so `solid models` reports
it `failed`. Exit is nonzero if any failed. `solid test --all` extends the runner's existing
"several selections, one run" shape (a multi-node file already tests every
node in one reported run), anchoring the directory per selection; a model
that will not load or build is a failure of that model, and `--failfast`
keeps its meaning. `--all` with a reference is an argument error; `--all` in
a single-model project is refused rather than silently building the one
model, so the flag means what it says.

## Risks / Trade-offs

- [Name lookup precedes the qualifier reading, so a declared name hides a
  top-level module of the same spelling] → the project chose the name; the
  module stays reachable as `name:Class` or by path, and the rule is stated
  in `cli`.
- [The flat root's sweep is pruned by name, so a declared name added *after*
  a sub-node build already mirrored a same-named source directory could
  hide those artifacts] → the manifest check refuses a name that equals a
  root directory, so no mirrored path can share a model directory's name.
- [In-process paths depend on `SOLID_BUILD_DIR` being set before the node
  is constructed] → the selection step is the first thing each command does
  after argument parsing; a test builds a two-model fixture through every
  command and asserts the artifact directory.
- [A host reading `_build/viewer.json` in a multi-model project finds
  nothing] → that is the point: there is no project-level publication to
  mistake for a model's. `solid models --json` tells the host where each
  one is.
- [Sequential `--all` on the clocks is minutes per model] → accepted for
  this cycle; per-model locks leave the door open to `--jobs`.
- [Found during verification: `prepare_build_dir` removed the held lock
  file on every build, since `<build dir>.lock` spells like the versioned
  siblings the ADR-032 migration sweeps away] → the cleanup now skips the
  lock path. This was true of the flat `_build.lock` before this change and
  is fixed for every build directory; a red test in `test_build_lock`
  guards it.

## Migration Plan

Nothing moves for a project without a `models` table. The originating
project adds the table and a default after this integrates; its existing
flat `_build/` becomes the flat root holding nothing a declared model owns,
and the first `solid build` publishes `_build/wall_clock_01/`. The stale
flat publication is not removed by the framework (it belongs to no model and
sweeping it would be a guess); the project may delete it.

## Open Questions

None for ratification. The ADR number is assigned when the ADR is written;
ADR-072 is taken by the unintegrated `declared-time-base` cycle.
