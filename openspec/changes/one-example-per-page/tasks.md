## 1. Prove the failure

- [ ] 1.1 Add a test to `tests/test_docs_exports.py` asserting that a
      document embedding a build-time example export embeds exactly one
      `.. solid-node::` directive, and that each such export is embedded by
      exactly one document.
- [ ] 1.2 Run it and confirm it fails red on `docs/examples.rst` embedding
      both example machines.

## 2. Split the pages

- [ ] 2.1 Create `docs/example-v8-engine.rst` with the V8 engine prose, its
      single `.. solid-node:: examples/v8-engine/docs/_exports/v8-engine`
      directive and its source link.
- [ ] 2.2 Create `docs/example-metamaquina2.rst` with the Metamaquina 2
      prose, its single
      `.. solid-node:: examples/metamaquina2/docs/_exports/metamaquina2`
      directive and its source link.
- [ ] 2.3 Rewrite `docs/examples.rst` as the index: keep the `_examples`
      label and the intro, add a toctree over the two new pages with a short
      description of each, keep the "Models used in this documentation"
      section, and remove both directives.

## 3. Repoint the references

- [ ] 3.1 Retarget the two `:doc:` cross-references in `docs/testing.rst` to
      `example-v8-engine`.
- [ ] 3.2 Confirm no other document or the README references the moved
      content by a path that no longer resolves.

## 4. Verify

- [ ] 4.1 Run `tests/test_docs_exports.py` and `tests/test_sphinx_ext.py`
      green.
- [ ] 4.2 Build the documentation with the tutorial exports available and
      `-W`, and confirm no toctree, reference, or duplicate-label warning.
- [ ] 4.3 Confirm the rendered examples index carries no iframe and each new
      page carries exactly one.
