## Context

Every intersection, containment, connectivity and weld assertion in
`solid_node/test.py` routes on the compared nodes' `exact` attribute: two
exact nodes are compared by the OCCT boundary-representation kernel, any
other pair by `manifold3d` over the parts' built STLs (ADR-029, ADR-044,
ADR-052). Exactness is fixed by adapter type, so a project modelled in
CadQuery, build123d or molejo takes the exact path for every comparison
whether or not the question needs it.

`spike/interference/FINDINGS.md` measured what that costs on the v8-engine
root suite after the `fast-test-feedback` cycle removed every repeated
computation: the uncacheable flexible-part comparisons remain, at roughly
430 ms each on the exact kernel against roughly 14 ms on meshes, with the
same verdict. Finding 6 asked whether the default should be the mesh path
and answered that the choice is the pilot's, because the faceted path is not
the exact path minus cost: tessellation is written at 0.1 mm, meshes produce
contact noise where solids touch exactly, `assertNoSolidInterference` is
specified epsilon-free, and `volume_epsilon` is ignored on exact pairs.

Design evidence gathered for this change on 2026-09-05, in the originating
project (`projects/v8-engine`, root suite `solid test`, 36 tests, springs
included), by shadowing `exact` on every node class after an ordinary build:

| run | wall time | result |
| --- | ---: | --- |
| exact kernel (FINDINGS, same suite) | 1687 s | — |
| faceted kernel, epsilon 0.0 | 92 s | 34 passed, 2 failed |

Of the two failures, one was the spike's own artifact — a test that asserts
`node.exact` is true, which the shadowing falsified and which the design
below leaves true — and the other,
`test_new_rotating_parts_clear_nearby_stationary_structure`, fails on the
exact kernel too: the hand-crank arm and the display-stand base share
12.3 mm³ at four of the sweep's 73 instants, with a measured exact clearance
of 0.0 mm there against 0.4 mm elsewhere. That is a finding for the project,
not a kernel disagreement. **At epsilon 0.0 the two kernels reached the same
verdict on every comparison of the v8 root suite**, 18 times faster.

## Goals / Non-Goals

**Goals:**

- A developer runs a suite on meshes without editing the model or the tests,
  and a CI runner runs the same suite exactly without configuring anything.
- The choice lives where checkout-local configuration already lives: the
  project's ignored `.env`, read by the CLI like every other `SOLID_*`
  setting, overridable by a flag.
- A faceted run is always visibly a faceted run.
- The exact run — its verdicts, warnings, messages, imports and output — is
  byte-for-byte what it is today.
- One seam: the five routing sites ask one policy; the two engine-native
  verdict helpers apply one epsilon.

**Non-Goals:**

- Changing what a node's `exact` attribute reports, or what the build writes.
  The kernel is a property of the run.
- A per-assertion or per-test kernel override. The evidence shows no
  comparison in the originating project that needs the exact kernel while the
  rest run faceted; if one appears, it is a new requirement with its own
  evidence (see Open Questions).
- A tolerance on the exact kernel. It has none to absorb; offering one is
  refused.
- Any change to the build: a faceted run of an exact project still builds its
  BREPs, because the build is the model's, not the run's.
- Skipping the shop-floor `solid_test` tool's matching argument: that is a
  shop change in the shop repository, made separately.

## Decisions

### The kernel is a run policy, resolved once, not a node property

**Decision.** `solid_node/test.py` holds one module-level comparison policy,
`(kernel, volume_epsilon)`. `solid test` resolves it from its flags and the
environment and sets it before building the first node. Any other entry —
`ScenarioTest` under pytest, an assertion driven directly — resolves it from
the environment at the first comparison of the process, with the same rules.
A single predicate replaces the five `getattr(node, 'exact', False)` routing
reads: a node routes exact when it is exact AND the run's kernel is exact.

**Alternatives.**

- *A declaration on the root node* (a class attribute or new syntax). Rejected:
  the declarative API is explicit that the class body declares what a part
  is, and this is not a property of the part. A committed value is either
  always slow or always weak, switching means editing source, and CI would
  inherit the developer's choice.
- *A `volume_epsilon`-style parameter on every assertion.* Rejected as the
  primary mechanism: it freezes the policy in test source, must be changed at
  every call site to switch modes, and the existing `volume_epsilon` is
  already documented as a smell rather than a tool.
- *A setting in `pyproject.toml`.* Rejected: the manifest is committed, so CI
  would inherit it. The ignored `.env` is the one place that is per-checkout
  by construction, and `scripts/dev-env` already writes per-bench `.env`
  files for exactly this reason.

### Exact stays the default

