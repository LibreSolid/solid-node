## Context

`solid_node/math.py` is the source of truth for the one expression semantics
ADR-022 records: OpenSCAD's degree conventions, with `^` as power, agreed on
by Python, OpenSCAD and the viewer's single TypeScript evaluator. Every
function in it wears three faces:

1. **numeric** — plain numbers, computed with the standard library in degrees;
2. **symbolic** — any argument an `OpenSCADConstant` (solid2's `$t`, or a
   qualified driver token), returning a new `OpenSCADConstant` whose string is
   an OpenSCAD call over the rendered arguments;
3. **declarative** — any argument an `Expression` (ADR-062's parameter tokens
   and formulas), returning a `Formula` whose dimension `function_formula` in
   `solid_node/parameters.py` assigns.

The module exports eight functions. Everything a project needs beyond them it
writes itself, and the workspace shows what that costs — four verbatim copies
of a `sqrt`-based clamp kit, four models importing
`solid2.core.object_base.OpenSCADConstant` to reach `floor`, and three
different hand-rolled point rotations, two of them numeric-only. The proposal
lists the originating files.

The false premise those copies rest on was checked against the code, not
assumed. `solid-node-viewer/solid_node_viewer/widget/src/evaluator.ts` builds
its evaluation scope by walking `Object.getOwnPropertyNames(Math)` and copying
every one, then overriding the trigonometry to degrees. `abs`, `floor`,
`ceil`, `min`, `max`, `sign` and `pow` are therefore all in scope already, and
OpenSCAD has builtins of exactly those names. Nothing in the viewer needs to
change for this cycle.

A second thing was checked rather than assumed: solid2's `OpenSCADConstant`
already defines `__abs__`, so Python's builtin `abs()` on a symbolic value
returns `abs($t)` today. What it does not do is give a `Formula` an `abs`, or
give the module one uniform place where the numeric and symbolic faces of a
name are known to be the same function.

## Goals / Non-Goals

**Goals:**

- Give a project the expression vocabulary it demonstrably needs, in the
  module that already owns the semantics, with all three faces.
- Emit only expressions OpenSCAD and the viewer's evaluator compute
  identically to Python, and prove it in the parity corpus rather than
  asserting it.
- Remove the reason a project reaches into solid2's private object base.
- Keep every existing expression string byte-identical, so no published
  document, no fixture case and no build artifact changes.

**Non-Goals:**

- Mechanism laws — gear mesh, slider-crank, lead screw, delta kinematics,
  circle intersection, timeline slicing. The pilot is planning those as a
  separate cycle; nothing here anticipates their shape.
- Any change to `solid-node-viewer`. Its evaluator already answers every name
  emitted here, and the regenerated fixture is committed in that repository
  under the pilot's decision.
- Migrating the originating projects. Two are used as validation evidence and
  neither commit belongs to this cycle.
- A general expression-simplification or common-subexpression pass. The
  compositions below are written out, and `piecewise` in particular grows
  linearly with its waypoint count.

## Decisions

### D1 — Two layers, one module

Layer 1 is scalars. Within it, only the six direct builtins touch
`function_formula`; layer 1's compositions do not, for the reason D5 gives.
Layer 2 is vector helpers, defined purely as composition over layer 1, so it
needs no dimension rule and no symbolic branch of its own: a symbolic or
declared component reaching `rotate_x` flows through layer 1's dispatch
without layer 2 knowing which face it is on. That is also why layer 2's
helpers are worth having at all — the two originating copies of `polar` and
`_turn` were written against Python's stdlib and break on a symbolic driver.

*Alternative rejected:* a separate `solid_node.vectors` module. The helpers
are three lines each and are meaningless without the degree convention layer 1
carries; a second module would only make the import line longer.

### D2 — The direct builtins are `abs`, `floor`, `ceil`, `min`, `max`, `sign`

Each is a name OpenSCAD and JavaScript's `Math` both carry, with identical
semantics on every input the framework can produce, so the symbolic face is
one `_symbolic_call` and needs no rewriting anywhere downstream.

`min` and `max` take **exactly two arguments**. OpenSCAD's `min`/`max` accept
a vector or a variable number of arguments depending on version, and
JavaScript's are variadic; pinning the arity at two keeps the emitted string
in the intersection every version of every runtime agrees on, and every
originating caller wanted two. A three-way minimum is `min(min(a, b), c)`.

