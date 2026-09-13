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
rigid model reference SHALL be derived relative to the selected build directory
that owns the artifact, SHALL remain rooted beneath the export's `models/`
directory with no parent traversal, and SHALL resolve to a copied artifact so
the export remains portable and self-contained regardless of the caller's
working directory. An artifact outside that build directory SHALL make export
fail before it creates or modifies the requested output. Changes to the shared
tree shape or operation serialization are breaking and MUST bump `version` and
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

When the serialized root declares `time = Time.running()` the document SHALL
declare `version: 5` and SHALL carry the `program` object defined by the
requirement "A running root's document publishes the compiled program",
whatever its tree content — the version ladder below 5 is derived from the
CONTENT because flexible leaves and shared subexpressions are properties of
the tree, while a compiled program is a property of the ROOT'S DECLARATION,
and a running root with a trivial program is still a machine a version 4
consumer would animate wrongly. A root declaring no time base or a looping
one SHALL NEVER declare `version: 5`, SHALL NOT carry a `program` key, and
SHALL be byte-identical to the document published before the program existed.

The bump to `version: 5` SHALL NOT be treated as additive. A consumer
ignoring `program` would read a document whose joint placements are bare
coordinate names it can bind nothing to, so a consumer that cannot read
version 5 SHALL refuse the document by name rather than render it or animate
it as a loop.

The `instructions` table SHALL publish, under `version: 5`, EVERY declared
instruction, each entry carrying exactly one of `targets` (where the drivers
land) and `by` (how far they travel from where they stand), both keyed by
qualified driver id and both in design units, beside `duration` in seconds.
Under versions 2, 3 and 4 an instruction stating `by` SHALL continue to be
OMITTED from the table, because a consumer of those versions reads `targets`
off every entry.

#### Scenario: A running root's document declares version 5

- **WHEN** a root declaring `time = Time.running()` is exported
- **THEN** `manifest.json` declares `version: 5` and carries a `program`
  object beside `drivers`, `instructions` and `bindings`

#### Scenario: An untimed document is unchanged in every byte

- **WHEN** a root declaring no time base, and one declaring
  `time = Time(loop=2.0)`, are exported
- **THEN** neither document carries a `program` key, each declares the
  version its content already needed, and each is byte-identical to the
  document exported before this change

#### Scenario: Both instruction forms are published under version 5

- **WHEN** a running root declares `Instruction(by={'crank': 10.0},
  duration=0.5)` beside `Instruction({'crank': 40.0}, duration=0.5)`
- **THEN** the version 5 document's `instructions` table has an entry for
  each, the first carrying `by` and no `targets`, the second carrying
  `targets` and no `by`, both keyed by qualified driver id

#### Scenario: A relative instruction stays out of a version 4 table

- **WHEN** an untimed root declares only relative instructions
- **THEN** its document's `instructions` table is empty and the rest of the
  document is unchanged

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

#### Scenario: Export starts in a project subdirectory

- **WHEN** a project model is exported from a working directory below its
  project root to an output directory elsewhere
- **THEN** every model reference contains no parent traversal and resolves to
  its copied artifact beneath the output's `models/` directory

#### Scenario: Export uses a configured or selected build directory

- **WHEN** export uses a relative configured build root or a named model's
  selected build directory
- **THEN** model references preserve artifact paths relative to that resolved
  directory and resolve beneath the export's `models/` directory

#### Scenario: A model artifact is outside its build directory

- **WHEN** a rigid node names an STL whose canonical path is outside its
  resolved build directory
- **THEN** direct export raises `ExportModelPathError`, CLI export exits
  nonzero with that diagnostic, and the requested output is not created or
  modified

## ADDED Requirements

### Requirement: A running root's document publishes the compiled program

A document declaring `version: 5` SHALL carry a top-level `program` object,
beside `drivers`, `instructions` and `bindings` and ahead of `root`, holding
what COMPILE TIME decided about the machine and nothing the tick computes.
Every expression it carries SHALL be written in the document's existing
expression language and SHALL participate in the same ordered `bindings`
table the tree's expressions use, so no subexpression is published twice and
no producer-local sharing syntax appears anywhere in the document. The
object SHALL be ordered deterministically for a given tree, so republishing
an unchanged model produces a byte-identical document.

