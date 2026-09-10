# ADR-090: The Placement Quantum Is a Property of the Test Run

**Status:** Accepted
**Date:** 2026-09-09
**Amends:**
- [ADR-070: Relative Placement as the Identity of an Intersection Question](./ADR-070-relative-placement-as-the-identity-of-an-intersection-question.md)

**Related to:**
- [ADR-073: The Comparison Kernel Is a Property of the Test Run](./ADR-073-the-comparison-kernel-is-a-property-of-the-test-run.md)
- [ADR-029: Manifold Cache and AABB Broad Phase for Assertions](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)
- [ADR-025: Perturbation-Based Kinematic Fit Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md)

## Context and Problem Statement

ADR-070's verdict memo keys an intersection question on
`(identity₁, identity₂, path, bytes(inv(M₁) @ M₂))` — the exact bytes of the
pair's relative placement. That key asks a narrower question than it means
to.

Measured on 3DPrintedClocks `wall_clock_02` under the exact kernel
(`workflow/warts.md`, "3DPrintedClocks wall clock 02 (2026-09-09, exact
sweep cost)"): a sweep instant costs ~19 s, essentially all of it in
`BRepAlgoAPI_Common`. Of 118 candidate pairs from the world-AABB broad
phase, 30 are rigidly carried together — the pendulum with its suspension,
the motion works, the weight with its line — and their relative matrices
differ between instants by ~1e-13. Only 5 pairs hit the memo. That ~1e-13
is not a placement: it is the residue of composing the same rigid motion
by two different routes in IEEE 754 — the parent rotation multiplies into
each child's chain in a different order, and the last bits disagree. The
memo asks "are these the same bytes?" when the question it means is "are
these the same placement?".

## Decision Drivers

- The memo must never change a verdict (ADR-070's first driver, carried
  over in force).
- The default run's output must not change (ADR-073's driver: a green run
  must never read as a different one in a log).
- A tolerance must not be made globally and invisibly. ADR-070 rejected
  "key on the relative matrix rounded to a tolerance" precisely because a
  hidden, global rounding would decide, for every project at once, the
  judgement `volume_epsilon` exists to leave with the project.

## Considered Options

1. **A quantised key, as a run-level option** (chosen)
2. Canonicalise the relative matrix instead — re-orthonormalise the
   rotation block and round to a fixed number of significant digits
3. Key on the two nodes' *declared* placements rather than the composed
   matrices
4. Leave it and take the cost

## Decision Outcome

Chosen: **a quantised key, as a run-level option.**

`_verdict_key` now divides the relative matrix by the run's placement
quantum and rounds to INTEGER cell indices — not rounded floats — before
keying:

```python
relative = np.linalg.inv(matrix1) @ matrix2
if not np.all(np.isfinite(relative)):
    return None
cells = np.rint(relative / q).astype(np.int64)
return (identity1, identity2, path, q, cells.tobytes())
```

Integer cells, not `np.round(relative / q) * q`: `-0.0` and `0.0` are
distinct byte patterns as floats but `np.rint(...).astype(np.int64)` maps
both to the integer `0`, so a placement landing on a cell boundary from
either side is one key. A relative matrix carrying a non-finite entry — a
degenerate composed transform — yields no key and is computed exactly as
today, on the same "not cacheable" path an identity-less node already
takes.

The quantum is a field of `ComparisonPolicy`, resolved and validated
before the kernel is even branched on, and carried by BOTH kernels — the
one deliberate departure from mirroring `volume_epsilon`, because the
quantum identifies a question (arithmetic noise) and not a quantity of
material, and both kernels' verdicts pass through the same memo. It sits
in the key tuple beside `path`, so two entries built under two different
quanta in one process (a test suite that changes policy mid-run) can
never compare equal even if their cell indices coincide. Three
spellings name one value: policy field `placement_quantum`, flag
`--placement-quantum MM`, environment `SOLID_TEST_PLACEMENT_QUANTUM`,
resolved flag-beats-environment-beats-default exactly as ADR-073's
kernel and epsilon are. The default is `1e-9` mm. `--placement-quantum 0`
restores ADR-070's exact-bytes key precisely — not "no memo", the escape
hatch that keeps that key reachable and testable. A negative or
non-finite value is refused naming whichever of `--placement-quantum` or
`SOLID_TEST_PLACEMENT_QUANTUM` supplied it: `inf` parses as a valid float
but divides every relative matrix down to the same all-zero cell,
serving one verdict for every pair in the run, and `nan` reaches
`astype(np.int64)` undefined, so both are checked with `math.isfinite`
alongside the negative check, from either source, before the kernel is
branched on. No upper bound is imposed: a cap would be a second, invisible judgement,
and any cap defensible at one machine scale is wrong at another. A
non-default quantum is named on the summary line, in the same
parenthesis ADR-073 established, beside the faceted label and epsilon
when both apply; the default run's output is unchanged, byte for byte,
with no pre-build line.

### Why this cannot serve a wrong verdict

Two relative matrices sharing a cell differ per entry by less than the
quantum `q` (each within `q/2` of the cell centre). Writing a point of
the second solid, in the first's frame, as `p = A x + t`, the two
placements move it by at most `‖A' − A‖·|x| + |t' − t| ≤ 3q·L + √3 q`,
linear in `q` and in the part's extent `L` from its own origin. At the
default `q = 1e-9` mm and `L = 1000` mm (a metre-scale part) that bound
is about **3 nanometres** — far below the exact kernel's own tolerances,
OCCT's `Precision::Confusion` (1e-7 mm), and any clearance a machine is
designed to hold. The flush-contact contract of ADR-025/ADR-029 — a
non-empty result at exactly 0.0 mm³ — is a statement about *touching*,
and two placements 3 nm apart both touch or both do not, unless a
design's clearance is itself 3 nm, which is not a design.

