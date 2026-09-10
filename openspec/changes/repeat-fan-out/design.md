## Context

The couplings layer (ADR-089) resolves each end of a relation to exactly
one coordinate, at the end of the declaring instance's construction, and
solves the class's relations in a fixpoint at the end of that instance's
simulate phase. `.repeat(n)` (ADR-061/ADR-063) realizes n identical
copies of one declaration, named `<attr>-<index>`, sharing one `uniq_id`
and one cached artifact. The two have never met: `read_through` and
`coordinate_ref` refuse a repeated declaration outright, and
`RepeatDeclaration.__getattr__` raises `SidewaysReadError`.

The relevant code, all in this worktree at base `5b28510`:

| Seam | Where | Today |
|---|---|---|
| reading a coordinate off a repeat | `declarative.py:305-317` | `SidewaysReadError`, advising "state the relation inside the repeated class" |
| reading a repeat through a child | `couplings.py:576-583` (`read_through`) | `TypeError`, same advice |
| the repeat as a bare end | `couplings.py:1073-1078` (`coordinate_ref`) | `TypeError`, same advice |
| the walk finding a list | `couplings.py:494-509` (`PathRef._step`) | `CouplingError`, same advice |
| resolving a relation | `couplings.py:904-918` (`Relation.resolve`) | returns exactly one `RelationRecord` |
| the fixpoint | `couplings.py:1213-1247` (`solve_relations`) | iterates a flat list of records |
| the law | `couplings.py:909-911` | `self.callable_law(driver.node, driven.node)`, once per instance |
| the copies | `declarative.py:329-337` (`RepeatDeclaration.realize`) | `[decl.realize(values, owner) for _ in range(count)]` |
| the reader | `ports.py:385-399` (`set_coordinate`) | a writer, and no reader beside it |

The advice those four refusals give is unreachable for every sighting:
what the copies follow is a coordinate of the PARENT (or of a sibling),
and the repeated class cannot name it — ADR-061's sideways-read rule is
exactly what stops it.

## Goals / Non-Goals

**Goals:**

- One relation, written once in the parent's class body, drives every
  copy of a repeated child.
- A `law=` sees the copy, so a per-copy sign, phase or rank is one
  attribute read — with no change to the law protocol ADR-089 fixed.
- Every refusal keeps naming the relation, the path as written, and now
  also the copy.
- The dotted names ADR-095 made writable become readable.
- Nothing that is not rewritten moves: a pose comparison over every
  project that uses `.repeat()` with the motion layer.

**Non-Goals:**

- A repeated SOURCE, in any spelling. n copies hold n values.
- Inverting a broadcast, even when every copy happens to hold the same
  value: the framework does not compare values to decide whether
  statements agree (ADR-089).
- Indexing a repeat in a class body (`beads[2].travel`). A structurally
  different expression per copy is the Pascaline's finding and stays
  open; a per-copy SOURCE is InMoov's and closes with cycle 5.
- List-held children (`plates = [Left(), Right()]`) as a broadcast end.
  They are already distinguishable — each carries its own arguments and
  its own `uniq_id` — so a relation names one of them; a list-held end
  stays refused with its own message.
- Any change to how a copy's own joints compose (ADR-093) or to how a
  repeat is built, named, identified or omitted.
- A `count` on the copy (see Decision 3).
- A wiring keyword on `.repeat()` (see Decision 9).

## Decisions

### 1. A broadcast end is `BroadcastRef`, and it resolves to n records

`children.joint` as a driven end yields a **`BroadcastRef`**, a
`CoordinateRef` beside `PathRef`, holding the same `(root, segments,
terminal)` triple plus the position of the repeated segment. Class
definition validates it exactly as `PathRef` does — every segment
checked against the class the previous one names, the terminal resolved
to one coordinate by the same `declaration()` walk — because the
CLASSES are all known there and the repeat changes only how many
instances the path lands on.

At realization, `Relation.resolve(instance)` returns **n
`RelationRecord`s**, one per realized copy, rather than one. Alternatives
weighed:

- *One broadcast relation object holding n ends* — rejected. Every step
  of the solver (`_step_relation`, `_claim`, `_refuse`, `_binder_of`)
  would need a second shape, `DoublyBound` would have to say which copy
  it meant through a new mechanism, and the ADR-089 sentence "Relations
  declared on a class SHALL apply per instance … each realized instance
  SHALL resolve, solve and refuse its own" would stop being literally
  true.
