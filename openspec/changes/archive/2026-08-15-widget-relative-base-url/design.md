## Context

`resolveBaseUrl(sourceUrl, baseUrl?)` in
`solid_node/viewers/widget/src/options.ts` produces the string the tree
concatenates onto every model path (`tree.ts`: `baseUrl + data.model`). It
derives the base by stripping the query/fragment and then the last path
segment:

```ts
const root = baseUrl ?? sourceUrl.replace(/[?#].*$/, '').replace(/[^/]*$/, '');
return root.endsWith('/') ? root : `${root}/`;
```

For `manifest.json` the second replace yields `''`; `''.endsWith('/')` is
false, so the function returns `'/'` — the server root. The shipped export page
mounts with exactly that URL (`index.html`:
`data-solid-widget="manifest.json"`), so every self-contained export is
affected. It goes unnoticed locally because `solid develop` serves the export
directory at the root, where `/models/...` resolves to the intended file.

Existing tests only exercise sources carrying a directory
(`https://example.test/models/demo/manifest.json`, `/_build/viewer.json`), so
the shipped shape was never covered.

## Goals / Non-Goals

**Goals:**

- A document URL naming no directory resolves models beside the document.
- Preserve every currently-correct resolution: absolute URLs, rooted paths,
  and host-supplied bases (with or without a trailing slash).
- Keep the result a plain string that stays correct under `base + path`
  concatenation, since that is how `tree.ts` consumes it.

**Non-Goals:**

- Reworking model-path resolution to use the URL API or changing the
  concatenation contract in `tree.ts`.
- Changing the manifest format or `solid_node/core/export.py`; exported model
  paths are already document-relative and correct.
- Changing how `solid_node/sphinx.py` places or links exports; its iframe
  `src` already uses `relative_uri` and is correct.

## Decisions

**Return `'./'` when the derived root is empty.**

The empty string is the accurate relative base — `'' + 'models/x.stl'` is
already resolved beside the document by the browser — but returning `''` would
make the function's postcondition ("always ends in `/`", relied on for
joinability) untrue and would read as "unset" to any future caller doing a
truthiness check. `'./'` is explicit, satisfies the trailing-slash
postcondition, and `'./models/x.stl'` resolves identically to
`'models/x.stl'`.

Alternatives considered:

- *Return `''`*: minimal, but breaks the trailing-slash invariant the return
  contract advertises and is easy to misread as absent.
- *Resolve against `document.baseURI` with `new URL()`*: correct, but converts
  a relative base into an absolute one, changing observable request URLs and
  making the unit tests environment-dependent. Disproportionate to the defect.
- *Fix at the call site in `index.html`* (e.g. `data-solid-widget="./manifest.json"`):
  would repair the shipped page only, leaving the same trap for every other
  host that passes a bare filename, and would not satisfy the spec scenario.

**Guard on the derived root only, not on a supplied base.** A host that
explicitly passes `baseUrl: ''` is asking for document-relative resolution and
gets the same `'./'`; the branch is on the resulting empty string, so both
paths behave consistently.

## Risks / Trade-offs

- [A host string-compares the returned base against `'/'`] → No such consumer
  exists; `tree.ts` only concatenates. Covered by running the widget suite.
- [`'./'` is cosmetically visible in request URLs] → Browsers normalise `./`
  during resolution; the emitted network request is unchanged from the
  intended relative form.
- [Fix is invisible to the existing dev-server workflow] → The regression is
  reproduced by unit tests asserting on the resolved base rather than by
  serving, so it holds without a subpath-serving harness.
