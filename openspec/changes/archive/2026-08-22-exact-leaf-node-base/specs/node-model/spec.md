## ADDED Requirements

### Requirement: Leaf adapters are distinct types

Each leaf adapter SHALL be a distinct type, and no adapter SHALL be an
instance of another. Adapters that share an implementation base SHALL NOT
thereby become interchangeable to a type test: a project or a framework path
that distinguishes backends by `isinstance` or by walking the method
resolution order SHALL get the same answer whatever bases the adapters
happen to share.

This constrains how shared adapter behaviour may be factored. It does not
require any particular factoring, and it does not make a shared base part of
the public interface.

#### Scenario: Adapters sharing a base stay distinct

- **WHEN** the exact adapters `CadQueryNode` and `Build123dNode` are tested
  against each other with `isinstance`
- **THEN** neither is an instance of the other, and each remains its own type

#### Scenario: The backend lookup is not confused by a shared ancestor

- **WHEN** a node's STL generation resolves the backend name by walking the
  method resolution order for adapter class names
- **THEN** an exact adapter resolves to no mesh-rendering backend, as it did
  before any base was shared, and never launches OpenSCAD
