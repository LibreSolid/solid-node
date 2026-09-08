# WP8 — Bounded exact placement retention (P07)

## Scope

This package changes only `solid_node/exact.py` and the managed-test-run reset
hook in `solid_node/manager/test.py`.  It replaces the run-local unbounded
placed-shape mapping with a module-owned, access-ordered LRU capped at the
internal default of 512 entries.  The key pairs the stable cached-shape
identity with the exact IEEE-754 bytes of the 3×4 transform consumed by OCCT;
it applies no tolerance or rounding.  Shapes without a stable identity remain
uncached, and a BREP rebuild continues to evict that shape identity's
placements and local bounds eagerly.

The direct isolation seam is private: `exact._reset_placement_cache()`.  A
managed test run calls it only if `solid_node.exact` was already loaded, which
clears same-interpreter retention without importing CadQuery for an otherwise
faceted-only run.  A fresh builder/develop process starts with an empty module
cache by process lifetime.

## Red/green proof

The initial focused red run recorded in [wp8-red.log](wp8-red.log) had 8
failures.  Several correctly established that the new private limit/reset seams
were absent; the signed-zero matrix test exercised existing behavior and
failed because the prior tuple key collided.  Independently, the unchanged
planning baseline's 4,000-transform probe retained 4,000 entries, which is the
actual unbounded-retention observation.  The capacity tests now use
`patch.object(..., create=True)`, so against that legacy implementation their
injected small limit is ignored and they fail by observing over-retention,
verified by an isolated test-only load of planning HEAD: injecting limit 3 and
placing 10 unique transforms retained 10 entries.  The cache-specific green
run then passed 10 tests.  The combined focused suite in [wp8-green.log](wp8-green.log)
passed 120 tests: the new cache tests plus exact geometry, intersection memo,
comparison-policy manager, and keyframe-reversal regressions.

The new tests cover capacity, access-order hits and LRU eviction, exact matrix
bytes (including signed zero), unstable shapes, eager rebuild eviction of
placements and bounds, reset behavior, an evicted placed object retained by a
caller, cached/evicted/uncached OCCT Boolean equivalence, and a working set
smaller than the limit.

## Long trajectory observation

[wp8-memory.log](wp8-memory.log) records a reproducible checked-in probe run
in fresh processes, using a temporary BREP and the workspace venv.  In the
bounded path, retained entries were 512 at 1,000, 4,000, and 8,000 transforms;
the raw uncached comparison retained zero entries at those same points.  The
bounded process's observed RSS was nearly flat across its trajectory; the
uncached process's observed RSS was also nearly flat.  After the trajectory,
a repeated three-transform working set made 12 requests: the first three were
reinserted and the next nine were hits, while the uncached path constructed all
12 placements.

RSS remains an observation rather than proof of an allocation mechanism,
universal bytes-per-shape law, or threshold.  The retained-entry plateau and
the counted useful hits are the P07 result.  The controlled probe explicitly
runs `gc.collect()` at sample points, so its nearly-flat RSS does not establish
an ordinary runtime RSS plateau.  The earlier no-forced-collection observation
is preserved separately in [wp8-memory-initial.log](wp8-memory-initial.log).

## Provenance and limits

- Planning/baseline source: `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c` on
  `performance-analysis`.
- Interpreter: `/home/asa/devel/libresolid-studio/.venv/bin/python` with
  `PYTHONPATH="$PWD"`, from the framework worktree.
- Candidate source/test SHA-256 values after the green run:
  - `solid_node/exact.py`:
    `da81c386f9f7dcf3a1c1bd1790f36667be5505c9f83eb6b4f5f3d9b3de659e27`
  - `solid_node/manager/test.py`:
    `080e6cc9b951391bcde7a5843d888eb8ed55eb58f83ba191a67ad1d2fcc23d28`
  - `tests/test_exact_placement_cache.py`:
    `c20f4a70805313f996b562475586f678a68cbe3b72f83ffecbbce72ef902fdd4`
  - `workflow/due-dilligence-performance/remediation/wp8_probe.py`:
    `e3056c094bc839e27a82f411e7eaff35610c187035f4f2b27b7cf097aafe55c4`
- No original project, historical audit asset, task checkbox, OpenSpec record,
  ADR, or progress record was changed by this package.
- Measurements ran after the root baseline gate and without a competing
  benchmark from this worker. Other package agents were active; root advised
  that WP1 tests could overlap, so the elapsed/RSS figures are observational
  rather than comparative timing evidence.
