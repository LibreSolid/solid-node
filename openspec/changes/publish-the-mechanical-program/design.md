# Design — publish the mechanical program

## Context

### What already exists

- **The compiled program** (`solid_node/simulation/program.py`). At `Sim`
  construction under a running root, `compile_program(root, inputs,
  coordinates)` applies each relation's law ONCE to a symbolic token per
  source and keeps the `ExpressionNode` graph it builds, over the sources'
  QUALIFIED IDS. A graph carrying a jump primitive gets a `JumpPlan`
  beside it: the jump nodes in the graph's postorder, each with its level
  quantity and whether that level is affine in the sources, and the
  SKELETON of the whole law with every jump node replaced by a branch
  placeholder (`$j0`, `$q0`). `Program` holds `inputs`, `coordinates`,
  `nodes`, ordered `edges`, `spans`, `sources` and an `identity` digest of
  `described()`.
- **The document** (`solid_node/core/serializer.py`,
  `core/export.py`, `core/builder.py`). Three producers share one walk.
  `symbolic_document` binds every declared DRIVER to a `DriverToken` of
  its qualified id through an internal path — never `set_state`, whose
  numbers-only contract is what keeps a bound pose a function of numbers
  — renders once, and yields the declarations and the instructions.
  `serialize_node` writes the tree; `bind_document` publishes every
  subexpression that repeats once, as an ordered `bindings` table
  (ADR-080), and rewrites each occurrence to its name. `document_version`
  reads the version off the finished content: 4 with a non-empty
  `bindings`, else 3 with a flexible leaf, else 2.
- **The consumer** (`solid-node-viewer`, read-only here).
  `RENDERED_VERSIONS = [1, 2, 3, 4]`; `assertRenderable` refuses anything
  else by name, then validates the bindings table, then refuses any
  expression naming an id that is neither `$t`, a binding, nor a declared
  driver. `expressions.ts` is a hash-consed DAG over the same scalar
  grammar; `evaluator.ts` evaluates it from a nested driver scope;
  `drivers.ts` holds native values and runs client-side ramps.
  `bundle.describe()` reports `path`, `index`, `apiVersion` (7 today) and
  `version`.
- **The acceptance project**, read-only: the Pascaline module, three
  dials, nine joint coordinates, three multi-source carry laws with
  `floor`, six intermediates (`<column>.wheel`, `<column>.stop.angle`),
  three `by=` instructions, no spans yet. Its committed `_build/viewer.json`
  is version 4, 30,529 bytes, 147 bindings — and it publishes the carry
  law ABSOLUTELY, which is the defect this cycle removes.

### The authority

`workflow/open-run-simulation/design.md`, "Decision 2026-09-13", item 10
(export and viewer) and item 8 (instructions); "Python-to-browser
architecture" (one compiled program consumed by Python and by a browser
worker; a new capability/version boundary an old viewer must refuse;
geometry and program published atomically; a shared conformance corpus);
"Runtime and program interfaces". The cycle split is `roadmap.md`,
"Execution, 2026-09-13".

## 1. The version 5 document, field by field

A version 5 document is a version 4 document plus one top-level key,
`program`, and one changed rule for the `instructions` table. Everything
else — `format`, `animation`, `drivers`, `bindings`, `root`, `pieces` —
is what it is today, produced by the same code, in the same order.

```
{
  "format":  "solid-node-export",
  "version": 5,
  "animation": {"fps": 30, "frames": 360},      // no "loop": running has none
  "drivers":  { ...unchanged... },
  "instructions": {
      "Add one": {"by": {"units_entry": 1.0}, "duration": 1.0},
      "Park":    {"targets": {"crank": 40.0}, "duration": 0.5}
  },
  "bindings": [ {"name": "_b0", "expression": "..."} , ... ],
  "program": { ...below... },
  "root":   { ...unchanged... },
  "pieces": [ ...unchanged... ]
}
```

`program` is:

```
{
  "identity": "62bb22d2…",              // Program.identity, hex sha256

  "clock": "time",                      // the free name elapsed seconds bind to

  "coordinates": {                      // THE BANK, in Program order
    "units_entry":     {"kind": "input",      "initial": 0.0},
    "units.drum.turn": {"kind": "coordinate", "initial": 0.0, "unit": "deg"},
    …
  },

  "intermediates": ["units.wheel", "units.stop.angle", …],

  "edges": [ …one object per edge, in program order… ],

  "spans": {
    "input.turn": {"low": {"expression": "_b31"}, "high": null}
  },

  "sources": {                          // Program.sources, candidate table
    "units.drum.turn": ["units_entry"],
    "tens.drum.turn":  ["tens_entry", "units_entry"],
    …
  },

  "limits": {
    "crossing_tolerance": 1e-12,
    "subdivisions":       64,
    "bisection_rounds":   64,
    "max_crossings":      1000,
    "agreement":          1e-9
  }
}
```

### 1.1 `coordinates`

One entry per BANK id, in `Program.coordinates`/`inputs` order (inputs
first, then joint coordinates, each sorted — the order `compile_program`
already fixes). `kind` is `"input"` for a declared driver and
`"coordinate"` for a joint coordinate. `initial` is the value the REST
POSE gave it, which is `dict(sim.initial.bank)[id]` — the one number a worker
cannot compute, because computing it means running the CAD tree's rest
render. A coordinate entry carries `unit`, the joint's declared unit, or
`null`.

