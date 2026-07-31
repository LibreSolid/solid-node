## Why

The `snowman-2` project exposed that a package entry point cannot re-export a
node class from an implementation module: `NODE = SnowmanBody` is rejected
solely because `SnowmanBody` was imported. This forces projects to add a
meaningless local subclass or keep implementation in `__init__.py`, even
though an explicit marker is already an unambiguous declaration of intent.

## What Changes

- Allow an explicit module-level `NODE` marker to name an
  `AbstractBaseNode` subclass imported from another project-local module.
- Continue requiring the marker value to be a node class and preserve loud
  ambiguity failures when no marker is present.
- Keep implicit single-class discovery scoped to classes defined in the loaded
  file, so imported helpers are never selected accidentally.
- Update the loader contract, architecture synthesis, and the accepted loader
  decision record to describe package entry-point re-exports.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `build-pipeline`: Explicit `NODE` markers may select project-local imported
  node classes, while implicit discovery remains same-file-only.

## Impact

The public project entry-point contract changes in
`solid_node/core/loader.py`. Loader fixtures and tests gain the originating
`snowman-2` package-layout reproduction. The build-pipeline baseline, ADR-026,
and `docs/architecture.md` require reconciliation. No dependency or CLI syntax
change is expected.
