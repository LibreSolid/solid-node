# ADR-091: The Broad Phase Chooses Its Indexing Frame

**Status:** Accepted
**Date:** 2026-09-10
**Extends:**
- [ADR-029: Manifold Cache and AABB Broad Phase for Assertions](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)

**Related to:**
- [ADR-040: Topmost-Rigid Assembly Integrity](./ADR-040-topmost-rigid-assembly-integrity.md) —
  completeness is proved by framework tests, not re-checked at runtime.
- [ADR-048: Gravity Support Graph Assertion](./ADR-048-gravity-support-graph-assertion.md) —
  why the support graph's own boxes stay world-axis.
- [ADR-070: Relative Placement as the Identity of an Intersection
  Question](./ADR-070-relative-placement-as-the-identity-of-an-intersection-question.md) /
  [ADR-090: The Placement Quantum Is a Property of the Test
  Run](./ADR-090-the-placement-quantum-is-a-property-of-the-test-run.md) —
  the sibling exact-negative shortcut and its key.
- [ADR-025: Perturbation-Based Kinematic Fit
  Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md) —
  verdict semantics that must not move.

## Context and Problem Statement

`assertNoSolidInterference` indexes its candidate pairs on conservative
**world-axis** AABBs (ADR-029): the box of a solid's 8 local-bounds
corners under its composed world matrix. That box is exact for an
axis-aligned, unrotated part and grows under rotation — up to √2 in the
plane of a 45° turn. Growth is harmless when parts are rotated
individually; it is expensive when **every** part shares one outermost
rigid turn, because then every box grows and no relative information is
gained by the inflation — the assembly is exactly as sparse as it was,
and the index no longer sees it.

Measured on 3DPrintedClocks `wall_clock_02`
(`workflow/warts.md`, "3DPrintedClocks wall clock 02 (2026-09-09, exact
sweep cost)", second bullet): 53 topmost rigid solids, ~118 candidate
pairs from the world-AABB broad phase and ~19 s per sweep instant,
essentially all of it `BRepAlgoAPI_Common`. The same model driven with
`--set facing=0` — the same geometry and clearances, only without the
common turn — yields 69 candidate pairs and 6.4 s per instant.

That finding's own wording named the wrong site: it said the clock
"declares `facing = 45°` on its root" and filed the fix as
`broad-phase-in-the-root-frame`. Reading `Clock.render()`
(`projects/3DPrintedClocks/simulation/shared/assemblies.py`, ~line 609),
the turn is applied to **each direct child of the root**, not to the
root itself:

```python
def render(self):
    for part in children_of(self):
        part.rotate(UPRIGHT, [1, 0, 0])
        part.rotate(self.facing, Z)
```

The root carries no placement of its own, so "strip the root's
placement" would strip nothing and would have measured no improvement
at all. What is actually true, and sufficient, is that every topmost
rigid solid lies under one of those children and therefore shares one
outermost rigid turn — wherever it was declared. This cycle is
`broad-phase-indexing-frame`, and `workflow/warts.md`'s wording is
corrected to "declares `facing` on each child of its root".

## Decision Drivers

- Never change a verdict: a shortcut here must remain exact-negative,
  in the same sense ADR-029's own broad phase is.
- No new public knob, flag, environment variable, or assertion
  argument.
- Keep the frame choice deterministic for the same inputs, so a run is
  reproducible and a diagnostic pair order is stable.
- Leave the gravity-support assertion's world-frame reasoning
  untouched.
- Keep the scoring cost linear in the number of solids.

## Considered Options

1. Strip the root node's own placement — rejected: it does not
   describe the originating project (the turn is declared one level
   down) and is defeated by any project that turns its assembly the
   same way.
2. An OBB or PCA frame fit over all solids — rejected: not a frame any
   part is actually aligned to, needs an eigendecomposition per call,
   and its determinism under a degenerate spectrum (a perfectly
   symmetric assembly) is fragile.
3. Index in every solid's own frame and keep the best — rejected:
   quadratic scoring cost, and past the two or three largest parts the
   candidate frames are near-duplicates of one another.
4. Let the project declare an indexing frame — rejected: turns a
   performance detail into a public contract, and invites a project to
   declare a wrong one.
5. **World plus the K largest solids' frames, scored by total padded
   box volume — chosen.**

## Decision Outcome

Chosen: **world plus the K largest topmost solids' own placement
frames, scored by total box volume, world unpadded and every other
candidate padded by a fixed margin.**

### 1. The index's frame is free; the proof

