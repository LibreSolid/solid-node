## Context

Three exact-negative shortcuts stand between a candidate pair and a
`BRepAlgoAPI_Common` today, and all three reason about whole solids:

- ADR-029's conservative AABB, taken from a solid's eight local-bounds
  corners under its composed world matrix, culled by `_boxes_disjoint`;
- ADR-091's choice of the frame those boxes are taken in, which recovers the
  candidate set an assembly would have had without its common outermost turn;
- ADR-070/090's verdict memo, which asks the same question once per relative
  placement cell.

On the originating model — 3DPrintedClocks `wall_clock_02`,
`test_movement_runs_free_through_a_swing`, `@testing_steps(48)`, exact
kernel — that leaves **67 candidate pairs per instant, 1089 Booleans and
265.99 s** for the sweep, *all Booleans empty*
(`openspec/changes/archive/2026-09-10-broad-phase-indexing-frame/evidence.md`).

Those 1089 are not an artefact of a bad frame. They are the pairs a
whole-solid box genuinely cannot separate. A clock movement is a wheel train
running between two plates: the plates' box **encloses** every wheel, in every
frame, at every instant, because the wheels are literally inside the volume the
plates span. No AABB tier, however cleverly framed, can cull that pair — and
each one costs 0.5–2.2 s of OCCT.

What decides such a pair is not the solids' extents but their **surfaces**: the
wheel runs in the air between the plates, and no face of the wheel comes near
any face of the plates. That is a question about O(F1 × F2) small boxes and no
Boolean at all.

### The finding, and one correction to it

`workflow/warts.md`, last section, third bullet: "One enclosing solid defeats
whole-solid boxes". It says "the fused frame (both plates and their pillars,
one solid) sits in 40 of the 118 pairs". Two things about that sentence need
care:

1. The count 118 predates `broad-phase-indexing-frame`; the surviving
   population is 67 pairs per instant.
2. The `broad-phase-indexing-frame` evidence shows **two** separate topmost
   rigid solids of frame-like size — `standoffs` (local diagonal 442.45 mm)
   and `plates` (421.55 mm), the top two of 53 by diagonal and tied for the
   chosen indexing frame. So "one fused solid" is not what the assembly
   actually contains, and either of the two, or both, may be what encloses the
   movement.

The implementer therefore **measures which solids sit in the surviving pairs**
(task 5.2) instead of trusting either wording, and corrects the bullet with
what was measured.

## Goals / Non-Goals

**Goals:**

- Decide, without a Boolean, an exact pair whose solids are enclosed by one
  another's boxes but whose surfaces never come near each other.
- Keep the tier exact-negative and verdict-identical, by construction, by
  proof, and by test.
- Keep the failure direction one-way: anything the tier cannot prove falls
  through to the Boolean that runs today.
- Cache the per-shape work under the identity discipline the rest of
  `solid_node/exact.py` already uses.

**Non-Goals:**

- Any public knob, flag, environment variable or assertion argument. The
  margin and the chunk size are module constants and internal policy.
- The faceted path. A Manifold has no faces, and a faceted run must not read
  a solid's `shape()` at all.
- Any change to the whole-assembly index, its frame choice, its sweep, the
  verdict memo, or its key.
- Tighter geometry than a face's AABB — no OBB per face, no surface-distance
  query, no BVH over faces. The mesh-distance tier is its own filed finding.
- Fixing the inscribed local bounds of an exact solid in the whole-assembly
  index (§8). Filed, not done here.

## Decisions

### 1. The face-box tier, stated

For two exact shapes `S1`, `S2` placed by world matrices `M1`, `M2`, with
`R = inv(M1) @ M2`:

1. `B1 = cached_face_boxes(S1)` — an `(F1, 2, 3)` array of local AABBs, one
   per face of `S1`, in `S1`'s own frame.
2. `B2' =` for each face box of `S2`, the AABB of its eight corners under `R`,
   enlarged by `_FACE_BOX_MARGIN` on every side. Also `(F2, 2, 3)`, now
   expressed in `S1`'s frame.