**Decision.** Without a flag and without `SOLID_TEST_KERNEL`, the run is
today's run. Finding 6 asked whether the mesh path should be the default;
this change answers no. Every assertion's contract is stated against the
exact kernel; a default that silently weakened verdicts would be the
substitution the shop's contract forbids. The fast loop is one line in an
ignored file away, and a CI runner that has no such file needs nothing.

### One epsilon, applied at the verdict helpers, composing with the assertion's own

**Decision.** A faceted run carries a volume epsilon (mm³, default 0.0).
`_intersection_stats` and `_placed_intersection` — the two engine-native
`(is_empty, volume)` producers every volume assertion reads — apply it after
the memoized verdict is read: a volume not above the epsilon is reported as
empty with zero volume. `assertNoSolidInterference` keeps adding nothing of
its own; the perturbation assertions' `volume_epsilon` keeps filtering on top.
The verdict cache stores the raw engine verdict, so a policy change within a
process (framework tests) never serves a filtered verdict as a raw one.

**Why a volume, and why zero by default.** Every assertion already speaks
mm³, and the spike showed the originating project needs no epsilon at all:
its clearances exceed the 0.1 mm tessellation deviation, so the meshes never
touch where the solids do not. A linear "penetration depth" would be the more
physical knob but the boolean does not produce it, and deriving it from a
volume needs a contact area the framework does not have. The number, when a
project needs one, is the developer's statement about that project's tight
fits, recorded beside the kernel choice in the same `.env`.

**Refusal on the exact kernel.** `--volume-epsilon` with an exact run is a
usage error, and `SOLID_TEST_VOLUME_EPSILON` is not read under the exact
kernel: the exact kernel has nothing to absorb, and the ignored-epsilon
warning already establishes that a tolerance nobody applies is a mistake
worth naming. Reading the environment only under the faceted kernel lets a
developer's `.env` carry both lines while CI overrides only the kernel.

### A faceted run announces itself twice

**Decision.** Before the first build the runner prints one line naming the
faceted kernel and its epsilon; the summary line gains the suffix
` (faceted kernel, volume epsilon E mm³)`. The exact run prints neither. The
summary prefix `Ran N tests in X seconds: P passed, F failed` is preserved
verbatim so `tests/test_meta.py` and any external parser keep matching, and
the suffix is what stops a green fast run from being read as an exact one in
a log or a commit message.

### The faceted run never reaches the exact stack through the test framework

**Decision.** Under the faceted kernel no routing site calls `shape()`, so the
deferred kernel names of `solid_node/test.py` are never resolved and
`cadquery` is not imported by the test framework — the `cli-startup-cost`
discipline holds for the fast loop without a new mechanism. The build still
imports what it needs; that is the build's cost.

### The scaffold ignores `.env`

**Decision.** `solid new` adds `.env` to the generated `.gitignore`, so the
line a developer writes there is per-checkout from the first commit. A
project scaffolded earlier adds the line itself; nothing in the framework
depends on it.

## Risks / Trade-offs

- [A faceted green run is trusted as release evidence] → the run is
  labelled at start and on the summary line; the docs state that CI and
  release runs are exact and that a faceted verdict is at tessellation
  precision.
- [A project with sub-tessellation clearances fails faceted at epsilon 0]
  → that is the honest answer: the faceted kernel cannot decide that
  question. The developer either records an epsilon that names the noise, or
  runs that suite exact. The docs say which is which. The v8 evidence shows
  a well-clearanced project needs neither.
- [An epsilon large enough to hide real interference] → the epsilon is
  visible on every faceted summary line, exists only under the faceted
  kernel, and never reaches the exact run CI performs.
- [A `.env` committed by accident enables faceted runs in CI] → the new
  scaffold ignores it; an existing project's CI is exact only while its
  `.env` stays out of the repository, which the docs state.
- [The mesh engine becomes required for a faceted run of an all-exact
  project] → yes, by construction: it is the faceted kernel. `manifold3d` is
  a framework dependency; the conditional-dependency contract (ADR-052) is
  about the exact run, which is unchanged.

## Migration Plan

Nothing migrates: the default run is the current run. A developer opting in
adds `SOLID_TEST_KERNEL=faceted` to the project's `.env`. Rolling back is
deleting the line.

## Open Questions

- A per-test or per-assertion exact override (`@testing_exact`, or
  `exact=True` on an assertion) for a suite that is mostly decidable on
  meshes but has one sub-tessellation fit. Deferred until a project produces
  the case; the v8 root suite did not.
- Whether the shop floor's `solid_test` tool should expose the kernel to the
  machinist (an exact run before a commit, a faceted one while iterating).
  A shop change, decided in the shop repository.
