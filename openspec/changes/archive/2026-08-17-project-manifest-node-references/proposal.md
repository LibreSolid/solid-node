## Why

The framework has no concept of a project root. `os.getcwd()` stands in for one
in three places — `sys.path` seeding (`loader.py:12`), the marker containment
check (`loader.py:105`), and the source-closure boundary (`sources.py:45`) — and
this only works because every caller happens to `chdir` into the project
directory first. Run any command from a subdirectory and `source_closure`
silently truncates: a node's tracked source set loses files it genuinely depends
on, and the build believes stale artifacts are current.

Having no root forced the entry point to be a fixed path, `root/__init__.py`.
That in turn forced `NODE` into existence as the only way to say "the node class
is somewhere else" — the loader's one supported answer to a question the file
should not have been asked. The marker then spread by imitation to files with a
single node class, where it decides nothing:
`docs/examples/v8-engine/root/cylinder_unit.py:77` and `crankshaft.py:44` both
set it redundantly. Its one defensible use, the package facade in
`tests/loader_fixtures/imported_entrypoint/__init__.py`, exists only because the
entry point could not be named directly.

Meanwhile nothing can address a node that is not the project root. `solid
snapshot` exists so an agent can look at its own work without a human
(ADR-021), but an agent developing one sub-assembly can only snapshot the whole
model. The accessor an agent needs — name any node, from anywhere — is the same
accessor that makes `NODE` unnecessary, because a caller that can name a class
never needs the file to name it.

Test resolution has the identical defect with no marker to soften it.
`find_class` applies the marker branch only to `AbstractBaseNode`
(`loader.py:83`); for `TestCase` it returns `candidates[0][1]`, first class
wins. `Test.handle` then binds exactly one `TestCase` to exactly one node
(`manager/test.py:44-46`). A test file holding several `TestCase`s runs one of
them and reports success. A silently unrun test is worse than a wrongly loaded
node: the wrong node is visible on screen, the missing test is visible nowhere.

## What Changes

- **Project manifest.** `pyproject.toml` gains `[tool.solid-node]` with
  `model = "dutch_windmill.dutch_windmill:DutchWindmill"`. The project root is
  the directory holding the nearest ancestor `pyproject.toml` that carries that
  table, searched from the referenced file when the reference is a path and
  from the working directory otherwise. The notation is the entry-point object
  reference the framework already uses for itself
  (`solid = "solid_node.cli:manage"`).
- **Node references.** Every node-scoped command accepts three spellings that
  resolve to the same class object: the qualifier `package.module:Class`, a
  file path, and the hybrid `path/to/file.py:Class`. A path with no colon means
  "the single node class defined in this file" and fails loudly when the file
  defines several.
- **The positional becomes optional.** With no argument, a node-scoped command
  operates on the manifest's model. `solid build` replaces `solid build root`.
- **`NODE` is removed** — `NODE_MARKER`, `_resolve_marker`, and every use in
  the framework's fixtures and examples. `AmbiguousNodeError` survives, now
  telling the caller to name a class rather than to add a marker. The
  project-containment check survives too, re-anchored to the discovered root:
  a qualifier makes `solid snapshot solid_node.node.leaf:Leaf` expressible for
  the first time, so the guard matters more than it did, not less.
- **Root anchoring.** `sys.path`, the dotted module name computed in
  `import_module_from_path`, `source_closure`'s boundary, and the project's
  build directory all derive from the discovered root instead of `os.getcwd()`.
  The build directory is on that list because the build lock is derived from
  it: resolved against the caller's cwd, a command run from a subdirectory
  publishes into a private tree and takes a private lock. Both spellings of a
  reference must reach the same `sys.modules` entry; two entries for one file
  would give two class objects and corrupt the closure that `sources.py`
  resolves by identity.
- **Every companion `TestCase` runs.** The loader returns all of them, not the
  first. A `TestCase` may declare `node = <NodeClass>`; an undeclared one binds
  to the node module's single node class, and is a hard error naming the class
  when that module defines several.
