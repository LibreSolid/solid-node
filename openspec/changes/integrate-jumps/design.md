## Context

Cycle 1 built the machine this cycle finishes. Measured on this tree
(`solid_node/simulation/program.py`, `run.py`,
`solid_node/scad_expression.py`, `solid_node/math.py`):

- **A law is already an expression over its sources.** At construction
  each relation's law is applied ONCE to a `symbol(id)` per source, in
  the direction the rest render solved it, and the `ExpressionNode`
  graph that application builds is stored on an `Edge`
  (`program.py::_law_graphs`, `_graph_of`). `Edge.increments` then
  evaluates it twice per tick and returns the difference
  (`program.py:160-175`).
- **The five jump primitives are already named and already refused.**
  `_JUMP_CALLS = ('floor', 'ceil', 'sign')` and
  `_JUMP_OPERATORS = ('%', '<', '<=', '>', '>=', '==', '!=')`;
  `_graph_of` walks `postorder` and raises `UnsupportedLaw` by relation
  identity on any of them, saying jumps are the next cycle's
  (`program.py:392-410`).
- **`GraphValue.evaluate` is the evaluator, and its semantics are
  fixed.** `%` is `math.fmod` — `a − b·trunc(a/b)`, the sign of the
  DIVIDEND, which is the semantics OpenSCAD and JavaScript agree on and
  the reason `solid_node.math` has no `mod()`
  (`scad_expression.py:56-60`, `math.py` module docstring). A
  comparison evaluates through Python's `operator` and yields a `bool`,
  which arithmetic then reads as `1`/`0`. A `call` is dispatched to
  `solid_node.math` by name.
- **`wrap` and `piecewise` need nothing of their own.**
  `wrap(v, P) = v − P·ceil((v − P/2)/P)` is built on `ceil` because
  OpenSCAD has no `mod()`; `piecewise` is a sum of `clamp01` terms and
  is already continuous, already exact under cycle 1 (`math.py`).
- **`postorder` visits each reachable node identity once**
  (`expression_graph.py:24-38`), so a shared subgraph is ONE node with
  one branch — the sharing ADR-080 introduced survives into the jump
  plan for free.
- **The spike** (`workflow/open-run-simulation/spikes/kernel.py`)
  localized crossings with `_event_distance` (an analytic distance to
  the next periodic level along the current velocity), settled
  same-instant events in `_settle` (≤ 64 rounds), subdivided a tick in
  `_step` (≤ 1000 intervals), and carried `EPS = 1e-8` / `TIME_EPS = 1e-12`.
  Its `EPS` existed to answer "is this coordinate ON the surface"
  (`_on_surface`), and `_settle` existed because an event WROTE memory
  and two same-instant writes had to be ordered. The decision removes
  declared events and memory, so both questions disappear; what carries
  over is the localization discipline, the tolerances and the test
  scenarios (`workflow/open-run-simulation/evidence/report.md`).
- **The report's precision finding** — a billion crank turns cost
  `4.79e-5°` of wheel error, a trillion `0.00659°` — was measured on a
  design that recomputed the wheel from the crank. Under the integrated
  reading the driven coordinate accumulates independently of the
  source's magnitude; §11 measures what is actually left.

The authority is the pilot's decision of 2026-09-13 in
`workflow/open-run-simulation/design.md`, items 3, 4 and 5; the cycle
split is `roadmap.md`, "Execution, 2026-09-13".

## Goals / Non-Goals

**Goals:**

- Every relation whose expression contains `floor`, `ceil`, `sign`, `%`
  or a comparison compiles and integrates.
- Over one tick a law contributes the sum of its change over the
  continuous pieces between its crossings; a jump never moves a part.
- Every crossing inside a tick is found — several of one surface family
  (three tooth windows in one tick), several jump nodes, and nested
  jumps — not only the endpoints' difference.
- A law that moves only by jumping is refused by relation identity.
- A bounded, optional record of what crossed.
- No cost added to a continuous law, and the per-tick cost of a jump
  law measured against cycle 1's 1.16 ms.
- The Curta window and the Pascaline module's `handed_on` compile and
  integrate unchanged.

**Non-Goals:**

- Stops: a joint range still FAILS the tick rather than blocking the
  group (cycle 3). Nothing here localizes a range.
- Export of the compiled program, the browser worker, the conformance
  corpus (cycles 4 and 5).
- Declared events, declared memory, a `Running` object, a `running(r)`
  protocol, phase admissibility on re-engagement — all removed by the
  decision or named as later.
- A phase-plus-winding representation of a periodic coordinate (§11
  measures the boundary and defers the representation).
- A compiled evaluator. `GraphValue.evaluate` stays the evaluator;
  speed is cycle 4's.
- Reverse moves. Cycle 1 refuses them and this cycle does not lift that
  (the algorithm is direction-agnostic and needs no change when cycle 3
  does).

## Decisions

### 1. The five primitives, their level quantity, and their surfaces

A JUMP NODE is a `call` whose op is in `_JUMP_CALLS` or a `binop` whose
op is in `_JUMP_OPERATORS`. Each has a LEVEL QUANTITY `u` — a continuous
expression over the sources and over the branches of any jump nodes
inside it — and a family of SURFACES, the values of `u` at which the
node's value changes discontinuously:

| Node | Level quantity `u` | Surfaces | Branch on a segment |
| --- | --- | --- | --- |
| `floor(x)` | `x` | every integer | `m = floor(u)`, a constant |
| `ceil(x)` | `x` | every integer | `m = ceil(u)`, a constant |
| `sign(x)` | `x` | `0` | `σ = (u>0) − (u<0)` ∈ {−1, 0, +1} |
| `a % b` | `a / b` | every NONZERO integer | `a − q·b`, `q = trunc(u)` |
| `a ⊙ b`, ⊙ ∈ {`<`,`<=`,`>`,`>=`,`==`,`!=`} | `a − b` | `0` | `1.0` or `0.0` |

`%` deserves its row read carefully. `GraphValue.evaluate` computes
`math.fmod(a, b) = a − b·trunc(a/b)`, and `trunc` is `0` on the whole
of `(−1, 1)`: it jumps by `+1` at every integer of modulus at least
one and is CONTINUOUS at zero. So `a % b` is continuous where `a/b`
crosses zero and jumps where `a/b` crosses a nonzero integer. Its
branch is not a constant but the integer quotient `q`; with `q` fixed
the node reads `a − q·b`, which is continuous in `t` (and affine when
`a` and `b` are). A `%` whose divisor `b` is zero anywhere the tick
evaluates is refused for that tick, naming the relation: `a/b` has no
level there and `fmod(a, 0)` is `nan`.

`wrap()` and `piecewise()` get nothing of their own: `wrap` IS a `ceil`
node and integrates through this table, and `piecewise` is a sum of
`clamp01` terms with no jump node in it at all, already exact under
cycle 1.

The argument `x`, `a`, `b` is itself an arbitrary subgraph over the
sources, and may contain further jump nodes (§4).

*Alternative rejected:* adding `mod()`/`round()` to
`SYMBOLIC_BUILTINS` so a periodic law reads better. Out of scope, and
`math.py` documents why neither name exists (three runtimes, three
answers).

### 2. The path: a straight line in source space, parametrised by `t`

A tick moves a law's sources from the values they hold, `s⁰`, to
`s⁰ + Δ`, where `Δ` is the increment each source has already been given
by the program's ordering (cycle 1 guarantees every source of an edge
is determined before the edge runs). The path is the straight line

```text
s(t) = s⁰ + t·Δ,   t ∈ [0, 1]
```

— in the JOINT source space for a law naming several sources, which is
what makes the Pascaline's `(dial & wheel)` and the spike's clutch one
question rather than two. The parameter `t` is dimensionless; every
tolerance in §5 that is stated in `t` converts to a source's own units
by multiplying by that source's `Δ`.

A tick with `Δ = 0` on every source has a zero-length path and
contributes ZERO without evaluating anything. This is not a corner: it
is what an uncommanded input does on every tick, and it is also why the
sum of §3 must never be applied to a degenerate path (a one-point path
would read as `f(t⁻) − f(t⁺)`, i.e. minus a jump).

