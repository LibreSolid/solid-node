# simulation delta: layered driver controls

## MODIFIED Requirements

### Requirement: Driver declarations separate from simulation state

The system SHALL let an assembly declare its drivers as stateless
class attributes: `Driver(default, range=None, unit=None, dtype=None,
scale=None)`, where `dtype=int` marks a discrete device whose state is
integer-typed and `scale` declares design units per native unit. A
declared `range` SHALL be expressed in design units — the units a
maker thinks and instruction targets are stated in — regardless of
`scale`; it is presentation metadata and never a clamp. A node class's
declared drivers SHALL be discoverable by name off the class without
instantiating it. Mutable driver state SHALL live only in a running
simulation, never on the declaration and never shared between node
instances or between simulations.

#### Scenario: Declarations carry no state

- **WHEN** two simulations run over nodes of the same class, stepping
  the same declared driver differently
- **THEN** each simulation observes only its own state trajectory and
  the class declaration is unchanged

#### Scenario: Declared drivers are discoverable

- **WHEN** a consumer inspects an assembly class declaring
  `x = Driver(default=100, range=(0, 200), unit='mm')`
- **THEN** it can enumerate the driver with its default, range, unit,
  dtype, and scale without constructing the assembly

#### Scenario: A scaled driver's range reads in design units

- **WHEN** an axis declares
  `motor = Driver(default=0, range=(0, 100), unit='ustep', dtype=int, scale=0.0125)`
- **THEN** the range means 0 to 100 design units of travel — 0 to 8000
  native microsteps — and a presenter converts through `scale` to
  relate it to native state, while nothing anywhere clamps state to it
