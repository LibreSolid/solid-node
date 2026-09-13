## MODIFIED Requirements

### Requirement: The motion package holds what moves

The system SHALL provide a package `solid_node.motion` whose subject is
what moves and what drives what, laid out as three submodules so that an
import line names the kind of thing it brings in:

- `solid_node.motion.ports` — a value that flows between nodes: the port
  declarations, their bound value slot, the binding helper, the
  declaration enumerator, the root's own time channel (`Time`, with its
  two bases `Time(loop=...)` and `Time.running()` told apart by `mode`,
  and the enumerator that reads a class's time declaration), and the
  binder kind a running simulation binds as (`RunBinder`), kept here so
  the binding helper can recognize it without importing the simulation
  layer;
- `solid_node.motion.joints` — a pair that places a body: `Revolute` and
  `Prismatic`, their error kind and their enumerator (capability
  `joints`);
- `solid_node.motion.couplings` — a law between two coordinates: `Affine`,
  the relation and derived-coordinate kinds, their error kinds and their
  enumerators (capability `couplings`).

The package `__init__` SHALL export no name of its own and SHALL NOT
resolve a submodule's names as attributes of the package, so there is
exactly one import path for each name.

#### Scenario: The submodules hold their kinds

- **WHEN** a consumer imports `solid_node.motion.joints` and
  `solid_node.motion.couplings`
- **THEN** `Revolute` and `Prismatic` are read off the first and `Affine`
  off the second, and each module's docstring states its subject

#### Scenario: The package itself exports nothing

- **WHEN** a consumer reads any port, time-base, joint or coupling name
  off `solid_node.motion` directly
- **THEN** `AttributeError` is raised, so
  `from solid_node.motion import RotationalPort` fails at the import and
  the submodule path is the only path

#### Scenario: The running base and the run binder are imported from the ports module

- **WHEN** a consumer writes
  `from solid_node.motion.ports import Time, RunBinder` and declares
  `time = Time.running()` on a root
- **THEN** `type(root).time.mode` reads `'running'`, `type(root).time.loop`
  reads `None`, and `RunBinder` is the class every running simulation's
  binder is an instance of

## ADDED Requirements

### Requirement: A run-owned coordinate has one binder, the run

A coordinate a running simulation has bound — its slot's binder being a
`RunBinder` — SHALL accept a new binding only from that same run. Every
other binding that reaches the one binding path for such a slot — an
author's `simulate()` assignment, a `connect()`, a wiring's or a
relation's application — SHALL be refused as doubly bound, naming the
coordinate, the class whose `simulate()` is running (or the node that owns
the coordinate when none is), and the running simulation, and saying that
a law stated in `simulate()` belongs in a relation. The refusal SHALL be
the same kind the couplings capability raises for two binders. A run's own
rebinding SHALL be recorded with the run as the binder exactly as any
binder is recorded, and the freshness rule of the couplings capability
SHALL leave a run-bound slot alone.

#### Scenario: An author assignment of a run-owned joint is refused

- **WHEN** the running simulation owns `first.turn` and an assembly's
  `simulate()` assigns `self.first.turn = 12.0`
- **THEN** the binding raises the doubly-bound refusal naming `first.turn`,
  the assembly's class and the running simulation, and the slot keeps the
  run's value

#### Scenario: The run rebinds its own coordinate

- **WHEN** the run binds `first.turn` again on the next tick
- **THEN** the binding is accepted, the slot's binder is the run, and the
  joint's body is placed at the new value

#### Scenario: A connect into a run-owned coordinate is refused

- **WHEN** an assembly's `simulate()` calls `connect(source, child.turn)`
  on a coordinate the run owns
- **THEN** the binding is refused by the same rule, naming the coordinate
  and the run
