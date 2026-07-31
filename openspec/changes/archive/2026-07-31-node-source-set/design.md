## Context

Two ratified requirements are not met by the code. `build-pipeline`'s
`Mtime-equality caching` promises that any contributing source file invalidates
ancestor artifacts, but a node tracks only `{self.src}`. `node-model`'s
`Template-method render lifecycle` puts the up-to-date check after `render()`
and `as_scad()`, so the check can never prevent work.

Measured on `projects/v8-engine` (10 CadQuery leaves, 6 assemblies), on this
bench's base commit:

| Build | Time |
|---|---|
| Cold — no `_build`, everything rendered | 19.77 s |
| No-op rebuild — everything cached, zero renders | 20.86 s |
| Bare interpreter plus framework imports | ~2.45 s |

The cached rebuild is not cheaper than building from scratch. Cost is
tessellation in the project's own `render()`; `con_rod.py` and `piston.py`
deliberately pre-mesh at fine tolerance, and the adapter's export reuses that
cached triangulation, so the unguarded export is a small fraction of it.

## Goals / Non-Goals

**Goals:**

- A node's tracked source set includes the project modules its source imports,
  so editing `kinematics.py` invalidates the nodes that depend on it.
- An up-to-date leaf costs nothing beyond the staleness check.
- The two adapters that produce artifacts inside `as_scad` respect that check.
- Keep every currently correct build correct. Speed must not buy staleness.

**Non-Goals:**

- `solid sources` (publishing the set to an external watcher). This change makes
  the set trustworthy; exposing it is separate work.
- Skipping the tree walk for internal nodes — see D3.
- Tracking non-import dependencies: data files, `importlib`, environment. D5
  states that boundary rather than pretending to close it.
- Changing artifact identity, layout, publication, or the watch loop. The watch
  loop already consumes `node.files` and improves for free.

## Decisions

### D1 — Compute the import closure from the AST, resolving through `sys.modules`

For a node's defining module, parse its source with `ast`, collect `import` and
`from … import` targets, resolve each name against `sys.modules` (already
populated — the builder has imported the project), take each resolved module's
`__file__`, keep those inside the project tree, and recurse.

*Why AST rather than runtime inspection:* `from .kinematics import pin_center`
binds a function, not a module, so a node's `__dict__` cannot be walked back to
the file. Scanning all of `sys.modules` instead would attribute every module the
build ever imported to every node.

*Why resolve through `sys.modules` rather than reimplementing import
resolution:* relative imports, packages, and `__init__` chains are fiddly and
already resolved correctly by the interpreter that just did it. Reimplementing
that is the bug-prone part.

*Direction of error:* over-approximate. An extra file in the set costs an
unnecessary rebuild; a missing one serves a stale model. Every ambiguity
resolves toward including the file.

### D2 — Follow named modules only, never the package `__init__` chain

The walk adds the module a statement names. It does not add the `__init__.py`
of packages traversed on the way.

*Why this is essential, not an optimisation:* in the conventional project
layout `root/__init__.py` is the root assembly's own source, so it imports its
children and transitively every node beneath them. Python executes it when
resolving `from .kinematics import …` from anywhere in the package, so treating
package initialisation as a dependency would put every node's source in every
node's set. Every edit would invalidate everything, destroying the one-file-one-node
property this change exists to restore.

*Accepted consequence:* a node that reaches a constant through the package
(`from . import BANK_HALF`) rather than by naming a module does not track it.
This is the one place the walk deliberately under-approximates against D1's
rule, and it is principled: because the package `__init__` is the ancestor
node's source, that import is a child depending on its parent — the single
dependency direction that contradicts the tree's own invalidation model, where
files aggregate upward only. The framework does not support that shape; D5
records the boundary.

### D3 — Skip only at the leaf; internal nodes still walk

`LeafNode.assemble()` returns the imported artifact directly when the node is
rigid, optimizing, and up to date, skipping `render()`, `as_scad()`, and
`generate_scad()`. `InternalNode` keeps rendering.

*Why not skip internal nodes too:* an internal node's `files` is the union of
its children's, computed during their assemble (`internal.py:27`). It cannot
know whether it is current without walking the tree that answers the question.
A leaf can: its set is known at construction.

*Why that is enough:* the measured cost is leaf tessellation. Instantiating the
tree is cheap. This gets the win without a circular dependency.

*Consequence for the lifecycle:* `assemble()` no longer guarantees `render()` is
called once per instance — it may be called zero times. That is a ratified
scenario and the delta spec changes it explicitly rather than quietly.

*`self.model` when skipped:* left unset and computed lazily if anything asks.
It holds the node's own geometry for the `.scad` artifact, and the copy already
in the build directory is still valid — `BuildSession` carries it forward.

### D4 — Guard the adapters that produce artifacts inside `as_scad`

`CadQueryNode.as_scad` exports only when stale; `JScadNode.as_scad` spawns its
subprocess only when stale. Both still return `import_stl(self.local_stl)`.

*Why keep this once D3 skips the call anyway:* D3's skip requires `optimize`.
A non-optimizing rigid node still reaches `as_scad` and should not re-export a
current artifact. `generate_stl()` has always had exactly this guard; this makes
the two production paths consistent instead of one guarded and one not.

### D5 — State the boundary instead of implying completeness

The tracked set covers Python imports of project modules. It does not cover a
data file read at runtime, a module reached through `importlib` or a computed
name, or an environment variable that changes geometry. For those a node can
look current when it is not.

*Why accept this:* it is the same boundary `Builder`'s watch loop has always
had — it watches `node.files` too. This change does not widen the gap; it
closes the common case and names what remains. A project needing more can add a
file to the set explicitly.

## Risks / Trade-offs

- **The skip converts a slow-but-correct build into a fast one that trusts the
  source set.** If D1 misses a dependency, the maker sees a stale model instead
  of a slow one — a worse failure. → This is why the source set is fixed in the
  same change and why D1 over-approximates. The red-first test proving a
  shared-module edit rebuilds is the gate; without it the skip does not land.
- **Over-approximation could invalidate broadly** if a node imports a module
  that imports much of the project. → Bounded by D2. Worst case is today's
  behaviour: a rebuild.
- **A leaf importing another node's module** picks up that node's source, so
  editing the sibling rebuilds both. Over-invalidation, correct and rare.
- **`assemble()` no longer always renders**, so anything relying on a render
  side effect breaks. → The full suite plus new CadQuery fixtures are the check.
  There are none in the suite today, which is why this survived.
- **Build non-determinism already exists**: HEAD built twice produces differing
  bytes on `crank_throw`. Pre-existing and out of scope, but it means
  byte-identical output cannot be the only equivalence check — compare rendered
  artifact sets and geometry, and note the known-unstable node.

## Migration Plan

None required. No artifact layout, identity, or public API changes. A project
with an existing `_build` gets a correct incremental build on the next run;
worst case is one extra rebuild as the corrected source set invalidates
artifacts whose real dependencies moved earlier and went unnoticed.

## Open Questions

None blocking. Whether to expose the corrected set through `solid sources` is a
separate proposal that this change makes possible.
