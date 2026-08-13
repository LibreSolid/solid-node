## MODIFIED Requirements

### Requirement: OpenSCAD GUI viewer

The system SHALL alternatively open a project in OpenSCAD with
`solid develop --openscad`, retaining its existing PID lifecycle behavior.

Opening the GUI viewer is one of the paths that require the OpenSCAD binary
under the `openscad-dependency` capability. When the flag is given and the
binary is unavailable, the system SHALL report that the OpenSCAD viewer was
requested and the binary is missing, rather than failing at the subprocess
launch. It SHALL NOT open the web viewer in its place; the web viewer runs
because it was not suppressed, never as a stand-in for a viewer that could not
start.

`solid develop` without `--openscad` SHALL NOT require the binary, so a
project whose model is exact develops with the web viewer and no OpenSCAD
installed.

#### Scenario: Viewer already open

- **WHEN** develop restarts while the recorded OpenSCAD PID is alive
- **THEN** it does not open a second window

#### Scenario: The viewer is requested without the binary

- **WHEN** `solid develop --openscad` runs and no `openscad` is on the PATH
- **THEN** it reports the requested viewer and the missing binary, and does
  not silently continue with only the web viewer

#### Scenario: Developing an exact project without OpenSCAD

- **WHEN** `solid develop` runs on an all-exact project with no `openscad` on
  the PATH and no `--openscad` flag
- **THEN** the build and the web viewer run normally and the binary is never
  required
