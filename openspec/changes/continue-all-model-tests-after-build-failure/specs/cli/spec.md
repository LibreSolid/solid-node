## MODIFIED Requirements

### Requirement: Test command

The system SHALL provide `solid test [reference]` with `--failfast`, the
mutually exclusive kernel selectors `--exact` and `--faceted`, and
`--volume-epsilon MM3`, accepting a node reference in any accepted spelling,
or the path of a companion test file, which resolves to the node module it
exercises. Without a selector the kernel comes from `SOLID_TEST_KERNEL`, and
without `--volume-epsilon` a faceted run's epsilon comes from
`SOLID_TEST_VOLUME_EPSILON`, both read through the same `.env` rule as the
other `SOLID_*` settings. Runner behavior, the resolution order and the
errors are specified in the test-framework capability.

`solid test --all` SHALL run, as one test run reported once, the tests of every
declared model in declaration order, each model built in its own build
directory. A model that fails reference resolution, load, construction,
initial keyframe binding, render, assembly, or artifact generation SHALL be
reported and counted once as a failure of that declared model. Its tests SHALL
NOT run, and the runner SHALL proceed to the next declared model unless
`--failfast` is given. The final report and exit status SHALL include every
model failure and test result observed before the run completed or stopped.
The command SHALL NOT accept a reference beside the flag and SHALL fail in a
project that declares no models.

#### Scenario: Test file as argument

- **WHEN** a user runs `solid test windmill/test_gear.py`
- **THEN** the runner resolves and builds the nodes defined in
  `windmill/gear.py` and runs their tests

#### Scenario: One node by qualifier

- **WHEN** a user runs `solid test windmill.gear:Gear`
- **THEN** the runner builds `Gear` and runs its own test methods and the test
  cases bound to it

#### Scenario: A developer runs the fast kernel by flag

- **WHEN** a user runs `solid test --faceted --volume-epsilon 0.5`
- **THEN** the runner compares every pair on meshes with that epsilon and
  labels the run as faceted

#### Scenario: Both selectors together are refused

- **WHEN** a user runs `solid test --exact --faceted`
- **THEN** argument parsing fails naming the two flags as mutually exclusive

#### Scenario: Every declared model is tested

- **WHEN** a user runs `solid test --all` in a project declaring two models,
  each with companion tests
- **THEN** one run executes both models' tests, the summary counts all of
  them, and the exit status is nonzero iff any test failed

#### Scenario: A model build failure is aggregated

- **WHEN** the first declared model fails during construction, render,
  assembly, or artifact generation and a later declared model can build
- **AND** the user runs `solid test --all` without `--failfast`
- **THEN** the first model is named and counted once as failed
- **AND** the later model's tests run
- **AND** one final report covers both models and the command exits nonzero

#### Scenario: A model build failure honors failfast

- **WHEN** the first declared model fails to build and a later declared model
  can build
- **AND** the user runs `solid test --all --failfast`
- **THEN** the first model is named and counted once as failed
- **AND** the later model does not build or run tests
- **AND** one final report covers the failure and the command exits nonzero
