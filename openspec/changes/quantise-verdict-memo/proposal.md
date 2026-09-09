## Why

The per-run verdict memo of ADR-070 keys on the exact bytes of
`inv(M1) @ M2`. A pair carried together by a parent rotation does not
produce the same bytes twice: composing the parent's matrix through
each child leaves ~1e-13 of float noise between instants, so the memo
misses the very pairs it was built for.

Measured on 3DPrintedClocks `wall_clock_02` under the exact kernel
(`workflow/warts.md`, "3DPrintedClocks wall clock 02 (2026-09-09, exact
sweep cost)"): a sweep instant costs ~19 s, essentially all of it in
`BRepAlgoAPI_Common`. Of 118 candidate pairs per instant, 30 are
rigidly carried together — the pendulum, the motion works, the weight
and its line — and re-run a boolean whose answer the memo already
holds. Only 5 pairs hit. Two sweeps of 48 and 32 instants are ~18.5 min
of a 1175 s suite; a quarter of every instant is spent re-asking
questions already answered.

The difference between those matrices is not a difference in placement.
It is the arithmetic noise of having composed the same rigid motion
twice by different routes.

## What Changes

- **The verdict key's placement term is quantised.** `_verdict_key`
  divides the relative matrix by a quantum, rounds to integer cell
  indices, and keys on those integers. Two relative placements in the
  same cell are one question; two in different cells are two, exactly
  as today.
- **The quantum is a stated property of the run**, in the same place
  ADR-073 put the kernel and the volume epsilon: policy field
  `placement_quantum`, flag `--placement-quantum MM` on `solid test`,
  environment `SOLID_TEST_PLACEMENT_QUANTUM` read through the CLI's
  `.env` rule, flag beats environment beats default. The default is
  `1e-9` mm. `0` restores the exact-bytes key ADR-070 specified — the
  memo still works, keyed on bytes. A negative or non-numeric value is
  an error naming the flag or the variable.
- **It applies under both kernels.** The memo is shared, and float
  noise is not a property of the kernel, so unlike `--volume-epsilon`
  the exact kernel accepts `--placement-quantum` rather than refusing
  it.
- **A non-default quantum is announced; the default run's output is
  byte-for-byte what it is today.** The summary line names the quantum
  only when it is not the default, beside the faceted label when both
  apply.
- **No verdict changes, and nothing is breaking.** Within a cell the
  two placements are indistinguishable at any manufacturing scale, and
  a pair that straddles a cell boundary simply misses and recomputes,
  as today.
- **One ADR amending ADR-070** records why the tolerance ADR-070
  rejected as "global and invisible" is admissible as a visible,
  overridable, removable property of the run — and that it is a
  judgement about float noise, not about material, which is why it may
  have a default where `volume_epsilon` may not.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-framework`: "An intersection verdict is computed once per run"
  — the key's placement term becomes the quantised relative placement,
  with the guarantee that a quantised hit cannot serve a wrong verdict
  and that the failure direction is a miss. "Run-level comparison
  kernel" — the run's comparison policy gains the placement quantum,
  its resolution order, its errors, and the fact that it applies under
  both kernels.
- `cli`: "Test command" — `solid test` gains `--placement-quantum MM`
  and reads `SOLID_TEST_PLACEMENT_QUANTUM`.
- `user-documentation`: "The comparison kernels are documented" — the
  testing page explains what the quantum absorbs and how it is
  selected; the CLI page lists the option and the variable.

## Impact

**Framework code.** `solid_node/test.py`: `ComparisonPolicy` gains
`placement_quantum`, declared with the default so its seven existing
two-argument constructions keep meaning what they mean;
`resolve_comparison_policy` resolves and validates it, `_verdict_key`
quantises. `solid_node/manager/test.py`: the flag,
and the summary suffix. Nothing else: `_record_key`, `_memoized`,
`_engine_intersection_stats` and `_placed_intersection` inherit the new
key through the one function they already call, and
`solid_node/exact.py`'s `placed_shape`/`_placement_cache`/
`_bounds_cache` keep keying on exact matrix bytes — quantisation is for
the verdict key alone, never for the geometry a comparison sees.

**Tests.** `tests/test_intersection_memo.py` gains the noise, boundary,
zero-quantum and signed-zero scenarios;
`tests/test_manager_test.py` (`ComparisonKernelSelectionTest`) gains
the flag, environment and error scenarios and has its policy tuples
widened.

**Docs.** `docs/testing.rst`, `docs/cli.rst`, `docs/architecture.md`
(the memo paragraph names the exact-bytes key), `docs/changelog.rst`,
`docs/adrs/TEST-FRAMEWORK/ADR-090`, `docs/adrs/README.md`,
`workflow/warts.md`.

**Projects.** Nothing changes for a project that says nothing: the
default run behaves as today except that the memo hits more often. The
originating project, 3DPrintedClocks `wall_clock_02`, is where the
cycle's evidence is measured; nothing is committed outside this
framework repository.

**Downstream.** The two remaining wall-clock-02 findings —
`broad-phase-in-the-root-frame` and `face-box-broad-phase` — are
independent of this one and are their own cycles. Parallel pair
booleans and a mesh-distance exact-negative tier stay out.
