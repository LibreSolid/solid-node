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

The report SHALL also carry `documentVersions`, the list of node-tree
document schema versions the installed viewer renders, so a framework channel
that is about to publish or photograph a document can ask the fact it needs
rather than infer it from an unrelated counter. A report that does not carry
the field SHALL be read as `[1, 2, 3, 4]` — the versions every viewer
released before the field existed renders — so an older viewer beside a newer
framework keeps working and is described truthfully.

#### Scenario: The report says which documents the viewer renders

- **WHEN** a program runs the framework's viewer report against an
  installation whose viewer declares the document versions it renders
- **THEN** the result carries that list beside the bundle path, the export
  page, the API version and the package version

#### Scenario: A viewer that predates the field

- **WHEN** the framework resolves an installed viewer whose report carries no
  document-version list
- **THEN** the framework treats it as rendering versions 1 to 4, and says so
  wherever it names what the viewer can read

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
