## Why

solid-node's design premise is one node per file, so that editing one file
rebuilds one node. The `build-pipeline` capability already ratifies the
mechanism: an artifact is up to date iff its mtime equals `node.mtime`, the
maximum mtime "across all files tracked for the node", and "a change to any
contributing source file invalidates all ancestor artifacts".

The implementation does not deliver that, in two independent ways.

**A node's tracked source set is wrong.** `AbstractBaseNode.__init__` seeds
`self.files = {self.src}` — the node's own file and nothing else. Imports are
never tracked. In `projects/v8-engine`, `crankshaft.py` and `cylinder_unit.py`
both import geometry from `kinematics.py`, which defines no node. Editing a
kinematics constant changes the model and moves no tracked mtime, so every
artifact reports up to date. The ratified requirement says such a file is a
contributing source; the code cannot see it.

**Nothing is skipped even when the answer is known.** `assemble()` runs
`render()` and `as_scad()` before anything consults `_up_to_date`, so the only
check happens after the expensive work. A no-op rebuild of `v8-engine` — every
STL cached, zero renders launched, the log itself reporting `STL up to date` —
costs 20.86 s against 19.77 s to build the same project from nothing. Caching
saves approximately zero. Two adapters make it worse by producing their artifact
inside `as_scad`: `CadQueryNode` exports unconditionally and `JScadNode` spawns a
subprocess unconditionally, upstream of every guard.

These interact, and the interaction is why this must be one change rather than
two. Today the unconditional render is what keeps a shared-module edit correct:
the geometry is recomputed and re-exported even though no mtime moved. Fix the
skip alone and that correctness disappears — a fast build that silently serves a
stale model. Fix the source set alone and builds stay slow. Only together do
they produce what the spec already promises.

This was never a regression. `CadQueryNode.as_scad` is byte-identical from
`v0.0.7` to HEAD and the guard has never existed there. The defect stayed
invisible because its cost is per-CadQuery-leaf: `dutch-windmill` sits at the
2.45 s interpreter floor and always has. `v8-engine` is the first model heavy
enough to expose it.

## What Changes

- A node's tracked source set becomes its real one: the node's own source plus
  the project-local modules that source transitively imports. Files outside the
  project and standard or third-party libraries stay untracked.
- An up-to-date rigid node with `optimize` set skips `render()` and `as_scad()`
  entirely rather than performing them and discarding the result. **BREAKING**
  for the ratified lifecycle: `assemble()` no longer calls `render()` exactly
  once per instance in every case.
- `CadQueryNode.as_scad` and `JScadNode.as_scad` produce their artifact only
  when it is stale, matching the guard `generate_stl()` has always had.
- The build gains the evidence that the shop's model watcher needs, and the
  same corrected source set is what a later `solid sources` command would
  publish. That command is **not** part of this change.

## Capabilities

### New Capabilities

None. Both affected behaviours are already specified; this change makes the
implementation conform and tightens two requirements that were loose enough to
permit the defect.

### Modified Capabilities

- `build-pipeline`: `Mtime-equality caching` says "all files tracked for the
  node" without saying what a node is obliged to track, which the current
  single-file set technically satisfies. State the obligation: a node's tracked
  set SHALL include the project-local modules its source imports, transitively.
- `node-model`: `Template-method render lifecycle` ratifies
  render → validate → `as_scad` → … → optional optimized import, with the
  up-to-date check last. Reorder it: when the artifact is current, the node
  imports it without rendering. Its `Multi-backend leaf adapters` requirement
  gains the obligation that an adapter not produce its artifact when current.

## Impact

- `solid_node/node/base.py` — source-set construction and the `assemble()`
  lifecycle.
- `solid_node/node/leaf.py` — the up-to-date leaf path.
- `solid_node/node/adapters/cadquery.py`, `adapters/jscad.py` — export guards.
- `tests/` — there are no CadQuery fixtures in the suite at all, which is why
  this survived; the change adds them.
- Consumers of `node.files` benefit without changing: `Builder`'s watch loop
  watches exactly this set, so it stops missing edits to imported modules.

Risk concentrated in one place: a node whose geometry depends on something the
import walk cannot see — a data file read at runtime, a module reached by
`importlib`, an environment variable — becomes stale-prone in a way the current
unconditional render hides. `design.md` settles how the walk is computed and
what it deliberately does not promise.
