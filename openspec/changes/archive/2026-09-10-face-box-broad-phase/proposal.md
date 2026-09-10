## Why

A whole-solid AABB cannot cull a wheel that runs between two plates: the
plates' box encloses the wheel wherever the wheel is, in any indexing frame,
so the pair is emitted and settled by an exact Boolean that comes back empty
after 0.5–2.2 s. What actually decides such a pair is cheap and local — no
FACE of one solid comes near any face of the other — and the framework never
asks it.

The finding is `workflow/warts.md`, last section, "3DPrintedClocks wall clock
02 (2026-09-09, exact sweep cost)", third bullet ("One enclosing solid defeats
whole-solid boxes"). After the two sibling cycles this one stacks on
(`quantise-verdict-memo`, ADR-090; `broad-phase-indexing-frame`, ADR-091) the
originating model still emits **67 candidate pairs per instant** and pays
**1089 Booleans and 266 s** on its 48-instant swing sweep — and every one of
those Booleans comes back empty. The remaining cost is not spurious boxes any
longer; it is genuinely overlapping boxes around solids that genuinely do not
touch.

**One correction to the bullet, carried by this cycle.** It calls the
enclosing solid "the fused frame (both plates and their pillars, one solid)".
The `broad-phase-indexing-frame` evidence shows two separate topmost rigid
solids — `standoffs` (local-bounds diagonal 442.45 mm) and `plates`
(421.55 mm) — both frame-like and both enclosing the movement, tied at the top
of that cycle's frame ranking. The implementer measures which solids sit in
the surviving pairs (task 5.2) rather than trusting either wording.

## What Changes

- **A second exact-negative tier for pairs of EXACT solids: face-box culling
  with a containment guard.** It runs after the AABB cull and before
  `intersect_shapes`, inside the memoized computation, so its verdict is
  cached under the same key any Boolean verdict would be.
- **Face boxes are computed once per shape identity.** For an exact shape, the
  local AABB of every face (`shape.Faces()`) as an `(F, 2, 3)` array, cached
  in `solid_node/exact.py` beside `_bounds_cache`, under the same shape cache
  key, evicted by the same `_evict`. They are taken with
  `BRepBndLib.Add_s(face.wrapped, box, False)` — OCCT's own tolerance
  enlargement, and no triangulation — so a face box is a pure function of the
  exact surface and can never depend on whether an STL export happened to
  attach a tessellation to the shape.
- **A pair is tested in the FIRST solid's local frame.** Solid 1's face boxes
  are used as they are; solid 2's are the AABBs of their eight corners under
  the relative matrix `inv(M1) @ M2` — the same relative placement the verdict
  memo keys on — enlarged by a fixed absolute margin
  (`_FACE_BOX_MARGIN`, a sibling of ADR-091's `_INDEXING_FRAME_MARGIN` with
  the same rationale) so float residue cannot separate a flush contact. The
  test is vectorised over F1 × F2 in NumPy, chunked over rows so memory stays
  bounded, with an early exit at the first overlap found.
- **Disjoint face boxes are not by themselves a verdict.** Two closed solids
  whose boundaries do not meet are either disjoint or one lies inside the
  other. So when no face boxes overlap, one vertex of EACH SOLID of shape 1 is
  classified against placed shape 2 with `BRepClass3d_SolidClassifier`, and
  one vertex of each solid of shape 2 against placed shape 1 — each vertex
  against each SOLID of the partner, never against a compound, since the
  classifier is specified for a solid and the proof is about one connected
  body against another. **Only if every classification is `TopAbs_OUT`** is the pair reported
  `IntersectionStats(True, 0.0, True)` with no Boolean. Any `IN`, any `ON`,
  any classifier refusal, and any shape the tier cannot represent falls
  through to the Boolean exactly as today.
- **Verdict semantics are untouched.** Flush contact still reaches the kernel
  (touching face boxes overlap) and still comes back non-empty at 0.0 mm³. A
  solid wholly inside another still fails. A solid inside another's cavity
  still passes. The faceted path is untouched — Manifolds have no faces.
- **No public surface changes**: no flag, no environment variable, no
  assertion argument, no message change. A project that says nothing pays
  fewer Booleans for the same verdicts.
- **One ADR (ADR-092)** extending ADR-029 and ADR-091, related to ADR-044 and
  ADR-025.
