## ADDED Requirements

### Requirement: A shared subexpression is published once

A published document — the export `manifest.json` and the normal-build
`viewer.json` alike — SHALL publish each subexpression that occurs more than
once among its expressions exactly once, as a named entry in an ordered
`bindings` table, and SHALL reference that entry by name everywhere the
subexpression occurred.

The expressions this covers are every operation's expression strings and every
flexible leaf's `params` values. A subexpression that is a single number or a
single name — a literal or a driver id — SHALL NOT be bound: it is shorter
written out than referenced.

`bindings` SHALL be a JSON array of objects, each carrying a `name` and an
`expression`, and SHALL be ordered so that an entry's expression names only
`$t`, qualified driver ids declared in the document's `drivers` table, and
entries appearing **earlier** in the array. A consumer SHALL therefore be able
to evaluate the table in one forward pass, into the same scope in which it
resolves `$t` and driver values, before evaluating any operation or `params`
expression.

An entry SHALL NOT carry the inputs its expression depends on. The ordering
guarantee is what lets a consumer derive them: an entry's inputs are the names
it mentions together with the inputs of the entries it names.

A reference SHALL be the binding's name written where an expression would
otherwise be, with nothing marking it as a reference. It is an ordinary name
in the expression language and SHALL be resolved as `$t` and a driver id are
resolved.

The table SHALL be ordered deterministically for a given tree, so that
republishing an unchanged model produces a byte-identical document.

An expression the producer cannot read SHALL be published **verbatim and
unshared**, and SHALL NOT prevent the document from being written. Sharing is
an improvement to a document that already published and already rendered, so an
expression the framework fails to understand SHALL cost only that expression's
share of the improvement. The producer SHALL warn once per such expression,
naming the offending text and identifying the expression — truncated, because a
published expression may be megabytes — and the rest of the document SHALL be
bound as usual.

The producer SHALL refuse to write a document only when the table it would
publish would be wrong: an entry naming a later entry, a name colliding with a
declared driver id, or a rewritten expression that does not reproduce what the
producer built. Those are defects in the framework, not in the model, and SHALL
be reported as such.

#### Scenario: A subexpression reused across operations is published once

- **WHEN** a document is published in which one subexpression appears in the
  operations of several nodes
- **THEN** its text appears once, as one `bindings` entry, and each of those
  operations carries that entry's name in place of the subexpression

#### Scenario: No expression text is repeated

- **WHEN** a document carrying repeated subexpressions, every one of them
  readable by the producer, is published
- **THEN** no operator application, call, or parenthesised group appears twice
  anywhere in the document's expressions and bindings taken together

#### Scenario: An expression the producer cannot read is still published

- **WHEN** a tree carries an expression the producer cannot read, beside
  expressions it can
- **THEN** the document is written, that expression appears verbatim and
  unshared, every readable expression is bound as usual, and a warning names
  the offending text and identifies the expression without printing all of it

#### Scenario: An unreadable expression does not silence the rest

- **WHEN** a tree carries one unreadable expression and a subexpression shared
  between two readable ones
- **THEN** the shared subexpression is still published once as a binding, and
  the document declares the version that table needs

#### Scenario: A bare number or name is not bound

- **WHEN** a document is published in which a literal and a driver id each
  occur many times
- **THEN** neither becomes a `bindings` entry, and both stay written out where
  they occur

#### Scenario: The table is ordered so one forward pass suffices

- **WHEN** a document carrying bindings is published
- **THEN** every name each entry's expression mentions is either `$t`, a
  qualified id present in the `drivers` table, a name defined by the
  expression language's own functions, or the name of an entry appearing
  earlier in the array

#### Scenario: Republishing an unchanged model changes nothing

- **WHEN** an unchanged model is published twice
- **THEN** the two documents are byte-identical, bindings and their order
  included

#### Scenario: The published document evaluates to what the flat one did

- **WHEN** a document carrying bindings is published, and each binding is
  substituted back into the expressions that reference it
- **THEN** the reconstructed expressions evaluate, at every value of `$t` and
  of every driver, to what the expressions the producer built evaluate to

### Requirement: Binding names cannot collide with anything the consumer resolves

Binding names SHALL be `_b0`, `_b1`, … in table order, so that a name is short
and cannot collide with `$t` or with any function the expression language
defines.

Where a qualified driver id in the same document would collide with a name the
table is about to use, the producer SHALL lengthen the prefix by a leading
underscore and re-derive the names, repeating until no collision remains. A
model SHALL NOT be refused because of the names its drivers were given, and a
driver id SHALL NOT be altered to make room.

#### Scenario: Ordinary names

- **WHEN** a document with bindings is published from a tree declaring no
  driver whose id begins with an underscore
- **THEN** its bindings are named `_b0`, `_b1`, … in table order

#### Scenario: A driver named like a binding

- **WHEN** a tree declares a driver whose qualified id is `_b0` and its
  document carries bindings
- **THEN** the document is published, the driver keeps the id `_b0` in its
  expressions and in the `drivers` table, and the bindings are named under a
  longer prefix that collides with nothing

### Requirement: What a binding name means to a consumer

The table is resolved before the document's other names, and dependence flows
through it. A consumer SHALL read a published document by these rules.

