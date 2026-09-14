## ADDED Requirements

### Requirement: A document the installed viewer cannot read is refused before the browser starts

The web renderer SHALL compare the schema version of the document it is about
to stage against the document versions the installed viewer reports it
renders, and SHALL REFUSE — naming the version the document needs, the
versions the viewer renders and the viewer's package version — before the
browser process starts, writing no image and leaving no staging directory
behind.

A capture is a one-shot: the viewer's own refusal would reach the caller as
an opaque non-zero exit from a headless page, and this capability's standing
rule is to fail with what is missing rather than substitute. It SHALL NOT
fall back to the OpenSCAD renderer, which is the same rule stated for a
missing viewer package and a missing browser.

When the installed viewer does report the version the document needs, the
capture SHALL proceed exactly as it does for any other document.

#### Scenario: A running model photographed by a viewer that cannot read it

- **WHEN** a maker runs the web renderer on a root declaring
  `time = Time.running()` in an installation whose viewer renders versions 1
  to 4
- **THEN** the command fails naming document version 5, the versions the
  viewer renders and the viewer's package version, no browser is started, no
  image is written, and no OpenSCAD render is attempted instead

#### Scenario: A viewer that can read it photographs it

- **WHEN** the same model is photographed in an installation whose viewer
  reports that it renders version 5
- **THEN** the staged document is handed to the viewer's capture and a PNG is
  written, exactly as for any other document

#### Scenario: An untimed model is unaffected

- **WHEN** a maker photographs a root declaring no time base with the web
  renderer
- **THEN** the version comparison passes and nothing about the capture
  changes
