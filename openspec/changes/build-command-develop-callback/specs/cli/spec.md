## ADDED Requirements

### Requirement: Build command
The system SHALL provide `solid build <path>` as a node-scoped command using
the command-first grammar and the shared directory-to-`__init__.py` path
resolution.

#### Scenario: Build command appears in CLI help
- **WHEN** a user runs `solid -h`
- **THEN** the command list includes `build`

### Requirement: Callback mode validation
The `solid develop` command SHALL accept `--callback URL` only in its normal
web mode.  It SHALL reject combinations of `--callback` with `--openscad` or
`--web-dev` with a clear argument error.  `solid build` SHALL NOT accept a
callback option.

#### Scenario: Callback requested for OpenSCAD mode
- **WHEN** a user runs `solid develop root --openscad --callback URL`
- **THEN** the command exits with a clear argument error before starting
development processes

#### Scenario: One-shot build receives callback option
- **WHEN** a user runs `solid build root --callback URL`
- **THEN** argument parsing rejects the unsupported option
