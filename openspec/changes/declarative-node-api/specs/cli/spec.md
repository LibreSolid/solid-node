## ADDED Requirements

### Requirement: Root parameter overrides

Every command that loads a node SHALL accept `--set name=value`, repeatable,
applied to the root node's declared parameters under the `declarative-nodes`
capability. A value SHALL be parsed by the parameter's declared kind — a
float for `Length`, `Angle`, `Ratio` and `Scalar`, an integer for `Count`,
`true` or `false` for `Flag` — and checked by the declared constraints
exactly as a Python caller's value would be. A name that is not a declared
parameter of the root, or names a derived parameter, SHALL fail listing the
root's settable parameters; a root that declares no parameters SHALL refuse
the flag naming the root. The develop command SHALL apply the same overrides
to every rebuild of its watch loop.

#### Scenario: A build at another bore

- **WHEN** `solid build engine.py --set bore=32.0` runs on a root declaring
  `bore = Length(30.0)`
- **THEN** the build realizes the root with `bore` at `32.0`, every
  dependent child follows, and the published artifacts are those of that
  parameter set

#### Scenario: A value the declaration refuses

- **WHEN** `--set count=1` names a `Count(8, min=2)`, or `--set
  guard_installed=maybe` names a `Flag`
- **THEN** the command fails naming the parameter and the violated
  constraint or the expected form, and nothing is built

#### Scenario: An unknown name

- **WHEN** `--set boar=32.0` names no declared parameter of the root
- **THEN** the command fails listing the root's settable parameters

#### Scenario: A node without a default is loaded directly

- **WHEN** `solid develop piston.py` loads a leaf declaring
  `diameter = Length()` without `--set diameter=...`
- **THEN** the command fails naming the class and the parameter, and
  `solid develop piston.py --set diameter=29.4` loads it

#### Scenario: Overrides survive a reload

- **WHEN** a develop session started with `--set bore=32.0` rebuilds after
  a source edit
- **THEN** the rebuilt root is realized with `bore` at `32.0`
