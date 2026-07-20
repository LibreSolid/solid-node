## Context

`solid export` carries an optional node color in its stable v1 manifest. The
development viewer uses `MeshNormalMaterial` when rendering models; the export
widget instead assigns an uncolored mesh a gray-blue `MeshStandardMaterial`.

## Goals / Non-Goals

**Goals:**

- Give each uncolored exported model the development viewer's normal-based
  material.

**Non-Goals:**

- Change any other widget behavior or the export format.

## Decisions

`WidgetTree` will use Three.js `MeshNormalMaterial` when no explicit or
   inherited manifest color is present, matching the material currently used
   by `solid develop`. Explicit colors retain their current standard-material
   rendering and precedence.

   This reuses the development viewer's established, orientation-responsive
   color language without changing the manifest. A separate palette was
   rejected because it would not match the development viewer.

## Risks / Trade-offs

- [Normal colors differ from author-selected colors] → an explicit node or
  ancestor color remains the author-controlled override.
