# ADR-092: Face Boxes Decide an Enclosed Pair Without a Boolean

**Status:** Accepted
**Date:** 2026-09-10
**Extends:**
- [ADR-029: Manifold Cache and AABB Broad Phase for Assertions](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)
- [ADR-091: The Broad Phase Chooses Its Indexing Frame](./ADR-091-the-broad-phase-chooses-its-indexing-frame.md)

**Related to:**
- [ADR-044: Derived Exact-Geometry Capability](./ADR-044-derived-exact-geometry-capability.md) —
  whose `shape()` and cache identity this tier's face boxes hang off.
- [ADR-070: Relative Placement as the Identity of an Intersection
  Question](./ADR-070-relative-placement-as-the-identity-of-an-intersection-question.md) /
  [ADR-090: The Placement Quantum Is a Property of the Test
  Run](./ADR-090-the-placement-quantum-is-a-property-of-the-test-run.md) —
  the sibling exact-negative shortcut and the key this tier's verdict is
  cached under.
- [ADR-025: Perturbation-Based Kinematic Fit
  Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md) —
  verdict semantics that must not move.

## Context and Problem Statement

`workflow/warts.md`, "3DPrintedClocks wall clock 02 (2026-09-09, exact
sweep cost)", third bullet: a whole-solid AABB, in ANY frame, cannot cull
a wheel that runs between two plates, because the plates' box encloses
the wheel's wherever the wheel is. After the two sibling cycles this one
stacks on (`quantise-verdict-memo`, ADR-090; `broad-phase-indexing-frame`,
ADR-091) the originating model — 3DPrintedClocks `wall_clock_02`,
`test_movement_runs_free_through_a_swing`, `@testing_steps(48)`, exact
kernel — still emits 67 candidate pairs per instant and pays 1089
Booleans and 265.99 s on the swing sweep, every one of those Booleans
empty.

The bullet's own wording needed a correction before this cycle could even
measure against it: it said "the fused frame (both plates and their
pillars, one solid) sits in 40 of the 118 pairs", but
`broad-phase-indexing-frame`'s own evidence had already shown `standoffs`
and `plates` are two separate topmost rigid solids, tied at the top of
that cycle's frame ranking by local-bounds diagonal — not one fused
frame. This cycle measured which solids actually sit in the pairs a
face-box tier cannot decide rather than trusting either wording (see
Consequences): the dominant solid turned out to be neither the plates nor
the standoffs, but the wheel train's own thin mounting rod.

## Decision Drivers

- Never change a verdict: a shortcut here must remain exact-negative, in
  the same sense ADR-029's own AABB broad phase and ADR-091's indexing
  frame are.
- No new public knob, flag, environment variable, or assertion argument.
- A one-way failure direction: anything the tier cannot prove falls
  through to the Boolean that runs today, never the reverse.
- Cache the per-shape work under the identity discipline
  `solid_node/exact.py` already uses (ADR-044).
- Keep the per-shape work a pure function of the exact geometry, so it
  cannot depend on whether a triangulation happens to be attached.

## Considered Options

1. A tighter whole-solid bound (an OBB or convex hull per solid) —
   rejected: it does not help at all against enclosure, which is a
   containment relation, not an orientation artefact a tighter box could
   fix.
2. A surface-distance query (`BRepExtrema_DistShapeShape`) per pair —
   rejected: it is itself expensive on real parts and answers more than
   the question needs.
3. Face boxes with no containment guard — rejected: it returns a wrong
   empty for a solid wholly inside another, which the ratified scenario
   "Overlap hidden from a global volume comparison still fails" forbids.
4. The mesh-distance tier (distance above twice the declared linear
   deflection proves exact solids disjoint) — a separate filed finding;
   it needs the mesh engine and is inexact where this tier is exact.
5. **Face boxes plus a per-solid containment guard — chosen.**

## Decision Outcome

Chosen: **face-box culling with a per-solid containment guard**, run
after the AABB cull and before any Boolean, for a pair of EXACT solids.

### 1. The tier, stated

For two exact shapes `S1`, `S2` placed by world matrices `M1`, `M2`, with
`R = inv(M1) @ M2`:

