## MODIFIED Requirements

### Requirement: The declarative authoring surface is documented

The documentation SHALL include a page on declaring a machine that covers
the three layers of a value (parameter, constant, port), the parameter
kinds and the dimension algebra including the `solid_node.math` functions,
derived formulas, class-body child declarations, literal lists and
`repeat`, a class-body list comprehension over module-level values, an
internal `render()` that positions and returns nothing, `omit()`, root
overrides from Python and from `--set` on the command line, a parameter
without a default, `check()` for guards over several parameters, where
placement goes — stationary parts once in `__init__` after
`super().__init__(**kwargs)`, moving parts in `render()`, stated as the
recommendation for now — and the two pitfalls: class-level names are
invisible to a class-body comprehension, and structure that depends on
time. It SHALL state that a driver cannot be qualified on a repeated or
list-held child and that ports are the drive path for identical units. The
node-tree, assemblies, leaf-node and CLI pages SHALL cross-reference it,
and the changelog SHALL record the capability with the one-time artifact
re-keying note for migrated classes.

#### Scenario: A reader replaces an `__init__`

- **WHEN** a reader who knows the constructor form looks up how to declare
  a leaf's parameters
- **THEN** the page shows the declared form beside the constructor form it
  replaces, states that identity is derived by the framework, and shows the
  value read back as a plain number in `render()`

#### Scenario: A reader repeats a unit

- **WHEN** a reader needs eight identical parts placed differently
- **THEN** the page shows `repeat` with per-unit placement in `render()`
  through `enumerate` and constants, states that the units share one
  artifact, and warns that a class-body list comprehension cannot see
  class-level names while one over a module-level table declares

#### Scenario: A reader guards two parameters against each other

- **WHEN** a reader has a rule that one declared dimension must exceed
  another
- **THEN** the page shows `check()` raising for the bad pair, states when
  the framework calls it and that a refused instance realizes no child,
  and that it is not called on a class that declares nothing

#### Scenario: A reader places a stationary part

- **WHEN** a reader migrating a class asks where a once-only placement goes
- **THEN** the page shows `__init__(self, **kwargs)` calling
  `super().__init__(**kwargs)` and then placing, states that the children
  are realized by then, keeps `render()` for what moves, and marks the
  arrangement as the recommendation for now

#### Scenario: A reader varies a design from the shell

- **WHEN** a reader wants to build the model at another size
- **THEN** the CLI page shows `--set name=value`, how a value is parsed by
  its kind, and what happens for a parameter with no default
