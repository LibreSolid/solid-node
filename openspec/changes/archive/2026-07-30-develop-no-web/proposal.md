## Why

`solid develop` always starts the framework's own web viewer unless
`--openscad` is passed alone, so a caller that only wants the watch/rebuild
loop cannot avoid binding `SOLID_NODE_PORT`. An external viewer host that
renders `_build/` itself gets a second HTTP server it never opens, a port it
did not ask for, and a collision when two such hosts run at once.

The concrete caller is the solid-node-shop harness: it runs
`solid develop root --callback URL` purely for the rebuild loop, serves the
published `_build/` directory through its own browser renderer, and never
opens `http://localhost:8000`. Two shops on one machine currently fight over
that port for a viewer neither of them uses.

## What Changes

- Add `--no-web` to `solid develop`: run the builder watch loop with no web
  viewer and no npm dev server.
- Allow `--callback URL` together with `--no-web`, so a host that publishes
  its own view still receives the build-ready notification. Callback remains
  rejected with `--openscad` and `--web-dev`.
- Reject `--no-web` alongside a flag that explicitly asks for the web viewer
  (`--web`, `--web-dev`, `--debug-web`) with a clear argument error.
- `--no-web` with `--openscad` is accepted; both suppress the web viewer.
- No change to default behavior: `solid develop <path>` still starts the web
  viewer. Not a breaking change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`: the Develop command requirement currently states the web viewer "is
  suppressed only when `--openscad` is passed alone" — `--no-web` becomes a
  second, explicit suppression. The Callback mode validation requirement
  currently admits `--callback` "only in normal web mode" — it must also admit
  no-web mode.
- `one-shot-build-and-notification`: the Development build-ready callback
  requirement is worded "each complete successful normal-web development
  build"; the callback must fire in a no-web session too.

## Impact

- `solid_node/manager/develop.py`: argument definition, the mode-selection
  condition at the top of `handle()`, and callback-compatibility validation.
- `solid_node/cli.py`: unchanged; the flag is registered through the command's
  own `add_arguments`.
- No change to `Builder`, `BuildSession`, publication, or callback delivery
  semantics.
- Downstream: solid-node-shop can drop the unused viewer and its port. The
  framework's own `docs/cli.rst` develop section needs the new flag.
