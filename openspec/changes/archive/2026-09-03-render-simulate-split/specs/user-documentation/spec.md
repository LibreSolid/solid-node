## MODIFIED Requirements

### Requirement: The declarative authoring surface is documented

The documentation SHALL include a page on declaring a machine that covers
the three layers of a value (parameter, constant, port), the parameter
kinds and the dimension algebra including the `solid_node.math` functions,
derived formulas, class-body child declarations, literal lists and
`repeat`, a class-body list comprehension over module-level values, an
internal `render()` that positions and returns nothing, `omit()`, root
overrides from Python and from `--set` on the command line, a parameter
without a default, `check()` for guards over several parameters, the
lifecycle split — `render()` builds the machine at rest and places what
does not move, `simulate()` reads drivers, time and ports and moves what
does, motion composing innermost — the deprecation of driver reads in
`render()` with the warning a reader will see, and the two pitfalls:
class-level names are invisible to a class-body comprehension, and
structure that depends on time. It SHALL NOT recommend placement in
`__init__`. It SHALL state that a driver cannot be qualified on a repeated
or list-held child and that ports are the drive path for identical units.
The animation, driving, assemblies, testing and API pages SHALL read
drivers and time in `simulate()`, the node-tree, assemblies, leaf-node and
CLI pages SHALL cross-reference the declaring page, and the changelog SHALL
record the lifecycle with the deprecation.

#### Scenario: A reader places a stationary part

- **WHEN** a reader asks where a once-only placement goes
- **THEN** the page shows it in `render()`, shows the moving part's
  operation in `simulate()`, states that the framework runs `render()`
  once and `simulate()` per instant, and that motion composes inside the
  rest placement

#### Scenario: A reader migrates a render that reads time

- **WHEN** a reader's build prints the deprecation warning
- **THEN** the page shows the warning, the `render()` that caused it, and
  the same class with the read and its operations moved to `simulate()`
