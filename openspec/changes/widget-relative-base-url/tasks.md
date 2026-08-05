## 1. Reproduce (red)

- [ ] 1.1 Add a failing case to `solid_node/viewers/widget/src/options.test.ts`
      asserting `resolveBaseUrl('manifest.json')` resolves beside the document
      (`'./'`) rather than at the server root (`'/'`)
- [ ] 1.2 Add a failing case for the same document URL carrying a query string
      (`'manifest.json?v=2'`), covering the query-stripping path
- [ ] 1.3 Run the widget suite and confirm the new cases fail with the observed
      `'/'`, matching the published 404 on `/models/root/*.stl`

## 2. Fix (green)

- [ ] 2.1 In `solid_node/viewers/widget/src/options.ts`, return `'./'` from
      `resolveBaseUrl` when the derived root is empty, leaving every other
      branch untouched
- [ ] 2.2 Run the widget suite and confirm the new cases pass

## 3. Verify no regression

- [ ] 3.1 Confirm the pre-existing `resolveBaseUrl` cases still pass: absolute
      document URL, rooted `/_build/viewer.json`, and host-supplied base with
      and without a trailing slash
- [ ] 3.2 Run the full widget test suite green
- [ ] 3.3 Run the Python sphinx-extension tests (`tests/test_sphinx_ext.py`) to
      confirm the embedding path is unaffected
