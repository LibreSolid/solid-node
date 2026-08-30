## Why

Loading a real project's node tree is dominated by filesystem path
resolution that repeats the same work once per node.

Measured on Metamaquina2 (567 nodes, 96 published artifacts, every artifact
already current so nothing is rendered):

| phase of a no-op `solid build` | measured |
| --- | ---: |
| framework imports | 2.6 s |
| **`load_node`** | **15.3 s** |
| `assemble` | 0.4 s |
| serialize + piece inventory | 1.5 s |

`cProfile` attributes 21.8 s of the 22.4 s spent constructing nodes to
`solid_node/node/sources.py:101`:

```python
def _package_of(path):
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and os.path.realpath(filename) == path:
            return getattr(module, '__package__', None) or None
```

Every call rescans all of `sys.modules` — 1 793 modules once the CAD stack is
loaded — and calls `os.path.realpath` on each one's `__file__`. Across one
load that is 343 877 `realpath` calls producing **3 467 847 `lstat`
syscalls**: 10.6 s of syscall time plus 3.0 s of path joining.

The cost is quadratic in the wrong pair of things. It scales with the number
of source files a project has *times* the number of modules the interpreter
happens to have imported, so it grows both as a project grows and as the
framework's own dependency graph grows — while the answer it computes is a
property of neither loop iteration count.

Replacing the scan with an index built once removes essentially all of it.
Measured cold, in a fresh process:

| | before | after |
| --- | ---: | ---: |
| `load_node` (excluding framework imports) | 15.5 s | 2.6–2.9 s |
| cold `load_node` including imports | 19.4 s | 4.8 s |
| **a no-op `solid build`, wall clock** | **23.4–24.3 s** | **8.0 s** |
| `realpath` calls inside `_package_of` | 341 169 | 2 635 |
| `lstat` calls inside `_package_of` | 3 463 099 | 26 434 |

The resulting node tree is identical: 567 nodes, 202 distinct source files,
39 512 closure entries, with no disagreement in `src`, source closure,
`mtime_ns`, or artifact path — and the sha256 of all 265 published artifacts
is unchanged.

The residual `load_node` time is not the lookup: profiling the indexed
version shows a subprocess wait, module import, and enum construction, with
0.195 s of `lstat` left. The lookup is no longer measurable.

This is paid twice per project open on the LibreSolid Studio floor, because
`solid build` and `solid snapshot` each load the tree.

## What Changes

- The package-of-a-file lookup that `source_closure` depends on resolves
  through an index of loaded modules built once and reused, instead of a
  linear rescan with a `realpath` per module per call.
- The index is rebuilt when the set of loaded modules changes, so a module
  imported after the index was built is still found. Correctness never
  depends on the index being warm.
- No change to what a node tracks: the same source closure, the same
  `mtime_ns`, the same artifact currency decisions, the same published
  document. This is a pure cost change.

## Capabilities

### New Capabilities

- `source-closure-cost`: what resolving a node's source closure is permitted
  to cost — the answer is identical to today's, and the filesystem work does
  not scale with the number of modules the interpreter has loaded.

### Modified Capabilities

None. The `build-pipeline` requirement that "the loaded file and the selected
class's project-local implementation and import closure SHALL all contribute
to the node's tracked source set" holds unchanged, and so does every
artifact-currency behaviour built on it (ADR-006, ADR-033, ADR-050).

## Impact

- `solid_node/node/sources.py` — the package lookup and its cache.
- Every node-scoped command benefits, because all of them construct the node
  tree: `build`, `develop`, `test`, `snapshot`, `export`.
- No dependency, CLI, or public API change.
- Interacts with the parked `fast-cli-startup` cycle only favourably: that
  change shrinks `sys.modules`, which shrinks the scan this change removes
  outright. Neither depends on the other.
- Downstream: LibreSolid Studio's floor, where this is the largest single
  framework-side cost of opening an already-built project.
