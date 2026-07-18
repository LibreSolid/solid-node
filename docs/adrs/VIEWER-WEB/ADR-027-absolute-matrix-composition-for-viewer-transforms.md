# ADR-027: Absolute World-Matrix Composition for Viewer Transforms

**Status:** Accepted
**Date:** 2026-07-17
**Depends on:**
- [ADR-012: Three.js for 3D Mesh Rendering and Visualization](./ADR-012-threejs-for-3d-rendering.md)
- [ADR-023: Kinematic Operations Model and Driver-Tagged Idempotent Renders](../NODE/ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)

**Related to:**
- [ADR-022: Cross-Runtime Degree-Trig Parity for `$t` Expression Evaluation](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)

## Context and Problem Statement

ADR-023 established a **one-transform, three-consumers** parity contract: an operation must render identically through `.scad()` (OpenSCAD build output), `.mesh()` (the trimesh meshes ADR-009 assertions consume), and `.serialized` (the wire form the browser evaluates, per ADR-022). The backend semantics that contract fixes are precise: **every rotation is about the world axis through the origin, every translation is in world space, and later operations apply outermost.** Under those semantics the pose of a leaf is the ordered product of its own operations and every ancestor's, folded into world coordinates.

The web viewer was the consumer that quietly failed to honor this. It applied each operation of the flattened chain **incrementally** to the Three.js mesh — `applyQuaternion` for each rotation, `mesh.position.add` for each translation — and, before every re-render, undid the whole chain with a mirror-image, reverse-iteration `unapplyOperations` pass. That incremental scheme agrees with the backend's world-space, outermost-last semantics **only while every rotation in the chain precedes every translation**: a rotation applied after a translation, in the incremental model, spins the mesh about its own current position rather than carrying that already-translated position around the world origin.

The V8-engine `CylinderUnit` broke exactly that assumption. An assembly-level rotation sitting *above* already-translated children should carry each piston onto its 45-degree bank; in the browser each piston instead spun in place. The trimesh tests were correct — only the viewer diverged. This is precisely the per-consumer **silent divergence** risk ADR-023 names: a transform definition that is honored by two consumers and quietly mis-honored by the third.

## Decision Drivers

- **Uphold ADR-023 parity in the browser consumer.** The viewer must reproduce the same world pose as `.mesh()` and `.scad()` for **arbitrary** operation orderings, not just rotations-before-translations.
- **World-space, outermost-last semantics.** Rotations about the world origin, world-space translations, later operations outermost — matching the backend exactly.
- **Idempotent re-render.** `setContext` recurses into every node and re-triggers its subtree; re-rendering the same declared state repeatedly must reproduce the pose, never accumulate.
- **Eliminate the mirror-image undo.** A scheme that mutates and then carefully reverses its own mutation is fragile: any asymmetry between the apply pass and the undo pass corrupts the pose.

## Considered Options

1. **Incremental per-operation apply / mirror-image undo** — the shipped prior design.
2. **Absolute world-matrix recomposition** — fold the whole chain into one `THREE.Matrix4` from scratch each render (chosen).

## Decision Outcome

Chosen: **absolute world-matrix composition** (landed in solid-node commit `23bd5e1`, "Web viewer: compose operations into an absolute world matrix (improvements.md #23)").

A pure, exported `composeOperations(operations)` folds the node's operation levels — level 0 is the node's own operations, each deeper level is an ancestor's operations, exactly the shape `Node.operations` holds after `setOperations` cascades down the tree — into a single `THREE.Matrix4`. Each op's matrix is **premultiplied** in encounter order, so the composed transform is `world = M_opk · … · M_op1` (later operations outermost). Rotations become `makeRotationAxis` on the normalized axis with the angle converted from degrees to radians; translations become `makeTranslation`.

`applyOperations` sets this matrix directly on the mesh:

```
this.mesh.matrixAutoUpdate = false;
this.mesh.matrix.copy(composeOperations(this.operations));
this.mesh.matrixWorldNeedsUpdate = true;
```

