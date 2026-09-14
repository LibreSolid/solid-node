## MODIFIED Requirements

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

It SHALL additionally WARN, without failing the build, when the embedded
manifest declares a document version the installed viewer does not report as
one it renders — naming the export, the version the manifest declares and the
versions the viewer renders. The export being embedded is a committed
artifact the documentation build does not produce and cannot change, and the
embedded widget refuses such a document in the page, visibly; the warning is
what tells the author why, at build time, without failing a docs build over
an artifact it does not own. The check SHALL read the version off the
manifest the directive already opens and SHALL NOT load the CAD runtime.

#### Scenario: Missing export

- **WHEN** the directive's argument is not a directory
- **THEN** the build fails telling the user which `solid export` command to
  run
- **WHEN** the directory exists but has no `manifest.json` or a foreign
  manifest format
- **THEN** the build fails naming the path and the expected
  `solid-node-export` format

#### Scenario: An embedded export the viewer cannot render

- **WHEN** a doc embeds an export whose manifest declares version 5 and the
  installed viewer reports that it renders versions 1 to 4
- **THEN** the build completes and warns naming the export, the declared
  version and the versions the viewer renders

#### Scenario: An embedded export the viewer can render

- **WHEN** a doc embeds an export whose version the installed viewer reports
  it renders
- **THEN** the build completes with no such warning
