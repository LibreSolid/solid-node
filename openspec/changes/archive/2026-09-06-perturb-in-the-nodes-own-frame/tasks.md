## 1. Red

- [x] 1.1 In `tests/test_assertions.py`, rewrite `PerturbationInsertionTest` to expect the injected operation at index 0 for a node whose operations are `[Rotation, Translation]`, and add a `LocalFrameCarriedByRotationTest` twin whose node leads with the Rotation, expecting the carried destination.
- [x] 1.2 Run them and confirm they fail on the base for the intended reason.

## 2. Green

- [x] 2.1 `solid_node/test.py` `_assert_perturbation`: insert at index 0; update the surrounding comments.
- [x] 2.2 Framework suite green; run abacus's rod contracts with directions restated in the rod's frame as the caller check.

## 3. Records

- [x] 3.1 ADR amending ADR-025 in `docs/adrs/TEST-FRAMEWORK/`; index and `docs/architecture.md` updated.
- [x] 3.2 Sync delta spec, archive the change, final validation.
