## MODIFIED Requirements

### Requirement: Structural omission

The system SHALL let `render()` call `omit()` on a declared child to remove
it from the machine for that realization: an omitted child SHALL NOT be
linked, built, exported, fused or serialized. Every child is always
declared; `render()` selects presence. Structure SHALL vary with parameters
only: `omit()` called during `simulate()` SHALL raise `StructureError`, and
on the legacy path, where `render()` re-runs, a render whose omitted set
differs from that instance's first render SHALL raise naming the node and
both sets. On a once-only `render()` the omitted set of the first run is the
instance's structure. An omitted list member SHALL leave its siblings'
indices and identities unchanged.

#### Scenario: Simulate cannot omit

- **WHEN** an assembly's `simulate()` calls `omit()` on a declared child
- **THEN** `StructureError` is raised naming the node and `simulate()`

#### Scenario: Omission holds across bindings

- **WHEN** a once-only `render()` omits a child under a `Flag` and the
  assembly is simulated under three bindings
- **THEN** every enumeration returns the same children without the omitted
  one
