# Viewer Package Specification

## Purpose

The reusable, React-free browser viewer shared by static exports and future
framework hosts.
## Requirements
### Requirement: A host mounts the viewer and receives a handle

The viewer SHALL mount into a caller-supplied container against a published tree
document and resolve to a handle. The handle SHALL expose `dispose()` (stop
rendering, release resources and empty the container), `view()` (camera position
and orbit target), `reload()` (rebuild the document while preserving the view),
`artifactChanged(path)` and `manifestChanged()` (update only what changed),
assembly inspection and navigation operations, and the declared API version.
Loading the viewer core SHALL NOT modify the document; only an explicit mount
may do so.

#### Scenario: A host unmounts a viewer

- **WHEN** a host calls `dispose()`
- **THEN** rendering stops, the container is empty, and no later frame or
  resize callback runs

#### Scenario: A host remounts and keeps the maker's viewpoint

- **WHEN** a host captures `view()`, disposes, and supplies that view to a new
  mount
- **THEN** the new viewer uses the captured camera and orbit target rather
  than fitting again

#### Scenario: A host refreshes a changed model in place

- **WHEN** a source document changes and the host calls `reload()`
- **THEN** the new tree renders while camera position and orbit target remain
  unchanged

#### Scenario: Loading the core mounts nothing

- **WHEN** a host loads the core without calling `mount()`
- **THEN** no element is created, document fetched, or container modified

### Requirement: A host updates only what changed

The handle SHALL expose two targeted updates beside `reload()`.
`artifactChanged(path)` SHALL refetch the model file at that document-relative
path and replace the geometry of every node referencing it without adding or
removing nodes. `manifestChanged()` SHALL refetch the document and reconcile the
rendered tree in place, adding and removing nodes and applying changed operations
and colour. Both updates preserve the camera, orbit target, animation clock, and
every node the document still names.

#### Scenario: One artifact changes

- **WHEN** a host calls `artifactChanged()` with one model path
- **THEN** only that model is requested and replaced

#### Scenario: The model gains and loses parts

- **WHEN** a document adds one node and removes another, and the host calls
  `manifestChanged()`
- **THEN** the added node is rendered, the removed node and its resources are
  gone, and common nodes keep their meshes

#### Scenario: A placement edit costs no fetch

- **WHEN** a document changes only operations or colour
- **THEN** `manifestChanged()` updates the render without requesting a model

### Requirement: Geometry is refetched only when its identity changes

The viewer SHALL treat geometry as current only while both its model path and
`mtime` match the values it loaded, and SHALL refetch when either differs. A
node whose geometry `artifactChanged()` has just fetched SHALL count as current
for the `manifestChanged()` that immediately follows, even though the document
it fetches names a new `mtime` for that node, because the two calls loaded the
same bytes moments apart.

#### Scenario: A parameter change moves the model path

- **WHEN** a node's model path changes with an unchanged `mtime`
- **THEN** its geometry is refetched

#### Scenario: A source edit moves the mtime

- **WHEN** a node's `mtime` changes with an unchanged model path
- **THEN** its geometry is refetched

#### Scenario: A manifest update follows the artifact update it describes

- **WHEN** `manifestChanged()` names a new `mtime` for a node whose geometry
  `artifactChanged()` already replaced
- **THEN** `manifestChanged()` does not refetch that node's geometry

### Requirement: A failed update leaves the model standing

A targeted update that cannot fetch what it needs SHALL report the failure while
leaving the rendered model and camera in place; the handle remains usable for a
later update. The viewer SHALL fetch replacements before it removes any node.

#### Scenario: An artifact fetch fails

- **WHEN** `artifactChanged()` cannot fetch its model file
- **THEN** the previous model remains displayed and a later update can succeed

#### Scenario: A document fetch fails

- **WHEN** `manifestChanged()` cannot fetch or parse the document
- **THEN** the rendered tree is unchanged

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

### Requirement: The host chooses how animation is presented

