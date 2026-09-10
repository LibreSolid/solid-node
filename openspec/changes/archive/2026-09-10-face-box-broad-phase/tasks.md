## 1. Red first: the face-box tier

Most of this lands in a new `tests/test_face_box_culling.py`. Build its exact
fixtures the way `tests/test_intersection_memo.py` does — `write_brep` into a
tmp path with a fixed mtime, `cached_shape` to load it, `ExactFakeNode` where a
node is needed — and clear the exact caches between fixtures with
`tests/exact_test_support.clear_exact_shape_caches()`. Open the module with a
docstring stating the three-step proof of design.md §2 in short: disjoint face
boxes ⇒ disjoint boundaries ⇒ each solid entirely inside or entirely outside
the partner ⇒ one representative per solid, in BOTH directions, decides ⇒ all
OUT ⇒ empty. That paragraph is why the containment guard exists, and it belongs
where the next reader will meet the tests for it.

Count booleans by patching `solid_node.test.intersect_shapes` (the same seam
`tests/test_exact_geometry.py::test_exact_aabb_culls_before_boolean` uses:
`side_effect=AssertionError(...)` where no boolean may run, a counting wrapper
where one must).

- [x] 1.1 Fixture helpers: a `brep(shape, name)` writing and loading a cached
  shape, and an `exact_pair(shape1, matrix1, shape2, matrix2)` calling the
  tier's own seam and the verdict path around it, so the tests exercise
  `_faces_disjoint` AND the two call sites rather than a reimplementation.
