# ADR-025: Perturbation-Based Kinematic Fit Assertions

**Status:** Accepted
**Date:** 2026-07-17
**Depends on:**
- [ADR-009: Trimesh-Based Mesh Assertions for CAD Testing](./ADR-009-trimesh-based-mesh-assertions-for-cad-testing.md)
- [ADR-023: Kinematic Operations Model and Driver-Tagged Idempotent Renders](../NODE/ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)

**Extended by:**
- [ADR-029: Manifold Cache and AABB Broad-Phase for Intersection Assertions](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md) — accelerates the intersection path while preserving the strict `volume_epsilon=0` flush-contact contract

**Related to:**
- [ADR-010: TestCaseMixin Pattern for Embedded Tests](./ADR-010-testcasemixin-pattern-for-embedded-tests.md)
- [ADR-011: Animation Testing Decorators for Time-Based Validation](./ADR-011-animation-testing-decorators.md)

## Context and Problem Statement

ADR-009 gave the framework static-pose mesh assertions: at one configuration, do two parts intersect, contain, or stand a given distance apart. That is necessary but not sufficient for *mechanical fit*. A keyed shaft in a keyed bore, a torque coupling, a ratchet pawl, a journal bearing, a sliding dovetail, a press-fit boss — these are defined not by a single pose but by **how the fit behaves under a small perturbation along its working degree of freedom**: it must be free to move within its intended play, and it must genuinely lock (foul against its mating part) once pushed beyond that play. That degree of freedom may be **angular** (a part rotating about its axis) or **linear** (a part sliding along a vector). Neither property is expressible as a single static check.

Worse, a naive "the parts must interfere when moved" test is **trivially gamed**: an oversized bore or an undersized key will pass a blocking test by never really constraining anything, because the parts happen to overlap somewhere — or will pass a clearance test because they never touch at all. A fit contract needs *both* directions of the guarantee, stated together, or it certifies nothing.

The framework therefore needed a kinematic assertion layer that:

- perturbs a part along its **working degree of freedom** — a small rotation about its own working axis (the way it spins in its bore/pocket), or a small translation along a given vector (the way it slides in its guide);
- reuses the existing transform semantics (ADR-023) so a perturbed pose is computed exactly as the viewer and build would compute it;
- never leaves residue in the model after the check;
- expresses fit as a **paired** contract (free within the play window, blocked beyond it) so it cannot be gamed;
- tolerates the float noise that boolean intersections produce at flush contacts.

## Decision Drivers

- **Mechanical-fit semantics, not just geometry.** Assertions must express engagement (fit lock) and clearance (play window) as first-class contracts.
- **Both angular and linear play.** Fit contracts cover rotational fit (torque/keyed engagement) and translational fit (sliding clearance, press-fit, axial play); the layer must perturb along the relevant degree of freedom.
- **Rotate about the part's own axis.** A rotational perturbation must model a part turning in place, which means rotating before the part's placement translation, not after.
- **Reuse the ADR-023 operations model.** A perturbed pose must be the same computation as a real motion — the same `Rotation`/`Translation` operation, the same `node.mesh` ancestor composition — so tests and reality agree.
- **Leave no residue.** The model's `node.operations` must be exactly as found after the assertion, pass or fail.
- **Anti-gaming by construction.** Fit must be certified by a paired free/blocked contract, with the anti-gaming guarantee itself covered by red/green fixtures.
- **Numerical robustness.** Flush contacts yield non-empty boolean slivers (~1e-13 mm^3) that `is_empty` cannot distinguish from real interference; the layer must separate genuine fouling from boolean noise without weakening the strict default.
- **A contract-independent safety net.** Beyond hand-written fit contracts, any two parts nobody thought to test should still be checked for collision.

## Considered Options

**Perturbation mechanism:**
1. Temporarily inject an operation into `node.operations` and always remove it in `finally` (chosen).
2. Transform a copied mesh directly, outside the operations model.
3. Model explicit kinematic joints with degrees of freedom.

**Boolean-noise handling:**
1. Exact `is_empty` as the strict default, plus an opt-in `volume_epsilon` threshold (chosen).
2. Exact `is_empty` only.
3. Mesh-tolerance / merge cleanup of the boolean result before measuring.

## Decision Outcome

**Mechanism — temporary operation injection with guaranteed restore, parameterized by perturbation type.** The core helper `_assert_perturbation(...)` injects a single operation into `node.operations`, evaluates fouling against the mating part, raises `AssertionError` on any contract violation, and in a `finally` block **always** removes the injected operation, leaving `node.operations` exactly as found. The injected operation is chosen by the perturbation type:

