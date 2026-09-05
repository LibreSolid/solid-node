## ADDED Requirements

### Requirement: The test framework does not import the exact-geometry stack

The system SHALL import `solid_node.exact`, and through it the
boundary-representation stack, at the exact path's first use rather than at
`solid_node.test` module scope. Importing `solid_node.test` in a fresh
interpreter SHALL NOT import `cadquery`.

This completes the deferral the loader requirement already states from the
other side: loading a node imports neither the test framework nor cadquery,
and now importing the test framework does not import cadquery either. A
project that models entirely in solid2 and asserts entirely over meshes
therefore runs its tests without ever loading the exact stack.

The deferral SHALL NOT make exact geometry optional or change any exact
verdict. A comparison between two exact nodes SHALL import the same stack it
imports today and produce the same result; only the moment of the import
moves. The names `solid_node.test` resolves from `solid_node.exact` today
SHALL remain resolvable as attributes of `solid_node.test`, so a caller that
patches one keeps working whether or not an exact comparison has yet run.

A failure of the deferred import SHALL surface under the existing
deferred-import requirement: the underlying error is raised at first use,
naming the name, never swallowed or substituted.

#### Scenario: Importing the test framework loads no exact stack

- **WHEN** `solid_node.test` is imported in a fresh interpreter
- **THEN** `cadquery` is absent from `sys.modules`

#### Scenario: A faceted project's test run loads no exact stack

- **WHEN** a project whose nodes are all faceted runs its tests to completion
- **THEN** the run reports the same results as today and `cadquery` is absent
  from `sys.modules`

#### Scenario: An exact comparison still loads the stack

- **WHEN** two exact nodes are compared by an intersection assertion
- **THEN** the exact stack is imported and the comparison returns the verdict
  it returns today

#### Scenario: A patched name still resolves

- **WHEN** a caller patches an exact-kernel name on `solid_node.test` before
  any exact comparison has run
- **THEN** the exact path uses the patched object
