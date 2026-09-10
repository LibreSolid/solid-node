## Context

ADR-029 gave every intersection-based assertion a conservative **world-axis**
AABB broad phase: the box of a solid's 8 local-bounds corners under its
composed world matrix (`_world_bounds`), culled pairwise by `_boxes_disjoint`
and swept by `_bounds_candidates` (ADR-040's sweep-and-prune, later made
axis-adaptive). It is exact-negative: disjoint boxes prove an empty
intersection, so the cull can only save work, never change a verdict.

A world-axis box is exact for an axis-aligned part and grows under rotation.
That is fine when parts are rotated individually. It is expensive when *every*
part shares one outermost turn, because then every box grows and no relative
information is gained by the inflation — the assembly is exactly as sparse as
it was, and the index no longer sees it.

The finding is `workflow/warts.md`, last section, "3DPrintedClocks wall clock
02 (2026-09-09, exact sweep cost)", second bullet, "A common rigid turn
inflates every world box": 53 topmost rigid solids, ~118 candidate pairs and
~19 s per sweep instant, essentially all of it `BRepAlgoAPI_Common`, versus
**69 pairs and 6.4 s** for the same model at `--set facing=0`.

### The finding's two imprecisions, corrected

The bullet says the clock "declares `facing = 45°` on its root" and names the
cycle `broad-phase-in-the-root-frame`. Reading
`projects/3DPrintedClocks/simulation/shared/assemblies.py`, `Clock.render()`
(~line 609) is:

```python
def render(self):
    for part in children_of(self):
        part.rotate(UPRIGHT, [1, 0, 0])
        part.rotate(self.facing, Z)
```

The turn is applied to **each direct child of the root**, not to the root. The
root carries no placement of its own, so "strip the root's placement" would
strip nothing and the cycle as named would have measured no improvement at
all. What is actually true — and sufficient — is that every topmost rigid
solid lies under one of those children and therefore shares one outermost
rigid turn. This cycle is renamed `broad-phase-indexing-frame` and the wart's
wording corrected to "on each child of its root". Both corrections are tasks
of this cycle; the planning commit may carry the rename.

The generalisation matters beyond the wording: a fix that reached only for the
root's own matrix would be defeated by any project that turns its assembly one
level down, which is what the originating project does. Choosing a frame from
the *solids* is indifferent to where the common turn was declared.

## Goals / Non-Goals

**Goals:**

- Cut the candidate pairs `assertNoSolidInterference` emits for an assembly
  under a common rigid turn, toward what the same assembly emits untuned.
- Keep the change exact-negative and verdict-identical, by construction and by
  test.
- Keep the frame choice deterministic for the same inputs, so a run is
  reproducible and a diagnostic order is stable.
- Leave the gravity-support assertion's world-frame reasoning untouched.

**Non-Goals:**

- Any public knob, flag, environment variable or assertion argument. K and the
  scoring rule are module constants and internal policy.
- Tighter bounds than an AABB (OBB, convex hull, face boxes). The face-box
  tier is its own filed cycle, `face-box-broad-phase`.
- The pair-level broad phases inside `_exact_verdict` and `_faceted_verdict`.
- Any change to the sweep itself (`_axis_order_and_pressure`,
  `_sweep_candidates`, `_bounds_candidates`), to `_world_bounds`, or to
  `_boxes_disjoint`.
- Any change to `assertAssemblySupported`, `assertNoPairwiseIntersections`,
  `assertNotIntersecting`, `assertFreeWithin`, `assertBlockedBeyond` or
  `assertJoined`.

## Decisions

### 1. The index's frame is free; the proof

**Claim.** Let `F` be any invertible affine frame and `A`, `B` two placed
solids with world matrices `M_A`, `M_B`. Let `box_F(X)` be the axis-aligned
box of `X`'s 8 local-bounds corners under `inv(F) @ M_X`. If `box_F(A)` and
`box_F(B)` are disjoint then `A ∩ B = ∅`.

**Proof.** `inv(F)` is an invertible affine map, so it carries the local box's
convex hull onto the convex hull of the images of its corners; the solid is
inside its local box, hence inside `box_F` (a superset of that hull). If the
two boxes are disjoint, the images `inv(F)·A` and `inv(F)·B` are disjoint. An
invertible map preserves intersection: `inv(F)·(A ∩ B) = (inv(F)·A) ∩
(inv(F)·B) = ∅`, so `A ∩ B = ∅`. ∎

