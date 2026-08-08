## MODIFIED Requirements

### Requirement: Test declaration and binding

The system SHALL support two test styles run by the same command: companion
`TestCase` classes in a test file (package node `pkg/__init__.py` →
`pkg/test.py`; module node `gear.py` → `test_gear.py`), and tests embedded on
the node via `TestCaseMixin`.

The system SHALL load **every** `TestCase` defined in a companion file, never
only the first. A `TestCase` MAY declare the node it exercises with a
class-level `node = <NodeClass>` attribute. An undeclared `TestCase` SHALL bind
to the node module's single node class; when that module defines several node
classes, an undeclared `TestCase` SHALL fail the run with an error naming it and
listing the candidate node classes, and SHALL NOT be silently skipped.

A companion `TestCase` receives its bound node as `self.node` and as a
snake_case alias derived from the test class name with the `Test` suffix
stripped (e.g. `SimpleClockTest` → `self.simple_clock`).

#### Scenario: Companion test binding

- **WHEN** `solid test` runs a `GearTest(TestCase)` next to `gear.py`
- **THEN** test methods can reference the node as both `self.node` and
  `self.gear`

#### Scenario: Several test cases in one companion file

- **WHEN** a companion file defines `WindmillTest` and `SailTest`, each
  declaring its node
- **THEN** both run, each bound to the node it declares

#### Scenario: An undeclared test case cannot be bound

- **WHEN** a companion file defines a `TestCase` with no `node` declaration and
  its node module defines two node classes
- **THEN** the run fails with an error naming the test case and the candidate
  node classes

### Requirement: Test runner lifecycle

The system SHALL build each node under test before testing it (load,
`set_keyframe(0)`, render, assemble, `build_stls`), then run all
`test_`-prefixed methods found on the node and on every companion test case
bound to it. The build SHALL hold the project build lock and SHALL release it
before the first test method runs, so a test sweep never blocks another build of
the same project.

When the reference names a single node, the run covers that node and the test
cases bound to it. When the reference names a file, the run covers every node
class defined in that file and every test case in its companion. No test case in
a companion file SHALL be excluded from a run that covers its node.

Each method runs once per declared testing instant (default `[0]`), with the
keyframe set per instant, a colored pass/fail dot printed per instant, and each
child's operations checkpoint restored between instants and between tests. The
run SHALL print `Ran N tests in X seconds: P passed, F failed` and exit 1 if any
failed; `--failfast` stops at the first failure.

#### Scenario: Failing contract fails the run

- **WHEN** any assertion raises across any instant
- **THEN** the summary counts the failure and the process exits 1

#### Scenario: A test sweep does not block a rebuild

- **WHEN** a test run has finished building the node and is running test methods
- **THEN** another process can acquire the project build lock and rebuild the
  same project

#### Scenario: A file reference runs every node in the file

- **WHEN** a user runs `solid test windmill/model.py` on a file defining two
  node classes, each with a companion test case
- **THEN** both nodes are built and the test methods of both test cases are
  counted in the summary
