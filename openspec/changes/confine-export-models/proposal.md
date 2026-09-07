## Why

Due-diligence finding F03 reproduced `solid export` writing a model outside
the requested output directory while reporting success. The exporter derives
its artifact root from the caller's working directory, even though nodes derive
their artifacts from the discovered project root and selected model directory.

## What Changes

- Resolve exported model paths relative to the same selected build directory
  that owns the node artifacts, independent of the command's working directory.
- Refuse an export before creating its output when a rigid node names an
  artifact outside that build directory.
- Keep every manifest model reference beneath `models/`, without a parent
  traversal, and copy it to the matching location beneath the requested output.
- Cover project-root and nested-directory invocation, configured build roots,
  and selected named-model build directories.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `export`: make the existing portable, self-contained model-path contract
  explicit for every invocation origin and reject artifacts outside the
  selected build directory.

## Impact

- `solid_node/core/export.py`: derive and validate model paths against the
  framework's resolved build directory.
- `solid_node/manager/export.py`: report the new controlled export failure.
- `tests/test_export.py`: add direct and CLI regressions for containment,
  invocation origin, configured build roots, and named models.
- `docs/changelog.rst` and the due-diligence records: document F03's resolution.
- The manifest schema, model deduplication, CLI syntax, viewer consumers, and
  successful export layout remain unchanged.
