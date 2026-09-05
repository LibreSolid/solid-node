## ADDED Requirements

### Requirement: The comparison kernels are documented

The testing page SHALL explain that a test run compares on one of two
kernels: the exact boundary-representation kernel, the default and the one a
release or CI run uses, and the faceted kernel, which answers every geometric
question on the parts' meshes at tessellation precision and is the one a
developer selects for a fast loop. It SHALL state how the kernel is selected
(`--exact` / `--faceted`, else `SOLID_TEST_KERNEL`, else exact), that a
checkout's ignored `.env` is where a developer records the faceted choice so
CI inherits nothing, what the volume epsilon absorbs and that it exists only
for the faceted kernel, and that a faceted run labels itself. The CLI page
SHALL list the three options under `solid test` and the two environment
variables. The changelog SHALL record the capability.

#### Scenario: A developer learns how to run fast

- **WHEN** a reader whose suite is slow on exact solids reads the testing page
- **THEN** they find the faceted kernel, the `.env` line that selects it for
  their checkout, and the statement that CI keeps the exact kernel

#### Scenario: A reader looks up the flags

- **WHEN** a reader looks up `solid test` on the CLI page
- **THEN** they find `--exact`, `--faceted`, `--volume-epsilon`, and the two
  environment variables with their precedence
