# ADR-023: Kinematic Operations Model and Driver-Tagged Idempotent Renders

**Status:** Accepted
**Date:** 2026-07-17
**Depends on:**
- [ADR-001: Composite Pattern for Node Tree Architecture](./ADR-001-composite-pattern-node-tree-architecture.md)
- [ADR-002: Template Method Pattern for Node Lifecycle](./ADR-002-template-method-pattern-for-node-lifecycle.md)
- [ADR-008: Time-Based Animation System for Assemblies](./ADR-008-time-based-animation-system-for-assemblies.md)

**Extended by:**
- [ADR-028: Cached Base Meshes and Single-Matrix World Composition for `.mesh`](./ADR-028-cached-base-meshes-and-single-matrix-world-composition.md) — adds `.matrix()` as a fourth operation consumer surface

**Related to:**
- [ADR-009: Trimesh-Based Mesh Assertions for CAD Testing](../TEST-FRAMEWORK/ADR-009-trimesh-based-mesh-assertions-for-cad-testing.md)
- [ADR-014: Recursive NodeAPI REST Pattern Mirroring Node Tree](../VIEWER-WEB/ADR-014-recursive-nodeapi-rest-pattern.md)
- [ADR-022: Cross-Runtime Degree-Trig Parity for `$t` Expression Evaluation](../MATH/ADR-022-cross-runtime-degree-trig-parity-for-t-expressions.md)

**Extended by:** [ADR-027: Absolute World-Matrix Composition for Viewer Transforms](../VIEWER-WEB/ADR-027-absolute-matrix-composition-for-viewer-transforms.md)

## Context and Problem Statement

ADR-008 established *that* an `AssemblyNode` has a normalized `time` and *that* assemblies animate. It did not specify how the transforms an assembly applies to its children are represented, how they render identically in OpenSCAD, in trimesh-based tests, and in the browser, how they compose up an assembly hierarchy into world coordinates, or how they stay correct when a node is re-rendered many times (once per test instant, once per assemble, continuously in the viewer) -- possibly by more than one driving assembly.

An assembly moves parts by calling `node.rotate(angle, axis)` / `node.translate(vector)` inside its `render()`. These calls must:

- produce the same motion in three consumers -- OpenSCAD build output, the trimesh meshes used by test assertions (ADR-009), and the serialized wire form the browser evaluates (ADR-022);
- compose correctly through nested assemblies so a leaf ends up in world coordinates;
- be **absolute per render**, not cumulative: rendering the same assembly at `$t=0.5` twice must yield the same pose, not double the rotation;
- survive the test runner, which renders a node at many discrete instants and restores checkpointed state between them;
- tolerate **multiple independent drivers of the same node instance** (e.g. a wheel spun by its axle assembly *and* steered by the steering assembly) without one driver corrupting the other's contribution.

The naive approaches (remembering which operation objects were added and removing them, or snapshotting/restoring the operations list) break under the runner's checkpoint restore and under multi-driver scenarios -- as the project discovered empirically (commit `079a172`).

## Decision Drivers

- **One transform, three consumers.** A rotate/translate must apply identically in `.scad()` (OpenSCAD), `.mesh()` (trimesh tests), and `.serialized` (browser) -- "the same results can be obtained in browser and in tests" (operations module intent).
- **World-coordinate composition.** A node's test mesh must reflect its own operations *and* every ancestor's, matching what the viewer renders.
- **Absolute, non-accumulating kinematics.** Re-rendering an instant must reproduce the pose, never accumulate onto the previous render.
- **Multi-driver safety.** Two assemblies driving the same node instance must not disturb each other's operations.
- **Runner robustness.** Per-instant checkpoint save/restore must not resurrect stale operations or clobber live ones.
- **Numeric resolution at keyframes.** Under `set_keyframe()`, animated solid2 expressions must resolve to plain floats so trimesh transforms can be built; the keyframe must propagate into nested assemblies.

## The Transform Model (design)

**Operations as first-class tri-consumer objects** (`operations.py`). `Rotation(angle, axis, node)` and `Translation(vector, node)` each expose:
- `.scad(obj)` -- wraps the solid2 object with `rotate`/`translate` for build output;
- `.mesh(m)` -- applies the equivalent trimesh transform, resolving animated angles/components to floats via `_as_number` -> `node.as_number` (falling back to `float()` when the operation was rebuilt through `unserialize()` and has no node);
- `.serialized` -- the wire form `['r', str(angle), axis]` / `['t', [str(x), ...]]` the browser evaluates (feeding ADR-022);
- `.reversed` -- the inverse operation.
An `_operations` registry (`{'r': Rotation, 't': Translation}`) plus `unserialize()` round-trips the wire form back into objects.

**World-coordinate mesh composition** (`base.mesh`). The mesh is loaded from the STL, then each of the node's own operations is applied, then the walk climbs `_parent` applying each ancestor's operations -- own-first, then up the tree -- producing the world pose the viewer renders, which the ADR-009 assertions consume.

**Keyframe propagation** (`assembly.set_keyframe`, `assembly.time`). `set_keyframe(time)` sets `_time` and recurses into rendered children so nested assemblies also render numerically; `time` returns `_time` when set (tests/keyframes) else solid2's `get_animation_time()` (`$t`).

## Considered Options (the mechanism for absolute, multi-driver-safe kinematics)

The headline decision was how to make re-renders express **absolute** kinematics without accumulation and without cross-driver corruption.

1. **Tag each operation with its driving assembly; sweep by driver tag before each render** (chosen).
2. **Object-identity removal** -- record the specific operation objects added during a render and remove those exact objects next time.
3. **Snapshot-baseline restore** -- snapshot the node's operations list before driving it and restore to that baseline before re-rendering.