3. If **no** box of `B2'` overlaps **any** box of `B1` — overlap defined
   exactly as `_boxes_disjoint` defines it, so touching counts as overlapping —
   the two boundaries are proven disjoint. Otherwise the tier declines.
4. Given disjoint boundaries, classify one vertex of each solid of `S1`
   against **each solid of** `placed(S2)`, and one vertex of each solid of
   `S2` against each solid of `placed(S1)`, in the world frame, with
   `BRepClass3d_SolidClassifier` at `Precision::Confusion`. If every state is
   `TopAbs_OUT`, return `IntersectionStats(True, 0.0, True)`. Anything else
   declines.

   **Solid by solid, never against a compound.** `BRepClass3d_SolidClassifier`
   is specified for a solid; what it does when loaded with a compound of
   several solids is not a behaviour this design will rest on. So the
   classifier is loaded from `placed2.Solids()[j]` (and symmetrically), which
   is `s1 × s2` classifications per direction — a handful, since a topmost
   rigid solid is normally one solid and rarely more than a few — and it makes
   step 3 of the proof literally what the code does: the proof is about one
   connected body against another connected body, and so is every call.

Declining always means "run the Boolean that runs today".

### 2. Why disjoint face boxes prove disjoint boundaries — and why that is not
yet a verdict

**Step 1 (boxes → boundaries).** A face's AABB contains that face. A union of
face boxes therefore contains the whole boundary `∂S`. `R` is an invertible
affine map, so the AABB of the eight corners of `S2`'s face box under `R`
contains the image of that face box, hence contains the image of that face
(the same corner-box argument ADR-091 §1 makes for a whole solid, applied to a
face). Enlargement only grows a box. So if no box of `B2'` meets any box of
`B1`, then `R·∂S2 ∩ ∂S1 = ∅`, i.e. the two placed boundaries do not meet.

**Step 2 (boundaries → containment or disjointness).** Let `A`, `B` be closed
regular solids with `∂A ∩ ∂B = ∅`. Every connected component of `∂A` is a
connected set disjoint from `∂B`, hence lies entirely in the interior of `B`
or entirely in its exterior; symmetrically for `∂B`. Therefore
`A ∩ B ≠ ∅` implies one of the two contains the other's material: there is no
partial overlap without the boundaries crossing.

**Step 3 (one vertex per solid decides, in both directions).** A shape here
may be a compound of several solids, and each solid is a separate connected
body: one component could lie inside the partner while another lies outside.
So one representative point per SOLID of each shape is classified, against
each SOLID of the partner — both sides of every classification are then one
connected body, which is what step 2 is a statement about and what
`BRepClass3d_SolidClassifier` is specified for. A vertex of solid `s` lies on
`∂s`, which by step 2 is entirely inside or entirely outside each solid of the
partner — so its classifications decide that whole solid against that whole
partner solid. If every
representative of `S1` is OUT of `S2` and every representative of `S2` is OUT
of `S1`, no solid of either shape lies inside the other, and by step 2 the
intersection is empty. ∎

**Both directions are load-bearing, and so is "per solid".** Two failure
shapes make it concrete:

- `S1` ⊂ `S2` (a small cube inside a big one). `S1`'s vertices are IN `S2`;
  `S2`'s vertices are OUT of `S1`. The `S1`-side check catches it. Without it
  the tier would return a wrong empty for real containment — which the ratified
  scenario "Overlap hidden from a global volume comparison still fails"
  forbids.
- `S2` embedded in the WALL of a hollow `S1`, `∂S2` entirely inside `S1`'s
  material. `S1`'s vertices (on either of its shells) are OUT of `S2`, but
  `S2`'s vertices are IN `S1`. The `S2`-side check catches it.