- **`solid new`** scaffolds `<name>/<name>/<name>.py` with the manifest written,
  normalising hyphens to underscores and deriving the class name — `solid new
  snowman-3` gives `snowman_3/snowman_3.py` holding `Snowman3`. The word `root`
  disappears from the scaffold and from the printed next steps.
- **`solid snapshot`** takes the project build lock around node preparation,
  releasing before the OpenSCAD render, and defaults `-o` from the reference
  instead of the fixed `snapshot.png`.

Breaking change. Every project must gain a manifest; `root/__init__.py` stops
being meaningful as a convention. Migration of the projects that live outside
this repository is not in this cycle.

## Capabilities

### New Capabilities

None. Project-root discovery is added as a requirement under `build-pipeline`,
which already owns loader rules.

### Modified Capabilities

- `build-pipeline`: "Path-based node loading" currently requires a `NODE`
  marker when a file defines several node classes and anchors the marker's
  project-containment check on the working directory. It becomes reference
  resolution against a discovered project root, with the marker gone. A new
  requirement covers manifest discovery and the model reference.
- `cli`: "Node path resolution" requires a `path` positional for every
  node-scoped command and rewrites a directory to `<dir>/__init__.py`; both
  clauses go. "Build command", "Test command", "Snapshot command" and "New
  command" all name paths, `root`, or `__init__.py` in their text or scenarios.
- `test-framework`: "Test declaration and binding" describes one companion
  `TestCase` per node file; "Test runner lifecycle" runs the methods of "the
  companion test case", singular.

## Impact

- `solid_node/core/loader.py`: reference parsing and resolution, root
  discovery, module naming, marker deletion, all-`TestCase` loading.
- `solid_node/node/sources.py`: `source_closure` boundary from the discovered
  root.
- `solid_node/cli.py`: optional positional, directory-coercion removal.
- `solid_node/manager/`: `build.py` (resolve-or-exit-66, preserving
  `MODEL_NOT_FOUND`), `test.py` (multiple test cases, reference-aware test
  mapping), `snapshot.py` (build lock, output default), `new.py` and its
  templates, `develop.py` and `export.py` for the optional positional.
- Framework fixtures and examples: `tests/test_loader_node_marker.py`, eight
  `tests/loader_fixtures/*`, ten `tests/meta_project/*`,
  `tests/source_set_project/__init__.py`, `tests/test_meta.py`,
  `tests/test_manager_develop.py`, `docs/examples/v8-engine/`.
- `docs/cli.rst` and the loader documentation.
- Downstream, not in this cycle: solid-node-shop passes the literal `"root"` to
  `solid build` in `floor/watcher.py` and `floor/preparation.py`, and
  `shop-skills/solid-node/SKILL.md:67` teaches `NODE = MyAssembly`. Both need
  the shop's own cycle once this lands.

## Known gaps recorded, not closed here

- **Rebuild granularity.** Staleness remains file-granular: `node.mtime` is the
  maximum over `source_closure` (`base.py:407`) while artifact identity is
  class+args, so editing a file that defines several nodes re-renders all of
  them and republishes artifacts whose geometry did not change. Measured
  during this cycle's planning: OpenSCAD STL output varies in facet *order*
  between runs of identical input (`sort` of two runs is byte-identical), so
  comparing published bytes cannot detect this, but the generated `.scad` is
  stable across reloads and would. That is a change to the geometry-staleness
  key and to SPRINT-003's D6, and belongs in its own cycle.
- **Animation keyframe is not part of the artifact key.** `solid snapshot
  --time 0.5` writes an assembly's `.scad` at that keyframe to a path keyed only
  on class and arguments. Under the build lock there is no interleaving, nothing
  serves `.scad`, and the next build regenerates it.
- **`pyproject.toml` is not watched.** `Builder.on_modified` filters to `.py`,
  so editing the model reference during `solid develop` has no effect until
  restart.
