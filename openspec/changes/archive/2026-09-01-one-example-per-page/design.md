## Context

`docs/examples.rst` holds two `.. solid-node::` directives. The Sphinx
extension renders each as an `<iframe>` onto a copied export's widget, so
one page starts two viewers, fetches two manifests and animates two of the
largest published models simultaneously.

Two existing constraints shape where the split pages can go:

- `docs/conf.py` sets `exclude_patterns = ['_build', 'examples/**', ...]`,
  because `docs/examples/` holds the example projects' own checkouts.
- `tests/test_docs_exports.py` skips any `.rst` whose first path component
  under `docs/` is `_build` or `examples`, mirroring that exclusion.

A page placed under `docs/examples/` would therefore be silently dropped
from the build and from the test that keeps every embedded export honest.

## Goals / Non-Goals

**Goals:**

- One live model per page for the worked examples.
- Keep every export path, build command and committed export untouched.
- Keep `tests/test_docs_exports.py` covering the moved directives.

**Non-Goals:**

- Changing the Sphinx extension, lazy-loading iframes, or adding a
  click-to-load poster. Those are separate designs; this change reduces the
  load by splitting the material, not by changing the embedding mechanism.
- Splitting the tutorial pages that embed several small demo models
  (`leaf-nodes`, `testing`, `fusion`, `assemblies`). Those models are small,
  and each is the illustration of the paragraph above it, so moving them
  would break the teaching rather than help it.
- Renaming or restructuring the two example projects.

## Decisions

**Per-example pages sit directly in `docs/`, named `example-<machine>.rst`.**
`docs/examples/` is excluded from the Sphinx build and from the export test,
so a nested `docs/examples/*.rst` layout would be invisible to both. A flat
sibling matches the rest of the documentation, which is entirely flat, and
keeps every directive argument byte-identical because the directive resolves
its argument against the document's own directory — still `docs/`.

Alternative considered: a new `docs/gallery/` directory. It would work, but
it buys nothing over a flat name and introduces the only nested document
directory in the project, plus a `../` in every directive argument.

**`docs/examples.rst` stays the entry in `docs/index.rst` and becomes an
index page with a nested toctree.** Readers, external links and the existing
`:ref:`examples`` label keep working, and `maxdepth: 2` in the Reference
toctree already renders the nested children.

**`docs/testing.rst`'s two cross-references retarget to the V8 engine page.**
Both point a reader at the V8 engine specifically, not at the collection.

## Risks / Trade-offs

- [A reader who wants to browse both machines now pays a navigation click]
  → The index page keeps both descriptions, so the choice is made from prose
  rather than by waiting for two viewers to start.
- [A future example added to the index without its own page would quietly
  reintroduce the problem] → The spec states one page per worked example,
  and the index page embeds no directive of its own, so adding one there is
  a visible departure rather than an easy default.