An input entry carries NO `unit`, `dtype`, `scale`, `range` or `default`:
the document's own `drivers` table already publishes every one of them,
keyed by the same qualified id, and `Program.inputs` is exactly the same
set of declarations. *Alternative that lost:* repeating the declaration
inside `program.coordinates`, as the cycle brief sketched. Rejected —
two tables carrying one declaration is two tables that can disagree, and
a consumer holding both cannot tell which is authoritative. The
publication asserts the identity instead: a task proves every
`kind == "input"` id is a key of `drivers` and vice versa.

### 1.2 `intermediates`

Every `Program.nodes` entry whose kind is `intermediate`: a plain port or
a derived coordinate a compiled edge determines, which the run recomputes
from the bank on every tick and never stores. Published as its own list
rather than inferred from "a name in an edge that is not in
`coordinates`", so a name the producer failed to qualify cannot silently
become an intermediate.

A `Program` node whose qualified id could not be computed — the
`f'{ClassName}.{name}'` fallback `_qualified` takes when `driver_id`
raises — is REFUSED at publication, naming the node and why: a fallback
name is not unique across two instances of one class, and publishing it
would put two different coordinates under one name in one expression
scope. Nothing in the framework's suite or in any surveyed project
reaches it today; the refusal is what keeps it that way.

### 1.3 `edges`

One object per `Program.edges` entry, IN PROGRAM ORDER — the order Kahn
gave at compile time, which is the order the tick propagates in. Common
fields:

```
{"kind": "law" | "wiring" | "formula" | "check",
 "needs": ["units.drum.turn", …],     // bank ids and intermediates
 "gives": ["units.input.turn", …],    // empty for a check
 "description": "drum.turn drives input.turn",
 "stated_by": "DecimalModule"}
```

`needs` and `gives` are the qualified ids `Program.nodes[key].name`
carries, and they are exactly the free names each expression reads:
`Edge.names[i] == nodes[needs[i]].name` by construction, so no separate
name list is published.

`description` and `stated_by` travel because every refusal the run makes
— a conflict, a partition over a thousand cuts, a `%` whose divisor
reaches zero — names the relation AS WRITTEN and the class that stated
it. A worker that cannot say which relation disagreed is a worker whose
message is useless.

**`kind: "law"`** adds, one entry per driven end, aligned with `gives`:

```
 "expressions": ["(_b0 + (…))", null],     // null for a CONSTANT law
 "affine":      [false],                   // Edge.affine
 "plans":       [ {…} | null ]             // a JumpPlan, or null
```

A plan is:

```
{"skeleton": "(_b0 + ((((((((65.54 * _j0) + (4.1 * min(max(…",
 "jumps": [{"name": "_j0", "primitive": "floor",
            "level": "_b2", "affine": true}]}
```

in the graph's postorder — the order the plan's partition reads them in.
`primitive` is one of `floor`, `ceil`, `sign`, `%`, `<`, `<=`, `>`, `>=`,
`==`, `!=`. `name` is the branch placeholder as the SKELETON reads it;
`level` is the level quantity's expression, with every jump inside it
already replaced by its own placeholder. A `%` node is NOT a placeholder
in the skeleton: `_skeleton` already rewrites it to `a - q * b`, so the
placeholder is the quotient and the skeleton is written out.

**Placeholders are minted at publication, document-wide.** The compiler
names them `$j0`, `$q0` PER PLAN, which is fine inside one plan and fatal
in a document: `$j0` is not a name in the published grammar
(`_NAME_RE` admits `$t` and nothing else beginning with `$`), and three
plans all calling their first jump `$j0` would let the bindings pass
share one subtree between three different jump nodes. A probe of the
Pascaline module with per-plan names produced exactly that — one binding
`_b6 = (65.54 * _j0)` referenced from all three carry skeletons, three
different `floor`s under one name. So publication renames every jump node
of every plan to `_j0`, `_j1`, … in edge order then postorder, under a
prefix lengthened by a leading underscore for as long as any published id
matches `<prefix>\d+`, exactly as `_mint_prefix` lengthens `_b`.

**`kind: "wiring"`** adds `"factor": 1.0` — the target's scale, or 1.0.
Its value is `source * factor` and its increment `delta_source * factor`.

**`kind: "formula"` and `kind: "check"`** add
`"factors": [...]` aligned with `needs`, `"constant": 0.0`, and
`"slot": "<id>"` — the derived coordinate's own slot. These are
`Edge.factors`, `Edge.constant` and `nodes[slot_key].name`, and the two
evaluation rules are stated in full in the spec delta, because a worker
must reproduce `_linear` and `predicts` exactly:

- forward (`slot` is in `gives`): `constant + Σ needs[i] * factors[i]`;
- backward (`gives` is one term): `needs` carries the slot FIRST (with
  factor `0.0`), then the other terms, then the solved-for term itself
  with its own coefficient LAST, and the value is
  `(held[slot] - constant - Σ other * factor) / own`;
- an increment is the same arithmetic with `constant` replaced by zero;
- a `check` predicts `constant + Σ needs[i] * factors[i]` over every need
  but the slot, and the tick REFUSES when that disagrees with what the
  slot received beyond `limits.agreement` relatively.

*Alternative that lost:* publishing a formula and a wiring as ordinary
law expressions, so the worker has one evaluation rule for every edge.
Tempting — an affine expression's `f(end) − f(start)` equals the linear
increment, so it is behaviour-identical — and rejected for two reasons.
A `check` edge needs the coefficient form anyway, to predict; and the two
runtimes would then run DIFFERENT arithmetic for one edge, which the
corpus can only pin to a float tolerance instead of to the same
associativity. Publishing the coefficients keeps the arithmetic itself
the contract.

