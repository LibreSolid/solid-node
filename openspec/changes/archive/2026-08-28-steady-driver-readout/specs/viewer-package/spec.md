## MODIFIED Requirements

### Requirement: A maker drives the focused layer's drivers and instructions on screen

For a document that declares drivers, the mounted viewer SHALL present
an on-screen control for each driver and each instruction declared at
the focused assembly layer: a button per instruction and a bounded
slider with a numeric readout per driver. Control labels SHALL be the
declared identifiers relative to the focused layer. Sliders SHALL
present values in design units with the declared unit, and SHALL move
live while a ramp plays. A driver's readout SHALL show a fixed number
of decimal places, and SHALL hold the position of its digits, its sign,
and everything laid out beside it steady as the value changes: reading
a value while dragging SHALL not require following a moving target.
Interacting with a control SHALL produce the
same observable state as the corresponding host driving call, so a
value or trigger set on screen and one set through the handle are
indistinguishable to expressions, listeners, and readbacks. The
declared `range` SHALL bound only the slider's travel, never the
underlying value: a value bound past the range through the host API
SHALL survive intact, with the slider pinned at its end and the
numeric readout showing the true value. Every control SHALL carry an
accessible name for assistive tools. A document declaring no drivers
SHALL present none of this chrome.

#### Scenario: A maker homes an axis with a button

- **WHEN** the focused layer declares the instruction `Home` and the
  maker presses the button labelled `Home`
- **THEN** the same ramp plays as a host `trigger` of that qualified
  instruction, the affected driver's slider travels with it to the
  target, and the button indicates the run until it lands

#### Scenario: A maker jogs a motor with a slider

- **WHEN** the maker drags the slider labelled `motor` on a focused
  axis whose driver declares `unit: ustep` and a millimetre scale
- **THEN** the model pose follows the drag, the readout shows the
  design-unit value with its unit, and `driver()` on the handle
  reports the corresponding native value

#### Scenario: A readout holds still through a drag

- **WHEN** the maker drags a driver's slider through values of
  differing digit counts and across zero into negative travel
- **THEN** every value is written with the same number of decimal
  places, and neither the change of digit count nor the appearance of
  the minus sign moves the readout's digits or the unit beside them

#### Scenario: A re-pressed button replaces the run

- **WHEN** the maker presses an instruction's button while its ramp is
  still playing
- **THEN** the new run replaces the old one, exactly as a host
  re-trigger does

#### Scenario: An out-of-range value is shown honestly

- **WHEN** a host binds a driver past its declared range and the maker
  looks at that driver's control
- **THEN** the slider sits pinned at its nearest end, the readout
  shows the actual out-of-range value, and the bound value is
  unchanged by the chrome

#### Scenario: A driverless document is unchanged

- **WHEN** a document with an empty drivers table is mounted
- **THEN** no driver control, readout, or focus affordance appears and
  the widget presents exactly its pre-existing chrome
