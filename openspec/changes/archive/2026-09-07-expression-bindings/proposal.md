## Why

A published document is 31.6 MB of the same arithmetic written out again and
again, and the machine it describes will not animate.

3DPrintedClocks' `wall_clock_53_grasshopper` — a grasshopper escapement whose
kinematics are written in `solid_node.math` over `$t`
(`design/wall_clock_53_grasshopper/kinematics.py`) — publishes
`_build/wall_clock_53_grasshopper/viewer.json` at 31,638,555 bytes, of which
**31,611,478 are operation expression text**. The document describes 46 nodes,
76 operations and 40 STL models; the models are separate files. Essentially
the whole document is one arithmetic expression, repeated.

The cause is in the producer. Symbolic values travel as solid2
`OpenSCADConstant`s, which are string-eager: `__operator_base__` returns
`OpenSCADConstant(f'({self} {op} {other})')`, so **every reuse of a value
pastes its full text again**. The escapement nests those reuses, and the text
doubles per level. Measured on the published document:

| operation                                 | text    | parse nodes | distinct subexpressions |
|-------------------------------------------|---------|-------------|-------------------------|
| escape wheel (and 5 train arbors, 5 rods) | 1.66 MB | 328,336     | 193                     |
| cannon pinion, hands, arbor, hour holder  | 3.32 MB | 656,718     | 224                     |
| entry arm / exit arm                      | 23 KB   | 4,536       | 75                      |
| whole document                            | 31.6 MB | ~7 million  | **263**                 |

Two hundred and sixty-three distinct subexpressions, published as seven
million. The escape wheel's angle alone is copied whole into fourteen
operations.

What that costs the consumer was measured in the viewer repository: 7.65 s of
one-time parsing, 723 MB of parse trees retained for the life of the page,
and about two frames per second — the pilot sees the whole machine stutter.
The shop's `docs/warts.md` item 12 recorded the finding and deferred the fix:

> **Expression math has no common-subexpression pass.** … Revisit when a
> published document outgrows the viewer.

This is that document.

A viewer-side change is in flight in parallel
(`solid-node-viewer/openspec/changes/share-expression-subtrees`): hash-consing
inside the evaluator, no format change, so every document already published
gets its frame rate back. It leaves 31 MB on the wire and 7.65 s of parsing,
because the redundancy is in the document. **This change fixes the document.**

The empirical chain: 3DPrintedClocks needed a grasshopper escapement →
building it out of reused symbolic values produced a 31.6 MB document that
will not animate → the framework must publish a shared subexpression once
rather than once per use.

## What Changes

- The published document — the export `manifest.json` and the normal-build
  `viewer.json` alike — gains an ordered top-level **`bindings`** table:
  named intermediate expressions, each referring only to `$t`, to qualified
  driver ids, and to bindings **earlier in the table**. Operation expressions
  and flexible `params` reference those names instead of repeating their text.
- Every subexpression that occurs more than once in a document's expressions
  is published once, named, and referenced — except a bare number or a bare
  name, which is shorter written out than referenced. There is no size
  threshold to tune.
- Binding names are `_b0`, `_b1`, … in table order. The prefix is lengthened
  by a leading underscore, deterministically, if any qualified driver id in
  the same document would collide with a name the table is about to mint, so
  a legal model is never refused for its choice of driver name. No name the
  viewer's math context defines can collide: none begins with an underscore.
- A document carrying a non-empty `bindings` table declares **`version: 4`**.
  A document with nothing shared omits the key entirely and declares the
  version its content already needed (2, or 3 for flexible content) — so
  every document without repeated subexpressions is byte-identical to the one
  the framework publishes today. `document_version()` keeps reading the answer
  off the finished content rather than the producer declaring it.
- The bump is a real one, not an additive key: a consumer that ignored
  `bindings` would evaluate an unresolvable name and render a wrong pose, so
  it must refuse instead. Version 4 is what makes it refuse loudly.
- Sharing is detected **at serialization**, by parsing each expression string
  the producer already built and interning it structurally across the whole
  document. Nothing about `solid_node.math`, solid2 arithmetic, the driver
  token, the ports layer or any project's code changes. See `design.md`
  decision D1 for the route not taken.
- **An expression the framework cannot read is published verbatim and
  unshared**, with a warning naming the offending text and identifying the
  expression (truncated — a published expression may be megabytes). It never
  fails the build. Every one of these expressions publishes and renders today;
  sharing is an improvement to a working document, so a model that produced a
  working document yesterday must produce one tomorrow, and an unreadable
  expression costs only its own share of the improvement. The producer refuses
  only a table that would be *wrong* — an entry naming a later entry, a name
  colliding with a declared driver id, a rewrite that does not reproduce what
  the producer built — which is a framework defect, not a project's fault.
- The document states the **consumer's** rules too, so the paired viewer change
  can be written from this spec: a binding name resolves before it is judged an
  undeclared driver id, and an expression naming a binding depends on every
  input that binding transitively depends on, so an operation whose expression
  is a binding name over `$t` is still a time-dependent operation.
- The `.scad` path is untouched. Operations reach OpenSCAD as
  `operation.scad(...)`, never through `operation.serialized`, so the
  generated SCAD text keeps the flattened expression it has today and
  `Solid2Node.as_number`'s `echo(...)` round-trip still resolves.
- `solid snapshot --renderer web` stages a keyframed, numerically baked
  document; its expressions are constants, nothing is shared, and its
  documents stay at version 2/3 whatever viewer is installed.
