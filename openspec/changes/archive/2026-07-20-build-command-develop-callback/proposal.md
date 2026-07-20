## Why

The shop floor needs to build a project's conventional model once and then
learn when the machinist has published a later usable build, without owning
the model process or polling source files.  The existing `develop` command
combines a watch loop and viewer lifetime, while no public one-shot build or
build-ready callback exists.

## What Changes

- Add `solid build <path>`, which performs the ordinary solid-node build
  pipeline once, publishes its normal project build artifacts, and exits.
- Give a missing resolved model path the documented `MODEL_NOT_FOUND` exit
  status 66; retain normal non-zero failure behavior for other build errors.
- Preserve the last complete successful build artifacts across a failed later
  build; never publish a partial replacement as a successful result.
- Add `solid develop <path> --callback URL` for the default web mode.  It
  issues an empty HTTP POST to the supplied URL after the initial successful
  build and each later successful rebuild, once artifacts are fully
  published.
- Keep callback delivery best-effort: use a short timeout, log failures, do
  not retry, and never stop the development watch loop because the callback
  is unavailable.  Failed builds do not invoke the callback.
- Reject `--callback` with `--openscad` or `--web-dev`; `solid build` does
  not accept callbacks.

## Capabilities

### New Capabilities

- `one-shot-build-and-notification`: One-shot build publication and
  development build-ready notification for external local consumers.

### Modified Capabilities

- `cli`: Add the `build` command and constrain the `develop --callback` CLI
  surface.
- `build-pipeline`: Define successful publication, last-known-good artifacts,
  and the point at which an external consumer may observe a successful build.

## Impact

The change affects the command registry and help, `Develop` process
orchestration, builder publication/error behavior, CLI and build-pipeline
tests, and command-line documentation.  It supplies the framework contract
for shop STORY-005; browser embedding and floor lifecycle remain consumers of
this API and are not changed here.
