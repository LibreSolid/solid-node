# Build Viewer Artifacts Specification

## Purpose

Complete normal-build viewer state for private local framework consumers.
## Requirements

### Requirement: Complete builds publish a viewer snapshot

The builder SHALL publish the versioned viewer snapshot named `viewer.json` in
the normal build directory only after the current project model has assembled
and every required STL artifact is current. The document SHALL declare
`format: "solid-node-export"`, the schema version its content needs, an
`animation` object with numeric
`fps` and `frames`, and a `root` with the same observable schema and child-name
behavior as export `manifest.json`. When the root assembly declares a time
base, the `animation` object SHALL also carry numeric `loop`: the declared
seconds of machine time one turn of `$t` covers; when it declares none, the
key SHALL be absent. `loop` is additive within the current schema version: a
consumer that does not read it plays `frames / fps` exactly as before, and
the published expressions already carry the multiplication. The root SHALL
include node identity, type,
colour, `mtime`, serialized operations, child relationships, and
build-root-relative rigid-model paths. The shared format SHALL identify this
versioned tree-document schema without implying portability. The snapshot SHALL
be written after the model files it references, atomically, so that every path
it names is readable the moment the snapshot itself is. The build publication
SHALL remain non-portable: it SHALL NOT create an export-style `models/`
directory or copy models into one. Changes to the shared tree shape or operation
serialization are breaking and MUST bump `version` and update every producer and
consumer of the shared schema together.

When the serialized document contains a subexpression occurring more than
once, `viewer.json` SHALL carry the same ordered `bindings` table the export
manifest carries, under the same shared-subexpression, naming and version
rules, and SHALL declare `version: 4`. When it contains no such subexpression
the key SHALL be absent and the snapshot SHALL declare the version its content
already needed, byte-identical to the snapshot published before bindings
existed.

When the built root declares `time = Time.running()`, `viewer.json` SHALL
declare `version: 5` and SHALL carry the same `program` object the export
manifest carries, under the same rules — the coordinate table with each bank
id's kind, rest value and unit, the intermediates, the edges in program
order with their expressions and jump plans, the spans, the candidate table,
the program identity, the clock name and the algorithm's limits — and its
pose expressions SHALL name bank ids under the requirement "A committed bank
poses the geometry". When the root declares no time base or a looping one,
`viewer.json` SHALL carry no `program` key and SHALL be byte-identical to
the snapshot published before the program existed.

Because publication is decided by comparing the serialized document against the
one already published, the `bindings` table SHALL be ordered deterministically
for a given tree: rebuilding an unchanged model SHALL NOT republish merely
because its bindings were named or ordered differently. The `program` object
and every name it mints SHALL be ordered deterministically for the same
reason.

A producer that writes a document whose version the installed viewer does not
report as one it renders SHALL WARN once, naming the version written, the
versions the installed viewer renders and the installed viewer's package
version, and SHALL publish the document anyway: the build, its artifacts and
a viewerless watch loop are unaffected by a browser that cannot render, and
the document's own refusal is the consumer's to make.

#### Scenario: A running model publishes its program

- **WHEN** `solid build <project>` completes a model whose root declares
  `time = Time.running()`
- **THEN** its `viewer.json` declares `version: 5`, carries a `program`
  object naming every bank coordinate and every compiled edge, and its joint
  placements are those coordinates' own names

#### Scenario: An untimed build is unchanged

- **WHEN** `solid build <project>` completes a model whose root declares no
  time base
- **THEN** its `viewer.json` has no `program` key and is byte-identical to
  the snapshot published for that model before this change

#### Scenario: A viewer that cannot read what was written

- **WHEN** `solid build <project>` publishes a version 5 document in an
  installation whose viewer reports that it renders versions 1 to 4
- **THEN** the build completes, the document is published, and one warning
  names the version written, the versions the viewer renders and the viewer's
  package version

#### Scenario: An unchanged running model is not republished