**Cavities are handled by the classifier itself, not by special-casing.** A
point in a solid's void classifies OUT — verified in this workspace's venv on
a 20 mm cube with a 10 mm cubic void: the centre point classifies
`TopAbs_OUT`, a point in the wall `TopAbs_IN`. That is exactly the semantics
the proof needs: a solid sitting in another's cavity shares no material with
it, so "OUT" is not an approximation there, it is the right answer. Every
representative is OUT in both directions, and the tier reports empty — which
is the same verdict `BRepAlgoAPI_Common` reports for that pair today, more
cheaply.

**The failure direction is always a fall-through.** The tier can be wrong only
by declining to prove something true; it can never assert an emptiness that is
false, because every step it takes is a containment (a face inside its box, a
box inside its transformed box, an enlargement outward) and the final step is a
classifier state that must be OUT for *every* representative.

### 3. Face boxes: `BRepBndLib.Add_s(face, box, False)`, cached per shape identity

`cached_face_boxes(shape)` mirrors `cached_bounding_box`: keyed by
`_shape_keys[id(shape)]`, stored in a `_face_box_cache` beside `_bounds_cache`,
dropped by the same line in `_evict`, and — for a shape with **no** cache
identity (one composed for this comparison, or read from a node whose BREP is
not current) — computed directly and not cached, exactly as
`cached_bounding_box` already does. It returns an `(F, 2, 3)` float64 array;
`(0, 2, 3)` for a shape with no faces.

Each face box is one `Bnd_Box` filled by
`BRepBndLib.Add_s(face.wrapped, box, False)` and read with `box.Get()`, which
already includes the box's gap. Verified in this workspace's venv: for a
cylinder of radius 5, `Get()` returns `±5.0000001` — OCCT's tolerance
enlargement is applied and the box strictly encloses the exact surface.

**Why `useTriangulation=False`, and a correction to the brief.** The stated
reason for avoiding `True` is that a triangulation attached to the shape could
shrink the box below the exact surface. Measured here, that specific fear does
not reproduce: with a 0.5 mm deflection triangulation attached, `Add_s(...,
True)` returned `±5.0365` — *larger* than the exact `±5.0000001`, because OCCT
adds the triangulation's deflection as a gap. The brief also says CadQuery's
`BoundingBox()` default passes `useTriangulation=True`; in the pinned CadQuery
here it does not — `BoundBox._fromTopoDS` defaults to `optimal=True` and calls
`AddOptimal_s`, the tight-but-expensive box, and only its `optimal=False`
branch meshes the shape and passes `True`.

`False` remains the right choice, for reasons that survive the correction and
that the implementer should state in the code comment:

- **Determinism under a cache keyed only on shape identity.** With `True`, the
  box depends on whether a triangulation happens to be attached and at what
  deflection — state that an STL export or a viewer read can change on a shape
  the cache is already holding. A cached measurement must be a pure function
  of its key. `False` makes it one.
- **Conservativeness by construction.** `Add_s(..., False)` bounds each face
  from its surface's own poles/parametric bounds plus the face tolerance:
  outward-only slack, never inward.
- **Cost.** `AddOptimal_s` is an iterative tightening. On a 15-face test part
  the two were indistinguishable (~0.04 ms per shape for all faces), but the
  tightening's cost grows with face count and curvature, and its tightness
  buys nothing here: a tighter face box culls marginally more pairs, and any
  tightening that reached *below* the exact surface would be unsound. Conserv-
  ative and cheap beats tight and slow for a superset test.

*Alternatives considered.* (a) One box per SHELL rather than per face — fewer
boxes, but a shell's box is nearly the solid's box and would cull almost
nothing; the whole point is that faces are where the sparsity is. (b) A BVH
over faces, built once per shape — strictly better asymptotics and the right
answer if F grows into the tens of thousands, but it is a new persistent data
structure with its own eviction and its own tests, for a population (a few
hundred faces per part) where the flat vectorised test is already a few
hundred microseconds. Filed as the follow-up in §7 rather than built here.

### 4. The pair frame: solid 1's own frame, and one padded side

