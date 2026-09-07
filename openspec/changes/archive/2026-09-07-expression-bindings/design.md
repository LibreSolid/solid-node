## Context

Every symbolic value in the framework is a solid2 `OpenSCADConstant`, and
`OpenSCADConstant` is string-eager:

```python
def __operator_base__(self, op, other):
    return OpenSCADConstant(f'({self} {op} {other})')
def __unary_operator_base__(self, op):
    return OpenSCADConstant(f'({op}{self})')
```

`$t` enters as one (`assembly.read_time` → `get_animation_time() * base.loop`),
a driver enters as `DriverToken(OpenSCADConstant)` whose string is its
qualified id, and `solid_node.math._symbolic_call` wraps rendered arguments in
`f'{name}({rendered})'`. Nothing anywhere holds a tree; the text **is** the
value. So a value used twice is written twice, and a value used twice at each
of ten levels is written a thousand times.

Serialization is one funnel. `serializer.serialize_node` writes
`[operation.serialized for operation in node.operations]`, and
`Rotation.serialized` / `Translation.serialized` are `str(self.angle)` /
`[str(x) for x in self.translation]`. The only other place expression text
enters a document is `FlexibleNode.flexible_document()['params']`, from
`bound_expressions()`, which is `str(port.value)` per port. Two call sites,
one document.

Three producers wrap that walk: `core/export.py` (`manifest.json`),
`core/builder.py` (`_build/<model>/viewer.json`) and `viewers/browser.py` (the
web-snapshot staging document). The first two serialize under
`symbolic_document`, so their expressions are symbolic. The third keyframes
first, so its expressions are constants.

Measurements below are from the published grasshopper document
(`projects/3DPrintedClocks/_build/wall_clock_53_grasshopper/viewer.json`,
31,638,555 bytes, format version 2, 46 nodes, 76 operations, 116 operation
expression strings of which 30 are distinct, no drivers,
`animation.loop = 43200.0`) on the pilot's workstation with the workspace
venv's CPython 3.12. The prototype lives in this cycle's scratch and is not
committed.

## Goals / Non-Goals

**Goals:**

- A subexpression appearing many times is published once.
- The document is small enough to load and parse without the consumer
  retaining hundreds of megabytes of parse trees.
- Exact numeric parity: the document evaluates to what the flattened one
  evaluated to, at every `$t` and every driver value.
- No change to how a project writes kinematics, and no change to the
  algebra, the driver token, the time base or the ports layer.
- No change to the `.scad` path, to `as_number`, or to any numeric answer.
- A document with nothing to share is byte-identical to today's.
- The contract is specified well enough that the paired viewer change can be
  written from this spec.

**Non-Goals:**

- OpenSCAD `let()` in the document. The pilot has settled this: the project
  began with OpenSCAD as a core broker and that dependency is being removed
  in steps, so the document format must not grow more OpenSCAD grammar. A
  bindings table is a table, not a language feature.
- Making the producer stop *building* the flat text. That is a separate,
  later change (D1, "the follow-up"); this one makes the *document* small.
- A new expression language, new functions, or new operators. Every name and
  operator the table can carry is one the framework already emits.
- Compressing the document, deduplicating STL references, or anything else
  about its size that is not repeated expression text. On this document,
  repeated expression text is 99.9% of it.
- Any per-frame evaluation strategy. That is the viewer's, and
  `share-expression-subtrees` is already deciding it.

## Decisions

### D1. Detect sharing at serialization, by parsing — not by building a DAG from the start

Two routes were weighed.

**Route (a) — a DAG from the start.** Replace the `OpenSCADConstant` strings
flowing through `solid_node.math`, `DriverToken`, `read_time` and the ports
layer with a solid_node expression type whose operator overloads intern nodes
into a table. Sharing is then structural, free, and *linear*: the text is
never materialised at all.

**Route (b) — hash-cons at serialization.** Keep every string the producer
builds today. At serialization, parse each expression once, intern it
structurally across the whole document, and emit the shared nodes as a table.

**Route (b) is recommended.** The reasons, in order of weight:

