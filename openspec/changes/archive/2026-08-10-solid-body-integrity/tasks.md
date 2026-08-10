## 1. Fusion hierarchy and static rigidity

- [x] 1.1 Red: a `FusionNode` rendering an `AssemblyNode` child raises, naming
      the fusion and the child. Currently it silently becomes non-rigid.
- [x] 1.2 Red: a `FusionNode` over leaves and a nested fusion stays rigid, and
      its `rigid` is its type's — not recomputed from children.
- [x] 1.3 Implement the non-rigid-child rejection in `InternalNode.validate`
      (`internal.py`), scoped to `FusionNode`.
- [x] 1.4 Remove `self.rigid = self.rigid and child.rigid` from
      `InternalNode.as_scad` (`internal.py:28`).
- [x] 1.5 Green 1.1–1.2; confirm no other code path depended on propagation.

## 2. Topmost rigid node

- [x] 2.1 Red: given an assembly holding a fusion of leaves and a nested
      fusion, the topmost-rigid-node walk yields the outer fusion only —
      not the leaves, not the nested fusion, not the assembly.
- [x] 2.2 Red: a rigid root is its own topmost rigid node.
- [x] 2.3 Implement the walk: descend from the root, stop at and yield the
      first rigid node on each branch.

## 3. Remove the `bodies` declaration

- [x] 3.1 Red: `bodies`, `verify_bodies` and `DisconnectedBodyError` are absent
      from `solid_node.node.base`, and `FusionNode` declares no `bodies`.
- [x] 3.2 Remove `bodies` (`base.py:216`), `verify_bodies()` (`base.py:596`),
      and `DisconnectedBodyError`.
- [x] 3.3 Remove `bodies = 1` from `fusion.py`.
- [x] 3.4 Remove the declared-count tests from `tests/test_connectivity.py`.

## 4. Build verification at the topmost rigid node

- [x] 4.1 Red: a build whose topmost rigid node's STL has two components
      publishes nothing and writes the failure to `errors.json`, naming the
      node and the count.
- [x] 4.2 Red: the same on the already-current publication path.
- [x] 4.3 Red: a fusion joining two multi-piece leaves into one body passes,
      and neither leaf is checked.
- [x] 4.4 Red — the originating defect: a topmost rigid node driven by an
      animated assembly verifies without resolving any operation value.
      Must fail today with `TypeError: ... is not a number`.
- [x] 4.5 Rewrite `_verify_declared_bodies` (`builder.py:381`) as the
      topmost-rigid-node sweep, counting on the node's own STL with no
      operations applied, on both publication paths.
- [x] 4.6 Green 4.1–4.4.

## 5. Test-framework assertions

- [x] 5.1 Red: `assertOneBody`, `assertBodyCount` and
      `assertNoDisconnectedParts` are absent from the test case.
- [x] 5.2 Remove all three from `solid_node/test.py` (:413, :425, :467) and
      their tests.
- [x] 5.3 Red: `assertJoined` on two features whose enclosing solid is driven
      by an animated assembly reaches the same verdict at every instant, and
      composes no operation at or above the enclosing solid.
- [x] 5.4 Red: `assertJoined` fails for two features of a one-body fusion that
      meet only through a third feature.
- [x] 5.5 Introduce one matrix composer parameterised by its stop condition;
      express world framing and solid-local framing through it, leaving
      `node.mesh` world-framed and unchanged.
- [x] 5.6 Rebase `assertJoined` (`test.py:441`) and its `_intersection_stats`
      path on the solid-local frame; green 5.3–5.4.
- [x] 5.7 Confirm collision assertions, the adjacency sweep, the Manifold
      cache and the AABB broad-phase still use world meshes and still pass.

## 6. Validate against the originating project

- [x] 6.1 Run the full framework suite.
- [x] 6.2 Build `projects/delme-claude` against this worktree; it must build
      and publish, where it currently fails with `(360 * $t) is not a number`.
- [x] 6.3 Confirm both gear STLs are still verified as one body each, and that
      a deliberately fragmented variant is rejected.

## 7. Records

- [x] 7.1 Promote the drafted ADR into `docs/adrs/NODE/` as ADR-039 and add it
      to `docs/adrs/README.md` in order.
- [x] 7.2 Amend ADR-003: rigidity propagation superseded by the structural
      fusion-hierarchy constraint, with a dated amendment section and a link
      to ADR-039.
- [x] 7.3 Update `docs/architecture.md` where the synthesis changed.
- [x] 7.4 Update the narrative docs that mention body counts
      (`docs/testing.rst`, `docs/fusion.rst`) if they do.
- [x] 7.5 Sync delta specs into `openspec/specs/` and archive the change.
