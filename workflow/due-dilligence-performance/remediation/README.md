# Remediation validation evidence

## Pre-implementation framework baseline

This run validates the unchanged framework after the audit branch's rebase.
It does not replace the historical audit's tests or performance measurements.

- Source commit: 40a848d6f8939b3e0d69e45a11b514b4ebfa263f.
- Framework source tree: d1481386a91cc1fe5aa40a525c8f1f217fb922ad.
- Framework tests tree: 7c970429e4479ddc68155f68e3fd5ce8436f3415.
- Source/test diff against that commit: empty before and after the run.
- Start: 2026-09-07T18:00:40.230157+00:00, host devel.
- Interpreter: workspace .venv, Python 3.12.3.
- JUnit: [baseline-framework.xml](baseline-framework.xml).

Command, run from the performance-analysis framework worktree:

```bash
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 \
  /home/asa/devel/libresolid-studio/.venv/bin/python -m pytest -q \
  --durations=10 \
  --junitxml=workflow/due-dilligence-performance/remediation/baseline-framework.xml
```

Result: **1,639 passed, 16 skipped, 46 warnings, 302 subtests passed in
209.68 seconds**. JUnit reports 1,957 cases including subtests, zero errors
and zero failures.

The skips are 13 missing-Sphinx cases, two absent
Internal-Cycloidal-Actuator vendor STEP fixtures and one opt-in web snapshot case
requiring SOLID_NODE_WEB_SNAPSHOT_E2E=1. No live browser capture was performed.
Warnings include dependency deprecations, legacy render-time driver access,
the deprecated pairwise assertion, and test fixtures using fork in a
multi-threaded process; they were not suppressed.

The Sol proposal author and read-only proposal reviewer worked on planning
while this suite ran. No implementation or simultaneous audit benchmark ran.
This is a correctness baseline, not a controlled suite-speed comparison with
the older audited commit. Performance probes and per-package red regressions
remain pending the concrete proposal's ratification.

## Evidence preservation

The original report, probes, fixtures, JSON, XML and project-input patch under
the sibling performance/ directory remain unchanged. Future before/after
measurements belong here with their own exact input and implementation
provenance. For an uncommitted implementation candidate, record the planning
commit and a source/test diff or content hash; do not invent an implementation
commit before the framework workflow creates it.

At proposal preflight, `git diff --exit-code 40a848d -- solid_node tests
workflow/due-dilligence-performance/PERFORMANCE.md
workflow/due-dilligence-performance/performance` passed with no differences.
Running the saved `performance/verify_evidence.py` also passed: 104 successful
workers across seven sections, artifact/provenance/candidate/volume checks and
the historical JUnit counts. This checks saved evidence, not current performance.

The [historical SHA-256 inventory](historical.sha256) covers all 18 audit files
tracked at cycle base 40a848d. `sha256sum -c` passed for every entry; completion
will repeat this check without regenerating the inventory.

See [proposal preflight review](proposal-review.md) for the design safeguards
identified before ratification. The implementation review remains pending.
