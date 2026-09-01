## MODIFIED Requirements

### Requirement: Composite node tree

The system SHALL model a project as a tree of nodes rooted in
`AbstractBaseNode`, where `InternalNode` subclasses compose children and
`LeafNode` subclasses generate geometry. An `InternalNode.render()` SHALL
return a list or tuple of node instances, or `None` on a class with
declared children under the `declarative-nodes` capability, in which case
the framework substitutes the realized declared children minus the omitted
ones before any consumer sees the result. A `LeafNode.render()` SHALL
return a single geometry object, never a list and never `None`. Validation
runs on every `assemble()` and enforces these contracts before any SCAD
generation.

#### Scenario: Internal node returns children

- **WHEN** an `InternalNode` subclass's `render()` returns a list of
  `AbstractBaseNode` instances
- **THEN** `assemble()` links each child, assembles it, and unions the
  results (union applied only when there is more than one child)

#### Scenario: Internal node returns nothing

- **WHEN** an `InternalNode` subclass with declared children defines a
  `render()` that positions them and returns nothing
- **THEN** `assemble()` links, assembles and unions the declared children
  exactly as if `render()` had returned them in declaration order

#### Scenario: Structural contract violations are rejected

- **WHEN** an `InternalNode.render()` returns a non-list that is not the
  declarative `None`, returns an element that is not an `AbstractBaseNode`,
  or returns an instance of its own type
- **THEN** validation raises an error during `assemble()`
- **WHEN** a `LeafNode.render()` returns a list, returns `None`, or returns
  an object whose module does not start with the adapter's declared
  `namespace`
- **THEN** validation raises an error during `assemble()`

### Requirement: Parameter-hashed artifact identity

The system SHALL give each node instance a `uniq_id` of the form
`<readable-prefix>-<12-hex-sha256>`, hashed over a canonical serialization of
the class `__qualname__` and the node's parameters. For a class that declares
no parameters and no children under the `declarative-nodes` capability, the
parameters are the positional args in order and the kwargs sorted by key that
reach `AbstractBaseNode.__init__`, exactly as before. For a declarative
class, the parameters are the resolved, coerced values of its declared
parameters sorted by name, derived by the framework and never forwarded by
hand. The readable prefix is sanitized and truncated to 60 characters; the
hash is computed over the full untruncated serialization. Build artifact
basenames are always `<script-name>-<uniq_id>`. The `name=` kwarg SHALL
never influence `uniq_id`.

#### Scenario: Parameter change invalidates artifact key

- **WHEN** the same node class is instantiated with any differing parameter
  value
- **THEN** the two instances have different `uniq_id`s and separate build
  artifacts

#### Scenario: Identical instances share artifacts

- **WHEN** the same class is instantiated twice with identical args
- **THEN** both instances share one `uniq_id` and one cached artifact set

#### Scenario: Distinct no-arg classes never collide

- **WHEN** two different no-arg node classes are built
- **THEN** their `uniq_id`s differ because the class qualname is part of the
  serialization

#### Scenario: A declarative class cannot forget a parameter

- **WHEN** a class declares six parameters and is realized twice with one
  value differing
- **THEN** the two `uniq_id`s differ without the class forwarding anything
  to `super().__init__()`

#### Scenario: A migrated class keeps its key

- **WHEN** a class that forwarded all of its kwargs to `super().__init__()`
  with float defaults is rewritten to declare exactly those parameters with
  the same defaults
- **THEN** an instance realized with defaults has the same `uniq_id` as
  before the rewrite