**Bindings resolve first.** A name appearing in an operation's expression, in a
flexible leaf's `params`, or in another binding SHALL be resolved as a binding
before it is treated as a driver id. A binding name SHALL NOT be reported as an
undeclared driver: a consumer that refuses a document naming an id absent from
the `drivers` table SHALL make that check after the table's names are known.

**Dependence flows through a binding.** Where a consumer bounds re-evaluation by
the inputs an expression depends on — `$t`, a driver id, or both — an expression
naming a binding SHALL be treated as depending on every input that binding
transitively depends on. An operation whose whole expression is a binding name
that resolves through the table to `$t` is a time-dependent operation and SHALL
be re-evaluated when time changes, exactly as it was when its expression was
written out in full.

**Every other name is unchanged.** A name that is neither `$t`, nor a binding,
nor a declared driver id means what it means today: a function of the
expression language where the language defines one, and otherwise the same
unresolved name it was before bindings existed. This change introduces no new
name kind and no new resolution failure.

#### Scenario: An operation that is only a binding name still follows time

- **WHEN** an operation's expression is a binding name, and that binding
  resolves through the table to an expression over `$t`
- **THEN** a consumer bounding re-evaluation by inputs re-evaluates that
  operation when time changes, as it did when the expression was written out

#### Scenario: A driver reached through a binding is a dependence of the operation

- **WHEN** a binding's expression names a declared driver id, and an operation
  names that binding
- **THEN** the operation depends on that driver, and changing the driver's
  value re-evaluates the operation

#### Scenario: A binding name is not an undeclared driver

- **WHEN** a document declaring an empty `drivers` table carries bindings, and
  its operations name them
- **THEN** a consumer that refuses documents naming undeclared driver ids
  accepts it, because every name its expressions carry is `$t`, a binding, or
  a function of the expression language

## MODIFIED Requirements

### Requirement: Manifest contract

The manifest SHALL retain the document name `manifest.json` and SHALL declare
`format: "solid-node-export"`, `animation: {fps, frames}`, a
`drivers` table, an `instructions` table, and a
`root` tree with the same observable schema and child-name behavior as the
normal-build `viewer.json`. When the exported root declares a time base the
`animation` object SHALL also carry numeric `loop`, the declared seconds of
machine time one turn of `$t` covers, and SHALL omit the key otherwise; the
browser-snapshot document SHALL publish `loop` under the same rule. `loop` is
additive within the current schema version — a consumer that does not read
it plays `frames / fps` as before — and `--fps` / `--frames` keep their
meaning as the timeline's playback resolution. A rigid node SHALL emit one
`model` reference and
stop recursion; a non-rigid node whose render result is a list or tuple SHALL
recurse into its children; a flexible leaf SHALL emit one `flexible` object
and stop recursion. Each node SHALL carry `name`, `type`, `color`,
`mtime`, and its operations as unevaluated expressions so `$t`
animation is preserved rather than baked to the constants of one instant. A
rigid model reference SHALL remain rooted
beneath the export's `models/` directory and SHALL resolve to a copied artifact
so the export remains portable and self-contained. Changes to the shared tree
shape or operation serialization are breaking and MUST bump `version` and
update every producer and consumer of the shared schema together.

When the serialized document contains a subexpression occurring more than
once, the manifest SHALL carry a non-empty `bindings` table beside `drivers`
and `instructions`, under the shared-subexpression requirement above, and SHALL
declare `version: 4`. When it contains no such subexpression the `bindings` key
SHALL be absent and the document SHALL declare `version: 3` when the serialized
tree contains at least one flexible leaf and `version: 2` otherwise — so a
document with nothing to bind is byte-identical to the one published before
bindings existed, and an old consumer refuses only what it genuinely cannot
render.

The bump to `version: 4` SHALL NOT be treated as additive. A consumer ignoring
`bindings` would resolve a binding name to nothing and place the machine in a
wrong pose, so a consumer that cannot resolve the table SHALL refuse the
document rather than render it. Consumers SHALL accept versions 2, 3 and 4.

#### Scenario: A declared time base is exported

- **WHEN** a root declaring `time = Time(loop=43200)` is exported
- **THEN** `manifest.json` carries `animation.loop == 43200` beside the
  requested `fps` and `frames`, its version is unchanged by the key, and its
  operations carry `$t` multiplied by the loop rather than a constant

#### Scenario: An undeclared root exports no loop

- **WHEN** a root declaring no time base is exported
- **THEN** `manifest.json`'s `animation` object has no `loop` key and is
  byte-identical to the manifest exported before this change

#### Scenario: A document with nothing shared is unchanged

- **WHEN** a tree whose expressions repeat no subexpression is exported
- **THEN** `manifest.json` has no `bindings` key, declares the version its
  content already needed, and is byte-identical to the manifest exported
  before bindings existed

#### Scenario: A document with sharing declares the new version

- **WHEN** a tree whose expressions repeat a subexpression is exported
- **THEN** `manifest.json` declares `version: 4` and carries a non-empty
  `bindings` array

#### Scenario: A flexible document with sharing declares the new version

- **WHEN** a tree holding a flexible leaf and repeating a subexpression is
  exported
- **THEN** `manifest.json` declares `version: 4` rather than `3`, and its
  flexible leaf's `params` may reference the table
