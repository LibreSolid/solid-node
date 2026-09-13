# Validation — voron-faceted-contact

Date: 2026-09-13. Base `b768bdf979552751d016dd89c2f5814693134f9a`;
ratified planning commit `f08eb5c`. All framework commands run inside the
isolated bench with `PYTHONPATH="$PWD"` and workspace
`/home/asa/devel/libresolid-studio/.venv/bin/python` or sibling `solid`.
The tested import path was verified to name this bench's `solid_node`.

## Red, green and mutations

Command: `python -m pytest tests/test_assembly_integrity.py -q`.

- Before implementation: 7 failures (six signed/kernel subcases and the
  negative-then-positive sequence), 21 passed, 18 subtests passed. Failures
  reported the negative candidates, not a loader or environment problem.
- After implementation: 22 passed, 24 subtests passed.
- Old-sign mutation (disable the new branch), `-k finite_negative_faceted`:
  all six negative/kernel subcases failed. Restored afterward.
- Positive-skipping mutation (continue for every nonzero volume),
  `-k any_positive_candidate`: the smallest-positive test failed because
  `AssertionError` was not raised. Restored afterward.

No epsilon, source movement, repair or cached-verdict normalization was used.
The regression table covers ordinary and subnormal signed values, ±zero,
NaN and both infinities, exact provenance, remaining candidates, and unchanged
strict pairwise and fit checks. These synthetic candidate tests establish the
decision boundary; the independent actual-source run below establishes the
caller path. They do not certify arbitrary negative-volume geometry.

After both mutations were restored, the combined final unit regression passed
214 tests and 72 subtests (one expected deprecation warning). With the 23
passing CLI meta tests, that is 237 passing tests. Strict validation passes
for the change and the baseline `test-framework` capability. Synchronization
was compared byte-for-byte for the changed requirement: all 19 original
scenarios remain and the six ratified scenarios are present.

## Broader framework regression

`python -m pytest tests/test_exact_geometry.py tests/test_exact_test_isolation.py
tests/test_intersection_memo.py tests/test_manifold_cache.py
tests/test_broad_phase_culling.py tests/test_adaptive_broad_phase.py
tests/test_manager_test.py -q`:
192 passed, 48 subtests passed; one expected deprecated-sweep warning.

`python -m pytest tests/test_meta.py -k 'AssemblyIntegrity or VolumeEpsilon or
FacetedKernel or ExactGeometry or PerturbationAssertions' -q`:
23 passed, 38 deselected. These meta tests check actual CLI/build/test behavior,
including deliberately red strict-contact fixtures.

## Originating project

Project `projects/3D-Printers/Voron-2` remains at `235451b` for this check.
The reference is its absolute
`simulation/tools/corner_probe.py:SourceCorner`, source solids 1262 and 1388.
`SOLID_BUILD_DIR="$PWD/_build/voron-corner"` isolates diagnostic artifacts
from the project's published frame. Run `solid test --faceted <reference>`
and `solid test --exact <reference>` from the framework bench.

| Kernel | Assembly integrity | Strict pairwise | CLI result |
| --- | --- | --- | --- |
| Faceted, base | FAIL | FAIL | 0/2 pass, exit 1 |
| Faceted, fixed | PASS | FAIL (unchanged negative measurement) | 1/2 pass, exit 1 |
| Exact, base and fixed | PASS | PASS | 2/2 pass, exit 0 |

The faceted diagnostic's exit 1 is intentional evidence of preserved strict
pairwise behavior, not a green-suite claim. The measured negative value remains
−9.947598300641403e−14 mm³. The initial project diagnosis confused
engine-emptiness and positive-material questions; the resumed project must
correct that wording and use the appropriate contract without hiding contact.
The genuine frame overlap inventory and remaining machine are unfinished.

## Architecture and scope

No new ADR: this is a scoped assertion correction under ADR-040, preserving
ADR-029/073 and changing no boundary, public argument, dependency, cache or
broad phase. The synthesis now states the assembly/pairwise distinction.
No viewer, source CAD, upstream mesh, primary checkout or other worktree was
edited during implementation. Integration is separately authorized by the
pilot and gated on clean unchanged main and a complete two-commit cycle.
