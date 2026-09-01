# user-documentation Specification

## Purpose
TBD - created by archiving change docs-0-6-narrative. Update Purpose after archive.
## Requirements
### Requirement: Release-current narrative framing

The published user documentation's entry surface — the Sphinx index page,
the "why" page, the quickstart, and the README's user-facing section — SHALL
present the framework as the released version defines it: a machine with
declared named inputs that can be stepped deterministically in Python and
driven by hand in the viewer, whose parts span the full released leaf
taxonomy (the modelling-backend adapters plus sheet, imported-mesh, and
flexible leaves). Entry pages SHALL NOT present a superseded framing (such
as backend aggregation or `$t`-only animation) as the product's thesis.

#### Scenario: First contact with the landing page

- **WHEN** a reader opens the documentation index
- **THEN** its introduction names drivers, simulation, and the driveable
  viewer alongside modelling, and its toctree offers pages for driving a
  machine and for simulating scenarios

#### Scenario: The "why" page matches the release

- **WHEN** a reader opens the "why solid-node" page
- **THEN** every capability it claims exists in the released version, its
  backend list matches the released adapters, and no released leaf kind is
  absent from its story

### Requirement: The public motion surface is documented

The documentation SHALL document the released motion and simulation surface:
driver declaration and attribute reads, `set_state` with instance-qualified
ids, ports and `connect()`, instruction declarations, the fixed-`dt`
simulation loop, and scenario tests that run under both plain pytest and
`solid test`. Every name exported by `solid_node.simulation` SHALL appear in
at least one published page. Tutorial pages that embed a model SHALL use
committed exports so the docs build stays free of the CAD stack.

#### Scenario: Setting a driver from Python

- **WHEN** a reader looks up how to move a machine from code
- **THEN** the documentation shows `set_state` with a qualified dotted id,
  states that assignment to a driver attribute is rejected, and shows the
  driver being read back as an attribute

#### Scenario: Driving a published model in the browser

- **WHEN** a reader opens the driving tutorial
- **THEN** an embedded committed export shows per-driver sliders and
  per-instruction buttons, and the page explains the layer-scoped controls
  and breadcrumb focus

#### Scenario: Deterministic stepping

- **WHEN** a reader needs to test a machine's behavior over time
- **THEN** the documentation shows a `ScenarioTest` building a `Sim` with a
  fixed `dt`, scheduling actions and assertions by tick, and running under
  pytest and `solid test` unmodified

### Requirement: Viewer and embedding claims are accurate

Embedding and viewer documentation SHALL state the viewer API version the
widget actually declares and the document schema versions it accepts, SHALL
document the complete public mount-handle surface including the driving
methods and chrome suppression, and SHALL warn hosts that pin their own
bundle when older viewers cannot detect documents they do not understand.
Known interface limitations (such as poses that can only be preset through
`$t`) SHALL be stated rather than left for the reader to discover.

#### Scenario: A host pins its own bundle copy

- **WHEN** an embedding host reads the embedding page
- **THEN** a prominent warning states that a pre-0.6 viewer silently
  renders only part of a 0.6 document and that a pinned bundle must be
  upgraded with the framework

#### Scenario: A host builds its own control UI

- **WHEN** a host wants programmatic driving without the built-in chrome
- **THEN** the documentation shows `driverControls: 'none'` and the driving
  methods of the mount handle, including that values are in native driver
  units and that declared ranges never clamp

### Requirement: Installation and dependency claims match released packaging

Requirement and installation statements in the documentation SHALL match the
released packaging: dependencies that are conditional in the release (such
as the OpenSCAD binary and the mesh engine on the faceted path) SHALL be
described as conditional with the condition named, hard dependencies (such
as molejo) SHALL NOT be described as optional or unpublished, and an upgrade
that requires reinstalling the environment SHALL be called out where an
existing user would look for it.

#### Scenario: An all-exact project

- **WHEN** a reader whose parts are all OCCT-backed reads the quickstart
- **THEN** they learn the OpenSCAD binary is needed only for the
  OpenSCAD-family and faceted paths, not for installing or using the
  framework

#### Scenario: Upgrading an existing environment

- **WHEN** a 0.5.x user consults the documentation before upgrading
- **THEN** they find the instruction to reinstall the environment and the
  reason the in-place upgrade fails

### Requirement: Worked examples demonstrate the released capabilities

The documentation SHALL present worked example projects whose pinned sources
actually contain what the documentation claims of them, and at least one
example SHALL demonstrate the released machine surface: declared drivers,
machine-level instructions, and flexible parts.

Each worked example SHALL live on its own page, reached from an examples
index page that embeds no model of its own, so that opening one example
loads one live model rather than every example at once.

#### Scenario: An example's description matches its pinned source

- **WHEN** a reader follows an example's source link at the documented
  pinned revision
- **THEN** every capability the example's page attributes to it is present
  in that revision's source

#### Scenario: A machine example exists

- **WHEN** a reader looks for a full-machine example
- **THEN** the documentation offers one whose root assembly declares drivers
  and instructions and whose parts include flexible leaves

#### Scenario: Opening one example loads one model

- **WHEN** a reader opens the page of a worked example
- **THEN** that page embeds exactly one live model, and no other worked
  example's model is loaded by it

#### Scenario: Reaching the examples

- **WHEN** a reader opens the examples index
- **THEN** it links to every worked example's page and embeds no live model
  itself

### Requirement: The release is recorded where readers are sent

The documentation SHALL carry the released version's changelog entry on its
changelog page, a release note under `docs/releases/` for each release that
has one-page announcements, and a status page that reports the released
version as released, with a roadmap that does not list shipped work as
pending.

#### Scenario: Following the status page to the changelog

- **WHEN** a reader follows the status page's link to the changelog
- **THEN** the changelog's top entry is the released version with its date

#### Scenario: Roadmap honesty

- **WHEN** a reader compares the roadmap against the released feature set
- **THEN** no roadmap item is already shipped, and deliberate deferrals
  recorded in the changelog appear as open work

