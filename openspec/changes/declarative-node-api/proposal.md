## Why

Defining a node tree today repeats every parameter three times — in the
`__init__` signature, as `self.x = x`, and in the `super().__init__()` call —
and the third repetition is load-bearing: `uniq_id` hashes over exactly what
reaches `super().__init__()`, so a forgotten kwarg silently gives two
different parts one artifact. The v8-engine and windmill projects show the
cost: 99 `__init__` definitions across two projects, derived dimensions
frozen as comment-documented constants (`PISTON_DIAMETER = 29.4  # bore −
2 × 0.3`), a hand-rolled root-parameter dataclass with 27 validity checks and
`as_kwargs()` plumbing, and eight geometrically identical cylinder units
hashing to eight artifacts. solid-node is meant to be parametric, and this is
the step that makes a design parametric for a maker, not only for a Python
caller. The pilot settled the shape in the shop's design reference
(`docs/new-declarative-api.md` in libresolid-studio) and resolved its open
points in the discussion of 2026-09-01 that this proposal records.

## What Changes

- **Typed parameter declarations** on node classes: `Length`, `Angle`,
  `Count`, `Ratio`, `Flag` and the unchecked `Scalar`, each with an optional
  default and value constraints (`min=`, `max=`) checked at instantiation.
  A declaration without a default is supplied by the parent, or by the
  command line for a root; instantiating without a value raises naming the
  class and the parameter. Read on an instance they are plain Python
  values; assignment is refused; they are enumerable off the class like
  ports and drivers.
- **A dimension algebra** over declared parameters: a quantity is a vector of
  dimension exponents; multiplication and division combine them, addition
  and comparison require equal exponents, and a mismatch fails at class
  definition, on `import`. `sqrt` and degree trigonometry take part through
  the existing `solid_node.math` functions, with their own dimension rules.
  Dimensions only, no unit conversion. Extensible by subclassing a kind with
  its own exponents.
- **Derived parameters** as bare class-body formulas over declared tokens
  (`piston_diameter = bore - 2 * wall_clearance`).
- **Class-body child declarations**: a node constructed inside a node class
  body is a declaration, not an instance. Each parent instance realizes its
  own children at construction, top-down from the root's bound values, with
  tokens passed by reference. Literal lists of declarations and
  `.repeat(count)` for count-many identical units, named `<attr>-<index>`
  without renumbering. Reading a parameter off a sibling declaration is
  refused with advice to declare it on the parent.
- **Realization at the root**: `Engine()` realizes with defaults (what
  `load_node` already does); `Engine(bore=32.0)` rebinds the root and every
  derived value and child follows. Unknown keywords and positional arguments
  are rejected on a declarative class.
- **Root parameters from the command line**: every command that loads a
  node accepts `--set name=value`, applied to the root, parsed by the
  declared kind and checked by the declared constraints, and carried through
  the develop loop's reloads.
- **Framework-owned identity** for declarative classes: `uniq_id` is the
  class plus the resolved declared parameter values, so the forgotten-kwarg
  collision cannot happen. Repeated identical units share one identity and
  one artifact.
- **`render()` that returns nothing.** `render()` stays the one method.
  On an internal node it now only positions and selects: when it returns
  `None`, the children are the realized declared children in declaration
  order minus those it omitted with `omit()`. A pure grouping node needs no
  `render()` at all. A `render()` that returns a list keeps today's contract
  exactly. Structure may vary with parameters, never with time: a render
  whose omitted set differs from the instance's first render raises. The
  rename of `render()`, `assemble()` and `shape()` into workshop verbs is a
  breaking refactor the pilot has deferred.
- **Port assignment binds**: `unit.crank = expression` on a declared port is
  the same binding `connect()` performs, scale applied. `Port` becomes a data
  descriptor so an assignment can no longer silently shadow a declaration.
- **Additive migration**: nothing in the existing `__init__`/`render()`
  contract changes for classes that do not declare.

Deliberately out of this change: publishing declared parameters in the
serialized document (a later cycle, once a consumer exists), cross-parameter
assertions, an enumerated `Choice` kind (it appeared in the reference but was
never ratified; `Flag` is the only selector), and migrating the evidence
projects (a shop-floor job after this integrates).

## Capabilities

### New Capabilities
- `declarative-nodes`: typed parameter declarations and their dimension
  algebra, derived parameters, class-body child declarations with lists and
  `repeat`, realization order and root overrides, framework-derived identity,
  `render()` returning nothing, `omit()`, and structural stability across
  renders.

### Modified Capabilities
- `node-model`: the composite-tree requirement admits an internal `render()`
  that returns nothing, meaning the declared children minus the omitted; the
  parameter-hashed identity requirement gains the declarative form, identity
  from the class plus resolved declared values.
- `ports`: per-render causal binding gains the assignment form; a port
  declaration refuses to be shadowed by an instance attribute.
- `cli`: every node-loading command accepts root parameter overrides.
- `user-documentation`: the declarative authoring surface is documented.

## Impact

- `solid_node/node/`: a new `declarative.py` (kinds, algebra, formulas,
  parameter and child declarations, the node metaclass, realization);
  `base.py` (metaclass, construction order, identity for declarative
  classes, `omit()`); `internal.py`, `assembly.py`, `fusion.py` (the
  `None`-returning `render()` and the omitted-set check); `ports.py`
  (`__set__`); `adapters/cadquery.py` (`CheckCQEditor` derives from the node
  metaclass); `__init__.py` (exports). `solid_node/math.py` gains formula
  awareness beside its numeric and symbolic modes.
- `solid_node/cli.py`, `core/loader.py`, `core/builder.py` and the
  managers that load a node (build, develop, test, snapshot, export) carry
  the override flag.
- Tests: new red-first suites for the algebra, declarations, realization,
  identity, `render()` returning nothing, omission, repetition, port
  assignment and the CLI flag; the existing suite must pass unchanged, and
  the v8-engine and windmill project suites are the additivity evidence.
- Documentation: a new user page for declaring a machine, cross-referenced
  from the node-tree, assemblies, leaf-node and CLI pages, and a changelog
  entry with the one-time artifact re-keying note.
- Shop follow-ups outside this repository: `shop-skills/solid-node-api/SKILL.md`
  currently instructs authors to create children in `__init__` and never as
  class attributes, which this change reverses for declarative classes; the
  originating projects migrate on a shop floor afterwards.
