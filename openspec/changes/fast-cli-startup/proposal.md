## Why

Every `solid` invocation pays for every command and every CAD backend the
framework ships, whether or not the invoked command touches them. Measured on
this workspace:

| invocation / import | cost |
| --- | ---: |
| `solid --help` | 4.06 s |
| `solid viewer` (prints two JSON fields) | 3.63 s |
| `import solid_node.viewers.bundle` — all `solid viewer` actually needs | 0.01 s |
| `import solid_node.cli` | 3.11 s |
| `import cadquery` (reached via `solid_node.node` → `fusion` → `solid_node.exact`) | 1.84 s |
| `import trimesh` (reached via `solid_node.node.base`) | 0.64 s |

The framework is driven by agents and by the LibreSolid Studio shop floor,
which spends this cost repeatedly: opening one project runs `solid viewer`,
`solid build`, and `solid snapshot` — roughly ten seconds of process startup
before anything about the project has been read. A project that uses only the
OpenSCAD/`solid2` backends still pays 1.84 s for `cadquery` on every command,
including `solid new`, which touches no geometry at all.

The cost is entirely import-time bookkeeping, not work: `solid_node/cli.py`
imports all seven command modules at module scope so it can build one argparse
subparser per command, and `solid_node/node/__init__.py` eagerly re-exports
every backend class so that importing *any* node module drags in the exact
geometry stack.

## What Changes

- The `solid` CLI imports only the module of the command being run. The
  command registry becomes a name → module table so the migration guard and
  the subparser names, which need only command *names*, no longer force
  every command module to load.
- Top-level `solid -h` keeps its present output. It is the one path that needs
  every command's docstring, so it — and only it — loads all command modules.
- `solid_node/node/__init__.py` keeps exporting exactly the names it exports
  today, resolved on first attribute access rather than at package import.
  A project that never touches an exact-geometry or CadQuery node never
  imports `cadquery`.
- `trimesh` is imported by the one function that uses it rather than at
  `solid_node/node/base.py` module scope.
- **Two further chains reach the exact stack without going through
  `solid_node/node/__init__.py` at all, and are deferred the same way.**
  Implementation evidence found them: a real `solid build` of a
  `Solid2Node`-only project still imported `cadquery` after the three changes
  above, because
  - `solid_node/core/loader.py:15` imports `from solid_node.test import
    TestCase` at module scope, and `solid_node/test.py:22` imports
    `solid_node.exact`. `TestCase` is used at exactly one place,
    `load_tests()`; a build never needs it.
  - `solid_node/core/serializer.py:57` imports
    `solid_node.simulation.enumeration`, which runs
    `solid_node/simulation/__init__.py`, whose `.scenario` re-export imports
    `solid_node.test` and lands in the same place.
  Both are deferred to their use sites, the second through the same PEP 562
  accessor used for the node package.
- `solid_node/node/operations.py` imports `trimesh` at module scope, and
  `base.py` imported `Rotation`/`Translation` from it at module scope — so
  deferring only the direct `trimesh` import would not have kept it out of
  `solid_node.node.base`. That import is deferred to its two call sites.
- No change to the command grammar, command set, options, help text, exit
  codes, error messages, or the public `solid_node.node` API. Not breaking.

## Capabilities

### New Capabilities

- `cli-startup-cost`: what a `solid` invocation is permitted to import — a
  command loads only its own module, the node package resolves backend
  exports on demand, and neither changes any observable output.

### Modified Capabilities

None. The `cli` capability's requirements — command-first grammar and
migration guard, dotenv precedence, node path resolution, and every command's
options and behaviour — hold unchanged; this change only moves when their
modules are imported.

## Impact

- `solid_node/cli.py` — command registry and dispatch.
- `solid_node/node/__init__.py` — module-level `__getattr__` for the exported
  backend names.
- `solid_node/node/base.py` — `trimesh` and `.operations` deferred to their
  use sites.
- `solid_node/core/loader.py` — `TestCase` deferred into `load_tests()`.
- `solid_node/simulation/__init__.py` — exports resolved on demand.
- Dependencies are unchanged: `cadquery` and `trimesh` remain required
  installs (`pyproject.toml`). This change is about *when* they are imported,
  not whether they are needed.
- `solid build` still imports `trimesh`, because `PieceInventory`
  (`solid_node/core/pieces.py`) derives every piece's geometry facts from the
  cached base mesh on each publication. The deferral benefits the commands
  that never reach that path.
- Consumers that read `solid_node.node.<submodule>` as an attribute without
  importing the submodule keep working, because the same accessor resolves
  submodule names.
- Downstream: LibreSolid Studio's floor (`floor/preparation.py`) runs three
  `solid` subprocesses per project open and is the largest beneficiary.
