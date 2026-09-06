# ADR-022: Cross-Runtime Degree-Trig Parity for `$t` Expression Evaluation

**Status:** Accepted, revised 2026-09-06 (vocabulary widened, corpus covers it)
**Date:** 2026-07-17
**Revised:** 2026-08-26 — see *Revision (2026-08-26)* below
**Revised:** 2026-09-06 — see *Revision (2026-09-06)* below
**Depends on:**
- [ADR-008: Time-Based Animation System for Assemblies](../NODE/ADR-008-time-based-animation-system-for-assemblies.md)

**Related to:**
- [ADR-014: Recursive NodeAPI REST Pattern Mirroring Node Tree](../VIEWER-WEB/ADR-014-recursive-nodeapi-rest-pattern.md)
- [ADR-020: Static Export Channel with Embeddable, React-Free Viewer Widget](../EXPORT/ADR-020-static-export-and-embeddable-viewer-widget.md)
- [ADR-056: Signals, Drivers, Ports, and Stepped Simulation](../NODE/ADR-056-signals-drivers-ports-and-stepped-simulation.md)

## Context and Problem Statement

`AssemblyNode.time` (ADR-008) lets assemblies express motion as functions of a normalized animation time `$t`. Linear expressions in time (e.g. `720.0 * self.time`) survive symbolically through solid2's own operator overloads, but **genuinely non-linear kinematics** -- anything wrapping `$t` in a trig or root function, e.g. `asin(0.25 * sin(720 * $t))`, or a slider-crank piston height `r*cos(720t) + sqrt(l^2 - (r*sin(720t))^2)` -- cannot. `solid_node/math.py` exists to handle exactly these: it is a **dual-mode** module. Under `set_keyframe()` (tests and keyframe renders) `time` is a plain float and the functions compute numerically; in the viewer/build path `time` is solid2's `$t` (an `OpenSCADConstant`), and the same functions instead emit a new `OpenSCADConstant` that builds an equivalent OpenSCAD call string, deferred for later evaluation.

Crucially, `math.py` computes trig **in degrees** (`sin(90) == 1.0`, `asin(0.5) == 30.0`, `atan2` returns degrees). This is not a stylistic choice: **OpenSCAD's trig builtins are degree-in / degree-out**, so the numeric Python path and the symbolic OpenSCAD string must be the *same function* -- one evaluated now, one deferred.

The problem is that this "evaluate a `$t` expression" semantics is now reimplemented in **four independent runtimes that must agree function-for-function**, and there is **no mechanism that enforces their agreement**. When any copy drifts, an animation renders differently depending on where it is viewed.

### The four-runtime reality (as of 2026-07-17)

> **Superseded by the 2026-08-26 revision.** Runtime #3 no longer
> exists and runtime #4's divergence is fixed. Kept because the
> decision below was taken against this state.

1. **`solid_node/math.py`** (Python) -- dual-mode numeric (degrees, stdlib) and symbolic (emits degree-convention OpenSCAD call strings). The source of truth for the intended semantics.
2. **OpenSCAD** -- evaluates the symbolic strings `math.py` emits. Degree-in/degree-out trig; the reason `math.py`'s numeric path uses degrees.
3. **`viewers/web/app/src/evaluator.ts`** (dev/live viewer) -- evaluates operation expressions in-browser with jokenizer. It deliberately overrides trig to degrees (`sin: d => Math.sin(d*PI/180)`, `asin: x => Math.asin(x)*180/PI`, etc.) to match `math.py`, and runs a `powify` pass rewriting `^` into `pow()` because jokenizer parses `^` as JavaScript bitwise XOR. It carries a golden test (`evaluator.test.ts`) that pins its output to `math.py`'s numeric-mode values for composed non-linear expressions, and a comment instructing implementers that it "must match [math.py] function-for-function."
4. **`viewers/widget/src/evaluator.ts`** (the ADR-020 static export widget) -- the same job, but it only copies raw `Math` plus `ln`/`log`/`mod`. It does **not** override trig to degrees, and has **no** `powify` pass and **no** parity test.

