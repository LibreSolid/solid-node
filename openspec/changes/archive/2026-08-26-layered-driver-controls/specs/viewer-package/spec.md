# viewer-package delta: layered driver controls

## ADDED Requirements

### Requirement: A maker drives the focused layer's drivers and instructions on screen

For a document that declares drivers, the mounted viewer SHALL present
an on-screen control for each driver and each instruction declared at
the focused assembly layer: a button per instruction and a bounded
slider with a numeric readout per driver. Control labels SHALL be the
declared identifiers relative to the focused layer. Sliders SHALL
present values in design units with the declared unit, and SHALL move
live while a ramp plays. Interacting with a control SHALL produce the
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

### Requirement: Controls follow the focused layer

The viewer SHALL scope driver controls strictly to the focused
assembly layer. With focus at the document root, only drivers and
instructions declared with bare (root-level) identifiers SHALL be
presented. Focusing an instance SHALL replace the controls with those
the instance itself declares, labelled relative to it; controls of its
descendants and of other branches SHALL NOT be presented. When a
document update removes the focused node and focus resets, the
controls SHALL re-scope with it. A focused layer declaring nothing
SHALL present no sliders or buttons while the focus affordance remains
available.

#### Scenario: Focusing an axis reveals its controls

- **WHEN** the maker focuses `x_axis` on a machine whose axes each
  declare a `motor` driver and a `Home` instruction
- **THEN** exactly one slider labelled `motor` and one button labelled
  `Home` appear, driving `x_axis.motor` and `x_axis.Home`, and
  `y_axis`'s controls are not shown

#### Scenario: A root that declares nothing shows no controls

- **WHEN** the maker views the root of a machine that declares all
  drivers and instructions on its children
- **THEN** no slider or button is presented at the root and the focus
  affordance still offers the declaring children

#### Scenario: A republish that removes the focused node re-scopes

- **WHEN** a document update removes the focused instance and the
  viewer resets focus to the root
- **THEN** the presented controls become the root layer's

### Requirement: The host chooses how driver controls are presented

The host SHALL be able to choose at mount time whether the driver
chrome (controls and focus affordance) is presented. By default it is
presented for documents that declare drivers. A host that suppresses
it SHALL retain the full driving API unchanged.

#### Scenario: A shop floor builds its own instrument panel

- **WHEN** a host mounts with the driver chrome suppressed
- **THEN** no on-screen driver control or focus affordance appears
  while `drivers()`, `setDriver`, `trigger`, and `onDriverChange`
  behave exactly as when the chrome is shown

#### Scenario: A published export shows the controls

- **WHEN** a maker opens a self-contained export of a driver-declaring
  document with default options
- **THEN** the driver chrome is presented
