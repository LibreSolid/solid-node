# ADR-059: Import at the Point of Use

**Status:** Accepted
**Date:** 2026-08-30
**Depends on:**
- [ADR-024: Command-First CLI Grammar and Duck-Typed Command Registry](./ADR-024-command-first-cli-grammar-and-duck-typed-command-registry.md)

**Related to:**
- [ADR-046: Conditional OpenSCAD Dependency](../NODE/ADR-046-conditional-openscad-dependency.md)
- [ADR-058: Indexed Package Lookup for Source Closures](../NODE/ADR-058-indexed-package-lookup-for-source-closures.md)

## Context and Problem Statement

Every `solid` invocation imported every command module and the whole CAD
backend stack, whichever command was asked for. Measured on a development
workspace: a bare `solid --help` took 4.06 s; `solid viewer`, which prints two
JSON fields, took 3.63 s, while the module that answers it —
`solid_node.viewers.bundle` — imports in 0.01 s.

Three eager-import sites caused it:

- `cli.py` imported all seven command classes at module scope, because
  `manage()` builds one argparse subparser per command and uses each command's
  `__doc__` as help (ADR-024). Help text is the only thing that needs the class;
  the names alone drive the grammar and the migration guard.
- `node/__init__.py` re-exported every backend, so importing *any* node module
  ran that list and pulled `solid_node.exact` → `cadquery` (1.84 s). Since
  importing a submodule runs its package `__init__`, every consumer of
  `node.base` paid it.
- `node/base.py` imported `trimesh` (0.64 s) at module scope for one call site.

The framework is driven by agents and by the LibreSolid Studio shop floor,
which runs `solid viewer`, `solid build` and `solid snapshot` per project open
— roughly ten seconds of process startup before anything about the project had
been read.

## Decision Drivers

- The framework is an agent-facing surface (ADR-024). Startup latency is paid
  per invocation, and agents invoke constantly.
- A project that uses only the OpenSCAD/`solid2` backends should not pay for
  the exact-geometry stack.
- No observable change: same grammar, help, options, exit codes, error
  messages, and public `solid_node.node` API.
- Nothing may become *optional*. These are declared dependencies; this is about
  when they load.

## Considered Options

1. **Import each thing at its point of use, exposing packages through PEP 562
   module `__getattr__`** (chosen)
2. Delete the package re-exports and require deep imports
3. Lazy proxy objects standing in for the exported classes
4. Leave it; accept the startup cost

## Decision Outcome

Chosen: **import at the point of use.**

- `cli.py`'s command list becomes a name → (module, class) registry. `manage()`
  resolves only the command being run. The migration guard and subparser names
  work from names alone. Top-level `solid -h` is the one path that genuinely
  needs every docstring, and it alone resolves the whole table.
- `node/__init__.py`, and `simulation/__init__.py`, keep exporting exactly the
  names they export today through a module-level `__getattr__` that imports the
  defining submodule on first access and caches the result into `globals()`.
  `__all__` and `__dir__` keep the surface declared. Submodule names resolve
  through the same accessor, because the eager imports used to bind them as a
  side effect.
- `node/base.py` imports `trimesh` in the function that reads meshes, and
  defers its `.operations` import too — `node/operations.py` imports `trimesh`
  at its own module scope, so deferring only the direct import would have left
  it reachable through the back door.
- `core/loader.py` imports `TestCase` inside `load_tests()`, its one use site.

The last two were found by implementation, not design: after the first three
changes a real `solid build` of a `Solid2Node`-only project *still* imported
`cadquery`, through `core/loader.py` → `solid_node.test` → `solid_node.exact`,
and through `core/serializer.py` → `simulation/__init__` → `.scenario` → the
same place. Neither passes through `node/__init__.py`. Every node-scoped command
goes through the loader, so that chain was the one that mattered most.

Measured after: `import solid_node.cli` 3.48 s → 0.002 s (77 modules loaded
instead of 2 227), `solid_node.node` 3.59 s → 0.110 s, `core.loader` → 0.120 s,
`solid viewer` 3.79 s → 0.044 s. A `Solid2Node`-only build imports no
`cadquery`, `solid_node.exact`, `solid_node.test` or `scenario`; a CadQuery
project still imports all of them.

### Why not deep imports only (option 2)

Breaking. Every existing project and the packaged `solid new` template do
`from solid_node.node import Solid2Node`.

### Why not lazy proxies (option 3)

`isinstance` and `issubclass` are load-bearing here, and `CadQueryNode` carries
the `CheckCQEditor` metaclass. A proxy that is not the real class breaks both.
PEP 562 hands back the real object.

## Consequences

- A command's cost is its own. Adding a heavy dependency to one command no
  longer taxes the other six.
- **`solid -h` keeps today's cost**, since it renders every command's docstring.
  Making it fast would mean duplicating each docstring's first line in the
  registry, which invites drift; the interactive help path is not the hot path
  and no automated caller uses it. The option stays open behind a test pinning
  the copies to the docstrings.
- Nothing became optional. Running or discovering a test imports the test
  framework exactly as before; a broken backend raises its own `ImportError`
  naming the requested export, never a bare `AttributeError` — the trap a naive
  `__getattr__` sets, because `hasattr()` swallows the error and reports the
  name as missing.
- `solid_node.node.base` keeps `trimesh` resolvable as an attribute, because
  `mock.patch('solid_node.node.base.trimesh.load')` must keep working. Without
  it, that patch fails only when its test runs in isolation — passing in a full
  run because an earlier test happens to populate the binding.
- Import-cost assertions are expressed as *which modules a fresh subprocess
  imported*, which is deterministic, rather than wall-clock, which is not.
- The lazy accessors weaken static analysis slightly; `__all__` keeps the names
  declared, and a `TYPE_CHECKING`-guarded eager block can restore full checking
  at no runtime cost if a type checker ever needs it.
- This compounds with ADR-058: `_package_of` indexes `sys.modules`, so a
  smaller module table also makes each index build cheaper.

## References

- `solid_node/cli.py` — command registry and single-command resolution
- `solid_node/node/__init__.py`, `solid_node/simulation/__init__.py` — PEP 562
  export accessors
- `solid_node/node/base.py` — deferred `trimesh` and `.operations`
- `solid_node/core/loader.py` — deferred `TestCase`
- `tests/import_probe.py` — fresh-subprocess import reporting
- OpenSpec change `fast-cli-startup`, capability `cli-startup-cost`
