## ADDED Requirements

### Requirement: The running engine costs nothing to a model that declares no running time

The system SHALL import the running simulation's modules — the compile
step and the engine beneath `solid_node.simulation` — only when a `Sim`
is constructed over a root declaring `Time.running()`. Importing
`solid_node.simulation`, constructing a `Sim` over an untimed or looping
root, building or publishing any model, and importing
`solid_node.motion.ports` or `solid_node.motion.couplings` SHALL NOT import
them. The running time base and the run-binder marker SHALL live in
`solid_node.motion.ports` with no import of their own, so the motion
package's import cost is unchanged, and the couplings module's recognition
of a run binder SHALL add no import to it.

#### Scenario: A looping root's simulation imports no running engine

- **WHEN** a fresh interpreter constructs a `Sim` over a root declaring
  `Time(loop=...)` and runs it
- **THEN** the compile step and the engine modules are absent from the
  process's imported modules

#### Scenario: Ports and couplings cost what they cost

- **WHEN** `solid_node.motion.ports` and `solid_node.motion.couplings` are
  imported in fresh interpreters
- **THEN** their imported `solid_node` modules are the sets the "The motion
  package is cheap to import" requirement already states, with nothing
  from `solid_node.simulation` among them

#### Scenario: A running root's simulation imports the engine on construction

- **WHEN** a `Sim` is constructed over a root declaring `Time.running()`
- **THEN** the compile step and the engine are imported then, and no CAD
  backend and no exact-geometry stack with them