`program` SHALL carry:

- `identity`: the compiled program's identity — a digest over the root
  class, the bank's ids, the inputs' declarations, the spans and every
  edge's ends, direction and expression — so a state taken against one
  program is refused against another.
- `clock`: the free name elapsed simulation seconds bind to, under the
  requirement "A running document's clock is a published name".
- `coordinates`: one entry per BANK id, in the compiled program's own order
  — inputs first, then joint coordinates, each sorted — each carrying
  `kind` (`"input"` for a declared driver, `"coordinate"` for a joint
  coordinate), `initial` (the value the untimed REST POSE gave it), and,
  for a joint coordinate, `unit` (the joint's declared unit, or `null`). An
  input entry SHALL NOT repeat `unit`, `dtype`, `scale`, `range` or
  `default`: the document's `drivers` table publishes them under the same
  qualified id, and the two tables SHALL name exactly the same set of ids.
- `intermediates`: the sorted qualified ids of every value a compiled edge
  determines that the bank does NOT hold — a plain port, a derived
  coordinate — which a consumer recomputes from the bank on every tick and
  never stores.
- `edges`: one entry per compiled edge, IN PROGRAM ORDER, defined by the
  requirement "The published edges say what each one reads, gives and
  computes".
- `spans`: one entry per banked coordinate whose joint declares a range,
  keyed by its qualified id, carrying `low` and `high`, each `null` for
  unbounded, a number, or `{"expression": <text>}` for a bound stated as an
  expression over that coordinate's OWN id.
- `sources`: for each bank id and each intermediate, the sorted list of
  INPUT ids that reach it through the program — the candidate table a
  stop's blocked group is filtered out of.
- `limits`: the constants the algorithm is defined by, as numbers, so a
  consumer cannot silently differ from the producer: `crossing_tolerance`,
  `subdivisions`, `bisection_rounds`, `max_crossings` and `agreement` (the
  relative window inside which two increments on one coordinate are called
  equal).

The producer SHALL REFUSE to publish a program naming a coordinate or
intermediate whose qualified id could not be computed from its position in
the tree, naming the node and the reason: a fallback name derived from a
class name is not unique across two instances of that class, and publishing
it would put two different values under one name in one expression scope.

The producer SHALL REFUSE a running root on which a declared driver or a
joint coordinate qualifies to the id `time`, naming it and the reservation:
`time` is the one snapshot entry that is global by contract and the name a
running document's clock is published under.

Every entry of `program.coordinates`, input or joint coordinate, SHALL
carry a `domain` field, so a consumer's readouts and jog controls need no
second reading of the tree. For a JOINT COORDINATE its value SHALL be the
declared domain of the port the joint owns — `rotational`,
`translational` or `signal`, as the port kinds name them — beside its
unit. For an INPUT its value SHALL be `null`: a driver declaration states
a default, a range, a unit, a dtype and a scale, and no domain, and the
producer SHALL NOT derive one from the unit. The document SHALL NOT
publish a `dt`: the step is the executing runtime's choice, the supported
law class is exact across its kinks and locates its jumps and stops
inside whatever tick they fall in, and the conformance corpus pins each
machine's step per scenario.

Publication SHALL succeed over a tree a live running simulation owns and
SHALL leave that simulation's ownership, bank and ability to advance
intact: the publication binder is admitted over a run-owned slot and the
run's binder is restored afterwards.

#### Scenario: Coordinates publish their domain

- **WHEN** the Pascaline module's running root is exported
- **THEN** every `program.coordinates` entry carries `domain`, each arbor
  coordinate reading `rotational` beside its unit, and each dial — a
  declared driver, which states no domain — reading `null`

#### Scenario: Publishing does not disturb a live run

- **WHEN** a running simulation is halfway through a move and the tree's
  document is serialized in the same process
- **THEN** the document is produced, the simulation's bank and commands
  are unchanged, and the next tick advances exactly as it would have

#### Scenario: The program names the bank and the edges

- **WHEN** a running root with three drivers, nine joint coordinates and
  nine relations is published
- **THEN** `program.coordinates` has twelve entries with the drivers' ids
  first, each joint coordinate entry carries the rest pose's value and the
  joint's unit, and `program.edges` lists the nine relations in the order
  the run propagates them

#### Scenario: The drivers table is the one declaration

- **WHEN** a version 5 document is published
- **THEN** every `program.coordinates` entry whose `kind` is `"input"` is a
  key of the document's `drivers` table and every key of that table is such
  an entry, and no declaration field is repeated inside `program`

#### Scenario: A plain port is an intermediate, not a bank entry

- **WHEN** a running root drives a plain readout port from a joint
  coordinate
- **THEN** that port's qualified id is in `program.intermediates`, is not in
  `program.coordinates`, and the edge that computes it names it in `gives`

#### Scenario: A declared range travels as a span

- **WHEN** a running root declares
  `range=(lambda turn: 36 * floor(turn / 36), None)` on a joint
- **THEN** `program.spans` carries that coordinate with `low` an expression
  over that coordinate's own id and `high` `null`

#### Scenario: The program's expressions share the document's bindings

- **WHEN** a running root's law and one of its jump plans read the same
  subexpression
- **THEN** that subexpression appears once, as a `bindings` entry, and both
  the law's expression and the plan reference it by name; no `program`
  expression carries producer-local sharing syntax

#### Scenario: Republishing an unchanged running model changes nothing

- **WHEN** an unchanged running model is published twice
- **THEN** the two documents are byte-identical, the program's ordering and
  its minted names included

#### Scenario: An id that cannot be qualified is refused

- **WHEN** a running root's relation reaches a value on a node whose
  instance path is not computable
- **THEN** publication fails naming that node and saying a fallback class
  name is not unique, and no document is written

#### Scenario: A driver named like the clock is refused

- **WHEN** a running root declares a driver whose qualified id is `time`
- **THEN** the simulation refuses at construction, naming the id and that
  `time` is reserved for the clock

### Requirement: The published edges say what each one reads, gives and computes

Each `program.edges` entry SHALL carry `kind` (`"law"`, `"wiring"`,
`"formula"` or `"check"`), `needs` and `gives` as lists of qualified ids
(`gives` empty for a check), `description` — the relation or derived
coordinate AS WRITTEN — and `stated_by`, the class that stated it, so a
consumer's refusal names what a reader can find in the model. The free
names each of the entry's expressions reads SHALL be exactly the ids in
`needs`, so no separate name list is published.

**A law** SHALL carry three lists aligned with `gives`: `expressions`, the
law applied once to a symbolic token per source, or `null` where the law is
a constant and contributes nothing; `affine`, whether that driven end's
value is affine in its sources along a tick's path; and `plans`, `null`
where the expression carries no discontinuous primitive and otherwise a
JUMP PLAN carrying `skeleton` — the whole expression with every jump node
replaced by a branch placeholder — and `jumps`, the jump nodes IN THE
EXPRESSION'S POSTORDER, each with `name` (the placeholder the skeleton
reads it under), `primitive` (`floor`, `ceil`, `sign`, `%`, or a
comparison), `level` (the expression of the level quantity whose surfaces
it crosses, with every jump inside it already replaced by its own
placeholder) and `affine` (whether that level quantity is affine in the
sources). A `%` node SHALL NOT appear as a placeholder in the skeleton: the
skeleton SHALL already carry `a − q * b`, `q` being that node's
placeholder.