## Decision Outcome

Chosen: **driver-tagged idempotent renders.** While an `AssemblyNode.render()` runs, it sits on a module-level `_render_stack`; every `rotate()`/`translate()` applied in that window is tagged with the driving assembly (`operation._driver = assembly`) and the target node is registered in that assembly's persistent `_driven_nodes` set (`_tag_driver`). Before its next render, the assembly sweeps each driven node and drops **only** the operations whose `_driver` is itself:

```
node.operations[:] = [op for op in node.operations
                      if getattr(op, '_driver', None) is not self]
```

`AssemblyNode.__init_subclass__` wraps every subclass `render()` with `_idempotent_render`, which performs this sweep and manages the render stack (with re-entrancy handling so a subclass delegating to `super().render()` does not sweep twice). Operations applied outside any render (static placement in `__init__`, a test poking `node.operations` directly) are left untagged and are never swept.

This is chosen over the alternatives because sweeping **by driver identity** rather than by operation-object identity or by list snapshot is the only approach that is simultaneously robust to the test runner's checkpoint restore and safe under multiple independent drivers:

### Tag-by-driver sweep (chosen)
- Good: drops exactly this assembly's contribution regardless of which operation *objects* currently sit in the list, so a checkpoint restore that resurrects old operation objects cannot cause accumulation.
- Good: two assemblies driving the same node each remove only their own tagged operations -- multi-driver safe by construction.
- Good: `_driven_nodes` is persistent, so a node driven in one render but not the next is still swept clean.
- Good: untagged (statically placed) operations are preserved automatically.
- Bad: mutates shared node state via a module-level render stack -- implicit coupling that must be understood to reason about ordering.
- Bad: relies on subclass-hook wrapping (`__init_subclass__`), which is invisible at the call site.

### Object-identity removal
- Good: conceptually simple -- remember what you added, remove it.
- Bad: the runner's per-instant checkpoint restore copies back a saved operations list, resurrecting **old** operation objects the assembly already believed it discarded; identity-based removal misses them and the pose accumulates (root cause fixed in `079a172`).
- Bad: fragile to any code path that rebuilds operation objects (e.g. `unserialize`).

### Snapshot-baseline restore
- Good: no per-operation bookkeeping; just restore a list.
- Bad: with two independent drivers of one node, restoring to one driver's baseline clobbers the other driver's operations -- the core multi-driver corruption (`079a172`).
- Bad: interacts badly with checkpoint save/restore, which already manipulates the same list from the runner side.

## Consequences

- **A single transform definition serves OpenSCAD, tests, and the browser.** Adding a new operation type means implementing `.scad`/`.mesh`/`.serialized`/`.reversed` and registering it in `_operations`; all three consumers and `unserialize` then work. Forgetting one consumer silently diverges that runtime (mirrors the parity risk of ADR-022, but per-operation).
- **`node.mesh` is the shared truth for spatial assertions.** ADR-009's `assertIntersecting`/`assertInside`/etc. operate on this world-coordinate mesh; correctness of the ancestor-chain composition directly determines test validity.
- **Idempotent renders make instants reproducible.** The runner can render any instant repeatedly and in any order; combined with per-instant checkpoint isolation and unclobberable snapshots (`18b409c`, `446f430`), child state does not leak between instants.
- **Multi-driver kinematics are a supported, tested topology.** The driver tag makes a node shared by two assemblies well-defined; this is a deliberate capability, not an accident.
- **Implicit, stateful coupling is the cost.** The module-level `_render_stack`, the `_driver` attribute stamped onto operations, and the `__init_subclass__` wrapping are non-obvious. A contributor writing a custom `render()` inherits idempotency automatically but must understand the sweep to reason about why an operation vanished.
- **`set_keyframe` must reach every nested assembly.** Numeric mesh evaluation depends on `_time` being set throughout the subtree (`c320ae7`); a nested assembly missed by propagation would fall back to `$t` and fail numeric resolution in `.mesh()`.
- **Historical fragility, now covered.** Several sharp edges were found and fixed empirically this cycle: `Rotation.mesh` crashing on animated angles (`e5c7ce8`), `unserialize` calling the registry key as a constructor (`f00e6ff`), `Translation.reversed` arity (`81a330a`), and phantom mesh mutation in checkpoint restore (`446f430`). They indicate this layer's invariants are subtle and benefit from the explicit documentation this ADR provides.

## References

- `solid_node/node/operations.py` -- `Rotation`/`Translation` tri-consumer objects, `_as_number`, `_operations`, `unserialize`
- `solid_node/node/base.py:36-46` -- `_render_stack`, `_tag_driver`
- `solid_node/node/base.py:422-445` -- `rotate`/`translate`, world-coordinate `mesh` composition
- `solid_node/node/base.py:455-465` -- `save_checkpoint`/`restore_checkpoint`
- `solid_node/node/assembly.py:11-47` -- `_idempotent_render` driver-tagged sweep
- `solid_node/node/assembly.py:67-81` -- `set_keyframe` propagation, `time`
- Commits: `78eb57a` (ancestor composition in `node.mesh`), `079a172` (multi-driver sweep-by-tag), `7497235` (idempotent renders), `18b409c` (per-instant snapshot isolation), `c320ae7` (keyframe propagation), `446f430` (phantom mesh mutation), `e5c7ce8` (`Rotation.mesh` animated angle), `f00e6ff` (`unserialize`), `81a330a` (`Translation.reversed`)
