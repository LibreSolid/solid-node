## 1. Red

- [ ] 1.1 Add the failing evaluator cases: a bare exponent literal, one
      inside an arithmetic expression, a negative exponent and a positive
      one, and the identifiers that must not be rewritten.
- [ ] 1.2 Extend the producer's parity corpus generator with a scaled
      driver term whose scale prints with an exponent, plus a tiny and a
      large bare literal; regenerate `parity-fixture.json` and watch the
      parity suite fail.

## 2. Green

- [ ] 2.1 Add the literal normalization to `evaluator.ts` on the cached
      tokenize path.
- [ ] 2.2 Run the widget suite (`npm test`) and the framework's Python
      suite.

## 3. Prove it on the model that found it

- [ ] 3.1 Rebuild the widget bundle and confirm the OpenFlexure
      Microscope document evaluates: its driver-scaled placement
      expressions resolve to the producer's numbers.

## 4. Record

- [ ] 4.1 Sync `openspec/specs/viewer-package/spec.md`.
- [ ] 4.2 Archive the change.
