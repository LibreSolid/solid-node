# Viewer Distribution

## REMOVED Requirements

### Requirement: Distributions carry a built viewer bundle
**Reason**: solid-node no longer contains the viewer. The bundle is carried by the `solid-node-viewer` distribution, whose own `viewer-distribution` capability specifies how it is built into wheels and source distributions.
**Migration**: Install the viewer with `pip install "solid-node[viewer]"`. Wheels and source distributions of solid-node contain no JavaScript and building them needs no npm.

## MODIFIED Requirements

### Requirement: An installed framework reports its viewer

The framework SHALL report, to a program that does not import it, the
filesystem path of the installed viewer bundle and the integer API version the
viewer declares, as one machine-readable result on standard output, together
with the absolute path of the viewer's standalone export page and the
installed viewer package version. The reported paths SHALL be absolute and
SHALL exist. When no viewer is installed, the framework SHALL instead report a
failure that names the remedy — installing the `viewer` extra — and SHALL
exit non-zero.

#### Scenario: A host asks an installed framework for the viewer

- **WHEN** a program runs the framework's viewer report against an installation
  with `solid-node-viewer` installed
- **THEN** it receives, on standard output, the absolute path of an existing
  bundle file, the export page, the declared viewer API version and the viewer
  package version, and the process exits zero

#### Scenario: A host asks an installation that has no bundle

- **WHEN** a program runs the viewer report against an installation without
  `solid-node-viewer`
- **THEN** the process exits non-zero, standard output carries no result, and
  the message names `pip install "solid-node[viewer]"`

### Requirement: One answer about the bundle across framework channels

Every framework channel that needs the viewer — the viewer report, static
export, documentation embedding, the development viewer and the web snapshot
renderer — SHALL resolve it from the same lookup of the installed viewer
package and SHALL name the same remedy when it is absent: installing the
`viewer` extra. Documentation embedding SHALL continue to resolve the bundle
without loading the CAD runtime.

#### Scenario: Export and documentation embedding disagree about nothing

- **WHEN** the viewer is absent and an export and a documentation build each
  report it
- **THEN** both name the same remedy

#### Scenario: A documentation build stays free of the CAD runtime

- **WHEN** a documentation build completes an export that was made without
  viewer files
- **THEN** it copies the bundle from the installed viewer package without
  importing the framework's CAD runtime

## ADDED Requirements

### Requirement: The viewer is an optional extra

The framework SHALL declare the `viewer` extra, installing the
`solid-node-viewer` distribution, and the `web-snapshot` extra, installing
`solid-node-viewer[snapshot]`. The framework's own dependencies SHALL NOT
include the viewer, and every framework operation that does not open, embed
or photograph through the browser viewer SHALL work in an installation
without it.

#### Scenario: A plain installation is complete

- **WHEN** `pip install solid-node` runs without the extra
- **THEN** building, testing, exporting without the widget, snapshotting
  through OpenSCAD and developing with the OpenSCAD viewer all work

#### Scenario: The extra brings the viewer

- **WHEN** `pip install "solid-node[viewer]"` runs
- **THEN** `solid viewer` reports the installed bundle and `solid develop`
  opens the web viewer by default

### Requirement: The framework finds the installed viewer through its entry point

The framework SHALL locate the viewer by loading the `solid_node.viewer`
entry point group and calling its `bundle` entry, which returns the bundle
path, the export page, the declared API version and the package version. The
framework SHALL import no other code of the viewer package. When the group
has no entry, the viewer is not installed.

#### Scenario: The lookup runs no viewer code beyond the entry point

- **WHEN** the framework resolves the installed viewer
- **THEN** the viewer's rendering, serving and capturing modules are not
  imported into the framework's process

#### Scenario: A viewer that is installed but has no built bundle

- **WHEN** the entry point raises because its installation carries no bundle
- **THEN** the framework reports the viewer package's own remedy rather than
  its missing-extra remedy

### Requirement: The framework uses the viewer only as a process

Beyond the lookup, the framework SHALL use the viewer only by running the
viewer package's command line as a separate process, through the interpreter
running the framework: `serve --build-dir` for the development viewer and
`capture` for the web snapshot. The framework SHALL NOT import the viewer's
server or capture code.

#### Scenario: The interpreter's own viewer is the one used

- **WHEN** a different `solid-node-viewer` executable appears earlier on the
  PATH than the one installed beside the running interpreter
- **THEN** the framework still runs the viewer installed beside its interpreter