- *n records* — chosen. `resolve_declared_relations` flattens; the
  fixpoint's `records` list is flat as it is today; `_solved_formulas`,
  `_claim`, `_step_relation` and `_refuse` are untouched; each copy's
  relation is independent, so a copy whose end is doubly bound is
  refused naming that copy and the other n-1 still solve.

**`repr` and reading a named relation.** Off the CLASS, the declaration
reads as it does today, with the written path: `<relation
eccentric_shaft.spin drives eccentric_bearings.orbit>` — the count is a
property of the instance, not of the class, so the class-level `repr`
states no count. Off an INSTANCE, a named broadcast yields a **tuple of
records in copy order** (an empty tuple for a zero-count repeat), where a
named ordinary relation yields one record; a test reaching
`instance.some_relation[2]` gets copy 2's record with its own
`direction`. Each record's `described()` appends the copy it applies to,
so `DoublyBound` reads `… the relation 'orbit_drive'
(eccentric_shaft.spin drives eccentric_bearings.orbit, copy
eccentric_bearings-2) …`. The driven end's own `described()` already
resolves through `where(node)` to the copy's tree path, so the two agree.

**Serialization: nothing.** ADR-089 settled that a relation is not
published in the document; a broadcast lowers to the same operations n
hand bindings produce, carrying whatever value — number or expression —
each copy was solved with. No document key, no schema version, no viewer
change.

### 2. One repeated segment, anywhere in the path

A path may pass through **at most one** repeated segment. All of these
are one fan-out and all are allowed:

```python
earth.drives(beads.travel)              # the repeat is the first segment
earth.drives(beads)                     # …standing for Bead's ONE joint
drive.drives(column.beads.travel)       # a repeat one level down
yaw.drives(legs.femur.lift)             # a plain child under the copies
```

The rule is stated once instead of per position: `read_through` returns a
`RepeatDeclaration` as a PLACE rather than refusing (the same relaxation
ADR-095 made for a multi-coordinate joint), `PathRef.__getattr__` yields
a `BroadcastRef` when it steps onto one, and `BroadcastRef.__getattr__`
keeps walking and **refuses a second repeat by name**, naming both
repeated segments and saying a broadcast fans out over one repeat because
n×m relations from one sentence is not a thing a reader can count.

Rejected: allowing the first segment only. `column.beads.travel` would
have stayed refused with no reason a reader could give, and the
one-repeat rule is not harder to state than the first-segment rule.

`PathRef._step`'s list refusal survives for **list-held** children, whose
message becomes its own (a list-held child is named one by one), and
`BroadcastRef`'s own walk expands the list of copies instead of refusing
it.

### 3. The copy carries `index`, and not `count`

`RepeatDeclaration.realize` stamps `child.__dict__['index'] = i` on each
copy, **after** it is constructed. `index` is a plain instance attribute:
not a declared parameter, not in `_parameters`, not in `identity_values`,
so `uniq_id` is untouched and `repeat` still means one geometry and one
cached artifact. `_attr_name_for`'s scan of `__dict__` is unaffected —
an `int` is not a child node.

**Not `count`.** The walkthrough ratified "its `index` (0-based) and the
count". Two things force it out:

- The abacus declares `halves = FrameHalf(count=count, …).repeat(2)`
  and `FrameHalf` declares `count = Count(9, min=1)` of its own
  (`Vibecoded-demos/abacus/abacus/frame.py:35-43`,
  `frame_half.py:21`). A declared parameter is a data descriptor, so a
  framework-set `count` in the instance dict is **silently invisible**:
  measured in `evidence/probe_shadow.py`, `h.__dict__['count']` is `2`
  while `h.count` reads `9`. Refusing the name instead would refuse a
  model the catalogue already contains.
- No sighting's law reads it. OpenCycloid's sign is `index < 2`, the
  abacus's rank is `index`, the V8's phase is `THROW_PHASES[index]`,
  fender-bender's offset is `channel_y(index)`; each takes its n from a
  module constant or a parent parameter. Thor's bearing cage even
  declares `count = Count(36)` on the PARENT and repeats
  `BearingBall` — the count already lives where the repeat is written.

A second sighting can add `count` (under whatever name survives the same
survey) exactly as ADR-093 made the slot keyword wait for one.

