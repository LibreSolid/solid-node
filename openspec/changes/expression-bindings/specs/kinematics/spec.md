## MODIFIED Requirements

### Requirement: The parity corpus covers every symbolic function

The system SHALL name, in one place in `solid_node/math.py`, every OpenSCAD
builtin the module may emit as a call, and every function that emits one
SHALL take its name from that inventory rather than spelling it a second
time. That inventory is the source of truth for what the corpus must cover;
no consumer SHALL keep a second, hand-maintained list of the same names.

The system SHALL pin every function `solid_node.math` can emit symbolically
in the cross-runtime parity corpus, so no exported symbolic name reaches a
published document without a fixture case behind it. The corpus SHALL keep
its existing discipline: an expected value is a producer value, obtained by
serializing one node tree twice — once bound to a numeric snapshot and once
symbolically — and pairing the two walks by structure, never by evaluating an
expression a second way.

The corpus SHALL carry the document's `bindings` table beside its cases, and a
case's expression MAY be, or reference, a binding name. The coverage check
SHALL therefore read emitted builtin names across the bindings and the cases
together: an emitted name that appears only inside a binding SHALL count as
covered, and a name appearing in neither SHALL fail the regeneration. A corpus
whose cases were self-contained SHALL NOT be able to hide an emitted builtin
by moving it into the table.

Adding a symbolic function to the module SHALL therefore add at least one
case exercising it to the corpus. The corpus SHALL be extended by adding a
new tree beside the existing one rather than by altering the existing cases,
so a regeneration changes no expected value that was already pinned. An
existing case's expression MAY be rewritten to reference a binding where the
producer now shares a subexpression, because the expression is how the value
is written and not the value itself; its key and its expected value SHALL be
unchanged.

The corpus SHALL include at least one tree whose expressions repeat a
subexpression, so the fixture pins the table's own semantics: an entry
referring to an earlier entry, a binding referenced from more than one node,
and a binding over a driver id as well as over `$t`.

#### Scenario: Every emitted name is pinned

- **WHEN** the parity fixture is regenerated
- **THEN** it carries at least one case whose expression, or one binding the
  case reaches, contains each name in the module's own inventory of emitted
  builtins, and the check that says so reads that inventory rather than a list
  of its own

#### Scenario: A new emitted name cannot slip through

- **WHEN** a function emitting a builtin absent from the corpus is added to
  the module and the fixture is regenerated
- **THEN** the regeneration fails naming the uncovered builtin

#### Scenario: A name inside a binding is covered

- **WHEN** the corpus reuses a subexpression so that an emitted builtin ends
  up only inside a `bindings` entry and in no case's own expression
- **THEN** the regeneration succeeds and reports that builtin as covered

#### Scenario: The corpus pins the table

- **WHEN** the parity fixture is regenerated
- **THEN** it carries a `bindings` array holding at least one entry that names
  an earlier entry and at least one entry referenced from more than one case

#### Scenario: Regeneration leaves the existing corpus's values alone

- **WHEN** the fixture is regenerated after the new corpus is added
- **THEN** every case the previous fixture carried is present under the same
  key and with the same expected value, whether or not its expression was
  rewritten to reference a binding