The pair is tested in `S1`'s local frame. `S1`'s face boxes are then used
verbatim — no arithmetic, no residue, exact as cached — and only `S2`'s are
transformed. This is the pair-level analogue of the follow-up ADR-091's
design.md §4 named: for a pair, the first solid's frame is strictly better
than world, because it inflates one side's boxes instead of both, and it
composes with the relative matrix the memo already forms.

`R = inv(M1) @ M2` is computed by the caller and passed in. If `R` carries a
non-finite entry the tier declines — the same failure direction `_verdict_key`
takes for a degenerate composed transform (ADR-090).

**Only the transformed side is padded.** The margin exists to absorb the float
residue of an inversion and two matrix products; that residue lives entirely on
`S2`'s side. Padding one side by `ε` is exactly as separating as padding both
by `ε/2`, and leaving `S1`'s boxes untouched keeps them bit-for-bit what the
cache holds — the same asymmetry, for the same reason, that ADR-091 uses when
it pads every non-world candidate and never the world one.

**`_FACE_BOX_MARGIN = 1e-6` mm, a sibling constant, not a reuse.** ADR-091's
`_INDEXING_FRAME_MARGIN` has the same value and the same rationale — a million
times the residue at metre scale, orders of magnitude below any clearance a
project would want culled on. They are kept separate because they absorb the
arithmetic of two different tiers read by two different call paths, and a
future measurement that moves one should not silently move the other. The
constant's comment names ADR-091's and says they are deliberately equal today.

**The margin can only add work, never remove a pair.** Enlargement only grows a
box, so it can only make the tier decline where it might have proven
disjointness. A pair whose true surface gap is under 1e-6 mm pays the Boolean
it pays today.

### 5. The overlap test: chunked NumPy over F1 × F2, early exit

`_faces_disjoint` computes, for a chunk of rows of `B1` against all of `B2'`,
the standard separating-axis test broadcast over three axes, and returns
`False` (declines) as soon as any pair of boxes overlaps. Overlap follows
`_boxes_disjoint` exactly: disjoint iff `box1.hi < box2.lo` or
`box2.hi < box1.lo` on some axis, with strict `<`, so **touching counts as
overlap** and a flush contact is never culled.

`_FACE_BOX_CHUNK = 256` rows bounds the working set: a chunk is
`256 × F2 × 3` booleans, ~4 MB at F2 = 5000, which is the point of chunking.
The constant is internal tuning, documented like
`_ADAPTIVE_CANDIDATE_BUFFER_LIMIT`.

