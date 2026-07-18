# ADR-022: Cross-Runtime Degree-Trig Parity for `$t` Expression Evaluation

**Status:** Accepted
**Date:** 2026-07-17
**Depends on:**
- [ADR-008: Time-Based Animation System for Assemblies](../NODE/ADR-008-time-based-animation-system-for-assemblies.md)

**Related to:**
- [ADR-014: Recursive NodeAPI REST Pattern Mirroring Node Tree](../VIEWER-WEB/ADR-014-recursive-nodeapi-rest-pattern.md)
- [ADR-020: Static Export Channel with Embeddable, React-Free Viewer Widget](../EXPORT/ADR-020-static-export-and-embeddable-viewer-widget.md)

## Context and Problem Statement

`AssemblyNode.time` (ADR-008) lets assemblies express motion as functions of a normalized animation time `$t`. Linear expressions in time (e.g. `720.0 * self.time`) survive symbolically through solid2's own operator overloads, but **genuinely non-linear kinematics** -- anything wrapping `$t` in a trig or root function, e.g. `asin(0.25 * sin(720 * $t))`, or a slider-crank piston height `r*cos(720t) + sqrt(l^2 - (r*sin(720t))^2)` -- cannot. `solid_node/math.py` exists to handle exactly these: it is a **dual-mode** module. Under `set_keyframe()` (tests and keyframe renders) `time` is a plain float and the functions compute numerically; in the viewer/build path `time` is solid2's `$t` (an `OpenSCADConstant`), and the same functions instead emit a new `OpenSCADConstant` that builds an equivalent OpenSCAD call string, deferred for later evaluation.

Crucially, `math.py` computes trig **in degrees** (`sin(90) == 1.0`, `asin(0.5) == 30.0`, `atan2` returns degrees). This is not a stylistic choice: **OpenSCAD's trig builtins are degree-in / degree-out**, so the numeric Python path and the symbolic OpenSCAD string must be the *same function* -- one evaluated now, one deferred.

The problem is that this "evaluate a `$t` expression" semantics is now reimplemented in **four independent runtimes that must agree function-for-function**, and there is **no mechanism that enforces their agreement**. When any copy drifts, an animation renders differently depending on where it is viewed.

### The four-runtime reality

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

### KNOWN DEFECT (shipped): the export widget evaluator diverges from `math.py`

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

## References

- `solid_node/math.py` -- dual-mode degree trig (numeric + symbolic OpenSCADConstant), source of truth
- `solid_node/viewers/web/app/src/evaluator.ts` -- dev viewer: degree overrides (lines ~79-85) and `powify` (~40-53)
- `solid_node/viewers/web/app/src/evaluator.test.ts` -- golden parity cases pinning the dev evaluator to `math.py` numeric mode (composed non-linear and slider-crank expressions)
- `solid_node/viewers/widget/src/evaluator.ts` -- export widget evaluator: raw `Math` + `ln`/`log`/`mod`, **no** degree overrides, **no** `powify` (the divergence)
- `tests/test_math.py` -- `math.py` numeric/symbolic tests referenced by the JS golden corpus
- Commits: `2975e51` (add `solid_node.math`, #19), `2019d30` (Math builtins in context, `^` as power)