1. **Route (a) still needs route (b)'s parser, and route (b) does not need
   route (a).** solid2 remains the algebra for everything the framework does
   not own. `OpenSCADConstant.__abs__` emits `abs(...)` as text with no
   overload of ours in the path; `__eq__`/`__lt__` and the rest emit
   comparisons; `scad_inline(code)` hands a project arbitrary text; and a
   project reaching solid2 directly — which the clock models did, before
   `solid_node.math` grew `floor` — produces a plain constant. Under route
   (a) any of those mixed into an expression is either parsed anyway or
   refused, and refusing is a breaking change to working projects. Route (b)
   reads every one of them, whatever produced it.
2. **Blast radius.** Route (b) touches `serializer.py` and adds one new
   module. Route (a) touches `math.py` (every `_symbolic_call` and the
   `isinstance(x, OpenSCADConstant)` dispatch that is its whole face),
   `qualified.DriverToken` (whose docstring names string-eagerness as the
   *reason* it subclasses `OpenSCADConstant` — "no operator overloads and no
   expression tree to maintain"), `assembly.read_time`, `node/ports.py`,
   `flexible.bound_expressions`, and `flexible._time_fed_ports`, which
   detects a time-fed port by comparing `str(get_animation_time())` against
   the port's value — a *string* comparison a lazy expression type breaks
   silently. It also risks moving the emitted `.scad` text, which would
   invalidate every artifact's currency for no behavioural gain.
3. **Route (b) is provably correct against the shipped producer**, because
   the check is a numeric comparison against the flattened string the
   producer actually emitted. Route (a) replaces the producer, so its parity
   claim is against itself.

What route (b) costs, stated honestly: **it does not remove the exponential,
it only stops publishing it.** Both routes leave the producer building the
flat text; route (b) then reads it. Measured on a synthetic chain in the
escapement's shape (each level reusing the level below four times):

| levels | flat text | producer builds | route (b) parses | interned nodes |
|--------|-----------|-----------------|------------------|----------------|
| 6      | 0.13 MB   | 0.00 s          | 0.03 s           | 54             |
| 8      | 2.05 MB   | 0.00 s          | 0.55 s           | 70             |
| 9      | 8.21 MB   | 0.02 s          | 2.20 s           | 78             |
| 10     | 32.86 MB  | 0.13 s          | 8.33 s           | 86             |

Both columns are exponential in the depth of reuse; route (b) multiplies the
producer's own cost by a constant (about 2.5× on the real document, up to
~64× on this adversarial synthetic, where a single expression carries no
cross-expression sharing to amortise). On the real document the whole pass is
**3.95 s** — against a CAD build that takes minutes — and the peak resident
set is ~100 MB, against the 31.6 MB document already in memory.

**The follow-up, recorded and not proposed here:** a `solid_node.expression`
type subclassing `OpenSCADConstant` that keeps the flat `value` byte-for-byte
(so `.scad`, `as_number` and `_time_fed_ports` are untouched) while also
carrying the interned node its operators built, letting serialization read the
node instead of parsing for it. That is strictly additive on top of this
change — same table, same schema, same tests — and removes the 3.95 s. It
should be proposed if and only if a machine's build time is measurably hurt
by this pass. Removing the exponential *entirely* is a third change, and it
cannot be done without answering what the `.scad` path writes, since OpenSCAD
receives the flat text by contract today.

### D2. What the parser must read

The grammar is small and completely determined by what the framework emits:

| form | producer |
|------|----------|
| `$t` | `solid2.core.builtins.$t` through `get_animation_time()` |
| `a.b.c`, `motor` | `DriverToken`, whose string is a qualified driver id |
| `208.47`, `1e-05`, `2` | `str()` of a Python number, exponent form included |
| `(A + B)`, `- * / % ^` | `OpenSCADConstant.__operator_base__` |
| `(A == B)`, `!= <= >= < >` | the same, from the comparison overloads |
| `(-A)` | `__unary_operator_base__` |
| `name(A, B)` | `solid_node.math._symbolic_call`, `SYMBOLIC_BUILTINS` only, plus `abs(...)` from `OpenSCADConstant.__abs__` |

Two properties make this easy and one makes it fast.

