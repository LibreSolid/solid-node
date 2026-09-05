# Sphinx Embedding

## MODIFIED Requirements

### Requirement: Export asset pipeline

At `html-collect-pages` the system SHALL copy each referenced export
directory into `<outdir>/_solid_node/<dest>` and complete any missing widget
files (`index.html`, `solid-widget.js`) from the installed viewer package, so
widget-less committed exports still render; the per-document export registry
SHALL survive incremental and parallel builds (purge/merge handlers). When an
export lacks widget files and no viewer package is installed, the build SHALL
fail naming `pip install "solid-node[viewer]"`.

#### Scenario: Committed widget-less export

- **WHEN** a repo commits only `manifest.json` and `models/` for an embed
- **THEN** the docs build fills in the widget files from the installed
  solid-node-viewer package and the embed works

#### Scenario: Widget-less export without the viewer

- **WHEN** a widget-less export is embedded and the viewer package is not
  installed
- **THEN** the build fails naming the extra rather than emitting an iframe
  onto a page that cannot render