Two consequences worth stating plainly, because they are what makes the change
safe:

- Box overlap **in any one common frame** remains a *necessary* condition for
  intersection. Completeness — "every pair that meets is emitted" — therefore
  holds in every candidate frame, not only in the world frame. The frame
  choice can only change *which superset* of the meeting pairs is emitted.
- Because the choice affects only the emitted set and its order, and every
  emitted pair is still settled by an exact same-kernel Boolean, **no verdict
  can change**. This is the same category of shortcut as ADR-029's cull and
  ADR-070/090's verdict memo: less work asked, the same answers.

The world frame is `F = I`, in which `box_I(X)` is exactly today's
`_world_bounds(local_bounds, M_X)`. So the world candidate is not an
approximation of today's behaviour — it *is* today's behaviour, bit for bit,
and it is candidate zero.

**The frame change is arithmetic, and arithmetic must be paid for.** The
proof above is exact; the floating-point evaluation of it is not. A world box
is one matrix product applied to eight corners. A frame box is an inversion
and two matrix products, each leaving on the order of `1e-13 × |coordinate|`
of residue. Two solids in exact flush face contact — non-empty at 0.0 mm³,
which the ratified completeness requirement counts as non-empty, and which the
clause "bounds that touch without overlapping SHALL be treated as a candidate
rather than culled" exists precisely for — can come out of that arithmetic
with boxes separated by `1e-13` in `F` and be culled, where the world index of
the same axis-aligned placement emits them exactly.

That exposure exists today only for individually rotated parts. A chosen frame
would extend it to **every axis-aligned flush pair in a turned assembly**,
which is a large and ordinary population: a clock's plates and pillars, a
printer's frame extrusions and brackets. It cannot change an interference
verdict — a flush pair's intersection is zero-volume and passes either way —
but it breaks the completeness requirement as ratified, and it would make the
chosen-frame completeness test over the boundary table (face, edge and vertex
contact under rotation) flaky at the bit level.

**Every non-world candidate's boxes are therefore padded by a fixed absolute
margin** before scoring or sweeping: `_INDEXING_FRAME_MARGIN = 1e-6` mm, a
module constant beside K. A padded box is `(low − margin, high + margin)`,
still a superset of the solid's placed geometry in that frame, so the proof of
§1 is untouched — padding only ever adds candidates. The value is a million
times the residue at metre scale and orders of magnitude below any clearance a
project would want culled on: it absorbs the arithmetic without absorbing
geometry.

**World boxes are not padded.** They are `record[2]`, produced by the same
single matrix product they are produced by today, so candidate zero stays
today's behaviour bit for bit. That asymmetry has a second, useful effect,
recorded here because the tests depend on it: on an assembly where an
axis-aligned solid's frame would produce the same boxes as the world frame,
the padded frame boxes have *strictly larger* volume, so the world frame wins
**strictly** rather than by the earliest-candidate tie rule. The tie rule
remains as the last resort it was, but the ordinary axis-aligned assembly is
now decided by the score itself.

**Only the rotational part of `F` matters.** `inv(F)` translates every corner
of every solid by the same vector, so box extents, total volume and overlap
relations are unchanged by `F`'s translation. The translation is carried
anyway, because a frame anchored on a real solid keeps the coordinates near
the assembly and avoids needless cancellation, and because "the placement
matrix of solid *i*" is a simpler thing to specify and to test than "its
rotational part".

### 2. The candidate frames: world, plus the K largest topmost solids

Candidates, in order:

0. the world frame (identity);
1..K. the composed world matrix `M_i` of each of the K largest topmost solids,
   ranked by the diagonal of their **local** bounds (`‖hi − lo‖`), descending,
   ties broken by selection index ascending.

**K = 3**, as `_INDEXING_FRAME_CANDIDATES = 3` beside
`_ADAPTIVE_CANDIDATE_BUFFER_LIMIT`, with the same comment discipline: an
internal tuning value, not a public assertion-control knob.

