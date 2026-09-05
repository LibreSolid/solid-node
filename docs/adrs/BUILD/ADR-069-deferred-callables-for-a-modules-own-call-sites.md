# ADR-069: Deferred Callables for a Module's Own Call Sites

**Status:** Accepted
**Date:** 2026-09-05
**Extends:**
- [ADR-059: Import at the Point of Use](./ADR-059-import-at-the-point-of-use.md)

**Related to:**
- [ADR-052: Conditional Mesh-Engine Dependency](../TEST-FRAMEWORK/ADR-052-conditional-mesh-engine-dependency.md)
- [ADR-067: Fresh-Interpreter Build Subprocesses](./ADR-067-fresh-interpreter-build-subprocesses.md)

## Context and Problem Statement

ADR-059 removed the CAD stack from `solid` startup, but one path survived it:
`solid_node/test.py` imported seven names from `solid_node.exact` at module
scope, and `solid_node.exact` imports cadquery at module scope. Discovering or
running any test therefore paid for the exact-geometry stack, whether or not a
single comparison used it.

Measured on a development workspace: `import solid_node.test` took 2.84 s, of
which 1.52 s was cadquery; the framework's own suite spent roughly 150 s of its
269 s there, and every project's `solid test` paid 2.8 s before reading
anything.

ADR-059's mechanism does not reach this case. PEP 562's module `__getattr__` is
consulted only for *attribute* access on the module object — `mod.name` from
outside. It is not consulted for a global-name lookup inside the module's own
functions. The five call sites in `test.py` are ordinary global reads, so an
`__getattr__`-based deferral leaves them raising `NameError` until something
outside the module happens to touch the attribute first. This was verified
empirically before the design was changed, not reasoned about.

## Decision Drivers

- No observable change: the same verdicts, the same errors, the same public
  surface. A broken exact backend must still raise its own `ImportError`.
- The five call sites must keep reading as ordinary calls. Rewriting each into
  a local import inside its function scatters the decision across the file and
  invites the next call site to forget it.
- `mock.patch('solid_node.test.intersect_shapes', ...)` is load-bearing in the
  suite and must keep working, both before and after the first real use.

## Considered Options

1. **Module-scope deferred callables that resolve and replace themselves**
   (chosen)
2. Module `__getattr__`, as ADR-059 used for package re-exports (rejected: does
   not serve the module's own call sites — the defect above)
3. A local `from solid_node import exact` inside each of the five functions
4. Move the exact comparison path into its own module, imported on demand

## Decision Outcome

Chosen: **module-scope deferred callables.**

Each of the seven names is bound at module scope to a small wrapper. On first
call the wrapper imports `solid_node.exact`, resolves the real callable, and —
only if the global still holds the wrapper itself — rebinds the global to the
resolved object before calling through. Later calls reach the real callable
directly, at no wrapper cost.

The identity guard is what keeps patching honest in both directions. Patching
before first use replaces the wrapper, so the resolution never overwrites the
patch; patching after first use replaces an already-resolved name, exactly as
it always did.

### Why not a local import per call site (option 3)

It works, but it puts the same four lines in five places and states the
decision nowhere. The wrapper states it once, at the top of the file, where the
`from ... import` it replaces used to be.

### Why not a separate module (option 4)

The exact and faceted paths share the broad phase, the caches, and the
`IntersectionStats` contract. Splitting them to move an import trades a real
cohesion for a mechanical one.

## Consequences

- `import solid_node.test` falls from 2.84 s to 0.79 s, and the framework's own
  suite from 269.2 s to 179.1 s. A faceted-only project runs its whole suite
  without cadquery entering `sys.modules`.
- **Before its first use, an exported name is a wrapper, not the object.**
  `solid_node.test.fuse_shapes is solid_node.exact.fuse_shapes` is False until
  something calls it. Nothing in the framework depends on that identity, but it
  is a real difference from the eager import and is pinned by a test.
- A broken exact backend now surfaces on first *use* of a kernel name rather
  than at import of `solid_node.test`. Three tests that read the failure
  through `solid_node.simulation.ScenarioTest` — a chain this removes — were
  re-pointed at that use site.
- This does not make ADR-067's spawn fix any less necessary, and must not be
  read as making it so. ADR-067 rejected "drop the parent-side import" for the
  right reason: the hazard is that ANY parent-side import touching geometry
  re-arms a fork deadlock, and nothing at the fork site can see that it
  happened. This removes one such import for cost reasons. The next one is
  still structurally possible, and the explicit spawn context is what makes it
  harmless.
- ADR-059 is not superseded. Its `__getattr__` remains right for package
  re-exports, where every access really is an attribute access from outside.
  The two mechanisms answer two different questions, and this ADR records which
  one applies where.

## References

- `solid_node/test.py` — `_deferred_exact` and the seven bound names
- `tests/test_lazy_test_framework.py` — import-cost and patchability tests
- `tests/import_probe.py` — fresh-subprocess import reporting
- `spike/interference/FINDINGS.md` — finding 1
- OpenSpec change `fast-test-feedback`, capability `cli-startup-cost`
