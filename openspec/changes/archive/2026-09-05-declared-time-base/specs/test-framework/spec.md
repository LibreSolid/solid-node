## MODIFIED Requirements

### Requirement: Animation-instant decorators

The system SHALL provide `@testing_instant(instant)` and
`@testing_steps(steps, start=0, end=1)` setting `testing_instants` on a test
method; the runner executes the method once per instant with the keyframe
set. `testing_steps` requires `steps >= 2` and forces the final instant to
exactly `end`. An instant is handed to `set_keyframe` unchanged, so it means
what the tested root's time base says: a fraction of the timeline for a root
declaring none, and seconds for a root declaring `Time(loop=...)`. The
decorators' defaults do not change with the declaration; a test over a
declared root states the span it sweeps in seconds.

#### Scenario: Sweeping a rotation

- **WHEN** a method is decorated `@testing_steps(10)`
- **THEN** it runs at 10 evenly spaced instants from 0 to 1 inclusive

#### Scenario: Sweeping seconds under a declared time base

- **WHEN** a test over a root declaring `Time(loop=43200)` is decorated
  `@testing_steps(48, end=1.5)`
- **THEN** it runs at 48 instants from 0 to 1.5 seconds inclusive, and the
  root reads `time` as those seconds
