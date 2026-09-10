## 1. Red first: the index in a chosen frame

Everything here lands in `tests/test_broad_phase_culling.py`, whose existing
`Placement`, `translation`, `rotation_z`, `intersecting_pairs`,
`emitted_pairs` and `box_overlapping_pairs` helpers already build exactly the
fixtures these tests need. Extend the module docstring and the
"Broad-phase completeness" comment block with the indexing-frame obligation
and its one-paragraph proof (design.md §1) — the comment block is where this
module explains *why* its coverage is enumerated rather than generated, and
the frame argument belongs beside it.

- [x] 1.1 Test helpers: `assembly_records(placements)` building real
  `_place_solid` records from a list of `Placement`s (a `FakeNode`-shaped
  `solid`, the STL the fixture already writes, each placement's local bounds
  and matrix), and `assembly_emitted_pairs(records)` calling whatever seam the
  assertion uses to index — so the tests exercise the assertion's own path,
  not a reimplementation of it. Keep `emitted_pairs` as it is: it is the
  world-axis reference the new tests compare against.
- [x] 1.2 `IndexingFrameCompletenessTest`: run `BoundaryTableCompletenessTest`'s
  full `cases()` table and `LatticeCompletenessTest`'s 64-placement lattice
  through the chosen-frame index, asserting `truth <= emitted` against the same
  `intersecting_pairs` brute force. Assert containment, never equality — the
  index is free to emit extra pairs (design.md §3). RED on the current tree
  only insofar as the seam does not exist; once green it is the standing proof
  that the frame choice cannot drop a meeting pair.
- [x] 1.3 A bound taken in a non-world frame encloses the placed geometry
  expressed in that frame: build a rotated `Placement`, take its box under
  `inv(F) @ M` for a rotated `F`, and compare against the bounding box of
  `placement.placed.transform(inv(F)[:3, :4])`, the same shape
  `WorldBoundsConservativeTest` uses for the world case.
- [x] 1.4 **The clock-shaped scenario.** An assembly of several boxes whose
  LARGEST is axis-aligned and whose others are laid out so that, after a
  common 45° turn about Z applied to every solid, at least two pairs' world
  boxes overlap while their boxes in the largest solid's frame do not. Assert,
  in one test: the world-axis index of the turned assembly emits those pairs;
  the assembly assertion's chosen-frame index does not; the emitted set of the
  turned assembly equals the world-axis emitted set of the UN-turned assembly
  (they are the same boxes, by construction, and the fixture's gaps are
  macroscopic — orders of magnitude above `_INDEXING_FRAME_MARGIN` — so the
  enlargement cannot add a pair here); and `assertNoSolidInterference`
  passes on both the turned and the un-turned assembly with no message. Build
  the fixture from `Placement` and `rotation_z(45)`, and assert the fixture's
  own premises first (`assertFalse(_boxes_disjoint(...))` on world boxes,
  `assertTrue` on frame boxes) so a fixture that stops exercising the point
  fails loudly rather than passing vacuously. RED on the current tree.
- [x] 1.5 **Flush contact survives the frame change.** Take the
  `face_contact` and `edge_contact` cases from
  `BoundaryTableCompletenessTest.cases()` — axis-aligned cubes at exactly 2.0
  offsets, whose intersection is non-empty with zero volume — put them in one
  assembly with a LARGER axis-aligned solid so the chooser has a frame to
  pick, then place every solid by a common 45° turn about Z. Assert the chosen
  frame is that largest solid's (not world), and that BOTH contact pairs are
  emitted. Then assert the failure this test exists to catch: with the
  enlargement removed (patch `_INDEXING_FRAME_MARGIN` to `0`), at least one of
  them is culled — the bit-level exposure design.md §1 describes, pinned so
  the margin cannot be quietly dropped later. If the zero-margin case happens
  not to cull on this machine's arithmetic, say so in the commit message and
  keep the positive half of the test; do not tune the fixture until it breaks.
  RED on the current tree.
