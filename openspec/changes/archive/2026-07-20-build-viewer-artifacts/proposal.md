## Why

The shop floor needs to inspect the complete model produced by `solid build`
and refresh it after `solid develop --callback`, without importing project
Python into its long-lived process.  The new commands currently publish only
STL and SCAD files, while the existing development viewer additionally
derives the model tree and its serialized operations from the loaded project.

## What Changes

- Publish a complete, viewer-readable model representation as part of every
  successful normal build-directory publication.
- Make the representation sufficient for a host such as shop-floor to serve
  the existing solid-node viewer implementation directly from `_build`.
- Preserve the previous complete viewer state when a later build fails, just
  as the build artifacts themselves are preserved.
- Add red-first command and build-pipeline coverage proving that `solid build`
  and successful `solid develop --callback` publications expose the same
  usable viewer state.

## Capabilities

### New Capabilities

- `build-viewer-artifacts`: Complete viewer model data published with a normal
  build for local consumers that do not import project code.

### Modified Capabilities

- `build-pipeline`: A successful build publication includes the complete
  viewer-readable model state and preserves last-known-good state on failure.
- `cli`: `solid build` produces a completed build directory suitable for the
  framework viewer as well as ordinary STL consumers.

## Impact

The change affects builder publication, the build command, development
callback consumers, and focused CLI/build lifecycle tests.  It originates
from solid-node-shop Sprint 001 STORY-005, whose floor consumes `_build` and
the framework viewer implementation without importing project Python.
