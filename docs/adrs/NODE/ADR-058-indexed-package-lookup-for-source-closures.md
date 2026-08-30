# ADR-058: Indexed Package Lookup for Source Closures

**Status:** Accepted
**Date:** 2026-08-30
**Depends on:**
- [ADR-033: Import-Closure Source Set and Up-To-Date Leaf Path](./ADR-033-import-closure-source-set-and-up-to-date-leaf-path.md)
- [ADR-006: Mtime-Based STL Caching Strategy](./ADR-006-mtime-based-stl-caching-strategy.md)

## Context and Problem Statement

ADR-033 made a node's tracked source set its project-local import closure, so
that a module contributing a dimension invalidates the geometry that reads it.
Building that closure needs, for each file it parses, the package that file was
imported as, so relative imports can be resolved. `_package_of` answered that by
scanning `sys.modules` and calling `os.path.realpath` on every module's
`__file__` until one matched.

The answer is a property of the interpreter's module table. The *cost* of asking
was the product of two unrelated quantities: how many source files a project
has, and how many modules the process happened to import. Both grow — projects
get larger, and the framework's own dependency graph pulls in CadQuery, OCP,
trimesh, numpy and scipy.

On Metamaquina2 (567 nodes, 202 distinct source files) one load made 135 calls
over ~1 800 modules: **341 169 `realpath` calls, 3 463 099 `lstat` syscalls**.
`cProfile` attributed 21.8 s of 22.4 s of node construction to it. A no-op
`solid build` — one that renders nothing and logs "Published artifacts are
already current" — took 23–24 s, of which the maker sees every second twice per
project open, because the build and the snapshot each load the tree.

## Decision Drivers

- A node's source set decides its artifact currency (ADR-006). Any lookup that
  can return a superseded answer makes a stale artifact report itself current —
  the one failure mtime caching cannot survive.
- The interpreter is the correct authority for which package a file was imported
  as: it handles namespace packages, `__init__.py` packages, and files imported
  under a non-obvious module name alike.
- Node construction should not slow down as the framework imports more.
- The framework already has an established shape for caching a view of
  something mutable: a module-level dict keyed so a stale view is unusable
  rather than invisible (`_import_cache`, `_base_mesh_cache`).

## Considered Options

1. **Index the module table once, stamped on the exact set of module names**
   (chosen)
2. Index it, stamped on `len(sys.modules)`, rebuilding once on a miss
3. Derive the package from the filesystem layout instead of from `sys.modules`
4. Leave the scan and memoise `_package_of` per path

## Decision Outcome

Chosen: **an index of `realpath(module.__file__) -> module.__package__`, built
once and keyed on the exact set of loaded module names.**

`_package_of` takes `frozenset(sys.modules)` as the stamp, looks up the index
for that stamp, and rebuilds when the module set has changed. The cache holds
one entry, so it cannot grow. The index is built with `setdefault`, never
assignment: two modules can resolve to one real path, and the scan this replaces
returned the first one `sys.modules` offered.

Measured on Metamaquina2: `realpath` calls inside `_package_of` 341 169 → 2 635,
`lstat` 3 463 099 → 26 434, cold `load_node` 19.4 s → 4.8 s, and a no-op
`solid build` **23.4–24.3 s → 8.0 s**. The resulting tree is identical — 567
nodes, 39 512 closure entries, no disagreement in source closure, `mtime_ns` or
artifact path — and the sha256 of all 265 published artifacts is unchanged.

### Why not the length stamp (option 2)

It was implemented faithfully and still returns a stale answer. Rebuilding on a
*miss* cannot repair a stale *hit*: after a module is removed and another
imported, the length is unchanged, the path is still in the index, and the
lookup returns the old package where a fresh scan returns `None`.

This is not hypothetical. `loader.import_module_from_path` does exactly
remove-then-import when a name was loaded from a different project — a real
state in test runs and in a long-lived host like the shop floor.

The exact stamp costs ~30 µs per call, ~24 ms per load, about 1% of the new
`load_node`. Paying 1% to remove a silent source-set corruption is not a close
call.

### Why not derive the package from the filesystem (option 3)

It would remove the dependency on `sys.modules` entirely, but it re-derives
something the interpreter has already resolved correctly, and would have to
reproduce namespace-package and non-obvious-module-name semantics. A
performance fix is the wrong place to take on that risk.

### Why not memoise per path (option 4)

It fixes the repeat cost but not the first call for each of the 202 files, and
it needs the same staleness reasoning anyway. The index answers every path for
one scan instead of one path per scan.

## Consequences

- Node construction no longer scales with the size of `sys.modules`. The
  framework can import more without slowing every project load.
- `_package_of`'s time is no longer measurable in a `load_node` profile; the
  residual is subprocess wait, module import and enum construction.
- The correctness of a node's source set now depends on the stamp covering
  every mutation of `sys.modules` that could change an answer. The exact key set
  covers addition, removal and replacement. It does not cover a module whose
  `__file__` is reassigned in place without any name changing; nothing in the
  framework does that, and a test pins the late-import and first-wins
  properties the index could otherwise lose.
- Cost assertions in the test suite are expressed as call counts rather than
  wall-clock, so they are machine-independent and do not flake.

## References

- `solid_node/node/sources.py` — `_package_of`, `_index_loaded_modules`,
  `_package_index`
- `tests/test_source_closure_index.py` — cost, agreement, first-wins,
  late-import and miss behaviour
- OpenSpec change `fast-source-closure`, capability `source-closure-cost`
