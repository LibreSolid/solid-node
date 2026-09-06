## 1. Red

- [x] 1.1 In `tests/test_manager_test.py`: a file defining a machine and a sub-assembly whose `render` raises when built alone, with a companion declaring only the machine — the run passes and the sub-assembly's failure never appears; a file defining two classes and no companion — both build and the run reports zero tests.
- [x] 1.2 Run them and confirm the first fails on the base for the intended reason.

## 2. Green

- [x] 2.1 `solid_node/manager/test.py`: select the declared classes in the ambiguous branch; refuse an undeclared case before building.
- [x] 2.2 Framework suite green; run `solid test --faceted simulation/don1/robot.py` in openvmp from the bench as the caller check.

## 3. Records

- [x] 3.1 No ADR: the runner's selection rule is not an architectural boundary; `docs/architecture.md` sentence on file references updated if it states the old rule.
- [x] 3.2 Sync delta spec, archive the change, final validation.
