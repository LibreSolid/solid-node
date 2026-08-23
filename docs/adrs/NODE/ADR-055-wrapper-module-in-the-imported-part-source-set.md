# ADR-055: The wrapper module joins an imported part's tracked source set

**Status:** Accepted

**Date:** 2026-08-23

**Change:** `stl-node`

**Depends on:**
- [ADR-006: Mtime-based STL caching](ADR-006-mtime-based-stl-caching-strategy.md)
- [ADR-033: Import-closure source set and the up-to-date leaf path](ADR-033-import-closure-source-set-and-up-to-date-leaf-path.md)
- [ADR-050: Nanosecond-fidelity artifact freshness](ADR-050-nanosecond-fidelity-artifact-freshness.md)
- [ADR-054: An imported mesh is admitted, selected and corrected explicitly](ADR-054-imported-meshes-admitted-selected-and-corrected-explicitly.md)

## Context and Problem Statement

A node's artifacts are fresh exactly while their mtime equals the maximum
mtime over `node.files` (ADR-006/050), and that set is the node's own source
plus the project-local modules it imports, transitively (ADR-033).

For a leaf whose source is not a `.py` file, the closure has nothing to walk:
`source_closure()` returns the file itself and stops, because
`_parse_project_imports` cannot parse a `.js` or an `.stl`. That is exactly
right for `JScadNode` — a `.js` file *is* the whole of the part's geometry,
and the python wrapper carries nothing but the declaration.

It is wrong for `StlNode`. Its wrapper module carries geometry: the `body`
index that decides which part of a pack this is, and the `adjust` hook that
scales, mirrors or reframes the mesh before it is written (ADR-054). Tracked
like a `JScadNode`, an imported part would report up to date after its
`adjust` hook was rewritten, and every artifact above it would serve the old
geometry — the exact failure ADR-033 exists to prevent, reintroduced through
a new door.

## Decision Drivers

- Freshness must follow *everything that decides the geometry*, whatever kind
  of file that lives in.
- `sources.py` states its posture already: the closure is deliberately an
  over-approximation, because an extra tracked file costs a rebuild while a
  missing one serves a stale model.
- The rule should be local to the leaf that needs it; nothing else in the
  build pipeline should have to learn about mesh wrappers.
- Corrections are frequently expressed with a constant from a shared
  dimensions module, so tracking the wrapper alone would leave the same hole
  one level up.

## Considered Options

1. **The node extends its own `files` with the closure of its wrapper
   module** (Chosen)
2. Teach `source_closure()`/`_parse_project_imports` to find the python
   module wrapping a non-python source
3. Track only the mesh file, as the other external-file adapters do, and
   document that editing the wrapper needs a manual rebuild

## Decision Outcome

Chosen option: **`StlNode.__init__` calls `source_closure()` on the module
that defines the subclass and unions the result into `self.files`.**

The set therefore holds the mesh file, the wrapper `.py`, and — transitively
— the project-local modules that wrapper imports, so a constant an `adjust`
hook scales by is tracked as surely as the mesh itself. Editing any of them
moves `mtime_ns`, the artifact stops reporting current, and the part is
rebuilt with the correction applied.

The node is the right place for this knowledge because it is the only place
that has it. The source walk sees a path; it cannot know which python module
wraps a given mesh, and inventing a convention (same basename? same
directory?) would make it guess. The node knows its own class, and therefore
its module, exactly.

This also makes the admission gate of ADR-054 sufficient at materialization
time. `require_watertight` lives in the wrapper, so flipping it invalidates
the artifact and re-runs the check on the next build; nothing has to
re-validate an artifact that is already on disk.

The rule is stated under the `stl-import` capability rather than as a change
to `build-pipeline`: it adds files to one node's tracked set, which the
track-more-rather-than-fewer posture already permits.

## Pros and Cons of the Options

### The node extends its own files with its wrapper's closure

- **Good**: Every input that decides the geometry is tracked, including
  constants reached through an import
- **Good**: Local to the adapter that needs it; no other leaf's behaviour
  changes
- **Good**: Uses the existing closure wholesale rather than a second,
  parallel notion of "related file"
- **Bad**: A node's tracked set is now assembled in two places — the base
  class and this adapter
- **Bad**: An edit anywhere in a wrapper module rebuilds every part declared
  in it, even the ones the edit did not touch

### Teach the source walk about wrappers

- **Good**: One rule, applying to every external-file adapter at once
- **Bad**: The parser is given a path, not a class; recovering the wrapping
  module from a mesh path requires a naming convention it would have to guess
- **Bad**: Would also pull `JScadNode` wrappers into the set for no reason,
  since a `.js` leaf's wrapper carries no geometry

### Track only the mesh file

- **Good**: Nothing to add; identical to the existing external-file leaves
- **Bad**: Editing an `adjust` hook or a `body` index would leave every
  artifact reporting up to date, serving geometry the source no longer
  describes
- **Bad**: "Remember to rebuild manually" is the failure ADR-033 was written
  to end

## Consequences

Freshness is now correct for a leaf whose geometry is decided partly by a
foreign file and partly by python code. The cost is coarse invalidation
inside one module: declaring ten imported parts in one `parts.py` means an
edit to any of them rebuilds all ten. That is the over-approximation
`sources.py` already chose deliberately, and the remedy — one module per
part, or per group of related parts — is the layout projects already use.

A future adapter whose python wrapper likewise carries geometry-affecting
code should do the same thing, in the same place.

## References

- `solid_node/node/adapters/stl.py` — `StlNode.__init__`
- `solid_node/node/sources.py` — `source_closure()` and its
  over-approximation posture
- `tests/test_stl_node.py` — `StlSourceDeclarationTest`: the wrapper is
  tracked, editing it invalidates, and a module it imports is tracked too
- `openspec/changes/stl-node/`