- [x] 1.6 Determinism: the same records indexed twice choose the same frame
  and yield the same ORDERED list of pairs (compare lists, not sets); and a
  permutation of the input order that leaves the size ranking intact chooses
  the same geometric frame.
- [x] 1.7 The candidate set, the strict preference, and the tie rule: with
  `K = 3`, exactly the world frame and the three largest solids by
  local-bounds diagonal are scored (pin by asserting the chooser's candidate
  list, or by patching the box builder and counting the frames it is called
  with); a fourth, larger solid displaces the third from the candidate list;
  and an axis-aligned assembly — where an axis-aligned solid's frame produces
  the same boxes as the world frame before enlargement — chooses the WORLD
  frame because the padded candidate scores STRICTLY higher, not because of
  the tie rule. Assert the strict inequality of the two scores directly, so
  the test says which mechanism decided it (design.md §1, §3). Keep a separate
  assertion for the tie rule itself, driving the chooser with two candidates
  whose scores are exactly equal, so the last-resort rule is still pinned.
- [x] 1.8 Guards: a candidate solid whose placement matrix is singular is
  dropped from the candidate list rather than raising or producing non-finite
  boxes, and an assembly whose every solid frame is singular indexes exactly as
  the world-axis index does.
- [x] 1.9 An axis-aligned assembly is indexed EXACTLY as today: assert the
  chosen-frame emitted pairs equal `emitted_pairs(...)` on the same placements,
  as an ordered list, AND that the boxes the index swept are bit-for-bit the
  records' `record[2]` — unpadded, one matrix product, today's boxes. This is
  the no-regression pin for the ordinary project.
- [x] 1.10 The support path still reads world boxes. Assert directly that a
  `_place_solid` record's index-2 bounds equal
  `_world_bounds(record[7], record[6])` — world axes, no frame applied — and
  name the existing statics tests that would break if they moved:
  `tests/test_assembly_supported.py`
  `GroundSeedTest.test_default_seeds_are_the_solids_at_the_furthest_extent`,
  `DropSupportTest.test_gravity_direction_selects_which_solids_are_held`, and
  `BroadPhaseTest.test_only_bounds_overlapping_pairs_are_intersected`. Run
  those three explicitly in task 3.5 and record that they were run.
- [x] 1.11 Every existing test in `tests/test_broad_phase_culling.py` and
  `tests/test_adaptive_broad_phase.py` stays green as written, unedited. If one
  needs editing, stop: it means the change reached further than design.md §4
  says it does.

## 2. Implementation

- [x] 2.1 `solid_node/test.py`: `_INDEXING_FRAME_CANDIDATES = 3` and
  `_INDEXING_FRAME_MARGIN = 1e-6` beside `_ADAPTIVE_CANDIDATE_BUFFER_LIMIT`,
  with the same comment discipline — internal tuning values, not public
  assertion-control knobs. The margin's comment states what it absorbs (an
  inversion and two matrix products of residue, where a world box carries one
  product), that it can only add candidates, and that world boxes are never
  padded.
- [x] 2.2 `_framed_bounds(local_bounds, matrix, inverse_frame)` beside
  `_world_bounds`: the AABB of the eight local corners under
  `inverse_frame @ matrix`. Implement `_world_bounds` in terms of it or leave
  `_world_bounds` alone — do NOT change `_world_bounds`'s signature or
  behaviour; it is read by `_exact_verdict`, `_faceted_verdict`,
  `_place_solid` and `_virtual_floor`.
- [x] 2.3 `_indexing_frame_boxes(records)` (or equivalently named): build the
  candidate frame list per design.md §2, score each per §3, and return the
  chosen frame's boxes in record order. Every NON-WORLD candidate's boxes are
  enlarged by `_INDEXING_FRAME_MARGIN` on each side of each axis BEFORE they
  are scored, so a frame is scored on the boxes it would actually hand the
  sweep (design.md §1, §3). World is candidate zero, unpadded, and its boxes
  are `record[2]`, already computed — do not recompute them. Drop a candidate
  whose matrix cannot be inverted (`np.linalg.LinAlgError`) or whose inverse or
  boxes carry a non-finite entry. Docstring states the proof of §1 in short,
  says plainly that the choice changes which pairs are emitted and never a
  verdict, and says why the margin exists and why the world frame does not
  carry it.
