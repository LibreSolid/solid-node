## ADDED Requirements

### Requirement: Reusing motion does not expand all its descendants

The framework SHALL let a project compose and reuse deferred motion through
ordinary arithmetic, supported `solid_node.math` functions, ports, couplings,
transformations and flexible parameters without copying the complete expression
of an operand on each reuse. Memory used to construct these values SHALL scale
with the operations the project constructs and their operand references, not
with the number of occurrences in a fully expanded expression tree.

The guarantee SHALL hold within one law as well as across laws and consumers.
It SHALL NOT require the project to name intermediate values through a special
API, reduce controls, approximate a law or bake poses. The framework SHALL
preserve numerical order of operations and the existing supported math
semantics, including degree trigonometry and symbolic comparisons. A symbolic
value SHALL continue to refuse conversion to Python truth.

The guarantee covers framework-generated values and supported combinations
with legacy symbolic operands. Text explicitly expanded by project code or
arbitrary third-party text-building functions is outside construction's
resource guarantee; accepting that text SHALL NOT be presented as recovering
memory already spent creating it.

#### Scenario: Repeated doubling within one law

- **WHEN** a law applies `x = x + x` N times to a symbolic driver
- **THEN** construction adds a bounded number of operations and references per
  step instead of allocating the exponentially expanded text
- **AND** the value at a driver binding agrees with the original arithmetic

#### Scenario: Carry profile feeds several coordinates

- **WHEN** a composed carry law drives a piecewise profile whose result feeds
  several flexible parameters and rigid transformations
- **THEN** each use preserves the composed value without expanding its entire
  ancestry, and every consumer follows the same driver state

#### Scenario: A deep chain has little repetition

- **WHEN** a law creates and publishes a chain of 10,000 additions with changing
  literal operands
- **THEN** the framework handles that depth without a recursion failure or
  dropping expression sharing because of its own traversal stack

### Requirement: All normal consumers preserve bounded expression handling

Building, exporting, generating SCAD, collecting flexible parameters, inspecting
time dependence and reporting errors SHALL NOT materialize the fully expanded
tree of a shared framework expression. Publication SHALL account for the
reachable expressions and output slots together. SCAD output SHALL remain
bounded by the compact expressions it actually writes, even where separate
output sites carry separate self-contained copies.

Diagnostics SHALL bound the expression detail they produce before rendering
large text, rather than expanding a value and truncating afterward.

#### Scenario: Shared time reaches a flexible part

- **WHEN** animation time reaches a flexible port through shared intermediates
- **THEN** the build preserves the existing time-fed no-snapshot behavior and
  publishes the live flexible parameter without flattening its expression

#### Scenario: Unresolved driver is not mistaken for animation time

- **WHEN** a flexible port holds an unresolved driver-only expression on the
  SCAD snapshot path
- **THEN** the framework reports the existing binding error with bounded
  expression detail and does not silently omit the part as time-fed

#### Scenario: A diagnostic encounters a large shared expression

- **WHEN** an invalid use of a large shared expression must be reported
- **THEN** the error identifies the use and gives bounded expression detail
  without allocating the expression's fully expanded spelling

### Requirement: Expression processing does not retain discarded machines

After a machine and its publication are discarded, the framework SHALL NOT
retain their expression graphs through an unbounded process-wide expression
registry. Processing unrelated models repeatedly SHALL NOT accumulate the
expression data of all previously discarded models.

#### Scenario: Repeated independent publications

- **WHEN** different machine instances are built, published and discarded in
  one process
- **THEN** expression storage for discarded instances can be reclaimed and the
  live expression working set follows the still-referenced instances

### Requirement: Supported legacy expressions retain their behavior

Existing SolidPython symbolic operands SHALL remain accepted by framework
math and motion in either operand order. Recognized scalar expression text
SHALL retain its evaluation and free inputs when combined with shared values.
The framework's own compact SCAD scalar expressions SHALL be readable back into
motion processing without adding that syntax to the viewer document language.
Unrecognized legacy text SHALL retain the export capability's verbatim fallback
and warning behavior; failure to read the framework's own emitted scalar form
SHALL be reported as a framework defect.

#### Scenario: Legacy operand appears on either side

- **WHEN** a legacy SolidPython scalar is added, subtracted, divided, compared
  or otherwise combined using a supported operator with a framework symbolic
  value in either order
- **THEN** the operation preserves its original operand order and evaluation,
  and supported combinations remain publishable

#### Scenario: A legacy function wraps compact framework text

- **WHEN** a supported legacy scalar function wraps a shared framework value
  in its own symbolic text
- **THEN** the framework recovers the value and its local dependencies for
  publication without leaking SCAD-local bindings into the viewer document

#### Scenario: Explicitly expanded project text

- **WHEN** project code constructs a large raw expression string before passing
  it to the framework
- **THEN** the existing legacy-input behavior applies, but the framework makes
  no guarantee that constructing that project-owned string used bounded memory
