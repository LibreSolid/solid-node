## Context

`solid_node/node/declarative.py` is 934 lines carrying two separable
concerns. The first is the parameter layer: a declaration descriptor, the
dimension algebra, `Quantity` and its five named kinds, `Flag`, formulas,
and enumeration off a class. The second is the structure layer: a node
constructed in a class body becoming a `ChildDeclaration`, `repeat`, the
declaring namespace, `NodeMeta`, and realization at construction.

The module imports nothing but `sys`. Every framework dependency runs the
other way: `base.py` imports the structure half, `math.py` reaches into it
for `Expression` and `function_formula`, and `solid_node/node/__init__.py`
routes eight public names to it through its lazy export map.

The parameter surface is unreleased. It exists on the unmerged
`declarative-node-api` line and is used by three projects in this workspace
and by nothing else.

## Goals / Non-Goals

**Goals:**

- A build parameter is imported from a module whose name says so.
- Exactly one import path per name. `solid_node.node` no longer answers for
  a parameter kind.
- The cut leaves both halves coherent, with the dependency running one way.
- No change to how a parameter is declared, resolved, checked or read.

**Non-Goals:**

- No change to the dimension algebra, the kinds, their constraints, or the
  formula evaluation.
- No compatibility shim, alias or deprecation path.
- No new parameter kind. The pilot has refused vector, text and choice
  kinds; that stands.
- No move of the structure half's public names. `declared_children` stays
  in `solid_node.node`.

## Decisions

### D1. A top-level module, not a submodule of the node package

`solid_node/parameters.py`, imported as
`from solid_node.parameters import Length`.

The alternative was `solid_node/node/parameters.py`. It was rejected
because the framework's public surface is already split by concern at the
top level and not inside the node package: `solid_node.simulation` holds
drivers and instructions, `solid_node.test` holds the test case. A build
parameter is a peer of those, so the import block of a typical node module
reads as three concerns rather than one bag and one aside:

    from solid_node.node import AssemblyNode, CadQueryNode
    from solid_node.parameters import Length, Flag
    from solid_node.simulation import Driver

The contrast the pilot asked to make visible — parameters build the
machine, drivers drive it — is exactly the contrast between the second and
third lines, and it is only visible when both sit at the same level.

The move also repairs an existing layering inversion: `solid_node/math.py`
is a top-level module that today imports from `solid_node.node.declarative`.
After the move it imports from a top-level peer.

### D2. The name is `parameters`

The framework's own word throughout: `declared_parameters`,
`ParameterError`, `resolve_parameters`, `parse_overrides`, and the whole
declaring page. Rejected alternatives: `knobs` (informal, and the shop uses
it for values rather than declarations), `dimensions` (a `Flag` has no
dimension, and `DimensionError` already means the physical kind), `build`
(collides with the STL build path), `spec` (collides with OpenSpec).

The module is named `parameters` rather than `build_parameters` because the
package qualifier already carries the domain: `solid_node.parameters` is
unambiguous, and `solid_node.build_parameters` reads as a stutter at every
import site.

### D3. The cut is at the child declarations

Moving to `solid_node/parameters.py`: `DimensionError`, `ParameterError`,
the dimension helpers, the reserved-name set, `Declaration`, `Expression`,
`Formula`, `function_formula`, `Quantity`, the coercions, `Length`,
`Angle`, `Count`, `Ratio`, `Scalar`, `Flag`, `declared_parameters` and its
cache.

Staying in `solid_node/node/declarative.py`: `StructureError`,
`SidewaysReadError`, `ChildDeclaration`, `RepeatDeclaration`, the
declaring namespace, `in_class_body`, `NodeMeta`, `declared_children`,
`is_declarative`, `resolve_parameters`, `identity_values`,
`realize_children`, `declared_child_nodes`, `parse_overrides`.

The boundary was chosen by following the existing dependencies rather than
by topic. Three names cross it and they all cross in the same direction,
structure importing parameters: `Declaration` (the declaring namespace
names any declaration, and `declared_children` filters on the type),
`Flag` (an operand `_evaluate` resolves), and the operand evaluator itself,
which the child and repeat declarations use to resolve a parent's tokens
into a child's arguments. Nothing in the parameter half needs a name from
the structure half, so `parameters.py` keeps `declarative.py`'s property of
importing only from the standard library.

`declared_parameters` moves and `declared_children` does not, even though
they sit side by side today with parallel caches. The rule the pilot set is
that a name about a build parameter is answered by the parameter module,
and enumerating a class's parameters is such a name. Splitting the pair
costs a duplicated four-line cache idiom and buys an unambiguous surface.

`resolve_parameters`, `identity_values` and `parse_overrides` stay. They
are node-construction and CLI-override machinery that happens to read
parameters; they are not the parameter vocabulary, and they are internal.

### D4. The evaluator becomes public to the package

`_evaluate(operand, values)` is renamed `evaluate` because it crosses a
module boundary: resolving a declared operand against an instance's bound
values is a service the parameter layer provides to the structure layer,
not a private detail. It is not added to `__all__`; the public surface of
the module is the kinds, the algebra types, the enumerator and the two
errors.

### D5. No shim, and the removal is enforced by a test

`solid_node/node/__init__.py`'s `_EXPORTS` map loses its eight parameter
entries, so `from solid_node.node import Length` raises `AttributeError`
through the existing unknown-name path. `test_node_lazy_exports` pins that
map against the module each name resolves from; it gains an explicit case
that the parameter names are gone, so a later re-export cannot be
reintroduced silently.

A shim was considered and rejected by the pilot. The surface is unreleased,
so no consumer outside this workspace can be broken, and a second working
path would defeat the only purpose of the move.

### D6. `solid_node.parameters` is eager, and stays cheap

The node and simulation packages resolve their exports lazily because they
reach backends that cost seconds to import. This module has no such
dependency: it imports `sys` alone, and it is on the import path of every
node module in every project. A lazy accessor here would add indirection
for no measurable gain, exactly as `StlRenderStart` is eager in the node
package for the same reason. The startup-cost spec gains a requirement that
importing it pulls in no framework module, so the property is pinned rather
than assumed.

## Risks / Trade-offs

- **Every project node module gains an import line** → Unavoidable and
  intended; that line is the change. The migration is mechanical and is
  done in this cycle for all three projects.
- **`declared_parameters` and `declared_children` no longer sit together** →
  The duplicated cache idiom is four lines. The docstrings on both name the
  other so a reader finds the pair.
- **A stale project on the old import raises `AttributeError`, not a
  message that says where the name went** → The three projects are migrated
  here and the surface is unreleased, so the only reader who can hit it is
  a reader of an unmerged branch. Adding a helpful `__getattr__` for the
  removed names is a shim by another name and was refused.
- **A merge of the earlier declarative branches after this one would
  resurrect the old imports** → The branches stack in order and the pilot
  integrates them in order; the export test fails loudly if the map comes
  back.

## Migration Plan

One commit for the framework move and the docs, then one commit per project
repository on its existing `declarative-api` branch. The projects are
migrated by subagents after the framework change is green, against the
worktree they already build against.

Rollback is the branch: nothing is pushed and nothing is released.
