## MODIFIED Requirements

### Requirement: An internal render that returns nothing

The system SHALL treat an internal node's `render()` that returns `None` as
returning the realized declared children in declaration order minus those
omitted during that render, so the method's job on a declarative class is
to position and select. Whether this substitution applies SHALL be determined
from the class's child declarations, independently of how many children those
declarations realize for one instance. A declared repeat that realizes zero
children and a render that omits every declared child SHALL therefore expose
an empty list to every consumer. A class with nothing to position SHALL need
no `render()`. A `render()` that returns a list or tuple SHALL keep its
existing contract unchanged. Every consumer of `render()` — the build, the
serializer, the driver walk and state propagation — SHALL see the substituted
list, never `None`. On an assembly the animator sweep SHALL run before the
author's `render()` exactly as it does today. A leaf `render()` returning
`None` SHALL remain an error.

#### Scenario: A grouping node needs no methods

- **WHEN** an `AssemblyNode` subclass declares three children and defines no
  method
- **THEN** rendering it yields those three children, linked and named after
  their attributes, and the serialized document lists them

#### Scenario: Positioning without a return

- **WHEN** an assembly's `render()` rotates a child by an expression in
  `self.time` and returns nothing, and the assembly is rendered at two
  keyframes
- **THEN** the child carries exactly one rotation after each render, for
  that instant, and both renders yield the declared children

#### Scenario: A returned list keeps its contract

- **WHEN** a declarative class's `render()` returns a hand-picked list
- **THEN** that list is what the framework builds, and declared children
  absent from it are not built

#### Scenario: A fusion positions its declared parts

- **WHEN** a `FusionNode` subclass declares two children and its `render()`
  translates one and returns nothing
- **THEN** the fusion is composed from both children with that placement

#### Scenario: A zero repeat remains declared structure

- **WHEN** a methodless `AssemblyNode` declares
  `parts = Part().repeat(count)` and its resolved `count` is zero
- **THEN** `render()` returns `[]`, assembly succeeds, and every consumer sees
  an empty child list rather than `None`

#### Scenario: Every declared child is omitted

- **WHEN** an `AssemblyNode` omits all of its declared children during its
  once-only render
- **THEN** assembly succeeds with no linked children and serialization
  publishes `children: []`
