## MODIFIED Requirements

### Requirement: An intersection verdict is computed once per run

The shared `(is_empty, volume)` helper SHALL answer from a per-run cache when
it is asked a comparison it has already decided, and SHALL compute a verdict
only for a comparison it has not.

A comparison's cache key SHALL identify everything the verdict depends on and
nothing else:

- the identity of each compared solid's geometry, under the same
  `(file, mtime)` identity the per-STL cache already uses, so a rebuilt part
  is a different key rather than a stale hit;
- the pair's RELATIVE placement — one node's composed world matrix inverted
  and applied to the other's — QUANTISED to the run's placement quantum;
- the run's placement quantum itself, so entries made under two different
  quanta in one process can never serve one another;
- the evaluation path taken (exact, faceted, or the `.mesh` fallback), so a
  pair is never served an exact answer from a faceted entry or the reverse.

The relative placement is sufficient because intersection emptiness and volume
are invariant under a common rigid transform: two solids moved together share
exactly the volume they shared before. A repeated key is therefore provably
the same verdict, and reusing it SHALL NOT change any assertion's outcome,
message, or epsilon semantics. This is a recomputation shortcut of the same
kind as the AABB broad phase, not a new tolerance on any assertion.

The quantised placement SHALL be built from the INTEGER cell indices of the
relative matrix — each entry divided by the quantum and rounded to the nearest
integer — and SHALL NOT be built from rounded floating-point values, so that
`-0.0` and `0.0` fall in one cell and two placements are one question exactly
when their integers are equal. A quantum of `0` SHALL restore the exact bytes
of the relative matrix as the placement term, keying the memo precisely as it
was keyed before the quantum existed. A relative matrix carrying a non-finite
entry SHALL yield no key, and its comparison SHALL be computed as an
uncacheable one.

Quantisation SHALL merge only placements that are indistinguishable at the
scale the run models: two relative matrices sharing a cell differ per entry by
less than the quantum `q`, so for a part of extent `L` from its own origin
every point of one solid in the other's frame moves by at most `3qL + √3 q`.
At the default quantum that bound is nanometres at metre scale. The failure
direction SHALL be a miss: two placements that straddle a cell boundary key
differently and are recomputed, exactly as they are today, so quantisation can
only add cache hits and never widens a verdict at a boundary.

Quantisation SHALL apply ONLY to the verdict key. The geometry a comparison is
handed SHALL still be placed by its own exact matrix, the exact placement and
bounding-box caches SHALL keep their exact keys, and the world-AABB broad phase
SHALL keep reading the real matrices.

The cache SHALL be keyed independently of which assertion asked, so the
animation sweep, the pairwise sweep, the whole-assembly interference
assertion and the perturbation assertions share one another's answers for the
same pair in the same relative placement.

A node whose geometry has no stable identity — a test double exposing only
`.mesh`, or a flexible leaf evaluating its current binding — SHALL NOT be
cached, and its comparisons SHALL be computed exactly as they are today.

#### Scenario: A repeated comparison is not recomputed

- **WHEN** an assertion compares the same two solids in the same relative
  placement a second time within one run
- **THEN** the verdict returned equals the first verdict exactly, and no
  boolean is run by either kernel

#### Scenario: A moved pair is recomputed

- **WHEN** two solids are compared, then one is placed differently relative
  to the other, and they are compared again
- **THEN** the second comparison runs its boolean and returns the verdict for
  the new placement

#### Scenario: A pair moved together is not recomputed

- **WHEN** two solids are compared, then BOTH are placed by the same
  additional rigid transform and compared again
- **THEN** the verdict is served from the cache and equals the first verdict

#### Scenario: A pair carried together through a parent is not recomputed

- **WHEN** two solids are compared, then both are carried by the same parent
  rotation composed so that their relative matrix differs from the first by
  float noise far below the run's placement quantum, and they are compared
  again
- **THEN** the verdict is served from the cache and no boolean is run

#### Scenario: A pair displaced by more than the quantum is recomputed

- **WHEN** two solids are compared, then one is displaced relative to the
  other by more than the run's placement quantum, and they are compared again
- **THEN** the second comparison runs its boolean and returns the verdict for
  the new placement

