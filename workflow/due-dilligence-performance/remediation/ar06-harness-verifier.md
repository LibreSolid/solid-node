# AR-06 measurement-verifier correction evidence

Recorded: 2026-09-07T21:04:29Z

Scope: measurement harness only.  No framework production or product test file
was changed by this correction.  No formal performance workload was run and no
current-candidate identity was materialized.

## Red reproduction

The following focused command was run after adding three negative tests and
before hardening `verify_section()`:

```text
/home/asa/devel/libresolid-studio/.venv/bin/python workflow/due-dilligence-performance/remediation/test_current_performance_harness.py WorkerValidationTest.test_unchanged_build_rejects_byte_identical_file_churn WorkerValidationTest.test_placement_rejects_an_early_over_cap_sample WorkerValidationTest.test_placement_rejects_a_zero_reuse_working_set -v
```

Result: **3 failed**.  Each failure was `ValueError not raised`, independently
reproducing the three verifier gaps: unchanged artifact churn was accepted, an
early `513 > 512` cache sample was accepted, and a twelve-construction/zero-hit
working set was accepted.

## Correction and local green

The verifier now requires:

- empty artifact churn on explicitly unchanged build/project repeats and on
  warmed actual-Builder detail runs;
- zero actual SCAD publish/restamp operations on those warmed detail runs,
  without applying that rule to first settle or metadata refresh;
- bounded placement mode and the exact sample series 1000, 4000, 8000;
- every placement sample at or below the recorded cache cap; and
- the fixed twelve-request working set to report three constructions, nine
  hits, internally coherent totals, and a post-run cache no larger than the
  cap.

The same focused command then passed **3/3**.  The complete lightweight harness
suite passed **16/16** in 0.281 seconds, and all five harness files passed
`python -m py_compile`.  Both immutable SHA inventories continued to verify.

## Independent green

The independent xhigh implementation reviewer (`/root/implementation_adversarial`)
reported a combined re-run covering the AR-05 regression and the complete
harness suite: **17 passed, 14 subtests**.  The reviewer described the AR-06
correction as statically sound.  Formal current-candidate measurements remain
blocked on the root agent's explicit GO.

## Corrected harness hashes

```text
30f464150fe278622381fea67f647cbb6783e8d5ea19ace3c88bb4dfd1e6d360  current_performance_common.py
19926bf2aba20dd6b3c228471d838a31babed86de68757f04d97c0f9d26d862c  current_performance_worker.py
3562f15fdd1473842fa98aaf7b6aaea96f17298d063243a75d562c4cc071ce68  run_current_performance_probe.py
b5bdfc3abfebe0fe995768cc600050830dfa07ef397311fb76c0bc9482eb7859  verify_current_performance_evidence.py
b2f559f34bdd1dd1773141e00a4eece4e0236c107a4ba1158119d18c4097b855  test_current_performance_harness.py
```