Branch placeholders SHALL be minted AT PUBLICATION and be unique across the
WHOLE document — `_j0`, `_j1`, … in edge order and then postorder — under a
prefix lengthened by a leading underscore for as long as any published id
matches `<prefix>` followed by digits. A placeholder that repeated across
two plans would let two different jump nodes share one published
subexpression.

**A wiring** SHALL carry `factor`: its value is `source × factor` and its
increment `Δsource × factor`.

**A formula and a check** SHALL carry `factors` aligned with `needs`,
`constant`, and `slot` — the derived coordinate's own id — and SHALL be
evaluated by these rules and no others:

- forward, where `slot` is in `gives`: the value is
  `constant + Σ needs[i] × factors[i]`;
- backward, where `gives` is one term of the formula: `needs` carries the
  slot FIRST with factor `0.0`, then the other terms, then the solved-for
  term itself with its own coefficient LAST, and the value is
  `(slot − constant − Σ other × factor) ÷ own`;
- an INCREMENT is the same arithmetic with `constant` replaced by zero;
- a check determines nothing: it PREDICTS `constant + Σ needs[i] ×
  factors[i]` over every need but the slot, and a tick in which that
  disagrees with the increment the slot received, relatively beyond
  `limits.agreement`, is a conflict that commits nothing.

