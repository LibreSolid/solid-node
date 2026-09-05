## ADDED Requirements

### Requirement: An intersection verdict is computed once per run

The shared `(is_empty, volume)` helper SHALL answer from a per-run cache when
it is asked a comparison it has already decided, and SHALL compute a verdict
only for a comparison it has not.

A comparison's cache key SHALL identify everything the verdict depends on and
nothing else:

- the identity of each compared solid's geometry, under the same
  `(file, mtime)` identity the per-STL cache already uses, so a rebuilt part
  is a different key rather than a stale hit;
- the pair's RELATIVE placement — one node's composed world matrix inverted
  and applied to the other's;
- the evaluation path taken (exact, faceted, or the `.mesh` fallback), so a
  pair is never served an exact answer from a faceted entry or the reverse.

The relative placement is sufficient because intersection emptiness and volume
are invariant under a common rigid transform: two solids moved together share
exactly the volume they shared before. A repeated key is therefore provably
the same verdict, and reusing it SHALL NOT change any assertion's outcome,
message, or epsilon semantics. This is a recomputation shortcut of the same
kind as the AABB broad phase, not a new tolerance.

The cache SHALL be keyed independently of which assertion asked, so the
animation sweep, the pairwise sweep, the whole-assembly interference
assertion and the perturbation assertions share one another's answers for the
same pair in the same relative placement.

A node whose geometry has no stable identity — a test double exposing only
`.mesh`, or a flexible leaf evaluating its current binding — SHALL NOT be
cached, and its comparisons SHALL be computed exactly as they are today.

#### Scenario: A repeated comparison is not recomputed

- **WHEN** an assertion compares the same two solids in the same relative
  placement a second time within one run
- **THEN** the verdict returned equals the first verdict exactly, and no
  boolean is run by either kernel

#### Scenario: A moved pair is recomputed

- **WHEN** two solids are compared, then one is placed differently relative
  to the other, and they are compared again
- **THEN** the second comparison runs its boolean and returns the verdict for
  the new placement

#### Scenario: A pair moved together is not recomputed

- **WHEN** two solids are compared, then BOTH are placed by the same
  additional rigid transform and compared again
- **THEN** the verdict is served from the cache and equals the first verdict

#### Scenario: A rebuilt part invalidates its entries

- **WHEN** a solid's geometry file is rebuilt and a comparison that involved
  it is repeated
- **THEN** the comparison is recomputed against the new geometry

#### Scenario: Flush contact keeps its verdict through the cache

- **WHEN** a flush abutment that reports non-empty with exactly 0.0 mm³ is
  compared twice
- **THEN** both comparisons report non-empty with 0.0 mm³, and the strict
  `volume_epsilon=0` default still reports the foul

#### Scenario: A node without stable geometry identity is not cached

- **WHEN** a comparison involves a node exposing only `.mesh`
- **THEN** the comparison is computed as it is today and no cache entry
  serves a later comparison in its place

### Requirement: An exact placement is computed once per shape and matrix

On the exact path, the placed shape and the local bounding box a comparison
needs SHALL each be computed once per `(shape identity, matrix)` and reused,
in the same spirit as the per-STL Manifold cache.

Placement caching SHALL NOT change the geometry any comparison sees: a cached
placed shape SHALL be the shape the kernel would have produced for that
matrix, and a shape rebuilt under a new identity SHALL NOT be served a
placement built from the old one.

#### Scenario: One placement serves repeated comparisons

- **WHEN** the same solid is placed by the same matrix for several
  comparisons in one run
- **THEN** the placement is constructed once and the later comparisons reuse
  it

#### Scenario: A different placement is constructed

- **WHEN** the same solid is placed by a different matrix
- **THEN** a placement for that matrix is constructed and used
