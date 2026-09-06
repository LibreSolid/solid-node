# ADR-075: The Perturbation Is the Node's First Operation

**Status:** Accepted
**Date:** 2026-09-06
**Amends:**
- [ADR-025: Perturbation-Based Kinematic Fit Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md)

**Related to:**
- [ADR-023: Kinematic operations and driver-tagged idempotent renders](../NODE/ADR-023-kinematic-operations-and-driver-tagged-idempotent-renders.md)

## Context and Problem Statement

ADR-025 injects the perturbation "immediately before the node's first
`Translation`, appended if none", so that a rotational perturbation turns
the part about its own axis before its placement moves it away from the
origin, and a translational one is carried by the placement rotations
that follow. The contract the framework states — in its spec, in the shop's
API skill and in the assertion's own comment — is that `axis` and `along`
are local: directions in the node's frame, carried by its rotations.

A node whose first operation is a Rotation breaks the contract. The search
for the first Translation passes over the Rotation, the perturbation is
applied after it, and its direction is read in the frame that Rotation
produces: the parent's axes. Two projects met it on the same day. abacus's
rod carries only a Rotation, so its "sideways" and "up" had to be written
in the column's frame; kossel's pulley is turned onto its shaft before it
is placed, so its spin axis had to be written as the tower's radial Y. Both
tests documented the exception. The frame a direction is read in depended
on which operation happened to come first.

## Decision Drivers

- One frame for a direction, stated once, true for every node.
- ADR-025's own reason — a part turns about its own axis, not the world
  origin — must survive.
- No new parameter: a test spells the direction in the node's frame,
  which the node's own rotations make known.

## Considered Options

1. Insert before the first Translation *or* Rotation, whichever comes
   first.
2. Insert at index 0, before every pre-existing operation.
3. Add a `frame=` selector.

## Decision Outcome

Option 2. `_assert_perturbation` inserts at index 0. Because the
perturbation is the first operation applied, `axis` and `along` are read in
the node's own untransformed frame and every one of the node's own
operations — a leading Rotation, a simulated motion, a placement — carries
them, as do its ancestors'. A node whose first operation is a Translation,
or that has none, is placed exactly as before.

Option 1 is index 0 for every node that has an operation and adds only a
search. Option 3 was rejected as a parameter for a question the node's own
frame already answers.

## Consequences

- The spec's "Translational mode" scenario and the API skill's "directions
  are local and carried by placement rotations" are now true without
  exception; the skill's sentence about the insertion point is corrected in
  the shop repository.
- A test that relied on the parent-frame reading of a leading Rotation
  changes meaning. The framework's own pin is rewritten and gains a twin
  for the leading-Rotation case; abacus and kossel restate their
  directions in the node's frame.

Change record: `openspec/changes/archive/2026-09-06-perturb-in-the-nodes-own-frame/`.
