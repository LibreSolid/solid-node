## Why

Due-diligence finding F08 reproduced `solid new 3d-printer` reporting success
while generating `class 3dPrinter`, which is invalid Python and makes the fresh
project fail its first build. The existing CLI contract already promises an
identifier-safe package and derived class, but normalization covers punctuation
without covering leading digits or Python keywords.

## What Changes

- Normalize every scaffold name to a valid, non-keyword Python package
  identifier before deriving paths, module references, and class names.
- Prefix a sanitized name that starts with a digit or is a Python keyword with
  `project_`; preserve established results for already valid names and names
  containing punctuation such as `snowman-3`.
- Derive the model and test class names from the final package identifier so
  all generated Python compiles and the manifest names the generated class.
- Add normalization examples and end-to-end acceptance coverage requiring
  digit-leading and keyword-named projects to build and run their scaffolded
  tests without edits.
- Keep the hard-coded browser URL in the printed next steps outside this change;
  it is an independent documentation/configuration review lead, not the cause
  of the unusable generated source.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `cli`: make the new-project command's identifier-safety promise explicit for
  leading digits and Python keywords.

## Impact

- `solid_node/manager/new.py`: centralize package/class derivation and apply a
  deterministic `project_` prefix when the sanitized basename is not a usable
  Python identifier.
- `tests/test_manager_new.py`: cover the normalization matrix, compilation,
  manifest consistency, and real build/test acceptance.
- `docs/due-dilligence/probe_build.py`: the existing numeric scaffold probe
  becomes caller evidence for a clean first build.
- `docs/changelog.rst` and due-diligence records will describe the fix and
  retain the separate printed-URL review lead.
- Existing valid scaffold names, CLI grammar, templates, dependencies, and
  generated project structure are unchanged.