*Alternative considered: a sweep over the 3D interval endpoints.* It is
`O((F1 + F2) log(F1 + F2))` against the flat test's `O(F1 × F2)`, and it would
win for very large F. It loses here on three counts: the case this cycle
exists for (an enclosed solid touching nothing) has **no** overlapping pair at
all, so there is nothing to early-exit out of and the flat test does its full
work either way — which for F1 = F2 = 300 is 90,000 rows of three comparisons,
sub-millisecond in NumPy; a sweep needs a sort per call or a cached sorted
order per shape (another cached structure, per §3's rejected BVH); and the flat
test is trivially deterministic and trivially reviewable against
`_boxes_disjoint`'s own definition. If the evidence's per-instant tier cost
turns out to be significant against the Booleans saved, the sweep or the BVH is
the follow-up, chosen on that number.

### 6. Where it is called

One function, `_faces_disjoint(shape1, placed1, shape2, placed2, relative)`,
in `solid_node/test.py`, called from exactly two places:

- **`_placed_intersection`, inside the `exact()` closure**, before
  `intersect_shapes`. The AABB cull for this path was already done by the
  whole-assembly index (`_indexing_frame_boxes` → `_bounds_candidates`), so
  the tier is the first thing the closure does. `first[3]`/`second[3]` are
  already-placed shapes, `first[6]`/`second[6]` the matrices — so the relative
  matrix costs one inversion and one product — and `first[8]`/`second[8]` the
  LOCAL shapes, per §6a.
- **`_exact_verdict`**, after its own `_boxes_disjoint` cull and before
  `intersect_shapes`. Here the placed shapes must be materialised for the
  classifier — but `placed_shape` is cached and this is the same set of pairs
  that materialise them today (a pair culled by the AABB returns before them,
  exactly as now), so no pair pays a placement it did not already pay. This
  call site needs no plumbing at all: its `shape1`/`shape2` arguments are
  already the LOCAL shapes, which is exactly what §6a has to add to the record
  path.

### 6a. The record must carry the LOCAL shape

`cached_face_boxes(shape)` keys on `_shape_keys[id(shape)]`, the identity of
the LOCAL cached shape. A placement record does not hold one: it holds the
PLACED copy (`record[3]`), the exact identity (`record[5]`) and the matrix
(`record[6]`). `_solid_geometry` has the local shape in hand and `_place_solid`
drops it after placing.

**Decision: append the local shape as `record[8]`**, exactly as ADR-091
appended local bounds as `record[7]`. `_place_solid` returns `(solid,
deferred_manifold, world_bounds, placed_shape, faceted_identity,
exact_identity, matrix, local_bounds, shape)`, where `shape` is the same
`None`-or-shape `_solid_geometry` already returns and `_place_solid` already
receives as its `shape` argument — no extra cache read, no extra geometry
work, and both call sites already have it.

- No existing tuple position moves, so every index-2/3/4/5/6/7 reader is
  unchanged.
- `_record_key`'s `len(record) <= 6` guard is untouched and still means "this
  record was not built by `_place_solid`": the virtual floor stays a 4-tuple,
  a real record becomes a 9-tuple, and the threshold still separates them.
  ADR-091's comment already states that a future trailing field must keep the
  guard's intent true by staying above 6; this is that future field.
- A shape with no cache identity — a fixture shape composed in memory — still
  travels in `record[8]` and is measured directly and uncached by
  `cached_face_boxes`, exactly as `cached_bounding_box` treats it. The tier
  works on such a shape; only the caching does not.

*Alternative rejected: compute the face boxes from the PLACED shape*
(`record[3]`), which the record already holds. It is wrong twice over. The
placed shape is created per placement, so it has no stable cache identity and
its face boxes would be recomputed — `F` calls to `BRepBndLib.Add_s` per solid
**per instant**, uncached, where the design pays `F` calls per shape **once
ever**. And a placed face box is taken on world axes, so it is inflated by the
solid's own rotation, exactly the inflation §4's local-frame test exists to
avoid.

*Alternative rejected: resolve `record[5]` back through `_shape_cache`.* The
exact identity IS the cache key, so a reverse lookup would work today. It is
refused because it inverts the module's own invariant: `_shape_keys` exists
precisely because a shape cannot be its own key and an identity is a
*derived* fact about a shape the caller already holds. A reverse lookup would
make `test.py` depend on `_shape_cache`'s internal layout, would need a new
public accessor in `exact.py` to avoid reaching into a private dict, and would
silently return the WRONG shape — or `None` — for exactly the fixture shapes
that have no identity, where carrying the object costs nothing and always
works.

**Inside the memo, not around it.** Both call sites sit inside the memoized
computation, so the tier's verdict is cached under the ordinary verdict key
and a repeated question costs one dictionary lookup. That also means a
placement difference below the run's placement quantum serves the tier's
verdict just as it serves a Boolean's — which is precisely the trade ADR-090
ratified, applied to a cheaper computation rather than a new kind of one.

**`assertAssemblySupported` inherits the tier**, because it routes through
`_placed_intersection` too. Its question is directed (does the dropped solid
land inside the target?) but its answer is the same intersection verdict, so
an exact-negative shortcut is as sound there as anywhere. Its virtual floor
carries no shape (`record[3] is None`), so it never reaches the exact branch at
all. No support requirement changes.

### 7. Declines, guards, and cost

The tier declines — falls through to the Boolean — whenever it cannot prove
emptiness:

- either shape has **no faces** or **no solids** (`Solids()` empty): not a
  closed solid, so step 2 of the proof does not apply — and a partner with no
  solids is the same decline, since there is then nothing for the classifier
  to be loaded from;
- a solid has **no vertices** (a full torus is the realistic case): no
  representative point, and the tier does not invent one;
- `relative` is non-finite;
- the classifier is `Rejected()`, or reports `TopAbs_UNKNOWN`, or raises;
- any representative classifies `IN` or `ON`.

`ON` is treated as a decline rather than as contact, deliberately: `ON` at
`Precision::Confusion` on a pair whose face boxes were proven disjoint means
the two computations disagree, and the framework's answer to a disagreement is
the kernel, not the shortcut.

**Cost.** Per proven-disjoint pair: one 4×4 inversion and product; `F2` box
transforms (8 corners each) — vectorisable in one `(F2, 8, 4)` product; up to
`F1 × F2 × 3` comparisons; and one `BRepClass3d_SolidClassifier`
construction per solid of each shape, each performed against the
representative vertices of the other shape's solids (`s1 × s2` per direction,
both directions). Per shape, once ever: `F` calls to
`BRepBndLib.Add_s`. Against a 0.5–2.2 s Boolean this is expected to be
invisible, and **task 5.3 times the tier itself** so the claim is measured
rather than argued. The classifier construction is the one term that could
surprise (it builds an internal explorer over the placed solid); if it does,
caching a classifier per placed solid is the named follow-up — not
done here, because a cache with no measurement behind it is exactly what this
repository's performance record keeps having to undo.

