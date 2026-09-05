# OpenSCAD Dependency

## ADDED Requirements

### Requirement: The default development viewer follows installation, and says so

`solid develop` without a viewer flag SHALL require the OpenSCAD binary only
when the `solid-node-viewer` package is not installed, because then the
OpenSCAD GUI is the viewer it opens. When neither the viewer package nor the
binary is available, it SHALL fail before starting any development process
with one error naming both remedies: installing the `viewer` extra, or
installing OpenSCAD. With the viewer package installed, `solid develop`
without `--openscad` SHALL NOT require the binary, so a project whose model is
exact develops with the web viewer and no OpenSCAD installed.

#### Scenario: Developing an exact project without OpenSCAD

- **WHEN** `solid develop` runs on an all-exact project with `solid-node-viewer`
  installed, no `openscad` on the PATH and no `--openscad` flag
- **THEN** the build and the web viewer run normally and the binary is never
  required

#### Scenario: Nothing to open

- **WHEN** `solid develop` runs with no viewer flag, no `solid-node-viewer` and
  no `openscad` on the PATH
- **THEN** it fails naming `pip install "solid-node[viewer]"` and OpenSCAD
  installation, and starts no builder
