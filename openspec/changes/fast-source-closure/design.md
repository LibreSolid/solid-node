## Context

`source_closure(src)` is called once per node from `AbstractBaseNode.__init__`
(`node/base.py:436`). It walks the project-local import graph, and for each
file it parses it calls `_package_of(path)` to learn the package that file was
imported as, so relative imports can be resolved.

`_parse_project_imports` is already correctly memoised on `(path, mtime)`, so
on Metamaquina2 it runs 135 times for 567 nodes. The cost is not repetition of
the parse — it is that each of those 135 calls asks `_package_of`, and
`_package_of` scans all of `sys.modules` calling `os.path.realpath` on every
module's `__file__`. 135 × ~1 793 modules = 343 877 `realpath` calls, each of
which walks its path component by component with `lstat`: 3 467 847 syscalls,
10.6 s of system time.

`_package_of` deliberately uses the interpreter as its oracle rather than
re-deriving a package name from the filesystem layout — "taken from the
interpreter, which has already done the resolution correctly". That decision is
sound and this change keeps it. The defect is only that it re-derives the
entire mapping on every question instead of once.

## Goals / Non-Goals

**Goals:**

- Identical source closures, `mtime_ns`, artifact paths, and currency
  decisions. This is a pure cost change.
- Remove the dependence of node construction on the size of `sys.modules`.
- Keep the interpreter as the authority on which package a file was imported
  as.

**Non-Goals:**

- Deriving a package name from the filesystem layout instead of from
  `sys.modules`. That would be a semantic change, and the current approach is
  correct for namespace packages, `__init__.py` packages, and files imported
  under a non-obvious module name alike.
- Changing `_parse_project_imports`'s existing `(path, mtime)` memoisation, the
  AST scan, or what counts as a project-local import.
- Anything about artifact currency, rendering, or publication.
- The CLI/backend import work parked in `fast-cli-startup`. That change shrinks
  `sys.modules` and so shrinks the index build; the two are independent.

## Decisions

### Invert the scan into an index of loaded modules

Build a `realpath(module.__file__) -> module.__package__ or None` mapping once
and answer each lookup from it. The mapping must preserve **first-wins** over
`sys.modules` iteration order, because that is what the current linear scan
returns when two modules resolve to the same real path — `setdefault`, not
assignment.

This turns 135 full scans into at most a couple of index builds per load.

### Correctness does not depend on the index being warm

The index is a cache of a mutable thing: `sys.modules` grows while a project
loads, because the loader imports project modules as it goes. A lookup for a
module imported after the index was built must still succeed, so the index
carries a stamp of the module set it was built from and is rebuilt when that
stamp no longer matches.

`len(sys.modules)` is the cheap stamp, but it is not sufficient on its own: a
module removed and another added leaves the length unchanged. Two mitigations,
either of which the implementation may take — decide with a measurement:

1. Stamp on the exact key set. Iterating ~1 800 dict keys costs tens of
   microseconds; even at one stamp per call that is milliseconds across a whole
   load, against the 10.6 s of syscalls being removed. Exact and simple.
2. Stamp on the length, and on a *miss* rebuild once and retry before
   concluding `None`, memoising the negative result under the current stamp so
   a genuinely absent path is not rescanned repeatedly.

**Settled by implementation: option 1, the exact key set.** The two measure the
same end to end on Metamaquina2 — within noise, one index build per load either
way — so cost did not decide it. Correctness did: option 2 was implemented
faithfully and still returns a stale answer, because a rebuild-on-miss cannot
repair a stale *hit*. After a module is removed and another added, the length is
unchanged, the path is still in the index, and the lookup returns the old
package where a fresh scan returns `None`.

That is not hypothetical here. `loader.import_module_from_path` does exactly
remove-then-import when a name was loaded from a different project, which is a
real state in test runs and in long-lived hosts like the shop floor. The exact
stamp costs ~24 ms per load — about 1% of the new `load_node` — against a
correctness failure that would silently corrupt a node's source set and, through
ADR-006, its artifact currency. That price is right.

A length-only stamp with no miss path is forbidden outright, and a length stamp
with one is rejected on the evidence above.

### Keep the module-level cache shape the framework already uses

`sources.py` already carries `_import_cache` as a module-level dict with
explicit stale-entry eviction, and `node/base.py` does the same for base meshes
(ADR-028). The index follows that established shape rather than introducing
`functools.lru_cache`, whose invalidation cannot be tied to `sys.modules`.

## Risks / Trade-offs

- **A stale index returns a wrong package, silently changing a node's source
  set** — the worst possible failure, because a wrong closure means wrong
  artifact currency and a stale model → the stamp must cover module
  *addition*, which is the only mutation that occurs during a load; the spec's
  "late import" scenario tests exactly this, and the full-tree equality test
  catches any drift on a real project.
- **First-wins ordering is easy to lose** — assignment instead of `setdefault`
  would flip which of two colliding paths wins → asserted directly by comparing
  the indexed answer against the linear scan for every loaded module file.
- **The index build itself is O(modules) with a `realpath` each** — unchanged
  per build, but it happens once or twice instead of 135 times; if a
  pathological caller forced a rebuild per lookup the change would be neutral,
  not worse.
- **The benchmark is one project on one machine** → the spec asserts the
  *shape* of the cost (path-resolution calls must not scale with the loaded
  module set), which is deterministic and machine-independent; the 40× figure
  stays in the proposal as motivation.