- solid2 **fully parenthesises**: every binary and unary operation is wrapped.
  Precedence is therefore never load-bearing in text the framework produced.
  The parser implements precedence climbing anyway, so a hand-written
  `scad_inline` string that omits parentheses is still read correctly rather
  than silently misgrouped.
- `^` is exponentiation with OpenSCAD's binding, and the viewer already
  rewrites it to `pow`. The framework's table publishes `^` as it publishes it
  today; the rewrite stays the consumer's, unchanged.
- **Python's `ast` cannot be used.** It cannot read `$t`, it reads `^` as
  bitwise xor, and it would silently accept Python semantics for `%` on
  negative operands. The parser is ~150 lines of stdlib.

**An expression the parser cannot read is published verbatim and unshared**,
with a warning naming the offending text and identifying the expression —
truncated, since a published expression may be megabytes. It does not fail the
build.

That is the load-bearing choice of this decision, and it is the opposite of the
first draft. Every one of these expressions publishes and renders today. Sharing
is an *improvement* to a working document, so a model that produced a working
document yesterday must produce one tomorrow, and the cost of an expression the
framework cannot read must be confined to that expression losing its share of
the improvement. A parser that failed the build would turn an internal
optimisation into a new way for a project to stop working — over a grammar
inferred from two producers, which a `scad_inline` string is free to sidestep.

The producer refuses only when the table it would publish would be **wrong**: an
entry naming a later entry, a binding name colliding with a declared driver id,
or a rewritten expression that does not reproduce what the producer built. Those
are framework defects, not a project's fault, and publishing past them would put
a wrong pose on the wire.

**Speed comes from a substring memo.** Because the producer builds text by
concatenation, structurally identical subexpressions have *identical text*.
Before looking at a character of a parenthesised group, the parser checks the
group's source substring against a memo. The escape wheel's 1.66 MB
subexpression is therefore parsed once and hit thirteen times as a dictionary
lookup. Measured on the real document: 163 memo misses, 90 hits, 78.5 MB of
characters actually scanned out of 31.6 MB of text visited across 116
expressions.

The memo is only a fast path; the **interner is structural**, keyed on
`(kind, operator-or-name, child ids)`. So two spellings of one structure
(`(1.0 + 2.0)` from solid2 and `1.0+2.0` from a hand-written `scad_inline`)
cost two parses and still become one node.

### D3. The document's shape

A new top-level key beside `drivers` and `instructions`:

```json
{
  "format": "solid-node-export",
  "version": 4,
  "animation": {"fps": 30, "frames": 360, "loop": 43200.0},
  "drivers": {},
  "instructions": {},
  "bindings": [
    {"name": "_b0", "expression": "($t * 43200.0)"},
    {"name": "_b1", "expression": "((2 * _b0) / 1.5)"},
    {"name": "_b2", "expression": "floor((_b1 - 1.0))"},
    {"name": "_b3", "expression": "(_b2 - (2 * floor((_b2 / 2))))"}
  ],
  "root": {"operations": [["r", "_b56", [0, 0, 1]]]}
}
```

**An ordered array, not an object.** Order is the contract — an entry refers
only to `$t`, to driver ids, and to entries before it — and JSON says nothing
about an object's key order. An array states the invariant in the format
rather than relying on a runtime's insertion-order behaviour.

**Objects, not two-element arrays.** `["_b0", "($t * 43200.0)"]` is terser and
matches how an operation serializes, but the table is now three kilobytes
whole; the twenty bytes an entry spends on its own key names buy a
self-describing document and room for a later additive per-entry key without
a version bump.

**Entries do not carry their free inputs.** The consumer derives them, and the
ordering guarantee is what makes one forward pass enough: an entry's inputs
are the names it mentions, union the inputs of the entries it names. Carrying
them would be derived state in a published contract, able to disagree with the
expression beside it, for a saving that no longer matters at three kilobytes.

**A reference is a name where an expression would be.** Nothing marks it; the
name is an ordinary identifier in the expression language, resolved exactly as
`$t` and a driver id are resolved — from the scope the consumer already
builds. This is why the naming rule below has to be airtight.

### D4. Names: `_b0`, and a prefix that cannot collide

Names are `_b<N>`, N counting from 0 in table order.