`sign` has no originating caller — every other name in this change has at
least one. It is included because it completes the direct-builtin set the
pilot agreed in principle, costs one dispatch, and is the only way to get a
direction out of a symbolic difference without a branch. **This is the one
name here proposed on the strength of the direction rather than of evidence,
and it is the cheapest one to drop** if the pilot prefers evidence-only.

`ceil` likewise has no direct originating caller, but `wrap` is built on it
(D5), and floor without ceil is half a pair.

### D3 — `round` is left out

OpenSCAD rounds a half **away from zero** (`round(-0.5) == -1`), JavaScript's
`Math.round` rounds a half toward **positive infinity** (`Math.round(-0.5)
=== -0`), and Python's `round` rounds a half **to even** (`round(0.5) == 0`).
Three runtimes, three answers, on an input a timeline lands on constantly.
Exporting a `round` would be exporting a parity defect.

No kinematics module in the workspace uses `round` on a symbolic path —
checked, not assumed. A caller who wants half-up writes `floor(x + 0.5)`,
which all three runtimes agree on exactly.

*Alternative rejected:* define `round` explicitly on all three runtimes. That
requires changing the viewer's evaluator (an AGPL repository, a separate
change) and still cannot change OpenSCAD, so the symbolic face would have to
emit `floor(x + 0.5)` under the name `round` — a name that lies about what it
does. Better to make the caller write the honest expression.

### D4 — `mod` is left out, and `wrap` is built on `floor`

Two separate problems, both fatal:

- **OpenSCAD has no `mod()` function.** It spells the operation as the `%`
  operator. The viewer's evaluator nevertheless defines `mod(a, b)` in its
  scope, so emitting `mod(a, b)` would evaluate in the browser and fail to
  parse as OpenSCAD — a divergence in exactly the direction ADR-022 exists to
  prevent.
- **`%` itself disagrees.** solid2's `OpenSCADConstant.__mod__` emits
  `($t % 3)`, which OpenSCAD and JavaScript both evaluate C-style, with the
  sign of the dividend; Python's `%` takes the sign of the divisor. A numeric
  face written with Python's `%` would silently disagree with both other
  runtimes for a negative left operand.

So no `mod`, and `wrap` — the one originating need for periodicity — is built
on `ceil`, which every runtime agrees on:

    wrap(value, period=360.0) = value - period * ceil((value - period / 2) / period)

which lands in `(-period/2, period/2]`: `wrap(180) == 180`, `wrap(-180) ==
180`, `wrap(-181) == 179`. That is the interval
`projects/pascaline/pascaline/kinematics.py` documents for its own `wrap`, so
the framework's name means what the originating project's did.

*Alternative rejected:* keep pascaline's `atan2(sin(x), cos(x))`. It is
correct on the same interval and needs nothing new, but it costs three
transcendental calls per wrap, loses precision for a large `value`, and hides
what it does. The floor/ceil form is exact and reads as what it is. Both are
symbolic-safe; this is a quality choice, not a correctness one.

**A finding to record, out of scope to fix:** the `%` sign divergence above is
live today for any project writing `a % b` on a symbolic value. Nothing in the
framework or the corpus catches it. Reported rather than fixed here.

### D5 — The compositions, and what did not earn a name

Every composition is written out of layer 1 and the existing functions, so
each is one expression all three runtimes evaluate:

| name | definition | originating evidence |
| --- | --- | --- |
| `clamp(x, low, high)` | `min(max(x, low), high)` | 3 clock models (`clamp`) |
| `clamp01(x)` | `clamp(x, 0.0, 1.0)` | abacus, fender-bender, pascaline |
| `ramp(x, start, end)` | `clamp01((x - start) / (end - start))` | pascaline (`ramp`), inlined in abacus and fender-bender |
| `lerp(a, b, u)` | `a + (b - a) * u`, unclamped | pascaline's stylus path (twice, inline); the shape inside fender-bender's `piecewise` |
| `wrap(value, period=360.0)` | D4 | pascaline (`wrap`, `wrap_period`) |
| `piecewise(x, points)` | fender-bender's sum of clamped ramps | fender-bender (`piecewise`), pascaline's roll nodes |
| `bump(u)` | `p = clamp01(u); 16 * p * p * (1 - p) * (1 - p)` | fender-bender (`bump`) |

`piecewise` keeps fender-bender's formulation — start at the first `y` and add
`(y_b - y_a) * clamp01((x - x_a) / (x_b - x_a))` per segment — because a sum of
clamped ramps has no branch and no `min` chain, and is therefore the shortest
expression that is also exact at every waypoint. Its cost is length: `n`
waypoints produce `n - 1` clamp terms, so fender-bender's nine-waypoint release
path is eight of them, each a `min(max(...))`. That is a real size increase
over the `sqrt` form (which was also `n - 1` terms, of comparable length), and
it is accepted.

