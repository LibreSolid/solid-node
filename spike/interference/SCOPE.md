# Spike: where a solid-node test run spends its time

Design evidence for the `fast-test-feedback` OpenSpec change. This spike
locates the cost of a test run and validates or invalidates three candidate
fixes. It creates no requirements and ships no framework code. Everything
under `spike/interference/` is non-shipping measurement.

## Primary question

`docs/performance-improvement.md` fixes 1-3 landed and made the faceted
boolean cheap. Test runs are still slow. Where does the time go now, and is
the remaining cost in the boolean kernels at all?

## Questions this spike answers

1. What does a pair cost through each evaluation path today — faceted
   (`manifold3d`) and exact (OCCT `BRepAlgoAPI_Common`) — for an empty and a
   non-empty verdict?
2. Can a cheaper exact-negative filter reject a pair that survives the AABB
   broad phase but is still empty, before the boolean runs?
3. In a real animated suite, how many intersection comparisons repeat a
   question the run has already answered?
4. Is there a case for GPU evaluation? (Raised by the pilot;
   `docs/performance-improvement.md` already appraised it once, before the
   exact path existed.)

## Scripts

- `midphase.py` — per-pair cost of the faceted kernel, against a candidate
  triangle-level mid-phase that culls to the two parts' AABB overlap box.
- `exact_cost.py` — stage-by-stage cost of the exact path on real v8-engine
  BREP artifacts: import, bounding box, placement, boolean, result read.
- `census.py` — wraps `_intersection_stats` and the kernel entry points and
  runs the real v8-engine suite through the `solid test` runner, counting
  calls, time, and comparisons that repeat a (parts, relative placement) key.

Verdicts are in `FINDINGS.md`.
