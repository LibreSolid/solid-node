## Why

A published export renders no geometry when it is served anywhere but a server
root. `resolveBaseUrl` derives the mesh base by stripping the filename from the
document URL; for a document URL with no directory component it strips to the
empty string and returns `/`, the server root. The widget page shipped with
every export mounts exactly that way — `index.html` carries
`data-solid-widget="manifest.json"` — so every self-contained export resolves
its models against the domain root instead of against its own directory.

Found empirically on the published documentation: the V8 engine example
embedded on `examples.html` requests
`https://solid-node.readthedocs.io/models/root/crank_throw-*.stl` and gets 404,
because the export is served under `/en/latest/_solid_node/<export>/`. The
failure is invisible on a dev server that serves the export directory *at* the
root, where the wrong base happens to resolve.

This violates the `viewer-package` requirement "One loader reads either
published document", which states the mesh base defaults to the document's
directory, and its scenario "A self-contained export", which requires model
paths to resolve beside the manifest.

## What Changes

- `resolveBaseUrl` treats a document URL with no directory component as "the
  current directory" and returns `./`, so model paths resolve beside the
  document rather than at the server root.
- A regression scenario pins the shipped mount shape (a bare `manifest.json`
  document URL, with and without a query string) at spec level, so the
  contract is not carried only by hosts that happen to pass a directory.

No API, option, or manifest format changes. Hosts that supply an explicit mesh
base, and document URLs that already carry a directory, are unaffected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `viewer-package`: the "One loader reads either published document"
  requirement gains a scenario fixing the resolution of a document URL that
  names no directory — it resolves beside the document, not at the server root.

## Impact

- `solid_node/viewers/widget/src/options.ts` — `resolveBaseUrl`.
- `solid_node/viewers/widget/src/options.test.ts` — regression coverage for the
  bare-filename document URL.
- Every consumer of the shipped export page, including the Sphinx embedding
  (`solid_node/sphinx.py`) that serves exports under `_solid_node/<dest>/`, and
  any export hosted under a subpath.
- No change to `solid_node/core/export.py`; manifest model paths are already
  correctly document-relative.
