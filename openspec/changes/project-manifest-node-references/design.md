# Design: project manifest and node references

This is the architectural decision for the cycle, written in ADR shape so that
extraction after implementation is mechanical. Target: **ADR-039, subsystem
BUILD**, superseding [ADR-005](../../../docs/adrs/BUILD/ADR-005-path-based-dynamic-module-loading.md)
(path-based dynamic module loading) and replacing the loader rules that
[ADR-026](../../../docs/adrs/NODE/ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md)
is cited for in the `build-pipeline` capability. ADR-026's own subject — artifact
identity as class plus parameters — is untouched.

## Context

A node is reachable today only by the path of the file that defines it, and a
file can define only one reachable node. Where those two facts do not hold, the
framework has a marker instead of an answer: `NODE = <Class>`, a module-level
variable the loader consults to decide which of several classes is "the" node.

The marker is a symptom. Its containment check reads

```python
project_root = os.path.realpath(os.getcwd())
```

which is the framework stating that it does not know where the project is. The
same substitution appears in `sys.path.append(os.getcwd())` and in
`source_closure`'s boundary. Every one of them is correct only while the caller
stands in the project directory, and nothing enforces that. From a
subdirectory, `source_closure` silently returns a smaller set than the truth,
which is a wrong answer rather than an inconvenience: the build then trusts
artifacts it should have rebuilt.

Two callers made this urgent. Agents need to snapshot a sub-assembly while
developing it, and cannot name one. The shop hardcodes the literal string
`"root"` in two places because there is nothing else to pass.

## Decision

### A project declares its root and its model

`[tool.solid-node]` in `pyproject.toml` carries `model`, an entry-point object
reference:

```toml
[tool.solid-node]
model = "dutch_windmill.dutch_windmill:DutchWindmill"
```

The project root is the directory holding the nearest ancestor `pyproject.toml`
carrying that table. Discovery walks up from the *reference* when the reference
names a path, and from the working directory only when there is no reference or
the reference is a qualifier, which carries no location. A path identifies a
project as surely as it identifies a file; keying discovery on the caller's
directory instead would reject a path in another project as foreign, and would
force any repository holding fixture projects to declare itself a project to
reach them.

That root — not `os.getcwd()` — anchors `sys.path`, the dotted module name of
any file loaded by path, `source_closure`'s boundary, and the project's build
directory. The build directory belongs on that list for the same reason as the
rest: the build lock is derived from it, so a build directory resolved against
the caller's cwd would give a command run from a subdirectory a private build
tree and a private lock, and mutual exclusion would hold per directory rather
than per project.

*Rejected: a dedicated `solid.toml` or a `[solid-node]` top-level table.* A
project already has `pyproject.toml`, because a solid-node project is a Python
package; a second manifest is a second thing to keep true. `[tool.*]` is where
PEP 518 puts tool configuration.

*Rejected: keeping a conventional path such as `root/__init__.py` or
`<project>/model.py`.* Every file in a solid-node project models something.
Naming one by its role rather than by what it models — `model.py`,
`root.py` — carries no more information than `pythonfile.py` would. The file is
named after the thing it models, and the root file after the whole product;
`dutch_windmill/dutch_windmill.py` repeats because the product's name is the
part's name, and `v8-engine/engine.py` does not repeat because it is not. The
manifest, not the filename, decides.

### A node is named by reference, in three interchangeable spellings

| Spelling | Example | Meaning |
|---|---|---|
| Qualifier | `dutch_windmill.windmill:Sail` | The class, from anywhere |
| Path | `dutch_windmill/windmill.py` | The single node class in the file |
| Hybrid | `dutch_windmill/windmill.py:Sail` | The class, tab-completably |

Parsing splits on the last `:`; the left side is a path when it ends in `.py` or
names an existing file, and a dotted module otherwise. A bare path resolves to
the one node class defined in the file and raises `AmbiguousNodeError` when
there are several — the same error as today, saying "name a class" instead of
"add a marker."

All three go through one resolver returning one class object. This is a
correctness requirement, not tidiness: `sources.py` resolves a module's file
through `sys.modules` and compares by identity, so a file imported under two
dotted names yields two distinct class objects and a corrupted dependency
closure.

The hybrid spelling exists because the packed file is exactly where tab
completion stops helping — the file name alone does not identify a node there.

*Rejected: qualifier only.* The path spelling is what an agent or a maker can
complete from the shell, and it is unambiguous for the overwhelming majority of
files.

*Rejected: enforcing one node per file, which would make the path spelling
always sufficient.* The rule does not deliver what it appears to. Invalidation
follows the import closure, not the file: `sail.py` and `cap.py` both importing
`dimensions.py` are invalidated together under perfect one-node-per-file
discipline. Co-residence in a file is one way to share an invalidation unit and
not the only one, so the rule buys a partial guarantee at the cost of forbidding
a reasonable way to write a model.

### `NODE` is removed rather than kept as a shorthand

Once a caller can name a class, a file never has to. The marker's only
defensible use — a package facade re-exporting a node defined in a sibling
module — was a workaround for an entry point that could not be named directly,
and disappears with it.

The containment check does not disappear. It becomes more necessary: a
qualifier can name any importable class, including one in site-packages, so
`solid snapshot solid_node.node.leaf:Leaf` is expressible for the first time. It
is re-anchored to the discovered root and keeps `inspect.getfile` as its test.

### Every companion `TestCase` runs, and may declare its node

The loader returns all `TestCase` classes in a companion file. A `TestCase` may
declare the node it exercises:

```python
class SailTest(TestCase):
    node = Sail
```

An undeclared `TestCase` binds to the node module's single node class. When that
module defines several and the `TestCase` is undeclared, the run fails with an
error naming the class. Every existing project keeps working, because every one
of them has a single node class per test file.

`solid test <qualifier>` runs that node's own `test_`-prefixed methods and the
`TestCase`s bound to it. `solid test <file>` runs every node in the file and
every `TestCase` in its companion.

*Rejected: a naming convention such as `<NodeClass>Test`.* It is guessable
rather than declared, and gives no error when it is not followed — the same
silence this cycle exists to remove.

*Rejected: leaving test resolution alone as pre-existing behaviour.* It is
pre-existing, but this cycle makes several node classes per file a supported
arrangement rather than an accident, and a silently unrun test reports success.
Nothing else in the framework fails that way.

## Consequences

- A command can be run from anywhere inside a project, and `source_closure`
  returns the same set wherever it is run from.
- `solid build` with no argument is the whole invocation; the shop's hardcoded
  `"root"` has something to become.
- An agent can snapshot any node it is working on, which is what ADR-021 asked
  for and could not express.
- Every project must gain a manifest. There is no fallback to `root/__init__.py`
  and no deprecation window; projects outside this repository migrate in their
  own cycle.
- A qualifier resolving to a class outside the project is refused, so the
  reference cannot become a way to run arbitrary installed code through the
  framework's loader.
- Packing several nodes into one file remains legal and still costs a shared
  invalidation unit. This cycle does not change that; it records it as a gap
  with the measurement that constrains the fix.