For a model with `$t` operations, the viewer SHALL present animation as an
always-visible inline play/pause and `0..1` timeline (`1/frames` step), the same
bar behind an initially collapsed accessible toggle, no controls, or externally
driven time with no controls. The host SHALL set initial time and autoplay.
Playback SHALL cycle every `frames / fps` seconds; scrubbing pauses it. Static
models SHALL present no controls.

#### Scenario: A shop floor hides the timeline until asked

- **WHEN** an animated model uses toggled presentation
- **THEN** the bar starts hidden behind a collapsed persistent toggle and the
  toggle reports its expanded state when activated

#### Scenario: A published export shows the bar

- **WHEN** an animated model uses inline presentation
- **THEN** play/pause and timeline are visible immediately

#### Scenario: A host drives time itself

- **WHEN** a host uses externally driven presentation and sets time
- **THEN** the viewer renders that pose with no controls

#### Scenario: A static model

- **WHEN** a model has no `$t` operation in any presentation mode
- **THEN** it creates no play/pause, timeline, or toggle

### Requirement: The camera fits the model unless the host restores a view

The viewer SHALL orient Z-up and, after meshes load, fit the model bounds with
orbit controls targeting its centre. A supplied view SHALL set position and
target instead, while near and far clipping continue to derive from bounds. A
host MAY additionally supply an up direction and a field of view; absent
either, the viewer SHALL keep its own Z-up orientation and default field of
view, so a host that supplies neither sees no change.

#### Scenario: A first look at a model

- **WHEN** a model mounts without a view
- **THEN** the whole model is framed and orbiting targets its centre

#### Scenario: A rebuild during a work session

- **WHEN** a model mounts with a supplied view
- **THEN** the camera is restored and the model is neither clipped nor beyond
  the far plane

#### Scenario: A host reproduces another renderer's framing

- **WHEN** a host mounts with a view, an up direction, and a field of view
- **THEN** the model is seen from that viewpoint, rolled to that up direction,
  and framed at that field of view

#### Scenario: An existing host is unaffected

- **WHEN** a host mounts without an up direction or field of view
- **THEN** the viewer frames the model exactly as it did before those options
  existed

### Requirement: Colour is inherited and falls back to a normal material

The viewer SHALL use a node colour or its nearest ancestor colour, and SHALL
use the framework's normal-based material when no colour is available.

#### Scenario: A part inherits its assembly's colour

- **WHEN** a node has no colour and an ancestor does
- **THEN** the part renders in the ancestor's colour

#### Scenario: A colourless assembly

- **WHEN** no node declares a colour
- **THEN** every model renders with the normal-based material

### Requirement: The host names the canvas for its own styles and assistive tools

The viewer SHALL apply a host-supplied CSS class, role, and accessible label to
the canvas. Absent a host choice, it SHALL add no such attributes.

#### Scenario: A shop floor labels the model view

- **WHEN** a host supplies a canvas class, role, and label
- **THEN** the canvas carries them for host styling and assistive tools

### Requirement: The viewer declares its API version

The package SHALL declare one API version, expose it on every mount handle and
the browser global, and make it readable without executing the bundle. It SHALL
be raised whenever the mount interface or handle changes incompatibly, and when
a capability a host may require is added to the handle. The declared version
SHALL be 5, reflecting the addition of flexible-geometry rendering. (The
previous baseline text recorded 3 while the shipped package declared 4 — the
driver-driving capability was raised in code without this spec syncing; this
revision records the correction alongside the new capability.)

#### Scenario: A host checks compatibility before mounting

- **WHEN** a host reads the installed viewer API version
- **THEN** it obtains the package's single declared version without running a
  browser bundle

#### Scenario: A mounted viewer reports its version

- **WHEN** a host inspects a mount handle or the browser global
- **THEN** both report the same declared API version

#### Scenario: A host requires targeted updates

- **WHEN** a host needs `artifactChanged()` and `manifestChanged()`
- **THEN** the declared API version tells it whether they are available

#### Scenario: A host requires camera orientation control

- **WHEN** a host needs to supply an up direction and field of view
- **THEN** the declared API version tells it whether they are available

#### Scenario: A host requires flexible geometry