Because the world matrix is recomposed from scratch out of `this.operations` every time, `applyOperations` is **idempotent** — redundant calls (e.g. `setContext` recursing into a node that then re-triggers its own subtree) simply recompute the same matrix. This made all undo bookkeeping unnecessary: `unapplyOperations` and its reverse-iteration undo logic were deleted entirely, `setContext`'s former unapply/reapply pair collapsed to a single recompose, and the redundant undo/redo that its node-then-subtree recursion previously required disappeared.

## Pros and Cons of the Options

### Incremental per-operation apply / mirror-image undo (rejected)

- Good: never builds an explicit matrix; leans on Three.js `quaternion`/`position` mutation.
- Bad: correct **only** under the all-rotations-before-all-translations ordering; silently wrong for any interleaving, as the V8-engine assembly-level rotate-above-translated-child case exposed.
- Bad: requires a perfect mirror-image `unapplyOperations` reverse pass before every re-render; any asymmetry between apply and undo corrupts the pose.
- Bad: violates the ADR-023 parity contract in the browser while leaving the trimesh tests correct — the hardest kind of divergence to notice.

### Absolute world-matrix recomposition (chosen)

- Good: a pure function of the declared operation levels — same input, same matrix.
- Good: idempotent, so redundant recursive calls are harmless and no undo state is kept.
- Good: reproduces the backend's world-space, outermost-last semantics for **arbitrary** operation orderings, restoring ADR-023 parity in the browser.
- Good: deletes `unapplyOperations` and the undo/redo bookkeeping entirely — less surface, fewer invariants.
- Bad: `matrixAutoUpdate = false` means `composeOperations` **owns** the mesh matrix; Three.js `position`/`quaternion` properties on these meshes no longer drive the transform, a convention a future contributor must know.

## Consequences

- **The browser consumer now structurally upholds ADR-023's parity contract for arbitrary operation orderings.** The viewer reproduces the same world pose as `.mesh()` and `.scad()` regardless of how rotations and translations interleave — the V8-engine banked pistons render correctly.
- **This rhymes with ADR-023's Python-side idempotent-render decision.** Both replaced "mutate and carefully undo" with "recompute absolutely from declared state": ADR-023's driver-tagged sweep rebuilds the operations list from what each driver declares rather than removing remembered objects; this ADR rebuilds the mesh matrix from `this.operations` rather than reversing a remembered chain of quaternion/position mutations.
- **`matrixAutoUpdate = false` transfers ownership of the mesh transform to `composeOperations`.** The mesh's local `position`/`quaternion` no longer participate; anyone extending the viewer must feed transforms through the operation levels, not through Three.js object properties.
- **Verification is Jest tests pinned against Python-computed cross-checks.** `composeOperations.test.ts` pins: the V8-engine increment-5 piston chain (a rotation about world X then a placement translation, cross-checked at `t=0` and `t=0.25` against backend-computed origins); an order-sensitivity fixture asserting `[t, r]` and `[r, t]` of the same pair differ; a rotate-above-already-translated-child fixture (the exact bug — the child must swing to the world origin's rotated position, explicitly *not* stay at its untranslated placement); and the pre-existing rotate-then-translate leaf pattern (increments 1–4), where old and new semantics agree and which must keep matching numerically.
- **Unrelated but adjacent viewer-lifecycle hardening** landed alongside this work (commit `3ea506c`): a monotonic generation counter disposes superseded trees so a stale STL callback from a replaced tree can no longer add an orphan mesh — noted here only as related lifecycle context, **not** part of this transform-composition decision.

## References

- `solid_node/viewers/web/app/src/node.ts:59-78` — `composeOperations`, the pure world-matrix fold
- `solid_node/viewers/web/app/src/node.ts:209-225` — `applyOperations`, absolute matrix set with `matrixAutoUpdate = false`
- `solid_node/viewers/web/app/src/composeOperations.test.ts` — parity fixtures cross-checked against backend-computed poses
- `solid_node/viewers/web/app/src/node.test.ts` — node-level operation/reload behavior
- Commit `23bd5e1` (absolute world-matrix composition); commit `3ea506c` (generation-counter tree disposal — related lifecycle hardening, not this decision)
