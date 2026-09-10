## MODIFIED Requirements

### Requirement: Exact geometry is persisted and reloaded

An exact rigid node's shape SHALL be persisted as a build artifact and
reloaded from it, so that consumers do not re-run the project's geometry
backend to obtain it. A shape reloaded from a current artifact SHALL be
equivalent to the shape the node would render.

Loaded shapes SHALL be cached in memory per artifact and modification time,
evicting a stale entry for the same artifact, in the manner of the existing
base-mesh and Manifold caches.

Measurements DERIVED from a loaded shape and independent of where it is
placed — its own bounding box, and the bounding boxes of its faces — SHALL be
cached under that same shape identity, computed at most once per identity, and
evicted with it when its artifact is rebuilt. A shape with no such identity —
one composed for a single comparison, or read from a node whose artifact is
not current — SHALL be measured directly and SHALL NOT be cached, so a stale
identity can never serve another shape's measurement.

Because such a measurement is served under an identity that names only the
artifact and its modification time, it SHALL be a function of the shape's
EXACT geometry alone. A face's cached bounding box SHALL enclose that face's
exact surface and SHALL NOT be derived from any triangulation the shape may
carry, so that attaching, replacing or discarding a tessellation cannot change
a measurement already served under that identity.

#### Scenario: A current artifact is reused

- **WHEN** an exact node's shape is requested and its artifact is current
- **THEN** the shape is read from the artifact and the geometry backend does
  not render the node

#### Scenario: A rebuilt artifact replaces its cached shape

- **WHEN** an exact node's source changes and its artifact is rebuilt
- **THEN** the next request returns the new shape and the entry cached under
  the previous modification time is evicted

#### Scenario: A shape's face bounds are measured once and evicted with it

- **WHEN** the bounding boxes of a loaded shape's faces are requested
  repeatedly, and then its artifact is rebuilt
- **THEN** they are computed once for that identity and served from the cache
  afterwards, and the rebuild drops the entry so the next request measures the
  new shape

#### Scenario: A shape with no identity is measured directly

- **WHEN** the bounding boxes of the faces of a shape with no cache identity
  are requested
- **THEN** they are computed from that shape and no cache entry is created

#### Scenario: A triangulation does not shrink a face's bounds

- **WHEN** a curved exact shape carries a triangulation whose vertices lie on
  its surface, and its faces' bounding boxes are requested
- **THEN** each box still encloses the exact surface, reaching the true extent
  of the curved face rather than the tessellation's inscribed extent
