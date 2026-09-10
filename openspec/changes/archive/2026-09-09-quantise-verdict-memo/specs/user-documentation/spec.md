## MODIFIED Requirements

### Requirement: The comparison kernels are documented

The testing page SHALL explain that a test run compares on one of two
kernels: the exact boundary-representation kernel, the default and the one a
release or CI run uses, and the faceted kernel, which answers every geometric
question on the parts' meshes at tessellation precision and is the one a
developer selects for a fast loop. It SHALL state how the kernel is selected
(`--exact` / `--faceted`, else `SOLID_TEST_KERNEL`, else exact), that a
checkout's ignored `.env` is where a developer records the faceted choice so
CI inherits nothing, what the volume epsilon absorbs and that it exists only
for the faceted kernel, and that a faceted run labels itself.

The testing page SHALL also explain the run's placement quantum: that the
verdict memo asks whether two comparisons are the same question, that the
relative placement deciding that is quantised to a grid so the float noise of
composing one rigid motion by two routes does not split a question in two,
that the quantum is selected by `--placement-quantum`, else
`SOLID_TEST_PLACEMENT_QUANTUM`, else the documented default, that `0` restores
the exact-bytes key, that it applies under both kernels, and that it is a
statement about arithmetic noise and must stay far below the smallest
clearance the suite judges. It SHALL state that a run at a non-default quantum
says so on its summary line.

The CLI page SHALL list the four options under `solid test` and the three
environment variables. The changelog SHALL record the capability.

#### Scenario: A developer learns how to run fast

- **WHEN** a reader whose suite is slow on exact solids reads the testing page
- **THEN** they find the faceted kernel, the `.env` line that selects it for
  their checkout, and the statement that CI keeps the exact kernel

#### Scenario: A reader looks up the flags

- **WHEN** a reader looks up `solid test` on the CLI page
- **THEN** they find `--exact`, `--faceted`, `--volume-epsilon`,
  `--placement-quantum`, and the three environment variables with their
  precedence

#### Scenario: A reader learns what the placement quantum decides

- **WHEN** a reader whose sweep re-runs booleans on parts that move together
  reads the testing page
- **THEN** they find what the quantum merges, its default, that `0` restores
  the exact key, and that it is not a tolerance on any assertion
