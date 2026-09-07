## MODIFIED Requirements

### Requirement: New command

The system SHALL provide `solid new <name>` scaffolding a project offline from
templates packaged in the wheel. It SHALL normalize the input basename to an
ASCII Python package identifier `<package>` by replacing non-alphanumeric or
underscore characters with underscores, removing boundary underscores, and
using `project` when nothing remains. If that sanitized name starts with a
digit or is a Python keyword, the command SHALL prefix it with `project_`.
After deriving `<ClassName>` from that final package identifier, it SHALL
create:

- `<package>/pyproject.toml`, declaring
  `model = "<package>.<package>:<ClassName>"`;
- `<package>/<package>/__init__.py`;
- `<package>/<package>/<package>.py`, defining the model node;
- `<package>/<package>/test_<package>.py`, defining a companion `TestCase`
  whose generated `test_solid_integrity` calls
  `assertNoDisconnectedSolids(self.node)` and whose generated
  `test_assembly_integrity` calls `assertNoSolidInterference(self.node)`; and
- `<package>/.gitignore`.

The node module and companion test filenames SHALL use the same normalized
package name, so the existing companion-file mapping discovers the tests
without a new loader convention. The generated tests SHALL be ordinary project
source: visible, editable, and deletable, with no registration or automatic
execution outside `solid test`. The assembly test SHALL use the runner's
default testing instant and SHALL remain valid when the generated model is a
single rigid node.

The command SHALL refuse to overwrite an existing target directory (exit 1)
and SHALL print next steps for entering the generated directory and running
`solid develop`. It SHALL NOT predict a viewer kind or endpoint; the develop
command owns viewer selection, configured ports, and dependency diagnostics.

#### Scenario: Fresh project includes both declared integrity tests

- **WHEN** a user runs `solid new my-project` in an empty directory
- **THEN** `my_project/my_project/my_project.py`,
  `my_project/my_project/test_my_project.py`, `my_project/pyproject.toml`, and
  `my_project/.gitignore` are created with no network access
- **AND** the companion test explicitly calls
  `assertNoDisconnectedSolids(self.node)` and
  `assertNoSolidInterference(self.node)` in separate named tests

#### Scenario: The scaffolded tests are discovered normally

- **WHEN** the user enters a freshly scaffolded project and runs `solid test`
- **THEN** the existing companion-test loader discovers `test_<package>.py`
  and the summary counts exactly the two generated integrity tests
- **AND** both pass for the generated single-rigid-node model

#### Scenario: Non-test commands do not execute the scaffolded tests

- **WHEN** a freshly scaffolded project is run with `solid build`,
  `solid develop`, or `solid snapshot`
- **THEN** the generated tests are not discovered or executed

#### Scenario: Existing target is preserved

- **WHEN** the normalized target directory already exists
- **THEN** `solid new` exits 1 without overwriting it

#### Scenario: Digit-leading project is made identifier-safe

- **WHEN** a user runs `solid new 3d-printer`
- **THEN** the command creates `project_3d_printer` with package
  `project_3d_printer`, class `Project3dPrinter`, and a matching manifest
- **AND** its generated source compiles, builds, and tests without edits

#### Scenario: Python-keyword project is made identifier-safe

- **WHEN** a user runs `solid new class`
- **THEN** the command creates `project_class` with package `project_class`,
  class `ProjectClass`, and a matching manifest
- **AND** its generated source compiles, builds, and tests without edits

#### Scenario: Next steps defer viewer details to develop

- **WHEN** `solid new my-project` succeeds in any viewer installation or port
  configuration
- **THEN** its next steps name the generated directory and `solid develop`
- **AND** they do not claim a browser URL or viewer kind