*Alternative rejected:* integrating each source's movement in turn
(source 1 from start to end at source 2's start value, then source 2).
It gives a different answer for a law that is not separable — the
clutch closing while the shaft turns is exactly that case — and it
would make the result depend on the order the sources were declared in.

### 3. Segments and branches: the constructive form of `Σ [f(t⁻) − f(t⁺)]`

Let `0 = t₀ < t₁ < … < tₙ = 1` be the path cut at every crossing (§4).
On each OPEN segment `(tᵢ, tᵢ₊₁)` every jump node holds one branch
(§1), because by construction its level quantity crosses no surface
there. Write `f_Bᵢ` for the law with each jump node replaced by its
branch on that segment. `f_Bᵢ` is continuous on the CLOSED segment
`[tᵢ, tᵢ₊₁]`, so

```text
f_Bᵢ(tᵢ)   = f(tᵢ⁺)      and      f_Bᵢ(tᵢ₊₁) = f(tᵢ₊₁⁻)
```

and the increment the decision asks for is computed with no epsilon and
no one-sided limit rule at all:

```text
Δdriven  =  Σᵢ [ f_Bᵢ(tᵢ₊₁) − f_Bᵢ(tᵢ) ]
```

Every jump is subtracted because no term of the sum ever spans one: the
value at `tᵢ` is taken on the branch of the segment ahead of it and the
value at `tᵢ₊₁` on the branch of the segment behind it.

**Branches are sampled at the segment's MIDPOINT**, `(tᵢ + tᵢ₊₁)/2`,
by evaluating each jump node's level quantity there in postorder and
reading off the branch column of §1. This is the central decision, and
it is what makes the whole algorithm free of epsilons and of direction
tests:

- The midpoint is a point genuinely INSIDE the segment, so the value
  read there IS the branch, exactly, at any magnitude of source.
- No rule is needed for "which side of the surface the law arrives
  from": a crossing of `floor` upward and downward, a tangency that
  touches a surface without crossing it, and a level quantity that sits
  EXACTLY on a surface for a whole segment all read correctly from one
  sample.
- A tick that begins or ends exactly on a surface needs no special
  case: `t₀ = 0` takes the branch of the segment ahead of it, which is
  `f(0⁺)`, and `tₙ = 1` the branch behind it, which is `f(1⁻)`. That
  is what makes the tick batching of §6 cadence-independent.

*Alternatives rejected.* (a) **Pinning the crossing node to its
one-sided limit values** — the form the decision's prose suggests and
this cycle's brief prefers over an epsilon. It is exact too, but it
needs a per-primitive left/right table AND the direction of travel of
the level quantity, it has no answer when the level quantity is tangent
to the surface, and it does not compose: when an OUTER jump's argument
is itself discontinuous at the same `t`, the outer's limits follow from
its argument's limits and must NOT be pinned, so the implementation
would have to distinguish "crossing continuously" from "jumping with
its argument" at every node. The branch formulation is the same
mathematics with none of those cases: a branch is constant on a
segment, so there is nothing to pin. (b) **Evaluating at `t ± ε`** —
rejected outright: `ε` has no correct value (at a source magnitude of
`3.6e11` a `t`-epsilon of `1e-12` is below the source's own `ulp` and
the evaluation lands back ON the surface), and it makes the answer
depend on a constant nobody can justify.

### 4. Enumerating the crossings

Jump nodes are taken in POSTORDER of the graph, so a node's level
quantity is asked where it crosses only after every jump node inside it
has already cut the path. The partition grows as the walk proceeds:

```text
T = {0, 1}
for j in jump nodes of the graph, in postorder:
    for each consecutive pair (a, b) of T:
        fix the branches of the jump nodes INSIDE j's level quantity,
          sampled at (a + b)/2
        u(t) = j's level quantity along the path, those branches fixed
        T |= { t ∈ (a, b) : u(t) reaches a surface of j }
```

On each pair `(a, b)` the inner branches are constant, so `u` is a
CONTINUOUS function of `t` on `[a, b]` and the search below is
well-posed. This is the whole of nesting: `floor(floor(x/10)/3)`'s outer
level quantity is constant between the inner's crossings, so it
contributes no new cut; the fixture of §6's alternating window is the
mechanically meaningful case.

**Affine level quantities are solved, not searched.** A level quantity
is AFFINE in the sources along the path when its branch-fixed graph is
built only of: numbers; source names; branch placeholders (constants on
this segment); unary minus; `+` and `−` of affine operands; `*` with at
least one operand constant; `/` by a constant operand; and the
branch-substituted form `a − q·b` of a `%` node whose `a` and `b` are
affine. Anything else — a `call`, a `^`, a product of two moving
operands — is not affine. The classification is structural and is done
ONCE at compile time, except for the `%`-divisor test, which needs the
branch. For an affine `u`, `u(a)` and `u(b)` determine it everywhere on
the segment, and

- for `floor`/`ceil`: every integer `m` with `min(u(a),u(b)) < m <
  max(u(a),u(b))` is crossed exactly once, at
  `t = a + (b − a)·(m − u(a))/(u(b) − u(a))`;
- for `%`: the same over the nonzero integers of `a/b` — which is
  affine only when the divisor is constant; a `%` with a moving divisor
  falls to the search below;
- for `sign` and a comparison: the single level `0`, crossed iff
  `u(a)` and `u(b)` straddle it.

Enumerating the integers — rather than differencing the endpoints —
is what makes a crank that passes three tooth windows in one tick add
three throws (§6).

**Anything else is bracketed and bisected.** `u` is sampled at
`_SUBDIVISIONS = 64` equal sub-intervals of `[a, b]`; within each, the
surfaces strictly between the two samples are the candidates, and each
is located by bisection on `u(t) − level` to the tolerance of §5. The
search therefore resolves any crossing pair separated by more than
1/64 of the tick's travel — at the Curta's 1.5° per tick that is
0.023° of crank, finer than anything a 240 Hz tick is resolving. A
non-affine level quantity that turns twice inside one sub-interval is
outside the guarantee and is stated as such (Risks); the answer is a
smaller `dt`, not a larger sample count.

**Coincident and near-coincident crossings.** Two crossings closer than
`_CROSSING_TOLERANCE` in `t` are ONE partition point (the later is
dropped); several jump nodes crossing at the same `t` are one partition
point whose midpoint sample fixes all their branches at once. There is
nothing to order and nothing to settle: the spike's `_settle` existed
because an event WROTE memory, and the decision removed memory. The
crossing RECORD (§10) lists coincident crossings in graph postorder
after sorting by `t`, so the listing is deterministic.

**A bound on the partition.** At most `_MAX_CROSSINGS = 1000` crossings
are admitted for one graph in one tick; beyond that the tick is refused
with `TooManyCrossings`, naming the relation, the driven coordinate,
the primitive and the count, and commits nothing — the same rollback
`RunConflict` takes. A thousand surfaces in one tick (240,000 a second
at the fixture's cadence) is a `dt` that is not resolving the
mechanism, and an unbounded partition would be an unbounded per-tick
cost inside a mode whose whole promise is bounded memory.

### 5. Tolerances, and the units they are in

Three numbers, and no more:

| Name | Value | Space | What it is for |
| --- | --- | --- | --- |
| `_CROSSING_TOLERANCE` | `1e-12` | `t`, dimensionless | the bisection's stopping bracket, and the width below which two crossings are one |
| `_SUBDIVISIONS` | `64` | count | the bracketing sample count for a non-affine level quantity |
| `_MAX_CROSSINGS` | `1000` | count | the per-graph per-tick partition bound |

`_CROSSING_TOLERANCE` is stated in `t` and converts to each source's
own units by multiplying by that source's tick travel `Δᵢ`: a crank
moving 1.5° in a tick has its crossing located to 1.5e-12°, and a
slide moving 0.1 mm to 1e-13 mm. Stating it in `t` rather than in a
coordinate's units is deliberate — a multi-source law has several
units and one path — and it is the same `TIME_EPS` the spike used. Its
justification is the run's own arithmetic: cycle 1 calls two increments
equal within `1e-9·max(1, |a|, |b|)`, so a crossing located three
orders finer than that can never manufacture a disagreement, and
bisecting further is below the resolution of `t` as a double over a
tick of unit travel. The bisection is capped at
`_BISECTION_ROUNDS = 64` as a safety net; 40 rounds already reach
`2⁻⁴⁰ < 1e-12` from a unit bracket.

There is deliberately NO surface tolerance — no `EPS = 1e-8`. The spike
needed one because it asked "is this coordinate on the surface"
(`_on_surface`); the segment formulation never asks. A level quantity
sitting exactly on a surface is read by the midpoint sample like any
other value.

### 6. The increment, with the pilot's numbers

The Curta illustration, exactly as the decision states it: the bench's
law made periodic,

```python
lambda angle: 4 + 72 * clamp01((angle - 360 * floor(angle / 360) - 113.5) / 11.25)
```

with `crank` at its default 100°, `dt = 1/240` and
`move('crank', by=360, duration=1.0)` — 240 ticks of 1.5°. The pinion
coordinate starts at the rest pose's `4`.

| Tick | crank | what happens | pinion |
| --- | --- | --- | --- |
| 0 | 100.0 | rest pose | 4.0 |
| 9 | 113.5 | the window opens exactly on a tick | 4.0 |
| 10 | 115.0 | in the ramp, 72·1.5/11.25 = 9.6 per tick | 13.6 |
| 16 | 124.0 | last ramping tick | 71.2 |
| 17 | 125.5 | `clamp01` saturates inside the tick | 76.0 |
| 173 | 359.5 | holding: the law's slope is zero here | 76.0 |
| **174** | **361.0** | **crossing at `t = 1/3`**, `floor` 0 → 1 | **76.0** |
| 240 | 460.0 | first turn complete | **76.0** |
| 414 | 721.0 | crossing at `t = 1/3`, `floor` 1 → 2 | 148.0 |
| 480 | 820.0 | second turn complete | **148.0** |

Every figure in that column is exact except the last, which reads
`147.99999999999994`: 480 increments summed is not a closed form, and
cycle 1's own tests compare an accumulated bank with `approx` for the
same reason. The tests of this cycle do the same, with `rel=1e-12`.

Tick 174 in full. `s⁰ = 359.5`, `Δ = 1.5`; the one jump node is
`floor(angle/360)`, its level quantity `angle/360` is affine, `u(0) =
0.998611…`, `u(1) = 1.002777…`, so the single integer strictly between
them, `m = 1`, is crossed at `t₁ = (1 − u(0))/(u(1) − u(0)) = 1/3`.
Two segments:

```text
(0, 1/3):  branch floor = 0 → f_B(0)   = 76.0   f_B(1/3) = 76.0   Δ = 0.0
(1/3, 1):  branch floor = 1 → f_B(1/3) =  4.0   f_B(1)   =  4.0   Δ = 0.0
```

The `−72` jump is subtracted and the pinion holds at 76. The 72 it
gained over the turn was gained in ticks 10..17, inside the window,
where the law's slope is not zero. Two teeth (or three) in ONE tick,
`move('crank', by=1080, duration=0)` from 100°: the level quantity runs
`0.2777… → 3.2777…`, the three integers 1, 2, 3 are crossed at
`t = 260/1080, 620/1080, 980/1080`, and the four segments contribute
`+72, +72, +72, 0` — the pinion lands on **220.0** and the crossing
record holds three entries. (Every figure in this section is
reproduced by `evidence/prototype.py`, a standalone check of §3–§5
written against the framework's own expression graph but outside
`solid_node/`; the implementation must reproduce them through the
framework's own evaluator, not through that file.)

Two more worked shapes the tests pin:

- **`2 * wrap(angle, 360)`** has slope 1 on every branch, so its
  integrated reading is the UNWRAPPED travel: from 100° through 500° of
  travel the driven coordinate gains exactly `1000.0`, with `ceil`
  crossings at `t = 0.16` and `t = 0.88`. A wrapped law integrates to
  the total.
- **`handed_on`'s shape** (the Pascaline's, with the fixture's own
  round constants: window open at 100, period 360, throw 60, segments
  `((100, 10, 20), (110, 40, 40))`, lead 0) hands on exactly `60.0`
  per revolution of the driving column and `120.0` over two. With a
  non-zero `CARRY_LEAD` the law is DISCONTINUOUS at the window
  boundary by `first_rise · lead / first_width`, and the integrated
  reading subtracts it: the fixture's lead of 0.5 makes the throw
  `59.0` and two throws `118.0`.

That last line is an empirical finding about the acceptance project,
not a framework question. The module's committed constants —
`CARRY_OPEN = 115.0`, `CARRY_LEAD = 0.10`, first segment
`(115.0, 3.0, 4.10)` — make `handed_on` jump by `4.10 · 0.10 / 3 =
0.136666…` at every window boundary, so under the integrated reading a
column hands on `65.403333…` per revolution rather than
`CARRY_THROW = 65.54`. The law compiles and integrates unchanged, which
is this cycle's obligation; whether the module wants the lead applied to
the phase reset as well is the module's own change, and this design
records the number so its migration starts from evidence.

### 7. Multi-source laws, and the clutch

A law over several sources takes the straight path in the joint source
space (§2); a surface may depend on all of them. The spike's clutch,
written in the vocabulary this cycle admits,

```python
(shaft.turn & sleeve.travel).drives(wheel.turn, law=clutch)
# law: lambda shaft, sleeve: -2 * shaft * (sleeve > 0.5)
```

behaves as the decision requires, and the three cases are one
computation:

| Tick | `shaft` | `sleeve` | partition | wheel increment |
| --- | --- | --- | --- | --- |
| open | 10 → 14 | 0 → 0 | none | `0.0` — the wheel holds |
| closed | 10 → 14 | 1 → 1 | none | `−8.0` — the pair drives |
| closing | 10 → 14 | 0 → 1 | `t = 0.5` | `−4.0` |

On the closing tick the branch is `0` on `(0, 0.5)` and `1` on
`(0.5, 1)`; the first segment contributes `0`, the second
`−2·(14 − 12) = −4`. The jump of `−2·shaft(t₁) = −24` that the absolute
reading would have applied at the instant of engagement is subtracted
whatever the shaft is doing on that tick — which is exactly "a jump
never moves a part", and exactly "re-engaging without a jump". Nothing
about phase ADMISSIBILITY on re-engagement is claimed: the decision
puts that outside the first increment and says so (item 9).

### 8. Disengagement contributes nothing, and propagation is untouched

Cycle 1's program has ONE determiner per coordinate, so a zero
increment and no increment are the same thing: a coordinate whose
determiner gives it zero holds, and so does a coordinate no edge
determines. This cycle therefore changes nothing in propagation, in
edge ordering, in the conflict rule or in the program's shape. There is
no `when=`, no edge switched on or off, no per-tick re-ordering.

Disengagement lives INSIDE a law, in one of two shapes, and both are
now expressible:

- a GATE FACTOR in a multi-source law — `shaft * (sleeve > 0.5)`, or
  `shaft * sign(...)` for a reversing one (§7);
- the ZERO-SLOPE REGION of a single-source law — the Curta window
  outside its ramp, where `clamp01` has saturated and the pinion holds
  while the crank turns on (§6, ticks 17..173).

Both were already the shape cycle 1 integrated; what this cycle adds is
that the gate may now be written with the operator that says it.

### 9. Two refusals: a law that only jumps, and a jump with nowhere to keep its history

**9a. A jump must drive a coordinate the run OWNS.** Cycle 1 lets a
relation drive an INTERMEDIATE — a plain port or a derived coordinate
that no bank holds but that reaches a bank coordinate through further
edges (`program.py::_reaching_the_bank`) — and keeps such an edge in
the program. Under a jump that is incoherent, and the incoherence is
measurable in cycle 1's own code:

- `Run._values()` recomputes every intermediate ABSOLUTELY from the
  bank on each tick (`run.py`, and the baseline's "Derived coordinates
  and plain ports SHALL NOT be stored"), which is right — an
  intermediate is a calculation, not a history. But the absolute value
  of a jumping law JUMPS, while the increment this cycle propagates
  from it does not. The intermediate and the bank coordinate behind it
  would then disagree by the accumulated jumps, visibly: the Pascaline
  module's `self.stop.angle = -self.wheel.value` would snap while the
  drum arbor it is wired to did not move.
- A DOWNSTREAM law edge reading that intermediate compounds the error:
  `Edge._inputs(values, deltas)` takes `values[key] + deltas[key]`, so
  it would start from the jumped absolute value and add the
  un-jumped increment.

So: **a law whose graph carries a jump and none of whose driven ends is
a bank coordinate is refused at construction, by relation identity**,
saying that a subtracted jump implies a history and only a coordinate
the run owns keeps one — state the relation into the joint coordinate
and let the port follow it. A continuous law driving an intermediate is
untouched: its absolute value and its increment agree by construction,
which is why cycle 1 could allow it.

This is not a corner. The Pascaline module as committed drives
`tens.wheel`, a `RotationalPort` wired to `tens.drum.turn`
(`simulation/module.py`), so its running migration must state the carry
into the joint. It already had to: cycle 1 refuses the carry relation
outright, because its SOURCE `units.wheel` is a plain port the root's
`simulate()` binds and no relation computes — `_refuse_opaque`. The
LAW — `handed_on`, `carried_column` — is
what this cycle promises to compile and integrate unchanged, and it
does; the declaration around it is the module's own migration, and this
refusal gives that migration a message that says what to do.

*Alternative rejected:* refusing only when a downstream LAW edge reads
the intermediate. It would leave the visible disagreement above (a
snapping port beside a smooth joint) unrefused, and it makes a law's
legality depend on what some other relation happens to read.

**9b. A law that only jumps.** Decision item 5: a law whose slope is
zero everywhere, moving nothing except by jumps, is refused as
arithmetic. The computable criterion:

> Build the graph's CONTINUOUS SKELETON by replacing every jump node —
> the node and its whole argument subtree — with an opaque constant. If
> the skeleton has no free coordinate name left, the law's value can
> change only by jumping, and every jump is subtracted, so the law can
> never move its driven coordinate. Refuse it at construction, by
> relation identity.

- `floor(turns)` → skeleton `C` → refused.
- `9 * enabled + floor(turns)` → skeleton `9·enabled + C` → NOT
  refused: `enabled` still carries slope.
- the Curta window → skeleton `4 + 72·clamp01((angle − 360·C −
  113.5)/11.25)` → `angle` survives → not refused.
- `handed_on` → skeleton keeps `wheel` → not refused.
- the clutch → skeleton `−2·shaft·C` → `shaft` survives → not refused.
- `2 * wrap(angle)` → skeleton `2·(angle − 360·C)` → not refused.

The message names the relation as written and the class that stated it,
says the law can only jump and that a jump never moves a part, and
points at what it is: **arithmetic, not a mechanism.** The case it
exists for is the Curta's carry bench,
`settled_value = lambda enabled, turns: 9 * enabled + floor(turns)`
(`projects/Calculators/Curta-Type-I-3x/simulation/carry_contact.py`) —
a dial position computed from an operand and a turn count rather than
driven by a mechanism. Be honest about the reach: as written,
`settled_value` is NOT refused, because `9 * enabled` carries slope;
what the running reading does to it instead is give the dial
`9·Δenabled` and nothing for the turns, so the arithmetic quietly stops
producing an answer, which is the campaign's whole point. The criterion
catches the pure form and no more.

*Alternative rejected:* a term-wise criterion, refusing a law any of
whose additive terms is jump-only. It has no well-defined "term" in a
DAG, and the obvious generalisation — refusing a jump node that cannot
affect the result except by jumping — would refuse `x * floor(y)`, a
stepped ratio, which is a perfectly good mechanism.

*Kept from cycle 1, deliberately:* a law whose graph has NO free name
at all — a constant — still compiles and contributes zero, as the
baseline states. It moves nothing, but it moves nothing by jumping
either, and untimed it legitimately pins its driven coordinate; the
running reading (the coordinate holds where the rest render put it) is
the same statement. Refusing it would change a requirement cycle 1
ratified after deliberating on it. Recorded as an open question.

### 10. What the run reports: a bounded crossing ring

`Sim(..., record=N)` already keeps a ring of the most recent `N`
`(tick, bank)` entries. It now also keeps a ring of the most recent `N`
CROSSINGS, read through `sim.crossings`, each a frozen

```python
Crossing(tick, relation, coordinate, primitive, level, t)
```

- `relation` is the edge's `description` — the relation as written —
  computed once at compile time, so appending an entry costs a tuple
  and no formatting;
- `coordinate` is the driven coordinate's qualified id, because a
  relation with several driven ends compiles one graph per end and the
  entry must say which one crossed (this is the one field added to the
  five the pilot's framing names);
- `primitive` is `'floor'`, `'ceil'`, `'sign'`, `'%'` or the comparison
  operator as written;
- `level` is the surface value in the LEVEL QUANTITY's own units — the
  integer for `floor`/`ceil`/`%`, `0.0` for `sign` and a comparison;
- `t` is the fraction of the tick, in `[0, 1]`.

Entries are appended in `(t, graph postorder)` order within a tick and
in program order across edges. `record=None` keeps nothing and builds
nothing — the crossing list is not even allocated, so a run that does
not record pays nothing for the record. `restore` and `reset` clear
both rings. The ring is bounded by the same `N`, so the mode's bounded
memory promise is unchanged.

*Alternative rejected:* folding crossings into the trajectory ring.
That ring is one entry per tick; a tick has zero or many crossings, and
merging them would either lose entries or unbound the ring.

### 11. Precision at a large origin

The report found that a periodic law over an ever-growing angle loses
precision in huge floats and recommended a phase-plus-winding
representation. That recommendation was made against the earlier
design, in which the wheel was RECOMPUTED from the crank; under the
integrated reading the driven coordinate accumulates on its own and
the crank's magnitude reaches it only through one tick's crossing.
This cycle therefore measures rather than assumes, and states the
boundary it finds:

- **Locating a crossing adds no error of its own.** For an affine level
  quantity the crossing is solved from the two source values the tick
  is handed, and the segment evaluation uses the same path; the answer
  is exact to the last bit at any magnitude the bank can represent.
- **What degrades is the bank.** A coordinate of magnitude `|s|`
  resolves movement only to `ulp(|s|) = |s|·2⁻⁵²`. A tick whose travel
  approaches that is quantised; below it, the travel is LOST and the
  machine stops moving.
- **Measured** on the Curta fixture (1.5° per tick, 240 ticks per turn,
  two turns), against the identical run at zero winding, by
  `evidence/prototype.py`:

  | initial winding | crank magnitude | `ulp` | max per-tick deviation | pinion after two turns, from a rest of 4.0 |
  | --- | --- | --- | --- | --- |
  | 0 | 100° | 1.4e-14 | — | 147.99999999999994 |
  | 10³ turns | 3.6e5° | 5.8e-11 | 0.0 | 147.99999999999994 |
  | 10⁶ turns | 3.6e8° | 6.0e-08 | 0.0 | 147.99999999999994 |
  | 10⁹ turns | 3.6e11° | 6.1e-05 | 0.0 | 147.99999999999994 |
  | 10¹² turns | 3.6e14° | 6.3e-02 | 0.0 | 147.99999999999994 |
  | 10¹³ turns | 3.6e15° | 5.0e-01 | 0.0 | 147.99999999999994 |
  | 10¹⁴ turns | 3.6e16° | 4.0e+00 | 144.0 | **4.0** — the crank does not move at all |

  (The last bits of `147.99999999999994` are cycle 1's accumulation, not
  this cycle's: 480 increments summed, not a closed form. It is
  BIT-IDENTICAL across six orders of winding, which is the finding.)

  The bound is `ulp(|s|) < per-tick travel`, and it is a CYCLE 1 bound
  (the bank's resolution), not a crossing bound. The test of §"tasks"
  measures the table and asserts the boundary at 10⁹ turns, which is
  where the report's own finding was taken.
- **Deferred:** the phase-plus-winding representation. Under integrated
  laws the coordinate IS the total travel and the law's own `floor` is
  what wraps it, so a second representation would have to be introduced
  for a problem this cycle cannot measure. It belongs with cycle 4's
  export, where a snapshot's serialisation is decided anyway.

### 12. Performance

The pin is cycle 1's measurement: `Train` at `dt = 0.1` costs
**1.16 ms** per tick against the untimed loop's 0.36 ms
(`openspec/changes/archive/2026-09-13-run-owns-the-coordinates/evidence.md`
§5.1, reproducible with that change's `evidence/probe_cost.py`). Two
rules keep this cycle answerable to it:

1. **A graph with no jump node takes cycle 1's path unchanged** — two
   evaluations, no partition, no midpoint sample. `Train` carries no
   jump, so its per-tick cost must come back within noise of 1.16 ms.
   This is the measurement the tasks require.
2. **A crossing search never evaluates the whole law.** At compile time
   each jump-carrying graph is rewritten ONCE into:
   - a SKELETON graph, the law with every jump node replaced by a free
     name `$j<k>` (and each `%` node by `a − $q<k>·b`), memoised by node
     identity so the DAG's sharing survives; and
   - one ARGUMENT graph per jump node, its level quantity with the jump
     nodes INSIDE it replaced by the same placeholders.

   A segment endpoint is then ONE `GraphValue.evaluate` of the
   skeleton over the sources plus that segment's branch values; a
   branch sample is one small evaluation per jump node; a crossing
   search is two argument evaluations per jump node per segment for the
   affine case. For the Curta window — one jump node, argument
   `angle/360` — a non-crossing tick costs two skeleton evaluations
   (what cycle 1 paid) plus three evaluations of a two-node argument,
   and a crossing tick costs four skeleton evaluations plus five
   argument ones.

One incidental saving falls out of §9a and is worth taking here:
`Run._values()` calls `edge.values(values)` on EVERY edge and then
discards the results whose keys are in the bank
(`run.py::_values`), so a law edge driving only bank coordinates
evaluates its graph once per tick for nothing. Skipping an edge whose
targets are all bank keys is behaviour-neutral (the discarded values
were never read), removes one evaluation per law per tick from cycle
1's cost as well as this cycle's, and — with §9a — means a jump graph
is never evaluated absolutely at all.

The tasks require the cost of a jump-carrying fixture to be MEASURED
and recorded beside 1.16 ms, not bounded in advance; the target is that
a non-crossing tick of a jump law stays inside twice cycle 1's, and any
overshoot is reported rather than optimised away here — a compiled
evaluator is cycle 4's.

*Alternative rejected:* compiling each argument to a Python closure at
construction. It would be faster and it is what cycle 4 will do for the
whole program; doing it here for arguments only would put a second
evaluator in the tree, which ADR-080's one-graph rule and the
Python/browser conformance obligation both argue against.

### 13. Module layout

`program.py` and `run.py`, extended. No third engine and no new module:

- `solid_node/simulation/program.py` — `_JUMP_CALLS`/`_JUMP_OPERATORS`
  become the recognised set; `_graph_of` stops refusing them and
  returns `(GraphValue, JumpPlan | None)`; new `JumpPlan` holding the
  skeleton, the ordered jump nodes with their argument graphs, surface
  families and affine flags, and the `increment(start, delta,
  crossings)` method implementing §3–§5; `_skeleton`,
  `_argument_graph`, `_affine_in_sources`, `_only_jumps`;
  `TooManyCrossings`; `Edge.plans` beside `Edge.graphs` and the branch
  path in `Edge.increments`.
- `solid_node/simulation/run.py` — the crossing ring, `Run.crossings`,
  the `TooManyCrossings` rollback in `integrate`, clearing in
  `restore`.
- `solid_node/simulation/sim.py` — `sim.crossings`.
- `solid_node/simulation/__init__.py` — `TooManyCrossings` lazily.

`Program.identity` is unchanged in FORM and changes in VALUE only where
a program now contains a law it used to refuse, which is the correct
behaviour (a snapshot cannot be restored into a different program). The
identity is taken of `described()`, which prints each graph's SCAD
text; the skeleton and the plan are derived from that graph and add
nothing to the listing.

*Alternative rejected:* a `solid_node/simulation/jumps.py`. The jump
plan is part of the compiled program — it is built at compile time,
stored on an edge, and carried into cycle 4's export with it — so
splitting it out would divide one question across two modules against
ADR-087.

### 14. What stays untouched

Untimed and looping documents and `Time(loop=)`; the bank and its
refusals; the program's node classification, ordering, identity and
every refusal of cycle 1 except the jump one; propagation, hold,
conflict and rollback; commands, ownership, retirement,
`Instruction(by=)`, snapshot, restore, reset, the trajectory ring; the
run binder and every solver rule cycle 1 added; the document schema and
the viewer; joints, ranges (a range still fails the tick), broadcasts,
groups; `SYMBOLIC_BUILTINS` and the published expression vocabulary;
every project.

### 15. Decisions that become ADRs after implementation

One, as the brief asks:

1. **How a jump is integrated** — a tick's path is cut at every
   crossing of every jump surface; on each segment the jump nodes hold
   a branch sampled at the segment's midpoint, making the law
   continuous there; the increment is the sum of the branch-substituted
   law's change over the segments, so a jump never moves a part.
   Carries with it: the five primitives' level quantities and surfaces
   (`%` as `fmod`, jumping at every NONZERO integer of `a/b`); the
   postorder walk that makes nesting work; the affine solve that finds
   every repeated crossing; and the two refusals of §9 — a law whose
   continuous skeleton has no free coordinate, and a jumping law that
   drives no coordinate the run owns, because a subtracted jump implies
   a history and only an owned coordinate keeps one.

A second candidate — the bounded crossing record — is deliberately NOT
proposed as an ADR: it is a diagnostic on the existing bounded
recording, not a boundary.

## Risks / Trade-offs

- [A non-affine level quantity that turns twice inside one of the 64
  sub-intervals has its crossing pair missed] → the answer is a smaller
  `dt`; every law in both originating projects is affine in its level
  quantity, so the search never runs for them. Stated in the docs and
  measured by a fixture that sits just inside the resolvable limit.
- [`min`/`max`/`abs` INSIDE a jump's argument make it non-affine, so
  `floor(max(x, 0))` falls to the search even though it is piecewise
  affine] → correct but slower; a piecewise-affine classifier is a
  later optimisation, not a correctness question.
- [A law whose graph carries a jump pays a partition even on ticks that
  cross nothing] → bounded by §12's rewriting: the extra work is
  evaluations of the small argument graph, not of the law. Measured.
- [`==`/`!=` are admitted uniformly although their one-sided limits are
  equal, so their "crossing" contributes nothing and only appears in
  the record] → uniformity is cheaper than a special case, and the one
  place the two differ from `<`/`>` — a level quantity identically zero
  over a stretch — the midpoint sample reads correctly. The residual
  hole is a NON-AFFINE level quantity exactly zero on a proper
  sub-interval, which no affine law can produce.
- [`_MAX_CROSSINGS` turns a very coarse `dt` into a refused tick rather
  than a slow one] → deliberate, and the message says which relation
  and how many; an unbounded partition is an unbounded per-tick cost in
  the one mode that promises bounded memory.
- [The Pascaline module's committed `CARRY_LEAD` makes `handed_on`
  discontinuous, so its throw integrates to 65.403333… rather than
  65.54] → a finding, recorded here with the number; the law compiles
  and integrates unchanged, which is this cycle's obligation, and the
  module decides what it wants in its own repository.
- [`Program.identity` changes for any root that used to be refused] →
  it could not have had a snapshot, because it could not be
  constructed.
- [The accumulated coordinate drifts in the last bits over many ticks
  (the fixture reads 147.99999999999994 after two turns)] → cycle 1's
  arithmetic, unchanged: an increment sum is not a closed form. Tests
  compare with `pytest.approx`, as cycle 1's do.

## Migration Plan

Additive and permissive: this cycle only turns refusals into
behaviour. No project changes; no root that constructs today changes
its answer, because a root that constructs today contains no jump. The
Curta bench and the Pascaline module opt in by declaring
`Time.running()` in their own repositories — which is what this cycle
unblocks. Rollback is restoring the refusal in `_graph_of`.

## Open Questions

- Should a CONSTANT law (no free name, no jump) be refused too, rather
  than compiling and contributing zero? §9 keeps cycle 1's ratified
  behaviour and argues for it; the decision's item 5 can be read either
  way.
- Should `settled_value`'s shape — a sloped term added to a jump-only
  term — be refused, or is the running reading (the jump-only term
  contributes nothing) the honest answer? §9 takes the latter.
- Should the crossing record be on by default under a running root,
  rather than tied to `record=N`? It is tied, so a run that records
  nothing pays nothing.
- Should a `%` with a MOVING divisor be refused rather than searched?
  It is searched; no project writes one.
