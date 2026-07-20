## Context

`docs/contributor-briefing.md` is a framework-owned orientation document, but
it currently carries instructions that are specific to one local checkout and
to an obsolete agent workflow.  Shop lifecycle authority lives in
`solid-node-shop`; framework architecture and verification knowledge belong in
the framework repository.

## Goals / Non-Goals

**Goals:**

- Give framework contributors an accurate map of the relevant source areas.
- Explain the meta-project harness and when it supplements direct pytest.
- State durable verification and runtime facts without assuming a particular
  checkout location or assistant.

**Non-Goals:**

- Define agent, OpenSpec, worktree, commit, or publication protocol.
- Replace the architecture synthesis, ADRs, baseline specifications, or public
  contributor workflow.
- Change framework behavior or its behavioral specifications.

## Decisions

- Keep the briefing as a compact contributor reference and link readers to
  framework-owned architecture, ADR, and specification records for detail.
  This preserves one current orientation document without copying the shop
  workflow.
- Retain the meta-project explanation and adversarial fixture guidance because
  those describe how framework behavior is verified.  Express commands with
  repository-relative tools rather than a hard-coded virtualenv path.
- Describe requirements in terms of available tools and environment variables
  (`openscad`, `SOLID_BUILD_DIR`) rather than a specific developer machine.

## Risks / Trade-offs

- [A concise briefing can omit a subsystem detail.] → Link to the architecture
  synthesis, specs, and ADRs as the authoritative detailed records.
- [Relative test commands may differ by environment.] → State the intent and
  leave environment activation/runner selection to the active development
  environment rather than prescribe a local path.
