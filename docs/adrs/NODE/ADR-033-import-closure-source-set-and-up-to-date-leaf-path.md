# ADR-033: Import-Closure Source Set and the Up-to-Date Leaf Path

**Status:** Accepted
**Date:** 2026-07-31
**Extends:** [ADR-006: Mtime-Based STL Caching Strategy](./ADR-006-mtime-based-stl-caching-strategy.md)
**Amends:** [ADR-002: Template-Method Pattern for Node Lifecycle](./ADR-002-template-method-pattern-for-node-lifecycle.md)
**Affects:** [ADR-004: Multi-CAD Backend Adapter Pattern](./ADR-004-multi-cad-backend-adapter-pattern.md)

## Context and Problem Statement

ADR-006 established that an artifact is up to date iff its mtime equals
`node.mtime`, the maximum mtime across the source files that contributed
to it, and named "tracking transitive source file dependencies" as a
requirement. The implementation tracked one file: the module the node
class was defined in.

That is not the contributing set. In the v8-engine project both
`crankshaft.py` and `cylinder_unit.py` take their geometry from
`kinematics.py`, a module that defines no node. Editing a kinematics
function changed the model and moved no tracked mtime, so every artifact
went on reporting up to date. `Builder`'s watch loop consumes the same
set, so `solid develop` did not even notice the edit.

Independently, `assemble()` ran `render()` and `as_scad()` before
anything consulted `_up_to_date`, so the cache check could only ever
happen after the expensive work. Two adapters made that worse by
producing their artifact inside `as_scad()`: `CadQueryNode` exported
unconditionally and `JScadNode` spawned its external renderer
unconditionally, upstream of every guard. A no-op rebuild of v8-engine
cost 19.79 s against 19.83 s to build it from nothing — caching saved
approximately zero.

The two defects interact, which is why they are one decision. The
unconditional render is what kept a shared-module edit correct: geometry
was recomputed and re-exported even though no mtime had moved. Skipping
render on the old source set would have converted a slow-but-correct
build into a fast one that silently served a stale model.

## Decision Drivers

- solid-node's premise is one node per file, so that editing one file
  rebuilds one node. Dependencies aggregate upward: a leaf's edit
  invalidates the assemblies containing it and nothing sideways.
- A missing dependency is a worse failure than a spurious one. A stale
  model is wrong; an extra rebuild is merely slow.
- The framework cannot execute arbitrary project code to discover
  dependencies; discovery must be static and cheap.
- Whatever the build tracks, the watch loop watches. One set serves both.

## Considered Options

1. **Static import closure over project-local modules** (chosen)
2. Runtime inspection of a node module's `__dict__`
3. Content hashing instead of an extended mtime set
4. An explicit per-node declaration of extra source files

Option 2 fails on the common form: `from .kinematics import pin_center`
binds a function, not a module, so there is nothing in `__dict__` to walk
back to a file. Scanning all of `sys.modules` instead would attribute
every module the build ever imported to every node.

Option 3 solves a different problem — it would fix nothing here, because
the defect is *which* files are consulted, not how their state is read —
and it would replace ADR-006's mechanism wholesale.

Option 4 puts the burden on every project author and fails silently when
forgotten, which is the failure mode being removed.

## Decision Outcome

A node's tracked set is its own source plus the transitive closure of
the project-local modules that source imports. The closure is computed
from the AST and resolved through `sys.modules` — the interpreter has
already performed the import correctly, and relative imports, packages
and `__init__` chains are exactly the fiddly part not worth
reimplementing. Modules outside the working tree, and the framework
itself, are libraries and are not tracked.

**The walk follows only the modules a statement names; it never follows
the `__init__.py` of a package it traverses.** In the conventional layout
that file is the root assembly's own source and imports every node
beneath it, and Python executes it to resolve any relative import inside
the package. Following it would put every node's source in every node's
set, so a single edit would invalidate the whole project — the change
would defeat its own purpose. The cost is that a constant reached
*through* the package rather than through a named module is not tracked.
That import is a child depending on its parent, the one direction the
tree's upward aggregation cannot express, and the framework does not
support it.

A rigid, optimizing leaf whose `.stl` and `.scad` are both current
assembles by importing the artifact: `render()` and `as_scad()` do not
run. `self.model` is left unset and rendered lazily if a caller actually
asks for the scad. Internal nodes keep rendering, because an internal
node's file set is the union of its children's and it learns that only by
walking them — it cannot know whether it is current without doing the
work the answer would skip. The measured cost is leaf tessellation, so
that is where the win is.

The two adapters that produce artifacts inside `as_scad()` gained the
guard `generate_stl()` has always had, and it stays there independently
of the assemble-level skip: a node that opts out of optimization still
reaches `as_scad()` and should not rewrite a current artifact.

### Consequences

**Positive**

- The invalidation promise ADR-006 made is now kept. Editing
  `kinematics.py` invalidates exactly the artifacts of the nodes that
  import it, and no leaf that does not.
- `solid develop` watches imported modules, because it consumes the same
  set. That defect is fixed without touching the watch loop.
- v8-engine, measured on this change against its base commit:

  | Build | Before | After |
  |---|---|---|
  | Cold, nothing built | 19.83 s | 5.39 s |
  | No-op rebuild | 19.79 s | 3.22 s |
  | `kinematics.py` edited | 19.27 s | 3.00 s |
  | One leaf edited | 20.04 s | 3.73 s |
  | A test file edited | 18.93 s | 3.16 s |

  About 2.45 s of each figure is the bare interpreter plus framework
  imports. The cold build gains because the build runs several render
  rounds and only the first now has work to do.

**Negative**

- `assemble()` no longer calls `render()` exactly once per instance; it
  may call it zero times. ADR-002's lifecycle is amended accordingly.
  Anything depending on a render side effect is affected.
- The skip trusts the source set. A node whose geometry depends on
  something a static import walk cannot see — a data file read at
  runtime, a module reached through `importlib` or a computed name, an
  environment variable — can now look current when it is not. The
  unconditional render used to hide that. The boundary is stated rather
  than implied, and the closure over-approximates everywhere else.
- A leaf importing a sibling leaf's module tracks that node's source, so
  editing the sibling rebuilds both. Over-invalidation, correct and rare;
  under the one-node-per-file discipline shared values live in a module
  that defines no node.
- Existing build directories rebuild once, as the corrected set
  invalidates artifacts whose real dependencies had moved unnoticed.

## Validation

The suite had no CadQuery fixtures at all, which is why this survived
from v0.0.7 to here — `CadQueryNode.as_scad` is byte-identical across
those releases and the guard never existed. `tests/source_set_project/`
adds a CadQuery leaf and a project module that defines no node, and
`tests/test_source_set.py` covers both halves.

The gate for the skip is that a shared-module edit still rebuilds its
dependants. On v8-engine, after editing a `kinematics.py` function body
with no artifact identity change: at the base commit **no** artifact's
mtime advanced; with this change exactly ten did — the root assembly,
the crankshaft, and all eight cylinder units, every node that imports
kinematics, and no leaf that does not. Every generated `.scad` is
byte-identical between the two builds, and four of the five STLs are
byte-identical; `crank_throw` differs in bytes with identical volume,
face count and extents, which reproduces at the base commit when its STL
is regenerated from the same `.scad` — OpenSCAD's output is not
byte-stable, independently of this change.
