# viewer-package delta: driver-aware viewer

## ADDED Requirements

### Requirement: A host reads and drives the document's drivers

The mounted viewer SHALL hold one driver state per mount, keyed by the
document's qualified driver ids and initialized from the `drivers`
table's declared defaults, in native driver units. The handle SHALL
expose `drivers()` (the table's entries verbatim: id, default, range,
unit, dtype, scale), `driver(id)` (the current native value),
`setDriver(id, value)` (bind and re-evaluate; an unknown id SHALL fail
loudly listing the known ids; declared `range` SHALL NOT clamp), and
`onDriverChange(fn)` (called once per changed driver per animation
frame while values change and synchronously on `setDriver`; returns an
unsubscribe function). A driver change SHALL re-evaluate only
operations whose expressions reference that driver's id; operations
referencing `$t` SHALL keep animating with the existing time
transport, including expressions referencing both.

#### Scenario: A slider-shaped call moves one carriage

- **WHEN** a host calls `setDriver('x_axis.motor', 8000)` on a mounted
  two-axis document
- **THEN** operations referencing `x_axis.motor` re-evaluate to the
  new pose that frame, operations referencing only `y_axis.motor` or
  only `$t` are not re-evaluated because of it, and
  `driver('x_axis.motor')` reports 8000

#### Scenario: Out-of-range values bind unclamped

- **WHEN** a host sets a driver past its declared range (a crash
  scenario drives past travel)
- **THEN** the value binds verbatim and the pose follows it

#### Scenario: An unknown id fails loudly

- **WHEN** a host calls `setDriver('z_axis.motor', 0)` on a document
  declaring only `x_axis.motor` and `y_axis.motor`
- **THEN** the call fails naming the unknown id and listing the
  declared ids, and no state changes

#### Scenario: A driver whose name shadows a word is not confused

- **WHEN** a document declares a driver named `total` and an operation
  expression calls a function whose name contains that word
- **THEN** only operations in which `total` is a free variable of the
  parsed expression re-evaluate when it changes — detection is by
  parsed free variables, never substring matching

### Requirement: A host triggers declared instructions

The handle SHALL expose `instructions()` (the document's instruction
entries verbatim: qualified name, design-unit targets keyed by
qualified driver id, duration) and `trigger(name)`. Triggering SHALL
convert each target to native units through the driver table's scale
and dtype exactly as the Python simulation does (nearest native unit
for integer dtypes) and ramp each target driver linearly from its
current value over the instruction's duration, advanced by the
viewer's animation loop on wall-clock elapsed time: intermediate
values are sampling, endpoints are contract — integer-dtype values
SHALL be whole at every frame and the final value SHALL be exactly the
converted target. Triggering an instruction whose target driver
already has an active ramp SHALL replace that ramp from the current
value. `trigger` SHALL return a handle with `done` (a promise
resolving when every target lands or the run is cancelled) and
`cancel()` (stop ramps at their current values). An unknown
instruction name SHALL fail loudly listing the known qualified names.
Disposing the viewer SHALL cancel active ramps.

#### Scenario: A button-shaped call homes one axis

- **WHEN** a host calls `trigger('x_axis.Home')` (target 0.0 mm over
  2.0 s, driver scale 0.0125 mm/µstep, dtype int)
- **THEN** `x_axis.motor` ramps from its current value to exactly 0
  native µsteps as the duration elapses, `y_axis.motor` holds, every
  intermediate value is a whole number, and `done` resolves at landing

#### Scenario: Re-triggering replaces the active ramp

- **WHEN** an instruction is triggered while a prior trigger on the
  same driver is mid-ramp
- **THEN** the new ramp starts from the driver's current value and the
  prior run's `done` resolves without landing on its old target

#### Scenario: An unknown instruction fails loudly

- **WHEN** a host triggers a name the document does not declare
- **THEN** the call fails listing the declared qualified instruction
  names and no driver changes

### Requirement: Client evaluation matches producer numerics

The viewer's expression evaluation — OpenSCAD degree trig, `^` as
exponentiation, `$t`, and qualified driver ids resolved through the
driver map — SHALL match the producer's numeric resolution of the
same expressions to within floating-point rounding, and that agreement
SHALL be enforced by tests against the shipped evaluator module using
producer-computed expected values covering at least: linear and scaled
driver terms, degree-trig chains, `^` terms, expressions mixing `$t`
with drivers, and design-to-native instruction target conversion for
integer dtypes.

#### Scenario: The parity corpus pins the shipped evaluator

- **WHEN** the widget test suite runs the producer-generated parity
  fixture against the shipped evaluator
- **THEN** every expression's client value matches the producer value
  within float rounding, and removing the `^` rewrite makes the suite
  fail

## MODIFIED Requirements

### Requirement: One loader reads either published document

The viewer SHALL render either portable `manifest.json` or normal-build
`viewer.json`, reading their shared fields. A document whose `drivers`
table is empty SHALL render exactly as a version 1 document. A document
whose `drivers` table is non-empty SHALL load and render at the pose its
expressions evaluate to under the table's declared defaults, with driver
and instruction entries exposed through the handle's driving API. A
document whose expressions reference a qualified id absent from its
`drivers` table is malformed and SHALL fail loudly naming the id. The
host supplies the document URL
and an optional mesh base; the base defaults to the document's directory, which
for a document URL naming no directory is the directory the document is served
from and never the server root. A fetch or parse failure SHALL name the
document and the reason.

#### Scenario: A build snapshot rooted elsewhere

- **WHEN** a host mounts a `viewer.json` with a mesh base unrelated to its
  document URL
- **THEN** models load from that base with the same tree, colours, and
  animation as the equivalent export

#### Scenario: A self-contained export

- **WHEN** a host mounts an export without supplying a mesh base
- **THEN** its model paths resolve beside the manifest and it renders

#### Scenario: An export served under a subpath

- **WHEN** a host mounts a document URL that names no directory, as the shipped
  export page does with `manifest.json`, and the page is served under a
  subpath rather than at the server root
- **THEN** model paths resolve beside that document under the same subpath, and
  no request is made to the server root

#### Scenario: An unreachable document

- **WHEN** the source document cannot be fetched
- **THEN** mounting fails with an error naming the document and failure

#### Scenario: A driver document renders at its defaults

- **WHEN** a host mounts a document whose `drivers` table declares
  `x_axis.motor` with default 8000
- **THEN** the model renders at the pose its expressions evaluate to
  with `x_axis.motor = 8000`, and no error is raised

#### Scenario: A malformed driver document is refused

- **WHEN** a mounted document's expressions reference a qualified id
  its `drivers` table does not declare
- **THEN** mounting fails naming that id rather than rendering a wrong
  pose
