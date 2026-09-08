# flexible-parts Specification

## Purpose
TBD - created by archiving change flexible-leaf-node. Update Purpose after archive.
## Requirements
### Requirement: A flexible part is a leaf whose shape is a function of its ports

The system SHALL provide an abstract flexible leaf kind, `FlexibleNode`:
a non-rigid leaf whose geometry at any instant is a pure function of the
values bound to its declared ports. A flexible leaf SHALL declare one
port per shape parameter, with the port's attribute name naming the
parameter; the parent assembly connects those ports in its `render()`,
exactly as it connects any port. The flexible leaf SHALL NOT read
animation time or driver state directly — `time` access raises as on any
leaf — and SHALL NOT accept per-instant parameter values through its
constructor. Constructor arguments remain structural: they may change
what `render()` returns and therefore the artifact identity, never the
per-instant binding.

After `render()` returns, the system SHALL check the rendered shape's
parameter names against the declared ports in both directions: a shape
parameter with no matching port, or a port naming no shape parameter,
SHALL fail with an error naming the node, the offending name, and both
name sets. Evaluating or serializing a flexible leaf with an unbound
port SHALL fail with an error naming the node and the port, never by
inventing a default.

#### Scenario: Shape follows the driver snapshot

- **WHEN** a flexible leaf's port is connected to an expression over a
  declared driver and two different numeric snapshots are bound
- **THEN** the leaf evaluates two different meshes, and repeated
  evaluation under one snapshot is deterministic

#### Scenario: Identity is structural

- **WHEN** one no-argument flexible leaf class is instantiated twice
  under different port bindings
- **THEN** both instances share one `uniq_id`; a differing structural
  constructor argument, by contrast, yields distinct identities

#### Scenario: A parameter without a port is rejected

- **WHEN** a flexible leaf renders a shape naming parameter `height`
  and declares no port named `height`
- **THEN** assembly fails naming the node, `height`, and the two name
  sets

#### Scenario: An unbound port is loud

- **WHEN** a flexible leaf is evaluated with a port no parent bound
- **THEN** the failure names the node and the port

### Requirement: A flexible leaf is non-rigid and cannot be fused

A flexible leaf SHALL report `rigid = False` while remaining a leaf. It
SHALL be rejected by a `FusionNode` during render validation with the
existing non-rigid-child error, SHALL raise on `stl` access like any
non-rigid node, SHALL never produce a cached rigid artifact, and SHALL
NOT be a topmost rigid node or join the printed-piece inventory.

#### Scenario: A spring cannot be fused

- **WHEN** a `FusionNode.render()` returns a flexible leaf among its
  children
- **THEN** validation raises naming the fusion and the flexible leaf,
  and no geometry is produced

#### Scenario: Not a printed piece

- **WHEN** a project containing a flexible leaf publishes its piece
  inventory
- **THEN** the flexible leaf contributes no piece and no model

### Requirement: The molejo adapter

The system SHALL provide `MolejoNode`, a flexible leaf adapter whose
`render()` returns a molejo `Shape` authored with molejo's Python
constructors, validated by the adapter `namespace` mechanism
(`molejo`). The embedded document form SHALL be the shape's own
serialization, and mesh evaluation SHALL be molejo's Python evaluator
over the spec plus the resolved port values — fixed declared
tessellation, parameter-independent vertex count and ordering. The
adapter SHALL surface molejo's own evaluation failures verbatim rather
than wrapping them silently.

#### Scenario: The backend object is the render contract

- **WHEN** a `MolejoNode.render()` returns an object outside the
  `molejo` namespace
- **THEN** namespace validation rejects it naming the node

#### Scenario: The mesh is molejo's evaluation

- **WHEN** a molejo leaf is evaluated at a bound snapshot
- **THEN** its mesh has exactly the vertex count molejo's declared
  tessellation implies and matches molejo's evaluation of the same
  spec and values

### Requirement: Snapshot artifacts on the SCAD path

