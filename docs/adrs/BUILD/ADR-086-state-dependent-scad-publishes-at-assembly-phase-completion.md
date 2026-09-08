# ADR-086: State-Dependent SCAD Publishes at Assembly Phase Completion

**Status:** Accepted
**Date:** 2026-09-07
**Change:** `bound-framework-performance-costs`
**Extends:**
- [ADR-038: Per-Artifact Atomic Build Publication](ADR-038-per-artifact-atomic-build-publication.md)
**Depends on:**
- [ADR-084: One Fresh Builder per Sealed Source Generation](ADR-084-one-fresh-builder-per-sealed-source-generation.md)
- [ADR-081: Per-Contributor Metadata Guards Aggregate-Mtime Currency](../NODE/ADR-081-per-contributor-metadata-guards-aggregate-mtime-currency.md)
- [ADR-003: Rigid vs Non-Rigid Node Distinction](../NODE/ADR-003-rigid-vs-non-rigid-node-distinction.md)
- [ADR-057: The Flexible Leaf, Whose Geometry Travels as a Spec](../NODE/ADR-057-the-flexible-leaf-and-spec-carried-geometry.md)

## Context and Problem Statement

The formal performance candidate exposed AR-07 on disposable project copies.
Every Abacus run atomically replaced byte-identical `Column` SCAD and currency
records; every V8 run did the same for `CylinderUnit` and `ValveMotion`.
Desired bytes and mtimes were stable, but inode and ctime changed on every
build. Metamaquina2 remained clean, and a finite third Abacus diagnostic
repeated the same churn.

The affected nodes are non-rigid assemblies. Several instances share one
parameter-derived artifact path and source/currency identity, while their
state- or binding-dependent descendants can make the instances' intermediate
SCAD differ. Immediate per-instance atomic publication correctly writes each
value and leaves the historical last occurrence on disk, but oscillates the
path before restoring the same final bytes.

The rigid generation cache cannot simply admit every non-flexible node.
Source/currency identity does not include all legacy descendant binding state,
so first-instance reuse could freeze the wrong assembly composition. The
cache also remembered a set of all `(path, identity)` values seen: after A then
B reached one path, a later A looked reusable even though B was current.

## Decision Drivers

- Every instance must still render and contribute its own in-memory assembly
  composition and placement.
- The final SCAD bytes must preserve historical last-occurrence behavior.
- Stable repeated builds must not replace byte-identical SCAD or currency
  records merely because intermediate instances differ.
- Flexible binding publication and direct calls without an owning phase must
  remain immediate.
- Source races, F04 lock ownership, F05 currency and ADR-038 atomicity must not
  weaken.

## Considered Options

1. **Publish the final state-dependent value at assembly phase completion**
   (chosen)
2. Admit every non-flexible node to immediate generation reuse
3. Keep immediate per-instance publication and accept path oscillation
4. Invent a complete legacy binding/spec identity and new artifact paths
5. Retain pending values beyond the phase or source generation

## Decision Outcome

Every affected non-rigid instance still executes `render()` and `as_scad()`,
and contributes its distinct in-memory composition. When a non-rigid,
non-flexible node generates SCAD inside the established assembly source phase,
the call immediately computes and freezes the desired text, `mtime_ns`,
node-scoped digest and source fingerprint. The phase retains one payload per
canonical artifact path. Replacing a path moves it to the end of the ordered
mapping, so flush order follows the paths' historical last occurrences.

On a clean assembly-phase exit, the generation first performs a fresh
pre-flush source check. It then snapshots and clears the ordered mapping and
passes each final payload through the existing compare-before-replace and
atomic currency publisher while the phase census and F04 project lock remain
active. A second fresh check follows the flush. The file therefore receives
the same last-wins value immediate publication historically left, but only
that final value reaches artifact comparison.

A body or pre-flush failure discards every pending value. A flush error leaves
any completed atomic replacement coherent, clears the remaining requests and
follows the existing assembly-error path. A post-flush source mismatch ends
the generation `SOURCE_CHANGED`; no viewer manifest certifies stale work, and
the next fresh process repairs any artifact whose source record is no longer
current. Logging reports actual completed publication, not discarded queued
intent.

Flexible SCAD and per-binding snapshot publication remain immediate and
uncached. A direct `generate_scad()` call outside the assembly phase is also
immediate because no phase lifetime owns it. Rigid base SCAD retains immediate
generation-local reuse, but its cache maps each canonical path to the full
identity currently published there. A→B→A therefore performs all three
required publications; an incomplete identity invalidates rather than reuses
the entry.

ADR-038's per-file temporary-write and atomic-replace rules, manifest-last
publication and tolerance of a partial mixed model after failure remain
unchanged. This decision adds the eligibility boundary for state-dependent
assembly SCAD; it does not restore complete-set publication.

## Consequences

- Repeated non-rigid instances settle without same-input inode/ctime churn and
  retain exactly their historical final SCAD bytes.
- Intermediate non-rigid assembly SCAD values are no longer externally visible
  while assembly is in progress. Each instance's actual in-memory composition
  remains available to its parent and final document.
- One immutable final text payload per distinct non-rigid path is retained for
  the duration of one assembly phase, then cleared on every exit. This is not a
  global or persistent cache.
- The phase performs an additional fresh check before and after its flush.
- A mid-flush failure may leave a prefix of complete new artifacts, as
  ADR-038 already permits, but never a torn file or a manifest naming stale
  work.
- Flexible and direct callers keep their existing publication timing.

## References

- `solid_node/source_generation.py`
- `solid_node/node/base.py`
- `tests/test_generation_dedup.py`
- `workflow/due-dilligence-performance/remediation/ar07.md`
- [Archived change](../../../openspec/changes/archive/2026-09-08-bound-framework-performance-costs/)
