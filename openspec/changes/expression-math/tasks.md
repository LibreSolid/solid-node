## 1. Red first: the failing tests

- [ ] 1.1 In `tests/test_math.py`, add a symbolic-string test asserting the
  exact OpenSCAD call each new symbolic function emits — `abs($t)`,
  `floor($t)`, `ceil($t)`, `sign($t)`, `min($t, 1.0)`, `max($t, 1.0)` — and
  that the compositions emit only those names, `sqrt`, the degree trig and
  arithmetic. Prove it red.
- [ ] 1.2 Add numeric-face tests for the six direct builtins over positive,
  negative, zero and exact-half inputs, pinning `floor(-2.5) == -3`,
  `ceil(-2.5) == -2` and `sign(0) == 0`.
- [ ] 1.3 Add tests for each composition's stated behaviour: `clamp`,
  `clamp01`, `ramp` (including the equal-endpoints refusal), `lerp`,
  `wrap` at `180`, `181`, `-180`, `-181` and `540` and over a non-360
  period, pinning both edges of the half-open interval (`wrap(181) == -179`),
  `piecewise` at, between and outside its waypoints plus its two refusals
  (fewer than two waypoints, non-increasing `x`), and `bump` at
  `-1, 0, 0.25, 0.5, 1, 2`, pinning `bump(0.25) == 0.5625` so the polynomial's
  shape is held and not only its endpoints and peak.
- [ ] 1.4 Extend the existing `_eval_openscad_expr` helper in
  `tests/test_math.py` with the six new builtin names and add a
  numeric/symbolic agreement test over an expression composed from the new
  vocabulary, sampled across `$t`.
- [ ] 1.5 Add a test that `min` (and one composition) called with a symbolic
  value and a declared parameter token raises, naming both operands, rather
  than embedding a `repr()` in the expression string.
- [ ] 1.6 Add layer-2 tests: `polar`, `turn` with and without a centre, and
  `rotate_x`/`rotate_y`/`rotate_z`, each numerically at known angles and each
  with a symbolic angle, asserting no raise and a well-formed expression per
  component.
- [ ] 1.7 In `tests/test_declarative_algebra.py`, add the dimension-rule
  tests: `abs` preserving, `min`/`max` requiring equality and preserving,
  `floor`/`ceil` refusing a dimensioned argument and accepting a ratio of two,
  `sign` accepting any dimension and returning dimensionless, `clamp`/`ramp`/
  `lerp`/`wrap`/`piecewise` behaving as the delta spec's consequences say
  while having no branch of their own, `clamp01(bore)` and `max(bore, 0.0)`
  raising from `min`/`max` over a declared `Length`, and `polar` over a
  declared `Length` and `Angle` yielding two length formulas while
  `polar(radius, radius)` raises.

## 2. Layer 1: the scalar functions

- [ ] 2.1 In `solid_node/math.py`, bind the shadowed builtins privately at
  module scope (`_abs`, `_min`, `_max`) before any definition that shadows
  them, and extend the module docstring to say what the module now covers and
  why the names shadow builtins deliberately.
- [ ] 2.2 Add the mixed-face guard to the dispatch: a call carrying both an
  `OpenSCADConstant` and an `Expression` raises naming both operands.
- [ ] 2.3 Implement `abs`, `floor`, `ceil`, `sign`, `min` and `max` with the
  module's three-face dispatch, `min` and `max` taking exactly two arguments.
- [ ] 2.4 Implement `clamp`, `clamp01`, `ramp` and `lerp` as compositions.
- [ ] 2.5 Implement `wrap(value, period=360.0)` as
  `value - period * ceil((value - period / 2) / period)`, validating a
  positive numeric period.
- [ ] 2.6 Implement `piecewise(x, points)` as the sum of clamped ramps, with
  call-time validation of the waypoint sequence.
- [ ] 2.7 Implement `bump(u)` as `p = clamp01(u); 16 * p * p * (1 - p) *
  (1 - p)` — a polynomial, not the trigonometric form, so the function has a
  declared face at all (design D5).
- [ ] 2.8 Add the module-level `SYMBOLIC_BUILTINS` tuple naming every OpenSCAD
  builtin `_symbolic_call` may emit — the six new ones, the seven trig
  functions and `sqrt` — and have every function take its emitted name from
  it rather than spelling the name a second time (design D9).
- [ ] 2.9 Extend `__all__` and confirm `round` and `mod` are absent, with a
  module comment recording why (design D3, D4).

## 3. Layer 2: the vector helpers

- [ ] 3.1 Implement `polar`, `turn(point, angle, about=(0.0, 0.0))`,
  `rotate_x`, `rotate_y` and `rotate_z` as composition over layer 1 only,
  returning plain tuples, and add them to `__all__`.
