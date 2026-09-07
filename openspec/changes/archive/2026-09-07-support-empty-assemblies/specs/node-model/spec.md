## ADDED Requirements

### Requirement: Empty internal composition

The system SHALL allow a non-rigid `AssemblyNode` to render an empty list or
tuple. Its ordinary assembly lifecycle SHALL complete with an empty SCAD
grouping, its linked `children` SHALL be empty, it SHALL generate no STL of its
own, and serialization SHALL include `children: []`.

A rigid `FusionNode` SHALL require at least one selected child because it
represents one solid and has no valid rigid geometry when its membership is
empty. A zero-child fusion SHALL fail during validation with a diagnostic
naming the fusion, before SCAD, BREP, or STL publication.

#### Scenario: Explicit empty assembly

- **WHEN** an `AssemblyNode.render()` explicitly returns `[]`
- **THEN** `assemble()` succeeds, the node has no linked children, and its
  serialized document contains an empty `children` array

#### Scenario: Empty fusion is refused

- **WHEN** a `FusionNode` returns an empty list or declarative selection
  removes every child
- **THEN** validation raises naming the fusion and explaining that a fusion
  requires at least one rigid child
- **AND** no SCAD, BREP, or STL artifact for that fusion is published
