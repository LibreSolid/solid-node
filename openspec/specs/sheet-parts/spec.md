# sheet-parts Specification

## Purpose

Authoring a part cut from sheet stock: a 2D profile plus a declared
thickness as the single source from which both the solid in the tree and
the nominal DXF cut file derive, so the part a maker previews and the
file a cutter consumes cannot diverge.

## Requirements

### Requirement: A sheet part is authored as a profile plus thickness

The system SHALL provide an abstract sheet leaf kind whose part is authored
as a two-dimensional profile plus a declared thickness. A concrete sheet
adapter's extension point SHALL be `profile()`, returning the 2D profile in
its backend's terms; the sheet base SHALL own the derivation of the solid as
the extrusion of that profile — profile on the XY plane, extruded along +Z by
`thickness` — so the solid in the tree and the cut profile always derive from
the one authored profile. The system SHALL NOT offer a sheet-leaf path that
authors the solid and the cut profile separately.

`thickness` SHALL be declared per node, as a class attribute or a constructor
argument, and SHALL be a positive number. A sheet leaf with a missing or
non-positive thickness SHALL fail at construction with an error naming the
node.

#### Scenario: The solid is the extruded profile

- **WHEN** a sheet leaf declares `thickness` and its `profile()` returns a
  planar profile of area A
- **THEN** the node renders a solid of volume A × thickness, extending from
  the XY plane to Z = thickness

#### Scenario: Thickness is required and positive

- **WHEN** a sheet leaf is constructed with no thickness, or with a zero or
  negative one
- **THEN** construction raises an error naming the node

#### Scenario: Two thicknesses of one panel are distinct parts

- **WHEN** one sheet leaf class is instantiated twice with different
  `thickness` constructor arguments
- **THEN** the two instances have distinct artifact identities and neither
  reuses the other's artifacts

### Requirement: A sheet profile is one manufacturable face

The profile of a sheet leaf SHALL be exactly one planar face: a single outer
boundary with any holes strictly inside it. One sheet leaf SHALL be one part.
A `profile()` result that is not planar, is not a single face, or is a solid
or other non-2D object SHALL be rejected with an error naming the node and
the type it produced, before any artifact is written.

#### Scenario: A profile with holes is accepted

- **WHEN** `profile()` returns one planar face whose boundary encloses
  interior holes
- **THEN** the node renders, and the holes pierce the extruded solid through
  its full thickness

#### Scenario: A multi-part profile is rejected

- **WHEN** `profile()` returns two disjoint faces
- **THEN** validation raises an error naming the node, and no artifact is
  written

#### Scenario: A non-2D render source is rejected

- **WHEN** `profile()` returns a solid rather than a planar face
- **THEN** validation raises an error naming the node and the type it
  produced

### Requirement: A nominal DXF artifact is built beside the solid

Each sheet leaf SHALL produce a DXF artifact of its profile during the build,
through the same artifact lifecycle that produces its STL and BREP: written
beside them, regenerated when stale, and not rewritten when current. The
build SHALL treat the sheet leaf's work as skippable only when the DXF is
current along with the other artifacts.

The DXF SHALL be nominal: the authored profile's boundary and holes at model
scale (millimeters), with no kerf or other machine compensation applied.
Circular and arc edges SHALL be preserved as arc entities, not tessellated
into polylines.

#### Scenario: A build produces the cut file

- **WHEN** a project containing a sheet leaf is built
- **THEN** a `.dxf` artifact for that leaf exists beside its `.stl`,
  containing the profile's outer boundary and holes

#### Scenario: A current DXF is not rewritten

- **WHEN** a sheet leaf is assembled and all its artifacts, the DXF
  included, are current
- **THEN** no artifact is rewritten

#### Scenario: A missing DXF alone forces regeneration

- **WHEN** a sheet leaf's STL and BREP are current but its DXF is absent
- **THEN** the build regenerates the DXF

#### Scenario: Arcs stay exact in the cut file

- **WHEN** a sheet leaf's profile contains a circular hole
- **THEN** the DXF represents it as a circle or arc entity at the modelled
  radius, not as a polyline approximation
