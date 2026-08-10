# ADR-039: Solid integrity at the topmost rigid node

- **Status:** Proposed
- **Date:** 2026-08-10
- **Subsystem:** NODE
- **Change:** `solid-body-integrity`
- **Amends:** [ADR-003](../../../docs/adrs/NODE/ADR-003-rigid-vs-non-rigid-node-distinction.md)
- **Reverses (in part):** the `bodies` declaration introduced by
  `connectivity-contracts` (archived 2026-08-09)
- **Relates to:** [ADR-028](../../../docs/adrs/NODE/ADR-028-cached-base-meshes-and-single-matrix-world-composition.md),
  [ADR-008](../../../docs/adrs/NODE/ADR-008-time-based-animation-system-for-assemblies.md)

> Draft. Promoted to `docs/adrs/NODE/` with the implementation commit; the
> relative links above resolve from that location.

## Context

`connectivity-contracts` gave nodes a `bodies` attribute declaring how many
connected solids their mesh may have, and a builder sweep enforcing it. The
failures that motivated it were real: parts whose features never reached each
other, watertight and green and wrong. The mechanism was not.

`verify_bodies()` counted components on `AbstractBaseNode.mesh`, which by
ADR-028 is deliberately *world*-framed — the node's operations composed with
every ancestor's into one matrix, so mesh and viewer placement agree. But by
ADR-008 an assembly's operations are `$t` expressions, and during a build no
keyframe is set, so `AssemblyNode.time` yields the symbolic `$t`. Composing the
matrix calls `as_number()` on `(360 * $t)` and raises `TypeError`. Build-time
verification thus failed for every part any assembly animates.

Reproduced in `projects/delme-claude`: a `GearPair` rotating two `SpurGear`
leaves that declare `bodies = 1`. Both built STLs contain exactly one component.
The build failed anyway, on a check that never read the geometry.

Two errors compound here, and only one is the crash.

**Wrong question.** Asking a node *how many* bodies it may have makes multi-body
a designable property of a printed part, and makes the contract opt-in — so the
default was no contract at all. The only sound contract is that a solid is one
body.

**Wrong frame.** Connected-component count is invariant under rigid transform.
Applying a placement matrix to answer it is cost that cannot change the result,
and it was the sole source of the failure. Connectivity is local and timeless.
Only collision between separately placed parts is world-framed and
time-dependent.

**Wrong unit.** The old sweep held *every* declaring node, and the test-side
`assertNoDisconnectedParts` held every *leaf*. A leaf under a fusion may
legitimately be two ribs the fusion joins — that is what fusion is for. The
contract belongs to the part that gets printed, not to its ingredients.

A structural gap made the right unit hard to name. `InternalNode.as_scad`
propagated `parent.rigid = parent.rigid AND child.rigid` (ADR-003) precisely to
cope with an `AssemblyNode` under a `FusionNode`. That arrangement is
meaningless — you fuse into a solid, then assemble solids; you cannot fuse an
assembled thing — yet it did not error. The fusion silently went non-rigid,
produced no STL, and was skipped everywhere.

## Decision

**A solid is one connected body, unconditionally.** Remove `bodies`,
`verify_bodies()` and `DisconnectedBodyError`. Nothing is declared; nothing is
opt-in.

**A `FusionNode` may not contain a non-rigid node.** Enforced in render
validation, naming the fusion and the child, before geometry is produced. With
that rule, rigidity propagation can never change an outcome — `AssemblyNode` is
already statically non-rigid and can no longer sit under a fusion — so the
propagation line is removed and `rigid` is read from the node's type. This
amends ADR-003: propagation is replaced by a structural constraint that makes
the propagated case illegal.

**The verified unit is the topmost rigid node**: a rigid node whose parent is
non-rigid, or the root when the root is rigid. The build checks exactly these
and does not descend past one. A leaf, or a fusion nested inside a fusion, may
be several separated pieces so long as the enclosing solid joins them; the
outer fused body is checked as a whole.

**The count is taken from the node's own STL, with no operations applied.**
Geometry below a topmost rigid node is already composed into that STL by
`as_scad`. Operations at or above it are placement of the whole body. No world
matrix is composed, so no operation value needs resolving and an animated
subtree verifies exactly as a static one does.

