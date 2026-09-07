# ADR-080: A shared subexpression is named once — the document's bindings table

**Status:** Accepted

**Date:** 2026-09-07

**Change:** `expression-bindings`

**Extends:**
- [ADR-034: Shared node-tree document schema across export and build snapshots](ADR-034-shared-node-tree-document-schema.md)

**Depends on:**
- [ADR-022: Cross-Runtime Degree-Trig Parity for `$t` Expression Evaluation](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)
- [ADR-051: Producer-owned animation time in node-tree documents](ADR-051-producer-owned-animation-time-in-node-documents.md)

**Related to:**
- [ADR-056: Signals, drivers, ports, and stepped simulation](../NODE/ADR-056-signals-drivers-ports-and-stepped-simulation.md)
- [ADR-057: The flexible leaf, whose geometry travels as a spec](../NODE/ADR-057-the-flexible-leaf-and-spec-carried-geometry.md)
- [ADR-068: An optional viewer package behind a process boundary](ADR-068-optional-viewer-package-behind-a-process-boundary.md)

## Context

Every symbolic value in the framework is a solid2 `OpenSCADConstant`, and
`OpenSCADConstant` is string-eager: `__operator_base__` returns
`OpenSCADConstant(f'({self} {op} {other})')`. The text *is* the value, so a
value used twice is written twice, and a value used twice at each of ten
levels is written a thousand times. `DriverToken` subclasses it deliberately —
its docstring names string-eagerness as the reason, "no operator overloads and
no expression tree to maintain" — and `solid_node.math` dispatches on
`isinstance(x, OpenSCADConstant)` to wrap rendered arguments in call text.
Nothing anywhere holds a tree.

That was adequate until a machine reused enough. 3DPrintedClocks'
`wall_clock_53_grasshopper` publishes a `viewer.json` of 31,638,555 bytes, of
which 31,611,478 are operation expression text: 46 nodes, 76 operations, and
about seven million written subexpressions that are **263 distinct ones**. The
escape wheel's angle is 1.66 MB and is copied whole into fourteen operations;
the motion works' is 3.32 MB. Measured in the viewer: 7.65 s of one-time
parsing, 723 MB of parse trees retained, about two frames per second.

The consumer's half of that is being answered separately, by hash-consing
inside the viewer's evaluator with no format change, so documents already
published get their frame rate back. It cannot answer the wire: the redundancy
is in the document.

## Decision

**A subexpression that occurs more than once in a document's expressions is
published once, as a named entry in an ordered `bindings` table, and referenced
by name everywhere it occurred.**

- The table is a top-level JSON array beside `drivers` and `instructions`,
  each entry an object with a `name` and an `expression`, ordered so that an
  entry names only `$t`, qualified driver ids, and entries before it. A
  consumer evaluates it in one forward pass into the scope it already builds
  for `$t` and drivers, before any operation or `params` expression.
- An entry does not carry the inputs it depends on. The ordering is what makes
  them derivable, and derived state in a published contract can disagree with
  the expression beside it.
- A reference is the name written where an expression would be, marked by
  nothing. It is an ordinary name in the expression language.
- A bare number or a bare name is never bound: it is shorter written out than
  referenced. There is no other threshold.
- Names are `_b0`, `_b1`, … in table order. No name the expression language
  defines begins with an underscore and none begins with `$`, so only a
  qualified driver id can collide; when one would, the producer lengthens the
  prefix by an underscore and re-derives, rather than refusing a model for the
  names its drivers were given.
- A document carrying a non-empty table declares **version 4**. One carrying
  none omits the key and declares the version its content already needed, so it
  is byte-identical to the document published before this decision.

**Sharing is detected at serialization, by parsing the strings the producer
already built** — not by replacing the producer's algebra with an expression
DAG. The framework parses each expression once, interns it structurally across
the whole document, and emits the shared nodes.

**An expression the framework cannot read is published verbatim and unshared**,
with a warning naming the offending text and identifying the expression,
truncated. It does not fail the build. Every one of these expressions publishes
and renders today; sharing is an improvement to a working document, so an
expression the framework fails to understand costs only that expression's share
of the improvement. The producer refuses only a table that would be *wrong* — an
entry naming a later entry, a name colliding with a declared driver id, a
rewrite that does not reproduce what the producer built — which is a framework
defect rather than a project's fault.

**The consumer's rules travel with the schema**, because the viewer's half is
written from it. A binding name resolves as a binding *before* it is judged an
undeclared driver id, and dependence flows through the table: an expression
naming a binding depends on every input that binding transitively depends on, so
an operation whose whole expression is a binding name over `$t` is still a
time-dependent operation. Every other name means exactly what it means today.

**Nothing of the `.scad` path changes.** Operations reach OpenSCAD through
`operation.scad(...)` and a port through `port.value`, never through
`operation.serialized` or `flexible_document()`, so the generated SCAD keeps
the flattened expression it has today, `Solid2Node.as_number`'s `echo(...)`
round-trip still resolves, and the table never has to be expressed in OpenSCAD.

## Alternatives Considered

