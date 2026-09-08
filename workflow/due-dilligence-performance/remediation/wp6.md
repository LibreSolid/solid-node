# WP6 — Adaptive ordered broad phase (P05)

`solid_node.test._bounds_candidates` now measures interval pressure on X first.
Zero X pressure is a proven global minimum, so it preserves the old X sweep
without sorting Y/Z.  Otherwise it measures Y and Z with an inclusive
endpoint heap, chooses the least-pressure axis with X/Y/Z tie-breaking, and
filters discovered candidates through the unchanged full-AABB predicate.

Adaptive candidates are buffered only up to a private finite limit, then
sorted by `(later X rank, earlier X rank)` to reproduce the old X-sweep order.
When the buffer fills, it discards the adaptive result and streams the old X
sweep.  Thus dense cases retain no quadratic pair list and first-foul/support
diagnostic order remains unchanged.

## Red/green proof

[wp6-red.log](wp6-red.log) records the unchanged X sweep's structural failure:
128/256/512/1,024 boxes whose X intervals all overlap but whose Y intervals
are disjoint caused 8,128/32,640/130,816/523,776 full-AABB checks.  The new
test requires zero checks on that input, not a wall-clock threshold.

[wp6-green.log](wp6-green.log) records the combined focused result: 170
passed, 22 subtests, and 3 pre-existing warnings.  The dedicated tests also
pin inclusive face/edge/vertex touches, degenerate bounds, containment,
coincidence, X/Y/Z ties, exhaustive independent AABB oracle cases, multiple
deterministic randomized inputs plus reversed input order, rotated world
bounds, directed support candidates, exact legacy-X order, and fallback after
a deliberately tiny candidate buffer. The X-pressure-zero fast path is also
structurally pinned to avoid Y/Z pressure estimates.

Real-project bounds are not claimed as package evidence yet. WP10's
current-project remeasurement must compare those bounds/candidates with the
legacy reference under its provenance and disposable-project rules.

No OpenSpec task, progress, specification, ADR, or historical evidence file
was changed.  The shared `solid_node/test.py` retains WP5's flexible-cache
work; this package modified only the broad-phase region.