### 8. The inscribed local bounds of an exact solid: recorded, and DEFERRED

`_solid_geometry` reads every topmost solid's local bounds from the STL mesh
via `_cached_local_bounds`, for exact solids as well as faceted ones. A
tessellation's vertices lie **on** the exact surface, so the mesh's extents are
INSCRIBED: on a curved face they can fall short of the exact solid's extents by
up to the declared linear deflection (0.1 mm by default). The whole-assembly
AABB index is therefore **not strictly conservative to the exact surface**, and
a sub-deflection overlap right at a box boundary could in principle be culled —
a completeness hole in the ratified `Broad-phase completeness` requirement,
independent of anything this cycle does.

The fix is at hand and geometrically free: this cycle computes exact face boxes
anyway, and their union **is** an exact conservative solid box. Using that
union as the local bounds of an EXACT solid (faceted solids keep mesh bounds,
the mesh being their geometry) would close the hole at no extra geometric cost.

**Decision: record the finding, do not fix it in this cycle.** Three reasons,
each independently sufficient:

1. **It contradicts ratified text, in two places.** `Accelerated intersection
   evaluation` says "The bounding boxes the broad phase transforms SHALL come
   from the cached base mesh for every solid, exact or faceted. The candidate
   pairs a given assembly emits SHALL NOT depend on whether its solids carry
   exact geometry." The fix reverses both sentences. That is a proposal about
   the whole-assembly index's inputs, deserving its own proposal, its own
   ratification and its own red-first test — not a rider on a pair-level tier.
