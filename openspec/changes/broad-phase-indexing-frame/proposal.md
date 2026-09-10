## Why

`assertNoSolidInterference` indexes its candidate pairs on conservative
**world-axis** AABBs (ADR-029). When every solid in an assembly shares one
outermost rigid turn, every one of those boxes is inflated by that turn — up
to √2 in the plane of a 45° rotation — and pairs that can never meet are
emitted anyway. Each spurious pair costs one exact Boolean, which on a real
assembly is seconds.

The finding is recorded in `workflow/warts.md`, last section, "3DPrintedClocks
wall clock 02 (2026-09-09, exact sweep cost)", second bullet ("A common rigid
turn inflates every world box"). Measured there: 53 topmost rigid solids, ~118
candidate pairs and ~19 s per sweep instant, ~110 booleans of which every one
comes back empty. The same model driven with `--set facing=0` — the same
geometry, the same clearances, only without the common turn — yields **69
candidate pairs and 6.4 s per instant**. Nothing about the machine changed;
only the frame the boxes were taken in.

Two details of that bullet are imprecise and this cycle corrects them. It
names the cycle `broad-phase-in-the-root-frame` and says the clock "declares
`facing = 45°` on its root". In fact `Clock.render()`
(`projects/3DPrintedClocks/simulation/shared/assemblies.py`, ~line 609)
applies `rotate(UPRIGHT, x)` and then `rotate(self.facing, Z)` to **each
direct child** of the root, not to the root itself — so stripping the root's
own placement would strip nothing. What is true, and what this change acts
on, is that every topmost rigid solid shares one outermost rigid turn.
Wherever that turn is declared, the fix is the same: **take the index's boxes
in a frame chosen from the assembly, not on world axes.** The cycle is
therefore renamed `broad-phase-indexing-frame` and the wart's wording
corrected to "on each child of its root".

## What Changes

- **The whole-assembly interference index takes its boxes in a chosen
  indexing frame.** For a candidate frame `F`, each solid's index box is the
  AABB of its 8 local-bounds corners under `inv(F) @ M_i`. World axes remain
  one of the candidates, and the identity frame reproduces exactly today's
  boxes.
- **The candidate frames are the world frame and the placement frames of the
  K largest topmost solids** by local-bounds diagonal, K = 3, a module
  constant and not a public knob. The frame with the smallest total box
  volume (summed over all solids) wins; ties resolve to the earliest
  candidate, world first, so the choice is deterministic for the same inputs.
- **A non-world candidate's boxes are padded by a fixed margin**
  (`_INDEXING_FRAME_MARGIN = 1e-6` mm, a module constant beside K) absorbing
  the arithmetic of the frame change: a frame box costs an inversion and two
  matrix products of float residue where a world box costs one product, and
  without the margin two solids in exact flush contact could be culled in the
  chosen frame where the world index emits them. Padding only ever adds
  candidates. World boxes are never padded, so candidate zero remains today's
  boxes bit for bit — and, because every rival is padded, an axis-aligned
  assembly now prefers the world frame strictly rather than by the tie rule.
- **This is exact-negative, exactly as ADR-029's world-axis broad phase is.**
  A conservative AABB in *any* rigid frame is still a superset of the placed
  geometry expressed in that frame, and two solids intersect if and only if
  they intersect in every frame — so box overlap in one common frame remains
  a *necessary* condition for intersection. The change can shrink the
  candidate set; it can never drop a pair that meets, and it can never change
  a verdict.
- **Scope is one call site.** Only `assertNoSolidInterference`'s call to
  `_bounds_candidates` changes. The placement records' world bounds (record
  index 2, from `_place_solid` via `_world_bounds`) stay world-axis, because
  the gravity-support assertion reads them along a world gravity vector
  (`_gravity_extent`, `_grounded_seeds`, `_virtual_floor`,
  `_support_candidates`). Record[2] is not replaced and no existing tuple
  position moves.
- **The pair-level broad phases inside `_exact_verdict` and
  `_faceted_verdict` are out of scope**, and recorded in design.md as a
  possible follow-up.
- **No public surface changes**: no flag, no environment variable, no
  assertion argument, no message change. A project that says nothing gets
  fewer booleans and the same verdicts.
- **One ADR (ADR-091) extending ADR-029**, recording why the index's frame is
  free while the support graph's is not.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-framework`: "Broad-phase completeness" — completeness is stated for a
  bound taken in the frame the index chose, the index MAY choose that frame
  among the world frame and the frames of the largest solids by a
  deterministic rule, a bound taken in an indexing frame MAY be enlarged by a
  fixed margin absorbing the arithmetic of the frame change and remains a
  superset, and the choice SHALL NOT change any verdict. "Whole-
  assembly solid interference assertion" — the sentence naming "conservative
  world bounds" as the index's input becomes the chosen indexing frame's
  conservative bounds.

Not modified: the gravity-support requirements (their bounds stay world-axis
by design), and "Broad-phase work adapts to sparse orientation without
changing candidates or order" — that requirement is about the sweep *given* a
set of boxes, and is unchanged by which frame produced them.

## Impact

**Framework code.** `solid_node/test.py`: two module constants, a frame-choice
helper and a frame-relative box helper beside `_world_bounds`; `assertNoSolidInterference`
builds its index boxes through them. `_solid_geometry`/`_place_solid` must
make each solid's LOCAL bounds reachable from the assertion (the matrix is
already record[6]); design.md §5 settles how without disturbing
`_record_key`'s `len(record) <= 6` guard or any index-2/3/4/5/6 reader.
`_world_bounds`, `_boxes_disjoint`, `_bounds_candidates`,
`_axis_order_and_pressure` and `_sweep_candidates` are untouched.

**Tests.** `tests/test_broad_phase_culling.py` gains chosen-frame
completeness over the existing boundary table and lattice, the clock-shaped
common-turn scenario, flush contact surviving the frame change, determinism,
the K, margin and tie rules, and a check that the support path still reads
world boxes.
`tests/test_adaptive_broad_phase.py` is unaffected.

**Docs.** `docs/architecture.md` (the broad-phase paragraph),
`docs/testing.rst` (the two "conservative world AABB" sentences),
`docs/changelog.rst` Unreleased, `docs/adrs/TEST-FRAMEWORK/ADR-091`,
`docs/adrs/README.md`, `workflow/warts.md` (rename the cycle, correct the
wording, mark it fixed with the measured numbers).

**Projects.** Nothing to change in any project. The originating project,
3DPrintedClocks `wall_clock_02`, is where this cycle's evidence is measured;
nothing is committed outside this framework repository.

**Downstream.** The remaining wall-clock-02 findings — `face-box-broad-phase`,
the mesh-distance tier and parallel pair booleans — are independent cycles.
The baseline this cycle measures against is the tree *after*
`quantise-verdict-memo` (2526 booleans, 533 s on the swing sweep), which is
this branch's base, `4f23dff`.
