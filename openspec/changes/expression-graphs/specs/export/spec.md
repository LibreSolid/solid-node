## ADDED Requirements

### Requirement: Publication preserves sharing from motion construction

The ordinary build and export producers SHALL preserve shared framework motion
values through final publication without first rendering their fully expanded
strings. Operations and flexible parameters SHALL participate together in the
existing shared-subexpression binding contract. Publication SHALL retain the
document's current format, version ladder, expression vocabulary, deterministic
ordering, name-collision handling and legacy unreadable-text fallback.

SCAD-local sharing syntax and internal graph identifiers SHALL NOT occur as new
syntax in generated viewer expressions. A compact standalone scalar recognized
by the framework SHALL be lowered into the existing document language, rather
than forwarded as unreadable legacy text. Publishing SHALL preserve live
values and restore driver bindings according to the existing symbolic mode.

#### Scenario: A shared law reaches rigid and flexible outputs

- **WHEN** a framework motion value is reused in rigid operations and flexible
  parameters in a build or export
- **THEN** their document shares repeated compounds through its ordered
  bindings and no producer step constructs the fully expanded formulas

#### Scenario: Existing viewer consumes the result

- **WHEN** the new producer publishes a shared machine to a schema-4-capable
  viewer
- **THEN** the viewer evaluates its operations and flexible parameters with
  the existing expression language and controls, without a format upgrade

#### Scenario: Deterministic publication

- **WHEN** the same machine is published repeatedly with unchanged content
- **THEN** bindings and expression text are identical regardless of prior
  unrelated publications in the same process

#### Scenario: Nothing requires sharing

- **WHEN** a document contains no repeated compound expression
- **THEN** it omits bindings and retains the existing version and expression
  spelling appropriate to its content

#### Scenario: Legacy text sits beside native motion

- **WHEN** a document combines native shared motion and unreadable legacy text
- **THEN** native motion receives sharing, the legacy text remains verbatim with
  a truncated warning, and the existing table validity checks still apply

#### Scenario: A framework compact scalar returns through custom serialization

- **WHEN** a custom operation supplies the framework's compact standalone scalar
  text to a node-tree document producer
- **THEN** the scalar publishes through the existing expression language and
  bindings instead of introducing SCAD-local syntax into the document
