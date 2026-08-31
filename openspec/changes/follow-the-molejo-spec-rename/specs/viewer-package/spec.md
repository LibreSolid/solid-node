## ADDED Requirements

### Requirement: A flexible spec the evaluator cannot read is refused by name

The package SHALL refuse a `flexible` node whose spec the bundled
evaluator cannot read, naming the node and carrying the evaluator's own
reason, rather than rendering a wrong or missing shape. The refusal SHALL
happen when the node is constructed — the same point at which an
unevaluable `tech` is already refused — so that an unreadable document
fails at load with a message that identifies it, and never as an
exception escaping the render loop on some later frame.

The package SHALL NOT interpret the spec to decide this. It asks the
bundled evaluator whether the spec is readable and reports what the
evaluator says, so the document stays opaque to the viewer and the set of
readable specs remains the evaluator's to define.

#### Scenario: A spec the bundled evaluator cannot read is refused at load

- **WHEN** a document carries a `flexible` node whose `tech` the package
  evaluates, but whose spec the bundled evaluator rejects — for instance
  one written for an older evaluator, declaring a spec version that
  evaluator no longer reads
- **THEN** construction fails naming the node and including the
  evaluator's reason, no geometry is created for it, and no exception is
  raised from a later frame

#### Scenario: A readable spec is unaffected

- **WHEN** a document carries a `flexible` node whose spec the bundled
  evaluator reads
- **THEN** the node is constructed and evaluated exactly as before, with
  no additional per-frame work