Three namespaces meet in a consumer's evaluation scope: `$t`, the qualified
driver ids, and the math context's function names. A binding name must miss
all three.

- `$t`: no name begins with `$`.
- Math context: every name it defines (`sin`, `cos`, `pow`, `min`, `floor`, …)
  is a bare lowercase word. None begins with an underscore. Nothing to check.
- Driver ids: `driver_id` builds them from `[A-Za-z_][A-Za-z0-9_]*` segments,
  so a node could legally declare a driver called `_b0`.

Rather than reserve the spelling — which would refuse a legal model for a
choice of attribute name, and would have to be enforced in `driver_id`, far
from where the collision happens — **the serializer picks a prefix that is
free in this document**. It knows the whole driver table at the moment it
builds the bindings: start at `_b`, and while any qualified driver id matches
`<prefix>\d+`, prepend one underscore and check again. Deterministic, terminates
in at most one step in practice, never fails, and the document is
self-describing because the names it uses are written in it.

Names are short deliberately: 57 names each appearing several times, in a
table whose whole point is size.

### D5. Everything shared is bound; a bare number or name is not

The rule is an outcome, not a threshold: **a subexpression occurring more than
once anywhere in the document's expressions is published once as a binding
and referenced by name, unless it is a single number or a single name.**

- *Occurrences*, not distinct parents: `(big * big)` shares `big` with itself
  and must bind it.
- The exception is arithmetic, not taste. A reference costs four characters;
  `2` and `x_axis.motor` are shorter written out, and naming them would make
  the table longer than what it saved.
- No tunable size threshold. One was considered and rejected: it would be a
  number in the format's behaviour that nobody could derive, and it would let
  a document keep a megabyte of duplication just under the line.

**Why this rule, given the memoized viewer.** After
`share-expression-subtrees` the viewer already resolves each *distinct*
subexpression once per pass, so the table cannot improve the frame cost. Its
job is the wire and the load: 31.6 MB and 7.65 s of parsing become ~30 kB and
milliseconds. Binding every shared node minimises both, and costs the viewer
nothing — it is the same DAG the viewer would have hash-consed, handed over
already built.

Ordering falls out of the interner: a child is always interned before its
parent, so ascending node id is a topological order, and the table is emitted
in it. That also makes the table **deterministic**, which
`builder._write_viewer_snapshot` needs — it compares the serialized document
byte-for-byte against the published one to decide whether to republish.

### D6. Version 4, and the key is absent when there is nothing to bind

`document_version()` keeps its shape: the LOWEST version the finished content
needs, read off the document rather than tracked while building it.

- A document whose bindings table is non-empty → **4**.
- Otherwise → 3 if it holds a flexible node, else 2, exactly as today. The
  `bindings` key is **omitted**, so the document is byte-identical to the one
  the framework publishes now. This follows `animation.loop`, which is absent
  rather than null when a root declares no time base, and it lets the tests
  assert byte-identity rather than shape-compatibility.

**Why a bump and not an additive key.** `instructions` and `animation.loop`
were additive because a consumer ignoring them still renders correctly. A
consumer ignoring `bindings` would evaluate `_b56` as an unresolved name —
`NaN` through the viewer's `Number(value)` — and render the machine in a wrong
pose. Silence is exactly what the version ladder exists to prevent.

Versions 2, 3 and 4 form the ladder the existing scheme already implies: a
consumer that reads 4 reads 3 and 2. A non-flexible document carrying bindings
declares 4 and thereby over-claims a flexible capability it does not use; that
is a property of a linear version ladder, not a new one, and it errs toward
refusal.

### D7. Compatibility: the producer does not negotiate

The framework **cannot** condition the document on an installed viewer.
`solid build` publishes `viewer.json` in an installation that has no viewer at
all — the viewer is an optional extra and the framework is complete without it
(ADR-068). So there is no viewer to ask.

The answer is the versioning contract that already exists. The viewer refuses
a document version outside its accepted set, in its prepare phase, before the
live tree is touched, and reports it. Today that set is `[1, 2, 3]`; the
paired viewer change widens it to `[1, 2, 3, 4]`.