### 1.4 `spans`

One entry per `Program.spans` coordinate — a banked coordinate whose
joint declares a range. Each bound is `null` (unbounded), a number, or
`{"expression": "<text>"}` — an expression over that coordinate's OWN id
and nothing else, which cycle 3's compile already guarantees. A jump in a
bound is legal and means what it says: a bound is EVALUATED once per
tick, never integrated, so `floor` is the tooth pitch.

The unit is on the coordinate entry, not repeated here.

### 1.5 `sources`

`Program.sources` verbatim: for every bank id and intermediate, the
sorted list of INPUT ids that reach it through the program. The candidate
table a stop's group is filtered out of. See §5 for why this one is
published although a worker could compute it.

### 1.6 `limits`

The five constants the algorithm is defined by, as data:
`_CROSSING_TOLERANCE`, `_SUBDIVISIONS`, `_BISECTION_ROUNDS`,
`_MAX_CROSSINGS` from `program.py`, and `_TOLERANCE` from `run.py` under
the name `agreement`.

The brief named four. The fifth is `run.py`'s `_TOLERANCE = 1e-9`, the
relative window inside which two increments on one coordinate are called
equal. It belongs here for exactly the reason the other four do: a worker
with a different agreement window refuses a tick Python commits, or
commits one Python refuses, on a machine whose two routes to a coordinate
differ in the last bits — which is every multi-source machine, including
the Pascaline's own carry. Leaving it out would be the one divergence the
corpus is least likely to catch, because it shows on the case nobody
wrote.

*Alternative that lost:* the worker hard-codes the constants and the
corpus catches a divergence. Rejected: a corpus catches a divergence only
on a case that exercises it, and a tolerance divergence is by definition
the kind that hides. Publishing them also means a framework change to a
constant reaches every worker without a viewer release.

## 2. A worked excerpt: the Pascaline module's own document

Built from this worktree
(`projects/Calculators/Pascaline-module/WTs/open-run-simulation`), the
module's program is 3 inputs, 9 joint coordinates, 6 intermediates, 9
edges, no spans. Its version 5 `program` reads (elided, and with the
bindings the whole document shares):

```
"identity": "62bb22d2e3742320248ab18069ef0d7cfeece0a317527d1efb728a2f33e68b4b",
"clock": "time",
"coordinates": {
  "hundreds_entry": {"kind": "input", "initial": 0.0},
  "tens_entry":     {"kind": "input", "initial": 0.0},
  "units_entry":    {"kind": "input", "initial": 0.0},
  "hundreds.carry.turn": {"kind": "coordinate", "initial": -0.0, "unit": "deg"},
  "hundreds.drum.turn":  {"kind": "coordinate", "initial":  0.0, "unit": "deg"},
  "hundreds.input.turn": {"kind": "coordinate", "initial": -0.0, "unit": "deg"},
  "tens.carry.turn":     {"kind": "coordinate", "initial": -0.0, "unit": "deg"},
  "tens.drum.turn":      {"kind": "coordinate", "initial":  0.0, "unit": "deg"},
  "tens.input.turn":     {"kind": "coordinate", "initial": -0.0, "unit": "deg"},
  "units.carry.turn":    {"kind": "coordinate", "initial": -0.0, "unit": "deg"},
  "units.drum.turn":     {"kind": "coordinate", "initial":  0.0, "unit": "deg"},
  "units.input.turn":    {"kind": "coordinate", "initial": -0.0, "unit": "deg"}
},
"intermediates": ["hundreds.stop.angle", "hundreds.wheel",
                  "tens.stop.angle", "tens.wheel",
                  "units.stop.angle", "units.wheel"],
"spans": {},
"sources": {
  "units.drum.turn":  ["units_entry"],
  "tens.drum.turn":   ["tens_entry", "units_entry"],
  "hundreds.drum.turn": ["hundreds_entry", "tens_entry", "units_entry"],
  …
},
"edges": [
  {"kind": "law", "needs": ["units_entry"], "gives": ["units.drum.turn"],
   "description": "units_entry drives units.drum.turn",
   "stated_by": "Pascaline",
   "expressions": ["(36.0 * units_entry)"],
   "affine": [true], "plans": [null]},

  {"kind": "law",
   "needs": ["tens_entry", "units.drum.turn"], "gives": ["tens.drum.turn"],
   "description": "(tens_entry, units.drum.turn) drives tens.drum.turn",
   "stated_by": "Pascaline",
   "expressions": ["(_b0 + ((((((((65.54 * _b3) + (4.1 * min(max((((_b5 - 115.0) + 0.1) / 3.0), 0.0), 1.0))) + …"],
   "affine": [false],
   "plans": [{"skeleton": "(_b0 + ((((((((65.54 * _j0) + (4.1 * min(max((((_b7 - 115.0) + 0.1) / 3.0), 0.0), 1.0))) + …",
              "jumps": [{"name": "_j0", "primitive": "floor",
                         "level": "_b2", "affine": true}]}]},

  {"kind": "law", "needs": ["units.drum.turn"], "gives": ["units.input.turn"],
   "description": "drum.turn drives input.turn", "stated_by": "DecimalModule",
   "expressions": ["(-1 * units.drum.turn)"], "affine": [true], "plans": [null]},
  …
]
```

and the bindings those expressions resolve through, which the whole
document shares:

