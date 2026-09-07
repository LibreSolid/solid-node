## MODIFIED Requirements

### Requirement: Tree naming from parent attributes

The system SHALL derive a child's tree name when it is linked: an explicit `name=` always wins; otherwise the parent attribute holding the child is used (a plain attribute wins over list membership; list members become `<attr>-<index>`; `_`-prefixed attributes and `children`, the framework's own linked list, are skipped; class name is the fallback). Where the same child is reachable through several direct attributes, the first public direct attribute in insertion order SHALL win; only when no direct attribute holds it SHALL the first public list/tuple membership in attribute and element order name it.

Naming SHALL be idempotent and used consistently by the test runner, simulation/driver enumeration, the web/document serializer, and STL child linking. A framework traversal SHALL inspect a parent's attributes and sequence contents at most once, SHALL link and name all returned siblings from that traversal-entry snapshot before recursing into any child's user code, and SHALL then perform constant-time name lookup per child. It SHALL NOT rescan a wide list once per child.

Direct reassignment, alias changes, replacement, append/removal, and same-length in-place reordering SHALL be visible on the next traversal. A mutation performed by one child during recursive user code SHALL NOT change how a later sibling is named in the parent traversal already in progress; all siblings use the same entry snapshot, and the mutation is visible when another traversal begins. Every link SHALL update the child's current parent even when its explicit name prevents derivation.

#### Scenario: Attribute-derived name

- **WHEN** a parent stores a child as `self.wheel` and returns it from `render()`
- **THEN** the child's tree name is `wheel`

#### Scenario: A direct alias wins over list membership

- **WHEN** one unnamed child appears in a public list and is also held by a public direct attribute declared later
- **THEN** the direct attribute names it, and linking does not depend on the list scan encountering it first

#### Scenario: A wide list is indexed once per traversal

- **WHEN** one traversal links thousands of children held in a public list
- **THEN** the list is scanned once for that parent and each returned child is named by constant-time lookup, producing the same `<attr>-<index>` names as the unindexed contract

#### Scenario: Same-length mutable reorder is visible

- **WHEN** a legacy model reverses or swaps elements of a public child list without changing its length and the tree is traversed again
- **THEN** each unnamed child's derived `<attr>-<index>` name reflects its new position and each parent link is current

#### Scenario: Mid-traversal mutation waits for the next traversal

- **WHEN** the first child mutates or reorders its parent's public child list during recursive render or simulate work
- **THEN** every sibling in the current traversal keeps the name derived from the common traversal-entry snapshot, and a subsequent traversal reflects the mutated order

#### Scenario: The linked list never names

- **WHEN** an assembly's once-only `render()` returns fresh unnamed children and the tree is linked, assembled and serialized more than once
- **THEN** every link derives the same class-name fallback, never `children-<index>` from the list `as_scad` keeps
