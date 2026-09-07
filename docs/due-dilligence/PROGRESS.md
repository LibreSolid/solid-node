# Due-diligence remediation progress

This checklist is the source of truth for remediation status. Work proceeds
one item at a time according to the discipline in [README.md](README.md#remediation-discipline).
Unless the pilot selects another item, take the first unchecked finding in
the order below.

## Reproduced bugs

- [x] [F01 — Failed renderer output is committed as successful geometry](README.md#f01--failed-renderer-output-is-committed-as-successful-geometry)
  — planned in `7dee1a7`, fixed in `24a65da`.
- [x] [F02 — Build cleanup deletes files it does not own](README.md#f02--build-cleanup-deletes-files-it-does-not-own)
  — OpenSpec change `preserve-unowned-build-siblings`.
- [x] [F03 — Export paths can escape the output directory](README.md#f03--export-paths-can-escape-the-output-directory)
  — OpenSpec change `confine-export-models`.
- [x] [F04 — Exact geometry bypasses build mutual exclusion](README.md#f04--exact-geometry-bypasses-build-mutual-exclusion)
  — OpenSpec change `lock-artifact-assembly`.
- [x] [F05 — Aggregate timestamp equality hides changed source contents](README.md#f05--aggregate-timestamp-equality-hides-changed-source-contents)
  — OpenSpec change `guard-source-set-currency`; ADR-081.
- [x] [F06 — Changes to non-Python source files never trigger reload](README.md#f06--changes-to-non-python-source-files-never-trigger-reload)
  — OpenSpec change `watch-all-tracked-sources`.
- [x] [F07 — Successful rebuilds can leave `solid models` reporting failure](README.md#f07--successful-rebuilds-can-leave-solid-models-reporting-failure)
  — OpenSpec change `clear-recovered-build-errors`.
- [x] [F08 — `solid new 3d-printer` creates an unusable project](README.md#f08--solid-new-3d-printer-creates-an-unusable-project)
  — OpenSpec change `normalize-scaffold-identifiers`.
- [x] [F09 — Multi-model tests stop on build failures despite the continuation contract](README.md#f09--multi-model-tests-stop-on-build-failures-despite-the-continuation-contract)
  — OpenSpec change `continue-all-model-tests-after-build-failure`.
- [x] [F10 — Zero repeated children break the declarative render contract](README.md#f10--zero-repeated-children-break-the-declarative-render-contract)
  — OpenSpec change `support-empty-assemblies`; ADR-082.
- [x] [F11 — Invalid simulation time inputs can silently bypass checks](README.md#f11--invalid-simulation-time-inputs-can-silently-bypass-checks)
  — OpenSpec change `validate-simulation-time-boundaries`; ADR-083.

## Documentation and process inconsistencies

- [x] [C01 — Assertion documentation promises more than vertex sampling proves](README.md#c01--assertion-documentation-promises-more-than-vertex-sampling-proves)
  — corrected the assertion descriptions and documented their sampling limit.
- [x] [C02 — Browser capture instructions omit the required opt-in](README.md#c02--browser-capture-instructions-omit-the-required-opt-in)
  — documented the opt-in command and added a required real-capture CI job.
- [x] [C03 — The README overstates viewer process isolation](README.md#c03--the-readme-overstates-viewer-process-isolation)
  — aligned README and contributor wording with the entry-point boundary.
- [ ] **C04 — Audit scaffolded viewer next-step guidance.** The generated
  success message hard-codes `http://localhost:8000` without considering the
  configured port or whether the optional browser viewer is available. This
  is the separate review lead retained from F08.

## Cross-repository follow-ups

- [ ] **V01 — Audit the independent viewer's capture behavior when its staged
  input disappears unexpectedly.** Determine whether `solid-node-viewer`
  should add its own diagnostic or recovery behavior, and add viewer-owned
  regressions there if warranted. This is the viewer counterpart noted while
  resolving F02; it is deliberately outside the framework change.

Next framework finding by priority and order: **C04**.
