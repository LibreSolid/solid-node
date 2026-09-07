## 1. Regression Proof

- [x] 1.1 Extend build-publication tests to prove ordinary preparation and
  legacy symlink migration preserve unrelated sibling files, directories, and
  the project lock while consuming only the referenced target.
- [x] 1.2 Add a browser-staging regression proving a real staged document and
  hard-linked artifact survive overlapping build preparation.
- [x] 1.3 Run the focused tests red against the current implementation and
  retain the failure evidence.

## 2. Ownership-Bounded Preparation

- [x] 2.1 Remove prefix-based sibling deletion from `prepare_build_dir()` and
  remove its unused dependency while retaining referenced-target migration,
  directory creation, and Git exclusion.
- [x] 2.2 Add an Unreleased changelog entry and update F02's resolution note
  and remediation checklist without rewriting the original audit evidence.

## 3. Validation and Completion

- [x] 3.1 Run the focused build-publication and browser-staging tests.
- [x] 3.2 Run the saved cleanup probe, the complete framework suite, and strict
  OpenSpec validation, recording any skips or unrelated failures.
- [x] 3.3 Synchronize and archive the OpenSpec change, determine whether an ADR
  is warranted, and commit the completed implementation and records.
