## MODIFIED Requirements

### Requirement: Test runner lifecycle

The system SHALL build the node before testing (load, `set_keyframe(0)`,
render, assemble, `build_stls`), then run all `test_`-prefixed methods found
on both the node and the companion test case. The build SHALL hold the project
build lock and SHALL release it before the first test method runs, so a test
sweep never blocks another build of the same project. Each method runs once per
declared testing instant (default `[0]`), with the keyframe set per instant,
a colored pass/fail dot printed per instant, and each child's operations
checkpoint restored between instants and between tests. The run SHALL print
`Ran N tests in X seconds: P passed, F failed` and exit 1 if any failed;
`--failfast` stops at the first failure.

#### Scenario: Failing contract fails the run

- **WHEN** any assertion raises across any instant
- **THEN** the summary counts the failure and the process exits 1

#### Scenario: A test sweep does not block a rebuild

- **WHEN** a test run has finished building the node and is running test methods
- **THEN** another process can acquire the project build lock and rebuild the
  same project
