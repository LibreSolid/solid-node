## 1. Red tests on a shared-file project

- [ ] 1.1 Add a scratch-project fixture, on the pattern of
      `tests/test_content_verified_currency.py`, whose one `parts.py` defines
      two exact leaves and a fusion of them, with a render trace, beside a
      module of shared dimensions; the root assembly names them.
- [ ] 1.2 Red: after a full build, editing one leaf's class body re-derives
      that leaf and the fusion and restamps the other leaf without rendering
      it.
- [ ] 1.3 Guard: editing a module-level constant or helper in `parts.py`
      re-derives every node in it.
- [ ] 1.4 Guard: a leaf that reaches its sibling — as a base class, through a
      module-level helper that names it, and by its name as a string — is
      re-derived when the sibling's body is edited.
- [ ] 1.5 Guard: a single-class file's digest entry equals the sha256 of its
      bytes, so `source_digest` for the existing currency fixture is unchanged
      byte for byte and its recorded sidecars still match.
- [ ] 1.6 Guard: the fast path reads no source — the existing test stays green
      unchanged.
- [ ] 1.7 Guard: a `parts.py` whose sidecars carry whole-file digests
      rebuilds its nodes once after being touched, then reports current.

## 2. The scope beside the file set

- [ ] 2.1 A node records `scope = {realpath(src): {ClassName}}` for a Python
      source when it is constructed, beside `self.files`.
- [ ] 2.2 `InternalNode.as_scad` unions each child's scope where it unions
      `child.files`.
- [ ] 2.3 `node.source_digest` passes the scope to `currency.source_digest`.

## 3. Retained text

- [ ] 3.1 Extend the loaded-module index in `node/sources.py` (ADR-058) to
      answer the module name for a real path, and expose a way to name the
      node classes a file defines from the loader's `_defined_classes`.
- [ ] 3.2 One cached analysis per `(path, mtime_ns, size)`: the top-level
      node-class spans (first decorator line through `end_lineno`) and, per
      top-level statement, the `Name` ids and string constants it contains.
- [ ] 3.3 `retained_text(path, keep)`: remove the spans of node classes not in
      `keep`, then put back any removed class the retained statements refer
      to, to a fixpoint; whole file when the module or a class cannot be
      identified or the file does not parse.
- [ ] 3.4 `currency.source_digest(files, root, scope)` digests a scoped file's
      retained text and every other file's bytes, keeping the entry format;
      cache the retained digest on the file key plus the frozen retained set.

## 4. Verification

- [ ] 4.1 Turn every red and guard test from group 1 green.
- [ ] 4.2 Full framework suite.
- [ ] 4.3 On a real project laid out one node per file (v8-engine), confirm a
      settled rebuild re-derives nothing and every existing sidecar still
      matches; then move two of its leaves into one file and confirm editing
      one re-derives only it and its ancestors.
- [ ] 4.4 Confirm `solid develop` still watches the same file set.

## 5. Records

- [ ] 5.1 ADR-069 in `docs/adrs/NODE/`: node-scoped content currency; amends
      ADR-060 and ADR-033, withdraws the one-node-per-file driver, names the
      bare-path ambiguity as a node-reference property owned by `cli`/ADR-024.
- [ ] 5.2 Update `docs/adrs/README.md` and the node-model summary in
      `docs/architecture.md`.
- [ ] 5.3 Changelog entry; sync the `build-pipeline` spec; archive the change.