**Verification stays in the builder, on both publication paths.** It cannot
move into `assemble()`: STLs do not exist there, and STL generation unwinds the
build. Only the walk and the mesh source change.

**One governing distinction, stated once:**

| | question | frame | time |
|---|---|---|---|
| Connectivity | is this one part? | up to the enclosing solid | invariant |
| Collision | do these parts clash? | world | per instant |

`node.mesh` keeps its ADR-028 world semantics, which are correct for collision.
Connectivity stops at the enclosing solid.

**Consequently, three test assertions go and one is reframed.**
`assertOneBody`, `assertBodyCount` and `assertNoDisconnectedParts` assert a
property the build now guarantees structurally at a better unit;
`assertBodyCount` additionally teaches the mistake being corrected.
`assertJoined` stays, because it makes a claim the build cannot infer — that
two *named* features reach each other (a solid can be one component while the
pair the designer cared about connect only by a detour through others), with a
required weld volume (a 0.001 mm³ overlap is topologically one body and snaps
off the printer). Being a connectivity claim, it is rebased on the solid-local
frame.

## Consequences

- The guarantee strengthens: unconditional where it was opt-in, and at the unit
  that corresponds to a printed part.
- The failure mode disappears rather than being worked around. The
  `_compose_world_matrix` path leaves verification entirely, so the check is
  also cheaper than the one it replaces.
- `rigid` becomes a static, type-determined fact, so the topmost rigid nodes are
  computable from the tree's shape without rendering.
- Breaking, three ways: a project declaring `bodies` must delete it; calls to
  the three removed assertions must go; a `FusionNode` over an `AssemblyNode`
  now raises. Nothing in the framework, its examples, or any shipped project
  does any of these — the only users are synthetic nodes in
  `tests/test_connectivity.py` — and the third arrangement already produced no
  STL, so a project relying on it was already getting nothing.
- Verification now reads one STL per printed part where it usually read none.
  Bounded by part count, served by the existing `(path, mtime)` base-mesh cache,
  with no boolean or transform work.
- A part that is genuinely several separated solids is an assembly. The
  framework has one; it is no longer expressible as a solid with a count.
- The solid-local frame needs a matrix composer parameterised by its stop
  condition, shared with the world composer rather than a second walker that can
  drift from it.

## Alternatives considered

**Keep `bodies`, fix only the crash by counting on the local mesh.** Removes the
`TypeError` and nothing else. Leaves the contract opt-in, leaves multi-body a
designable property, and leaves the unit wrong. Rejected: it repairs the symptom
by preserving the structure that produced it.

**Set a keyframe before verifying.** Makes the world matrix resolvable. Rejected:
it makes a timeless property depend on an arbitrary instant, and something must
choose the instant.

**Compose only the node's own operations.** Rejected: provably cannot change a
component count, so it is cost without meaning — and it reintroduces the `$t`
dependency for exactly the assembly-driven nodes that broke, since those
operations live in the driven node's own list.

**Check every rigid node, not just the topmost.** Rejected: it forbids the
composition pattern fusion exists for — a leaf that is two ribs joined by its
fusion is ordinary modelling.

**Check leaves, as `assertNoDisconnectedParts` did.** Rejected for the same
reason, and it misses the case that matters most: a fusion whose children never
met.

**Keep rigidity propagation and allow a silently non-rigid fusion.** The current
behaviour. Rejected: it builds a meaningless tree without complaint, and it
leaves "topmost rigid node" dependent on render results instead of tree shape.

**Keep the three assertions as redundant belt-and-braces.** Rejected: a project
can no longer reach a state in which they fail, and keeping `assertBodyCount`
keeps teaching that a solid may legitimately be several pieces.

## References

- `solid_node/node/base.py` — `bodies`, `verify_bodies()`, `mesh`,
  `_compose_world_matrix`
- `solid_node/node/internal.py` — rigidity propagation, `validate()`
- `solid_node/node/fusion.py` — `bodies = 1`, `time` guard
- `solid_node/core/builder.py` — `_verify_declared_bodies()`
- `solid_node/test.py` — the connectivity assertions
- Originating evidence: `projects/delme-claude` (shop workspace)