**A composition gets no branch in `function_formula`.** This is the rule that
keeps a composition a composition. A rule branch would give each of these
names two definitions — a `Formula` carrying its own symbol and dimension
rule, and the composition its numeric and symbolic faces are — and the
declared face would stop being the same function as the other two, which is
the property this module exists to hold. So `clamp`, `clamp01`, `ramp`,
`lerp`, `wrap`, `piecewise` and `bump` have exactly one definition each: the
composition. Reached with a declared token, each simply builds the formula
tree its own body describes, and its dimension behaviour is a *consequence*
of the primitives' rules plus the algebra's addition, multiplication and
division rules — never a rule registered for the composition. The
`declarative-nodes` delta states those consequences anyway, because they are
what a caller experiences and what the scenarios test, but it states them as
consequences.

One consequence is worth naming because it will surprise someone:
`clamp01(length)` and `max(length, 0.0)` **raise**. A plain number is
dimensionless, `min`/`max` require equal dimensions, and a `Length` is not
dimensionless — so a bare numeric bound against a dimensioned quantity is
refused, exactly as `length + 1` is refused today. That is the intended
behaviour and not a defect: the cure is a dimensioned bound. `clamp01` is a
dimensionless-domain function to begin with, so a caller wanting to bound a
length states the bounds as lengths and uses `clamp`.

The same consequence reaches every composition holding a numeric literal
beside its argument, and there are two more. **`wrap(angle)` raises on a
declared `Angle`**, because the default period `360.0` is a plain number and
`angle - period / 2` mixes the angle axis with dimensionless; the declared
call states the period as a quantity, `wrap(bearing, Angle(360.0))`, and gets
a derived `Angle` back. And **`turn`'s default centre** would do the same to
a point of declared quantities. That one is fixed in the composition rather
than left to the caller — see D5b — because unlike a period, a centre of the
origin means "do nothing", and a composition should not make the caller pay
dimensionally for an operation it is not performing.

None of this touches the numeric or symbolic faces: a plain number and an
`OpenSCADConstant` carry no dimension to disagree about.

Its `x` coordinates must be plain numbers in strictly increasing order,
validated at call time. They always are: a waypoint table is authored data,
never a driver expression. Only `x` may be symbolic. Validating loudly is
what stops a duplicated `x` becoming a division by zero buried in a published
expression string.

`bump` is a polynomial, not fender-bender's `sin(180 * clamp01(u))²`, and the
reason is the third face. `sin` requires an `Angle`, a plain number is
dimensionless, and `Angle` is its own axis — so `180 * clamp01(u)` over a
declared token is dimensionless and `sin` refuses it:
`sin(<dimensionless>): <dimensionless> is dimensionless, and sin takes an
Angle`. The trigonometric form therefore has no declared face at all, for any
declared argument, which is the one thing this module is not allowed to ship.
`16 p²(1-p)²` has all three faces, needs no rule branch (so D5's composition
rule and the whole of the primitives/compositions split stay intact), and is
exact rational arithmetic with no transcendental call, so the three runtimes
agree on it trivially rather than to within a tolerance.

The curve is not the same curve, and that is stated rather than glossed. Both
are smooth 0–1–0 pulses: both are zero at and below 0 and at and above 1, both
peak at exactly 1 at `p = 0.5`, and both have zero slope at each end. Between
those points they differ — at `p = 0.25` the polynomial gives `0.5625` where
`sin²(45°)` gives `0.5`, and at `p = 0.1` it gives `0.1296` against `0.0955`.
The shape was never a contract: fender-bender's docstring promises "a smooth
0-1-0 pulse over u in [0, 1], zero outside", which the polynomial is. A
project that wants that exact curve keeps it by writing `sin` out, which costs
one line and is what a project should do when it wants a specific curve rather
than a pulse.

One cost to note: `clamp01(u)` appears four times in the emitted polynomial
where it appeared twice inside `s = sin(...); s * s`, because there is no
let-binding on the wire. The expression is longer and carries no `sin` call.

`smoothstep` is deliberately left out:
it is a different shape (a 0→1 S-curve, not a 0→1→0 pulse) and no project in
the workspace has written one. If a project needs it later it is
`u * u * (3 - 2 * u)` over `clamp01(u)`, one line, and that is when it earns
a name.

