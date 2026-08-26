# Layered driver controls

## Why

ADR-056's product goal is a maker clicking buttons and watching the
simulated machine respond. Stage 3b (`driver-aware-viewer`, archived
2026-08-26) shipped the programmatic driving API only: a maker looking
at an export or the develop web app still has no on-screen way to
trigger an instruction or move a driver. The pieces are already
ratified and waiting to be joined: the drivers table carries `range`
explicitly as presentation metadata for exactly this chrome, the
instructions table enumerates every triggerable action, and the
assembly-focus interface addresses instances by the same path segments
that qualify driver ids — so scoping controls to the focused layer is
a natural fit rather than a new concept.

## What Changes

- The widget grows driver chrome: one button per instruction and one
  slider (with numeric readout) per driver declared at the focused
  assembly layer, labelled relative to that layer, shown in design
  units with the declared unit, moving live while ramps play.
- Scoping is strict per layer: at the document root only root-declared
  controls appear; focusing an instance shows that instance's own
  controls. The root of a machine that declares everything on its
  children legitimately shows no sliders or buttons — that is product
  pressure toward declaring machine-level instructions on the machine,
  not a defect.
- A breadcrumb affordance inside the widget moves focus down into
  subassemblies that declare controls and back up toward the root,
  driving the existing host focus interface. Click-to-focus picking on
  the 3D scene is explicitly deferred.
- The host chooses whether the driver chrome is presented; a host
  building its own UI on the 3b API suppresses it.
- Driverless documents look exactly as they do today; no chrome, no
  breadcrumb.
- Excluded: raycast picking, theming beyond the widget's existing
  minimal styling, G-code-style programs in the trigger seat, and the
  shipped `dist` bundle rebuild (packaging step, as before).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `viewer-package`: new requirements for on-screen driver controls —
  layer-scoped sliders and instruction buttons, live updates, unit
  presentation, unclamped-range display, busy indication, and a host
  option controlling whether the chrome is presented.
- `viewer-assembly-navigation`: new requirement for an in-widget focus
  affordance (breadcrumb) that reaches every layer declaring drivers
  or instructions and returns to any ancestor, mirroring and driving
  the same focus state as the host API.
- `simulation`: the declaration requirement gains the one sentence the
  chrome forces us to pin — a declared `range` is expressed in design
  units, like instruction targets, and remains presentation-only. The
  slider is the first consumer that must convert it, so its units can
  no longer stay unstated.

## Impact

- Widget sources only: `viewer.ts`, `options.ts`, a new pure controls
  module, and their tests. No Python change, no producer change, no
  document schema change (the document already carries everything the
  chrome needs).
- ADR-056 gains its stage-3c status entry when the change is applied.
- Evidence chain: Metamaquina2 (a maker driving a printer's axes from
  buttons) remains the originating requirement; the expression-spike
  machine (two instances of one Axis class) is the validation model,
  exercised live in a browser as in stage 3b.