Let `F` be any invertible affine frame and `A`, `B` two placed solids
with world matrices `M_A`, `M_B`. Let `box_F(X)` be the axis-aligned box
of `X`'s 8 local-bounds corners under `inv(F) @ M_X`. **Claim:** if
`box_F(A)` and `box_F(B)` are disjoint then `A ∩ B = ∅`.

**Proof.** `inv(F)` is an invertible affine map, so it carries the local
box's convex hull onto the convex hull of the images of its corners; the
solid is inside its local box, hence inside `box_F` (a superset of that
hull). If the two boxes are disjoint, the images `inv(F)·A` and
`inv(F)·B` are disjoint. An invertible map preserves intersection:
`inv(F)·(A ∩ B) = (inv(F)·A) ∩ (inv(F)·B) = ∅`, so `A ∩ B = ∅`. ∎

Box overlap in **any one common frame** therefore remains a *necessary*
condition for intersection — completeness holds in every candidate
frame, not only the world frame — so the frame choice can only change
*which superset* of the meeting pairs is emitted, never drop one that
meets, and never change a verdict: every emitted pair is still settled
by an exact same-kernel Boolean. `F = I` gives exactly today's
`_world_bounds`, bit for bit, so the world candidate is not an
approximation of today's behaviour — it *is* today's behaviour, and it
is candidate zero.

**The proof is exact; its floating-point evaluation is not.** A world
box is one matrix product applied to eight corners. A frame box is an
inversion and two matrix products, each leaving on the order of
`1e-13 × |coordinate|` of residue. Two solids in exact flush contact —
non-empty at 0.0 mm³, which the ratified completeness requirement counts
as a candidate that must still be emitted — could come out of that
arithmetic separated by residue and be culled, where the world index of
the same axis-aligned placement emits them exactly. That exposure exists
today only for individually rotated parts; a chosen frame would extend
it to every axis-aligned flush pair in a turned assembly.

**Every non-world candidate's boxes are therefore padded by a fixed
absolute margin, `_INDEXING_FRAME_MARGIN = 1e-6` mm**, before scoring or
sweeping. A padded box is still a superset of the solid's placed
geometry in that frame, so the proof above is untouched — padding only
ever adds candidates. World boxes are **not** padded: they are
`record[2]`, produced by the same single matrix product as today, so
candidate zero stays bit for bit unchanged. That asymmetry has a second
effect the tests depend on: on an assembly where a solid's own frame
would reproduce the world boxes exactly, the padded candidate scores
*strictly* larger, so the world frame wins **strictly**, not by the
tie rule.

Only the rotational part of `F` matters — `inv(F)`'s translation shifts
every corner of every solid by the same vector, changing neither box
extents, nor total volume, nor overlap relations. The translation is
carried anyway because a frame anchored on a real solid keeps
coordinates near the assembly, and because "the placement matrix of
solid *i*" is simpler to specify and test than "its rotational part
alone".

### 2. The candidates: world, plus the K largest topmost solids

Candidates, in order: the world frame (identity), then the composed
world matrix of each of the `_INDEXING_FRAME_CANDIDATES = 3` largest
topmost solids, ranked by the diagonal of their **local** bounds,
descending, ties broken by selection index ascending. `K = 3` is a
module constant beside `_ADAPTIVE_CANDIDATE_BUFFER_LIMIT` — an internal
tuning value, not a public knob.

The frame or base of a machine is usually its largest single part, and
the part everything else is aligned to. Local-bounds diagonal — not
placed-box volume — is the size measure: a property of the part itself,
independent of where it currently sits and of the very inflation this
cycle fights, so the candidate list does not change as the assembly
turns, and it is already available (`_solid_geometry` reads local
bounds for every solid regardless). World is always a candidate because
it costs nothing extra (its boxes are `record[2]`, already computed),
it is the right answer for an ordinary axis-aligned assembly, and
keeping it as candidate zero with the earliest-wins tie rule means an
assembly that gains nothing from this change is indexed exactly as it
is today. Not all N frames: scoring cost would grow quadratically with
assembly size for a win that saturates after the two or three largest
parts.

### 3. The score: smallest total padded box volume, earliest candidate wins ties

For each candidate frame, compute every solid's box in that frame —
padded for every non-world candidate — and score the sum of the three
extents' product over all solids. The lowest score wins; on an exact
tie the earlier candidate wins (world, then rank 1, rank 2, rank 3).
Total box volume is the standard cheap proxy for the pair count a frame
would actually emit: it is a single float per frame, needs no sorting,
is deterministic under IEEE 754 given a fixed summation order, and a
common rigid frame change preserves the *true* geometry's volume while
changing only the boxes' — so the sum measures exactly the inflation.
The score is a heuristic, not a guarantee of minimality: it may
occasionally choose a frame that emits more pairs than another
candidate would, which is a performance miss, never a correctness one.