- **Rotational (selected by `axis`).** Injects a `Rotation(signed_angle, axis, node)` **immediately before the node's first `Translation`** in `node.operations` (appending if the node has no translation). Because operations apply in list order and translation places the part in the assembly, inserting the rotation ahead of the translation rotates the part **about its own axis** — a shaft spinning in its bore — rather than sweeping it around the world origin.
- **Translational (selected by `along`).** Injects a `Translation` that perturbs the part's linear position by the given magnitude (a distance in mm) along `along`, inserted at the **same point** as the rotational one — immediately before the node's first pre-existing `Translation`, appended if the node has none. Because the perturbation runs before the node's own placement translation, `along` is a direction in the node's **local, pre-placement frame**: any later placement or ancestor-assembly rotation that applies after this insertion point carries the perturbation's direction with it, rather than it being a fixed world vector. This local-frame semantics is deliberate and covered by `LocalFrameCarriedByRotationTest` in `tests/test_assertions.py`. `along` is normalized to a unit vector before it is scaled by the magnitude.

In both cases the pose is measured with `trimesh.boolean.intersection([node.mesh, against.mesh])`, both meshes in world coordinates via ADR-023's ancestor composition. `axis` and `along` are **mutually exclusive selectors** that choose the perturbation type; everything else about the mechanism, the twin methodology, and the noise tolerance is identical across the two modes.

Both modes are **implemented in `test.py` today** (commit `b56ab57` landed `along`). The signature specifics this ADR had deliberately left open are now settled:

- **`axis` defaults to `None`**, resolving to the historical `(0, 0, 1)` when `along` is also `None` — so rotation about Z stays the default mode when neither selector is given.
- **Passing both `axis` and `along` raises a loud `ValueError`**; so does a **zero `along` vector**. `along` is normalized to a unit vector, and the magnitude argument is interpreted as a distance in mm.
- **`directions='both'` (default) | `'forward'`**, honored in both modes: `'both'` checks the +magnitude and -magnitude perturbations separately (preserving prior behavior); `'forward'` checks only the +magnitude direction, for contracts that are deliberately **one-sided** (e.g. a sleeve blocked sliding inward by a lip but free to slide outward). Any other value is a loud error.

**Contract — the anti-gaming Blocked/Free twin (headline), mode-agnostic.**
- `assertBlockedBeyond(node, ..., against, axis=... | along=..., volume_epsilon=0.0)` — the fit engagement contract. Perturbed by the given magnitude in **both directions** (checked separately), `node` **must** intersect `against` in every direction: the fit must genuinely lock beyond its play. For the rotational mode this is torque-fit/keyed engagement; for the translational mode this is a linear stop / press-fit lock.
- `assertFreeWithin(node, ..., against, axis=... | along=..., volume_epsilon=0.0)` — the explicit anti-gaming twin. Perturbed by the given magnitude (or every magnitude in a list/tuple, e.g. a journal/freewheel sweep or a slide travel range), in **both directions**, `node` **must not** intersect `against`: a blocking test elsewhere cannot be gamed by an oversized bore/pocket/slot that never truly touches.

Together they bracket the intended play window from both sides, for whichever degree of freedom is selected. The anti-gaming guarantee is itself test-covered by TDD fixtures in `tests/meta_project` (`keyed.py` green; `keyed_loose.py` red — the "gamed fit" that a naive one-sided test would wrongly pass).

**Boolean-noise handling — strict default plus opt-in `volume_epsilon`.** `volume_epsilon` (mm^3, default `0.0`) preserves exact `is_empty` strictness by default; when `> 0`, an intersection counts as fouling only if `abs(volume) > volume_epsilon`. This lets flush contacts (shaft end faces meeting exactly, abutting slide faces) that produce pure-noise slivers avoid masquerading as real interference in either the blocked or the free direction, without loosening behavior for callers who do not set it. It applies uniformly across both perturbation modes.

**Safety net — `assertNoPairwiseIntersections(node, volume_epsilon=0.0)`.** Walks the assembled tree from `node` to all leaves (`_leaves`) and asserts every leaf pair is non-intersecting, applying the same `volume_epsilon` noise tolerance. This holds regardless of which specific fit contracts exist: any two parts nobody tested directly are still covered.

Rationale for the chosen options:

### Perturbation via temporary operation injection (chosen)
- Good: a perturbed pose is computed by the exact ADR-023 machinery the viewer/build use — tests and reality cannot diverge, for either rotation or translation.
- Good: reusing the operations model generalizes cleanly — the same inject/restore pattern serves both modes, differing only in which operation is injected.
- Good: insert-before-first-Translation gives correct own-axis rotation for free, using existing ordering semantics.
- Good: the `finally` restore guarantees zero residue, so assertions compose and order-independence holds.
- Bad: mutates shared `node.operations` mid-assertion; correctness depends on the restore always running.
- Bad: the own-axis heuristic keys on "first Translation," which assumes the conventional rotate-then-translate placement ordering.

