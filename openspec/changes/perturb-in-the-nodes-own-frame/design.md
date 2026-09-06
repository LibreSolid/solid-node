## Context

`_assert_perturbation` in `solid_node/test.py` finds the index of the
node's first `Translation` and inserts the perturbation there, appending
when there is none. `node.mesh` applies operations in list order, so
everything before the insertion point is applied to the mesh before the
perturbation — a leading Rotation orients the part first, and the
perturbation's `axis` or `along` is then read in the oriented frame. ADR-025
chose "before the first Translation" to keep a shaft spinning about its own
axis rather than about the world origin; it did not consider a node whose
first operation is a Rotation, and the API skill and the spec's own words
("local", "carried by placement rotations") describe the index-0 behaviour.

## Goals / Non-Goals

**Goals:**

- One rule: the perturbation is the node's first operation. Directions are
  the node's own, always.
- No change for nodes whose first operation is a Translation or that have
  none.

**Non-Goals:**

- A way to ask for a direction in the parent's or the world's frame. A
  test that wants that spells the direction in the node's frame; the
  node's own rotations are known to it.
- Any change to the anti-gaming pairing, epsilon or restore semantics.

## Decisions

**Insert at index 0.** `node.operations.insert(0, operation)` replaces the
first-Translation search. The rotation-about-own-axis property ADR-025
wanted still holds — index 0 precedes every placement — and the
translational mode's local frame becomes exactly what the spec said it was.
Alternative considered: insert before the first Translation *or* Rotation,
whichever comes first — rejected, that is index 0 for every node that has
an operation and adds nothing but a search.

**Rewrite the pins rather than keep both rules.** The suite's
"rotation inserted before first translation" pin becomes "inserted before
every operation"; `LocalFrameCarriedByRotationTest` is unchanged in
substance (its node's first operation is a Translation) and gains a twin
whose node leads with the Rotation.

## Risks / Trade-offs

- [A project test that relied on the parent-frame reading of a leading
  Rotation changes meaning] → the two known cases (abacus, kossel) are
  documented exceptions in their own tests and are restated in the node's
  frame as project follow-ups; no other project in the shop uses a
  leading Rotation with a perturbation assertion.