- **WHEN** a host needs `version: 3` documents rendered
- **THEN** the declared API version tells it whether the capability is
  available

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
driver terms, degree-trig chains, `^` terms, sums whose leading term is
negative, expressions mixing `$t` with drivers, and design-to-native
instruction target conversion for integer dtypes.

Agreement SHALL include operator precedence and not only arithmetic. A
unary minus SHALL bind to the term beside it rather than to the rest of
the expression, so a sum whose leading term is negative resolves to that
negative term plus the rest and never to the negation of the whole; and
`^` SHALL bind tighter than a unary minus, as the producer's own
language does.

#### Scenario: The parity corpus pins the shipped evaluator

- **WHEN** the widget test suite runs the producer-generated parity
  fixture against the shipped evaluator
- **THEN** every expression's client value matches the producer value
  within float rounding, and removing the `^` rewrite makes the suite
  fail

#### Scenario: A sum whose leading term is negative crosses the boundary

- **WHEN** the corpus carries an expression whose head is a negative
  literal, evaluated at more than one driver setting
- **THEN** the client value matches the producer value at every one of
  them, and a reader that bound the unary minus to the whole sum instead
  would agree at no more than one

### Requirement: A maker drives the focused layer's drivers and instructions on screen

For a document that declares drivers, the mounted viewer SHALL present
an on-screen control for each driver and each instruction declared at
the focused assembly layer: a button per instruction and a bounded
slider with a numeric readout per driver. Control labels SHALL be the
declared identifiers relative to the focused layer. Sliders SHALL
present values in design units with the declared unit, and SHALL move
live while a ramp plays. A driver's readout SHALL show a fixed number
of decimal places, and SHALL hold the position of its digits, its sign,
and everything laid out beside it steady as the value changes: reading
a value while dragging SHALL not require following a moving target.
Interacting with a control SHALL produce the
same observable state as the corresponding host driving call, so a
value or trigger set on screen and one set through the handle are
indistinguishable to expressions, listeners, and readbacks. The
declared `range` SHALL bound only the slider's travel, never the
underlying value: a value bound past the range through the host API
SHALL survive intact, with the slider pinned at its end and the
numeric readout showing the true value. Every control SHALL carry an
accessible name for assistive tools. A document declaring no drivers
SHALL present none of this chrome.

#### Scenario: A maker homes an axis with a button

- **WHEN** the focused layer declares the instruction `Home` and the
  maker presses the button labelled `Home`
- **THEN** the same ramp plays as a host `trigger` of that qualified
  instruction, the affected driver's slider travels with it to the
  target, and the button indicates the run until it lands

#### Scenario: A maker jogs a motor with a slider

- **WHEN** the maker drags the slider labelled `motor` on a focused
  axis whose driver declares `unit: ustep` and a millimetre scale
- **THEN** the model pose follows the drag, the readout shows the
  design-unit value with its unit, and `driver()` on the handle
  reports the corresponding native value

#### Scenario: A readout holds still through a drag

- **WHEN** the maker drags a driver's slider through values of
  differing digit counts and across zero into negative travel
- **THEN** every value is written with the same number of decimal
  places, and neither the change of digit count nor the appearance of
  the minus sign moves the readout's digits or the unit beside them

#### Scenario: A re-pressed button replaces the run

- **WHEN** the maker presses an instruction's button while its ramp is
  still playing
- **THEN** the new run replaces the old one, exactly as a host
  re-trigger does

#### Scenario: An out-of-range value is shown honestly

- **WHEN** a host binds a driver past its declared range and the maker
  looks at that driver's control
- **THEN** the slider sits pinned at its nearest end, the readout
  shows the actual out-of-range value, and the bound value is
  unchanged by the chrome

#### Scenario: A driverless document is unchanged

- **WHEN** a document with an empty drivers table is mounted
- **THEN** no driver control, readout, or focus affordance appears and
  the widget presents exactly its pre-existing chrome

### Requirement: Controls follow the focused layer