**How much refuses, stated plainly.** It is not a grasshopper-sized model that
becomes version 4 — it is *almost every animated model*. The rule in D5 has no
size threshold, so one subexpression repeated on two nodes is enough, and a
`$t * loop` reaching two operations already does it. Nearly every animated
project in the workspace will publish version 4 on its next build. So between
this cycle integrating and the paired viewer change landing, `solid develop`,
the shop floor's live viewer and the standalone export page **refuse almost
every animated model** with the viewer installed today. The failure is loud and
legible rather than a wrong pose, which is the correct failure — but it is a
wide one, and it is not confined to the model that motivated the change.

**Integrating this cycle into main before the viewer half exists is therefore
an explicit pilot decision, not a consequence of merging.** The design does not
assume it; see the migration plan.

Unaffected throughout, as measured: `solid snapshot --renderer web` and the
shop floor's still previews, which go through it. Both bake constants, share
nothing, and stay at version 2/3 with any viewer.

What each framework path does:

| path | document | effect |
|------|----------|--------|
| `solid build` / `solid develop` | symbolic; bindings when shared | version 4; served to whatever viewer is installed, which accepts or refuses per its own set |
| `solid export` | symbolic; bindings when shared | version 4; the standalone export page is the same widget under the same rule |
| `solid snapshot --renderer web` | keyframed, numeric | constants only, nothing shared, **version 2/3 forever** — works with any viewer |
| shop-floor hub previews | go through `snapshot --renderer web` | unaffected |
| `solid snapshot` (OpenSCAD), `solid test`, `solid build`'s `.scad` | no document | unaffected |

**No opt-out flag.** A `--flat-expressions` escape hatch was considered and
rejected: it would keep two published forms in parity forever, and the flat
form is the defect being fixed.

**The `viewer` extra stays unbounded in this cycle** (D11): solid-node-viewer
0.1.0 is founded and unreleased, so there is no published version to bound the
extra against, and inventing one here would put a false claim in
`pyproject.toml`. The bound belongs to the change that publishes the first
viewer version reading document version 4.

### D8. The OpenSCAD path never sees a binding

Worth stating plainly, because the brief asked and the answer is not the one
the brief assumed: **`$t` is symbolic on the OpenSCAD path.**
`assembly.read_time` returns `get_animation_time() * base.loop` whenever
nothing bound `time`, the builder never keyframes, and `assemble()` applies
each operation through `operation.scad(...)` into `scad_rotate` /
`scad_translate`. `generate_scad()` therefore writes `.scad` text containing
literal `$t` expressions — the full flattened ones — and `Solid2Node.as_number`
resolves a symbolic value by shelling out to OpenSCAD with an `echo(...)`
program over that same text. Only `solid snapshot` and the test runner bind a
number.

None of that goes near this change. Bindings are produced by
`operation.serialized` and `flexible_document()`, and the SCAD path uses
neither: it reads `self.angle` and `port.value` directly. The generated SCAD is
byte-identical after this change, so artifact currency, STL content and piece
identity are all untouched — and the bindings table never has to be expressed
in OpenSCAD, which is what the pilot's ruling requires.

The consequence to keep in mind: the flat text still exists, on that path, by
contract. Any future change that stops materialising it must answer for
OpenSCAD first. That is why the follow-up in D1 keeps `value` intact.

### D9. Every other consumer

| consumer | reads the document? | change |
|----------|--------------------|--------|
| `core/export.py` | produces it | publishes `bindings` when non-empty |
| `core/builder.py` | produces it, and reads it back to compare | publishes `bindings`; the byte comparison needs the deterministic order D5 gives |
| `viewers/browser.py` | produces the staging document | none; numeric by construction, asserted by test |
| `core/pieces.py` | no | none; hashes STL bytes |
| `simulation/*.py` | no | none; in-memory nodes and plain numbers. It mints the same qualified ids the driver table is keyed by, which the naming rule D4 keeps clear of |
| `manager/export.py` | no | none |
| `test.py` (`solid test`) | no | none; in-memory `Rotation`/`Translation`, keyframed to numbers |
| `sphinx.py` | **yes** | none; validates `format` only, never `root`, `version` or `operations` |
| `node/operations.py::unserialize` | takes a serialized operation | **none, and worth recording**: it has no caller anywhere in the framework, tests or tools, and `float()`s its argument, so it could never read an expression. If it is ever revived it needs the table |
| `tools/generate_parity_fixture.py` | writes the fixture | see D10 |
| solid-node-viewer | yes | the paired change |

