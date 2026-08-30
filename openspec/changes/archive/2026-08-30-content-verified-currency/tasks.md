## 1. Baseline and red tests

- [x] 1.1 Record the baseline: on a real multi-part project, time a settled
      rebuild and a rebuild after every source mtime is rewritten with no
      content change.
- [x] 1.2 Red: rewriting every source mtime with no byte changed re-derives no
      geometry, restamps every artifact, and leaves the published document
      unchanged.
- [x] 1.3 Guard: a source rewritten with *different* content still rebuilds and
      the fallback does not report it current.
- [x] 1.4 Guard: when mtime equality succeeds, no source file is read for a
      digest — the fast path is untouched.
- [x] 1.5 Guard: an artifact with no recorded digest rebuilds as today and
      gains one when written.
- [x] 1.6 Guard: for an exact node the `.stl` and `.brep` restamp together.

## 2. Recording the digest

- [x] 2.1 Compute the digest over `node.files` as a sorted sequence of
      (project-relative path, sha256 of bytes).
- [x] 2.2 Record it wherever the artifact is stamped — `_atomic_write_text`,
      `_atomic_write_bytes`, and `StlRenderStart.done()` — so artifact and
      digest are written together or not at all.
- [x] 2.3 Store it as a sidecar inside the build directory, never named by
      `viewer.json`.

## 3. The fallback

- [x] 3.1 In `_up_to_date`, consult the digest only when mtime equality fails.
- [x] 3.2 On a match, restamp the artifact to the current `node.mtime` and
      report current; on mismatch, missing record, or unreadable source, report
      not current.
- [x] 3.3 Do not loop when the restamp cannot achieve equality on a coarse
      filesystem: report current for this build on the strength of the digest.
- [x] 3.4 Confirm the callers behave — `generate_stl`,
      `_render_can_be_skipped`, and `Builder._artifacts_are_current` for both
      `stl_file` and `brep_file`.

## 4. The sweep

- [x] 4.1 Keep the sidecar of an artifact the sweep keeps, and drop the sidecar
      of an artifact it removes.
- [x] 4.2 Test that the fallback still fires *after* a publication has swept,
      since a sweep that quietly deletes sidecars leaves everything working and
      the optimisation permanently off.

## 5. Verification

- [x] 5.1 Turn every red and guard test from group 1 green.
- [x] 5.2 Full framework suite.
- [x] 5.3 On a real project: rebuild after `touch`ing every source and confirm
      no geometry is re-derived and every published artifact is byte-identical
      by sha256.
- [x] 5.4 Confirm a genuine edit still rebuilds exactly the affected subtree.
- [x] 5.5 Re-measure 1.1 and record before/after.

## Notes for the implementation record

**2.2 — the stamping sites are more than three.** The three named here are
where `os.utime` lives in `node/base.py`, but an exact node's `.stl`, `.brep`
and `.dxf` are stamped in `solid_node/exact.py::_atomic_export`, and an
`StlNode`'s mesh in `node/adapters/stl.py::_write_binary_stl`, and a
`JScadNode`'s output in place after its renderer exits. The requirement says
"wherever the artifact is stamped", and exact nodes are the ones this change
exists for, so all of them record. (`StlRenderStart.done()` is spelled
`finish()` in the code.)

**1.2 — "the published document is unchanged" cannot mean byte-identical.**
`viewer.json` publishes each node's source `mtime`, and a pure timestamp
rewrite genuinely moves it; the document has never been stable across one, with
or without this change. It is tested as identical apart from those recorded
mtimes: same tree, same names, same artifacts, every artifact byte-identical.

**1.3 — four existing guards asserted the old behaviour.**
`test_editing_an_imported_module_invalidates_the_artifact`,
`test_editing_the_mesh_invalidates_the_artifact`,
`test_editing_the_wrapper_invalidates_the_artifact` and the two coarse-
filesystem edit guards all said "edited" and only moved a timestamp. They now
change bytes, which is what they always meant, and each one goes red when the
digest comparison is mutated to always match.

**Measured, on the same 22-part CadQuery project as the proposal**
(`dutch-windmill-5`, copied to /tmp with `cp -a`):

| | before | after |
| --- | ---: | ---: |
| cold build | 35.40 s | 35.58 s |
| settled rebuild | 6.12 s | 6.03 s |
| rebuild after every source mtime is rewritten | 35.70 s | **5.83 s** |
| build of a copy whose every timestamp is new | — | 5.92 s |
| rebuild after one leaf is genuinely edited | — | 6.27 s |

All 72 published artifacts byte-identical by sha256 across the timestamp
rewrite; after the real edit exactly the four artifacts of the two edited
`LockingPin` instances changed and nothing else.
