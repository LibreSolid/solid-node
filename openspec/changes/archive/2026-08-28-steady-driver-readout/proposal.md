## Why

Driving the Metamaquina2 axes in the viewer is visually unstable: each
driver's readout is written with trailing zeros stripped, so the string
changes width digit by digit as the maker drags, and a value crossing
zero gains or loses a minus sign. The number, its unit, and everything
laid out beside it jump horizontally throughout the drag — the maker is
reading a moving target while trying to land a value.

## What Changes

- The driver readout shows a fixed number of decimal places (4), padded
  with trailing zeros, instead of the shortest faithful string.
- The readout's number occupies a fixed-width, right-aligned column with
  room reserved for a minus sign, and uses tabular figures, so the digits
  and the sign do not move the layout as the value changes.
- The declared unit moves out of the aligned number column into its own
  segment, so the number column's right edge stays fixed regardless of
  whether a unit is declared.
- The range-less driver's number *input* keeps the existing shortest
  faithful formatting: it is a field the maker types into, not a readout.

No driver value, conversion, range, pinning, or driving call changes.
This is presentation only.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `viewer-package`: the requirement covering the on-screen driver
  controls gains the readout's stability guarantee — fixed decimal
  places, a fixed-width right-aligned number column, and reserved sign
  room — so the readout holds still under a drag.

## Impact

- `solid_node/viewers/widget/src/controls.ts`: a readout formatter beside
  the existing `formatDisplay`.
- `solid_node/viewers/widget/src/viewer.ts`: the driver row's readout
  element and its styling.
- `solid_node/viewers/widget/src/controls.test.ts`: coverage for the new
  formatter.
- No Python, export, or manifest change; no public API change.
