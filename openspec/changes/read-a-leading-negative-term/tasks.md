## 1. Red first, twice

- [ ] 1.1 Unit cases in `evaluator.test.ts`: a leading negative literal, a leading negative term beside a product, and the Metamaquina2 entry expression verbatim — red on the shipped parser
- [ ] 1.2 The corpus itself: give `spike/expressions/machine_model.py` a sixth expression shape, regenerate the fixture, and confirm the producer-generated cases go red on the shipped parser

## 2. Read the expression the way it is written

- [ ] 2.0 Make the manifest installable first: declare `molejo` as the working copy beside the framework, which is what the shared `node_modules` was already symlinked to and what a spec-version-2 document needs
- [ ] 2.1 Move `jokenizer` to `^1.0.1`, and regenerate the lockfile by installing rather than by hand
- [ ] 2.2 Confirm the parse tree's node kinds are unchanged, so `powify` and the free-variable walk need no adjustment
- [ ] 2.3 Lift a negation out of the base of a `^` in `powify`, since converting the operator is the only place OpenSCAD's precedence for it can be applied, and record why JavaScript has no answer to copy

## 3. Pin both sides of the seam

- [ ] 3.1 Ask the corpus for the new shape by name in `parity-fixture.test.ts`, the way it already asks for `^`
- [ ] 3.2 Pin the producer's own spelling in `tests/test_driver_ids.py`, beside the five shapes it already pins

## 4. Evidence

- [ ] 4.1 Widget suite and typecheck green; framework Python tests green
- [ ] 4.2 Re-run the originating machine: every distinct expression Metamaquina2 publishes agrees between the producer and the viewer's parser
- [ ] 4.3 Prove the committed manifest resolves from a clean layout at the primary checkout's depth, with `npm ci` and nothing placed by hand
