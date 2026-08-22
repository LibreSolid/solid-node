## 1. Red first: prove the miss natively

- [x] 1.1 Add a coarse-filesystem test fixture (`tests/utils.py` or a new
      `tests/coarse_fs.py`) that patches **only** `os.utime`: resolve the
      requested value to nanoseconds the way CPython does (floor, for the
      float form; verbatim, for the `ns=` form), truncate to whole
      milliseconds, delegate to the real `os.utime` with that value. Reads
      stay unpatched. Provide a helper that stamps a file to a given
      whole-millisecond mtime.
- [x] 1.2 Assert the fixture's own premise: the pinned stamp
      `1787402869.540` loses a millisecond through the float form
      (`…539999961 ns` → `539 ms`) and is a fixed point through the `ns=`
      form. A platform whose conversion changed must fail here, loudly, as
      a broken premise rather than pass a test that proves nothing.
- [x] 1.3 Red: build a faceted rigid leaf under the fixture with
      whole-millisecond sub-second source mtimes, build again with no edit,
      and assert the artifacts report current and nothing is rewritten.
      Confirm it fails on today's code with the artifact one millisecond
      below `node.mtime`.
- [x] 1.4 Red: the same for an exact leaf, asserting `.stl` **and** `.brep`
      both current (ADR-044), and for an all-exact fusion whose BREP and
      STL are written synchronously (ADR-045). Confirm both fail today.
- [x] 1.5 Red: assert the safe direction under the fixture — a source
      edited after a build reports not current — and confirm it already
      passes today, so the fix cannot be credited with it.
- [x] 1.6 Record the observed red output (which artifact, requested vs
      stored nanoseconds) in the change record for the implementation
      commit.
      **Red, before any source change: 4 failed / 7 passed.**

      ```
      FAILED test_exact_leaf_caches_on_a_millisecond_filesystem
        AssertionError: ...ExactLeaf-d20b313b0496.stl is not current:
        it carries 1787402869539000000 ns and the node reports
        1787402869.54 (1787402869539999961 ns as a float)
      FAILED test_an_unchanged_exact_leaf_is_not_rebuilt
        render() ran for a leaf whose artifacts were already on disk
        and already current
      FAILED test_exact_fusion_caches_both_artifacts
      FAILED test_faceted_leaf_caches_on_a_millisecond_filesystem
        build_stls() did not converge in 3 passes: every artifact
        reported stale immediately after being written, so the loop
        would spin forever
      ```

      Passing before the fix, as designed: all four emulator-premise
      tests, both safe-direction guards, and native exact equality.
      After the fix: 11 passed.

      The non-termination is new information the spike did not have --
      it measured freshness directly rather than driving a faceted build
      loop. It is the same defect and the same fix, so it does not
      contradict the ratified design; it raises its severity from lost
      caching to a build that never finishes. Verified separately in a
      bounded harness: six consecutive OpenSCAD renders of one node,
      each immediately stale.

## 2. Carry the stamp as integer nanoseconds

- [x] 2.1 Add `AbstractBaseNode.mtime_ns` returning
      `max(os.stat(p).st_mtime_ns for p in self.files)`, and redefine
      `mtime` as `mtime_ns / 1e9` so the two cannot disagree about which
      file won the `max`. `mtime` keeps its float type and its published
      meaning (`core/serializer.py:36` writes it into `viewer.json`).
- [x] 2.2 Move `_up_to_date` (`node/base.py:693`) to
      `os.stat(path).st_mtime_ns == self.mtime_ns`, keeping the existence
      check and its exception behavior. This is the only freshness
      predicate; all eleven call sites keep their shape.
- [x] 2.3 Move `_atomic_write_text` (`node/base.py:25`) to
      `os.utime(temporary, ns=(…, mtime_ns))` and pass `self.mtime_ns` from
      `generate_scad` (`base.py:518`).
- [x] 2.4 Move `StlRenderStart` to carry and stamp nanoseconds
      (`base.py:712`/`716`), with `base.py:581` passing `self.mtime_ns`.
      Keep the log lines readable.
- [x] 2.5 Move `exact._atomic_export`, `write_brep`, and `write_stl`
      (`exact.py:81`–`111`) to nanoseconds, and their callers
      `node/exact_leaf.py:58,60` and `node/fusion.py:67,68`.
- [x] 2.6 Move `JScadNode.generate_stl`'s back-date
      (`node/adapters/jscad.py:57`) to nanoseconds.
- [x] 2.7 Decide and record the disposition of
      `core/builder.py:230`/`243`, which compares a loaded source mtime
      against the current one. It is a source-to-source comparison with no
      `utime` round trip, so it is not affected; move it to `mtime_ns` only
      if that is a coherence win, and say which was chosen and why.

## 3. Green, and no native regression

- [x] 3.1 Run the tests from batch 1 green.
- [x] 3.2 Review the `(path, mtime)` caches — `cached_base_mesh`
      (`node/base.py:52`), `exact.cached_shape`, `sources._import_cache`,
      `core/pieces.py:46`, the Manifold cache at `test.py:55` — and confirm
      none is a freshness decision. Record the finding; change nothing
      unless a real defect is found, and if one is, bring it back to the
      pilot rather than widening scope here.
      **Reviewed, all five unchanged.** Each reads a file's own mtime and
      keys on it, evicting stale entries for the same path: a comparison
      of a file against itself on one filesystem, with no `os.utime` round
      trip in between. No defect found.
- [x] 3.3 Run the full framework suite. `tests/test_source_set.py`,
      `tests/test_exact_geometry.py`, `tests/test_build123d_adapter.py`,
      `tests/test_scad_stl.py`, `tests/test_build_publication.py`,
      `tests/test_builder_lifecycle.py` and `tests/test_manifold_cache.py`
      touch currency directly and must stay green unchanged.
- [x] 3.4 Build a representative real project (v8-engine or an
      `examples/` project) twice on ext4 and confirm the second build
      reports everything current — exact-equality freshness on a normal
      filesystem is unchanged — and that a single edit still invalidates
      exactly its dependants.
- [x] 3.5 Confirm the one accepted migration cost: a build directory
      stamped by the previous float back-date rebuilds once, then reports
      current.

## 4. Records

- [x] 4.1 Inspect whether the implemented design carries a consequential
      architecture decision. If it does, extract one ADR amending ADR-006
      (equality preserved; its numeric representation fixed), add it to
      `docs/adrs/NODE/` and `docs/adrs/README.md`, and name the originating
      provenance in it: `browser-engine` change
      `prove-solid-node-runs-in-browser`, upstream finding 1,
      `evidence/groundwork.md`, the 13/25 probe, solid-node 0.5.1 at
      `1c03e337` under Pyodide 314.0.5 / Emscripten 5.0.3.
- [x] 4.2 If an ADR is accepted, update `docs/architecture.md` — the
      "build artifact is the currency, mtime is its clock" commitment, the
      build-pipeline mtime-equality paragraph, and the load-bearing
      invariant "an artifact is fresh iff its mtime equals the node's max
      source mtime" — to state the nanosecond rule.
- [x] 4.3 Sync the `build-pipeline` baseline spec from the delta and
      archive the change through the supported OpenSpec workflows.
- [x] 4.4 Report to the pilot what remains unproven: MEMFS behavior under
      `os.utime(ns=…)` is inferred from the mechanism, not measured, and
      the probe that would measure it belongs to `browser-engine`. Do not
      claim the browser case fixed on this repository's evidence alone.