*Why the largest solids.* The frame or base of a machine is usually its
largest single part, and it is the part everything else is aligned to: plates,
chassis, bed, spine. A part that dominates the assembly's extent is also the
part whose own box inflation costs the most, and the part most likely to be
squarely aligned with the lattice the designer laid the mechanism out on. In
the originating clock the fused frame — both plates and their pillars, one
solid — is exactly that part, and it is the part the wheels, arbors and
pillars are all parallel or perpendicular to. Choosing its frame is choosing
the designer's own working axes without asking the project to declare them.

Local-bounds diagonal, not placed-box volume, is the size measure: it is a
property of the part itself, independent of where it currently sits and of the
very inflation this cycle is fighting, so the candidate list does not change
as the assembly turns. It is also already available — `_solid_geometry` reads
local bounds for every solid regardless.

*Why also the world frame.* It costs nothing (its boxes are already computed
for the placement records), it is the right answer for the ordinary
axis-aligned assembly, and keeping it as candidate zero with the earliest-wins
tie rule means an assembly that gains nothing from this change is indexed
exactly as it is today.

*Why not all N frames.* Scoring N frames is `N² × 8` corner transforms —
22,472 for the clock's 53 solids, still cheap in absolute terms, but the
scoring cost then grows quadratically with assembly size while the win does
not, and it buys little: after the two or three largest parts the candidate
frames are near-duplicates of one another. K = 3 keeps the scoring cost linear
in N.

### 3. The score: smallest total padded box volume, earliest candidate wins ties

For each candidate frame `F`, compute every solid's box in `F` — **padded by
`_INDEXING_FRAME_MARGIN` for every non-world candidate, per §1** — and score
`Σ_i vol(box_F(i))`, the product of the three extents summed over all solids.
The lowest score wins; on an exact tie the earlier candidate wins, so world
beats solid 1 beats solid 2 beats solid 3.

The boxes that are scored are the boxes that are swept: a frame is scored on
what it would actually hand `_bounds_candidates`, padding included, so a frame
whose margin costs more than its de-rotation saves loses on its own merits.
Because the world candidate is unpadded and every other is padded, an
axis-aligned assembly's world frame wins **strictly**, not by the tie rule
(§1).

*Why total volume.* The quantity that actually matters is the number of
overlapping box pairs, but computing it per candidate frame is running the
sweep K + 1 times. Total box volume is the standard cheap proxy: the expected
number of overlapping pairs of boxes scattered in a region rises with the
boxes' volumes, and a frame that inflates every box necessarily raises the
sum. It is a single float per frame, needs no sorting, is deterministic under
IEEE 754 given a fixed summation order (solids in selection order), and is
comparable across frames because a common rigid frame change preserves the
*true* geometry's volume while changing only the boxes' — so the sum is
measuring exactly the inflation and nothing else.

*Why a proxy is acceptable.* The score is a heuristic and may occasionally
pick a frame that emits more pairs than another candidate would. That is a
performance miss, never a correctness one: the requirement this change is held
to is completeness and determinism, not minimality. Stating the guarantee as
"no worse than world" would be a promise the heuristic cannot keep, so the
spec does not make it; the clock-shaped scenario pins the case that motivated
the cycle instead.

*Degenerate boxes.* A flat (zero-extent) solid contributes volume 0 in the
unpadded world frame. An assembly of only such solids scores 0 in the world
frame and a small positive number in every padded candidate, so it falls to
world — today's behaviour — which is the safe resolution. (Before padding this
was a tie resolved by the earliest-candidate rule; it is now a strict win, and
the tie rule is no longer what carries the case.) A
half-perimeter (surface-area heuristic) score would discriminate among flat
assemblies; it was rejected as extra machinery for a case with no evidence
behind it, and it is a one-line change if evidence ever appears.

*Guards.* A candidate frame whose matrix cannot be inverted, or whose
inversion or resulting boxes contain a non-finite entry, is **dropped from the
candidate list** rather than scored. If every solid frame is dropped, the world
frame remains and the index behaves exactly as today. This is the same failure
direction the verdict memo takes for a non-finite relative matrix (ADR-090):
degrade to the old behaviour, never to a wrong one.

*Determinism.* Every input to the choice is a deterministic function of the
selected solids in selection order: the candidate list (size rank, ties by
index), the boxes, the summation order, and the earliest-wins tie rule. The
same inputs choose the same frame and emit the same ordered pairs, which is
what the assertion's diagnostic order depends on.