**A repeated class that answers to `index` is refused where the repeat
is written.** `RepeatDeclaration.__set_name__` asks
`getattr(node_class, 'index', None)` — which catches a declared
parameter, a port, a joint, a child declaration, a property or a plain
method — and raises naming the declaring class, the attribute, the
repeated class and what it found, advising that the parameter be renamed
or the children declared in a list. Silence is the alternative, and the
probe above is what silence looks like. Surveyed (grep for a class-body `index =` declaration across the
whole project catalogue, 2026-09-10): 3DPrintedClocks' arbor ranks
(`index = Count(...)` on arbor and moon-arbor part classes of eight
clocks, none of which uses `.repeat()`), and InMoov's `Hand`, which
declares `index = Driver(...)` for the index FINGER — on the PARENT of
`fingers = Finger().repeat(4)`, not on the repeated `Finger` class, so
it is not refused either. Nothing existing is refused; the InMoov case
is also the reminder that `index` is an ordinary word a machine may
already use, which is why the refusal names what it found.

**When it is set.** After the copy's own `__init__` has returned, so a
law declared INSIDE the repeated class cannot read it (that law runs at
the end of the copy's own construction), and neither can the copy's own
joint arguments or `check()`. No sighting needs either: every broadcast
law is declared on the PARENT and called at the end of the parent's
construction, after `realize_children`. Rejected alternative: a
module-level "realizing copy i" slot consumed by
`AbstractBaseNode.__init__`, which would make `index` available during
construction — rejected because a legacy (non-declarative) child calls
`super().__init__()` LAST, after building its own children, so the slot
would be consumed by the wrong node. If cycle 2's callable joint
arguments turn out to want a per-copy anchor, that is a change with its
own sighting, and it will need the constructor form solved properly.

**Reading `index` in the copy's own `render()`.** It is a plain
attribute and nothing forbids it, but a rigid leaf whose GEOMETRY
depends on it would produce n different shapes under one `uniq_id` and
one cached artifact — the `declarative-nodes` rule "Repeated identical
children SHALL share one `uniq_id` and one artifact" is a promise about
the geometry, and the framework cannot tell a geometry read from a
placement read. So the spec states the rule where it belongs — per-unit
GEOMETRY is not what `repeat` means, and a part that differs
geometrically is declared in a list — and the cycle adds no runtime
guard. Note that the sighting cited for this want, OpenCycloid's
per-index translate, is the PARENT's loop over the realized copies
(`actuator.py:72-74`), which needs nothing from this cycle and keeps
working unchanged.

### 4. The law's signature does not change

ADR-089: `law=` is "a CALLABLE of two arguments, which the framework
SHALL call exactly ONCE for each realized instance of the declaring
class, at realization, with the realized nodes that OWN the two
coordinates — driver first, driven second." Under a broadcast the owner
of the driven coordinate **is the copy**. So:

```python
def earth_lift(column, bead):                 # unchanged signature
    stroke = column.stroke
    rank = bead.index                         # the copy, not the repeat
    return ForwardOnly(lambda level: clamp(level, rank) * stroke)
```

The callable is called **once per copy** instead of once per instance,
at realization, and each copy's returned law is that copy's law for
every later run. ADR-089's "A law runs once, not once per instant" is
preserved exactly: n calls at realization, zero per instant. Every
existing law is untouched, because every existing law is called against
a relation that resolves to one record.

Rejected: a third argument, or an `index=` keyword sniffed by
`inspect.signature`. Both would make the framework inspect something
about a law beyond `forward`/`inverse`, which ADR-089 forbids in as many
words, and the copy already carries what the law needs.

### 5. `ratio=` and `offset=` under a broadcast

Every copy gets **the same** affine law. `ratio=`/`offset=` are resolved
ONCE against the declaring instance's `_parameters` (the same `evaluate`
call as today) and the resulting `Affine` — a frozen, stateless value —
is shared by the n records. Per-copy variation through `ratio=` is not
offered: a ratio is a number or a token of the declaring class, it has
no way to see a copy, and `law=` is what per-copy variation is for.

### 6. A repeated end is never a source, and never inverted

Two separate refusals, at two moments:

- **As a SOURCE, at class definition.** `BroadcastRef.check('driver')`
  raises `TypeError` naming the written path, the repeated declaration,
  the class and the count as written, and saying a relation's source is
  one value while n copies hold n; it advises binding the source from a
  coordinate the parent holds, or stating the relation inside the
  repeated class. `RepeatDeclaration.drives` is added for the same
  reason `ChildDeclaration.drives` exists: without it,
  `beads.drives(x)` would take the `drives` attribute through
  `__getattr__` and produce a nonsense path error instead of this one.
  A `BroadcastRef` also refuses the derived-coordinate arithmetic
  (`beads.travel - x`) by name: a formula has one value per term.