The viewer SHALL scope driver controls strictly to the focused
assembly layer. With focus at the document root, only drivers and
instructions declared with bare (root-level) identifiers SHALL be
presented. Focusing an instance SHALL replace the controls with those
the instance itself declares, labelled relative to it; controls of its
descendants and of other branches SHALL NOT be presented. When a
document update removes the focused node and focus resets, the
controls SHALL re-scope with it. A focused layer declaring nothing
SHALL present no sliders or buttons while the focus affordance remains
available.

#### Scenario: Focusing an axis reveals its controls

- **WHEN** the maker focuses `x_axis` on a machine whose axes each
  declare a `motor` driver and a `Home` instruction
- **THEN** exactly one slider labelled `motor` and one button labelled
  `Home` appear, driving `x_axis.motor` and `x_axis.Home`, and
  `y_axis`'s controls are not shown

#### Scenario: A root that declares nothing shows no controls

- **WHEN** the maker views the root of a machine that declares all
  drivers and instructions on its children
- **THEN** no slider or button is presented at the root and the focus
  affordance still offers the declaring children

#### Scenario: A republish that removes the focused node re-scopes

- **WHEN** a document update removes the focused instance and the
  viewer resets focus to the root
- **THEN** the presented controls become the root layer's

### Requirement: The host chooses how driver controls are presented

The host SHALL be able to choose at mount time whether the driver
chrome (controls and focus affordance) is presented. By default it is
presented for documents that declare drivers. A host that suppresses
it SHALL retain the full driving API unchanged.

#### Scenario: A shop floor builds its own instrument panel

- **WHEN** a host mounts with the driver chrome suppressed
- **THEN** no on-screen driver control or focus affordance appears
  while `drivers()`, `setDriver`, `trigger`, and `onDriverChange`
  behave exactly as when the chrome is shown

#### Scenario: A published export shows the controls

- **WHEN** a maker opens a self-contained export of a driver-declaring
  document with default options
- **THEN** the driver chrome is presented

### Requirement: The viewer evaluates flexible geometry per frame

The package SHALL bundle the molejo JavaScript evaluator and render a
document's `flexible` nodes: each node's `params` expressions are
evaluated in the same scope as operation expressions (`$t` and the
nested driver map), and the resulting values are handed to the molejo
evaluator, which writes vertex data into buffers the viewer allocates
once per node and reuses — vertex count and ordering are declared by
the spec and never change at frame rate, so no reallocation occurs.

Re-evaluation SHALL be bounded the way operation re-evaluation already
is: a flexible node's geometry is recomputed only on frames where a
free variable of one of its `params` expressions changed, and driving
a driver named by no `params` expression SHALL NOT re-evaluate it.

The loader SHALL accept documents declaring `version: 2` or
`version: 3`, and SHALL refuse — naming the node and the technology —
a `flexible` node whose `tech` the package cannot evaluate, rather
than rendering a wrong or missing shape.

The binding seam SHALL be pinned by the producer-generated parity
fixture: at least one case evaluates a real flexible document's
parameter expression client-side, feeds it to the bundled molejo
evaluator, and matches the producer's Python-side evaluation of the
same spec and binding within the fixture's tolerance. (Vertex-level
agreement between the two molejo evaluators is molejo's own parity
contract; what this package pins is the expression-to-parameter
binding in front of it.)

#### Scenario: A spring animates in the browser

- **WHEN** a document containing a molejo spring whose `height`
  expression references a declared driver is mounted and that driver
  is driven
- **THEN** the spring's geometry re-evaluates into its existing
  buffers on the frames where the driver changed, with vertex count
  unchanged

#### Scenario: An unrelated driver does not touch the spring

- **WHEN** a driver named by no `params` expression of the spring
  changes
- **THEN** the spring's geometry is not re-evaluated that frame

#### Scenario: An unknown technology is refused loudly

- **WHEN** a document carries a `flexible` node whose `tech` the
  package cannot evaluate
- **THEN** loading fails naming the node and the technology, and no
  wrong shape is rendered

#### Scenario: The binding parity case pins the seam

- **WHEN** the widget test suite runs the parity fixture's flexible
  binding case against the shipped evaluator and bundled molejo
- **THEN** the client-side parameter value and resulting evaluation
  agree with the producer-computed expectation within the declared
  tolerance