**OpenSCAD `let()` in the document.** The obvious way to name an intermediate
value in a language the document already resembles. Rejected by the pilot: the
project began with OpenSCAD as a core broker and that dependency is being
removed in steps, so the document format must not grow more OpenSCAD grammar. A
table is a table; `let()` is a language feature every consumer would have to
parse.

**Build a DAG from the start** — replace the `OpenSCADConstant` strings
flowing through `solid_node.math`, `DriverToken`, `read_time` and the ports
layer with an expression type whose operators intern nodes. It is the
structurally cleaner answer and it is *linear* where this one is not: the flat
text would never be materialised. Rejected for this cycle on three grounds.
First, it still needs a parser: solid2 remains the algebra for everything the
framework does not own — `__abs__`, the comparison overloads, `scad_inline`,
and any project reaching solid2 directly — so a mixed expression must be
parsed or refused, and refusing breaks working projects. Second, its blast
radius covers `math.py`'s entire dispatch, the driver token whose design
*depends* on string-eagerness, the ports layer, and
`FlexibleNode._time_fed_ports`, which detects a time-fed port by comparing
`str(get_animation_time())` against a port's value — a string comparison a lazy
type breaks silently. Third, parsing can be proved correct against the
flattened string the shipped producer actually emits; replacing the producer
means the parity claim is against itself.

The cost of the route taken is that the producer still builds the exponential
text and this decision then reads it: measured, 3.95 s and about 100 MB peak on
the grasshopper document, against a CAD build measured in minutes. The
follow-up — an expression type that keeps the flat `value` byte-for-byte while
also carrying the interned node, so serialization reads the node instead of
parsing for it — is strictly additive on this schema and should be proposed
when a build time is measurably hurt, not before.

**An additive key, no version bump**, as `instructions` and `animation.loop`
were. Rejected: those were additive because a consumer ignoring them still
renders correctly. A consumer ignoring `bindings` resolves `_b56` to nothing
and places the machine in a wrong pose. Silence is what the version ladder
exists to prevent.

**A size threshold** — bind only a subexpression above some number of
characters. Rejected: it puts a number in the format's behaviour that nobody
can derive, and it lets a document keep a megabyte of duplication just under
the line. "More than once, and not a bare number or name" needs no tuning.

**An object keyed by name instead of an array.** Rejected: the order is the
contract, and JSON says nothing about an object's key order.

**A `--flat-expressions` opt-out** for older viewers. Rejected: it would keep
two published forms in parity forever, and the flat form is the defect.

## Consequences

- Measured on the real document at implementation (`tasks.md` 6.3, superseding
  the design-time prototype's estimate): the grasshopper document's expression
  text falls from 31,611,478 bytes to 3,130 — 10,099.5× — and the document from
  31,638,555 bytes to 32,227 — 981.7×. 56 bindings are published; the longest
  is 212 characters. Numeric parity is exact: all 116 operation scalars at
  three values of `$t` (no driver is declared), checked against the flattened
  document — 348 checks, 0 mismatches. Nothing but `bindings`, `version` and
  the expression strings themselves differs between the two documents.
- A consumer that cannot resolve the table refuses the document, by version,
  in the phase where it already refuses an unknown version — before the live
  scene is touched. That is the correct failure, and it is why the bump is not
  additive.
- **The refusal is wide.** With no size threshold, one subexpression repeated on
  two nodes makes a document version 4, and `$t * loop` reaching two operations
  already does it — so nearly every animated model becomes version 4 on its next
  build, not only a grasshopper-sized one. Between this decision landing in the
  framework and the paired viewer change landing, `solid develop`, the shop
  floor's live viewer and the standalone export page refuse almost every
  animated model. Integrating the framework half first is therefore a decision
  to take deliberately, with the alternative of holding it until the viewer half
  is ready.
- The framework cannot negotiate with the consumer: `solid build` publishes
  `viewer.json` in installations that have no viewer at all, the viewer being
  an optional extra (ADR-068). Compatibility is the version ladder plus, once
  there is a released viewer version to name, a floor on the `viewer` extra;
  the extra stays unbounded until then, because nothing is published to pin
  against.
- `solid snapshot --renderer web` keyframes and bakes constants, so its staged
  document shares nothing, carries no table, and stays at version 2 or 3 with
  any viewer. The shop floor's hub previews go through it and are unaffected.
- The parity fixture gains the table, and its coverage check — the guard that
  no name in `SYMBOLIC_BUILTINS` reaches a published document without a case
  behind it — must read the bindings and the cases together, or an emitted
  builtin could hide inside an entry.
- The framework now owns a parser for the expression language it emits. That
  language was previously written down only as the union of two producers'
  behaviour; making it readable makes it explicit. The parser never guesses and
  never blocks: what it cannot read goes out unchanged, so the worst case is a
  document exactly as large as the one published today.
- The version stays a linear ladder rather than becoming a capability list.
  Consumers accept by membership in a set, so a version-4 document with no
  flexible leaves costs a conforming consumer nothing; replacing the version
  with capabilities is a separate format decision this one does not foreclose.