- The cross-runtime parity fixture gains the table: `tools/generate_parity_fixture.py`
  publishes `bindings` beside `cases`, a case's `expression` may reference a
  name, and the coverage check that reads `SYMBOLIC_BUILTINS` scans the table
  as well as the cases so an emitted builtin cannot hide inside a binding.

Measured on the grasshopper document with a prototype of exactly this design
(`design.md`, "What was measured"):

| | before | after |
|---|---|---|
| expression text in the document | 31,611,478 B | 3,072 B (**10,287×**) |
| the document itself | 31.6 MB | ~30 kB |
| distinct published subexpressions | ~7,000,000 written | 263 interned, 57 named |
| longest published expression | 3.32 MB | 197 characters |
| producer cost added | — | 3.95 s, ~100 MB peak |
| numeric parity, 7 values of `$t`, 116 expressions | — | exact, 0 failures |

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `export`: the "Manifest contract" requirement gains the `bindings` table —
  its shape, its ordering guarantee, the naming and collision rule, what a
  reference means, and the version rule — and states that a document with
  nothing shared is unchanged.
- `build-viewer-artifacts`: the "Complete builds publish a viewer snapshot"
  requirement carries the same table under the same rules, as it already
  mirrors the manifest's tree contract, and adds that the table is
  deterministically ordered so the builder's byte comparison still decides
  republication correctly.
- `kinematics`: "The parity corpus covers every symbolic function" is
  modified so the corpus carries the bindings table and the coverage check
  reads emitted builtin names across the table and the cases together.
- `flexible-parts`: the sentence in "Snapshot artifacts on the SCAD path"
  promising that a published `params` expression is carried "verbatim" is
  modified to say what it has always meant — the symbolic expression rather
  than the constant an instant computed — and that a shared subexpression
  within it may be published as a reference into the document's table.

Capabilities needing no delta, and why:

- `web-snapshot`: the staged document is keyframed and numeric. Its
  expressions are constants, so it never carries a table and never declares
  version 4. A test pins that rather than a requirement.
- `viewer-distribution`: the framework locates the viewer through the entry
  point and reports its `apiVersion`; it compares nothing, and this change
  adds no comparison. The `viewer` extra stays unbounded in this cycle
  (`design.md` D11): solid-node-viewer 0.1.0 is founded and unreleased, so
  there is no published version to bound it against, and the bound belongs to
  the change that publishes the first viewer reading version 4.
- `simulation`, `ports`: neither reads a serialized expression. Both work on
  in-memory nodes and plain numbers.
- `sphinx-embedding`: the embedder validates `format` and never inspects
  `root`, `version` or `operations`.
- `printed-pieces`: piece identity is a fingerprint of STL content and never
  touches an expression.

## Impact

- `solid_node/core/expressions.py` — **new**: the parser for the expression
  language the framework emits, the structural interner, the shared-node
  detection, the renderer, and the name minting. Stdlib only.
- `solid_node/core/serializer.py` — the walk collects each node's operation
  and flexible-`params` expression strings, builds the table once for the
  whole document, and rewrites the strings; `document_version()` answers 4
  for a document carrying a non-empty table.
- `solid_node/core/export.py`, `solid_node/core/builder.py` — publish the
  `bindings` key when the table is non-empty, and omit it otherwise.
- `solid_node/viewers/browser.py` — publishes no table; its document is
  numeric by construction. Asserted, not built.
- `tools/generate_parity_fixture.py` — publishes `bindings`, and
  `uncovered_builtins` reads the table and the cases together.
- `solid_node/node/operations.py`, `math.py`, `node/qualified.py`,
  `node/timebase.py`, `node/ports.py`, `node/flexible.py` — unchanged. The
  producer builds expressions exactly as it does today.
- `docs/architecture.md`, `docs/changelog.rst`, `docs/adrs/EXPORT/ADR-080`.
- **The paired viewer change is a separate change in
  `solid-node-viewer`**, and must follow `share-expression-subtrees`: the
  viewer widens its accepted document versions to `[1, 2, 3, 4]`, evaluates
  the table top to bottom into the scope it already builds for `$t` and
  drivers, bounds re-evaluation by the inputs each entry depends on (derived
  from the table's order, not carried in the document), resolves a binding name
  before judging it an undeclared driver id, and commits the regenerated parity
  fixture. Nothing of it is done in this cycle; this cycle specifies the
  contract it is written against.
- **How much refuses until that viewer change lands.** The sharing rule has no
  size threshold, so one subexpression repeated on two nodes is enough to make a
  document version 4 — and `$t * loop` reaching two operations already does it.
  Nearly **every animated project in the workspace** will publish version 4 on
  its next build. So between this cycle integrating and the viewer's half
  landing, `solid develop`, the shop floor's live viewer and the standalone
  export page refuse almost every animated model with the viewer installed
  today. The refusal is loud and legible rather than a wrong pose, which is the
  correct failure — but it is wide, and it is not confined to the clock that
  motivated the change. **Integrating this cycle into main before the viewer
  half exists is therefore an explicit pilot decision**, not a consequence of
  merging; `design.md`'s migration plan lays out the two coherent orders.
  `solid snapshot --renderer web` and the shop floor's still previews are
  unaffected either way: both bake constants and stay at version 2/3.
- The originating project, 3DPrintedClocks, changes nothing. Its document
  shrinks on the next build. Recording the measured before/after for
  `wall_clock_53_grasshopper` is the caller check that closes this cycle.
