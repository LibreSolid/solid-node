## 1. Baseline and red tests

- [x] 1.1 Record the baseline: `python -X importtime -c "import solid_node.cli"`,
      and timed `solid --help` / `solid viewer` in a project, so the change has
      a before/after figure.
- [x] 1.2 Add a helper that runs a snippet in a fresh subprocess and returns the
      set of imported top-level modules, following the shape of the existing
      `tests/mesh_engine_absent.py` isolation helper.
- [x] 1.3 Red: `import solid_node.cli` imports no `solid_node.manager.*` command
      module.
- [x] 1.4 Red: `solid viewer` imports neither `cadquery` nor `trimesh` and
      imports no node module, and still prints the same JSON and exits 0.
- [x] 1.5 Red: dispatching one command imports that command's module and no
      other command's module.
- [x] 1.6 Red: `import solid_node.node` does not import `cadquery`.
- [x] 1.7 Red: `import solid_node.node.base` does not import `trimesh`.

## 2. Lazy command dispatch

- [x] 2.1 Replace the eager `commands` list in `solid_node/cli.py` with an
      ordered name → (module, class) registry; keep command order for help.
- [x] 2.2 Resolve only the selected command in `manage()`: import its module,
      instantiate, add the shared `path` positional when `needs_node`, then
      `add_arguments`.
- [x] 2.3 Keep the pre-0.4 migration guard and unknown-command reporting
      working from names alone, with no command module imported.
- [x] 2.4 On the top-level help / no-subcommand path only, resolve every entry
      so `solid -h` renders each command's docstring exactly as today.
- [x] 2.5 Add the registry conformance test: every entry imports, instantiates,
      and exposes `__doc__`, `add_arguments`, and `handle`.

## 3. Lazy node exports

- [x] 3.1 Replace the eager re-exports in `solid_node/node/__init__.py` with a
      name → submodule table, `__all__`, and a PEP 562 module `__getattr__`
      that caches each resolution into `globals()`.
- [x] 3.2 Resolve submodule names through the same accessor, and add `__dir__`.
- [x] 3.3 Let a failing deferred import raise its own error naming the
      requested name, never an `AttributeError`.
- [x] 3.4 Keep `from .base import StlRenderStart` eager.

## 4. Deferred mesh library

- [x] 4.1 Move `import trimesh` from `solid_node/node/base.py` module scope
      into `cached_base_mesh`, leaving the cache keying and eviction untouched.
- [x] 4.2 Defer `base.py`'s module-scope `from .operations import ...`, which
      otherwise reaches `trimesh` through `node/operations.py`.
- [x] 4.3 Keep `trimesh` resolvable as an attribute of `solid_node.node.base`
      so `mock.patch('solid_node.node.base.trimesh.load')` works in isolation.

## 4b. Deferred test framework and simulation exports

- [x] 4b.1 Red: `import solid_node.core.loader` imports neither
      `solid_node.test` nor `cadquery`.
- [x] 4b.2 Red: a real `solid build` of a `Solid2Node`-only fixture project
      imports no `cadquery`.
- [x] 4b.3 Defer `from solid_node.test import TestCase` in
      `solid_node/core/loader.py` into `load_tests()`, its only use site.
- [x] 4b.4 Resolve `solid_node/simulation/__init__.py`'s exports on first
      access with the same PEP 562 accessor used for the node package, so
      reaching `simulation.enumeration` does not import `.scenario`.
- [x] 4b.5 Confirm companion-test discovery and `solid test` are unchanged.

## 5. Verification

- [x] 5.1 Turn every red test from group 1 green.
- [x] 5.2 Run the full framework suite and confirm no regression.
- [x] 5.3 Build a real OpenSCAD/`solid2`-only project and a CadQuery project
      end to end; confirm identical `_build` output and that only the CadQuery
      project's build imports `cadquery`.
- [x] 5.4 Re-measure 1.1 and record the before/after figures in the change.
- [x] 5.5 Confirm `solid -h`, `solid <command> -h`, the legacy-grammar exit
      code and message, and the unknown-command error are unchanged.