#### Scenario: A law with a jump publishes its plan

- **WHEN** a running root's law is
  `4 + 72 * clamp01((angle − 360 * floor(angle / 360) − 113.5) / 11.25)`
- **THEN** its edge carries one expression, `affine: [false]`, and one plan
  whose `jumps` holds a single `floor` entry whose `level` is that source's
  id divided by 360, marked affine, and whose `skeleton` reads that entry's
  placeholder where the `floor` stood

#### Scenario: Placeholders are unique across the document

- **WHEN** a running root carries three laws each holding one `floor`
- **THEN** the three plans' placeholders are three distinct names, and no
  `bindings` entry is referenced from two of the three skeletons in place of
  two different jump nodes

#### Scenario: A remainder is written out in the skeleton

- **WHEN** a running root's law contains `angle % 360`
- **THEN** the plan's jump entry carries `primitive: "%"` and the skeleton
  carries the subtraction of that placeholder times the divisor rather than
  the placeholder alone

#### Scenario: A derived coordinate publishes its coefficients

- **WHEN** a running root declares `left = wrist + 2 * tool` and the rest
  render solves it backward into one term
- **THEN** that edge is a formula whose `needs` names the slot first with
  coefficient `0.0`, the other terms next, and the solved-for term last with
  its own coefficient

#### Scenario: A check publishes what it predicts

- **WHEN** a running root's derived coordinate and every one of its terms
  are determined by other edges
- **THEN** the program carries a `check` edge with empty `gives`, naming the
  slot and the coefficients it predicts from

### Requirement: A committed bank poses the geometry

Under a running root the producer SHALL serialize the tree with every JOINT
COORDINATE of the linked tree bound to a symbolic token of its own qualified
id, beside every declared driver's token, through the same internal binding
path the symbolic driver mode uses and never through the numeric snapshot
door. The document's ordinary pose expressions SHALL therefore name bank
ids: a joint's own placement operation SHALL be that coordinate's id, or an
expression over the ids of a joint owning several; a plain port, a derived
coordinate and a flexible leaf's `params` SHALL be expressions over whatever
bank ids drive them; and a driver that poses geometry without passing
through a joint SHALL keep publishing its driver id.

A consumer therefore evaluates, per frame, exactly the expressions it
evaluates for any other document, from a scope holding the whole bank rather
than the driver values alone. No second table of poses SHALL be published,
and flexible parts SHALL follow this rule unchanged.

The producer SHALL restore every coordinate it bound — its value, its
binder and its freshness marks — and SHALL re-place the joints from what
their coordinates then hold, so a caller that held a posed tree still holds
one. A declared range SHALL NOT judge a symbolic binding.

#### Scenario: A joint's placement is its coordinate's name

- **WHEN** a running root drives a register wheel through a carry law and
  its document is published
- **THEN** that wheel's rotation operation is the single name of its joint
  coordinate, and the carry law appears only inside `program`

#### Scenario: A plain port follows the bank

- **WHEN** a running root's readout port is driven from a joint coordinate
  at ratio −1
- **THEN** that port's pose expression is an expression over the joint
  coordinate's qualified id

#### Scenario: A flexible part follows the bank

- **WHEN** a running root holds a flexible leaf whose shape parameter is
  driven from a joint coordinate
- **THEN** its `params` expression names that coordinate's qualified id and
  its `spec` is unchanged

#### Scenario: Every name the document reads is declared

- **WHEN** a version 5 document is published
- **THEN** every free name its operation and `params` expressions read, after
  the bindings table is resolved, is the clock name, a key of the `drivers`
  table, a key of `program.coordinates`, or a `program.intermediates` entry

#### Scenario: The tree is left as it was found

- **WHEN** a posed running tree is serialized and the producer returns
- **THEN** every joint coordinate holds the value, binder and placement it
  held before, and rendering it again reproduces the same pose

### Requirement: A running document's clock is a published name