1. `B1 = cached_face_boxes(S1)` — an `(F1, 2, 3)` array of local AABBs,
   one per face of `S1`, in `S1`'s own frame.
2. `B2' =` for each face box of `S2`, the AABB of its eight corners under
   `R`, enlarged by `_FACE_BOX_MARGIN` on every side. Also `(F2, 2, 3)`,
   now expressed in `S1`'s frame.
3. If no box of `B2'` overlaps any box of `B1` — overlap defined exactly
   as `_boxes_disjoint` defines it, so touching counts as overlapping —
   the two boundaries are proven disjoint. Otherwise the tier declines.
4. Given disjoint boundaries, classify one vertex of each solid of `S1`
   against each solid of `placed(S2)`, and one vertex of each solid of
   `S2` against each solid of `placed(S1)`, with
   `BRepClass3d_SolidClassifier` at `Precision::Confusion`. If every
   state is `TopAbs_OUT`, return `IntersectionStats(True, 0.0, True)`.
   Anything else declines.

**Solid by solid, never against a compound.**
`BRepClass3d_SolidClassifier` is specified for a solid; what it does when
loaded with a compound of several solids is not a behaviour this design
rests on. So the classifier is loaded from one solid of the placed
partner at a time — `s1 × s2` classifications per direction, a handful,
since a topmost rigid solid is normally one solid — and step 4 above is
literally what the code does.

Declining always means "run the Boolean that runs today".

### 2. The three-step proof

**Step 1 (boxes → boundaries).** A face's AABB contains that face. A
union of face boxes therefore contains the whole boundary `∂S`. `R` is an
invertible affine map, so the AABB of the eight corners of `S2`'s face
box under `R` contains the image of that face box, hence contains the
image of that face — the same corner-box argument ADR-091 makes for a
whole solid, applied to a face. Enlargement only grows a box. So if no
box of `B2'` meets any box of `B1`, then `R·∂S2 ∩ ∂S1 = ∅`, i.e. the two
placed boundaries do not meet.

**Step 2 (boundaries → containment or disjointness).** Let `A`, `B` be
closed regular solids with `∂A ∩ ∂B = ∅`. Every connected component of
`∂A` is a connected set disjoint from `∂B`, hence lies entirely in the
interior of `B` or entirely in its exterior; symmetrically for `∂B`.
Therefore `A ∩ B ≠ ∅` implies one of the two contains the other's
material: there is no partial overlap without the boundaries crossing.

**Step 3 (one vertex per solid decides, in both directions).** A shape
here may be a compound of several solids, and each solid is a separate
connected body: one component could lie inside the partner while another
lies outside. So one representative point per SOLID of each shape is
classified, against each SOLID of the partner — both sides of every
classification are then one connected body, which is what step 2 is a
statement about and what `BRepClass3d_SolidClassifier` is specified for.
A vertex of solid `s` lies on `∂s`, which by step 2 is entirely inside or
entirely outside each solid of the partner — so its classifications
decide that whole solid against that whole partner solid. If every
representative of `S1` is OUT of `S2` and every representative of `S2` is
OUT of `S1`, no solid of either shape lies inside the other, and by step
2 the intersection is empty. ∎

**Both directions are load-bearing, and so is "per solid".** `S1 ⊂ S2` (a
small cube inside a big one): `S1`'s vertices are IN `S2`; `S2`'s
vertices are OUT of `S1`. Only the `S1`-side check catches it — without
it the tier would return a wrong empty for real containment. `S2`
embedded in the WALL of a hollow `S1`, `∂S2` entirely inside `S1`'s
material: `S1`'s vertices are OUT of `S2`, but `S2`'s vertices are IN
`S1` — only the `S2`-side check catches it. A compound whose components
straddle the partner — one solid inside, one outside, no boundaries
meeting anywhere — needs the per-SOLID loop rather than one
representative per shape: classifying only one solid per shape can (and,
mutation-tested, does) wrongly prove such a pair empty.

**Cavities are handled by the classifier itself, not by special-casing.**
A point in a solid's void classifies OUT — verified on a 20 mm cube with
a 10 mm cubic void: the centre point classifies `TopAbs_OUT`, a point in
the wall `TopAbs_IN`. That is exactly the semantics the proof needs: a
solid sitting in another's cavity shares no material with it, so "OUT" is
the right answer, not an approximation. Every representative is OUT in
both directions, and the tier reports empty — the same verdict
`BRepAlgoAPI_Common` reports for that pair today, more cheaply.