#### Scenario: A zero quantum restores the exact key

- **WHEN** a run's placement quantum is `0` and two solids are compared, then
  carried together so that their relative matrix differs only by float noise,
  and compared again
- **THEN** the second comparison runs its boolean, as it does under the
  exact-bytes key

#### Scenario: Signed zero does not split a cell

- **WHEN** two comparisons of the same pair produce relative matrices whose
  corresponding entries are `-0.0` and `0.0`, with a nonzero quantum
- **THEN** the second comparison is served from the cache

#### Scenario: The exact kernel quantises too

- **WHEN** an exact run compares a pair of exact solids twice at relative
  placements that differ by less than the placement quantum
- **THEN** the second comparison is served from the cache and no OCCT boolean
  is run

#### Scenario: A rebuilt part invalidates its entries

- **WHEN** a solid's geometry file is rebuilt and a comparison that involved
  it is repeated
- **THEN** the comparison is recomputed against the new geometry

#### Scenario: Flush contact keeps its verdict through the cache

- **WHEN** a flush abutment that reports non-empty with exactly 0.0 mm³ is
  compared twice
- **THEN** both comparisons report non-empty with 0.0 mm³, and the strict
  `volume_epsilon=0` default still reports the foul

#### Scenario: A node without stable geometry identity is not cached

- **WHEN** a comparison involves a node exposing only `.mesh`
- **THEN** the comparison is computed as it is today and no cache entry
  serves a later comparison in its place

#### Scenario: The placed geometry is not quantised

- **WHEN** the same solid is compared at two relative placements differing by
  less than the placement quantum
- **THEN** each comparison that runs is handed geometry placed by its own
  exact matrix, and the exact placement cache keys those placements on their
  exact matrix bytes

### Requirement: Run-level comparison kernel

The test framework SHALL hold one comparison kernel per run, `exact` or
`faceted`, one volume epsilon in mm³, and one placement quantum in mm,
together the run's comparison policy. The kernel is a property of the run,
never of the model: a node's `exact` attribute SHALL keep reporting whether
its geometry is exact, and neither the build nor any artifact SHALL depend on
the kernel a test run selects.

`solid test` SHALL resolve the kernel from the mutually exclusive `--exact` /
`--faceted` flags, else from the `SOLID_TEST_KERNEL` environment variable
(`exact` or `faceted`; any other value is an error naming the variable), else
`exact`. It SHALL resolve the epsilon from `--volume-epsilon`, else from
`SOLID_TEST_VOLUME_EPSILON`, else `0.0`; a negative value is an error. The
epsilon exists only for the faceted kernel: `--volume-epsilon` together with
an exact run is an error saying the exact kernel has nothing to absorb, and
`SOLID_TEST_VOLUME_EPSILON` is not read under the exact kernel. The
environment is the project's, loaded through the CLI's `.env` rule, so a
setting in an ignored checkout-local `.env` selects the kernel for every run
in that checkout and nowhere else.

It SHALL resolve the placement quantum from `--placement-quantum`, else from
`SOLID_TEST_PLACEMENT_QUANTUM`, else the framework's default of `1e-9` mm. A
negative or non-finite value is an error naming the flag or the variable; an
environment value that is not a number is an error naming
`SOLID_TEST_PLACEMENT_QUANTUM` and saying it is a length in mm. Unlike the
volume epsilon, the placement quantum SHALL apply under BOTH kernels and
SHALL be accepted by the exact kernel, because it identifies a question and
not a quantity of material, and both kernels' verdicts pass through the same
memo. A quantum of `0` SHALL be accepted and SHALL mean the exact-bytes key.

Outside `solid test` — a `ScenarioTest` under pytest, an assertion driven
directly — the framework SHALL resolve the same policy from the environment
at the first comparison of the process, with the same defaults and the same
errors.

Under the exact kernel every assertion behaves as specified elsewhere in
this capability. Under the faceted kernel every intersection, containment,
connectivity and weld question SHALL be answered from the compared nodes'
meshes exactly as it is answered today for a node that is not exact, and the
verdicts of the shared intersection helper SHALL have the run's epsilon
applied before any assertion reads them.