### Transform a copied mesh directly
- Good: no mutation of node state; conceptually simple.
- Bad: reimplements the transform outside the operations model, risking divergence from how the part actually moves (the very parity problem ADR-023/ADR-022 guard against).
- Bad: must replicate ancestor composition by hand to reach world coordinates.

### Explicit kinematic joints with DOFs
- Good: the general, physically faithful way to model articulation and limits.
- Bad: far heavier than a test assertion needs; a modeling subsystem, not a check.
- Note: presented for completeness; there is no evidence this was actually weighed as an implementation route for the assertions.

### Boolean-noise: strict default + opt-in `volume_epsilon` (chosen)
- Good: keeps ADR-009's exact strictness by default; opt-in threshold only where flush contacts are expected.
- Good: one intuitive, unit-bearing knob (mm^3) shared across all the new assertions, both modes, and the adjacency sweep.
- Bad: the caller must know to set it; a too-large epsilon could hide a small real interference.

### Exact `is_empty` only
- Good: simplest, strictest.
- Bad: flush-contact designs are untestable — legitimate abutments raise false failures.

### Mesh-tolerance / merge cleanup
- Good: could remove slivers at the geometry level.
- Bad: opaque, global, and harder to reason about than an explicit volume threshold; risks masking real thin overlaps.

## Consequences

- **Mechanical fit is now a first-class, gaming-resistant contract for both angular and linear play.** `assertBlockedBeyond` + `assertFreeWithin` together certify a play window; used alone, `assertBlockedBeyond` is explicitly insufficient — the twin is the point, and the red fixture (`keyed_loose.py`) proves a one-sided test would pass a bad part.
- **One methodology, two degrees of freedom.** The `axis`/`along` selector generalizes the whole layer without duplicating it: the twin methodology, the `directions` selector, and `volume_epsilon` wrap whichever perturbation type is chosen. Both rotational and translational fit are available today under the same design.
- **Built directly on ADR-023.** The layer inherits the operations model's correctness (own-axis via operation ordering, world pose via `node.mesh`) and its risks (shared-state mutation); the `finally` restore is the discipline that keeps it safe.
- **Own-axis rotational perturbation assumes rotate-before-translate placement.** Parts placed with an unconventional operation order (translation before the intended local rotation) could rotate about the wrong center; this is an accepted convention, worth noting for authors. The translational mode **shares the same insert-before-first-Translation rule**, so `along` is interpreted in the node's local, pre-placement frame — carried by any later placement/ancestor rotation. That is the designed behavior (tested by `LocalFrameCarriedByRotationTest`), not a heuristic risk: authors give `along` in the part's local frame, the same frame the part is modeled in before placement.
- **`volume_epsilon` is a shared, opt-in robustness knob** across both perturbation modes and the adjacency sweep, defaulting to strict `is_empty`. It trades a small chance of hiding sub-epsilon interference for the ability to test flush-contact designs at all.
- **The adjacency sweep is a contract-independent backstop.** `assertNoPairwiseIntersections` scales O(leaves^2) in boolean operations, which can be costly for large assemblies, but catches collisions no hand-written contract covers.
- **Extends the ADR-009 assertion surface.** These are additional methods on the same test mixin (ADR-010), so they compose with static assertions and animation decorators (ADR-011); the kinematic layer does not replace the static one.

## References

- `solid_node/test.py:97-264` — `assertBlockedBeyond`, `assertFreeWithin`, `_resolve_perturbation_axis` (axis/along selector + validation), `_signed_perturbations` (`directions`), `_assert_perturbation` (rotational and translational injection at the same insert-before-first-Translation point + guaranteed restore)
- `solid_node/test.py:266+` — `assertNoPairwiseIntersections`, `_leaves` adjacency sweep
- `solid_node/test.py:33-95` — the ADR-009 static assertions this layer extends
- `tests/meta_project/keyed.py` (green) / `keyed_loose.py` (red, "gamed fit") — TDD fixtures covering the anti-gaming guarantee
- `tests/test_assertions.py` — `LocalFrameCarriedByRotationTest` covering the local-frame semantics of the translational (`along`) mode
- Commits: `adac98b` (`assertBlockedBeyond`/`assertFreeWithin`, issue #6), `ecfbdf9` (`assertNoPairwiseIntersections`, issue #11), `c21ae0c` (`volume_epsilon`, improvements.md #21), `b56ab57` (`along=` translational mode, improvements.md #25)