**The failure direction is always a fall-through.** The tier can be wrong
only by declining to prove something true; it can never assert an
emptiness that is false, because every step is a containment (a face
inside its box, a box inside its transformed box, an enlargement
outward) and the final step is a classifier state that must be OUT for
every representative. `ON` is treated as a decline rather than as
contact, deliberately: `ON` at `Precision::Confusion` on a pair whose
face boxes were proven disjoint means the two computations disagree, and
the framework's answer to a disagreement is the kernel, not the
shortcut.

### 3. Face boxes: `BRepBndLib.Add_s(face, box, False)`, cached per shape identity

`cached_face_boxes(shape)` mirrors `cached_bounding_box`: keyed by
`_shape_keys[id(shape)]`, stored in a `_face_box_cache` beside
`_bounds_cache`, dropped by the same line in `_evict`, and — for a shape
with no cache identity — computed directly and not cached. It returns an
`(F, 2, 3)` float64 array, `(0, 2, 3)` for a shape with no faces.

Each face box is one `Bnd_Box` filled by
`BRepBndLib.Add_s(face.wrapped, box, False)` and read with `.Get()`,
which already includes the box's gap: measured here, a cylinder of
radius 5 gives `±5.0000001`, OCCT's own tolerance enlargement, strictly
enclosing the exact surface.