`as_scad()` on a flexible leaf whose ports are all bound numerically
SHALL evaluate the shape at that binding and import the resulting
snapshot STL, keeping the assembled SCAD document complete for the
OpenSCAD GUI as a snapshot camera (never animation). The snapshot
artifact's name SHALL include a hash of the resolved parameter values
beside the node's `uniq_id`; within one binding the artifact
participates in normal mtime currency, and a different binding is a
different artifact. Unreferenced snapshots SHALL be collected by the
existing post-build sweep. The loader's binding of declared driver
defaults makes the driver-fed build path well-defined.

Where a port is bound to an expression over animation time, there is no
instant to photograph: animation time is the one value nothing binds on
this path, because an assembly nobody keyframed animates symbolically by
contract (ADR-008). `as_scad()` SHALL then emit no geometry for that
leaf, write no snapshot artifact, and allow assembly to proceed, rather
than failing the build or choosing an instant on the author's behalf.
The framework SHALL NOT substitute a value for animation time to
manufacture a snapshot.

This exemption SHALL be confined to animation time. A port that is
unbound, or bound to a symbolic value that does not involve animation
time — a raw driver token, which the loader's binding of declared
defaults should already have resolved — SHALL still fail loudly, naming
the node, the port, and the expression or the connection that would bind
it. A part with no instant and a part nobody wired are different things
and SHALL be reported differently.

Emitting no geometry SHALL be confined to the `.scad` path: it SHALL
NOT alter the published document, whose `params` carry the port's
symbolic expression — the expression itself, never the constant an
instant computed — for the consumer to evaluate per frame, and SHALL
NOT alter any numerically bound evaluation, mesh, or exact answer. Where
a `params` expression shares a subexpression with another expression of
the same document, it SHALL be published as a reference into the
document's `bindings` table, exactly as an operation's expression is: what
the guarantee preserves is the value the consumer evaluates, not the text
it is written in.

#### Scenario: Same binding, no re-evaluation

- **WHEN** a molejo leaf is re-assembled at an unchanged binding with a
  current snapshot artifact
- **THEN** no evaluation runs and the same SCAD import is returned

#### Scenario: New binding, new artifact

- **WHEN** the bound snapshot changes and the node is re-assembled
- **THEN** a snapshot artifact under a different binding hash is
  written, and a later successful build sweeps the unreferenced one

#### Scenario: A time-fed flexible part assembles without a snapshot

- **WHEN** a flexible leaf's port is bound to an expression over
  animation time and the tree is assembled on the build path
- **THEN** assembly succeeds, the leaf contributes no geometry to the
  assembled SCAD, no snapshot artifact is written for it, and the build
  goes on to publish its document

#### Scenario: The published document is unaffected

- **WHEN** that same tree is published
- **THEN** the flexible leaf appears in the document with its `tech`,
  its spec, and `params` carrying the time-dependent expression rather
  than a constant, exactly as for a driver-bound leaf

#### Scenario: A shared parameter expression is published through the table

- **WHEN** a flexible leaf's `params` expression shares a subexpression with
  an operation elsewhere in the same document
- **THEN** that subexpression is published once as a `bindings` entry, the
  leaf's `params` value references it by name, and evaluating the table and
  then the parameter yields what the flat expression yielded

#### Scenario: An unbound port still fails loudly

- **WHEN** a flexible leaf whose port no `connect()` binds is assembled
- **THEN** it fails, naming the node, the port and the connection that
  would bind it, rather than emitting an empty leaf

#### Scenario: A symbolic binding that is not over time still fails loudly

- **WHEN** a flexible leaf's port carries a raw driver token on the SCAD
  path
- **THEN** it fails, naming the node, the port and the expression,
  rather than being exempted as a part without an instant

### Requirement: Exact evaluation through molejo's B-rep evaluator

`MolejoNode` SHALL be exact: `shape()` at a bound snapshot SHALL return
the closed OCCT solid molejo's B-rep evaluator constructs from the same
spec and values, carrying molejo's declared approximation tolerance for
sweeps that are not analytically representable. Exactness SHALL NOT
alter the mesh or SCAD output.

#### Scenario: A spring instant answers an exact question

- **WHEN** an exact assertion runs between a molejo spring at a bound
  snapshot and a rigid exact part
- **THEN** the decision is made on B-rep geometry through the exact
  path, not on meshes

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
