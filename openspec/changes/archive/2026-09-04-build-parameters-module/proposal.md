## Why

`Length`, `Angle`, `Count`, `Ratio`, `Scalar` and `Flag` are imported from
`solid_node.node`, the same package that exports every node base class. The
import line therefore says nothing about what these names are: a reader of
`from solid_node.node import CadQueryNode, Length` cannot tell that one of
them is a node kind and the other a knob on the machine being built.

The framework already groups its public surface by concern above the node
package — runtime inputs come from `solid_node.simulation`, the test case
from `solid_node.test` — and build parameters are the one authoring concern
still buried in the node namespace. Naming them their own module states what
they are at every import site and puts the distinction that matters next to
the one it contrasts with: parameters build the machine, drivers drive it.

Now, because the declarative parameter surface has not been released. It
exists only on the unmerged `declarative-node-api` line, so the move costs
one refactor of three in-workspace projects and no compatibility burden at
all. After a release it would cost a deprecation period.

## What Changes

- **BREAKING** A new module `solid_node.parameters` holds the declaration
  types and their algebra: `Quantity`, `Length`, `Angle`, `Count`, `Ratio`,
  `Scalar`, `Flag`, `Formula`, `Expression`, `declared_parameters`,
  `DimensionError` and `ParameterError`.
- **BREAKING** `solid_node.node` stops exporting `Quantity`, `Length`,
  `Angle`, `Count`, `Ratio`, `Scalar`, `Flag` and `declared_parameters`.
  Reading one off that package raises `AttributeError` like any other
  unknown name. There is no re-export and no deprecation shim: the goal is
  that an import site names the concern, and a second working path would
  defeat it.
- `solid_node.node.declarative` keeps the structure half — the child and
  repeat declarations, the declaring namespace, `NodeMeta`, realization,
  `StructureError`, `SidewaysReadError` — and imports the parameter half
  from the new module. The class-body authoring experience is unchanged:
  a declaration is still a class attribute, and the metaclass still names it.
- `solid_node.math` stops reaching down into `solid_node.node.declarative`
  for the formula algebra and imports it sideways from `solid_node.parameters`.
- The API reference gains a Parameters section, which it does not have today.
- The three workspace projects are migrated in the same change.

## Capabilities

### New Capabilities

(none — this changes where an existing capability's surface lives, not what
it does)

### Modified Capabilities

- `declarative-nodes`: the typed-parameter requirement states the module the
  kinds are imported from, which it does not state today.
- `cli-startup-cost`: the pinned `solid_node.node` export list loses the
  parameter names, and the new module is required to stay import-cheap.
- `user-documentation`: the declaring, CLI and API-reference pages show the
  parameter import from its own module.

## Impact

- `solid_node/parameters.py` (new), `solid_node/node/declarative.py`,
  `solid_node/node/__init__.py`, `solid_node/math.py`.
- Tests: `test_declarative_algebra`, `test_declarative_nodes`,
  `test_declarative_render`, `test_simulate_split`, `test_node_lazy_exports`,
  and the declarative test project.
- Docs: `declaring.rst`, `cli.rst`, `api-reference.rst`, `changelog.rst`,
  `architecture.md`.
- Projects: v8-engine, Inmoov-sim and Metamaquina2 on their `declarative-api`
  branches. Nothing outside this workspace imports these names.
