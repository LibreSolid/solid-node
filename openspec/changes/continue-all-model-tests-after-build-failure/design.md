## Context

`Test.select_all()` already converts reference-resolution errors into
selection records which `Test.handle()` counts and skips. Once a reference has
resolved, however, `build_node()` can terminate through `self.fail()` during
load or can raise during keyframe binding, render, assembly, or STL creation.
The selection loop catches only `StopTestRun`, so either path escapes the
whole command before the next declared model or the final report.

Ordinary test-method failures already increment the shared counters and use
`StopTestRun` only when requested. Model preparation needs the same outer-run
semantics without turning a build failure into a fabricated test method.

## Goals / Non-Goals

**Goals:**

- Establish one failure boundary around every all-model selection's load,
  construction, initial keyframe, render, assembly, and artifact generation.
- Count a failed model once in the aggregate test totals and name the declared
  model in its diagnostic.
- Continue from that boundary when `--failfast` is false and stop from it when
  `--failfast` is true.
- Always print the one-run summary and return a nonzero status when any model
  preparation failed.
- Preserve current behavior for a single selected model and for failures
  raised by test methods.

**Non-Goals:**

- Retry a failed model or run its tests against a partially built node.
- Change the build pipeline, `errors.json`, model status, or artifact
  publication behavior.
- Treat interpreter-control exceptions such as `KeyboardInterrupt` as model
  failures.
- Redesign companion-test discovery or its setup and teardown lifecycle.

## Decisions

### D1: Catch failures at the all-model selection boundary

The runner will prepare a selection inside a model-aware boundary used only
when walking named models. A normal exception from load, construction,
keyframe binding, render, assembly, or artifact generation becomes that
model's failure. The next selection starts through the existing anchor logic,
so no partially prepared node or test case is reused.

Catching only around `render()` was rejected because constructor, assembly,
and artifact failures have the same contract and currently escape in the same
way. Catching around the entire command was rejected because it cannot resume
at the next declared model.

### D2: Reuse one model-failure accounting path

Reference-resolution failures and preparation failures will both increment
`num_tests` and `num_failed` exactly once and emit a diagnostic prefixed with
the declared model name. No tests are loaded or run for the failed model.
This preserves the existing interpretation established by unresolved models:
a declared model that cannot reach its tests occupies one failed entry in the
aggregate report.

Printing only the underlying exception was rejected because users could not
reliably associate it with one model in a multi-model project. Counting every
failed preparation stage was rejected because stages after the first failure
never ran and do not represent independent tests.

### D3: Route failfast through the existing run-control signal

After recording the model failure, the common helper will raise
`StopTestRun` only when `--failfast` is set. `handle()` already catches this
signal outside the selection loop and prints the aggregate report, so both
ordinary test failures and model failures retain one exit/report path.

Calling `self.fail()` for an all-model preparation failure was rejected
because its `SystemExit` bypasses the report. Suppressing the report under
`--failfast` was rejected because current test-method failfast behavior still
reports the work completed before stopping.

### D4: Prove every preparation family and the public continuation path

Focused regressions will force failures during construction/load, render,
assembly, and artifact generation and require one failed count in each case.
Non-failfast coverage will prove a later model's test runs; failfast coverage
will prove it does not. The saved subprocess probe supplies the real CLI proof
for the render case and must change from `second_ran: false` to true while
retaining exit status 1.

## Risks / Trade-offs

- **A concise model diagnostic can omit debugging context.** The diagnostic
  will retain the exception type and message while adding the model name;
  focused tests pin the useful identity and cause rather than terminal color
  or a full traceback layout.
- **A failed build may have partially changed artifacts.** This change does
  not alter build atomicity; existing build and artifact contracts remain
  responsible for their own publication boundaries.
- **Broad exception handling could swallow operator interrupts.** The boundary
  catches normal `Exception` failures only, with runner control flow handled
  separately.

## Migration Plan

No migration is required. The correction changes only runtime control flow
and reporting for `solid test --all`.

## Open Questions

None.