### D10. The parity fixture carries the table

The fixture is produced by the framework and consumed by the viewer's
`parity-fixture.test.ts` (ADR-068), and its expected values are producer
values obtained by serializing one tree twice — numerically bound and
symbolically — and pairing the two walks by structure. That method is
untouched.

Two things change:

- The fixture gains a top-level `bindings` array, and a case's `expression`
  may be or contain a binding name. A case is no longer self-contained; the
  viewer's test resolves the table exactly as the viewer resolves it in a
  document, which is the point — the fixture now pins the table's semantics
  as well as the function semantics.
- `uncovered_builtins()` regexes emitted names out of the cases. With a table,
  `sin(` can live in a binding and appear in no case. It must scan the table
  and the cases together, or a newly emitted builtin could reach a published
  document with no case behind it — the exact hole the `SYMBOLIC_BUILTINS`
  inventory exists to close.

The existing corpora (`spike/expressions/machine_model.py`,
`tests/expression_project/vocabulary.py`) share little, so the corpus is
extended — by adding a tree beside the existing ones, never by altering a
pinned case, as the kinematics spec requires — with one whose reuse actually
produces bindings: a value reused across several operations and several nodes,
so the fixture carries a chain of entries referring to earlier entries, a
binding referenced from more than one node, and a binding over a driver id as
well as over `$t`.

## What was measured

On the published grasshopper document, with a prototype implementing exactly
D2–D5 (parser, structural interner, substring memo, occurrence counting,
`_b<N>` names, ordered table):

```
load                 0.09 s   116 expression strings, 30 distinct, 31.61 MB
parse + intern       3.95 s   263 distinct nodes; 163 memo misses, 90 hits;
                              78.5 MB of characters scanned
shared (occurrences > 1)      81 nodes, of which 57 are not a bare number or name
render               0.00 s
bindings                      57 entries, 2.3 kB
operation expressions         0.8 kB (was 31.61 MB)
TOTAL expression text         3.1 kB      shrink 10,287x
longest binding expression    197 characters (was 3,322,703)
peak RSS                      ~0.10 GB, document included
```

Parity, run two ways, both exact:

1. **Table against flat.** Each published binding was substituted back into
   the rewritten operation expressions, reconstructing a flat string, and
   evaluated against a memoized walk of the DAG at
   `$t ∈ {0, 0.1, 0.25, 1/3, 0.5, 0.77, 0.999}` — 116 expressions × 7 values.
   **0 mismatches** at 1e-9 relative tolerance.
2. **DAG against the shipped document.** The same walk was compared against
   evaluating the *original* 31.6 MB strings out of the published
   `viewer.json`, at three values of `$t`. **0 mismatches.**

Both evaluations use OpenSCAD degree semantics — the ADR-022 contract — with
`^` as exponentiation and `%` as `fmod` (sign of the dividend), so the check
is against the semantics the document promises rather than Python's.

Sample of the published table, verbatim from the prototype:

```
_b0  = ($t * 43200.0)
_b1  = ((2 * _b0) / 1.5)
_b2  = floor((_b1 - 1.0))
_b3  = (_b2 - (2 * floor((_b2 / 2))))
...
_b55 = (_b49 + ((((-360) * _b0) / 3600) - _b49))
_b56 = (28.347830517908797 + (0.3333333333333333 * (191.12247881066565 - _b55)))
```

and the escape wheel's rotation, which was 1,661,408 characters, becomes
`["r", "_b56", [0, 0, 1]]`.

## Risks / Trade-offs

