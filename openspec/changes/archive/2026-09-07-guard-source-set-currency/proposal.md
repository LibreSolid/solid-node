## Why

Due-diligence finding F05 reproduced stale geometry after an imported helper
changed while a future-dated node source kept the same aggregate maximum mtime.
The current equality fast path observes only that maximum and bypasses the
recorded content digest, so it can certify sources different from those that
produced the artifact.

## What Changes

- Record a project-relative metadata fingerprint of every tracked source
  contributor beside each artifact, together with its existing content digest.
- Require an aggregate-mtime cache hit to match the recorded source-set
  fingerprint before it can report the artifact current without content
  verification.
- Fall back to the existing node-scoped content digest whenever the fingerprint
  differs or is absent, preserving no-op timestamp rewrite and sibling-class
  behavior while upgrading legacy digest-only records in place.
- Define the supported preserved-timestamp boundary: file size and filesystem
  change identity participate in the fingerprint, so ordinary rewrites remain
  visible even when mtime is restored; a filesystem that exposes no metadata
  change for changed bytes cannot provide a metadata-only fast path.
- Add regressions for an older dependency changing beneath an unchanged maximum
  mtime, restored-mtime same-size edits, legacy sidecar upgrade, and the
  no-source-read settled path.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `build-pipeline`: strengthen artifact currency from aggregate timestamp
  equality to equality plus the recorded state of every tracked contributor.

## Impact

- `solid_node/currency.py`: source-set fingerprinting and a backward-compatible
  structured sidecar record.
- `solid_node/node/base.py` and artifact-producing adapters: provide and consult
  the source-set fingerprint at publication and currency checks.
- Currency and adapter tests: prove invalidation, compatibility, fast-path cost,
  and publication behavior.
- ADR-060/071 and the architecture synthesis require an amended decision after
  implementation confirms the final currency design.
