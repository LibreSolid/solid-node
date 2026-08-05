## 1. Reproduce (red)

- [x] 1.1 Add a failing case to `solid_node/viewers/widget/src/options.test.ts`
      asserting `resolveBaseUrl('manifest.json')` resolves beside the document
      (`'./'`) rather than at the server root (`'/'`)
- [x] 1.2 Add a failing case for the same document URL carrying a query string
      (`'manifest.json?v=2'`), covering the query-stripping path
- [x] 1.3 Run the widget suite and confirm the new cases fail with the observed
      `'/'`, matching the published 404 on `/models/root/*.stl`

## 2. Fix (green)

- [x] 2.1 In `solid_node/viewers/widget/src/options.ts`, return `'./'` from
      `resolveBaseUrl` when the derived root is empty, leaving every other
      branch untouched
- [x] 2.2 Run the widget suite and confirm the new cases pass

## 3. Verify no regression

- [x] 3.1 Confirm the pre-existing `resolveBaseUrl` cases still pass: absolute
      document URL, rooted `/_build/viewer.json`, and host-supplied base with
      and without a trailing slash
- [x] 3.2 Run the full widget test suite green
- [x] 3.3 Run the Python sphinx-extension tests (`tests/test_sphinx_ext.py`) to
      confirm the embedding path is unaffected