Two helpers three projects copied are **deliberately not exported**:

- `at_least_zero(x)` is exactly `max(x, 0)`. Once `max` exists it is a second
  spelling of an existing name.
- `indicator(a, b)`, "1 when the integers `a` and `b` are equal", is
  `1 - clamp01(abs(a - b))` — but only for integers. For any other input it is
  a triangular hat, silently. The framework cannot check that precondition,
  symbolically least of all, so blessing the name would bless the trap. The
  documentation carries the one-liner instead, with its precondition stated,
  so a project writes it locally and honestly. **This is a judgement the pilot
  may reverse**: three projects wrote it, which is real repetition.

### D5b — `turn`'s default centre is the origin, and builds nothing

The ratified signature reads `turn(point, angle, about=(0.0, 0.0))`, and
taken literally that centres every turn by subtracting a bare `0.0` and
adding it back. Two costs, one of them found only by running it:

- **On the wire**, a turn about the origin becomes `(0.0 + ((x - 0.0) *
  cos(a)) - ((y - 0.0) * sin(a)))` where `((x * cos(a)) - (y * sin(a)))`
  says the same thing — four dead terms per component, on the commonest
  call there is.
- **In the algebra**, `point[0] - about[0]` is `Length - dimensionless`, so
  turning a point of declared quantities about the origin raises a dimension
  error for an operation that does nothing.

So the default is a module-private sentinel recognised by identity, and the
origin branch returns the rotation alone. The signature still reads as the
origin, an explicitly given centre still composes exactly as before, and an
explicit `(0.0, 0.0)` against a dimensioned point still raises — which is
right, because there the caller did ask for a centring, and stated it in the
wrong kind.

Identity, not `==`: comparing an `OpenSCADConstant` with `==` returns another
`OpenSCADConstant`, and `bool()` of one raises, so an equality test here
would break the symbolic face outright.

Layer 2 leaves out `projects/Inmoov-sim`'s tuple `_add` (one caller, and
`tuple(a + b for a, b in zip(p, q))` is the honest Python) and
`projects/kossel`'s `horizontal_offset` (delta-tower geometry, a mechanism
law, out of scope).

### D6 — Dimension rules, and the floor/ceil question the brief left open

`abs` preserves dimension; `min`/`max` require equality and preserve it (the
equality check `atan2` already has, with a different result rule); `sign`
accepts any dimension and returns dimensionless, because it compares against
zero and zero belongs to every dimension.

**`floor` and `ceil` require a dimensionless argument.** They compare a
quantity against the integers, and an integer bears no dimension; `floor(30
mm)` is meaningful only if millimetres are assumed, and assuming a unit is
precisely what ADR-062's algebra refuses to do ("dimensions only, never
units"). The originating use is dimensionless anyway —
`wall_clock_01`'s `floor(halves)` counts half swings. A caller who wants the
whole number of steps in a length writes `floor(length / step)`, which states
the unit it is counting in. This is the rule the brief asked to be decided and
stated.

The compositions' behaviour then follows without anyone writing it down as a
rule: `clamp` and `ramp` require their arguments equal, `clamp` preserving
and `ramp` returning dimensionless; `lerp` requires its endpoints equal and
its fraction dimensionless; `wrap` requires value and period equal,
preserving; `piecewise` requires the waypoint `x`s to match `x` and the
waypoint `y`s to match each other, returning the `y` dimension; `clamp01` and
`bump` require dimensionless and return dimensionless. Each of those is what
the composition's own body implies under the six rules above.

Only the first six of those rules are branches in `function_formula`: `abs`,
`floor`, `ceil`, `sign`, `min` and `max`, beside the existing `sqrt`, trig
and `atan2`. Everything from `clamp` down is a consequence of composition
(D5), and `function_formula` never hears those names.

Implementation note: `function_formula` currently dispatches on the function
name through an `elif` chain and raises `ValueError` for an unknown name. Six
branches are added; the alternative — a table of rule callables — is a
refactor of working code that this change does not need, and the chain stays
readable at this size. That the chain raises on an unknown name is also a
useful guard: if a composition ever reached it, it would fail loudly rather
than silently acquire a rule.

### D7 — Shadowing builtins is the intended usage

`from solid_node.math import floor, min, max, abs` shadows four builtins in
the importer's namespace. That is exactly what `from math import floor` does,
and what `sin` and `sqrt` already do for anyone importing this module beside
the standard library's. It is the point: a project's `kinematics.py` wants one
`min` that works on all three faces, not two spellings.

