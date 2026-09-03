## MODIFIED Requirements

### Requirement: Template-method render lifecycle

The system SHALL control the node lifecycle through `assemble()`, which users
do not override: render → simulate (assemblies only) → validate → `as_scad` →
`generate_scad` → optional optimized STL import → apply queued operations.
`assemble()` SHALL be idempotent — the result is memoized and `render()` is
called at most once per instance. On an assembly the framework SHALL run
`simulate()` after `render()` on every call that enumerates its children,
under the current binding; users override `render()` and `simulate()`, never
`assemble()`.

#### Scenario: Simulate follows render

- **WHEN** an assembly defining both `render()` and `simulate()` is
  assembled
- **THEN** `render()` has run before `simulate()`, and the queued
  operations applied include those `simulate()` produced