```
_b0 = (36.0 * tens_entry)
_b1 = (units.drum.turn - 114.9)
_b2 = (_b1 / 360.0)
_b3 = floor(_b2)
_b4 = (360.0 * _b3)
_b5 = (units.drum.turn - _b4)
_b6 = (360.0 * _j0)
_b7 = (units.drum.turn - _b6)
…
_b16 = (-1 * tens.drum.turn)
```

Two things are worth reading off it. `_b2` is both the law's own `floor`
argument and the plan's LEVEL QUANTITY, published once — the sharing
ADR-080 introduced surviving into the plan. And `units.carry.turn` and
`tens.input.turn` are both `_b16`: two coordinates driven by one
expression, published once.

Against that, the module's version 4 document today publishes the whole
carry law as part of the tens drum's POSE, over the DIAL drivers — its
rotation is `_b58 = (_b2 + _b57)`, and `_b6 = (65.54 * floor((((36.0 *
units_entry) - 114.9) / 360.0)))` is one of the fifty-seven bindings
under it (`evidence.md` §1). Under version 5 that pose becomes the single
name `tens.drum.turn`, and the law moves into `program`, where it is
integrated. That is the whole change, in one line of one document.

## 3. How a committed bank poses the geometry

**The rule.** Under a running root, `symbolic_document` binds every JOINT
COORDINATE of the linked tree to `symbol(<qualified id>)` beside every
driver's `DriverToken`, before the single render. The bindings the
document already publishes then read the coordinate ids as free names:

- a joint's own placement operation becomes that coordinate's id, or an
  expression over the six ids of a `Free`;
- a plain port, a derived coordinate and a flexible leaf's `params`
  become expressions over whatever bank ids drive them — the module's
  `stop.angle` is `(-1 * units.drum.turn)`, and its molejo `bend`
  parameter is the spline formula over that;
- a driver that poses geometry DIRECTLY, without passing through a joint,
  still publishes its driver id, which is why drivers keep their tokens.

A worker therefore evaluates, per frame, exactly the expressions the
viewer evaluates today, from a scope holding the bank it just committed
instead of a scope holding driver values alone. Nothing about how a pose
is expressed changes, and nothing new has to be evaluated: the flexible
parts follow by the same rule, because a `params` expression is an
expression like any other.

**Why this is the minimal change.** The coordinate binding goes where the
driver binding already goes. `drive_tree`'s `visit(node, path)` hook runs
"after its drivers are bound and before anything in the tree renders" —
which is precisely the window a coordinate binding needs — and
`symbolic_document` already passes a `visit` to collect instructions. So
the coordinate binding is added to that same callback: one walk, one
render, one restore. The binding itself is `set_coordinate` under
`binding_as(RunBinder())`, the path `CoordinateDelivery` already uses,
with the root's `_run_binder` installed for the duration so the solver
treats those slots as a run's and leaves them alone — which is exactly
what makes the relations record as solved rather than refuse as doubly
bound.

Three existing behaviours make this safe, each verified against the code:
`Joint._refuse_out_of_range` returns without judging a non-numeric
binding, so a symbolic coordinate never trips a declared range;
`bind()` refuses a run-owned slot only when the binder differs, and the
publication's binder is the one that bound them; and `set_state`'s
numbers-only contract is untouched, because this is the internal door,
not that one.

