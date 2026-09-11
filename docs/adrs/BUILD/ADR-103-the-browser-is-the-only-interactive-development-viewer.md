# ADR-103: The browser is the only interactive development viewer

**Status:** Accepted

**Date:** 2026-09-11

**Change:** [remove-openscad-viewer](../../../openspec/changes/archive/2026-09-11-remove-openscad-viewer/)

**Amends:** [ADR-046](../NODE/ADR-046-conditional-openscad-dependency.md),
[ADR-068](../EXPORT/ADR-068-optional-viewer-package-behind-a-process-boundary.md),
and [ADR-102](../NODE/ADR-102-native-materialization-precedes-optional-scad-presentation.md)

## Context

OpenSCAD was solid-node's first reliable development viewer. ADR-068 later
made the increasingly capable browser viewer a separate AGPL package and let
``solid develop`` choose between it and the OpenSCAD GUI according to what was
installed. That kept a plain Apache framework installation interactive while
the new package boundary was established.

Machine simulation has since made the two surfaces materially different. The
browser viewer exposes independent driver controls and instructions and
continuously evaluates flexible parts. OpenSCAD can receive one numerically
bound state and its ``$t`` timeline, but cannot present that machine control
surface or continuously evaluate the flexible geometry. Maintaining its GUI
launch and PID lifecycle therefore preserves a progressively less faithful
viewer and makes installation select the user's machine experience.

This does not diminish OpenSCAD as a modelling or output technology. Solid2
and raw OpenSCAD leaves still use it as their geometry backend, legacy
symbolic evaluation still invokes it, generated SCAD remains supported, and
the OpenSCAD snapshot renderer remains the established fixed-pose evidence
path. The separately founded ``solid-node-viewer`` 0.1.0 package is not yet
published; making its distribution available is consequently a v0.7 release
dependency, not an outcome of this framework change.

## Decision

The browser viewer is the only interactive viewer launched by
``solid develop``. The default and the retained explicit ``--web`` spelling
resolve the installed viewer package before starting either viewer or builder;
when absent, they fail naming ``pip install "solid-node[viewer]"``.
``--web-dev`` keeps the package's frontend-development mode. ``--no-web``
continues to run only the builder watch loop, without viewer discovery or a
viewer port.

The ``--openscad`` option, automatic OpenSCAD fallback, GUI launcher,
``.openscad.pid`` lifecycle, and their tests are removed. The option is not
kept as an alias because that would silently request a different viewer from
the one its name promises.

``OpenScadRenderer`` and the default of ``solid snapshot`` are unchanged.
OpenSCAD modelling nodes, legacy SCAD evaluation, SCAD generation and
OpenSCAD-backed geometry production are unchanged. OpenSCAD remains a
conditional dependency only for those paths and the fixed-pose snapshot
renderer; interactive browser development does not consult it.

## Alternatives rejected

- **Keep OpenSCAD as an automatic fallback:** installation would continue to
  select between two different machine experiences and retain the less
  faithful path as a supported product surface.
- **Keep ``--openscad`` as a deprecated alias for the browser:** the command
  would do something other than what the explicit option says.
- **Remove the OpenSCAD snapshot renderer too:** an explicitly fixed-pose
  renderer can faithfully consume a numerically bound machine and retains
  useful evidence controls. Its future is independent of interactive viewer
  fidelity.
- **Remove ``--web`` because the browser is now the default:** this would add
  unrelated CLI breakage without simplifying the process boundary.

## Consequences

- Interactive development needs the separate viewer distribution; a missing
  package fails before a watch loop is left running.
- A plain framework installation remains useful for builds, tests, viewerless
  development, widget-free export and OpenSCAD snapshots, but has no
  interactive viewer.
- There is one interactive machine surface for future simulation work and no
  framework-owned GUI/PID lifecycle.
- OpenSCAD remains in the complete conditional-dependency set only where its
  modelling, legacy-evaluation or fixed-pose rendering work invokes it.
- v0.7 release material must explain both the historical transition and the
  retained OpenSCAD capabilities.

## Evidence

- The linked change records the red CLI/dependency boundary, focused process
  and snapshot suites, real OpenSCAD modelling and PNG rendering, browser
  package/no-package/viewerless exercises, documentation validation and the
  full framework suite.
