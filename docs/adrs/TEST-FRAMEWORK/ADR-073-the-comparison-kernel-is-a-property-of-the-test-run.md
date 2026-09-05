# ADR-073: The Comparison Kernel Is a Property of the Test Run

**Status:** Accepted
**Date:** 2026-09-05
**Extends:**
- [ADR-044: Derived exact geometry capability](../NODE/ADR-044-derived-exact-geometry-capability.md)
- [ADR-029: Manifold Cache and AABB Broad Phase for Assertions](./ADR-029-manifold-cache-and-aabb-broad-phase-for-assertions.md)

**Related to:**
- [ADR-025: Perturbation-Based Kinematic Fit Assertions](./ADR-025-perturbation-based-kinematic-fit-assertions.md)
- [ADR-040: Topmost-Rigid Assembly Integrity](./ADR-040-topmost-rigid-assembly-integrity.md)
- [ADR-052: Conditional mesh-engine dependency](./ADR-052-conditional-mesh-engine-dependency.md)
- [ADR-070: Relative Placement as the Identity of an Intersection Question](./ADR-070-relative-placement-as-the-identity-of-an-intersection-question.md)

## Context and Problem Statement

ADR-044 made exactness a property of geometry, fixed by adapter type, and
routed every intersection, containment, connectivity and weld question of two
exact nodes through the OCCT boundary-representation kernel. That is the right
verdict and the wrong price for a development loop. ADR-070 removed every
repeated computation from a swept suite and left the remainder named: a
flexible part's comparisons are uncacheable by construction and cost about
430 ms each on the exact kernel against about 14 ms on the part's own mesh,
with the same verdict (`spike/interference/FINDINGS.md`, finding 6). The
v8-engine root suite took 28 minutes.

Finding 6 asked whether the mesh path should be the default and answered that
the choice was the pilot's, because the faceted path is not the exact path
minus cost: tessellation is written at 0.1 mm, meshes overlap by slivers
where solids only touch, `assertNoSolidInterference` is specified
epsilon-free, and `volume_epsilon` is ignored on exact pairs.

The question this record settles is where the choice of kernel lives.

## Decision Drivers

- The same suite must run fast while a developer iterates and exactly when a
  commit, a release or CI decides — without editing the model or the tests.
- The exact run must stay byte-for-byte what it is: verdicts, warnings,
  messages, imports and output.
- A fast green run must never be mistaken for an exact one.
- Every assertion's contract is stated against the exact kernel; a default
  that silently weakened verdicts is the substitution the shop's operating
  contract forbids.

## Considered Options

1. **A run-level policy: exact by default, faceted by flag or by the
   checkout's ignored `.env`** (chosen)
2. A declaration on the root node, or new declarative syntax
3. A kernel parameter on every assertion
4. A setting in the committed project manifest
5. Making the mesh path the default and the exact kernel the opt-in

## Decision Outcome

**Option 1.** `solid_node/test.py` holds one comparison policy per run,
`(kernel, volume_epsilon)`. `solid test` resolves it from the mutually
exclusive `--exact` / `--faceted` flags, else `SOLID_TEST_KERNEL`, else
exact, and sets it before the first build; any other entry — a
`ScenarioTest` under pytest, an assertion driven directly — resolves the same
policy from the environment at the first comparison. One predicate,
`_routes_exact(node)`, replaces the five routing reads of `node.exact`: a
node routes exact when it is exact **and** the run's kernel is exact. Under
the faceted kernel no `shape()` is read, no deferred kernel name is resolved,
and every question takes the path a non-exact node already takes.

A faceted run carries one volume epsilon (mm³, default 0.0), from
`--volume-epsilon`, else `SOLID_TEST_VOLUME_EPSILON`, else 0. It is applied
by the two engine-native verdict producers after the memo of ADR-070 is
read — the cache keeps raw verdicts — so every volume assertion inherits it
and `assertNoSolidInterference` still adds nothing of its own. At 0.0 it
changes nothing: the non-empty zero-volume flush contact of ADR-025/029
still fouls. The exact kernel refuses an epsilon and does not read the
environment's, so a checkout's `.env` may carry both lines while CI
overrides only the kernel.

A faceted run announces itself before the first build and suffixes the
summary line with `(faceted kernel, volume epsilon E mm³)`; the summary
prefix is preserved verbatim for parsers. `node.exact` keeps reporting the
geometry's capability, and the build is untouched: the kernel is the run's,
not the model's. `solid new` ignores `.env`.

Options 2 and 4 were rejected because a committed value is either always
slow or always weak and CI would inherit the developer's choice; option 2
also puts a property of the run into the declarative surface that describes
what a part *is*. Option 3 freezes the policy in test source and must be
flipped at every call site; the existing `volume_epsilon` is already
documented as a smell for the same reason. Option 5 was rejected because the
assertions' contracts are exact ones and the fast loop is one line in an
ignored file away.

## Consequences

- On the v8-engine root suite (36 tests, springs included) the faceted run
  takes 90 s where the exact run took 1687 s, and at epsilon 0 reaches the
  same verdict on every comparison. The one failure it reports —
  the hand-crank arm sharing 12.3 mm³ with the display-stand base at four of
  a sweep's 73 instants, at a measured exact clearance of 0.0 mm — is one the
  exact kernel reports too. It is a finding for that project.
- A faceted verdict is at tessellation precision. A clearance thinner than
  the 0.1 mm chord deviation can read as slight overlap and interference
  thinner than it can be missed; the docs say that commit evidence and
  release checks come from the exact run, and the run's own output says
  which kernel produced it.
- The mesh engine is required by a faceted run of an all-exact project, by
  construction; the conditional-dependency contract of ADR-052 is about the
  exact run, which is unchanged.
- A per-test or per-assertion exact override for a suite that is mostly
  decidable on meshes but has one sub-tessellation fit is deferred until a
  project produces the case; the v8 root suite did not.
- The shop floor's `solid_test` tool can expose the kernel to the machinist
  (exact before a commit, faceted while iterating); that is a shop decision.

## References

- `solid_node/test.py` — `ComparisonPolicy`, `resolve_comparison_policy`,
  `_routes_exact`, `_settled`
- `solid_node/manager/test.py` — the flags, the announcement, the summary
  suffix
- `tests/test_exact_geometry.py` (`FacetedKernelTest`),
  `tests/test_manager_test.py` (`ComparisonKernelSelectionTest`),
  `tests/test_meta.py` (`FacetedKernelMetaTest`), fixture
  `tests/meta_project/exact_clearance.py`
- `spike/interference/FINDINGS.md` — finding 6
- OpenSpec change `faceted-test-kernel`, capabilities `test-framework`,
  `cli`, `user-documentation`