**What restores.** Each slot's `(_value, binder, _enum_marker,
_bound_by)` is saved and put back, the joint re-placed from what its
coordinates then hold, and the root's `_run_binder` restored — the same
obligation `symbolic_document` already discharges for drivers.

**A tree a live run owns.** Publication may run while a `Sim` owns the
tree — a scenario that builds or exports in-process, the development
server after a run. The publication's binding is not an author binding,
so `bind()` SHALL admit the publication binder over a slot another
`RunBinder` owns, the saved binder being that run's; after the restore
the run owns its slots again with its committed values, its bank is
untouched, and it advances as if nothing had happened. Refusing here
would be the doubly-bound refusal misfiring on the one binder that is
not an author, and the takeover of §8.1 is not the tool either: a
publication is a read that must leave no trace. Task 3.x pins it with a
run that publishes mid-move and continues.

*Alternative that lost:* publish the pose expressions over DRIVER ids as
today and let the worker map drivers to coordinates. Rejected outright:
that is the absolute reading, and it is the defect. *Second alternative:*
publish a separate `bindings`-like table of "coordinate → pose
expression" beside the tree, leaving the tree's operations over drivers.
Rejected: it would publish every pose twice, and a consumer would have to
decide which one to believe.

## 4. `time` under a running root

Cycle 1 left an unbound `time` under a running root reading bare `$t`,
called it a preview, and deferred the question here.

**The decision.** The preview stays for Python — `read_time` is not
touched, so a bare render, the `.scad` path and `solid snapshot
--renderer openscad` behave in every byte as they do today. What changes
is the DOCUMENT: under a running root, `symbolic_document` BINDS `time`,
to `symbol('time')`, exactly as it binds a driver. So a version 5
document never carries `$t` from this source; where a running root's
`simulate()` or `render()` reads the clock, the document carries the free
name `time`, published as `program.clock`.

A worker binds that name to ELAPSED SIMULATION SECONDS, which never wrap.
Any consumer without a run — a still capture, a thumbnail — binds it to
ZERO, which is the instant the rest pose is defined at (cycle 1: "bind
the driver values with `time` at zero").

*Why not keep `$t`.* `$t` is the 0..1 animation fraction in every
document version 1 to 4; the viewer's slider and `animation.loop` are
built on that meaning. Giving it a second, version-conditional meaning —
seconds, unbounded — is the kind of thing that reads fine in a spec and
breaks in a playback loop. *Why not refuse an unbound read.* Cycle 1
rejected that and the reason still holds: it would fail a build whose
`simulate()` reads `self.time` for a reason that lives entirely in the
run. *Why a bare name rather than a minted one.* `time` is already
reserved: `set_state` documents it as "the one entry that is global by
contract", and `Run.bind()` passes it beside the whole bank. Minting
`_t0` would add a name kind for no gain.

**The hole that closes with it.** Because `time` is reserved and the run
binds it beside the bank, a root-declared driver or joint coordinate
whose qualified id is exactly `time` is ALREADY broken in cycle 1 —
`Run.bind()`'s `dict(self.bank, time=self.sim.time)` silently overwrites
it every tick. Publication makes the collision visible, so this cycle
refuses it at `Sim` construction, beside the existing driver/coordinate
clash refusal, naming the id and the reservation.

## 5. Published versus derived

**The rule: publish what COMPILE TIME decided; derive what the TICK
computes.** With one corollary, which settles the two cases the rule
alone does not: *a projection of published data with no decision inside
it is derived; a projection whose computation embeds a decision is
published.*

| Published | Why, and the alternative that lost |
| --- | --- |
| coordinate table, kinds, units, `initial` | `initial` is the rest render, which needs the CAD tree. *Lost:* the worker walks the tree — it has no tree. |
| `intermediates` | *Lost:* infer "not in `coordinates`" — that turns a mis-qualified name into an intermediate. |
| edges IN ORDER | Kahn's tie-break is arbitrary; two runtimes sorting independently would order two ready edges differently, and the order decides WHICH conflict a tick reports. *Lost:* publish unordered and sort in the worker. |
| law expressions, wiring factor, formula coefficients | The arithmetic itself is the contract. *Lost:* §1.3. |
| `affine` per driven end | `_affine_in_sources`'s degree rules over a skeleton are a whole algorithm. *Lost:* the worker analyses the DAG — a third place to keep in step. |
| jump plans: skeleton, postorder, level, `affine`, placeholder | The postorder, the `%` → `a − q*b` rewrite, and the level-quantity extraction with inner placeholders are three more divergence surfaces, and the worker can already SEE the jump primitives in the DAG — which is precisely why detecting them itself would look right and be subtly wrong. *Lost:* the worker builds its own plan. |
| `spans` | Compiled once from the declaration, refusals included. *Lost:* publish the raw `range` — a callable does not serialize. |
| `sources` | Derivable, and published anyway: the pass embeds two decisions — a `check` edge contributes nothing, and an input reaches ITSELF — that a worker would have to rediscover. This is the corollary's second half. |
| instructions, both forms | §6.2. |
| `identity` | A snapshot taken in one runtime and restored in the other must be refused across a changed machine. |
| `limits` | §1.6. |
| `clock` | §4. |

| Derived by the worker | Why |
| --- | --- |
| every bank value after the initial one | That is the machine running; it is the point. |
| `determiner` (id → the edge that gives it) | A one-line inversion of `gives` with no decision in it. Publishing it could disagree with the edges it projects. |
| the bank-key set | Same: `coordinates`' own keys. |
| per-tick increments, and each law's `f(end) − f(start)` | The tick. |
| crossing locations and the tick's partition | The tick: `JumpPlan.cuts` is a function of the tick's path. |
| a stop's `t*`, and whether an input PUSHES a stopped coordinate | Cycle 3 states outright that being reached is necessary and not sufficient, and that pushing is a property of the tick. |
| the segment loop, command admissions, statuses, retirement | The tick. |
| the pose, from the document's own expressions | Already published, unchanged. |

## 6. The version, and what each producer does with it

### 6.1 The version is a property of the root's declaration

`document_version(root_document, bindings, program=None)` returns 5 when
`program` is not None, and otherwise exactly what it returns today. Note
what this means and does not mean:

- A running root's document is ALWAYS 5, even with nothing shared and no
  flexible leaf. The version ladder below 5 is content-derived because
  those features are properties of the tree; `program` is a property of
  the ROOT'S DECLARATION, and a running root with a trivial program is
  still a machine a version 4 consumer would animate wrongly.
- An untimed or looping root NEVER reaches 5, and its document is
  byte-identical to today's — the obligation task 2 tests.
- The bump is NOT additive. A consumer ignoring `program` would read a
  document whose poses are bare coordinate ids it cannot bind, and refuse
  or render nothing. Which is why the refusal matters more than the key.

### 6.2 The instructions table

Under version 5 every declared instruction is published, each entry
carrying exactly one of `targets` and `by`, both keyed by qualified
driver id and both in design units, with `duration` in seconds.

Under versions 2 to 4 a relative instruction stays OMITTED, exactly as
cycle 1 left it. This is not tidiness: `drivers.ts` reads
`Object.entries(instruction.targets)` when a button is pressed, so a
version 4 entry without `targets` would throw in the shipped viewer at
the moment a maker clicks it. The omission is the version 4 contract and
it stays.

### 6.3 What each command does

The framework learns what the installed viewer can read from the existing
`solid_node.viewer` entry point: `bundle.document_versions()` returns the
report's `documentVersions`, or `[1, 2, 3, 4]` when the field is absent —
which is every viewer released so far. Cycle 5 adds the field in the
viewer's own repository; nothing here imports viewer code.

| Command | On a version 5 document |
| --- | --- |
| `solid build` | Publishes it. WARNS once when the installed viewer does not list 5, naming the version, the viewer's version, and that a viewer reading it is cycle 5's. |
| `solid develop` (with the viewer) | Publishes it and serves it. Same warning, from the same producer. The browser then refuses the document BY NAME — the designed behaviour, and the reason the CLI does not refuse: the build, the STLs and the tests are still useful, and `--no-web` is unaffected. |
| `solid develop --no-web` | Unchanged; no viewer, no warning. |
| `solid export` | Writes the manifest and the widget. Same warning. An export is an artifact that may be opened by a later viewer, so it is never refused. |
| The Sphinx directive | Does NOT produce a document: it embeds a COMMITTED export directory and copies the installed viewer's bundle beside it. It WARNS, reading the version off the `manifest.json` it already opens, and does not fail the build — the artifact is not its to fix, and the embedded widget refuses it visibly in the page. It loads no CAD runtime to do so, as that capability requires. |
| `solid snapshot --renderer web` | REFUSED by name, before the browser starts, when the installed viewer does not list 5 — naming the document version, the viewer's list and the viewer package version. A capture is a one-shot whose failure would otherwise surface as an opaque non-zero exit from a headless page, and the web-snapshot capability's standing posture is to fail with what is missing rather than substitute. |
| `solid snapshot --renderer openscad` | Unaffected, except §8.2's `--drive` and `--time`. |

*Alternative that lost:* `solid develop` refuses to start the browser at
all on a running root the viewer cannot read. Rejected — it would take
the watch loop away from a maker whose real complaint is one browser tab,
and the refusal already exists where the document is actually read.

*Alternative that lost:* gate on `apiVersion >= 8` instead of adding
`documentVersions`. Rejected: it would make the framework carry a magic
number about the viewer's own release counter, to answer a question about
the document schema. The report should state the fact it is asked for.

## 7. The conformance corpus

### 7.1 What it is

A JSON fixture written by the framework's own run and replayed by both
runtimes. It is the second half of ADR-022's pattern: the expected values
are PRODUCER values, so a disagreement means the consumer drifted.

`tools/generate_running_corpus.py` writes `tests/running-corpus.json`,
which is committed in the framework and copied into the viewer
(`solid_node_viewer/widget/src/running-corpus.json`) by cycle 5 — the
same arrangement `generate_parity_fixture.py` already has, with the
default target being the framework's own tests because the framework's
suite replays it too.

```
PYTHONPATH="$PWD" python tools/generate_running_corpus.py [OUTPUT]
```

### 7.2 The machines

Eight, every one an existing fixture of `tests/running_project/machine.py`
— cycles 1 to 3 built them and the suite already pins their behaviour:

| Machine | What it covers |
| --- | --- |
| `Train` | affine chain, a `clamp01` kink, a wiring into a plain port, both instruction forms, at two `dt`s |
| `Window` | `floor`, the pilot's own illustration; the periodic tooth window |
| `Clutch` | a comparison as a gate factor, multi-source, engagement mid-tick |
| `Ratchet` | an expression bound over the joint's own coordinate; reverse blocked at the last seated tooth |
| `Swept` | a stop on one group while an unrelated input runs its whole tick; `blocked` with fractional admitted travel |
| `TwoStops` | two groups stopping at two fractions of one tick |
| `StopAndJump` | a `wrap` fold and a stop in one tick, the crossing recorded at its fraction OF THE TICK |
| `CarryLead` | the Pascaline-shaped carry: multi-source, `floor`, a discontinuity the integration subtracts, at two `dt`s |

`Remainder` (`%`), `Throwing` (`sign`) and `Wrapped` (`ceil`) are added if
the coverage guard below finds a primitive uncovered — which it will, for
`%`, `ceil` and `sign`, so the list is nine to eleven machines in
practice. The guard decides, not the list.

### 7.3 The format

```
{
  "generated_by": "tools/generate_running_corpus.py",
  "corpus": "tests/running_project/machine.py",
  "tolerance": {"float": 1e-9},
  "machines": [
    {
      "name": "Train",
      "dt": 0.05,
      "document": { "format": …, "version": 5, "drivers": {…},
                    "instructions": {…}, "bindings": [...],
                    "program": {…} },
      "script": [
        {"tick": 0, "move":  {"input": "crank", "by": 10.0, "duration": 0.5},
                    "handle": "h0"},
        {"tick": 3, "rate":  {"input": "lever", "rate": 4.0}, "handle": "h1"},
        {"tick": 5, "trigger": "Advance",       "handles": ["h2"]},
        {"tick": 7, "snapshot": "a"},
        {"tick": 9, "restore":  "a"}
      ],
      "ticks": [
        {"tick": 1,
         "bank": {"crank": 1.0, "first.turn": 2.0, …},
         "crossings": [{"relation": "…", "coordinate": "first.turn",
                        "primitive": "floor", "level": 1.0, "t": 0.5}],
         "stops": [{"coordinate": "rack.travel", "bound": "high",
                    "value": 50.0, "t": 0.4, "inputs": ["steer"]}],
         "commands": [{"handle": "h0", "status": "active", "admitted": 2.0}]}
      ]
    }
  ]
}
```

- `document` carries the published document WITHOUT `root`, `pieces` and
  `animation`: the tree and the meshes are what the geometry tests cover,
  and what the run executes is the program. A framework test asserts that
  a machine's REAL document's `program`, `drivers`, `instructions` and
  `bindings` equal the fixture's, so the fixture cannot drift from the
  producer.
- `script` entries are applied BEFORE the tick they name is integrated,
  in array order. `handle` names the command the `ticks` entries report
  on; a `trigger` names one handle per input it claims, in the order
  `Run.trigger` issues them.
- `ticks` lists EVERY tick of the run, oldest first — not a sample. A
  run is short (20 to 60 ticks per machine) and a sampled fixture would
  let a divergence heal between samples.
- `crossings` and `stops` are the tick's own, in the order the run
  appends them; the machines run with `record=` large enough to keep all
  of them.
- `commands` reports every handle the script has created so far, with the
  status and admitted travel it holds AFTER the tick — including retired
  ones, because `blocked` and `completed` are exactly what must agree.

### 7.4 Tolerances

- EXACT (`==`): every tick number, every status word, every coordinate,
  relation, primitive, bound side and input name, every list ORDER, and a
  crossing's `level` (an integer surface, or zero).
- `1e-9` RELATIVE (`|a − b| <= 1e-9 * max(1, |a|, |b|)`): every bank
  value, every `t`, every `admitted`, every stop `value`.

`1e-9` is not a new number: it is `run.py`'s `_TOLERANCE`, the window
inside which the run itself declines to distinguish two increments. A
worker inside it cannot manufacture a disagreement the run would not
already have called agreement. Published as `program.limits.agreement`
too, so the fixture's tolerance and the algorithm's are one number.

### 7.5 The coverage guard

`uncovered_features(machines)`, mirroring
`generate_parity_fixture.uncovered_builtins`: the generator REFUSES to
write when the corpus misses any of the five jump primitives, a
multi-source law, a stop located inside a tick, an expression bound, a
`blocked` command, a `rate`, a snapshot/restore, a relative instruction,
an absolute instruction, or a tick with both a crossing and a stop. The
function is under direct test in the framework's suite, so the corpus's
width is visible without running the generator.

## 8. The three fixes

### 8.1 Two `Sim`s over one tree

**What happens today**, reproduced on `Train`:

```
a = Sim(Train_instance, 1/60)     # fine
b = Sim(Train_instance, 1/60)     # DoublyBound: Train.spindle is owned by
                                  # the running simulation, and Train would
                                  # bind it too.
