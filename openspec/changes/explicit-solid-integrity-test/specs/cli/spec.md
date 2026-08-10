## MODIFIED Requirements

### Requirement: New command

The system SHALL provide `solid new <name>` scaffolding a project offline from
templates packaged in the wheel. After normalizing `<name>` to an
identifier-safe package name `<package>` and deriving `<ClassName>`, it SHALL
create:

- `<package>/pyproject.toml`, declaring
  `model = "<package>.<package>:<ClassName>"`;
- `<package>/<package>/__init__.py`;
- `<package>/<package>/<package>.py`, defining the model node;
- `<package>/<package>/test_<package>.py`, defining a companion `TestCase`
  whose first and only generated test calls
  `assertNoDisconnectedSolids(self.node)`; and
- `<package>/.gitignore`.

The node module and companion test filenames SHALL use the same normalized
package name, so the existing companion-file mapping discovers the test without
a new loader convention. The generated test SHALL be ordinary project source:
visible, editable, and deletable, with no registration or automatic execution
outside `solid test`.

The command SHALL refuse to overwrite an existing target directory (exit 1)
and SHALL print next steps for entering the generated directory and running the
project.

#### Scenario: Fresh project includes its first declared test

- **WHEN** a user runs `solid new my-project` in an empty directory
- **THEN** `my_project/my_project/my_project.py`,
  `my_project/my_project/test_my_project.py`, `my_project/pyproject.toml`, and
  `my_project/.gitignore` are created with no network access
- **AND** the companion test explicitly calls
  `assertNoDisconnectedSolids(self.node)`

#### Scenario: The scaffolded test is discovered normally

- **WHEN** the user enters a freshly scaffolded project and runs `solid test`
- **THEN** the existing companion-test loader discovers
  `test_<package>.py` and the summary counts exactly the generated integrity
  test

#### Scenario: Non-test commands do not execute the scaffolded test

- **WHEN** a freshly scaffolded project is run with `solid build`,
  `solid develop`, or `solid snapshot`
- **THEN** the generated test is not discovered or executed

#### Scenario: Existing target is preserved

- **WHEN** the normalized target directory already exists
- **THEN** `solid new` exits 1 without overwriting it
