# Sphinx Embedding Specification

## Purpose

The Sphinx extension that embeds exported models in documentation via the
`solid-node` directive. Part of the ADR-020 export channel; the docs build
never runs the CAD stack — it only consumes committed export artifacts.

Code: `solid_node/sphinx.py`; used throughout `docs/` (e.g. `testing.rst`),
committed exports under `docs/_exports/`.

## Requirements

### Requirement: Directive registration

The system SHALL register a `solid-node` directive when
`'solid_node.sphinx'` is added to a project's `extensions`, declaring itself
parallel-read and parallel-write safe and reporting the package version.

#### Scenario: Enabling the extension

- **WHEN** `conf.py` lists `'solid_node.sphinx'` in `extensions`
- **THEN** `.. solid-node:: <export_dir>` becomes available in that project

### Requirement: Directive arguments and validation

The directive SHALL take a required export-directory argument and options
`:height:` (default `480px`, bare numbers get `px`), `:t:` (float validated
to 0..1), and `:autoplay:` (`yes`/`no`). It SHALL fail the build with an
actionable message when the argument is not a directory (this error includes
the exact `solid export <node.py> -o <dir>` invocation to run), has no
`manifest.json`, or the manifest's `format` is not `solid-node-export` (these
two name the offending path and expected format). It SHALL also detect
two different exports colliding on one output name, and register the
manifest as a dependency so docs rebuild when the export changes.

#### Scenario: Missing export

- **WHEN** the directive's argument is not a directory
- **THEN** the build fails telling the user which `solid export` command to
  run
- **WHEN** the directory exists but has no `manifest.json` or a foreign
  manifest format
- **THEN** the build fails naming the path and the expected
  `solid-node-export` format

### Requirement: Iframe rendering

For HTML builders the directive SHALL emit a lazy-loading `<iframe>`
(width 100%, configured height, no border) pointing at
`_solid_node/<dest>/index.html`, mapping `:t:` to `?t=…` and
`:autoplay: no` to `autoplay=0` — enabling static single-pose embeds.
Non-HTML builders SHALL skip the node.

#### Scenario: Static figure in docs

- **WHEN** a doc uses `:t: 0.3` and `:autoplay: no`
- **THEN** the built page embeds the widget paused at that pose

### Requirement: Export asset pipeline

At `html-collect-pages` the system SHALL copy each referenced export
directory into `<outdir>/_solid_node/<dest>` and complete any missing widget
files (`index.html`, `solid-widget.js`) from the installed package, so
widget-less committed exports still render; the per-document export registry
SHALL survive incremental and parallel builds (purge/merge handlers).

#### Scenario: Committed widget-less export

- **WHEN** a repo commits only `manifest.json` and `models/` for an embed
- **THEN** the docs build fills in the widget files from the installed
  solid-node package and the embed works
