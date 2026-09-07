## MODIFIED Requirements

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
