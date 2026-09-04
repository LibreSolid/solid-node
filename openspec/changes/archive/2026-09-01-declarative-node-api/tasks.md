## 1. Red tests first

- [x] 1.1 Write `tests/test_declarative_algebra.py`: kinds, exponent rules, mismatch at class definition, closure, `sqrt` and degree-trig rules through `solid_node.math`, project-defined kind, `Scalar`/`.value` escape, `Flag` outside the algebra, comparisons refused — all failing on import of the new module
- [x] 1.2 Write `tests/test_declarative_nodes.py`: parameter defaults and reads, coercion, constraints, a parameter without a default failing at instantiation and not at class definition, refused assignment, shadow guard, enumeration, derived formulas, per-instance child realization, tokens by reference, literal lists, `repeat`, legacy child class, sideways read refused, root overrides, positional/unknown kwargs refused, identity scenarios including the migrated-class-keeps-its-key check against the existing `_build_uniq_id`
- [x] 1.3 Write `tests/test_declarative_render.py`: methodless grouping node, `render()` returning nothing under two keyframes (sweep), a returned list keeping its contract, a fusion positioning declared parts, `omit()` under an assembly and under a fusion, time-conditioned omission raising on the second keyframe, index stability, omitted subtree absent from build and serialized document, a leaf `render()` returning `None` still rejected
- [x] 1.4 Add the port-assignment scenario to `tests/test_ports.py`
- [x] 1.5 Add `--set` scenarios to the CLI and manager tests: parse by kind, constraint failure, unknown name, a node without a default loaded directly, and the develop loop carrying overrides into each rebuild
- [x] 1.6 Confirm every new test fails for the right reason before any implementation

## 2. The declaration layer (`solid_node/node/declarative.py`)

- [x] 2.1 `Quantity` base with a dimension mapping, `DimensionError`, and the formula tree with `+ - * /`, unary `-`, integer `**`, plain-number operands, `.value`, and comparison refusal
- [x] 2.2 Kinds `Length`, `Angle`, `Count`, `Ratio`, `Flag`, `Scalar` with optional defaults, `min=`/`max=`, coercion and constraint checking on resolved values, and the missing-value error at instantiation
- [x] 2.3 Formula mode in `solid_node/math.py`: `sqrt` and the trig names dispatch on tokens and formulas with their dimension rules, beside the numeric and symbolic modes
- [x] 2.4 The parameter data descriptor: token on the class, resolved value on the instance under a private slot, `__set__` raising, `__set_name__` shadow guard, `declared_parameters(cls)` with per-class cache; derived formulas wrapped into the same descriptor by the metaclass
- [x] 2.5 `ChildDeclaration`, `RepeatDeclaration` and `.repeat(count)`, literal-list support, sideways attribute read raising with the hoisting advice, `declared_children(cls)` with per-class cache
- [x] 2.6 `NodeMeta`: `__prepare__` hands the body a marked namespace whose presence on the stack is the class-body signal (a depth counter would stay stuck when a body raises, which the algebra does on purpose); declarations named as they are assigned; namespace scan for parameters, formulas and child declarations
- [x] 2.7 Realization helper: resolve kwargs (reject positional and unknown, list declared names), evaluate derived, coerce and check constraints, evaluate child arguments, construct children in declaration order into the instance `__dict__`

## 3. Wiring into the node classes

- [x] 3.1 `AbstractBaseNode`: adopt `NodeMeta`, `__new__` returning a declaration while a node class body executes, construction order per design D5, `uniq_id` from resolved declared values for declarative classes, `omit()`
- [x] 3.2 `adapters/cadquery.py`: derive `CheckCQEditor` from `NodeMeta`
- [x] 3.3 The render wrapper: `None` from an internal `render()` becomes the declared children minus the omitted, omission marks cleared before the author's `render()` and the omitted set recorded and checked afterwards; `AssemblyNode` keeps the animator sweep in the same wrapper and `FusionNode` subclasses get the wrapper too; base `InternalNode.render()` returns `None`
- [x] 3.4 `Port.__set__` binding through the same path as `connect()`
- [x] 3.5 Export the kinds, `Quantity`, `declared_parameters` and `declared_children` from `solid_node.node` and keep `tests/test_node_lazy_exports.py` honest about the new names

## 4. The command line

- [x] 4.1 `--set name=value` registered once beside the shared `reference` positional in `cli.add_command_parser`; a parser that turns the strings into overrides by consulting the root class's declared kinds, failing on an unknown or derived name with the settable list and on a root that declares nothing
- [x] 4.2 `load_node(reference, overrides)` constructing `klass(**overrides)`; every node-loading manager (build, develop, test, snapshot, export) and `Builder` carry the overrides; the develop loop passes them into each `Builder` it starts

## 5. Green and clean

- [x] 5.1 All new tests green; full `pytest` and `flake8 solid_node tests` green in the worktree
- [x] 5.2 Additivity evidence: run the v8-engine and windmill project suites (`solid test`) from their project directories against this worktree's framework and record the results unchanged
- [x] 5.3 Snapshot evidence for one declarative example (a repeated-unit assembly with an omitted member, built once at defaults and once with `--set`) inspected, not only counted

## 6. Documentation

- [x] 6.1 New user page `docs/declaring.rst` per the user-documentation delta; add it to the toctree and cross-reference it from `node-tree.rst`, `assemblies.rst`, `leaf-nodes.rst` and `cli.rst`
- [x] 6.2 `cli.rst` documents `--set`, parsing by kind and the no-default case
- [x] 6.3 Changelog entry under the unreleased section, including the one-time artifact re-keying note for classes that previously omitted a kwarg or passed an integer where a float kind now resolves
- [x] 6.4 Note beside `CheckCQEditor` that a node metaclass must derive from `NodeMeta`

## 7. Records (commit 2, after implementation is green)

- [x] 7.1 Extract ADRs for the consequential decisions (class-body declaration through the metaclass; typed parameters and the exponent algebra; identity from resolved declared values; an internal render that returns nothing, with structural omission stable across renders) into `docs/adrs/NODE/` as ADR-061 to ADR-064, update the ADR index and `docs/architecture.md`
- [x] 7.2 Sync delta specs into `openspec/specs/`, archive the change, run final tests and `openspec validate`
