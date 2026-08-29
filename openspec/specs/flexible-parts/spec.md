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
symbolic expression verbatim for the consumer to evaluate per frame,
and SHALL NOT alter any numerically bound evaluation, mesh, or exact
answer.

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
  its spec, and `params` carrying the time-dependent expression
  verbatim, exactly as for a driver-bound leaf

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

