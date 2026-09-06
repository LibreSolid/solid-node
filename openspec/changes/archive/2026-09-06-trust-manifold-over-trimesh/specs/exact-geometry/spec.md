## ADDED Requirements

### Requirement: An exact artifact's mesh carries no degenerate triangles

The STL artifact written for an exact node — a leaf's tessellation or a
fused solid's — SHALL contain no degenerate (zero-area) triangles and no
vertex left unreferenced by their removal. The tessellation's tolerances are
unchanged; only the triangles OCCT emits with no area are dropped, so the
artifact's volume and the surface it encloses are those of the tessellation.

#### Scenario: A leaf whose tessellation emits degenerate triangles

- **WHEN** an exact leaf's shape tessellates to a mesh containing zero-area
  triangles and its STL artifact is written
- **THEN** the artifact holds every non-degenerate triangle of that mesh,
  none of the degenerate ones, and no vertex only they referenced

#### Scenario: A fused solid's export is unchanged

- **WHEN** a fused exact solid's STL artifact is written
- **THEN** it carries no degenerate triangles, as before
