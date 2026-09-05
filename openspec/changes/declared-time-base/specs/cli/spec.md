## ADDED Requirements

### Requirement: Snapshot time under a declared time base

`solid snapshot --time` SHALL keep its meaning as a 0.0–1.0 position on the
animation timeline under either renderer. When the snapshotted root declares
a time base, the command SHALL keyframe the node at `time * loop` seconds
before rendering, so the image shows the same instant the viewer shows at
that slider position; when the root declares none it SHALL keyframe the
fraction as before. Validation of the option does not change.

#### Scenario: A fraction lands on the declared instant

- **WHEN** `solid snapshot --time 0.5` runs on a project whose root declares
  `time = Time(loop=43200)`
- **THEN** the node is keyframed at 21600 seconds and the image shows the
  machine half a loop in

#### Scenario: An undeclared root is keyframed at the fraction

- **WHEN** `solid snapshot --time 0.5` runs on a project whose root declares
  no time base
- **THEN** the node is keyframed at `0.5`, exactly as before