The dev viewer (#3) enforces its parity with `math.py` locally via `evaluator.test.ts`, but that test lives beside #3 only. Nothing checks #4 against #1/#2/#3, so #4 drifted (see Known Issues).

## Decision Drivers

- **Degree conventions must match OpenSCAD.** OpenSCAD trig is degree-in/degree-out; every runtime evaluating `$t` expressions must use the same convention or non-linear animations diverge.
- **Dual-mode numeric/symbolic in Python.** `math.py` must both compute at keyframes (tests) and defer as OpenSCAD strings (builds/exports) -- and the two modes must be the same function.
- **The browser must match Python and OpenSCAD.** Both JS evaluators consume expressions ultimately produced by `math.py`'s symbolic mode; they must reproduce its numeric results exactly at every `$t`.
- **`^` is exponentiation, not XOR.** OpenSCAD (and solid2's `__pow__`) emit `^` for power; jokenizer's default `^` is JS bitwise XOR, so every JS evaluator must rewrite it.
- **Multiple copies with no shared source.** Two TS evaluators plus a Python module plus OpenSCAD, hand-kept in sync, with zero automated cross-runtime enforcement today.

## Considered Options (parity-enforcement strategies -- NONE implemented today)

> Current state has **zero cross-runtime enforcement**. The following are candidate mechanisms to *establish* the parity this ADR records as required; they are documented as future direction, not existing safeguards.

1. **Cross-runtime golden parity corpus.** A single, version-controlled list of `$t` expressions plus expected values, executed in CI against: `math.py` numeric mode, OpenSCAD (evaluating the symbolic strings), the dev-viewer evaluator, and the widget evaluator. Any drift fails the build.
2. **Single shared TS evaluator module.** Collapse the two TypeScript evaluators (#3 dev viewer, #4 widget) into one module both import, so browser-vs-browser drift becomes structurally impossible.
3. **Code-generated function table from one declarative spec.** Define the degree-trig / `^` / `ln`/`mod` semantics once in a neutral spec and generate both the JS override table and (ideally) the Python functions from it, making agreement true by construction.

## Decision Outcome

**Recorded decision (the architecture that already exists):** there is exactly one `$t` math semantics -- OpenSCAD's degree conventions -- and every runtime that evaluates a `$t` expression must reproduce it identically. `solid_node/math.py` is the dual-mode source of truth (numeric for keyframes/tests, symbolic OpenSCAD strings for builds/exports); OpenSCAD evaluates the symbolic strings; each JS evaluator must mirror `math.py` function-for-function, including degree-convention trig and `^`-as-power.

**Recommended enforcement (target state, NOT yet implemented):** adopt Option 2 **and** Option 1 together -- collapse the two TypeScript evaluators into a single shared module (removing the browser-vs-browser duplication that is the direct cause of the current bug), and back it with a cross-runtime golden parity corpus (the only mechanism that can also guard the Python<->OpenSCAD<->browser boundaries, which no shared code can span). Option 3 is noted as a heavier, longer-term way to make parity true by construction.

Ranking, if a single mechanism must be chosen first:

1. **Golden parity corpus (Option 1) -- best first step.** It is the only option that spans **all four** runtimes, including OpenSCAD and Python, which cannot share code with the browser. It would have caught the widget divergence the moment it shipped. It enforces behavior without restructuring code, so it is adoptable immediately.
2. **Single shared TS evaluator (Option 2) -- best structural fix.** It eliminates the #3/#4 duplication that produced *this specific* bug, but does nothing for the Python/OpenSCAD boundary; it needs the corpus to be complete.
3. **Code-generated table (Option 3) -- strongest guarantee, highest cost.** Generation-by-construction is the most robust but the most build machinery; premature until the corpus exists to validate the generator.

**This ADR does not implement any of these.** It records the required parity and the currently-unenforced reality so that the divergence below is understood rather than rediscovered.

## Known Issues / Consequences

### KNOWN DEFECT (shipped): the export widget evaluator diverges from `math.py` — **FIXED**

> **Fixed and no longer shipped.** The degree overrides and the `powify`
> rewrite are in `viewers/widget/src/evaluator.ts`, and since
> 2026-08-26 a parity fixture holds them there. The characterization
> below is history; see *Revision (2026-08-26)*.

`viewers/widget/src/evaluator.ts` -- the evaluator inside the ADR-020 static export widget -- diverges from the source-of-truth semantics on two counts, and this divergence is **shipped in every export**:

1. **Trig runs in RADIANS, not degrees.** The widget copies raw `Math.*` into its evaluation context without the degree overrides that `math.py` (#1) and the dev evaluator (#3) apply. Any exported animation using non-linear trig of `$t` -- precisely what `math.py` exists to produce, e.g. `asin((0.25 * sin((720.0 * $t))))` -- renders **wrong** in the widget, while the dev viewer, the Python tests, and OpenSCAD all agree with each other.
2. **`^` is evaluated as JS bitwise XOR, not exponentiation.** The widget has no `powify` pass, so any `^` in an animated expression (e.g. the slider-crank piston height `... (r*sin(720t)) ^ 2 ...`) is computed as XOR and is wrong.

Observable symptom: a model that animates correctly in `solid <path> develop`, in `pytest`, and in OpenSCAD will animate incorrectly once published through `solid export` and viewed in the embeddable widget -- for the exact class of non-linear kinematics `math.py` was built to support. Linear-in-`$t` expressions (the common case) are unaffected because they involve no trig or `^`.

Root cause: **there is no enforcement of cross-runtime parity.** The dev evaluator carries a golden parity test and an explicit comment that it must match `math.py` "function-for-function," but that guard is local to the dev viewer; nothing constrains the widget copy, so it drifted.

**The fix is intentionally out of scope for this ADR.** This is characterization: the defect is recorded here so that a separate effort (including agents that may encounter it empirically) can identify it against a written description of the intended architecture. Remediation (degree overrides + `powify` in the widget, or better, one of the enforcement options above) belongs to a later, separate change.

### Other consequences

- The dual-mode design in `math.py` is elegant and correct, but its correctness depends on every downstream evaluator honoring the same conventions -- a contract currently held together by discipline and comments, not tests.
- Adding a new expression builtin (or a new evaluator, e.g. for a future export target) multiplies the surfaces that must agree; without enforcement, each addition is a new drift opportunity.
- ADR-020's static export channel inherits this risk directly: the export widget is the runtime furthest from the `math.py` source of truth and the one with no parity test.

## Revision (2026-08-26): one evaluator, defect fixed, parity enforced

Three things this ADR recorded as open have changed. The **decision**
is unchanged -- one `$t` semantics, OpenSCAD's degree conventions, with
`^` as power -- and it now also covers driver expressions.

**1. There is one TypeScript evaluator, not two.** Runtime #3,
`viewers/web/app/src/evaluator.ts`, is gone; the development app mounts
the same shared viewer package the export does. Option 2 (a single
shared TS module) is therefore satisfied structurally, not by a merge
but by the duplicate's removal, and browser-vs-browser drift has no
place left to happen.

**2. The recorded defect is fixed.** `viewers/widget/src/evaluator.ts`
carries the degree-trig overrides and the `powify` rewrite. Non-linear
animated exports render the same in the widget as in `pytest`, the
development viewer, and OpenSCAD.

**3. Parity is enforced by a test, which is what this ADR asked for.**
Option 1 (the golden parity corpus) is implemented as
`viewers/widget/src/parity-fixture.test.ts` over the committed fixture
`viewers/widget/src/parity-fixture.json`, regenerated by
`viewers/widget/tools/generate_parity_fixture.py`. Its discipline is
the one this ADR states: identical semantics, float rounding only.

- The expected values are **producer values**, not a second
  implementation: the generator serializes one tree twice -- once bound
  to a numeric snapshot, so every operation holds the number Python
  computed through `math.py` and solid2, and once in symbolic mode, so
  every operation holds the wire expression -- and pairs them by
  structure. A disagreement therefore means the client drifted.
- The corpus is the ADR-056 expression spike's two-axis machine
  (`spike/expressions/machine_model.py`) over its seven snapshots: 182
  expression cases covering linear driver terms, a driver through a
  port scale, a degree-trig chain, `^` terms, and one formula mixing
  `$t` with a driver. Measured agreement is within 1e-9 (the spike
  measured 2.5e-14 over the same corpus).
- The `^` rewrite is proved load-bearing rather than assumed: with
  `powify` disabled, 14 cases fail by up to 0.186.
- The fixture also pins **design-to-native conversion**
  (`Driver.native`), including Python's round-half-to-even on integer
  dtypes, because an instruction's target crosses the same
  Python/browser boundary as an expression does.

**Scope extension.** The same semantics now govern **driver
expressions**, not just `$t`: a qualified driver id (`x_axis.motor`)
evaluates through a nested driver map, and every rule above -- degree
trig, `^` as power, one semantics across runtimes -- applies unchanged
to expressions naming drivers (ADR-056 stage 3b).

**What remains true.** OpenSCAD and Python still cannot share code with
the browser, so the corpus, not a shared module, is what spans them.
The OpenSCAD boundary itself is exercised by the spike's rendered
snapshots rather than by this fixture; a `.scad` document substitutes
bound driver values numerically and keeps `$t` symbolic, so it
evaluates the same functions on the same conventions. Option 3
(code-generated function tables) stays unadopted and unneeded.

## Revision (2026-09-06): the vocabulary grew, and the corpus covers all of it

The **decision is unchanged** -- one `$t` and driver expression
semantics, OpenSCAD's degree conventions, `^` as power, enforced by a
producer-valued parity corpus. What changed is how much vocabulary that
decision governs, and one new rule about the corpus.

**1. `solid_node.math` is no longer only trigonometry.** It now also
emits six direct OpenSCAD builtins -- `abs`, `floor`, `ceil`, `sign`,
`min` and `max` -- and composes over them `clamp`, `clamp01`, `ramp`,
`lerp`, `wrap`, `piecewise` and `bump`, plus the vector helpers `polar`,
`turn`, `rotate_x`, `rotate_y` and `rotate_z`. Only the emitted
primitives are new *semantics*; the compositions put nothing on the wire
that a primitive did not already put there.

The empirical case was that four projects
(`abacus`, `fender-bender`, `pascaline`, `snappy-reprap`) had each built
a clamp kit out of `sqrt(x * x)` on the belief that the browser's
expression language had no `min`, `max` or `floor`, and four clock
models under `3DPrintedClocks` imported solid2's private
`OpenSCADConstant` to emit `floor` themselves. **The belief was false**:
the evaluator copies every own property of JavaScript's `Math` into its
scope, so those names were always there, and OpenSCAD has the same
builtins. That the belief survived in four projects at once is itself
an argument for this ADR's discipline: the shared semantics were
documented, and their *extent* was not.

**2. Two names were refused on parity grounds**, which is this ADR's
criterion doing its job before code exists rather than after:

- **`round`.** OpenSCAD rounds a half away from zero, JavaScript's
  `Math.round` toward +infinity, Python to even. Three runtimes, three
  answers, on a value a timeline lands on constantly. `floor(x + 0.5)`
  is the half-up all three agree on.
- **`mod`.** OpenSCAD has no `mod()` function -- it spells the
  operation as the `%` operator -- while the viewer's evaluator does
  define `mod`, so emitting it would evaluate in the browser and fail to
  parse as OpenSCAD. `wrap` is built on `ceil` instead.

A latent hazard is recorded but not fixed: solid2's
`OpenSCADConstant.__mod__` emits `%`, which OpenSCAD and JavaScript
evaluate C-style (sign of the dividend) where Python's `%` takes the
sign of the divisor. Nothing in the framework or the corpus catches a
model that writes `a % b` on a symbolic value.

**3. The corpus must now cover every emitted name.** Enforcement is only
as wide as the corpus behind it, so a symbolic function added without a
case is a name no runtime is checked on. `solid_node/math.py` therefore
carries `SYMBOLIC_BUILTINS`, the single inventory of every builtin
`_symbolic_call` may emit; `_symbolic_call` refuses a name absent from
it, `tools/generate_parity_fixture.py` refuses to regenerate while one is
uncovered, and `tests/test_expression_corpus.py` says the same in the
framework's own suite. No consumer keeps a second list.

**4. The corpus is two trees, not one.** The spike's two-axis machine is
untouched -- editing it would change the key and expected value of every
case already pinned, and a regeneration nobody can review is one nobody
checks. The new vocabulary gets `tests/expression_project/vocabulary.py`,
whose operations are appended under their own key prefix. The fixture
went from 266 to 421 cases with **zero** existing cases changed or
removed; the widest deviation over the 155 new ones is 1.42e-14, the same
order as the 2.49e-14 the spike measured. One snapshot binds the driver
NEGATIVE on purpose: below zero is the only place `floor`, `ceil`,
`sign`, `min` and `max` could disagree between runtimes.

**5. No evaluator change was needed**, and that was verified against
`evaluator.ts` rather than assumed before the vocabulary was chosen. The
regenerated fixture is committed in the solid-node-viewer repository,
which is where it lives since ADR-068; a framework change that widens the
vocabulary is therefore two changes in two repositories, and this one
produced the numbers while the viewer commits them.

**What remains true.** OpenSCAD and Python still cannot share code with
the browser, so the corpus, not a shared module, is what spans them.
Option 3 (code-generated function tables) stays unadopted and unneeded.

## References

- `solid_node/math.py` -- the expression vocabulary and `SYMBOLIC_BUILTINS`, source of truth
- `solid_node/parameters.py` -- `function_formula`, the dimension rule of each emitted primitive
- `tools/generate_parity_fixture.py` -- regenerates the committed fixture from both corpora, and refuses while a builtin is uncovered
- `spike/expressions/machine_model.py`, `tests/expression_project/vocabulary.py` -- the two corpora
- `tests/test_math.py`, `tests/test_declarative_algebra.py`, `tests/test_expression_corpus.py` -- the three faces and the coverage rule
- `spike/expressions/FINDINGS.md` -- the parity measurement and its seam 7, now closed
- In the solid-node-viewer repository (relocated by ADR-068): `solid_node_viewer/widget/src/evaluator.ts`, the one TypeScript evaluator, and `solid_node_viewer/widget/src/parity-fixture.test.ts` with `parity-fixture.json`, the enforcement
- Commits: `2975e51` (add `solid_node.math`, #19), `2019d30` (Math builtins in context, `^` as power)
