## MODIFIED Requirements

### Requirement: SCAD remains a supported output and compatibility boundary

Existing SCAD-facing calls, including public `assemble()` and `as_scad()`,
SHALL remain usable. `assemble()` SHALL retain its SCAD-compatible result,
placement order, colours and optimized artifact imports. The normal
`solid build` SHALL retain its SCAD deliverables; a request for them SHALL use
the same prepared machine and canonical geometry as other consumers.

The system SHALL preserve OpenSCAD and Solid2 modelling support and legacy
SCAD-only adapter overrides. The OpenSCAD snapshot renderer SHALL remain
selectable with its existing default and missing-tool behavior. Flexible SCAD
output SHALL retain its numeric-snapshot and symbolic-time limitations; it
SHALL NOT be described as supporting live independent driver controls. The
OpenSCAD GUI SHALL NOT be offered as a solid-node viewer or automatic
development fallback.

SCAD text is presentation, not the machine's identity. Equivalent output text
is permitted where artifact references replace obsolete fusion expressions,
but SCAD presentation SHALL NOT compute a second faceted fusion with a
different geometry engine.

#### Scenario: A direct SCAD caller remains supported

- **WHEN** existing project code asks for `node.assemble()` or `node.scad_code`
- **THEN** it receives usable SCAD presentation with the existing transform
  and colour semantics, even if native preparation already occurred

#### Scenario: A normal build remains useful to OpenSCAD users

- **WHEN** an ordinary `solid build` completes
- **THEN** its SCAD deliverables remain available for OpenSCAD and repeated
  unchanged builds avoid rewriting identical presentation files

#### Scenario: SCAD and browser view the same fused part

- **WHEN** a faceted fusion is rendered from SCAD and in a browser export
- **THEN** both consume the canonical fused artifact rather than independently
  fusing the ingredients with different engines

#### Scenario: Viewer policy is independent of SCAD support

- **WHEN** `solid develop` runs without the optional browser viewer package
  and OpenSCAD is available
- **THEN** it fails naming the viewer extra rather than treating modelling or
  SCAD-output support as an interactive viewer

#### Scenario: The OpenSCAD snapshot boundary remains

- **WHEN** `solid snapshot --renderer openscad` renders a numerically bound
  machine pose
- **THEN** it uses the retained SCAD presentation and OpenSCAD renderer with
  the existing snapshot behavior
