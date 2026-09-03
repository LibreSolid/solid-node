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

### Requirement: Tree naming from parent attributes

The system SHALL derive a child's tree name when it is linked: an explicit
`name=` always wins; otherwise the parent attribute holding the child is used
(a plain attribute wins over list membership; list members become
`<attr>-<index>`; `_`-prefixed attributes and `children`, the framework's
own linked list, are skipped; class name is the fallback). Naming SHALL be
idempotent and used consistently by the test runner, the web NodeAPI, and
STL child linking.

#### Scenario: The linked list never names

- **WHEN** an assembly's once-only `render()` returns fresh unnamed
  children and the tree is linked, assembled and serialized more than once
- **THEN** every link derives the same class-name fallback, never
  `children-<index>` from the list `as_scad` keeps
