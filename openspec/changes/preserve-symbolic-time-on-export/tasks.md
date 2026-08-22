## 1. Red first: prove the defect and the missing primitive

- [ ] 1.1 In `tests/test_export.py::ExportAnimationTest`, add
      `test_time_expression_is_exported_raw_after_keyframe`: build the existing
      `Spinner` fixture, call `node.set_keyframe(0.25)`, export, and assert the
      child's rotation operation still contains `$t`. Run it and record the red
      output — it must fail with the baked constant `'90.0'`.
- [ ] 1.2 In `tests/test_export.py::ExportAnimationTest`, add
      `test_export_leaves_node_in_symbolic_time`: after exporting a keyframed
      `Spinner`, assert `node.time` is symbolic (not a float) and that a
      subsequent `set_keyframe` still resolves numerically. Record it red
      (`AttributeError`/`0.25` today).
- [ ] 1.3 In `tests/test_meta.py`, add a keyframe-reversibility test over
      `tests/meta_project/nested.py`: `set_keyframe(0.5)`, `clear_keyframe()`,
      then assert the inner cube's serialized translation equals the
      never-keyframed render's `(10 * $t)` form and `inner.time` is symbolic.
      Record it red (`AttributeError: 'Nested' object has no attribute
      'clear_keyframe'`).
- [ ] 1.4 In `tests/test_meta.py`, add the non-linear counterpart over
      `tests/meta_project/conrod.py`: keyframe, clear, and assert the rod's
      rotation serializes to `asin((0.25 * sin((360.0 * $t))))`, byte-identical
      to a fresh render, with the static `translate([2, 0, 0])` still present
      exactly once. Record it red.
- [ ] 1.5 In `tests/test_meta.py`, add the accumulation guard: alternate
      `set_keyframe`/`clear_keyframe` twice and assert the driven child holds
      exactly one rotation operation. Record it red.
- [ ] 1.6 In `tests/test_meta.py` (or beside the existing assembly tests), add
      the non-list-render guard test: call `set_keyframe` and `clear_keyframe`
      on an assembly whose `render()` returns a single node and assert neither
      raises. Record `set_keyframe`'s red `TypeError: ... is not iterable`.

## 2. Implement the reversible keyframe

- [ ] 2.1 Add `AbstractBaseNode.clear_keyframe()` in `solid_node/node/base.py`
      as a documented no-op, beside the existing `set_keyframe` no-op.
- [ ] 2.2 Add `AssemblyNode.clear_keyframe()` in `solid_node/node/assembly.py`:
      drop `_time`, re-render, recurse into rendered children. Docstring states
      it is the inverse of `set_keyframe` and that the idempotent-render sweep
      is what re-expresses driven operations symbolically.
- [ ] 2.3 Add the shared non-list/tuple guard to both `set_keyframe` and
      `clear_keyframe` so a partial node recurses into no children instead of
      raising, matching `serialize_node`'s tolerance.
- [ ] 2.4 Run 1.3–1.6 green.

## 3. Make export guarantee the animated document

- [ ] 3.1 In `solid_node/core/export.py`, have `export_node` call
      `node.clear_keyframe()` before `serialize_node`.
- [ ] 3.2 Update `export_node`'s docstring and the module docstring: the
      manifest always carries symbolic `$t`, the node is left in symbolic time,
      the caller re-applies `set_keyframe` if it wants a pose back, and a static
      presentation comes from the widget's `?t=&autoplay=0`.
- [ ] 3.3 Run 1.1–1.2 green.

## 4. Prove nothing else moved

- [ ] 4.1 Run `tests/test_export.py`, `tests/test_pieces.py`,
      `tests/test_web_viewer.py`, `tests/test_widget_e2e.py`,
      `tests/test_build_lock.py`, `tests/test_build_publication.py` and confirm
      the export and build documents are unchanged for non-keyframed nodes.
- [ ] 4.2 Run `tests/test_snapshot.py` and `tests/test_browser_renderer.py` and
      confirm the web-snapshot document is still numerically baked — the
      keyframed snapshot path must not become symbolic.
- [ ] 4.3 Run `tests/test_conrod_symbolic.py`, `tests/test_math.py`,
      `tests/test_meta.py`, `tests/test_node_mesh_cache.py`,
      `tests/test_manager_test.py` for the keyframe/`$t` surfaces.
- [ ] 4.4 Run the full suite (`--ignore=tests/test_build123d_adapter.py`) and
      compare against the recorded base result of 615 passed / 2 known
      environmental `build123d` failures in `tests/test_openscad_dependency.py`.
- [ ] 4.5 Re-run the finding's own reproduction end to end —
      `load_node` → `set_keyframe(0.0)` → `export_node` → read
      `manifest.json`'s operations — and record the transcript.

## 5. Document and complete

- [ ] 5.1 Document `clear_keyframe` in `docs/animation.rst` and
      `docs/api-reference.rst`, naming the publish-after-keyframe hazard it
      resolves.
- [ ] 5.2 Assess ADR need after implementation: the producer-owns-the-guarantee
      boundary (why `export_node` and not `serialize_node`, and why the
      web-snapshot producer stays baked) is the candidate; record it only if the
      implemented design confirms it as architectural.
- [ ] 5.3 Sync baseline specs and archive the change.
