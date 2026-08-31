## 1. Confirm the red

- [x] 1.1 Run the widget suite against the installed molejo and record
      the failure: ten cases across `src/flexible.test.ts` and
      `src/parity-fixture.test.ts`, each raising
      `spec.molejo: must be a spec version string, one of '0.1', '0.2', got 1`.
- [x] 1.2 Confirm `src/document.test.ts` passes despite carrying the same
      stale constant, so its fix is recorded as stale data rather than a
      failing case.

## 2. The hand-written constants

- [x] 2.1 `src/flexible.test.ts`: `SPRING_SPEC.molejo` becomes `'0.1'`.
- [x] 2.2 `src/document.test.ts`: the same.
- [x] 2.3 Re-run the suite; the eight `flexible.test.ts` failures clear
      and the two `parity-fixture.test.ts` failures remain, which
      isolates the fixture as the second, separate cause.

## 3. The producer-generated fixture

- [x] 3.1 Regenerate `src/parity-fixture.json` with
      `tools/generate_parity_fixture.py` against the workspace venv, so
      the version arrives from molejo rather than from an editor.
- [x] 3.2 Confirm the regenerated fixture differs from the committed one
      only where molejo's own output differs — the version string — and
      that its vertex data is unchanged. A geometry diff here would mean
      the rename moved geometry, which it must not.
- [x] 3.3 Re-run the suite; the parity cases pass.

## 4. The ambient declaration

- [x] 4.1 `src/molejo.d.ts`: `SPEC_VERSION` is declared `string`.
- [x] 4.2 Run `npm run typecheck` (`tsc --noEmit`) green.

## 5. Refuse an unreadable spec by name

- [x] 5.1 Red: construct a flexible node whose `tech` is `molejo` but
      whose spec the bundled evaluator cannot read (the integer version
      form is one such spec, and the one a pre-0.2 document carries).
      Assert it is refused at construction naming the node. It is not —
      construction succeeds and the failure arrives later, from
      `evaluate()`, as a raw `SpecError` with no node in it.
- [x] 5.2 In `FlexibleShape`'s constructor, after the `tech` check, ask
      the bundled evaluator whether the spec is readable and refuse on
      its answer, naming the node and quoting the evaluator's reason.
      Do not parse the spec or its version here: the set of readable
      specs is the evaluator's to define.
- [x] 5.3 Mirror the refusal at the document level the way the `tech`
      refusal is mirrored, so a document carrying such a node fails to
      load rather than mounting a tree with a hole in it.
- [x] 5.4 Assert the readable path is untouched: a valid spring still
      constructs, and the check costs nothing per frame because it runs
      once at construction.

## 6. The record

- [x] 6.1 `docs/adrs/NODE/ADR-057-…md`: the illustrative document shows
      `"molejo": "0.1"`. The decision text is untouched; only the example
      stops teaching a rejected form.
- [x] 6.2 Decided: no new ADR, and no `docs/architecture.md` update.
      The refusal is not a new decision — it applies ADR-057's recorded
      posture ("refusing it rather than rendering a wrong shape", already
      in force for an unevaluable `tech`) to the case one step further
      in, and it does so *through* ADR-057's opacity decision by asking
      the evaluator instead of reading the spec. The synthesis describes
      the same system afterwards.
- [x] 6.3 Run the full framework test suite, not only the widget's, to
      confirm the Python side is genuinely untouched.
