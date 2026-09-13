## Context

Status: ratified on 2026-09-13. The pilot replied "ratify, go on" to the
complete scope and the request for implementation, fast-forward integration
into unchanged clean main, and resuming the Voron simulation.

Standalone cycle identity:

| Item | Value |
| --- | --- |
| Source repository | `/home/asa/devel/libresolid-studio/solid-node` |
| Clean base / intended integration branch | `main` at `b768bdf979552751d016dd89c2f5814693134f9a` |
| Cycle branch | `voron-faceted-contact` |
| Cycle worktree | `/home/asa/devel/libresolid-studio/solid-node/WTs/voron-faceted-contact` |
| Shop launcher | `scripts/dev-env voron-faceted-contact setup`, slot 10 |
| Originating project | `projects/3D-Printers/Voron-2`, commit `235451b` |
| Integration | Authorized after validation; not yet performed |

The Voron reproduction contains unchanged source extrusions 1262 and 1388.
`assertNoSolidInterference` fails on −9.947598300641403e−14 mm³ faceted volume;
its exact check passes. Direct CadQuery geometry reports zero intersection
solids. The separate `assertNotIntersecting` test also fails faceted, but that
is consistent with ADR-029's stricter engine-emptiness contract, not a second
positive-volume defect. The initial project diagnosis conflated them.

The baseline `test-framework` requirement and ADR-040 distinguish assembly
material interference from strict contact. Current assembly code skips only
`is_empty` or `volume == 0.0`, so a finite negative volume reaches the same
failure as a positive volume. `IntersectionStats` already records which
representation supplied a result. No new routing interface is needed.

Read authority: framework architecture synthesis, `test-framework` baseline,
ADR-029, ADR-040, ADR-073 and ADR-074. No accepted decision is superseded:
ADR-040's positive-volume assembly contract is being made explicit for the
observed negative faceted case, while ADR-029/073's strict pairwise emptiness
and run-level policy remain intact.

## Goals / Non-Goals

**Goals:** Remove the finite-negative faceted false assembly failure, keep
strict positive-volume detection, preserve raw engine evidence, and validate
the originating unchanged corner from this bench.

**Non-Goals:** Change pairwise/fit/gravity/weld assertions; normalize shared
intersection results; change exact-path behavior; solve positive faceted
slivers; repair or displace source geometry; add an epsilon, public API,
dependency, viewer behavior, or new broad-phase/cache policy. Genuine original
Voron overlaps and the moving printer remain project work.

## Decisions

### 1. Interpret the sign only at the assembly assertion

Retain the candidate result, including its existing exact/faceted provenance.
After the existing empty/zero checks, pass a finite negative result only when
the candidate was evaluated faceted. Leave non-finite results failing and
exact candidates unchanged. The scope includes mesh comparisons in mixed or
faceted assemblies during an otherwise exact run; representation, not the
flag alone, decides applicability.

This is a sign rule, not a magnitude cutoff. No positive number is small
enough to pass at zero run epsilon. Raw `is_empty`, volume, cached verdicts,
geometry and source placements are not rewritten. A passing faceted assembly
check remains a tessellation-precision result, not exact certification or
proof that arbitrary negative-volume geometry is sound.

Rejected alternatives: clamp all shared negative results to empty (changes
pairwise and fit contracts); take absolute value (turns the observed negative
result into invented positive material); add an epsilon or shift the source
(hides the issue); change both kernels speculatively (no exact negative
reproduction is in scope); treat non-finite values as clear (unsafe evidence).

### 2. Prove the boundary before changing the branch

Add regression cases beside `tests/test_assembly_integrity.py`'s existing
non-empty zero and smallest-positive tests. Inject representation-tagged
candidate results to cover empty, ±0, finite negative values, the recorded
Voron value, smallest positive, ordinary positive, NaN and both infinities.
An exact-tagged negative case must retain its previous failure. Shared-helper
tests must show that non-empty negative/zero faceted results still reach
strict pairwise and fit checks unchanged. Cover a negative candidate followed
by a positive candidate so accepting one cannot skip the rest of the assembly.

Use the real project corner as independent end-to-end evidence, not a mock
substitute or a GPL geometry fixture copied into this Apache repository.
Test the assembly assertion's result separately from the stricter pairwise
test, whose continued faceted failure is expected. Inspect metadata and engine
admission as needed without repairing inputs. Restore the old assembly branch
temporarily as a mutation and require the negative regression to fail again;
a positive-volume-skipping mutation must be caught by the positive guard.

### 3. Keep project and framework records separate

The framework wart records both the repeated-name import friction (not fixed
here) and this assembly observation. The project keeps its extraction tools,
source geometry and original-overlap inventory. After integration, correct its
diagnostic wording and test intent in the project repository, then resume
ground-up implementation. Do not demand that its deliberately strict faceted
pairwise check become green as evidence of this fix.

## Risks / Trade-offs

- A negative result does not certify geometry → retain exact final regression,
  engine admission, raw evidence and the distinction between contact and volume.
- Broad shared-helper edits could relax unrelated contracts → change only the
  assembly decision and test the strict consumers and exact provenance.
- The real kernel can change its residue with version/platform → combine
  deterministic signed-result regressions with the recorded real-project run.
- The Voron frame still has 54 positive exact scan results → do not claim this
  fix makes the frame or printer pass; resume its measured-inventory work.
- Existing exact-negative and fast-interference worktrees are independent → do
  not edit, merge, rebase or borrow changes from them.

## Migration Plan

After explicit ratification, validate and commit only the planning artifacts
and originating wart evidence as commit 1. Apply red-first in this bench;
run focused assembly, comparison-kernel, cache/broad-phase and strict-contact
regressions plus the originating project diagnostic. Review ADR disposition
after implementation: no new architectural boundary is anticipated; update
the architecture synthesis to clarify the implemented distinction if needed.
Sync the accepted delta, archive, and commit the complete implementation
record as commit 2. Integrate into unchanged clean `main` only when directed;
otherwise report divergence. No push, release or issue is authorized.

If implementation contradicts these assumptions, return the evidence to the
pilot for revision rather than broadening the fix. A later rollback is a
separate revert under pilot authority, never a destructive reset.

## Open Questions

The finite-negative faceted interpretation is ratified. At planning commit,
no framework implementation has started. Exact negative-volume anomalies,
positive sub-tessellation slivers and import-name selectors are deferred,
not silently covered by this cycle.