- **Not fixed here, recorded as a finding**: `_solid_geometry` takes every
  topmost solid's local bounds from the STL mesh even for an exact solid, and
  a tessellation's vertices lie ON the exact surface, so those bounds are
  INSCRIBED and can fall up to the declared linear deflection short of the
  exact extents on a curved face. design.md §8 states the hole, why this
  cycle's face boxes would close it at no extra geometric cost, and why doing
  so is nevertheless a separate cycle: it contradicts two ratified sentences
  of `Accelerated intersection evaluation`, it would make the emitted
  candidate pairs depend on whether a solid carries exact geometry, and it
  must not fire under the faceted kernel, where no solid's `shape()` may be
  read at all. A new `workflow/warts.md` bullet files it as
  `exact-solid-index-bounds`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-framework`: `Accelerated intersection evaluation` — the exact pair
  path MAY decide a pair empty by a face-box tier with a containment guard,
  after the AABB cull and before any Boolean, as a second exact-negative
  shortcut that never changes a verdict; the tier's conditions, its
  fall-through direction, and the fact that flush contact still reaches the
  kernel are stated there. `Whole-assembly solid interference assertion` —
  each emitted pair of exact solids MAY be decided empty by that tier before
  any Boolean, with the enclosed-solid, containment, cavity, flush-contact and
  compound scenarios.
- `exact-geometry`: `Exact geometry is persisted and reloaded` — the derived
  per-shape measurements cached under a loaded shape's identity are named
  (its bounding box, and now its faces' bounding boxes), computed once per
  identity, evicted with it, and taken from the exact surface rather than from
  any triangulation the shape may carry.

Not modified: `Broad-phase completeness` (this cycle adds no bound and changes
no index), the gravity-support requirements, and every faceted-path
requirement.

## Impact

**Framework code.** `solid_node/exact.py`: a `_face_box_cache` beside
`_bounds_cache`, a `cached_face_boxes(shape)` accessor shaped like
`cached_bounding_box`, and one line in `_evict`. `solid_node/test.py`:
`_FACE_BOX_MARGIN` and `_FACE_BOX_CHUNK` module constants, `_faces_disjoint`
and its two helpers (the transformed-box builder and the classifier guard),
called from the exact branch of `_placed_intersection` — inside its `exact()`
closure, so both `assertNoSolidInterference` and `assertAssemblySupported`
inherit it — and from `_exact_verdict` after its AABB cull. `_place_solid`
appends the solid's LOCAL shape as `record[8]`, on the precedent of ADR-091's
`record[7]` and for the same reason: the tier's per-shape cache is keyed on the
local shape's identity and a record carries only the placed copy. No existing
tuple position moves and `_record_key`'s guard is untouched. `_boxes_disjoint`,
`_world_bounds`, `_framed_bounds`, `_indexing_frame_boxes`,
`_bounds_candidates`, `_verdict_key`, `_record_key`, `_memoized`,
`_faceted_verdict`, `_solid_geometry` and `_cached_local_bounds` are
untouched.

**Tests.** A new `tests/test_face_box_culling.py` carrying the tier's own
coverage (enclosure, containment, cavity, flush contact, compounds, the cache,
conservativeness under a triangulation, the margin, the fall-throughs), built
on the `cached_shape`/`write_brep`/`ExactFakeNode` fixtures
`tests/test_intersection_memo.py` already uses.
`tests/test_exact_geometry.py` gains the assertion-level scenarios.
`tests/test_broad_phase_culling.py` and `tests/test_adaptive_broad_phase.py`
are unaffected and unedited.

**Docs.** `docs/architecture.md` (the exact-path paragraph),
`docs/testing.rst`, `docs/changelog.rst` Unreleased,
`docs/adrs/TEST-FRAMEWORK/ADR-092`, `docs/adrs/README.md`,
`workflow/warts.md` (the third bullet marked fixed with numbers, plus the new
`exact-solid-index-bounds` bullet).

**Projects.** Nothing to change in any project. The originating project,
3DPrintedClocks `wall_clock_02`, is where this cycle's evidence is measured;
nothing is committed outside this framework repository.

**Downstream.** The baseline is this branch's base, `93612db` — the tree after
`broad-phase-indexing-frame` (67 candidate pairs per instant, 1089 Booleans,
265.99 s on the swing sweep). The wall-clock-02 findings still open after this
cycle are the mesh-distance exact-negative tier, parallel pair Booleans, and
the newly filed `exact-solid-index-bounds`.
