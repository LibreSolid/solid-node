## ADDED Requirements

### Requirement: Broad-phase work adapts to sparse orientation without changing candidates or order

For a set of conservative world AABBs, the spatial index SHALL estimate active-interval pressure on X, Y, and Z in bounded `O(N log N)` work and SHALL use the least-pressure axis for candidate discovery, tie-breaking X then Y then Z. Touching, degenerate, coincident, contained, and rotated conservative bounds SHALL retain the inclusive overlap semantics of the existing X sweep.

The emitted candidate set and order SHALL equal the existing X-axis sweep: each pair is canonicalized by input index, and accepted pairs are ordered by current-X-order rank then active-X-order rank. The implementation MAY buffer sparse accepted candidates only up to a finite internal limit. If that limit is reached, it SHALL discard the adaptive result and stream the existing X sweep so a dense true-overlap case does not retain `O(N²)` pair memory. Every emitted candidate SHALL still reach the selected narrow phase; the adaptive index SHALL NOT decide geometry or change exact/faceted routing.

#### Scenario: Unfavourable X orientation uses a sparse axis

- **WHEN** 1,024 disjoint boxes overlap along X but are separated along Y or Z
- **THEN** the index chooses a lower-pressure axis, emits no candidates, and does not construct or scan all `N * (N - 1) / 2` pairs

#### Scenario: Candidates and order match the current sweep

- **WHEN** adversarial and randomized bound sets include touching, zero extent, containment, coincidence, rotation, and input permutations
- **THEN** the adaptive path emits exactly the same canonical pairs in the same order as the current X sweep, and that set includes every exhaustive AABB overlap

#### Scenario: Dense candidates fall back to streaming

- **WHEN** true AABB overlaps fill the bounded candidate buffer
- **THEN** the index streams the current X sweep with bounded auxiliary memory and preserves its candidate order

### Requirement: Static-equilibrium storage is sparse and mathematically equivalent

The static-equilibrium phase of `assertAssemblySupported` SHALL express the same deterministic linear program required by the whole-assembly gravity support contract using sparse equality-matrix storage. It SHALL preserve variable and row order, targets, per-row tolerances, bounds, objective, HiGHS method, and elastic-slack interpretation. When several contributions address one cell, the coefficient builder SHALL accumulate them in the same nested-loop order as the current dense `+=` formulation before emitting one sparse value; it SHALL NOT delegate duplicate floating additions to an order-changing sparse coalescer. It SHALL use sparse slack identity blocks and SHALL NOT allocate a dense `rows × variables` coefficient matrix or dense `rows × rows` identity blocks.

For an equilibrium system, sparse storage SHALL produce the same feasibility result, optimized slack within the existing numerical contract, ordered body diagnostics, and force-versus-torque classification as the dense formulation. Memory required to construct the program SHALL scale with stored non-zero coefficients plus its row and column vectors, rather than with the square of free-body count solely because of slack identities.

#### Scenario: Existing statics verdicts are unchanged

- **WHEN** every existing balanced, unbalanced, counterweighted, cantilevered, declared-support, margin, and deterministic-repeat fixture is solved through sparse input
- **THEN** it produces the same pass/fail result and ordered diagnostic classification as the characterized dense formulation

#### Scenario: Duplicate contributions accumulate identically

- **WHEN** multiple contacts or declared-wrench terms contribute to the same matrix cell
- **THEN** the sparse coefficient equals the dense formulation's repeated `+=` result

#### Scenario: Near-tolerance diagnostics agree

- **WHEN** a generated small system places force or torque slack on either side of an existing tolerance boundary
- **THEN** sparse and dense reference formulations classify each body and balance kind identically

#### Scenario: A large sparse system allocates no dense slack blocks

- **WHEN** a representative system has 1,000 free bodies and sparse contacts
- **THEN** program construction uses sparse coefficient and identity structures, with no allocation proportional to `576 * F²` bytes for the two slack identities

## MODIFIED Requirements

### Requirement: An exact placement is computed once per shape and matrix

On the exact path, the placed shape and the local bounding box a comparison needs SHALL be reused by their exact identities, in the same spirit as the per-STL Manifold cache. A placement SHALL be computed once per `(shape identity, exact matrix bytes)` while its cache entry is retained. Placed-shape retention SHALL be access ordered and limited to a finite internal number of entries. A hit SHALL reuse its placed shape; insertion beyond the limit SHALL dispose the least-recently-used cache entry. A later lookup for an evicted placement SHALL recompute it exactly and MAY retain it under the same bound, even if another caller still holds the previously returned placed object.

Placement caching and eviction SHALL NOT change the geometry or verdict any comparison sees: a cached or recomputed placed shape SHALL be the shape the kernel produces for that exact matrix, no tolerance or rounding SHALL enter the key, and a shape rebuilt under a new identity SHALL NOT be served a placement built from the old one. A shape with no stable identity SHALL remain uncached. Local bounding-box caching SHALL remain tied to current shape identity and disposed when that identity is replaced.

The exact module SHALL own the bounded cache. A fresh build/develop process SHALL begin empty and disposal of that process SHALL dispose its cache. The test manager SHALL clear run caches when establishing a new comparison run. Direct in-process callers MAY share only the current interpreter's bounded cache and internal isolation tests SHALL be able to reset it.

#### Scenario: One retained placement serves repeated comparisons

- **WHEN** the same solid is placed by the same matrix for several comparisons while its entry remains in the working set
- **THEN** the placement is constructed once and the later comparisons reuse it

#### Scenario: A different placement is constructed

- **WHEN** the same solid is placed by a different exact matrix
- **THEN** a placement for that matrix is constructed and used

#### Scenario: A long changing trajectory plateaus

- **WHEN** one shape is placed at more distinct transforms than the internal limit
- **THEN** retained placed-shape entries never exceed the limit and old entries are disposed in least-recently-used order

#### Scenario: An evicted placement recomputes without changing verdict

- **WHEN** a transform is requested after its placement entry was evicted
- **THEN** the exact transform is recomputed and every Boolean result equals an uncached evaluation at that matrix

#### Scenario: A useful working set still hits

- **WHEN** a long run cycles among fewer distinct shape/matrix keys than the internal limit
- **THEN** each placement is constructed once after warm-up and later requests hit the bounded cache
