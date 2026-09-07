## MODIFIED Requirements

### Requirement: Manifest contract

The manifest SHALL retain the document name `manifest.json` and SHALL declare
`format: "solid-node-export"`, `animation: {fps, frames}`, a
`drivers` table, an `instructions` table, and a
`root` tree with the same observable schema and child-name behavior as the
normal-build `viewer.json`. When the exported root declares a time base the
`animation` object SHALL also carry numeric `loop`, the declared seconds of
machine time one turn of `$t` covers, and SHALL omit the key otherwise; the
browser-snapshot document SHALL publish `loop` under the same rule. `loop` is
additive within the current schema version — a consumer that does not read
it plays `frames / fps` as before — and `--fps` / `--frames` keep their
meaning as the timeline's playback resolution. A rigid node SHALL emit one
`model` reference and
stop recursion; a non-rigid node whose render result is a list or tuple SHALL
recurse into its children; a flexible leaf SHALL emit one `flexible` object
and stop recursion. Each node SHALL carry `name`, `type`, `color`,
`mtime`, and its operations as raw unevaluated expression strings so `$t`
animation is preserved verbatim. A rigid model reference SHALL be derived
relative to the selected build directory that owns the artifact, SHALL remain
rooted beneath the export's `models/` directory with no parent traversal, and
SHALL resolve to a copied artifact so the export remains portable and
self-contained regardless of the caller's working directory. An artifact
outside that build directory SHALL make export fail before it creates or
modifies the requested output. Changes to the shared tree shape or operation
serialization are breaking and MUST bump `version` and update every producer
and consumer of the shared schema together.

The document SHALL declare `version: 3` when the serialized tree contains at
least one flexible leaf, and `version: 2` otherwise, so a document without
flexible content stays byte-compatible with existing consumers and an old
consumer refuses only what it genuinely cannot render. Consumers SHALL accept
both versions.

#### Scenario: A declared time base is exported

- **WHEN** a root declaring `time = Time(loop=43200)` is exported
- **THEN** `manifest.json` carries `animation.loop == 43200` beside the
  requested `fps` and `frames`, its version is unchanged by the key, and its
  operations carry `$t` multiplied by the loop rather than a constant

#### Scenario: An undeclared root exports no loop

- **WHEN** a root declaring no time base is exported
- **THEN** `manifest.json`'s `animation` object has no `loop` key and is
  byte-identical to the manifest exported before this change

#### Scenario: Export starts in a project subdirectory

- **WHEN** a project model is exported from a working directory below its
  project root to an output directory elsewhere
- **THEN** every model reference contains no parent traversal and resolves to
  its copied artifact beneath the output's `models/` directory

#### Scenario: Export uses a configured or selected build directory

- **WHEN** export uses a relative configured build root or a named model's
  selected build directory
- **THEN** model references preserve artifact paths relative to that resolved
  directory and resolve beneath the export's `models/` directory

#### Scenario: A model artifact is outside its build directory

- **WHEN** a rigid node names an STL whose canonical path is outside its
  resolved build directory
- **THEN** direct export raises `ExportModelPathError`, CLI export exits
  nonzero with that diagnostic, and the requested output is not created or
  modified
