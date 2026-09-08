# Full-suite build-directory isolation correction

## Finding

The integrated candidate run in `candidate-framework.log` reported seven
failures after 1,749 passes. All seven were order-dependent: the same six
representative victims passed alone, while placing one new retained-builder
test before them immediately reproduced the wrong build directory and wrong
lock failures. The red commands and outcomes are preserved in
`full-suite-isolation-red.log`.

`Builder._start()` intentionally exports its selected `SOLID_BUILD_DIR` for
renderer subprocesses. Production invokes it in a disposable builder child,
but the new retained-lifecycle structural tests invoke it directly in pytest's
long-lived interpreter. Those tests left the environment pointing at their
temporary build directory and then removed that directory. Later node tests
recreated the leaked directory. Their artifacts accumulated outside the
legacy `tests/_build` fixture, explaining both the direct path/lock failures
and the later false-current SCAD, CadQuery, and JSCAD outcomes.

This is test pollution, not a production source-generation, currency, or
builder regression.

## Correction

`tests/test_retained_builder_generation.py` now gives every test class that
runs `_start()` in-process a common fixture. It snapshots both the presence
and value of `SOLID_BUILD_DIR` and restores that exact ambient state with a
test cleanup. The builder's production environment behavior is unchanged.

## Evidence

The formerly red minimal order passed 6/6 after the correction. The complete
retained-builder module followed by all seven original victims then passed:

```text
21 passed in 39.67s
```

A whole-suite diagnostic crossed the former 73--84% failure band and ended:

```text
1756 passed, 16 skipped, 48 warnings, 353 subtests passed in 294.29s (0:04:54)
```

Its complete output is `full-suite-isolation.log`. This run is diagnostic,
not the final frozen-candidate proof: another agent's production AR-02/AR-04
correction to `solid_node/test.py` overlapped the run. The final owner will run the
authoritative integrated suite after every writer has stopped.

Candidate evidence identities at handoff:

```text
79274fc8339bef9173a21b3aeb8fbd71d9ac699fe8efb51d7a0dbb5d4a6f7347  tests/test_retained_builder_generation.py
2a3db1c7ec58761854ec5a5ff67511b5d72af978b91319d4680749d6e39d2d7f  workflow/due-dilligence-performance/remediation/full-suite-isolation.log
```
