## Why

Thirteen mechanical projects in this workspace carry a `kinematics.py`, and
every one of them opens by rebuilding arithmetic the framework does not
export. `solid_node.math` offers `sin`, `cos`, `tan`, `asin`, `acos`, `atan`,
`atan2` and `sqrt` and nothing else, so a project that needs a clamp, a
floor, a smaller-of-two or an angle folded into one turn has to invent one.

Two inventions recur, and both are worse than the framework's own name would
be:

* **The `sqrt` trick.** `projects/abacus/abacus/kinematics.py`,
  `projects/fender-bender/simulation/kinematics.py`,
  `projects/pascaline/pascaline/kinematics.py` and
  `projects/snappy-reprap/simulation/cable_chain.py` each define
  `absolute(x) = sqrt(x * x)` and build `clamp01`, `at_least_zero`,
  `indicator`, `piecewise`, `bump`, `ramp`, `wrap`, `smooth_min` and
  `smooth_max` over it — four verbatim copies of the same lines. Their
  docstrings state the reason: *"the viewer's expression language has
  arithmetic and the functions in `solid_node.math` and nothing else: no
  `min`, `max`, `floor` or `mod`."*

  **That reason is false.** The viewer's evaluator copies every own property
  of JavaScript's `Math` into its evaluation scope
  (`solid-node-viewer/solid_node_viewer/widget/src/evaluator.ts`), so `abs`,
  `floor`, `ceil`, `min`, `max`, `sign` and `pow` are all already there, and
  OpenSCAD has the same builtins. Four projects carry a workaround for a
  limitation that does not exist, paying for it in longer expressions and in
  `sqrt(x*x)`'s loss of precision near zero.

* **The private-API escape.** `projects/3DPrintedClocks/design/wall_clock_01`,
  `wall_clock_02`, `mantel_clock_34_steampunk` and
  `wall_clock_53_grasshopper` each import `solid2.core.object_base
  .OpenSCADConstant` directly and hand-roll `_symbolic` / `_call` helpers to
  emit `floor`, `min` and `max` calls, plus a `clamp` over them. Four models
  depend on a private detail of a third-party package to reach builtins every
  runtime already evaluates — precisely the dependency `solid_node.math`
  exists to absorb.

A third, smaller repetition is vector arithmetic: `polar` in
`projects/openflexure-microscope/simulation/microscope/geometry.py`, `_turn`
in `wall_clock_53_grasshopper/kinematics.py`, `rotate_x` in
`projects/Inmoov-sim/Inmoov_sim/kinematics.py`, each written in that project's
own frame convention — and the first two written against Python's stdlib, so
they are numeric-only and break the moment a symbolic driver reaches them.

## What Changes

`solid_node.math` grows two layers. Every new name keeps the module's
existing three faces: numeric through the standard library, symbolic as an
OpenSCAD builtin call over `OpenSCADConstant` arguments, and declarative as a
`Formula` carrying a dimension rule in `function_formula`.

**Layer 1 — direct builtins.** `abs`, `floor`, `ceil`, `min`, `max` and
`sign`, each emitting the identically-named OpenSCAD builtin, which the
viewer's evaluator answers from JavaScript's `Math`. `min` and `max` take
exactly two arguments.

**Layer 1 — compositions over those primitives.** `clamp(x, low, high)`,
`clamp01(x)`, `ramp(x, start, end)`, `lerp(a, b, u)`, `wrap(angle,
period=360.0)` folding a value into `(-period/2, period/2]`,
`piecewise(x, points)` interpolating linearly through `(x, y)` waypoints and
clamped at the ends, and `bump(u)`, a smooth 0–1–0 pulse. Each is built only
from expressions all three runtimes evaluate identically.

**Layer 2 — vector helpers**, composition only, over the layer-1 functions
so a symbolic or declared component rides through: `polar(radius, angle)`,
`turn(point, angle, about=(0.0, 0.0))` for a 2D point about a centre, and
`rotate_x`, `rotate_y`, `rotate_z` for a 3D point about an axis. All degrees,
all returning plain tuples.