### 4. Scope: exactly one call site

`assertNoSolidInterference` currently indexes on `[item[2] for item in
solids]`. It will instead build the boxes in the chosen frame and pass those
to `_bounds_candidates`. Nothing else about the assertion changes: the same
sweep, the same candidate order semantics, the same `_candidate_intersection`
per pair, the same message.

**The placement records keep their world bounds at index 2**, and every
consumer of them is untouched:

- `_gravity_extent(bounds, unit_gravity)` projects a box onto the **world**
  gravity direction. It is only meaningful for a world-axis box.
- `_grounded_seeds` compares those projections to find the solids nearest the
  assembly's furthest extent along gravity.
- `_virtual_floor` builds a slab from the world-axis min/max of every box and
  from the same furthest extent.
- `_support_candidates` sweeps dropped boxes against placed boxes, where the
  drop is a world-frame translation folded into the matrix.

Gravity is a world-frame fact (ADR-048), and the support graph's seeds and
floor are defined in terms of it (ADR-040 fixed the selection those records
describe). Re-framing those boxes would change *which solids are seeded* and
*where the floor is* — real behavioural changes to a ratified assertion, in a
cycle whose whole claim is that nothing behavioural changes. So the support
path stays world-axis, and this cycle does not touch its requirements.

**Out of scope, recorded as a follow-up.** `_exact_verdict` and
`_faceted_verdict` each run their own two-box cull before the Boolean. For a
*pair*, the natural indexing frame is the first solid's own frame: in it, that
solid's box is exact (its untransformed local box), and only the second solid's
box is inflated — strictly better than inflating both on world axes, and it
composes with the relative matrix the memo already forms. It is left out here
because it is a different call path with its own tests and its own measurement,
and because folding it in would blur what this cycle's numbers mean. Whoever
takes it must take the margin with it: the same frame-change arithmetic
applies, and a pair-level cull that separates a flush contact by `1e-13` would
skip a Boolean the ratified requirement expects to be run.

### 5. Plumbing: the assertion needs each solid's local bounds

A box in frame `F` needs `(local_bounds, M_i)`. The matrix is already
`record[6]`; the local bounds are read by `_solid_geometry` and consumed by
`_place_solid`, then dropped.

**Decision: append the local bounds as `record[7]`.** `_place_solid` returns
`(solid, deferred_manifold, world_bounds, placed_shape, faceted_identity,
exact_identity, matrix, local_bounds)`.

- No existing tuple position moves, so every index-2/3/4/5/6 reader —
  `_candidate_intersection`, `_placed_intersection`, `_record_key`,
  `_gravity_extent`'s callers, `_virtual_floor`, `_support_candidates` — is
  unchanged.
- `_record_key`'s `len(record) <= 6` guard still separates the virtual floor
  (a 4-tuple with no geometry identity) from a real placement record (now an
  8-tuple). The guard's *meaning* is "this record was not built by
  `_place_solid`", and appending keeps that true; the task list will restate
  the guard's intent in its comment so a future field does not silently
  invalidate it.
- `_dropped_assembly_solids` gets the field for free, which is what a later
  pair-level or support-side use would need.
- The two `_place_solid` call sites already have `local_bounds` in hand; no
  extra cache read, no extra geometry work.

*Alternatives considered.* (a) `_placed_assembly_solids` returning
`(records, geometries)` — a second return value only one caller wants, and it
would need a change in `tests/test_persistent_piece_facts.py`, which calls
`_placed_assembly_solids` directly. (b) Re-deriving local bounds in the
assertion via `_cached_local_bounds` — a second cache read per solid per
assertion call for data the record already had. (c) A dataclass or namedtuple
for placement records — the right long-term shape, and out of proportion here:
it touches every index reader and would bury this cycle's actual change.

### 6. What the adaptive-sweep requirement means here

"Broad-phase work adapts to sparse orientation without changing candidates or
order" is a contract about the sweep *given a set of conservative AABBs*: it
must estimate pressure on X/Y/Z, pick the least-pressure axis, and emit
exactly the pairs and the order the legacy X sweep would emit **for those
boxes**. That contract is about the boxes it is handed, not about which frame
produced them, and this cycle hands it a different set of boxes for one
assertion. The requirement is therefore **unchanged and not modified by this
cycle**, and `tests/test_adaptive_broad_phase.py` needs no edit.

