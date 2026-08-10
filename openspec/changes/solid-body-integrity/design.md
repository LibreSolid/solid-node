## Context

The archived `connectivity-contracts` change (2026-08-09) introduced a `bodies`
class attribute, `verify_bodies()`, and a builder sweep holding every declaring
node to its count. The motivating failures were real — parts that arrived in
pieces, all watertight, all green — but the mechanism landed wrong in two ways
that only became visible under an animated model.

`AbstractBaseNode.mesh` is deliberately world-framed: it composes the node's own
operations and every ancestor's into one matrix (ADR-028) so mesh and viewer
placement share one semantics. `verify_bodies()` reused it. During a build no
keyframe is set, so `AssemblyNode.time` returns solid2's symbolic `$t`, and any
operation an assembly authored holds an expression like `(360 * $t)`. Composing
the matrix calls `as_number()` on it and raises `TypeError`. Build-time body
verification therefore fails for every part any assembly animates — a whole
class of models, not an edge case.

Reproduced in the shop workspace at `projects/delme-claude`: a `GearPair`
assembly rotating two `SpurGear` leaves that declare `bodies = 1`. Counting
components directly on both built STLs gives 1 and 1. The build fails anyway,
on a check that never read the geometry.

The second problem is the declaration itself. Asking a node *how many* bodies
it may have makes multi-body a designable option and makes the contract opt-in,
so the default is no contract at all.

Relevant existing state:

- `AbstractBaseNode.rigid = True` (`base.py:206`), `AssemblyNode.rigid = False`
  (`assembly.py:59`); both `LeafNode.time` and `FusionNode.time` raise. `rigid`
  is already the framework's word for "solid, no time here".
- `InternalNode.as_scad` runs `self.rigid = self.rigid and child.rigid`
  (`internal.py:28`). That line exists solely to cope with an `AssemblyNode`
  under a `FusionNode` — the case this change forbids. Today it does not error:
  the fusion silently becomes non-rigid, produces no STL, and is skipped by
  every rigid-gated path, so a nonsense tree builds quietly.
- `InternalNode.validate` already rejects bad child types and runs per render.
- `trigger_stl` calls `assemble()` before any STL exists, and `generate_stl`
  raises `StlRenderStart` to unwind the whole build so the builder can wait on
  OpenSCAD and restart. STLs arrive across several builder passes.

Nothing in the framework, its examples, or any shipped project declares
`bodies` or nests a `FusionNode` over an `AssemblyNode`. The only users are
synthetic nodes in `tests/test_connectivity.py`.

## Goals / Non-Goals

**Goals:**

- Make "a solid is one connected body" unconditional, undeclarable, and
  enforced at the right unit.
- Make the check independent of animation, by never resolving an operation
  value to answer it.
- Enforce the structural rule that makes the unit well defined: fuse into a
  solid, then assemble solids.
- Keep the one connectivity claim the build cannot infer — that two named
  features weld, by at least a stated volume.

**Non-Goals:**

- Changing `node.mesh` semantics. World framing is correct for collision.
- Changing collision assertions, the adjacency sweep, the Manifold cache, or
  the AABB broad-phase.
- Reporting a stale `bodies` declaration as an error. It becomes an ordinary
  unused attribute; the framework says nothing about it.
- Supporting a part that is deliberately several separated solids. That is an
  assembly, and the framework already has one.

## Decisions

### The verified unit is the topmost rigid node, not the leaf

A leaf under a fusion may legitimately be several disconnected pieces — two
ribs the fusion later joins is ordinary modelling. Holding the leaf to one body
outlaws it. Holding only the outermost solid to one body is the real contract:
what gets printed as one part.

"Topmost rigid node" = a rigid node whose parent is non-rigid, or the root when
the root is rigid. A fusion inside a fusion is *not* checked; the outer fused
body is, as a whole.

*Alternative considered — check every rigid node.* Rejected: it forbids the
composition pattern fusion exists for.

*Alternative considered — check only leaves (the old
`assertNoDisconnectedParts` unit).* Rejected for the same reason, and it misses
the case that matters: a fusion whose children never met.

### Verification reads the local STL, with no operations applied

Geometry below a topmost rigid node is already composed into its STL by
`as_scad`, which unions the children's assembled scad — each child's own
operations included. Operations at or above the topmost rigid node are
placement of the whole body, and connected-component count is invariant under
rigid transform. So the correct input is the STL as built, untransformed.

This is what removes the failure rather than working around it: no matrix is
composed, so nothing can be an unresolved `$t`. It is also strictly cheaper —
the whole `_compose_world_matrix` path drops out of verification.

*Alternative considered — set a keyframe before verifying.* Rejected: it makes
a timeless property depend on an arbitrary instant, and would have to pick one.