A candidate frame whose matrix cannot be inverted, or whose inverse or
resulting boxes carry a non-finite entry, is dropped from the candidate
list rather than scored. If every solid candidate is dropped, world
remains and the index behaves exactly as today — the same failure
direction ADR-090 takes for a non-finite relative matrix: degrade to
the old behaviour, never to a wrong one.

### 4. Scope: exactly one call site

Only `assertNoSolidInterference`'s call to `_bounds_candidates` changes,
now indexing on `_indexing_frame_boxes(solids)` instead of
`[item[2] for item in solids]`. The placement records keep their world
bounds at `record[2]`, and every other reader of a placement record is
unchanged: `_gravity_extent`, `_grounded_seeds`, `_virtual_floor` and
`_support_candidates` all read `record[2]` on world axes, because
gravity is a world-frame fact (ADR-048) and the support graph's seeds
and floor are defined in terms of it. Re-framing those boxes would
change *which solids are seeded* and *where the floor is* — a real
behavioural change to a ratified assertion, in a cycle whose whole claim
is that nothing behavioural changes. The pair-level broad phases inside
`_exact_verdict` and `_faceted_verdict` are also out of scope, and
remain world-axis; the natural frame for a two-solid cull would be the
first solid's own (only the second box then inflates), but it is a
different call path with its own tests, left as a named follow-up.

### 5. Plumbing: local bounds travel as `record[7]`

A box in frame `F` needs `(local_bounds, M_i)`. The matrix is already
`record[6]`; `_place_solid` now appends the local bounds it already had
in hand as `record[7]`, so `_placed_assembly_solids` returns
`(solid, deferred_manifold, world_bounds, placed_shape, faceted_identity,
exact_identity, matrix, local_bounds)`. No existing tuple position
moves, so every index-2/3/4/5/6 reader is unchanged, and
`_record_key`'s `len(record) <= 6` guard — whose meaning is "this
record was not built by `_place_solid`" — still separates the virtual
floor (a 4-tuple) from a real placement record (now an 8-tuple).

## Consequences

- Fewer candidate pairs for a commonly-turned assembly; the measured
  numbers (before/after candidate counts, the chooser's own ranking and
  scores, and the swing-sweep boolean/wall-time comparison) are in
  `evidence.md` of the `broad-phase-indexing-frame` OpenSpec change.
- A pair whose gap in the chosen frame is under `_INDEXING_FRAME_MARGIN`
  is emitted where a world-axis index of the same axis-aligned placement
  would have culled it — the cost direction padding takes, and the
  reason this record claims completeness, not minimality.
- The size ranking is a proxy for "the part everything is aligned to"
  and is weakest for long, thin parts (large diagonal, small
  cross-section); whether `K` should change on evidence from a specific
  project is left to the pilot, recorded as an open question in
  design.md and in the evidence for this cycle.
- An assembly that gains nothing from the frame choice is indexed
  exactly as today, because world is candidate zero, unpadded, and wins
  ties.
- The emitted pair order can differ between two instants of a sweep
  when the chosen frame moves (a candidate is a *moving* solid's own
  frame) — a failure's "first offending pair" may name a different pair
  than an earlier instant would have. Verdicts do not change; only the
  order of an otherwise-identical superset can.
- The support graph keeps world boxes; this is deliberate (ADR-048),
  not an oversight, and is pinned by a test reading `record[2]` back
  against `_world_bounds(record[7], record[6])`.
- The pair-level culls in `_exact_verdict`/`_faceted_verdict` remain
  world-axis and are a named follow-up, not part of this change.
- No interaction with the verdict memo (ADR-070/090): the memo keys on
  the relative matrix, a property of the pair, not of the index. Fewer
  candidates means fewer memo asks and a different hit/ask ratio, which
  is not comparable across the two cycles' evidence for that reason.

## References

- `solid_node/test.py` — `_INDEXING_FRAME_CANDIDATES`,
  `_INDEXING_FRAME_MARGIN`, `_framed_bounds`, `_ranked_solid_candidates`,
  `_indexing_frame_boxes`, `assertNoSolidInterference`
- `tests/test_broad_phase_culling.py` — the chosen-frame completeness,
  clock-shaped scenario, flush-contact, determinism, candidate-set,
  strict-preference/tie-rule, guard, and no-regression tests
- `workflow/warts.md` — "3DPrintedClocks wall clock 02 (2026-09-09,
  exact sweep cost)"
- OpenSpec change `broad-phase-indexing-frame`, capability
  `test-framework`
