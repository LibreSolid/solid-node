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
