## 1. Red first: prove the miss natively

- [ ] 1.1 Add a coarse-filesystem test fixture (`tests/utils.py` or a new
      `tests/coarse_fs.py`) that patches **only** `os.utime`: resolve the
      requested value to nanoseconds the way CPython does (floor, for the
      float form; verbatim, for the `ns=` form), truncate to whole
      milliseconds, delegate to the real `os.utime` with that value. Reads
      stay unpatched. Provide a helper that stamps a file to a given
      whole-millisecond mtime.
- [ ] 1.2 Assert the fixture's own premise: the pinned stamp
      `1787402869.540` loses a millisecond through the float form
      (`…539999961 ns` → `539 ms`) and is a fixed point through the `ns=`
      form. A platform whose conversion changed must fail here, loudly, as
      a broken premise rather than pass a test that proves nothing.
- [ ] 1.3 Red: build a faceted rigid leaf under the fixture with
      whole-millisecond sub-second source mtimes, build again with no edit,
      and assert the artifacts report current and nothing is rewritten.
      Confirm it fails on today's code with the artifact one millisecond
      below `node.mtime`.
- [ ] 1.4 Red: the same for an exact leaf, asserting `.stl` **and** `.brep`
      both current (ADR-044), and for an all-exact fusion whose BREP and
      STL are written synchronously (ADR-045). Confirm both fail today.
- [ ] 1.5 Red: assert the safe direction under the fixture — a source
      edited after a build reports not current — and confirm it already
      passes today, so the fix cannot be credited with it.
- [ ] 1.6 Record the observed red output (which artifact, requested vs
      stored nanoseconds) in the change record for the implementation
      commit.

## 2. Carry the stamp as integer nanoseconds

- [ ] 2.1 Add `AbstractBaseNode.mtime_ns` returning
      `max(os.stat(p).st_mtime_ns for p in self.files)`, and redefine
      `mtime` as `mtime_ns / 1e9` so the two cannot disagree about which
      file won the `max`. `mtime` keeps its float type and its published
      meaning (`core/serializer.py:36` writes it into `viewer.json`).
- [ ] 2.2 Move `_up_to_date` (`node/base.py:693`) to
      `os.stat(path).st_mtime_ns == self.mtime_ns`, keeping the existence
      check and its exception behavior. This is the only freshness
      predicate; all eleven call sites keep their shape.
- [ ] 2.3 Move `_atomic_write_text` (`node/base.py:25`) to
      `os.utime(temporary, ns=(…, mtime_ns))` and pass `self.mtime_ns` from
      `generate_scad` (`base.py:518`).
- [ ] 2.4 Move `StlRenderStart` to carry and stamp nanoseconds
      (`base.py:712`/`716`), with `base.py:581` passing `self.mtime_ns`.
      Keep the log lines readable.
- [ ] 2.5 Move `exact._atomic_export`, `write_brep`, and `write_stl`
      (`exact.py:81`–`111`) to nanoseconds, and their callers
      `node/exact_leaf.py:58,60` and `node/fusion.py:67,68`.
- [ ] 2.6 Move `JScadNode.generate_stl`'s back-date
      (`node/adapters/jscad.py:57`) to nanoseconds.
- [ ] 2.7 Decide and record the disposition of
      `core/builder.py:230`/`243`, which compares a loaded source mtime
      against the current one. It is a source-to-source comparison with no
      `utime` round trip, so it is not affected; move it to `mtime_ns` only
      if that is a coherence win, and say which was chosen and why.

## 3. Green, and no native regression

- [ ] 3.1 Run the tests from batch 1 green.
- [ ] 3.2 Review the `(path, mtime)` caches — `cached_base_mesh`
      (`node/base.py:52`), `exact.cached_shape`, `sources._import_cache`,
      `core/pieces.py:46`, the Manifold cache at `test.py:55` — and confirm
      none is a freshness decision. Record the finding; change nothing
      unless a real defect is found, and if one is, bring it back to the
      pilot rather than widening scope here.
- [ ] 3.3 Run the full framework suite. `tests/test_source_set.py`,
      `tests/test_exact_geometry.py`, `tests/test_build123d_adapter.py`,
      `tests/test_scad_stl.py`, `tests/test_build_publication.py`,
      `tests/test_builder_lifecycle.py` and `tests/test_manifold_cache.py`
      touch currency directly and must stay green unchanged.
- [ ] 3.4 Build a representative real project (v8-engine or an
      `examples/` project) twice on ext4 and confirm the second build
      reports everything current — exact-equality freshness on a normal
      filesystem is unchanged — and that a single edit still invalidates
      exactly its dependants.
- [ ] 3.5 Confirm the one accepted migration cost: a build directory
      stamped by the previous float back-date rebuilds once, then reports
      current.

## 4. Records

- [ ] 4.1 Inspect whether the implemented design carries a consequential
      architecture decision. If it does, extract one ADR amending ADR-006
      (equality preserved; its numeric representation fixed), add it to
      `docs/adrs/NODE/` and `docs/adrs/README.md`, and name the originating
      provenance in it: `browser-engine` change
      `prove-solid-node-runs-in-browser`, upstream finding 1,
      `evidence/groundwork.md`, the 13/25 probe, solid-node 0.5.1 at
      `1c03e337` under Pyodide 314.0.5 / Emscripten 5.0.3.
- [ ] 4.2 If an ADR is accepted, update `docs/architecture.md` — the
      "build artifact is the currency, mtime is its clock" commitment, the
      build-pipeline mtime-equality paragraph, and the load-bearing
      invariant "an artifact is fresh iff its mtime equals the node's max
      source mtime" — to state the nanosecond rule.
- [ ] 4.3 Sync the `build-pipeline` baseline spec from the delta and
      archive the change through the supported OpenSpec workflows.
- [ ] 4.4 Report to the pilot what remains unproven: MEMFS behavior under
      `os.utime(ns=…)` is inferred from the mechanism, not measured, and
      the probe that would measure it belongs to `browser-engine`. Do not
      claim the browser case fixed on this repository's evidence alone.
