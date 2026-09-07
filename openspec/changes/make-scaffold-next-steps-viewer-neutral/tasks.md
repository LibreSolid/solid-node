## 1. Regression proof

- [ ] 1.1 Capture successful `New.handle()` output and require the normalized
  target path, `cd` command, and `solid develop` command.
- [ ] 1.2 Reproduce that the output currently claims
  `http://localhost:8000` regardless of viewer availability or configured
  port.

## 2. Viewer-neutral guidance

- [ ] 2.1 Remove the unconditional browser endpoint from the scaffold success
  message without loading viewer or project configuration.
- [ ] 2.2 Preserve scaffold content, identifier normalization, overwrite
  refusal, and offline operation.

## 3. Completion

- [ ] 3.1 Run focused new-command, CLI, and scaffold acceptance coverage.
- [ ] 3.2 Run the complete framework suite and strict OpenSpec validation.
- [ ] 3.3 Update the changelog and due-diligence records, mark C04 complete,
  and leave V01 explicitly open as the only remaining follow-up.
- [ ] 3.4 Synchronize and archive
  `make-scaffold-next-steps-viewer-neutral`; assess the ADR disposition after
  final evidence.
- [ ] 3.5 Commit the completed implementation as the second C04 commit and
  leave the branch clean and unmerged.