The module must not lose the builtins it needs itself. `import math as _math`
is already the established idiom there, so the builtins are bound privately at
module scope — `_abs = abs`, `_min = min`, `_max = max` — **before** the
shadowing definitions, and the numeric faces call those. Without it
`abs`'s numeric branch calls itself.

`__all__` grows to include the new names, which means `from solid_node.math
import *` shadows builtins wholesale. Star-importing this module is already
unwise; nothing here makes it wiser, and nothing here prevents it.

### D8 — A call mixing a symbolic value and a declaration raises

`_symbolic_call` renders each argument with `str()`. A `Formula`'s `__repr__`
is `<formula +: L>`, so `min(symbolic, declared_length)` today would embed
that text in the published expression string. The hazard exists for `atan2`
already; this change takes multi-argument functions from one to seven and
adds `piecewise`, whose waypoints are a whole table of operands, so it is
worth closing now.

The dispatch therefore checks for the mixture explicitly and raises naming
both operands. This is a behaviour change to `atan2` — from emitting garbage
to raising — and it is stated in the spec delta rather than slipped in.

*Alternative rejected:* resolve the formula. It cannot be resolved: a formula
evaluates against an instance's bound values, and there is no instance at the
moment an expression is being serialized symbolically.

**Why the guard cannot fire on a correct model.** A guard that raises is only
safe if no legitimate path can reach it, so this was checked in the code
rather than assumed:

- `AbstractBaseNode.__init__` calls `resolve_parameters(type(self), kwargs)`
  and stores the result under `self.__dict__['_parameters']`
  (`solid_node/node/base.py:456`), before `check()`, before `uniq_id`, and
  long before any render. `resolve_parameters`
  (`solid_node/node/declarative.py:260`) resolves each declared parameter
  through `Quantity.resolve` (`solid_node/parameters.py:468`), which coerces
  to `float`, `int` or `bool`, and then evaluates each derived formula
  against those numbers. Every value in `_parameters` is a plain Python
  number or boolean.