- **As the DRIVEN end already bound, at solve time.** `_step_relation`
  never reads a broadcast record backwards, whatever the law offers;
  `_refuse` raises **`NotInvertible`** naming the relation, the copy,
  the bound coordinate and its binder, and saying that a broadcast is
  read forward only because the n copies would have to agree on one
  source value and the framework does not compare values to decide
  whether two statements agree. `NotInvertible` is reused rather than a
  new error kind added: the question a project catches it for — "this
  relation cannot be read backwards" — is exactly the same, and the
  message says which of the two reasons applies.

An `Affine` with a numerically-zero ratio is refused by the existing rule
before any of this; nothing changes there.

### 7. Where the n records sit in the solver

`solve_relations` iterates `records` in order, repeatedly, to a fixpoint.
A broadcast's n records occupy **the position of the declaration**, in
copy order, so a class that declares `A; broadcast; B` iterates
`A, copy-0, copy-1, …, copy-n-1, B`. The couplings spec's "Within one
pass the order SHALL be declaration order" therefore holds with copy
order as the tie-break inside one declaration, and — as ADR-089 says of
declaration order generally — the determinism is there for the messages,
not for the answer: the fixpoint makes the result order-independent.

ADR-093's joint **slots** are untouched and are a different axis: a slot
orders the joints of ONE body, and a broadcast binds one coordinate of
each of n bodies, through `set_coordinate` — the same binding path a
hand binding takes, so each copy's joints compose in their declaration
order innermost-first exactly as they do today. Two broadcasts over the
same repeat (a copy's `spin` and its `orbit`) are 2n independent
records, and the copy's composition still does not depend on which of
them bound first.

**Zero copies.** `.repeat(0)` is legal declared structure
(`declarative-nodes`, "A zero repeat remains declared structure"). A
broadcast over it resolves to ZERO records: it binds nothing, refuses
nothing, and leaves its source exactly as it found it. This is stated
rather than discovered, because "a relation that silently does nothing"
is otherwise the kind of thing a reader finds out from a wrong pose.

**Omitted copies.** `omit()` is a render-time selection and ends resolve
at realization, so a broadcast covers every copy the repeat REALIZED,
omitted or not. Binding an omitted copy places a body that is not
assembled; it refuses nothing and changes no pose. Stated for the same
reason.

### 8. `get_coordinate`, and what it does with an unknown name

```python
def get_coordinate(node, name):
    """The bound slot of the coordinate `name` of `node`, whatever kind
    of name it is."""
```

Exported from `solid_node.motion.ports` beside `set_coordinate`, and
mirroring it segment for segment: a name of one part is an attribute of
the node, a name of several (`pose.roll`) is the head read and the tail
taken off what it yields.

- **What it returns**: the `BoundPort` slot, which is what
  `node.turn` and `node.pose.roll` already yield — so the reader is the
  read an author already writes, reachable by a name held in a variable.
  A slot nothing has bound is a real slot whose `value` is `None`.
  Rejected: returning the VALUE, or returning `None` for an unbound
  slot. Both conflate "unbound" with "no such coordinate", and both
  throw away the domain, unit and scale that the consumer enumerating
  `declared_ports` is usually there for.
- **A name the enumerator does not report**: refused by name, naming the
  node, the name asked for and the names `declared_ports(type(node))`
  does report. Rejected: answering `None`. `set_coordinate(node,
  'bogus', 1)` silently creates an instance attribute today, and a
  reader that answered `None` would make the writer/reader pair silently
  wrong in both directions rather than in one. The membership test is
  against the enumerator, not against `getattr`, precisely so that a
  declared PARAMETER named like a coordinate cannot answer for one.

The ports requirement gains the sentence the wart asks for: a name the
enumerator reports is a name the framework can read back, and the pair
that guarantees it is `set_coordinate`/`get_coordinate`.

### 9. No wiring keyword on `.repeat()`

§3.1 as ratified listed `.repeat(n, travel=column.travel)` as "the
weakest form and the one to build first". It is already the contract.
`evidence/probe_wiring_repeat.py`, on this tree:

```python
class Column(AssemblyNode):
    earth = SignalPort()
    beads = Bead(travel=earth).repeat(4)      # travel is a WIRING
    def simulate(self):
        self.earth = 3.0
# beads: ['beads-0'…'beads-3']  travels: [3.0, 3.0, 3.0, 3.0]
# uniq: {'Bead-aa06a2f044b4'}   ops: [1, 1, 1, 1]
```

`ChildDeclaration.__init__` recognises a wiring by its VALUE,
`RepeatDeclaration._adopt` validates it once for the held declaration,
and `realize` records it on every copy — which is the ports spec's own
scenario "A repeated child is wired per instance". The fixpoint question
the briefing asks — what happens when the wired coordinate is itself
bound later in the same pass — was settled by ADR-089 and is unchanged
here: a wiring is a forward-only identity relation inside the same
fixpoint, so it waits an iteration and binds once its source is solved
(ports, "A wiring binds after the relation that solves its source"), and
an unbound source when propagation has FINISHED is still refused by name.

What a wiring cannot do is take its source from a PATH — `column.travel`
where `column` is a sibling child — because a wiring is downward-only
and its source must be a coordinate the declaring class itself declares
(`ChildDeclaration._check_wiring`). That case is exactly a broadcast
relation with the default ratio of one, which this cycle builds:
`column.travel.drives(nuts.travel)`. Adding the keyword would give the
first case a second spelling and the second case nothing.

## Risks / Trade-offs

- **A broadcast makes one written line into n bindings, and a reader
  counts them nowhere.** → The count is a property of the instance, so
  every message that mentions a broadcast names the COPY it is about,
  and a named relation read off an instance is a tuple whose length is
  the count. The docs passage shows the loop it replaces beside it.
- **`index` is a plain attribute and could be shadowed by a future
  declaration.** → Refused where the repeat is written, with the probe's
  own silence as the reason in the message. Surveyed against the whole
  catalogue: nothing existing is refused.
- **A rigid leaf could read `index` in `render()` and build n shapes
  under one artifact.** → Not detectable by the framework; stated in the
  spec as what `repeat` means, with the list form as the answer. No
  sighting does it: every per-index render loop in the catalogue is the
  parent's, over the realized copies.
- **`read_through` returning a repeated declaration as a place widens
  what a class body may name.** → The widening is exactly ADR-095's, for
  the same reason (a place is not a value), and the SOURCE side is
  refused by name at the same moment it was refused before, with a
  better message.
- **n law calls at realization instead of one.** → Realization-time
  only, once per instance, never per instant; the largest repeat in the
  catalogue is Thor's 36 bearing balls, which declares no relation.
- **A pose could move where a project's `.repeat()` children are bound
  today.** → Nothing in this cycle binds anything a project did not bind
  before; the proof is the pose comparison over all fourteen `.repeat()`
  projects at the base and at the head (tasks §6), not an argument.

## Migration Plan

Additive: every refusal that becomes a broadcast was a hard error, so no
project can have depended on it. Rollback is reverting the cycle; no
project code is edited here, and the two validation projects (OpenCycloid
and the abacus) are refactored at stage B in their own repositories.

## Open Questions

For the pilot, none blocking:

1. **`count` on the copy** is deferred for want of a sighting AND
   because `count` is a name the catalogue already uses on a repeated
   class. If a law ever needs n, the name will have to be chosen against
   the same survey — `repeat_count` is the obvious candidate, and it is
   ugly. Recorded, not decided.
2. **Reading a named broadcast off an instance yields a tuple.** An
   alternative is a small view object that could answer `len()` and
   `direction` collectively. No test needs it; a tuple is what the
   fixture will use.
3. **A list-held child read in its OWN class body** — `plates.turn`
   where `plates = [Left(), Right()]` is declared on the same class —
   raises a bare `AttributeError: 'list' object has no attribute 'turn'`
   with no framework advice, because a class-body list is a Python list
   and not a declaration object (measured,
   `evidence/probe_list_held_today.py`). Reached through a child
   (`frame.plates.turn`) or passed whole (`drives(plates)`) it does get
   the framework's message. Pre-existing, small, and not this cycle's;
   recorded so the next reader does not mistake it for a regression.
4. **A broadcast whose driven end is a WIRED coordinate of the copies**
   is refused per copy by the existing `_claim`, naming the wiring and
   the relation. That is the right answer, but the message will name one
   copy's wiring and not all n; left as is.
