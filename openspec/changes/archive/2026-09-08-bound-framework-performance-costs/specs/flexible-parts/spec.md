## ADDED Requirements

### Requirement: Flexible faceted geometry has a bounded multi-binding working set

During a test run the system SHALL reuse a flexible leaf's evaluated base mesh, local bounds, and admitted Manifold for repeated faceted reads of the same geometry-definition/source identity, structural node identity, and binding. Several simultaneously useful bindings MAY coexist, but the working set SHALL have a finite internal entry limit and access-ordered eviction. Rebinding among a working set smaller than the limit SHALL reuse one construction per distinct key; a long sequence of unique bindings SHALL NOT grow retained entries beyond the limit.

The correctness key SHALL use full, non-truncated values: flexible technology; defining project source/module identity and full current source fingerprint/digest; the full canonical structural identity from which `uniq_id` is shortened; exact canonical sorted binding values from which `binding_hash` is shortened; and a full digest of the current serialized flexible shape/spec. Same-named or same-`uniq_id` classes from different source definitions, different values sharing a shortened hash, and different specs SHALL NOT share geometry. A source/spec identity change SHALL cause a miss and current-shape evaluation. An evicted binding MAY be evaluated again and SHALL produce the same geometry as uncached evaluation.

This cache SHALL contain reusable faceted geometry, not intersection verdicts. A comparison involving a flexible node SHALL still execute the selected exact or faceted Boolean for the current binding. The existing `FlexibleNode` per-instance last-binding exact `(shape, tolerance)` memo SHALL remain separate and unchanged; this requirement SHALL NOT add cross-instance exact-shape reuse.

#### Scenario: Interleaved useful bindings build once each

- **WHEN** many identical flexible instances at one assembly instant alternate among three source-equal bindings and the working-set limit exceeds three
- **THEN** faceted geometry is constructed three times, later reads reuse the matching mesh/bounds/Manifold, and every returned volume and admission verdict equals uncached evaluation

#### Scenario: Same structural id from another source does not collide

- **WHEN** two flexible definitions have the same structural `uniq_id` and binding but different defining source/module identity
- **THEN** each evaluates and caches its own faceted geometry

#### Scenario: Short-hash collisions do not share geometry

- **WHEN** test-controlled structural or binding hash shortening makes two different full identities produce the same twelve-hex value
- **THEN** their flexible faceted geometry occupies distinct correctness keys and each returns its own mesh, bounds, and Manifold

#### Scenario: A source edit invalidates flexible geometry reuse

- **WHEN** a flexible definition's observable source identity changes while its structural id and binding remain equal
- **THEN** the next faceted read evaluates current geometry and cannot return the prior source generation's cached mesh or Manifold

#### Scenario: A long trajectory stays bounded

- **WHEN** a test reads more unique flexible bindings than the internal limit
- **THEN** retained faceted-geometry entries never exceed that limit, least-recently-used entries are disposed, and revisiting an evicted binding recomputes correct geometry

#### Scenario: Flexible verdicts remain uncached

- **WHEN** a flexible pair is compared twice at one binding after its geometry is reused
- **THEN** each comparison still runs the selected Boolean and reaches its own verdict from the current geometry

#### Scenario: Exact last-binding behavior is unchanged

- **WHEN** one flexible instance is asked twice for exact shape and tolerance at one binding and then at another
- **THEN** its first binding is evaluated once, the second binding replaces that instance's exact memo, and no other instance receives the exact result