**A mixed-face guard.** Passing a symbolic value and a declared formula to the
same function currently renders the formula's `repr()` into the expression
string — verified: `atan2(driver_token, SomeClass.radius)` returns
`atan2(x.motor, <derived radius: L>)` today. Multiplying multi-argument
functions from one (`atan2`) to seven makes that hazard worth closing: such a
call now raises, naming both operands. No correct model can reach it, because
a declared parameter read through `self` is a plain number by the time any
render runs (design D8 records the code path).

**One definition per composition.** Only the six direct builtins carry a
dimension rule of their own. `clamp`, `clamp01`, `ramp`, `lerp`, `wrap`,
`piecewise` and `bump` get none: each has exactly one definition, so its
declared face is the same function as its numeric and symbolic ones and its
dimension behaviour follows from the primitives it composes. One consequence
worth stating: `clamp01(length)` and `max(length, 0.0)` raise, because a
plain number is dimensionless — the same refusal `length + 1` already gives.

**Parity.** Every new symbolic function enters the ADR-022 parity corpus, so
the viewer's fixture pins it against producer-computed values, and
`solid_node.math` names the builtins it may emit in one place
(`SYMBOLIC_BUILTINS`) so the corpus check needs no second list.

Deliberately **not** included, each with its reason recorded in `design.md`:
`round` (the three runtimes round halves three different ways), `mod` (OpenSCAD
has the `%` operator but no `mod()` function, and Python's `%` disagrees with
OpenSCAD's and JavaScript's on negative operands), `at_least_zero` (it is
`max(x, 0)`), `indicator` (correct only for integers, a precondition the
framework cannot check), `smoothstep`, tuple add/subtract, and every
mechanism law (gear mesh, slider-crank, lead screw, delta kinematics, circle
intersection, timeline slicing) — the pilot is planning those separately.

No existing behaviour changes. Nothing is removed, no signature moves, and
every current expression serializes to the same string.

## Capabilities

### New Capabilities

None. The expression-math contract already lives in `kinematics`, and the
dimension rules already live in `declarative-nodes`.

### Modified Capabilities

- `kinematics`: the "Degree-convention dual-mode math" requirement grows the
  vocabulary the one expression semantics covers, states that a composition
  may emit only expressions every runtime evaluates identically, and gains
  the mixed symbolic/declared guard. A new requirement covers the layer-2
  vector helpers. The requirement's stale note — that the export widget
  diverges and that parity has no automated enforcement — is corrected: ADR-022's
  2026-08-26 revision fixed the defect and `parity-fixture.test.ts` enforces
  parity today.
- `declarative-nodes`: the typed-parameter algebra's paragraph on
  `solid_node.math` grows the dimension rule for each new function.

## Impact

- `solid_node/math.py` — the new functions and the mixed-face guard.
- `solid_node/parameters.py` — `function_formula` gains a dimension rule for
  the six direct builtins only; the compositions get none, reaching the
  declared face by composition alone.
- `tools/generate_parity_fixture.py` — a second corpus, appended to the
  existing cases so the spike's 266 cases keep their keys and values.
- `tests/expression_project/` — the new corpus: a small node whose
  `simulate()` puts one operation per new function on the wire, used by both
  the generator and the framework's own tests.
- `tests/test_math.py`, `tests/test_declarative_algebra.py` — red-first
  coverage, including a test pinning the exact OpenSCAD string each new
  symbolic function emits.
- `docs/api-reference.rst` (which has no expression-math section today),
  `docs/animation.rst`, `docs/declaring.rst`, `docs/changelog.rst`.
- `docs/adrs/MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md`
  and `docs/architecture.md` — a revision note recording that the symbolic
  vocabulary grew, written after implementation.
- **`solid-node-viewer` is not modified by this change.** Its evaluator
  already answers every name emitted here; that was verified against
  `evaluator.ts`, not assumed. The regenerated `parity-fixture.json` lives in
  that repository, and committing it there is a separate change under the
  pilot's decision. This cycle regenerates the fixture and runs the viewer's
  vitest as evidence only.
- Callers: `projects/abacus` and `projects/fender-bender` are the
  representative callers this cycle validates against, in their own
  repositories, as evidence only — no project commit belongs to this change.
