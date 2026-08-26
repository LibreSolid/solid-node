# build-pipeline delta: instance-qualified drivers

## ADDED Requirements

### Requirement: Loading binds declared driver defaults

When the build or test path loads a node whose tree declares drivers,
it SHALL bind every declared driver's default — enumerated across the
whole linked tree by qualified id — before the node's first render, so
a driver-declaring project builds, tests, and serves through the CLI
without binding its own defaults in `__init__` and without a running
simulation. A tree declaring no drivers SHALL load exactly as before.
Default binding SHALL live outside `solid_node/node/`, preserving the
rule that the node layer never imports the simulation layer.

#### Scenario: A driver-declaring project builds without self-binding

- **WHEN** the CLI builds a project whose assembly's `render()` reads
  a declared driver and whose `__init__` binds nothing
- **THEN** the build succeeds with the declared default bound, with no
  unbound-state error

#### Scenario: A driverless project loads unchanged

- **WHEN** the CLI builds a project declaring no drivers (the
  v8-engine path)
- **THEN** loading performs no state binding and behavior is identical
  to before this change
