## Why

The documentation's Examples page embeds both worked example machines — the
V8 engine and the Metamaquina 2 — on the same page. Each `.. solid-node::`
directive is an `<iframe>` running a full viewer: it fetches that machine's
export, builds its scene and animates it. A reader who opens the page pays
for both machines at once, and these are the two heaviest models the project
publishes. The page is slow to become usable, and on modest hardware it is
the worst first impression the documentation makes.

Nothing about the material requires the two machines to share a page. They
are independent projects with independent source repositories, and a reader
consults one of them at a time.

## What Changes

- The Examples page becomes an index: it introduces the worked examples and
  offers a nested toctree, and it embeds no live model itself.
- Each worked example machine moves to its own page, carrying its prose,
  its single `.. solid-node::` widget and its source link.
- The pointer to the small committed tutorial models stays on the index.
- Cross-references that point readers at an example (`docs/testing.rst`)
  point at that example's own page rather than at the shared page.
- No export path, build configuration, or committed export changes: the
  new pages sit beside the old one in `docs/`, so every directive argument
  stays exactly as it is.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `user-documentation`: the "Worked examples demonstrate the released
  capabilities" requirement changes from a single examples page presenting
  the worked examples to an examples section that gives each worked example
  its own page, so opening one example loads one live model.

## Impact

- `docs/examples.rst` — becomes the index; loses both widgets.
- New per-example pages under `docs/`.
- `docs/testing.rst` — two `:doc:` cross-references retargeted.
- `docs/index.rst` — unchanged entry (`examples` stays in the Reference
  toctree); the new pages are reached through its nested toctree.
- `tests/test_docs_exports.py` — no change needed: it walks every `.rst`
  under `docs/` and resolves each directive against its own document, so it
  keeps covering the moved directives. Its assertions are the proof that
  the move did not orphan an export.
- `.readthedocs.yaml` and `.github/workflows/python-app.yml` — unchanged;
  the same two exports are built to the same paths.