- **WHEN** an unchanged running model is built twice
- **THEN** the second build finds the serialized document equal to the
  published one — the program's ordering and its minted placeholder names
  included — and does not republish

#### Scenario: A complete model is built once
- **WHEN** `solid build <project>` completes successfully
- **THEN** its `_build` directory contains `viewer.json` with the shared format
  and node fields, and each rigid model path resolves relative to that same
  published build directory

#### Scenario: A completed animated model is published
- **WHEN** `solid build <project>` completes a model with a `$t` operation
- **THEN** its `viewer.json` contains numeric `animation.fps` and `animation.frames` values alongside the root tree

#### Scenario: A declared time base is published

- **WHEN** `solid build <project>` completes a model whose root declares
  `time = Time(loop=43200)`
- **THEN** its `viewer.json` carries `animation.loop == 43200` beside `fps`
  and `frames`, the document version is the one its tree content already
  needs, and the operations carry `$t` multiplied by the loop

#### Scenario: An undeclared root publishes no loop

- **WHEN** `solid build <project>` completes a model whose root declares no
  time base
- **THEN** its `viewer.json` `animation` object has no `loop` key

#### Scenario: A model whose expressions repeat a subexpression

- **WHEN** `solid build <project>` completes a model in which one
  subexpression appears in the operations of several nodes
- **THEN** its `viewer.json` declares `version: 4`, carries a non-empty
  ordered `bindings` array, and holds that subexpression's text exactly once

#### Scenario: A model with nothing shared publishes the document it always did

- **WHEN** `solid build <project>` completes a model whose expressions repeat
  no subexpression
- **THEN** its `viewer.json` has no `bindings` key and is byte-identical to the
  snapshot published for that model before bindings existed

#### Scenario: An unchanged model is not republished for its bindings

- **WHEN** an unchanged model carrying bindings is built twice
- **THEN** the second build finds the serialized document equal to the
  published one and does not republish

#### Scenario: Linked names match the portable export

- **WHEN** the same attribute-linked assembly is published as a normal build
  and as a static export
- **THEN** `viewer.json` and `manifest.json` contain the same linked node names,
  operations, bindings, colour, `mtime`, and rigid/non-rigid tree structure
  while retaining their distinct model path roots

### Requirement: Failed later builds retain viewer state

A build failure after a successful publication SHALL leave a readable viewer
snapshot naming readable model files, and SHALL report the failure through
`errors.json`. The snapshot and models MAY reflect a partially updated model
rather than the preceding complete one.

#### Scenario: A later project edit fails to build
- **WHEN** a later `solid develop` build fails after a completed publication
- **THEN** the callback is not emitted, `errors.json` reports the failure, and
  the snapshot readable from `_build` still names model files that are present
  and complete

### Requirement: Published build snapshots carry the piece inventory

The published `viewer.json` SHALL include the printed-piece inventory defined by
the `printed-pieces` capability, with each piece's `models` references using the
same build-root-relative model paths the tree uses. The snapshot SHALL remain
non-portable: computing the inventory SHALL NOT create a `models/` directory or
copy any mesh.

The inventory SHALL be derived from the same current artifacts the snapshot
already references, and SHALL be published within the existing atomic write, so
every model path and piece a consumer reads is backed by a file already present
and complete. A piece whose facts cannot be derived SHALL NOT prevent
publication of the tree.

#### Scenario: A complete build publishes its pieces

- **WHEN** `solid build <project>` completes successfully
- **THEN** its `viewer.json` contains a `pieces` list beside `root`, every rigid
  node carries a `piece` id present in that list, and every model the inventory
  names resolves relative to that same published build directory

#### Scenario: Publication is still not an export

- **WHEN** a complete build is published
- **THEN** the inventory names ordinary build-root-relative model files, creates
  no export-style `models/` tree, and copies no mesh

#### Scenario: Artifact sweeping is unaffected

- **WHEN** a build publishes a snapshot and sweeps artifacts it no longer
  references
- **THEN** every model named by the inventory survives the sweep
