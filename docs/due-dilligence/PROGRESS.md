# Due-diligence remediation progress

This checklist is the source of truth for remediation status. Work proceeds
one item at a time according to the discipline in [README.md](README.md#remediation-discipline).
Unless the pilot selects another item, take the first unchecked finding in
the order below.

## Reproduced bugs

- [x] [F01 — Failed renderer output is committed as successful geometry](README.md#f01--failed-renderer-output-is-committed-as-successful-geometry)
  — planned in `7dee1a7`, fixed in `24a65da`.
- [ ] [F02 — Build cleanup deletes files it does not own](README.md#f02--build-cleanup-deletes-files-it-does-not-own)
- [ ] [F03 — Export paths can escape the output directory](README.md#f03--export-paths-can-escape-the-output-directory)
- [ ] [F04 — Exact geometry bypasses build mutual exclusion](README.md#f04--exact-geometry-bypasses-build-mutual-exclusion)
- [ ] [F05 — Aggregate timestamp equality hides changed source contents](README.md#f05--aggregate-timestamp-equality-hides-changed-source-contents)
- [ ] [F06 — Changes to non-Python source files never trigger reload](README.md#f06--changes-to-non-python-source-files-never-trigger-reload)
- [ ] [F07 — Successful rebuilds can leave `solid models` reporting failure](README.md#f07--successful-rebuilds-can-leave-solid-models-reporting-failure)
- [ ] [F08 — `solid new 3d-printer` creates an unusable project](README.md#f08--solid-new-3d-printer-creates-an-unusable-project)
- [ ] [F09 — Multi-model tests stop on build failures despite the continuation contract](README.md#f09--multi-model-tests-stop-on-build-failures-despite-the-continuation-contract)
- [ ] [F10 — Zero repeated children break the declarative render contract](README.md#f10--zero-repeated-children-break-the-declarative-render-contract)
- [ ] [F11 — Invalid simulation time inputs can silently bypass checks](README.md#f11--invalid-simulation-time-inputs-can-silently-bypass-checks)

## Documentation and process inconsistencies

- [ ] [C01 — Assertion documentation promises more than vertex sampling proves](README.md#c01--assertion-documentation-promises-more-than-vertex-sampling-proves)
- [ ] [C02 — Browser capture instructions omit the required opt-in](README.md#c02--browser-capture-instructions-omit-the-required-opt-in)
- [ ] [C03 — The README overstates viewer process isolation](README.md#c03--the-readme-overstates-viewer-process-isolation)

Next by priority and order: **F02**.
