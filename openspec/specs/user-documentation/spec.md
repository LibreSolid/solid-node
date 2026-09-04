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

The examples page SHALL present worked example projects whose pinned sources
actually contain what the page claims of them, and at least one example
SHALL demonstrate the released machine surface: declared drivers,
machine-level instructions, and flexible parts.

#### Scenario: An example's description matches its pinned source

- **WHEN** a reader follows an example's source link at the documented
  pinned revision
- **THEN** every capability the examples page attributes to it is present
  in that revision's source

#### Scenario: A machine example exists

- **WHEN** a reader looks for a full-machine example
- **THEN** the examples page offers one whose root assembly declares
  drivers and instructions and whose parts include flexible leaves

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

### Requirement: The declarative authoring surface is documented

The documentation SHALL include a page on declaring a machine that covers
the three layers of a value (parameter, constant, port), the parameter
kinds and the dimension algebra including the `solid_node.math` functions,
derived formulas, class-body child declarations, literal lists and
`repeat`, a class-body list comprehension over module-level values, an
internal `render()` that positions and returns nothing, `omit()`, root
overrides from Python and from `--set` on the command line, a parameter
without a default, `check()` for guards over several parameters, the
lifecycle split — `render()` builds the machine at rest and places what
does not move, `simulate()` reads drivers, time and ports and moves what
does, motion composing innermost — the deprecation of driver reads in
`render()` with the warning a reader will see, and the two pitfalls:
class-level names are invisible to a class-body comprehension, and
structure that depends on time. It SHALL NOT recommend placement in
`__init__`. It SHALL state that a driver cannot be qualified on a repeated
or list-held child and that ports are the drive path for identical units.

Every example that declares a parameter SHALL import the kinds from the
dedicated build-parameter module, and the page SHALL state that build
parameters come from that module while node classes come from the node
package and drivers from the simulation package. The animation, driving,
assemblies, testing and API pages SHALL read
drivers and time in `simulate()`, the node-tree, assemblies, leaf-node and
CLI pages SHALL cross-reference the declaring page, and the changelog SHALL
record the lifecycle with the deprecation.

The API reference SHALL document the build-parameter module: the kinds, the
`Quantity` base a project subclasses, and the enumerator over a class's
declarations, in a section of its own beside the node, port, simulation and
testing sections.

#### Scenario: A reader learns where a kind comes from

- **WHEN** a reader looks up how to declare a parameter
- **THEN** the import line in the example names the build-parameter module,
  and the page says which module answers for parameters, for node classes
  and for drivers

#### Scenario: A reader looks up a kind in the reference

- **WHEN** a reader opens the API reference for `Length` or `Flag`
- **THEN** the reference documents it under the build-parameter module, with
  the module's import path stated in the section

#### Scenario: A reader replaces an `__init__`

- **WHEN** a reader who knows the constructor form looks up how to declare
  a leaf's parameters
- **THEN** the page shows the declared form beside the constructor form it
  replaces, states that identity is derived by the framework, and shows the
  value read back as a plain number in `render()`

#### Scenario: A reader repeats a unit

- **WHEN** a reader needs eight identical parts placed differently
- **THEN** the page shows `repeat` with per-unit placement in `render()`
  through `enumerate` and constants, states that the units share one
  artifact, and warns that a class-body list comprehension cannot see
  class-level names while one over a module-level table declares

#### Scenario: A reader guards two parameters against each other

- **WHEN** a reader has a rule that one declared dimension must exceed
  another
- **THEN** the page shows `check()` raising for the bad pair, states when
  the framework calls it and that a refused instance realizes no child,
  and that it is not called on a class that declares nothing

#### Scenario: A reader places a stationary part

- **WHEN** a reader asks where a once-only placement goes
- **THEN** the page shows it in `render()`, shows the moving part's
  operation in `simulate()`, states that the framework runs `render()`
  once and `simulate()` per instant, and that motion composes inside the
  rest placement

#### Scenario: A reader varies a design from the shell

- **WHEN** a reader wants to build the model at another size
- **THEN** the CLI page shows `--set name=value`, how a value is parsed by
  its kind, and what happens for a parameter with no default

#### Scenario: A reader migrates a render that reads time

- **WHEN** a reader's build prints the deprecation warning
- **THEN** the page shows the warning, the `render()` that caused it, and
  the same class with the read and its operations moved to `simulate()`