- **A parser for a language nobody wrote down.** The grammar is inferred from
  two producers (`OpenSCADConstant`'s overloads and `_symbolic_call`), and a
  project can bypass both with `scad_inline`. *Mitigation:* an expression the
  parser cannot read is published verbatim and unshared with a warning, never
  guessed at and never fatal, so the worst case is a document exactly as large
  as the one published today. The `SYMBOLIC_BUILTINS` inventory and the
  corpus-coverage test already guard the call names; a red test pins each
  operator form the overloads can emit, comparisons included, and another pins
  the pass-through.
- **A wrong parse would be a silently wrong machine.** *Mitigation:* the
  parity check is numeric, against the flattened string the producer emitted,
  and it is a test in this repository as well as a fixture case in the
  viewer's.
- **3.95 s added to a build.** Measured against builds that take minutes, and
  paid only by a document that has sharing to find. *Mitigation:* recorded as
  a number in the changelog, and D1's follow-up removes it if it ever matters.
- **Exponential text still built by the producer.** Route (b) publishes 263
  nodes but reads 78 MB to find them, and a machine deeper than the
  grasshopper will make both grow. *Mitigation:* named explicitly as the
  follow-up in D1, with its own trigger — a measured build-time regression —
  so it is a decision waiting on evidence rather than a gap.
- **An old viewer refuses a new document.** By design (D7), and loudly.
  *Mitigation:* the paired viewer change, and an honest `viewer` extra floor
  once there is a released version to name.
- **A driver named `_b0`.** Handled by minting rather than refusing (D4), and
  pinned by a test that declares exactly that driver.

## Migration Plan

None for a project: no project code changes, and the next build republishes.
No stored state, no artifact format, no on-disk migration. A document already
published stays readable — it is version 2 or 3 and nothing stops reading it.

The one ordering constraint is between repositories, and it is a real gate
rather than a preference. The viewer's `share-expression-subtrees` integrates
first (it is already in flight and needs no format change), then the viewer's
binding-table change, which is what makes a version-4 document renderable.

Until that second viewer change lands, integrating this cycle into the
framework's main makes nearly every animated model in the workspace refuse to
open in `solid develop`, the shop floor's live viewer and the standalone export
page — see D7. That is a **pilot decision to take deliberately**, with two
coherent orders available: hold this cycle on its branch until the viewer half
is ready, or integrate now and accept a window in which animated models are
built but not viewable (still snapshotted, since the web-snapshot path is
unaffected). Nothing in this change picks one.

## Decisions taken on the open questions

Three questions were left open in the first draft and have been decided.

### D11. The `viewer` extra stays unbounded in this cycle

`pyproject.toml` declares `viewer = ["solid-node-viewer"]` with no bound. The
honest bound is the first viewer version that accepts document version 4 —
and there is nothing published to pin against: solid-node-viewer 0.1.0 is
founded, unpushed and unreleased. Writing a bound now would put a claim in
`pyproject.toml` about a version that does not exist.

**Decided:** leave the extra unbounded here, and add the bound in the change
that publishes the first viewer version reading version 4. Recorded in
`tasks.md` as a follow-up to report, not as work in this cycle. Until then the
version ladder is the whole compatibility story, which is what D7 describes.

### D12. The version stays a linear ladder

A non-flexible document carrying bindings declares 4 and thereby appears to
claim the flexible-node shape it does not use. The alternative is a capability
list beside the version.

**Decided:** keep the ladder. Consumers accept by **membership in a set** — the
viewer's accepted set is `[1, 2, 3]` today and becomes `[1, 2, 3, 4]` — not by
comparing capabilities, so a version-4 document without flexible leaves costs a
conforming consumer nothing: it is in the set, and the flexible branch it never
takes is never exercised. Replacing the version with a capability list is a
separate format decision, with its own consumers to update and its own
migration, and it should not be smuggled in behind an optimisation. Nothing in
this change forecloses it.

### D13. The fixture's sharing corpus is a synthetic tree

**Decided:** a synthetic corpus tree beside the existing two, not the
grasshopper clock. The fixture is committed in the viewer's repository and read
by its parity test; a 31.6 MB corpus there would defeat the purpose of the
change that shrinks it, and would make the viewer's test suite carry a clock. A
small tree that deliberately reuses a value across several operations and
several nodes, over a driver as well as over `$t`, pins everything the table's
semantics need: an entry naming an earlier entry, an entry referenced from more
than one case, and a binding over a driver id. The kinematics spec's rule holds
either way — a new tree beside the existing ones, never an altered pinned case.