2. **It must not fire under the faceted kernel.** `_solid_geometry` runs
   whatever the run's kernel is, and a faceted run may not read any solid's
   `shape()` at all (`A faceted run verifies an exact assembly on its meshes`,
   `An exact run never judges a mesh`'s sibling). So the fix needs a
   kernel-conditioned bounds path, which is a real behavioural branch in
   selection — again its own cycle.
3. **It changes when exact shapes are loaded.** Today an exact solid's shape is
   loaded at selection but its FACES are measured only when a pair reaches the
   tier. Making local bounds depend on face boxes measures every selected
   solid's faces at selection, including solids no candidate pair ever
   compares. Cheap, probably; unmeasured, certainly. It belongs with the
   measurement of its own cycle.

Recorded as a **new bullet in `workflow/warts.md`**, marked **Filed** as cycle
`exact-solid-index-bounds`, stating the hole, the deflection bound, the fix,
and that this cycle's `cached_face_boxes` already provides the material for it.
Because it is deferred, this cycle adds **no** spec scenario and **no** test
for it — the pilot can strike the bullet without touching anything else.

If the pilot prefers it folded in after all, the whole of it is: gate on
`_routes_exact(solid)`, take `cached_face_boxes(shape).min/max` as
`local_bounds`, add the MODIFIED sentences to `Accelerated intersection
evaluation`, and add the cylinder-pair test the brief describes (two cylinders
whose mesh boxes are disjoint by less than the deflection while the exact
solids overlap by a sliver must be emitted).

## Risks / Trade-offs

- **[The classifier says OUT for a point that is really inside]** → It is the
  same OCCT classifier the kernel's own algorithms use, run at
  `Precision::Confusion` (1e-7 mm here), on a pair whose boundaries have
  already been proven separated by at least the face-box margin's worth of
  clearance. A wrong OUT would need the classifier to misplace a point that is
  nowhere near a surface. `ON`, `UNKNOWN` and `Rejected` all decline, so the
  only way to a wrong empty is a wrong OUT, and both directions must be wrong
  simultaneously for a containment to slip through.

- **[The tier costs more than it saves on an assembly it never helps]** → Its
  cost is paid only by pairs that already survived the AABB cull, i.e. pairs
  that would run a Boolean; the ratio of a face-box test to a
  `BRepAlgoAPI_Common` is the whole bet. An assembly of a few very
  high-face-count parts whose boxes always overlap and whose surfaces always
  touch would pay the tier and still pay every Boolean. The evidence times the
  tier per instant (task 5.3) so this is a number, not a hope; if it is
  material, the follow-ups in §3 and §5 are where it goes.

- **[A compound whose components straddle the partner]** → Exactly why one
  representative per SOLID is classified rather than one per shape. The test
  for it is a named scenario and a named test.

- **[Someone later drops the containment guard as "obviously redundant"]** →
  The proof in §2 and the ADR both state that disjoint boundaries do NOT imply
  disjoint solids, and the containment test (a small cube inside a big cube)
  fails loudly if the guard is removed. That test exists for that reader.

- **[Someone later switches the face boxes to `useTriangulation=True` or to
  `AddOptimal_s`]** → §3's reasons are in the code comment beside the call,
  and a test builds a cylinder, attaches a triangulation, and asserts the face
  box still reaches the exact radius.

- **[Memo interaction]** → None beyond §6: the tier is inside the memoized
  computation, so it produces the same `IntersectionStats` shape any Boolean
  would, cached under the same key. `exact=True` is preserved, so `_settled`
  and the epsilon-warning path see an exact verdict, which it is.

- **[The surviving pairs are not the plates at all]** → Possible; the wart's
  wording is already known to be imprecise (§Context). Task 5.2 records which
  solids actually sit in the surviving pairs and what the tier decides for
  each, and the wart is corrected to what was measured. The cycle's win is
  reported as measured whatever the answer.

## Migration Plan

None: no public surface, no persisted artifact, no project source change. One
new cache in `exact.py` and one new tier in `test.py`, both behind unchanged
signatures; reverting is reverting the commit.

## Open Questions

One, left for the pilot with evidence rather than a guess: **whether
`exact-solid-index-bounds` (§8) should be folded into this cycle after all.**
The design records the whole fix so that striking or taking it is a small
decision either way; the cycle as proposed does not take it.

Judgement calls made here in the absence of the pilot, all reversible and all
recorded above: face boxes taken with `Add_s(..., False)` rather than
`AddOptimal_s`, for determinism and conservativeness rather than for the
triangulation reason the brief gives (§3, with the measurement that corrects
it); one box per face rather than per shell, and no BVH (§3); the pair tested
in solid 1's frame with only the transformed side padded (§4); a sibling
`_FACE_BOX_MARGIN` constant rather than reusing `_INDEXING_FRAME_MARGIN`,
equal in value today (§4); a chunked flat NumPy test at
`_FACE_BOX_CHUNK = 256` rather than a sweep (§5); the local shape travelling
as `record[8]` rather than being resolved back through `_shape_cache` or
measured from the placed copy (§6a); the tier placed inside the
memoized computation and inherited by `assertAssemblySupported` (§6); `ON`,
`UNKNOWN`, `Rejected`, a faceless shape, a solid-less shape, a vertex-less
solid and a non-finite relative matrix all decline (§7); no classifier cache
until measured (§7); and §8 deferred rather than folded in.

## ADR-092 outline (for the implementer)

`docs/adrs/TEST-FRAMEWORK/ADR-092-face-boxes-decide-an-enclosed-pair-without-a-boolean.md`

- **Status:** Accepted. **Date:** 2026-09-10.
  **Extends:** ADR-029 (manifold cache and AABB broad phase) and ADR-091 (the
  broad phase chooses its indexing frame).
  **Related:** ADR-044 (derived exact-geometry capability — whose `shape()`
  and cache identity this tier's face boxes hang off), ADR-070/090 (the
  sibling exact-negative shortcut and the key this tier's verdict is cached
  under), ADR-025 (verdict semantics that must not move).
- **Context and Problem Statement:** the wall-clock-02 measurement after
  ADR-090 and ADR-091 (67 pairs per instant, 1089 Booleans, 265.99 s, all
  empty); the observation that a whole-solid box, in ANY frame, cannot
  separate a wheel from the plates it runs between, because the plates' extent
  encloses the wheel's; and the corrected reading of the wart's "one fused
  solid" against the two frame-like solids the ADR-091 evidence names.
- **Decision Drivers:** never change a verdict; no new public knob; a one-way
  failure direction (decline → Boolean); cache under the identity discipline
  `exact.py` already has; keep the per-shape work a pure function of the exact
  geometry.
- **Considered Options:** (i) a tighter whole-solid bound — an OBB or convex
  hull per solid — rejected, it does not help at all against enclosure, which
  is a containment relation and not an orientation artefact; (ii) a
  surface-distance query (`BRepExtrema_DistShapeShape`) per pair — rejected,
  it is itself expensive on real parts and answers more than the question
  needs; (iii) face boxes with no containment guard — rejected, it returns a
  wrong empty for a solid wholly inside another, which a ratified scenario
  forbids; (iv) the mesh-distance tier (distance above twice the declared
  linear deflection proves exact solids disjoint) — a separate filed finding,
  it needs the mesh engine and it is inexact where this is exact;
  (v) **face boxes plus a per-solid containment guard — chosen.**
- **Decision Outcome:** §§1–7 of this design, with the three-step proof of §2
  stated in full — it is the load-bearing paragraph of the whole record — and
  with the two asymmetries stated beside it: only the transformed side is
  padded, and only the second shape's boxes are transformed at all. The guard
  is specified solid against solid — one representative vertex of each solid
  of one shape against each solid of the other, in both directions — never a
  point against a compound, so the code is literally the proof's step 3 and
  rests on no unspecified classifier behaviour.
- **Consequences:** an enclosed pair that touches nothing is decided without a
  Boolean (the evidence.md numbers); flush contact still reaches the kernel
  and still fouls at 0.0 mm³, because touching boxes overlap; a solid wholly
  inside another still fails, through the containment guard, and a solid in
  another's cavity passes through it; every exact shape the tier meets carries
  one more cached per-identity measurement, evicted with its shape; the
  faceted path is untouched and a faceted run still reads no `shape()`;
  `assertAssemblySupported` inherits the tier through `_placed_intersection`;
  a placement record grows one trailing field (`record[8]`, the solid's LOCAL
  shape) on ADR-091's own precedent, leaving every existing index reader and
  `_record_key`'s guard untouched;
  the tier's verdict is memoized like any other, so it is served across
  instants under the run's placement quantum; the whole-assembly index's local
  bounds for an exact solid remain the INSCRIBED mesh bounds, which is a
  separate known hole filed as `exact-solid-index-bounds` (§8) and NOT closed
  here.
- **References:** `workflow/warts.md` last section; this change directory;
  `tests/test_face_box_culling.py`.
