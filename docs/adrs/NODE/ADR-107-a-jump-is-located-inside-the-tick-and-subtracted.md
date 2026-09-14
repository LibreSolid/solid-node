# ADR-107: A Jump Is Located Inside the Tick and Subtracted

**Status:** Accepted
**Date:** 2026-09-13
**Depends on:**
- [ADR-106: One law, two readings — a relation is inspected as an expression](./ADR-106-one-law-two-readings.md)
- [ADR-105: The run owns the coordinates and binds them](./ADR-105-the-run-owns-the-coordinates-and-binds-them.md)
**Cites:**
- [ADR-022: Cross-runtime degree trig parity for `$t` expressions](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)
- [ADR-076: Mechanism laws as compositions over expression math](../MATH/ADR-076-mechanism-laws-as-compositions-over-expression-math.md)
- [ADR-080: A shared subexpression is named once](../EXPORT/ADR-080-a-shared-subexpression-is-named-once.md)
**OpenSpec change:** `integrate-jumps`

## Context and Problem Statement

ADR-106 integrated every CONTINUOUS law exactly and refused, by name,
any whose expression contains `floor`, `ceil`, `sign`, `%` or a
comparison. That refusal covers the two laws the running mode exists
for. Both are periodic:

- the Curta's tooth window, `4 + 72 * clamp01((angle − 360 *
  floor(angle / 360) − 113.5) / 11.25)`, whose pinion must stand at `4`
  at the crank's rest, at `76` after one crank turn and at `148` after
  two;
- the Pascaline module's carry, `handed_on`, where `floor` counts the
  carry windows the driving column has already passed and six `clamp01`
  segments shape the one in progress.

Read absolutely, a periodic law can only say where a part IS for a
source value: after a whole revolution the Curta's pinion reads exactly
what it read before, and the throw it made in between is lost. That is
the campaign's originating failure, and it is the reading a running root
exists to replace.

The difficulty is that `f(end) − f(start)` over a tick is WRONG for such
a law in a different way: it adds the discontinuity. On the tick in which
the crank passes 360 degrees, the window's `floor` steps from 0 to 1 and
the law's value falls by 72 — so the endpoint difference would drive the
pinion BACKWARD by a whole throw. The mechanical fact is the opposite: a
jump is where a mechanism's description changes, not where a part moves.
The pilot's decision of 2026-09-13, item 4, states it directly — the
crossings of a law's jump surfaces are located inside the tick and the
jumps SUBTRACTED; a jump never moves a part.

## Decision Drivers

- The two originating laws must compile and integrate UNCHANGED. A
  project does not rewrite its mechanism to be simulated.
- Every crossing inside the tick must be found, not only the difference
  of its ends: a crank turned fast enough to pass three tooth windows in
  one tick adds three throws, and a display cadence must not change a
  machine's answer.
- No epsilon anybody has to justify. A source of magnitude `3.6e11`
  makes a `t`-epsilon of `1e-12` land below the source's own `ulp`, so
  an offset evaluation falls back onto the surface it was meant to step
  off.
- No cost added to a law that does not jump. ADR-106's recorded
  1.16 ms/tick is the pin.
- What the reading cannot support must be refused by relation identity,
  as ADR-106 refuses, rather than integrated wrongly.

## Considered Options

1. **Pin the crossing node to its one-sided limit values.** Exact, and
   the form the decision's prose suggests. Rejected: it needs a
   per-primitive left/right table AND the direction of travel of the
   level quantity, it has no answer when the level quantity is tangent
   to the surface, and it does not compose — when an OUTER jump's
   argument is itself discontinuous at the same instant, the outer's
   limits follow from its argument's and must NOT be pinned, so the
   implementation would have to tell "crossing continuously" from
   "jumping with its argument" at every node.
2. **Evaluate at `t ± ε`.** Rejected outright, for the magnitude reason
   above: `ε` has no correct value, and it makes the answer depend on a
   constant nobody can justify.
3. **Difference the endpoints of the level quantity and apply one jump
   per unit of difference.** Rejected: it is the right answer only for a
   single affine `floor` and says nothing about where the crossings are,
   which is what a nested jump, a multi-source gate and the crossing
   record all need.
4. **Refuse a jumping law and ask projects to write the phase
   differently.** Rejected: it is the campaign's whole subject, and the
   two laws are correct as written.

## Decision

**A law whose expression contains a jump contributes, over one tick, the
CONTINUOUS part of its change: the tick's path is cut at every crossing
of every jump surface it meets, and the law's change is summed over the
pieces between those cuts.**

The PATH is the straight line from the values the law's sources hold to
those values plus the increments they were given, parametrised by `t` in
`[0, 1]` — in the JOINT space of the sources for a law naming several,
which is what makes a clutch closing while a shaft turns one question
rather than two. A tick in which no source moves contributes zero
without evaluating anything.

Each jump node has a LEVEL QUANTITY and a family of SURFACES:

| Node | Level quantity | Surfaces | Branch on a piece |
| --- | --- | --- | --- |
| `floor(x)`, `ceil(x)` | `x` | every integer | that integer |
| `sign(x)` | `x` | `0` | `−1`, `0` or `+1` |
| `a % b` | `a / b` | every NONZERO integer | the quotient `q`, the node reading `a − q·b` |
| `a ⊙ b`, a comparison | `a − b` | `0` | `1` or `0` |

`%` earns its row: the operator is `fmod`, which takes the sign of the
DIVIDEND, and `trunc` is `0` on the whole of `(−1, 1)` — so `a % b` is
CONTINUOUS where `a / b` crosses zero and jumps only at a nonzero
integer of it. `wrap()` is a `ceil` node and integrates through this
table; `piecewise()` is a sum of `clamp01` terms with no jump in it at
all.

**A branch is read at the piece's MIDPOINT.** That is the decision that
makes the whole algorithm free of epsilons and of direction tests: the
midpoint is a point genuinely inside the piece, so the value read there
IS the branch, exactly, at any magnitude of source; a crossing upward, a
crossing downward, a tangency that touches a surface without crossing
it, and a level quantity sitting exactly on a surface for a whole piece
all read correctly from one sample. A tick that begins or ends exactly
on a surface needs no special case: `t = 0` takes the branch of the
piece ahead of it and `t = 1` the branch behind it, which are precisely
`f(0⁺)` and `f(1⁻)`.

With every jump node replaced by its branch, the law is CONTINUOUS on
the closed piece, so the increment is

```text
Δdriven  =  Σᵢ [ f_Bᵢ(tᵢ₊₁) − f_Bᵢ(tᵢ) ]
```

and every jump is subtracted because no term of the sum ever spans one.

Jump nodes are taken in the graph's POSTORDER, so a node's level
quantity is asked where it crosses only once every jump node inside it
has already cut the path — on each pair of consecutive cuts those inner
branches are constant, which is what makes nesting work and what makes
the search below well-posed. Where a level quantity is AFFINE in the
sources along the path — structurally: numbers, source names, branch
placeholders, unary minus, `+`/`−`, `*` with a constant operand, `/` by
one — every surface strictly between its two endpoint values is SOLVED,
all of them, which is what makes three tooth windows in one tick three
throws. Anything else is sampled at `_SUBDIVISIONS = 64` sub-intervals
and each bracketed crossing bisected to `_CROSSING_TOLERANCE = 1e-12` in
`t`; a level quantity that turns twice inside one sub-interval is
outside that guarantee, and the answer to it is a smaller `dt`.

Two crossings closer than the tolerance are ONE cut. A tick that would
cut one law's path more than `_MAX_CROSSINGS = 1000` times is refused
naming the relation, the coordinate, the primitive and the count, and a
`%` whose divisor is zero anywhere the tick evaluates is refused the same
way; both commit nothing, exactly as a conflict does.

**Two laws are refused at construction, by relation identity:**

- a law that can move its coordinate ONLY by jumping. The criterion is
  the law's CONTINUOUS SKELETON — every jump node reduced to what a
  fixed branch leaves of it, which is a constant for four of the five
  primitives and `a − q·b` for `%` — having no free coordinate left.
  Every jump is subtracted, so such a law can never move anything: it
  states arithmetic, not a mechanism. `floor(turns)` is refused;
  `9 * enabled + floor(turns)` is not, because `enabled` still carries
  slope;
- a jumping law none of whose driven ends is a coordinate the run owns.
  A subtracted jump implies a HISTORY, and only an owned coordinate
  keeps one: a plain port and a derived coordinate are calculations the
  ordinary enumeration recomputes absolutely from the bank on every
  tick, so such an end would snap by the accumulated jumps while the
  joint behind it moved smoothly, and a downstream law edge reading it
  would compound the error. The message says to state the relation into
  the joint coordinate and let the port follow it.

**For performance the plan is a rewriting, not a second evaluator.** At
compile time each jump-carrying graph is rewritten ONCE into a SKELETON
(the law with every jump node replaced by a free placeholder name,
memoised by node identity so the sharing of ADR-080 survives) and one
ARGUMENT graph per jump node (its level quantity, with the jump nodes
inside it replaced by the same placeholders). A piece's endpoint is then
one evaluation of the skeleton; a branch sample is one small evaluation
per jump node; a crossing search never evaluates the whole law.
`GraphValue.evaluate` stays the only evaluator (ADR-022, ADR-076,
ADR-080).

## Consequences

- The Curta bench's window and the Pascaline module's `handed_on`
  compile and integrate unchanged, which is what this cycle owed them.
  The pinion reads `4`, `76`, `148`; the module's column hands on
  `65.403333…` per revolution rather than its declared
  `CARRY_THROW = 65.54`, because its committed `CARRY_LEAD = 0.10` makes
  the law discontinuous at the window boundary by `4.10 · 0.10 / 3`.
  That deficit is a finding for the module's own migration, not a
  framework question: the integrated reading subtracts the jump the lead
  introduces, which is the whole point.
- Disengagement needs no switch, no `when=` and no per-tick re-ordering:
  it lives inside a law, as a gate factor in a multi-source law or as
  the zero-slope region of a single-source one, and a gate that closes
  mid-tick gives the travel after engagement only. Propagation, edge
  ordering, the conflict rule and the program's shape are untouched.
- The declared cost holds. A graph with no jump node takes ADR-106's
  path unchanged — two evaluations, no partition — and a jump-carrying
  law costs 1.3× its continuous twin on a non-crossing tick and 1.8× on
  a crossing one, measured on the same machine. `Run._values()` now
  skips an edge whose targets are all bank coordinates, whose results it
  computed and discarded, which takes one evaluation per law per tick
  off ADR-106's cost as well: 1.07 ms/tick against its recorded 1.16.
- Locating a crossing adds no error of its own: for an affine level
  quantity it is solved from the two source values the tick was handed,
  and two turns of the Curta window read BIT-IDENTICALLY from zero
  winding up to `10¹³` turns of it. What degrades at `10¹⁴` is the
  BANK's own resolution — `ulp` exceeding the tick's travel — which is
  ADR-105's bound, not this one's. A phase-plus-winding representation
  is therefore not introduced.
- A crossing reached exactly at a tick's own boundary is integrated
  correctly and contributes nothing, but is not "located inside a tick"
  and so does not appear in the crossing record.
- `Program.identity` changes in VALUE for any root that used to be
  refused — which could not have had a snapshot, because it could not be
  constructed. Its FORM is unchanged: the identity is taken of the
  graphs' SCAD text, and the skeleton and the plan are derived from
  those graphs.
- The plan is part of the compiled program — built at compile time,
  stored on an edge — so it travels with the program into the cycle that
  exports it and the browser worker that executes it.