A run at the default placement quantum SHALL produce exactly the output it
produces today: no announcement, and no change to the summary line. A run at
any other placement quantum SHALL name it on the summary line, after the
preserved summary prefix and beside the faceted label when both apply.

#### Scenario: The default run is the exact run

- **WHEN** `solid test` runs with no kernel flag and no `SOLID_TEST_KERNEL`
- **THEN** every comparison of two exact nodes uses the boundary-representation
  kernel and the run's output is unchanged

#### Scenario: A checkout selects the faceted kernel once

- **WHEN** the project's `.env` contains `SOLID_TEST_KERNEL=faceted` and
  `solid test` runs without a kernel flag
- **THEN** every comparison uses the faceted path and the run says so

#### Scenario: A flag overrides the environment

- **WHEN** `SOLID_TEST_KERNEL=faceted` is set and `solid test --exact` runs
- **THEN** the run uses the exact kernel and prints no kernel line

#### Scenario: An epsilon offered to the exact kernel is refused

- **WHEN** `solid test --exact --volume-epsilon 0.5` or
  `solid test --volume-epsilon 0.5` with no faceted selection is run
- **THEN** the command exits with an error saying the exact kernel has nothing
  for an epsilon to absorb, before any node is built

#### Scenario: An unknown kernel name is refused

- **WHEN** `SOLID_TEST_KERNEL=fast` is set
- **THEN** `solid test` exits with an error naming the variable and the two
  accepted values

#### Scenario: The default placement quantum needs no selection

- **WHEN** `solid test` runs with no `--placement-quantum` and no
  `SOLID_TEST_PLACEMENT_QUANTUM`
- **THEN** the run's policy carries the framework's default quantum and the
  run's output is byte-for-byte what it is without this option

#### Scenario: A quantum offered to the exact kernel is accepted

- **WHEN** `solid test --exact --placement-quantum 1e-6` runs
- **THEN** the run compares on the exact kernel with that quantum, and no
  error is raised

#### Scenario: A checkout selects a placement quantum

- **WHEN** the project's `.env` contains `SOLID_TEST_PLACEMENT_QUANTUM=1e-6`
  and `solid test` runs without the flag
- **THEN** the run's policy carries `1e-6` mm

#### Scenario: The quantum flag beats the environment

- **WHEN** `SOLID_TEST_PLACEMENT_QUANTUM=1e-6` is set and
  `solid test --placement-quantum 0` runs
- **THEN** the run's policy carries `0` and the memo keys on exact matrix
  bytes

#### Scenario: A negative or non-finite quantum is refused

- **WHEN** `solid test --placement-quantum -1` runs, or
  `SOLID_TEST_PLACEMENT_QUANTUM=-1` is set, or `solid test
  --placement-quantum inf` runs, or `SOLID_TEST_PLACEMENT_QUANTUM=nan` is set
- **THEN** the command exits with an error naming the flag or the variable,
  before any node is built

#### Scenario: A non-numeric quantum in the environment is refused

- **WHEN** `SOLID_TEST_PLACEMENT_QUANTUM=tight` is set
- **THEN** `solid test` exits with an error naming the variable and saying the
  value is a length in mm

#### Scenario: A non-default quantum is named on the summary line

- **WHEN** a run uses a placement quantum other than the default
- **THEN** the summary line keeps its prefix verbatim and names the quantum,
  beside the faceted label and volume epsilon when the run is faceted

#### Scenario: A faceted run of an exact project never reaches the exact stack

- **WHEN** an all-exact project is tested under the faceted kernel in a fresh
  interpreter and its build is current
- **THEN** the test framework imports no `cadquery` and reads no node's
  `shape()`, and the verdicts are those of the faceted path

#### Scenario: The model is unaware of the kernel

- **WHEN** a test reads `node.exact` under the faceted kernel
- **THEN** it reports the geometry's exactness as it does under the exact
  kernel

#### Scenario: A scenario test under pytest reads the environment

- **WHEN** a `ScenarioTest` runs under plain pytest with
  `SOLID_TEST_KERNEL=faceted` in the environment
- **THEN** its geometric assertions use the faceted path with the
  environment's epsilon