- [x] 1.2 **The between-plates scenario.** A thin disc between two plates
  joined by pillars, the plates and pillars fused into ONE exact solid (the
  originating model's shape). Assert the fixture's premises first — the two
  whole-solid AABBs overlap (`assertFalse(_boxes_disjoint(...))`) — then that
  no boolean runs and the verdict is empty with zero volume and `exact=True`.
  A fixture that stops exercising enclosure must fail loudly, not pass
  vacuously. RED on the current tree.
- [x] 1.3 **Containment.** A small cube wholly inside a big cube: the boolean
  RUNS and the verdict reports the small cube's volume. Assert the boolean ran
  (a counting wrapper, not just the volume), because the volume alone would
  also be produced by a wrong tier that happened to fall through for another
  reason. RED on the current tree only in the sense that it must stay green
  through 2.x — it is the guard's whole purpose, so write it before the guard.
- [x] 1.4 **Cavity.** A small cube inside a hollow cube's void, touching
  nothing: the verdict is empty with zero volume, and the tier's classifier
  reported OUT for every representative (assert the tier decided it, by
  asserting no boolean ran). Verified in the workspace venv while designing:
  a point in a cubic void classifies `TopAbs_OUT`, a point in the wall
  `TopAbs_IN`.
- [x] 1.5 **Flush contact.** The existing 2×2×2 boxes at exactly 2.0 offset
  (`tests/test_exact_geometry.py`'s `test_exact_boundary_contact_...` and
  `test_exact_pairwise_flush_contact_passes_and_warns` fixtures): the boolean
  RUNS and the verdict is the kernel's — non-empty at 0.0 mm³ on the pairwise
  path, empty on the exact-composition path, whichever the fixture already
  pins. Do not change what those fixtures assert about the kernel; assert only
  that the tier did not intercept them. Then patch `_FACE_BOX_MARGIN` to `0`
  and assert the pair is STILL not culled (touching boxes overlap by the
  strict `<` test, margin or no margin) — the margin's job is float residue in
  the transformed side, not the touching itself, and this test says so. The
  zero-margin half is sound only because THIS fixture's transformed side is
  computed exactly: axis-aligned boxes, an identity rotation and dyadic
  offsets, so `inv(M1) @ M2` carries no residue in float64 and "touching, not
  residue" is genuinely what is being tested. Do not extend that half to a
  rotated fixture — it would be flaky at margin 0 by design, which is the very
  reason the margin exists.
- [x] 1.5a **The classifier is loaded solid by solid.** Assert the guard
  classifies each representative vertex against each SOLID of the partner
  (`placed.Solids()`), never against the compound: patch
  `BRepClass3d_SolidClassifier` and assert every shape it is constructed from
  is a solid. This pins design.md §1 step 4 against a later simplification
  that would rest on unspecified OCCT behaviour.
- [x] 1.6 **Margin.** Two solids whose faces are separated, in solid 1's
  frame, by less than `_FACE_BOX_MARGIN`: the tier declines and the boolean
  runs. And a pair separated by orders of magnitude more: the tier decides.
  Between them, assert the margin is what moved the boundary by patching it.
- [x] 1.7 **A compound straddling the partner.** Shape 1 a compound of two
  solids, one wholly inside shape 2 and one wholly outside, no boundaries
  meeting: the boolean runs and the pair reports positive volume. Then the
  mutation that proves the test: classify only the FIRST solid of each shape
  (patch the tier's per-solid loop to take one solid) and assert the test
  fails. Record that mutation's result in `evidence.md`; do not leave the
  patched version in the tree.
- [x] 1.8 **Both directions are needed.** Two tests, each of which fails if one
  direction of the classification is dropped: shape 1 inside shape 2 (caught
  only by classifying shape 1's points against shape 2), and shape 2 embedded
  in the WALL of a hollow shape 1 (caught only by the other direction). State
  in each test's docstring which direction it pins.
- [x] 1.9 **Declines.** A faceless shape, a shape with no solids, a solid with
  no vertices, and a non-finite relative matrix each make the tier decline and
  the boolean run; a classifier that reports `TopAbs_ON`, `TopAbs_UNKNOWN`, or
  `Rejected()` (patch `BRepClass3d_SolidClassifier` for these) does too. No
  decline may raise.
- [x] 1.9a **The record carries the local shape.** A `_place_solid` record's
  `record[8]` is the LOCAL shape — not the placed copy — and has the cache
  identity `record[5]` names; positions 0–7 still hold what they held before;
  `_record_key` still returns `None` for the virtual floor and a key for a real
  record; and the tier called through `_placed_intersection` measures face
  boxes in the local frame (assert the boxes it used match
  `cached_face_boxes(local_shape)`, not the placed shape's). RED on the current
  tree.
- [x] 1.10 **The face-box cache.** `cached_face_boxes` is filled once per
  shape identity — measured by patching `BRepBndLib.Add_s` and counting, over
  two tier calls on the same shape — is dropped by `_evict` when the BREP is
  rebuilt under a new mtime, and returns an uncached array for a shape with no
  identity (a shape composed in memory, as `ShapeNode` fixtures build). Assert
  the array's shape is `(F, 2, 3)` and its dtype float64.
- [x] 1.11 **Face boxes are conservative on a curved face carrying a
  triangulation.** Build a cylinder of known radius, attach a triangulation
  (`BRepMesh_IncrementalMesh` at a coarse deflection, or the node's own STL
  write), and assert every face box still reaches the exact radius — measured
  while designing: `Add_s(face, box, False)` gives ±5.0000001 for radius 5,
  where `Add_s(..., True)` on the tessellated shape gives ±5.0365. Assert the
  box is at least the exact extent; do not assert an upper bound tighter than
  OCCT's own tolerance enlargement.
- [x] 1.12 In `tests/test_exact_geometry.py`, the assertion-level scenarios:
  `assertNoSolidInterference` on a three-solid assembly shaped like 1.2 passes
  with no boolean; on 1.3's containment fails naming both solids and the
  volume; on 1.4's cavity passes; on 1.7's compound fails. Use the existing
  `ShapeNode`/`StlShapeNode` doubles and root `SimpleNamespace` pattern already
  in that module.
- [x] 1.13 `assertAssemblySupported` still reaches the same support graph on an
  exact assembly (it routes through `_placed_intersection`, so it inherits the
  tier): run `tests/test_assembly_supported.py` unedited and add one test
  asserting a landing that really lands is still found on exact solids. If any
  existing test there needs editing, stop: it means the tier changed a verdict.
- [x] 1.14 Every existing test in `tests/test_exact_geometry.py`,
  `tests/test_intersection_memo.py`, `tests/test_broad_phase_culling.py` and
  `tests/test_adaptive_broad_phase.py` stays green AS WRITTEN, unedited.

## 2. Implementation

- [x] 2.1 `solid_node/exact.py`: `_face_box_cache = {}` beside `_bounds_cache`,
  with a comment saying what it holds (one `(F, 2, 3)` float64 array of local
  face AABBs per shape cache key) and why it is safe to cache under that key
  (it is a pure function of the exact geometry — see 2.2). One line in
  `_evict` dropping it with the shape.
- [x] 2.2 `solid_node/exact.py`: `cached_face_boxes(shape)`, shaped exactly
  like `cached_bounding_box` — `_shape_keys.get(id(shape))`, `None` meaning
  measure directly and do not cache. Each face's box is a fresh `Bnd_Box`
  filled by `BRepBndLib.Add_s(face.wrapped, box, False)` and read with
  `.Get()` (which already includes the box's gap). The docstring states why
  `useTriangulation=False`: the box must be a pure function of the exact
  surface, because the cache key names only the artifact and its mtime and a
  tessellation can be attached or replaced under a shape the cache is already
  holding; and it notes that CadQuery's own `BoundingBox()` takes a different
  route (`AddOptimal_s`) which is tighter, slower, and unnecessary for a
  superset test. Import `BRepBndLib` and `Bnd_Box` at module level beside the
  other OCP imports; `solid_node/test.py` reaches this through a
  `_deferred_exact('cached_face_boxes')` binding like its siblings, so the
  exact stack stays unimported on a faceted run.
- [x] 2.3 `solid_node/test.py`: `_FACE_BOX_MARGIN = 1e-6` and
  `_FACE_BOX_CHUNK = 256`, beside `_INDEXING_FRAME_MARGIN`, with the same
  comment discipline — internal tuning values, not public assertion-control
  knobs. The margin's comment states what it absorbs (the inversion and
  products of the relative placement, applied to the transformed side only),
  that it can only make the tier decline, and that it is deliberately equal to
  `_INDEXING_FRAME_MARGIN` today while being a separate constant because the
  two tiers' arithmetic is separate (design.md §4).
- [x] 2.4 `solid_node/test.py`: `_faces_disjoint(shape1, placed1, shape2,
  placed2, relative)` returning `True` only when the tier PROVES the pair
  empty. Structure it as design.md §§1, 5, 7: read both shapes' cached face
  boxes; decline on a faceless shape or a non-finite `relative`; transform
  shape 2's boxes (the AABB of each box's eight corners under `relative`,
  vectorised as one `(F2, 8, 4)` product) and enlarge them by the margin;
  compare chunked over `_FACE_BOX_CHUNK` rows of shape 1's boxes with the same
  strict `<` separating-axis test `_boxes_disjoint` uses, returning early at
  the first overlap; then run the containment guard. The docstring carries the
  three-step proof in short and says plainly that a decline is always a
  fall-through to the boolean and never a wrong empty.
- [x] 2.5 `solid_node/test.py`: the containment guard, as a small helper beside
  it — one `BRepClass3d_SolidClassifier` per SOLID of the placed partner
  (`placed.Solids()`), never one loaded from the compound, since the classifier
  is specified for a solid and design.md §1 step 4 rests on that; `Perform` at
  `Precision.Confusion_s()` on one vertex of each solid of the other shape,
  giving `s1 × s2` classifications per direction, both directions, every state
  required to be `TopAbs_OUT`. Decline on `Rejected()`, on any non-OUT state,
  on a shape with no solids (either side — there is then nothing to load the
  classifier from), on a solid with no vertices, and on any exception from
  OCCT. Import `BRepClass3d_SolidClassifier`, `TopAbs_OUT`
  and `Precision` where the module's other OCP names are reached (through the
  deferred-exact seam if that is where they belong, so a faceted run imports
  nothing new).
- [x] 2.5b `_place_solid`: append the solid's LOCAL shape as the ninth field
  (`record[8]`), per design.md §6a — the same `None`-or-shape it already
  receives as its `shape` argument, so no call site changes and no extra cache
  read or geometry work is added. Rewrite the docstring's account of the
  trailing fields, saying what `record[8]` is for (the face-box cache keys on
  the LOCAL shape's identity, which the placed copy at `record[3]` does not
  carry) and that a fixture shape with no identity travels here too and is
  measured directly. Leave positions 0–7 and `_record_key`'s `len(record) <= 6`
  guard exactly as they are; confirm in a test that the virtual floor is still
  separated by that threshold.
- [x] 2.6 `_placed_intersection`: call the tier as the first thing inside the
  `exact()` closure, returning `IntersectionStats(True, 0.0, True)` when it
  proves emptiness. `relative` is `np.linalg.inv(first[6]) @ second[6]`;
  `placed1`/`placed2` are `first[3]`/`second[3]`; the LOCAL shapes the tier
  measures face boxes from are `first[8]`/`second[8]`. Extend the method docstring's
  account of the exact branch. Change nothing else.
- [x] 2.7 `_exact_verdict`: call the tier after the existing `_boxes_disjoint`
  cull and before `intersect_shapes`, materialising `placed_shape(shape1,
  matrix1)`/`placed_shape(shape2, matrix2)` once and passing them to both the
  tier and (if it declines) the boolean, so no pair pays a placement twice and
  no pair culled by the AABB pays one at all.
- [x] 2.8 Confirm by reading — and state in the report — that
  `_faceted_verdict`, `_world_bounds`, `_framed_bounds`, `_boxes_disjoint`,
  `_indexing_frame_boxes`, `_bounds_candidates`, `_verdict_key`,
  `_record_key`, `_memoized`, `_solid_geometry`, `_cached_local_bounds` and
  every gravity-support helper need no edit at all, and that `_place_solid`
  needs only its new trailing field.

## 3. Validation

- [x] 3.1 `tests/test_face_box_culling.py` green.
- [x] 3.2 `tests/test_exact_geometry.py` and `tests/test_intersection_memo.py`
  green, the pre-existing tests unedited.
- [x] 3.3 `tests/test_broad_phase_culling.py`, `tests/test_adaptive_broad_phase.py`,
  `tests/test_assembly_supported.py` and `tests/test_sparse_statics.py` green.
- [x] 3.4 `tests/test_assertions.py`, `tests/test_assembly_integrity.py`,
  `tests/test_persistent_piece_facts.py` (it calls `_placed_assembly_solids`
  directly, so it sees the new record width) and `tests/test_meta.py` green.
- [x] 3.5 The whole suite green, including a faceted-kernel run, and record in
  the commit message that no faceted test imported the exact stack (the
  `tests/mesh_engine_absent.py` and `MeshNeverJudgedOnTheExactPathTest` paths
  are the ones that would catch it).

## 4. Documentation and the decision record

- [x] 4.1 `docs/adrs/TEST-FRAMEWORK/ADR-092-face-boxes-decide-an-enclosed-pair-without-a-boolean.md`,
  written from the outline at the end of design.md, with the numbers from
  task 5 in its Consequences. Status **Accepted**, **Extends** ADR-029 and
  ADR-091, related to ADR-044, ADR-070/090 and ADR-025. State the three-step
  proof in full: it is the load-bearing paragraph of the record.
- [x] 4.2 `docs/adrs/README.md`: the row in the TEST-FRAMEWORK section in
  chronological order, and "extended by 092" on the rows of ADR-029 and
  ADR-091.
- [x] 4.3 `docs/architecture.md`: the exact-path sentences of the shared
  intersection paragraph ("Exact pairs share the same world-AABB broad phase,
  then use OCCT common…") gain the face-box tier — what it proves, that a
  decline always falls through to the kernel, that flush contact still reaches
  the kernel, and that the containment guard is why disjoint boundaries are not
  by themselves a verdict. Add the face-box cache to the sentence that lists
  what the exact caches hold under a shape identity. Leave the frame-choice and
  memo paragraphs alone.
- [x] 4.4 `docs/testing.rst`: one paragraph in the assembly-integrity section
  saying that an exact pair whose bounds overlap may still be decided without a
  kernel call when no face of one comes near any face of the other, that a
  solid inside another is caught by the containment check and still fails, and
  that nothing about a project's verdicts changes. Keep it a user's account of
  cost, not an implementation walkthrough.
- [x] 4.5 `docs/changelog.rst` "Unreleased".
- [x] 4.6 `workflow/warts.md`, the wall-clock-02 section's THIRD bullet: mark
  it **Fixed** by cycle `face-box-broad-phase` (ADR-092) with the measured
  before/after from task 5, and correct "the fused frame (both plates and their
  pillars, one solid) sits in 40 of the 118 pairs" to what task 5.2 actually
  measured — which solids sit in the surviving pairs, out of how many, after
  ADR-091 (the `broad-phase-indexing-frame` evidence already shows `standoffs`
  and `plates` are two separate topmost solids, not one fused one). Leave the
  first two bullets as they stand.
- [x] 4.7 `workflow/warts.md`, a NEW bullet in the same section: **An exact
  solid's index bounds are inscribed, not conservative.**
  `_solid_geometry` takes every topmost solid's local bounds from the STL mesh
  even for an exact solid; a tessellation's vertices lie ON the exact surface,
  so those bounds fall up to the declared linear deflection (0.1 mm default)
  short of the exact extents on a curved face, and a sub-deflection overlap at
  a box boundary could in principle be culled by the whole-assembly index.
  State the fix (an exact solid's local bounds become the union of the exact
  face boxes this cycle already computes; faceted solids keep mesh bounds) and
  the three reasons it is a separate cycle (design.md §8: it reverses two
  ratified sentences of `Accelerated intersection evaluation`, it must not fire
  under the faceted kernel, and it moves when exact faces are measured).
  **Filed:** cycle `exact-solid-index-bounds`.
- [x] 4.8 Update the last bullet of that section if it still lists this cycle
  among the levers "deferred until the three above land": the three have landed.

## 5. Evidence in the originating project

The baseline is this branch's base, `93612db` — the tree AFTER
`broad-phase-indexing-frame`, whose numbers (67 candidate pairs at the first
swing-sweep instant, 1089 booleans, 265.99 s over the 48-instant sweep) are
what this cycle compares against. Do not compare against any earlier row. The
harness is the one the two archived siblings used: drive
`solid_node.manager.test.Test` directly from
`/home/asa/devel/libresolid-studio/projects/3DPrintedClocks` with the workspace
venv and this worktree on `PYTHONPATH`, filtering to
`test_movement_runs_free_through_a_swing`, and monkeypatch the seam you need —
see `openspec/changes/archive/2026-09-10-broad-phase-indexing-frame/tasks.md`
and its `evidence.md`, including the caveat that `run_test` returning `None`
filters a test while `num_tests` has already counted it.

- [x] 5.1 **What the tier decides, at one instant.** At the declared default
  `facing=45`, first instant: of the candidate pairs the index emits, how many
  the tier decides empty and how many reach `intersect_shapes`. Count by
  wrapping `_faces_disjoint` and `intersect_shapes` and stopping after the
  first instant (`os._exit(0)`, as the sibling harness does). Verify the
  emitted count reproduces the baseline's 67 BEFORE trusting the split.
- [x] 5.2 **Which solids remain.** For the same instant, record the names of
  the solids in every pair the tier did NOT decide, and their face counts. The
  finding claims an enclosing frame solid sits in most pairs and names it
  wrongly (design.md, Context): report what is actually there, and carry the
  answer into task 4.6. If the surviving pairs are dominated by something the
  finding never mentioned, that is the result — record it, do not tune the
  tier toward the forecast.
- [x] 5.3 **The tier's own cost.** Time `_faces_disjoint` itself
  (`time.perf_counter` around the wrapper from 5.1, summed) per instant, and
  report it beside the wall time and the boolean time it displaced. Report the
  classifier's share separately if it is measurable — design.md §7 names it as
  the one term that could surprise, and a follow-up depends on the number.
- [x] 5.4 **The swing sweep, end to end, after.** `@testing_steps(48)`, exact
  kernel, default quantum, `facing=45`: booleans, keyed memo asks, memo hits,
  wall time, against the baseline's 3210 asks / 2121 hits / 1089 booleans /
  265.99 s. Note that this cycle does NOT reduce the emitted candidate count,
  so the keyed-ask count should be unchanged — a change there is a finding
  about the tier reaching somewhere it should not.
- [x] 5.5 Confirm the test's verdict is identical before and after — same
  passes, same failures, same messages — and say so in `evidence.md`.
- [x] 5.6 Write `openspec/changes/face-box-broad-phase/evidence.md`: the
  decided/boolean split, the surviving pairs and their solids, the tier's own
  cost, the sweep row against the baseline, the verdict identity, and one
  honest sentence comparing the measured win with the finding's own forecast
  ("decides a wheel between two plates without a boolean", ~8 s of the 19 s
  attributed to plates × wheel booleans at the time it was written). Record the
  numbers whatever they are; do not tune the margin, the chunk size or the
  fixture to chase a forecast. Nothing is committed in the project repository
  by this cycle; only its ignored `_build/` directory is written by these runs.

## 6. Close the cycle

- [x] 6.1 `openspec validate face-box-broad-phase --strict` passes.
- [x] 6.2 Sync the modified `test-framework` and `exact-geometry` baseline specs
  and archive the change, per the shop's framework-change skill.
