## Why

The perturbation assertions inject their Rotation or Translation
immediately before the node's first pre-existing Translation, so that the
part turns about its own axis rather than sweeping around the world origin
(ADR-025). A node whose operations begin with a Rotation is displaced after
it: the direction is read in the frame that rotation produces, the parent's
axes, while the public contract says directions are local and the node's own
rotations carry them. Two projects tripped over it in one day — abacus (a
rod carrying only a rotation) and kossel (a pulley turned onto its shaft
before its placement) — and each had to document the exception in its
tests. The frame a direction is read in should not depend on which
operation happens to come first.

## What Changes

- The perturbation is inserted before every pre-existing operation of the
  node, at index 0 of `node.operations`. `axis` and `along` are always read
  in the node's own untransformed frame, and every one of the node's own
  operations — rotations, translations, simulated motion — carries them.
- A node whose first operation is a Translation is unaffected: the
  insertion point is the same one. A node with no operations is unaffected.
- **BREAKING** for a test that relied on a leading Rotation being applied
  before the perturbation: its `axis` or `along` must now be spelled in the
  node's own frame. The framework's own suite has one such pin, rewritten.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `test-framework`: the "Perturbation-based fit assertions" requirement's
  insertion point — before every pre-existing operation rather than before
  the first Translation.

## Impact

- `solid_node/test.py` `_assert_perturbation`.
- `tests/test_assertions.py`: the insertion-point pins and
  `LocalFrameCarriedByRotationTest`; one new pin for a leading Rotation.
- `docs/adrs/TEST-FRAMEWORK/ADR-025` is amended by a short ADR;
  `docs/architecture.md` says "own frame" where it says "local
  pre-placement frame".
- Originating projects: abacus and kossel restate their directions in the
  node's own frame once this integrates; that is project work, recorded in
  the shop's `docs/warts.md` plan. The shop's API skill sentence about the
  insertion point is corrected in the shop repository.