- [ ] 3.2 Confirm that no name reaches `function_formula` except the six
  direct builtins and the functions that already had a rule: neither the
  layer-1 compositions (`clamp`, `clamp01`, `ramp`, `lerp`, `wrap`,
  `piecewise`, `bump`) nor any layer-2 helper may have a branch there, so
  every one of them has exactly one definition and its dimension behaviour
  is a consequence of the primitives it composes (design D5).

## 4. The dimension rules

- [ ] 4.1 In `solid_node/parameters.py`, extend `function_formula` with a rule
  branch for exactly six names — `abs`, `floor`, `ceil`, `sign`, `min`,
  `max` — as the `declarative-nodes` delta states, with an error message that
  names the operand and its dimension. Add no branch for any composition.
- [ ] 4.2 Verify that each composition's declared behaviour falls out of those
  six rules and the algebra's own, with no rule of its own: `clamp`,
  `clamp01`, `ramp`, `lerp`, `wrap`, `piecewise` and `bump` build their
  formula tree by composition, `bump(ratio)` is a dimensionless formula, and
  `clamp01(length)` and `max(length, 0.0)` raise from `min`/`max` — the
  intended behaviour, matching `length + 1`.
- [ ] 4.3 Run `tests/test_declarative_algebra.py` and `tests/test_math.py`
  green.

## 5. The parity corpus

- [ ] 5.1 Add `tests/expression_project/` — a small assembly declaring one
  driver, whose `simulate()` applies one operation per new symbolic function
  under the driver and `$t`, and which the framework's own agreement test can
  also import.
- [ ] 5.2 Extend `tools/generate_parity_fixture.py` to walk that tree the same
  way it walks the spike's machine (numeric snapshot paired by structure with
  the symbolic serialization) and append its cases under distinct keys.
- [ ] 5.3 Add a generator-side check that every name in
  `solid_node.math.SYMBOLIC_BUILTINS` appears in at least one case's
  expression, reading that tuple rather than keeping a list of its own, and
  failing the regeneration by name when one is uncovered. Have the
  framework's own test read the same tuple.
- [ ] 5.4 Regenerate the fixture into `solid-node-viewer` and diff it: every
  case the previous fixture carried must be present unchanged, under the same
  key and expected value. Report any change to an existing case as a stop
  condition.
- [ ] 5.5 Run the viewer's vitest against the regenerated fixture and record
  the result and the worst deviation. Do not commit anything in the viewer
  repository; if the evaluator cannot answer a name, stop and report it rather
  than editing the evaluator.

## 6. Framework validation

- [ ] 6.1 Run the framework test suite and record the result.
- [ ] 6.2 Confirm no existing expression string changed: run the tests that
  pin serialized expressions (`tests/test_conrod_symbolic.py`,
  `tests/test_driver_ids.py`, `tests/test_document_drivers.py`) and the
  `meta_project` and `flexible_project` fixtures.

## 7. Representative-caller evidence

- [ ] 7.1 In `projects/abacus`'s own repository, replace `absolute`,
  `clamp01` and the `sqrt` trick in `abacus/kinematics.py` with the new
  `solid_node.math` names, run that project's tests and a snapshot, and record
  the result and the expression-length change. Leave the edit uncommitted;
  no project commit belongs to this cycle.
- [ ] 7.2 Do the same for `projects/fender-bender`'s `piecewise` and `bump`,
  as the second caller covering the composition path.

## 8. Documentation

- [ ] 8.1 Add an "Expression math" section to `docs/api-reference.rst`, which
  has none today, covering both layers.
- [ ] 8.2 Extend `docs/animation.rst`'s "Non-linear kinematics" section with
  the new vocabulary, and give the `indicator` idiom with its integer
  precondition stated, so a project writes it locally and honestly.
- [ ] 8.3 Extend `docs/declaring.rst`'s algebra section with the new dimension
  rules, including why `floor` and `ceil` want a dimensionless argument.
- [ ] 8.4 Add the changelog entry under `Unreleased` in `docs/changelog.rst`,
  in the house style: a bold lead, the originating evidence, and the OpenSpec
  change name.

## 9. Records (after implementation confirms the design)

- [ ] 9.1 Append a revision note to
  `docs/adrs/MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md`
  recording that the symbolic vocabulary grew, which names were refused and
  why (`round`, `mod`), and that the corpus now covers every emitted name.
  Update its status line and the ADR index if the status text changes.
- [ ] 9.2 Update the "Expression math" section of `docs/architecture.md` to
  the new state, rewriting rather than appending.
- [ ] 9.3 Sync the baseline specs from the delta and archive the change.
- [ ] 9.4 Report to the pilot: the `%` sign divergence found in D4 as a live
  latent defect with no cycle of its own, and the four open questions in
  `design.md`.
