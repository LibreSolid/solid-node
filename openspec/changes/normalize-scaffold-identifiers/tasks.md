## 1. Regression proof

- [ ] 1.1 Add normalization-table regressions for ordinary, punctuation,
  digit-leading, Python-keyword, and punctuation-only project names.
- [ ] 1.2 Extend generated-source coverage to compile both the model and test
  modules and require their class names and manifest reference to agree.
- [ ] 1.3 Add real acceptance cases proving digit-leading and keyword projects
  build and run both scaffolded tests without edits; capture the numeric case
  failing before the implementation.
- [ ] 1.4 Run the saved numeric-scaffold CLI probe before and after the fix,
  requiring the corrected target/source and a successful first build.

## 2. Identifier normalization

- [ ] 2.1 Introduce one package/class normalization helper that preserves the
  existing punctuation and fallback rules, then prefixes leading-digit and
  keyword results with `project_`.
- [ ] 2.2 Use the final normalized pair consistently for the target, package,
  modules, test class, template substitutions, and manifest.
- [ ] 2.3 Preserve overwrite refusal and outputs for existing valid names,
  including `snowman-3` becoming `snowman_3:Snowman3`.
- [ ] 2.4 Run focused new-command, CLI, loader, build, and generated-test
  coverage plus the saved probe.

## 3. Completion

- [ ] 3.1 Run the complete framework suite and strict OpenSpec validation.
- [ ] 3.2 Update the changelog and due-diligence records, mark F08 complete in
  `PROGRESS.md`, identify F09 as next, and retain the printed browser URL as a
  separate review item.
- [ ] 3.3 Synchronize and archive `normalize-scaffold-identifiers`; record the
  ADR disposition against the existing offline scaffold decision.
- [ ] 3.4 Commit the completed implementation as the second F08 commit, then
  require a clean worktree and exactly two-commit ancestry from F07 content
  commit `f19cd3a`.