- `Declaration.__get__` (`solid_node/parameters.py`) returns
  `instance.__dict__['_parameters'][self._name]` for an instance read and
  raises `AttributeError` when it is not resolved; `__set__` refuses
  assignment. So `self.<parameter>` inside `render()` or `simulate()` is
  always that plain value — never a token, never a `Formula`. This is the
  behaviour the `declarative-nodes` baseline spec already requires ("Read on
  an instance, a declared parameter SHALL be a plain Python value ... never a
  token") and `docs/architecture.md` already states ("By the time any
  `render()` runs every parameter is a plain value").
- The runtime values that *are* symbolic are not `Expression`s at all.
  `DriverToken` (`solid_node/node/qualified.py:187`) subclasses
  `OpenSCADConstant`, deliberately, and `DriverDeclaration`
  (`solid_node/node/qualified.py:64`) is a plain class. Neither is in the
  `Expression` hierarchy, so a driver read can never be mistaken for a
  declaration.

Confirmed by running it: instantiating a declarative assembly and printing
inside `render()` gives `bore float 30.0` and derived `radius float 15.0`,
with `isinstance(..., Expression)` false for both, while the same names read
off the *class* are `Length` and `Formula`. A token therefore reaches a math
function only from a class body — where `$t` is not in scope, because
animation time is reached through `self.time` on an instance — or from code
deliberately reading a declaration off the class at runtime, which is not a
path any correct model takes.

The same run reproduces what the guard closes: `atan2(driver_token,
SomeClass.radius)` today returns the string `atan2(x.motor, <derived radius:
L>)`, a Python `repr` embedded in an expression the viewer would be asked to
parse. There is no model for which that is the right answer, so turning it
into an error cannot break a working model.

### D9 — The parity corpus gains a tree, it does not change the existing one

`tools/generate_parity_fixture.py` builds its expected values by serializing
`spike/expressions/machine_model.py` twice — once numerically bound, once
symbolic — and pairing the walks by structure. That discipline is the reason a
disagreement means the client drifted, and it is kept exactly.

**One inventory of emitted names.** The corpus requirement — that every
symbolic name the module can emit has a case behind it — needs a source of
truth, and a second hand-maintained list in the generator would be exactly
the kind of copy this whole change exists to remove: it would drift, and its
drift would silently weaken the guarantee. So `solid_node/math.py` gains a
module-level tuple, `SYMBOLIC_BUILTINS`, naming every OpenSCAD builtin
`_symbolic_call` may emit — the six new ones, the seven trig functions and
`sqrt`. The functions take their emitted name from it rather than spelling
it a second time, the generator's coverage check reads it, and the
framework's own test reads it. Adding a function without adding its name to
the tuple leaves the function unable to emit; adding the name without a
corpus case fails the regeneration. Neither mistake is silent.

The new functions get a **second tree**, not new operations on the existing
one. Editing `machine_model.py` would change the keys and expected values of
the 266 cases already pinned, making a regeneration impossible to review; the
spike is also explicitly non-shipping. The new corpus is a small assembly
under `tests/expression_project/`, in the shipping test tree, whose
`simulate()` puts one operation per new symbolic function on the wire under a
driver and `$t`. The generator walks it the same way and appends its cases
under distinct keys, so every existing case survives byte-identical.

Putting the corpus in `tests/` rather than `spike/` also lets the framework's
own suite use the same tree, which is how the numeric/symbolic agreement test
gets its expressions without a second hand-written list.

**Repository boundary.** The regenerated `parity-fixture.json` is written into
`solid-node-viewer`, which is a separate AGPL repository. This cycle
regenerates it and runs the viewer's vitest **as evidence**; committing the
fixture there is a separate change in that repository under the pilot's
decision. The viewer's `evaluator.ts` is not touched: every name emitted here
is already in its scope, verified above. If implementation finds a name the
evaluator cannot answer, that is a stop condition to report, not a viewer edit
to make.

### D10 — ADR-022 gets a revision note, not a new ADR

The decision ADR-022 records — one expression semantics, OpenSCAD's degree
conventions, `^` as power, enforced by a producer-valued parity corpus — is
unchanged. What changed is the size of the vocabulary it governs and the fact
that the corpus now has a rule about covering all of it. That is a revision to
an accepted ADR, in the same style as its 2026-08-26 revision, plus an update
to the "Expression math" section of `docs/architecture.md`. Per the shop's
framework-change discipline, both are written after implementation confirms
the design, in commit 2.

The `kinematics` baseline spec's stale note — that the export widget diverges
and that parity has no automated enforcement — is corrected in the same delta,
because the requirement is being rewritten anyway and shipping a rewrite that
preserves a known-false statement would be worse than either alternative.

## Risks / Trade-offs

- **A composition emits something a runtime spells differently** → every new
  symbolic function enters the parity corpus, and the corpus requirement makes
  a missing case a spec violation rather than an oversight. The direct
  builtins were verified name by name against `evaluator.ts` and OpenSCAD's
  builtin list before being chosen.
- **`piecewise` expressions get long** → accepted and documented. The
  alternative (a `min`/`max` chain, or an emitted OpenSCAD `let`) is longer or
  unsupported by the evaluator's grammar. A nine-waypoint path is eight clamp
  terms, which the browser parses once and caches.
- **Shadowing builtins confuses a reader** → mitigated by precedent (`sin`,
  `sqrt`) and by documentation. Not mitigated for `import *`, which stays
  unwise.
- **`sign` and `ceil` ship without an originating caller** → stated openly in
  D2 so the pilot can drop either; neither carries any risk beyond an unused
  export.
- **`indicator` stays out and three projects keep their copy** → the copies
  are three lines and now rest on `clamp01` instead of `sqrt`, so they get
  shorter and more honest even without the name. Reversible in one line if the
  pilot disagrees.
- **The two-repository fixture split** → the framework cycle can go green with
  a fixture the viewer has not committed, leaving the two briefly out of step.
  Mitigated by reporting the regenerated fixture's diff and vitest result as
  evidence, and by the fact that the viewer's committed fixture only ever gets
  weaker (fewer pinned cases), never wrong.

## Migration Plan

None required. Nothing is removed or renamed, every existing signature is
unchanged, and every expression the framework emits today serializes to the
same string. The only behaviour change to an existing function is D8's guard,
which turns a call that produced a corrupt expression string into a call that
raises.

## Open Questions

1. **`indicator`** — three projects wrote it; the design leaves it out because
   it is correct only for integers. The pilot may prefer the name with a
   documented precondition.
2. **`sign`** — included with no originating caller (D2). Drop or keep.
3. **`lerp`** — included on inlined evidence rather than a named copy. Drop or
   keep.
4. **The `%` sign divergence** (D4) is a live latent defect reported, not
   fixed. Whether it becomes its own cycle is the pilot's call.
