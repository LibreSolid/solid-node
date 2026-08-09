## 1. Counting bodies

- [x] 1.1 Red: two disjoint closed shells are watertight and have positive
      volume — the premise the rest of the change rests on.
- [x] 1.2 Add `_body_count`, splitting with `only_watertight=False` so a
      fragment that is itself closed still counts as a body.

## 2. Connectivity assertions

- [x] 2.1 Red: `assertOneBody` fails on a node whose features never reached
      each other, naming the node and its body count, and passes a single
      solid.
- [x] 2.2 Red: `assertBodyCount` names both the expected and the actual count
      on failure.
- [x] 2.3 Red: `assertJoined` fails two solids meeting exactly on a face
      without overlapping, and passes genuinely overlapping features.
- [x] 2.4 Red: `assertJoined` fails a weld below `min_weld_volume` and passes
      one above it.
- [x] 2.5 Red: `assertNoDisconnectedParts` fails when one leaf anywhere in the
      tree has fragmented, passes an all-single-body tree, respects a leaf that
      declares a legitimate count, and still enforces that declared count.
- [x] 2.6 Implement the four assertions in `solid_node/test.py`.

## 3. Declared body counts on nodes

- [x] 3.1 Red: `AbstractBaseNode` declares no count by default and
      `FusionNode` declares one body.
- [x] 3.2 Red: `verify_bodies()` passes a single body, raises
      `DisconnectedBodyError` on a fragmented result, and skips an undeclared
      node and a non-rigid node without reading their meshes.
- [x] 3.3 Implement `bodies`, `verify_bodies()` and `DisconnectedBodyError` in
      `solid_node/node/base.py`, and `bodies = 1` in `solid_node/node/fusion.py`.

## 4. Build-time verification

- [x] 4.1 Red: a build whose node violates its declared count publishes no
      viewer snapshot and reports through `errors.json`.
- [x] 4.2 Red: the already-current publication path performs the same check and
      republishes nothing on violation.
- [x] 4.3 Implement `_verify_declared_bodies()` and call it before
      `_write_viewer_snapshot()` on both publication paths.
- [x] 4.4 Confirm the lifecycle tests exercise the real `verify_bodies`, not a
      no-op stand-in, so the undeclared-node fast path stays honest.

## 5. Whole-system checks

- [x] 5.1 Run the full framework test suite.
- [x] 5.2 Verify against the three real defects — the windmill fan, the
      selector fork, the selector gate — and confirm each goes red with its
      body count named.
- [x] 5.3 Sync the baseline specs for `test-framework`, `node-model` and
      `build-pipeline`.