*Alternative considered — compose only the node's own operations.* Rejected:
provably cannot change the answer, so it is cost without meaning, and it
reintroduces the `$t` dependency for exactly the driven nodes that broke.

### Verification stays in the builder, after artifacts are current

The natural reading — "verify as the build reaches the assembly, before
applying its operation" — is not implementable. `assemble()` runs before STLs
exist, and STL generation unwinds the build. The builder's existing placement,
on both publication paths, is already correct; only the walk and the mesh
source change. The sweep descends until it hits a rigid node, checks it, and
does not descend further.

### The fusion hierarchy is enforced in `validate()`, and `rigid` becomes static

`FusionNode` rejects a non-rigid child during render validation, where child
types are already checked and before geometry is produced. With that rule,
`self.rigid = self.rigid and child.rigid` can never change an outcome — the
only non-rigid node is `AssemblyNode`, which is already statically non-rigid,
and it can no longer sit under a fusion. The line is removed and `rigid` is
read from the type. That is what makes "topmost rigid node" computable from the
tree's shape without rendering anything.

This amends ADR-003, which chose rigidity propagation. Propagation is replaced
by a structural constraint that makes the propagated case illegal.

*Alternative considered — keep propagation and let a fusion-over-assembly stay
silently non-rigid.* Rejected: it is the current behaviour, it builds a
meaningless tree without complaint, and it leaves "topmost rigid node"
dependent on render results.

### Three assertions go; `assertJoined` stays and becomes solid-local

`assertOneBody`, `assertBodyCount` and `assertNoDisconnectedParts` assert a
property the build now guarantees structurally, at a better unit, on every
publish. They are removed rather than kept as redundant belt-and-braces,
because `assertBodyCount` in particular teaches the mistake this change is
correcting.

`assertJoined` is a different kind of claim and survives:

- One body overall does not imply any particular pair is joined. A fusion of
  five features can be one connected component while the two the designer cared
  about reach each other only via a detour through the other three. The build
  passes; `assertJoined(rib, boss)` is how you say *the rib must reach the
  boss*.
- `min_weld_volume` is not topological. A 0.001 mm³ overlap unions into one
  body, passes every connectivity check, and snaps off the printer. Only the
  designer knows how much weld the joint needs.

Because it is a connectivity claim, it must be frame-local: it composes
operations up to the nearest enclosing rigid node and stops. Today it reads
`node.mesh` and walks to the root, working only because the test runner sets a
keyframe first — the same latent defect as the build check.

The governing distinction, stated once so it is not re-derived:

- **Connectivity** — is this one part? Local, timeless. Compose up to the
  enclosing solid, no further.
- **Collision** — do these two parts clash? World-framed, time-dependent.
  `node.mesh` is right, and stays.

## Risks / Trade-offs

- [A project declaring `bodies` loses a check it was relying on] → The build
  now checks more, not less: unconditional instead of opt-in. The only capability
  lost is declaring a count other than one, which is the thing being removed on
  purpose. No known project declares one.
- [Verification now reads an STL for every topmost rigid node, where before it
  read none unless a project opted in] → Bounded by the number of printed parts,
  served by the existing `_cached_base_mesh` cache keyed on `(path, mtime)`, and
  with no boolean or transform work. The old path was cheaper only because it was
  usually disabled.
- [Enforcing fusion-over-assembly could break an unknown external project] →
  Nothing in the repository does it, and the rejected arrangement produces no STL
  today, so a project relying on it is already getting nothing. The exception
  names the fusion and the child and says what to do instead.
- [Removing three public assertions is a breaking API change] → They are
  removed by an explicit ratified decision with a migration note, not deprecated
  silently. `solid-node` is pre-v0.4 and the assertions shipped in the
  2026-08-09 change; exposure is small.
- [Composing "up to the enclosing rigid node" needs a helper that stops at a
  boundary, near-duplicating `_compose_world_matrix`] → Implement one matrix
  composer parameterised by its stop condition and express both world and
  solid-local framing through it, rather than a second walker that can drift.

## Migration Plan

1. Delete every `bodies` declaration from project source. There is no
   replacement; the attribute simply stops meaning anything.
2. Delete calls to `assertOneBody`, `assertBodyCount` and
   `assertNoDisconnectedParts`. Where a test meant "these two features weld",
   use `assertJoined`.
3. A part that is genuinely several separated solids becomes several solids
   under an `AssemblyNode`.
4. A `FusionNode` containing an `AssemblyNode` must be restructured: fuse the
   solids first, then assemble the results.

No rollback path is needed beyond reverting the change; nothing persists state
across it.

## Open Questions

None outstanding. Ratification is requested before implementation begins; the
ADR is drafted alongside this design (per the framework's ADR discipline, which
treats an ADR written alongside a pre-ratified proposal as the normal flow) and
is promoted into `docs/adrs/` with the implementation commit.