- [x] 2.4 `_place_solid`: append `local_bounds` as the eighth field
  (`record[7]`), and rewrite the docstring's account of the trailing fields.
  Restate `_record_key`'s `len(record) <= 6` comment as "a record not built by
  `_place_solid`" so the guard's intent survives a future field.
- [x] 2.5 `assertNoSolidInterference`: index on `_indexing_frame_boxes(solids)`
  instead of `[item[2] for item in solids]`. Extend its docstring's
  broad-phase paragraph — the argument it already makes ("any such pair has
  overlapping conservative world bounds") becomes the frame-general one.
  Change nothing else in the method.
- [x] 2.6 Confirm by reading — and note in the commit message — that
  `_bounds_candidates`, `_axis_order_and_pressure`, `_sweep_candidates`,
  `_boxes_disjoint`, `_world_bounds`, `_exact_verdict`, `_faceted_verdict`,
  `_verdict_key`, `_record_key`, `_gravity_extent`, `_grounded_seeds`,
  `_virtual_floor`, `_support_candidates`, `_dropped_assembly_solids` and
  `assertAssemblySupported` need no edit beyond `_place_solid`'s new trailing
  field.

## 3. Validation

- [x] 3.1 `tests/test_broad_phase_culling.py` green.
- [x] 3.2 `tests/test_adaptive_broad_phase.py` green, unedited.
- [x] 3.3 `tests/test_assembly_supported.py` and `tests/test_sparse_statics.py`
  green.
- [x] 3.4 `tests/test_intersection_memo.py`, `tests/test_exact_geometry.py`,
  `tests/test_persistent_piece_facts.py` (it calls
  `_placed_assembly_solids` directly) and `tests/test_meta.py` green.
- [x] 3.5 The whole suite green, and the three statics tests named in 1.10 run
  explicitly with their result recorded in the commit message.

## 4. Documentation and the decision record

- [x] 4.1 `docs/adrs/TEST-FRAMEWORK/ADR-091-the-broad-phase-chooses-its-indexing-frame.md`,
  written from the outline at the end of design.md, with the numbers from
  task 5 in its Consequences. Status **Accepted**, **Extends** ADR-029,
  related to ADR-040, ADR-048, ADR-070/090 and ADR-025.
- [x] 4.2 `docs/adrs/README.md`: the row in the TEST-FRAMEWORK section in
  chronological order, and "extended by 091" on ADR-029's row.
- [x] 4.3 `docs/architecture.md`: rewrite the broad-phase sentences of the
  interference paragraph (the one reading "It culls provably disjoint pairs
  with a conservative world-AABB broad-phase" and the
  `assertNoSolidInterference` paragraph's "a sweep-and-prune index estimates
  interval pressure on X, Y and Z") so they describe the chosen indexing
  frame, and add one sentence saying the support graph's boxes stay world-axis
  because gravity is a world-frame fact. Leave the memo and statics paragraphs
  otherwise alone.
- [x] 4.4 `docs/testing.rst`: the two "conservative world AABB" sentences,
  ~line 426 (assembly integrity, "builds one conservative world AABB per
  solid") and ~line 559 (gravity support, "the same conservative world AABBs").
  The first becomes the chosen indexing frame; the SECOND stays world-axis and
  gains the half-sentence saying why. A reader must come away knowing the two
  assertions differ here on purpose.
- [x] 4.5 `docs/changelog.rst` "Unreleased".
- [x] 4.6 `workflow/warts.md`, the wall-clock-02 section's second bullet:
  rename the filed cycle to `broad-phase-indexing-frame`, correct "declares
  `facing = 45°` on its root" to "declares `facing` on each child of its root"
  (with the `Clock.render()` reading behind it), correct "in the root's frame
  (the placement common to every solid stripped)" to the chosen indexing
  frame, and mark it **Fixed** with the measured before/after from task 5.
  Leave the other bullets as they stand. If the planning commit already
  carried the rename, this task carries only the fix marking and the numbers.

## 5. Evidence in the originating project

The baseline is this branch's base, `4f23dff` — the tree AFTER
`quantise-verdict-memo`, whose "after" numbers (2526 booleans, 533.39 s on the
swing sweep) are what this cycle compares against. Do not compare against the
pre-quantum numbers.

- [x] 5.1 **Candidate-pair count at one instant, cheap.** From
  `/home/asa/devel/libresolid-studio/projects/3DPrintedClocks`, count the pairs
  `_bounds_candidates` emits per instant for `wall_clock_02` at `facing = 45`
  (the declared default) and at `--set facing=0`, before and after the change:
  four numbers. Monkeypatch `solid_node.test._bounds_candidates` to count what
  it yields, and stop after the first instant. Drive
  `solid_node.manager.test.Test` exactly as the archived
  `quantise-verdict-memo` cycle's task 5.1 harness does — see
  `openspec/changes/archive/2026-09-09-quantise-verdict-memo/tasks.md` and its
  `evidence.md`, including the caveat that `run_test` returning `None` filters
  a test while `num_tests` has already counted it, so the summary reports more
  tests than ran. Verify the harness reproduces the finding's shape (~118 pairs
  at 45°, ~69 at 0°) BEFORE trusting the "after" numbers; if a monkeypatch
  point does not hold on the tree as implemented, adjust it and say so in the
  evidence.
- [x] 5.2 **The chooser's own numbers, at the same instant.** In the same
  harness, record for `wall_clock_02` at `facing = 45`: every topmost rigid
  solid's name and local-bounds diagonal for the top ~6 by diagonal, which
  three became candidates under `K = 3`, each candidate's score (world
  included), and which frame was chosen. This is not decoration — the finding
  is about the fused frame (both plates and their pillars, one solid), and the
  longest solids by diagonal are plausibly the pendulum and the weight's line
  instead (design.md, Risks). Report what the chooser actually saw.
- [x] 5.3 **If the fused plates are NOT among the candidates**, record that in
  `evidence.md` as a finding about K and about the diagonal as a size proxy,
  with the numbers behind it, and STOP there. Do not raise
  `_INDEXING_FRAME_CANDIDATES`, do not change the size measure, and do not
  re-run to find a K that reaches them. Whether K changes is the pilot's
  decision on these numbers. The cycle's win, whatever the chosen frame was,
  is measured and reported as it stands.
- [x] 5.4 **The swing sweep, end to end, after.** Run
  `test_movement_runs_free_through_a_swing` (`@testing_steps(48)`) under the
  exact kernel at the default quantum, recording booleans, keyed memo asks,
  memo hits and wall time; compare against the archived cycle's after row
  (5643 asks, 3117 hits, 2526 booleans, 533.39 s). Note in the evidence that
  fewer candidates means fewer memo ASKS as well as fewer booleans, so the
  hit/ask ratio is not comparable between the two cycles and only the boolean
  count and the wall time are.
- [x] 5.5 Confirm the test's verdict is identical before and after — same
  passes, same failures, same messages — and say so in `evidence.md`.
- [x] 5.6 Write `openspec/changes/broad-phase-indexing-frame/evidence.md`: the
  four candidate counts, the sweep run, the per-instant arithmetic, the
  candidate ranking and every candidate's score from 5.2, which frame the
  chooser picked and whether the fused plates were among the candidates at
  all, and one honest sentence comparing the measured win with the ~3× fewer
  pairs the finding predicted from the `facing=0` control. Record the numbers
  whatever they are; do not tune K, the margin or the score to chase a
  forecast. Nothing is committed in
  the project repository by this cycle.

## 6. Close the cycle

- [x] 6.1 `openspec validate broad-phase-indexing-frame --strict` passes.
- [x] 6.2 Sync the modified `test-framework` baseline spec and archive the
  change, per the shop's framework-change skill.