**Why `useTriangulation=False`.** With `True` the box would depend on
whether a triangulation happens to be attached and at what deflection —
state an STL export or a viewer read can change on a shape the cache is
already holding — and a cached measurement must be a pure function of
its key; `False` makes it one. It is also conservative by construction
(bounding a face from its surface's own parametric bounds plus its
tolerance is outward-only slack), where CadQuery's own `BoundingBox()`
instead calls the tighter, slower `AddOptimal_s`, unnecessary for a
superset test. Measured here with a 0.5 mm deflection triangulation
attached: `Add_s(..., True)` gives `±5.0365`, larger than the exact
`±5.0000001` (OCCT adds the triangulation's deflection as a gap) — so the
originally-feared direction (a triangulated box shrinking below the
exact surface) does not reproduce for this call, but determinism under a
cache keyed on shape identity alone is reason enough to keep `False`.

### 4. The pair frame: solid 1's own frame, one padded side

The pair is tested in `S1`'s local frame: `S1`'s face boxes are used
verbatim, and only `S2`'s are carried into that frame and padded. This is
the pair-level analogue of ADR-091's frame choice: for a pair, the first
solid's frame inflates one side's boxes instead of both, and composes
with the relative matrix the verdict memo already forms.
`_FACE_BOX_MARGIN = 1e-6` mm is a sibling of ADR-091's
`_INDEXING_FRAME_MARGIN`, equal in value today and kept separate because
the two tiers absorb the arithmetic of two different call paths.
Enlargement can only make the tier decline, never decide, so a pair
whose true surface gap is under the margin pays the Boolean it pays
today.

### 5. The overlap test: chunked NumPy, early exit

`_faces_disjoint` computes, for a chunk of rows of `B1` against all of
`B2'`, the standard separating-axis test broadcast over three axes, and
declines as soon as any pair of boxes overlaps. `_FACE_BOX_CHUNK = 256`
rows bounds the working set the vectorised comparison holds at once.

### 6. Where it is called, and what the record must carry

One function, `_faces_disjoint(shape1, placed1, shape2, placed2,
relative)`, called from exactly two places: `_placed_intersection`,
inside the `exact()` closure, before `intersect_shapes`; and
`_exact_verdict`, after its own `_boxes_disjoint` cull and before
`intersect_shapes`, with `placed_shape` materialised once per side and
handed to both the tier and, if it declines, the Boolean.

`cached_face_boxes(shape)` keys on the LOCAL cached shape's identity, and
a placement record held only the PLACED copy. `_place_solid` now appends
the solid's LOCAL shape as `record[8]`, on ADR-091's own precedent
(`record[7]`, local bounds): no existing tuple position moves, and
`_record_key`'s `len(record) <= 6` guard is untouched, since a real
record is now a 9-tuple and a virtual-floor record stays short.

`assertAssemblySupported` inherits the tier because it routes through
`_placed_intersection` too; its virtual floor carries no shape and never
reaches the exact branch at all.

### 7. Declines, guards, and cost

The tier declines whenever it cannot prove emptiness: either shape has no
faces or no solids; a solid has no vertices; `relative` is non-finite;
the classifier is `Rejected()`, reports `TopAbs_UNKNOWN`, or raises; any
representative classifies `IN` or `ON`. The OCP names the containment
guard needs (`BRepClass3d_SolidClassifier`, `TopAbs_OUT`, `Precision`,
`gp_Pnt`) are imported lazily inside the guard rather than at module
level, so a faceted run — which never reaches this tier, since a
Manifold has no faces — imports nothing new.

## Consequences

- An enclosed pair that touches nothing is decided without a Boolean.
  Measured on `wall_clock_02`'s swing sweep
  (`test_movement_runs_free_through_a_swing`, `@testing_steps(48)`, exact
  kernel, default quantum, `facing=45`, against the tree after
  `broad-phase-indexing-frame`): booleans 1089 → 708 (35.0% fewer — the
  tier decided 381 of the 1089 memo-misses without a Boolean) and wall
  time 265.99 s → 216.50 s (18.6% faster), the test's own verdict
  unchanged ("1 passed, 0 failed" both before and after). Keyed asks and
  memo hits are unchanged at 3210/2121, as expected: this tier does not
  change which candidate pairs are emitted, only whether an emitted pair
  needs a Boolean.
- At the first swing-sweep instant, of the 67 candidate pairs emitted
  (reproducing the `broad-phase-indexing-frame` baseline exactly), the
  tier decides 10 without a Boolean and declines 57. Its own cost there
  was 0.955 s (the containment guard's share 0.770 s across 10 classifier
  calls) against 10.04 s of Boolean time for the 57 declined pairs.
- The pairs the tier still declines are dominated by neither the plates
  nor the standoffs, contrary to the finding's own wording: of the 57,
  `wheel` (the train's five wheels) appears in 24, `rod` — a 3-face
  cylindrical shaft the wheel train is mounted on — in 23, `plates` in 9
  and `standoffs` in only 3. The wheel train's mounting rod is a
  genuinely close fit the face-box tier cannot separate, not a spurious
  whole-solid enclosure.
- Flush contact still reaches the kernel and still fouls at exactly
  0.0 mm³, because touching face boxes overlap; a solid wholly inside
  another still fails, through the containment guard; a solid in
  another's cavity passes through it, the same verdict the kernel
  reports for it.
- Every exact shape the tier meets carries one more cached per-identity
  measurement (its face boxes), evicted with its shape. The faceted path
  is untouched and a faceted run still reads no `shape()`.
- `assertAssemblySupported` inherits the tier through
  `_placed_intersection`; no support requirement changes.
- A placement record grows one trailing field (`record[8]`, the solid's
  LOCAL shape) on ADR-091's own precedent, leaving every existing index
  reader and `_record_key`'s guard untouched.
- The tier's verdict is memoized like any other, served across instants
  under the run's placement quantum.
- The whole-assembly index's local bounds for an exact solid remain the
  INSCRIBED mesh bounds, a separate known hole filed as
  `exact-solid-index-bounds` and NOT closed here — see
  `workflow/warts.md`.

## References

- `solid_node/exact.py` — `_face_box_cache`, `cached_face_boxes`
- `solid_node/test.py` — `_FACE_BOX_MARGIN`, `_FACE_BOX_CHUNK`,
  `_faces_disjoint`, `_mutually_outside`, `_placed_intersection`,
  `_exact_verdict`, `_place_solid`
- `tests/test_face_box_culling.py` — the enclosure, containment, cavity,
  flush-contact, compound, cache, and triangulation-conservativeness
  tests
- `workflow/warts.md` — "3DPrintedClocks wall clock 02 (2026-09-09,
  exact sweep cost)"
- OpenSpec change `face-box-broad-phase`, capabilities `test-framework`
  and `exact-geometry`