Under a running root the producer SHALL bind `time` symbolically for the
serialization, so a version 5 document carries the free name `time` — and
NOT the animation variable `$t` — wherever the model reads the clock, and
SHALL publish that name as `program.clock`. A consumer running the machine
SHALL bind it to ELAPSED SIMULATION SECONDS, which never wrap; a consumer
with no run — a still capture, a thumbnail — SHALL bind it to ZERO, the
instant the rest pose is defined at.

Every other reading of an unbound `time` under a running root SHALL be
unchanged: outside the document producer it SHALL go on reading the bare
animation variable exactly as it does today, so the OpenSCAD path, a bare
render and a numeric pose are untouched.

The `animation` object of a version 5 document SHALL carry `fps` and
`frames` as it always has and SHALL omit `loop`, which a running base does
not have.

#### Scenario: A running document carries no animation variable

- **WHEN** a running root whose `simulate()` reads `self.time` is published
- **THEN** its document carries the free name `time`, declares it as
  `program.clock`, and no expression anywhere in the document reads `$t`

#### Scenario: The Python preview is unchanged

- **WHEN** a running root's `time` is read outside a simulation and outside
  the document producer
- **THEN** it reads exactly what it read before this change

### Requirement: The two runtimes share a conformance corpus

The framework SHALL provide a generator that writes a JSON conformance
fixture from its own run, covering a set of small running roots, and the
framework's own suite SHALL replay that committed fixture and reproduce it.
The fixture is the contract between the framework's run and any other
runtime executing a published program: every expected value in it SHALL be
a value the framework's run PRODUCED, never a value recomputed a second way,
so a disagreement means the other runtime drifted.

The fixture SHALL carry, per machine: its name, its `dt`, the published
document's program-bearing keys — `format`, `version`, `drivers`,
`instructions`, `bindings` and `program` — verbatim; a SCRIPT of commands
(moves by a travel or to a value, rates, instruction triggers, a snapshot
and a restore) each naming the tick it is applied before and the handle its
outcomes are reported under; and EVERY TICK of the run, oldest first, each
carrying the whole committed bank, the crossings located in that tick, the
stops located in that tick, and every command created so far with its status
and the travel it has admitted. A sampled fixture SHALL NOT be accepted: a
divergence that heals between two samples is a divergence.

Agreement SHALL be EXACT for discrete state — tick numbers, command
statuses, coordinate, relation, primitive, bound and input names, crossing
surface levels, and the ORDER of every list — and within a stated RELATIVE
tolerance for floats: the bank's values, a crossing's or stop's fraction of
the tick, a stop's evaluated bound and a command's admitted travel. That
tolerance SHALL be the run's own agreement window, the same number the
document publishes as `program.limits.agreement`, because a consumer inside
it cannot manufacture a disagreement the run itself would not.

The generator SHALL REFUSE to write a corpus that does not exercise each of:
the five discontinuous primitives, a multi-source law, a stop located inside
a tick, a bound stated as an expression, a command retired `blocked`, a
rate, a snapshot and restore, an instruction in each of its two forms, and a
tick carrying both a crossing and a stop. The framework's suite SHALL test
that refusal directly, so the corpus's width is visible without running the
generator.

A framework test SHALL assert that each fixture machine's REAL published
document reproduces the fixture's own program-bearing keys, so the fixture
cannot drift from the producer it claims to come from.

#### Scenario: The framework reproduces its own corpus

- **WHEN** the committed fixture is replayed through the framework's run,
  machine by machine, applying each script entry before the tick it names
- **THEN** every tick's bank, crossings, stops and command outcomes match the
  fixture, exactly for discrete state and within the stated relative
  tolerance for floats

#### Scenario: The corpus carries the document it was run against

- **WHEN** a fixture machine's document is published afresh
- **THEN** its `program`, `drivers`, `instructions` and `bindings` equal the
  fixture's copy

#### Scenario: A corpus missing a primitive is refused

- **WHEN** the generator is asked to write a corpus whose machines contain
  no `%` law
- **THEN** it refuses naming the uncovered feature and writes nothing

#### Scenario: Every tick is present

- **WHEN** a fixture machine runs for forty ticks
- **THEN** the fixture lists forty tick entries, in order, with no gaps
