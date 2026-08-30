## Context

Two independent eager-import sites dominate `solid` startup.

**`solid_node/cli.py`** imports all seven command classes at module scope
because `manage()` builds one argparse subparser per command and uses each
command's `__doc__` as that subparser's help. Help text is the only thing that
requires the class object; the migration guard and the subparser *names* need
only the names.

**`solid_node/node/__init__.py`** re-exports every backend class. Because
importing a submodule runs its package `__init__`, `from solid_node.node.base
import AbstractBaseNode` — which `solid_node/core/loader.py`, `core/builder.py`,
`core/pieces.py`, `manager/test.py`, and `simulation/enumeration.py` all do —
executes that whole re-export list, and `from .fusion import FusionNode` pulls
`solid_node.exact` → `cadquery` (1.84 s). `solid_node/node/base.py` separately
imports `trimesh` (0.64 s) at module scope for a single call site.

Nothing dispatches on a registry of node subclasses: every consumer either
imports a concrete class by name or tests `issubclass(..., AbstractBaseNode)`
(`core/loader.py:163`, `simulation/enumeration.py:105`). So no import is
load-bearing for a side effect, and deferral is safe.

`cadquery` and `trimesh` are declared dependencies in `pyproject.toml` and stay
that way. This change is about when they load, not whether they are required.

## Goals / Non-Goals

**Goals:**

- `solid viewer` answers from `solid_node/viewers/bundle.py` alone.
- A command's process imports that command's module and no other's.
- Importing any node module does not import the exact-geometry stack.
- Identical observable behaviour: same grammar, help, options, exit codes,
  error messages, and public `solid_node.node` API.

**Non-Goals:**

- Making `cadquery`, `trimesh`, or any other dependency *optional*. That is the
  `mesh-engine-dependency` capability's shape and is not proposed here.
- Speeding up `solid build` itself. It reaches `PieceInventory`, so it still
  imports `trimesh`; and a project that uses CadQuery still imports `cadquery`,
  correctly.
- Changing the duck-typed command contract of ADR-024 (`__doc__`,
  `needs_node`, `add_arguments`, `handle`).
- Parallel rendering or artifact-currency work. Separate changes.

## Decisions

### The command registry becomes a name → location table

`commands = [Build(), Develop(), ...]` becomes an ordered mapping from command
name to the module path and class name that provides it. `manage()` resolves
one entry — the selected command — imports that module, instantiates the class,
and builds its subparser exactly as today.

Names are the only thing the migration guard and the choice validation need, so
both keep working with nothing imported.

*Alternative — a shared abstract base class with registration.* Rejected for
the same reason ADR-024 rejected it: it buys nothing at this command count and
adds ceremony. The table is the minimum change that removes the import.

*Alternative — a third-party CLI framework.* Rejected: a new runtime dependency
for a framework that values a lean footprint, and it would import more, not
less.

### Top-level help imports every command; nothing else does

`solid -h` and the no-subcommand invocation render every subparser's help, which
is each command's `__doc__`. That genuinely needs every class. On that path
alone, resolve the whole table.

*Alternative — carry a one-line help string in the table.* This would make
`solid -h` fast too, but it duplicates every command's docstring and invites
drift. Rejected for now; the interactive help path is not the hot path, and the
option stays open if `solid -h` later turns out to matter (the shop's floor
never runs it). A conformance test (below) would make the duplication safe if
we ever want it.

### `solid_node/node/__init__.py` uses a module-level `__getattr__` (PEP 562)

The exported names move into a table mapping each name to the submodule that
defines it. A module-level `__getattr__` imports that submodule on first access,
caches the resolved object in `globals()` so later accesses are a plain dict
lookup, and returns it. `__all__` lists the same names as today, so
`from solid_node.node import *` and tooling introspection are unchanged, and
`__dir__` returns them.

`__getattr__` also resolves *submodule* names, so `solid_node.node.assembly`
after a bare `import solid_node.node` still works — previously the eager
`from .assembly import AssemblyNode` bound that attribute as a side effect.

`from .base import StlRenderStart` stays eager. `base` is on every path that
matters and costs `solid2` + `numpy` ≈ 0.11 s; deferring it would complicate
the module for no measurable gain.