The failure direction is a miss, not a wrong hit: nothing forces two
placements within `q` into the same cell, so two values straddling a
cell boundary still differ and are still recomputed, exactly as today.
Quantisation can only ADD cache hits, never remove correctness margin at
a boundary. To get a wrong verdict from the memo, two placements would
have to differ by a real, INTENDED amount smaller than `q` and land in
one cell — unreachable at `q = 1e-9` mm, and a user who raises `q` to a
value where it might not be has stated that value explicitly, and the
summary line repeats it.

**Float64's mantissa, not `int64`, bounds the usable range.** A cell
index is `entry / q`, computed in float64 before the cast; float64
represents consecutive integers exactly only up to 2^53 ≈ 9.0e15. At the
default `q = 1e-9` mm a translation entry is exactly representable as a
cell index up to about ±9.0e15 cells — **±9.0e6 mm, a 9 km machine** —
ample for anything this framework models, and the degradation past it is
graceful (cells coarsen where the coordinate has already coarsened), not
wrong. Rotation entries are dimensionless and bounded by 1 for a rigid
matrix, so ±1e9 cells, nowhere near it.

### Why not canonicalising the matrix instead (option 2)

Re-orthonormalising the rotation block and rounding to significant
digits is still a tolerance — one with no name, no dial, and no place in
the run's stated policy. It would trade a visible, documented, removable
quantum for an invisible one baked into the key function.

### Why not keying on declared placements (option 3)

A flexible or derived placement has no declared form to key on — it is a
function of the current binding, evaluated at composition time.
ADR-070's finding 5 already showed that a name-shaped key overcounts
(the spike's census predicted 54% and measured 21%, because a flexible
part's geometry is a function of the driver binding, not of its name).
Keying on declared placements would repeat that mistake for every
carried pair, not just flexible ones.

### Why not leaving it (option 4)

The finding is a quarter of a sweep instant on the originating project,
and the noise it re-asks about is not a property of one project's
geometry but of composing matrices in IEEE 754 at all — every carried
assembly pays it.

## Consequences

- Measured on 3DPrintedClocks `wall_clock_02`,
  `test_movement_runs_free_through_a_swing` (`@testing_steps(48)`), under
  the exact kernel, before and after this change, and again after with
  `--placement-quantum 0` (full counts and the per-instant arithmetic in
  `evidence.md` of the `quantise-verdict-memo` OpenSpec change):

  | Run | Keyed asks | Memo hits | Booleans | Wall time |
  |---|---:|---:|---:|---:|
  | Before | 5527 | 1823 | 3820 | 779.37 s |
  | After (default quantum) | 5643 | 3117 | 2526 | 533.39 s |
  | After, `--placement-quantum 0` | 5643 | 1963 | 3680 | 692.68 s |

  Booleans fell 33.9% (1294 fewer, exactly the rise in memo hits) and wall
  time fell 31.6% — at or above the finding's ~25% forecast, the opposite
  direction from ADR-070's own history where the forecast proved generous.
  The quantum-0 run, on the same changed tree, reproduces the "before"
  shape (hits and booleans close to "before"'s, well short of the
  default-quantum run's), confirming the win comes from the quantum and
  not from any other change in this cycle. All three runs report the
  identical test verdict (`1 passed, 0 failed`), and the quantum-0 run's
  own summary line read `... (placement quantum 0 mm)`, confirming the
  announcement fires correctly outside the test suite too.
- The default run's output is unchanged, byte for byte — no announcement,
  no change to the summary line, confirmed by the manager test suite's
  exact-string assertion.
- `placed_shape`, `_placement_cache` and `_bounds_cache` in
  `solid_node/exact.py` still key on exact matrix bytes with no rounding
  — quantisation is for the verdict key alone, never for the geometry a
  comparison is handed. `_world_bounds` and `_boxes_disjoint` still read
  real matrices.
- Flexible parts remain uncacheable by construction (unchanged from
  ADR-070): a flexible leaf's per-instant identity was never the reason
  the memo missed carried pairs, and this cycle does not touch it.
- The two remaining wall-clock-02 findings — `broad-phase-in-the-root-frame`
  and `face-box-broad-phase` — are independent of this one and are their
  own cycles, as is the mesh-distance exact-negative tier and parallel
  pair booleans.
- `ComparisonPolicy`'s third field is declared with a default
  (`defaults=(DEFAULT_PLACEMENT_QUANTUM,)`), so the framework's own seven
  positional two-argument constructions of `ComparisonPolicy` keep
  meaning what they meant — "at the default quantum" — without editing
  any of them. The one place the default cannot help is EQUALITY: a
  2-tuple never equals a 3-tuple, so `ComparisonKernelSelectionTest`'s
  policy-equality assertions were widened to 3-tuples. That is an
  intended, visible break: a policy is what the run compares on, and a
  new dimension of it belongs in the tuple a test pins.

## References

- `solid_node/test.py` — `ComparisonPolicy`, `DEFAULT_PLACEMENT_QUANTUM`,
  `resolve_comparison_policy`, `_verdict_key`
- `solid_node/manager/test.py` — `--placement-quantum`, the summary suffix
- `tests/test_intersection_memo.py` — the carried-pair, boundary, zero-quantum,
  signed-zero, exact-kernel and non-finite scenarios
- `tests/test_manager_test.py` — `ComparisonKernelSelectionTest`
- `workflow/warts.md` — "3DPrintedClocks wall clock 02 (2026-09-09, exact
  sweep cost)"
- OpenSpec change `quantise-verdict-memo`, capability `test-framework`
