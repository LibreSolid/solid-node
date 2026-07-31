## MODIFIED Requirements

### Requirement: Template-method render lifecycle

The system SHALL control the node lifecycle through `assemble()`, which users
do not override: render → validate → `as_scad` → `generate_scad` → optional
optimized STL import → apply queued operations. `assemble()` SHALL be
idempotent — the result is memoized and `render()` is called at most once per
instance.

When a leaf node is rigid, has `optimize = True`, and its artifact is up to
date, `assemble()` SHALL import that artifact without rendering it: `render()`
and `as_scad()` SHALL NOT run. Queued operations SHALL still be applied, and
the assembled result SHALL be the same as if the node had been rendered. A node
whose artifact is absent or stale SHALL follow the full lifecycle above.

#### Scenario: Assemble is memoized

- **WHEN** `assemble()` is called twice on the same instance
- **THEN** `render()` runs only once and the cached result is returned

#### Scenario: Optimized import of cached STL

- **WHEN** a node has `optimize = True`, is rigid, and its STL is up to date
- **THEN** `assemble()` imports the STL (`import_stl`) instead of inlining
  the SCAD model, and queued operations are applied after the import

#### Scenario: An up-to-date leaf is not rendered

- **WHEN** a rigid optimizing leaf's artifact is up to date and `assemble()` runs
- **THEN** the node's `render()` is not called and no CAD geometry is computed

#### Scenario: A stale leaf is rendered

- **WHEN** any file tracked for that leaf has changed since its artifact was written
- **THEN** `assemble()` renders the node and regenerates the artifact

### Requirement: Multi-backend leaf adapters

The system SHALL provide leaf adapters for multiple CAD backends —
`Solid2Node` (solid2/SolidPython2), `CadQueryNode`, `OpenScadNode` (with
`scad_source` and optional `module_name`), and `JScadNode` (with
`jscad_source`) — all compiled through OpenSCAD as the universal target.
Each adapter SHALL implement `as_scad()`; adapters declaring a `namespace`
(`Solid2Node`, `CadQueryNode`, `OpenScadNode`) get namespace-based render
validation, while `JScadNode` declares none and skips that check.

An adapter that produces its artifact inside `as_scad()` SHALL produce it only
when that artifact is not up to date, and SHALL return the same SCAD output in
either case.

#### Scenario: OpenSCAD source adapter

- **WHEN** an `OpenScadNode` subclass declares `scad_source` and is
  instantiated with args/kwargs
- **THEN** the referenced `.scad` module is called with those args in the
  generated SCAD, with `module_name` defaulting to the file's basename

#### Scenario: CadQuery adapter routes through STL

- **WHEN** a `CadQueryNode` is assembled
- **THEN** the CadQuery object is exported to STL and re-imported via
  `import_stl` in the SCAD output

#### Scenario: An adapter does not rewrite a current artifact

- **WHEN** `as_scad()` runs on a `CadQueryNode` or `JScadNode` whose artifact is up to date
- **THEN** no export or external renderer runs, and the returned SCAD output is unchanged