*Alternative — delete the re-exports and require deep imports.* Breaking: every
existing project and the packaged `solid new` template do
`from solid_node.node import Solid2Node`. Rejected.

*Alternative — a lazy proxy class per export.* Rejected: `issubclass` and
metaclass behaviour (`CadQueryNode` uses the `CheckCQEditor` metaclass) would
have to be forwarded, and a proxy that is not the real class breaks
`isinstance`. PEP 562 hands back the real class.

### The test framework and the simulation package are deferred too

Implementation evidence overturned the assumption that `node/__init__.py` was
the only route to the exact stack. A real `solid build` of a `Solid2Node`-only
fixture still imported `cadquery`, through two chains that never touch the node
package's exports:

- `core/loader.py` → `solid_node.test` → `solid_node.exact` → `cadquery`
- `core/serializer.py` → `solid_node.simulation.enumeration`, which runs
  `simulation/__init__.py` → `.scenario` → `solid_node.test` → the same place

Every node-scoped command goes through the loader, so this is the chain that
matters most: it is on the shop floor's hot path, where `solid build` runs on
every project open and every watcher rebuild.

`TestCase` is used at exactly one place in the loader, `load_tests()`, so the
import moves there. The simulation package gets the same PEP 562 accessor as
the node package, for the same reason and with the same first-access caching —
its exports are a public surface (`from solid_node.simulation import Driver`)
that must not change.

Deferring these does **not** make the test framework optional or conditional:
it is imported the moment anything runs a test, exactly as before.

### `trimesh` moves into `cached_base_mesh`, and `.operations` with it

It has exactly one *direct* use site (`base.py:105`). The module-level cache and
its `(stl_file, mtime)` keying and stale-entry eviction (ADR-028) are untouched;
only the import moves. Python caches the module in `sys.modules`, so the
repeated statement costs a dict lookup.

Two things the first draft of this design missed, both found by implementation:

- `node/operations.py` imports `trimesh` at module scope, and `base.py`
  imported `Rotation`/`Translation` from it at module scope. Moving only the
  direct import would have left `trimesh` reachable from
  `solid_node.node.base` through the back door, so the requirement would have
  been unmeetable. That import is deferred into the two methods that use it.
- `tests/test_node_mesh_cache.py` patches `solid_node.node.base.trimesh.load`.
  A bare in-function `import trimesh` leaves no module attribute of that name,
  so `mock.patch` raises `AttributeError` — masked when the whole file runs,
  because an earlier test happens to populate the binding, and failing when
  the test runs alone. `base.py` therefore keeps a module-level accessor and a
  PEP 562 `__getattr__` resolving the name `trimesh`, the same mechanism this
  design already blesses for the node package.

### Import errors surface at the point of use

The deferred paths do not catch `ImportError`. A genuinely broken install
raises the real error when the name is first used, with the requested name in
the message, rather than degrading into `AttributeError` — the failure mode a
naive `__getattr__` produces when the inner import raises.

## Risks / Trade-offs

- **The name → module table can drift from reality** (a renamed class or moved
  module fails only when that command is invoked) → a test that walks the whole
  registry, imports and instantiates every command, and asserts the ADR-024
  duck-typed contract (`__doc__`, `add_arguments`, `handle`). It runs every
  command's import once, in one test, instead of on every invocation.
- **`solid -h` stays at today's cost** → accepted and recorded above; it is
  interactive-only and no automated caller uses it.
- **A lazy `__getattr__` weakens static analysis** — an IDE or linter no longer
  sees the names by following the imports → `__all__` keeps them declared; if a
  type checker complains, a `TYPE_CHECKING`-guarded eager import block restores
  it with no runtime cost.
- **Circular imports** — a submodule imported from `__getattr__` that itself
  reads a lazy name off `solid_node.node` would re-enter the accessor →
  resolution caches into `globals()` before returning, and no current submodule
  imports from the package root; the registry test would catch a future one.
- **`multiprocessing` in the builder** — the build supervisor forks a `Builder`
  per generation; a forked child inherits whatever was already resolved, so
  deferral cannot make it re-import. No change.
- **Measurement is environment-specific** — the figures come from this
  workspace's venv on this machine → the specs assert *which modules are
  imported*, which is deterministic; wall-clock numbers stay in the proposal as
  motivation, not as a contract.
