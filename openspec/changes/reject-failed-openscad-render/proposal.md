## Why

Due-diligence finding F01 reproduced an OpenSCAD assertion failure that
`solid build` reported as success while publishing the renderer's pre-created,
zero-byte temporary file as the current STL. A failed renderer must remain a
failed build and must not replace the last complete artifact.

## What Changes

- Treat a nonzero OpenSCAD subprocess exit status as an STL render failure.
- Remove the failed render's temporary output and per-STL lock without
  publishing or recording artifact currency.
- Propagate the failure through the ordinary builder outcome path so one-shot
  builds exit nonzero and development builds publish `errors.json` without a
  success callback or viewer-snapshot update.
- Preserve an existing published STL when its replacement render fails.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `build-pipeline`: make the asynchronous STL render protocol explicit about
  subprocess failure, cleanup, and preservation of the previously published
  artifact.

## Impact

- `solid_node/node/base.py`: `StlRenderStart.wait()` checks the renderer
  result and owns failure cleanup before publication.
- `tests/test_build_publication.py`: focused process-failure and artifact
  preservation coverage.
- `tests/test_meta.py`: a real OpenSCAD assertion failure proves the CLI exits
  nonzero and does not publish a cold or replacement render.
- Existing node APIs, command syntax, artifact names, and successful-render
  behavior remain unchanged. The JSCAD adapter is outside this change because
  F01 reproduced the OpenSCAD protocol; its separate direct-publication path
  needs its own evidence and design.
