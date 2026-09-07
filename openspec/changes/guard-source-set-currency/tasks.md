## 1. Regression proof

- [ ] 1.1 Add a currency-fixture regression in which an imported helper
  changes below an unchanged future-dated maximum source mtime, and capture the
  stale-artifact failure before production changes.
- [ ] 1.2 Add a same-size content rewrite with restored mtime, legacy
  digest-only sidecar upgrade, malformed-record, and settled no-content-read
  regressions.
- [ ] 1.3 Exercise the public CLI probe and require the second build to publish
  geometry derived from the changed helper.

## 2. Source-state currency

- [ ] 2.1 Implement deterministic source-set metadata fingerprints and a
  backward-compatible versioned `.sources` record.
- [ ] 2.2 Require artifact timestamp and fingerprint equality on the
  metadata-only path; use the existing scoped digest fallback and refresh the
  complete record after a verified match.
- [ ] 2.3 Pass complete source records through every SCAD, STL, BREP, DXF,
  flexible snapshot, imported-mesh, and JSCAD publication path while preserving
  atomic publication and sweep ownership.
- [ ] 2.4 Run focused currency, coarse-filesystem, scoped-currency, and adapter
  tests and confirm the settled path does not read source contents.

## 3. Completion

- [ ] 3.1 Run the saved F05 probe, complete framework suite, and strict OpenSpec
  validation.
- [ ] 3.2 Update the changelog and due-diligence records, mark F05 complete in
  `PROGRESS.md`, and identify F06 as next.
- [ ] 3.3 Extract the implemented currency decision into an ADR, update the ADR
  index and architecture synthesis, synchronize and archive
  `guard-source-set-currency`.
- [ ] 3.4 Commit the completed implementation as the second F05 commit, then
  require a clean worktree and exactly two-commit ancestry from the F04 content
  commit `c10f5fc`.