```

The second `Sim`'s `_bind_initial` renders at rest, the relation
`crank.drives(spindle)` reaches `bind()`, the slot is still owned by the
FIRST run's `RunBinder`, and `_binder` is the relation's — so `bind()`
refuses. The message is about `simulate()`, and no `simulate()` is
involved. `ScenarioTest.simulation()` promises the opposite in its own
docstring: *"Fresh per call, never per class: the state bank a simulation
owns is the whole of what a run mutates, so two scenarios of one class
share nothing but the geometry they were built from."* The node IS shared
per class (`scenario_node`), so the second scenario of any running class
fails today.

**The fix, in two halves.**

*One tree, one owner, newest wins.* `Sim.__init__` RELEASES a previous
run's ownership before `_bind_initial`: pops `_run_binder` off the root,
and for every joint coordinate of the linked tree whose slot is
`run_owned`, clears `_value`, `binder` and `_enum_marker`. The rest
render then finds a tree no run owns and poses it exactly as a first
`Sim` does. Verified: with that release, a second `Sim` over a `Train`
that had been moved 20 degrees reads the rest bank back, identical to the
first `Sim`'s `initial`.

*A released run refuses to advance.* Without this the fix creates a new
silent wrongness — two live `Sim`s binding one tree, the last tick
winning the pose. So `Run` checks, before it binds, that the root's
`_run_binder` is still its own, and raises naming both: this simulation
no longer owns this tree, another was constructed over it, and a run's
bank means nothing once something else poses the tree.

**What the refusal keeps meaning.** An AUTHOR binding of a run-owned
coordinate — a `simulate()` that states a law imperatively — is still
refused, at the first `Sim`'s own construction, by the same `bind()`
test, with the same message. The release happens BEFORE the rest render
of a NEW simulation, and never during one.

*Alternative that lost:* make `bind()` admit any `RunBinder` over a
run-owned slot. It does not fix this case at all — the binder that
reaches `bind()` here is the RELATION's, at a moment when the second run
does not exist. *Second alternative:* an explicit `sim.release()` the
caller must call. Rejected: the scenario base's contract is "fresh per
call", and a contract that needs the caller to remember a teardown is not
that contract.

### 8.2 `solid snapshot` cannot pose a running root

`--set` reaches the root's declared PARAMETERS (`Length`, `Flag`, …), not
drivers; `--time` under a running root has no loop to scale, so it
keyframes a bare fraction into `time` and changes nothing the machine
does. A running root therefore photographs only at its declared driver
defaults.

**The fix.** `solid snapshot --drive NAME=VALUE`, repeatable, binds
declared drivers by qualified id through `set_state` after the node is
loaded and before it is keyframed and assembled. It works under every
root, not only a running one, because a driver-declaring untimed project
has exactly the same gap. Under a running root the result is the REST
POSE at those driver values — which cycle 1 calls "admissible by
construction", and which is exactly the state a `Sim` starts from.

**And what it refuses.** A `--drive` naming a JOINT COORDINATE id is
refused by name. Not from tidiness: `set_state` accepts a coordinate id
under a running root (cycle 1's `CoordinateDelivery` opened that door for
the run), and with no run to own it the enumeration that `set_state`
itself runs immediately overwrites the value from the drivers. Verified —
`set_state(**{'first.turn': 99.0})` on a `Train` with no `Sim` leaves
`first.turn` at `0.0` and reports nothing. So the refusal says what is
true: a coordinate's value is what the run makes of it; ask for the
drivers, or drive the machine in a scenario or in the browser.

**A still image WITH history is not offered here, and here is why.** A
bank with history is only meaningful if it is REACHABLE — the carry
half-way through its window with the register where the law would have
put it. The only thing that knows which banks are reachable is the run,
and the value object that names one is `sim.snapshot()`, checked against
the program identity. A `--drive`-style flag over coordinate ids would
let a maker photograph a machine that cannot exist. Posing a run state
for a still belongs where a run exists: cycle 5's browser, or a scenario
calling `solid snapshot` on a node it has posed. Recorded as an open
question rather than invented here.

### 8.3 The dangling `:doc:` reference

`docs/scenarios.rst:412` reads ``:doc:`solid_node.math <math>``` and
there is no `docs/math.rst`. The module is documented as a section of
`docs/api-reference.rst`, and the file's own neighbours use
``:doc:`… <api-reference>``` for it. Corrected to
``:doc:`solid_node.math <api-reference>```.

## 9. Risks

1. **A running root whose `simulate()` BRANCHES on a coordinate's value.**
   Symbolic publication binds a symbol where a number stood; a Python
   `if self.wheel.turn.value > 0` would then take one branch and publish
   it as a fact. This hazard already exists for drivers and the design
   names it ("Ordinary Python branching over unknown runtime values …
   does not automatically become JavaScript"), but coordinates widen the
   surface. Mitigation: the existing posture — a symbolic value raises
   where a number is required — plus a fixture that branches, and a task
   that records what actually happens.
2. **Document size.** The program adds every law; the pose expressions
   lose them. The module's own numbers are the measurement, and a task
   records version 4 versus version 5 bytes for the module and for a
   clock, so a regression is a number rather than an impression.
3. **Republication churn.** Placeholder names must be deterministic for a
   given tree or the builder republishes an unchanged model. Same
   obligation `bindings` already carries; same test.
4. **The corpus is only as wide as its machines.** Answered by §7.5's
   guard, and the guard is only as wide as its own list — which is why
   the list is in the spec, not only in the tool.
5. **The contract is specified here and implemented there.** Cycle 5 is a
   different repository with a different licence. Mitigation: the spec
   delta states the schema and the evaluation rules in full, in terms a
   TypeScript proposer can take verbatim, and the corpus is the
   executable half.
6. **`dt` is not published.** A worker choosing a coarse `dt` misses
   crossings — cycle 2's documented limit, now reachable by a maker who
   never sees a `dt`. The Pascaline's carry segments are 3 degrees wide.
   Recorded as an open question (§10.1), not decided here.

## 10. Open questions for the pilot

1. Resolved in review: `dt` is NOT published and stays the worker's
   choice, as `Sim(dt=)` is the caller's. For the supported law class the
   answer does not depend on it: a continuous law is exact across its
   kinks at any step, a jump is located inside whatever tick it falls in,
   and a stop is located inside the tick too. What `dt` changes is the
   granularity of commands and the first-order localization of a stop
   behind a nonlinear edge, which are the worker's trade-offs. Cycle 5
   picks its default and the corpus pins each machine's `dt` per
   scenario, which is what cadence independence is tested against.
2. **Should `solid snapshot` be able to photograph a REACHABLE run
   state** — a `sim.snapshot()` written to a file and replayed — rather
   than only the rest pose at given driver values? §8.2 argues the rest
   pose is the honest offer for this cycle.
3. **Should a released run be INVALIDATED (§8.1) or should a second `Sim`
   over a live tree be refused instead**, naming the first? This cycle
   lets the newest win, because the scenario base promises freshness per
   call and a shared node is how the runner hands one over.
4. Resolved in review: `program.coordinates` publishes each entry's
   DOMAIN (`rotational`, `translational` or `signal`, as the port kinds
   name them) beside its unit, for every input and joint coordinate. The
   schema is new in this cycle, so the field costs no version and saves
   cycle 5 a second reading of the tree for its jog and readout
   presentation.
5. **Should a version 4 document gain the relative instruction** under a
   new key the shipped viewer ignores? §6.2 says no, because the shipped
   viewer does not ignore it.
6. Carried, still the pilot's, from cycles 1 to 3: whether a CONSTANT law
   should be refused; whether crossing and stop records should be on by
   default under a running root; whether an integer-dtype input should
   stop only on whole native units; whether a bound may name a SECOND
   coordinate.

## 11. The ADRs to extract

- **ADR-110 (EXPORT): The compiled program is published in the document,
  under a version an old consumer refuses.** The decision that a running
  root's document carries the program the Python run executes — compile
  time's decisions, not the tick's — that a committed bank poses the
  geometry through the document's existing pose expressions, and that the
  version bump is a property of the root's declaration rather than of the
  tree's content. Extends ADR-034 (the shared node-tree document schema)
  and ADR-080 (the bindings table); depends on ADR-104 to ADR-109.
- **ADR-111 (EXPORT): A conformance corpus is the contract between the
  two runtimes.** The decision that the published program's semantics are
  pinned by a producer-generated fixture replayed by both runtimes,
  exact for discrete state and at the run's own agreement tolerance for
  floats, with a coverage guard that refuses to regenerate a corpus
  missing a stated feature. Beside ADR-022, whose pattern it repeats for
  the run.

A third decision — one simulation owns a tree at a time, and the newest
takes it (§8.1) — is a REPAIR of ADR-105 ("the run owns the coordinates
and binds them") rather than a new architecture. It is recorded as a
dated amendment on ADR-105 and as scenarios in the `simulation` spec.
Promoting it to its own ADR is offered to the pilot if the review
prefers.