### 7. Cost

Per `assertNoSolidInterference` call: K × N × 8 corner transforms for the
solid-frame candidates (the world candidate reuses `record[2]`), K 4×4 matrix
inversions, K × N box paddings (two vector additions each), and K × N volume
products, plus a partial sort of N diagonals.
For the clock's N = 53 and K = 3 that is 1,272 corner transforms — a handful of
small NumPy operations against a per-instant budget in which a *single*
`BRepAlgoAPI_Common` costs 0.1–2.2 s. The measurement in evidence.md is
expected to show the scoring cost invisible beside the booleans saved; if it
does not, the number is recorded as it is rather than argued away.

## Risks / Trade-offs

- **[The heuristic picks a worse frame than world for some assembly]** → The
  world frame is always a candidate and always scored, so a frame is chosen
  over world only when its total box volume is strictly smaller. Volume is a
  proxy for pair count, so a regression is possible in principle; it is bounded
  in practice by the fact that a frame with smaller total box volume has
  smaller boxes, and it can only ever cost booleans, never correctness. Any
  measured regression is a follow-up on the score, not on the frame.

- **[A frame chosen from a *moving* solid changes between instants]** → It
  can, and that is admissible: the choice is per assertion call, and the
  assertion's contract is per call. The consequence to watch is that the
  emitted pair *order* can differ between two instants of a sweep, so a
  failure's "first offending pair" may differ from the one an earlier instant
  would have named. Verdicts do not change — every emitted pair is still
  settled exactly, and the set is still a superset of the meeting pairs — but
  the task list makes this explicit in the ADR's consequences. Choosing the
  frame from the *largest* solid makes the frame stable in the common case,
  since the largest part of a machine is usually its stationary frame.

- **[Verdict-memo interaction]** → None. The memo (ADR-070/090) keys on the
  relative matrix, which is a property of the pair and not of the index. A
  pair not emitted is a boolean not asked; a pair emitted is asked exactly as
  before. Fewer candidates means fewer memo asks and possibly a different
  hit/ask ratio in the evidence — worth noting when comparing to the
  `quantise-verdict-memo` baseline, so the two cycles' numbers are not
  conflated.

- **[Non-rigid placements]** → The proof needs only invertibility, so a mirror
  or a uniform scale in a placement chain is fine. A singular matrix is
  guarded (§3) by dropping the candidate.

- **[The margin culls a real pair]** → It cannot: padding only ever ENLARGES a
  box, so it can only add candidates, never remove one. The cost direction is
  the other one — a pair whose true gap in the chosen frame is under
  `1e-6` mm is emitted and pays a Boolean it would not have paid on world
  axes. At that scale the pair is flush contact or an unprintable clearance,
  and the assembly would have to be built out of such gaps for it to matter.
  This is why the spec scenario for the common turn asserts equality only for
  a fixture whose gaps are macroscopic, and does not promise "never more pairs
  than the un-turned world index" in general.

- **[The size ranking misses the part the finding is about]** → Real and
  unverified. Clock 2's longest solids by local-bounds diagonal are plausibly
  the pendulum and the weight's line — long, thin parts — rather than the
  fused plates that the finding identifies as the frame everything is aligned
  to. If the plates rank fourth at K = 3, the chooser never sees them and
  picks the pendulum's frame, tilted by the swing angle. That may still win
  handsomely (a few degrees of tilt inflates far less than 45°), but the cycle
  must not discover it by accident. Task 5 therefore requires the candidate
  ranking, the chosen frame and every candidate's score to be recorded at the
  measured instant. **If the plates are not among the candidates, that is
  reported in `evidence.md` as a finding about K — the implementer does not
  raise K to chase the number.** Whether K changes is the pilot's decision
  after seeing the numbers, and a follow-up if it is taken: a diagonal is a
  proxy for "the part everything is aligned to", and a long thin part is
  exactly where that proxy is weakest. A bounding-box VOLUME or the count of
  solids whose frames are parallel to a candidate would be the alternatives
  to weigh then, on evidence, rather than now on a guess.

- **[Someone later re-frames the support boxes by analogy]** → The ADR and the
  code comment both state why record[2] is world-axis and must stay so, and a
  test pins the support path reading world boxes.

## Migration Plan

None: no public surface, no persisted artifact, no project source change. The
change is one call site behind an unchanged assertion signature; reverting is
reverting the commit.

## Open Questions

One, deliberately left open for the pilot and answered with evidence rather
than a guess: **whether K = 3 reaches the clock's fused plates.** Task 5
records the ranking and the scores; raising K is the pilot's call on those
numbers, not the implementer's.

Judgement calls made here in the absence of the pilot, all
reversible and all recorded above: K = 3; the size measure is the local-bounds
diagonal; the score is total padded box volume with earliest-candidate
tie-breaking; non-world candidates are padded by `1e-6` mm and the world
candidate is not;
degenerate and singular frames are dropped rather than specially scored; the
local bounds travel as `record[7]`; the frame is chosen per assertion call
rather than pinned for a sweep.

## ADR-091 outline (for the implementer)

`docs/adrs/TEST-FRAMEWORK/ADR-091-the-broad-phase-chooses-its-indexing-frame.md`

- **Status:** Accepted. **Date:** 2026-09-10.
  **Extends:** ADR-029 (manifold cache and AABB broad phase).
  **Related:** ADR-040 (topmost rigid assembly integrity; completeness proved
  by framework tests, not re-checked at runtime), ADR-048 (gravity support
  graph — why *its* boxes stay world-axis), ADR-090/ADR-070 (the sibling
  exact-negative shortcut and its key), ADR-025 (verdict semantics that must
  not move).
- **Context and Problem Statement:** the wall-clock-02 measurement, the
  corrected reading of `Clock.render()`, and the observation that a world-axis
  box is exact for an axis-aligned part and inflated by up to √2 in the plane
  of a 45° turn — so a *common* turn costs every box and gains no relative
  information.
- **Decision Drivers:** never change a verdict; no new public knob; keep the
  choice deterministic; leave the gravity frame alone; keep the scoring cost
  linear in N.
- **Considered Options:** (i) strip the root node's own placement — rejected,
  it does not describe the originating project and is defeated by a turn
  declared one level down; (ii) an OBB or PCA frame over all solids — rejected,
  it is not a frame any part is actually aligned to, it needs an eigen
  decomposition per call, and its determinism under degenerate spectra is
  fragile; (iii) index in every solid's frame and take the best — rejected,
  quadratic scoring for a near-duplicate candidate set; (iv) let the project
  declare an indexing frame — rejected, it makes a performance detail a public
  contract and invites a project to declare a wrong one; (v) **world plus the
  K largest solids' frames, scored by total box volume — chosen.**
- **Decision Outcome:** §§1–3 of this design, with the proof in §1 stated in
  full — it is the load-bearing paragraph of the whole record — and with the
  margin stated beside it: the proof is exact, its floating-point evaluation
  is not, and a frame box carries an inversion and two products of residue
  where a world box carries one product. Non-world candidates are padded by
  `1e-6` mm so a flush contact under a common turn stays a candidate; world
  boxes are unpadded, so candidate zero is today's boxes bit for bit and the
  ordinary axis-aligned assembly wins the score strictly.
- **Consequences:** fewer candidate pairs for a commonly-turned assembly (the
  evidence.md numbers); a pair whose gap in the chosen frame is under the
  margin is emitted where a world-axis index of an axis-aligned placement
  would have culled it — the cost direction of padding, and the reason the
  record claims completeness rather than minimality; the size ranking is a
  proxy for "the part everything is aligned to" and is weakest for long thin
  parts, with the clock's own ranking recorded in the evidence; an assembly that gains nothing is indexed exactly as
  today because world is candidate zero and wins ties; the emitted pair order
  may differ between instants when the chosen frame moves, so a failure may
  name a different offending pair than it would have before — verdicts
  unchanged; the support graph keeps world boxes, and this is deliberate, not
  an oversight; the pair-level culls in `_exact_verdict`/`_faceted_verdict`
  remain world-axis and are a named follow-up.
- **References:** `workflow/warts.md` last section; this change directory;
  `tests/test_broad_phase_culling.py`.
