
.. _changelog:

=========
Changelog
=========

Unreleased
----------

**The whole-assembly interference index chooses its own indexing
frame.** A world-axis conservative bound is exact for an axis-aligned
part and grows under rotation; when every part in an assembly shares
one outermost rigid turn, every box grows and the index no longer sees
how sparse the assembly really is. ``assertNoSolidInterference`` now
indexes its candidate pairs in a chosen frame: the world frame, or the
placement frame of one of the assembly's largest topmost solids by
local-bounds diagonal, whichever scores the smallest total box volume,
world winning ties. A bound taken in a non-world frame is enlarged by a
small fixed margin absorbing the extra arithmetic the frame change
costs, so a flush-contact pair is never lost to it; world bounds are
never enlarged, so an assembly that gains nothing from the choice is
indexed exactly as it always was. The choice can only change which
candidate pairs are emitted, never a verdict, a message, or an epsilon.
``assertAssemblySupported``'s own bounds are unaffected and stay
world-axis, because gravity is a world-frame fact. No public surface
changes: no flag, no environment variable, no assertion argument.
(OpenSpec change ``broad-phase-indexing-frame``; ADR-091, extending
ADR-029.)

**The verdict memo absorbs float noise between two rigid motions.** A
pair carried together by a rotating parent recomposes a relative matrix
that differs from the previous instant's by float noise far below any
real placement — the residue of composing the same motion through a
different multiplication order — and the memo's exact-bytes key
(ADR-070) missed every one of those. ``solid test`` now resolves a
run-wide **placement quantum**: the relative matrix is divided by it and
rounded to integer cell indices, so two placements in the same cell are
one question. ``--placement-quantum MM`` / ``SOLID_TEST_PLACEMENT_QUANTUM``
select it, the same way as the kernel and the volume epsilon; the
default is ``1e-9`` mm, and ``0`` restores the exact-bytes key exactly.
Unlike the volume epsilon, the quantum applies under both kernels and
the exact kernel accepts it. A run at the default quantum is unchanged,
byte for byte; a non-default quantum names itself on the summary line.
(OpenSpec change ``quantise-verdict-memo``; ADR-090, amending ADR-070.)

**One coordinate can drive another.** A class body may now state a
relation between two coordinates, wherever they are in the tree::

    class Movement(AssemblyNode):
        power = TrainArbor(index=0)
        centre = TrainArbor(index=1)

        power.drives(centre, law=going_train)

``drives`` needs no import, and it is the ONLY vocabulary for relating
two coordinates: the framework looks up no method, attribute or hook of
any name on a project's class to discover what a relation means. Written
bare it is a statement, recorded on the class; assigned
(``great = power.drives(centre)``) it is additionally named, so a test
can reach it and every message about it can say its name. Either end may
be a port, a joint, a child declaration standing for its class's ONE
joint, a path through declared children (``motion_works.cannon.turn``,
``shoulder.art2.art3.wrist``), a derived coordinate, or — as the source
only — a ``Driver``, so a root driver reaches a joint at any depth
without a port forwarded at every level in between.

``drives`` states the MECHANICAL direction; which way the framework
SOLVES it is decided per run from whichever end is actually bound —
forward through the law, backward through its inverse — so a going train
written from the power arbor forwards is solved backwards from the one
arbor its ``simulate()`` bound, with nothing reordered.
``Affine(ratio, offset)``, the one new importable name in
``solid_node.motion.couplings``, is that law's usual shape, and
``ratio=``/``offset=`` on ``drives`` are its shorthand; ``law=`` takes a
CALLABLE of the two realized coordinate owners, called once per instance
at realization, so a project's own function reads the tooth counts and
the registration off the two arbors it is handed and returns the law.
Everything stays symbolic: a driver read or ``$t`` rides through a
relation into the published expressions the viewer already evaluates,
and is a plain number under ``set_state``.

A **derived coordinate** — a linear formula over coordinates, written in
the class body: ``relative_elbow = art3.elbow - shoulder``,
``left = wrist + 2 * tool`` — is itself a coordinate of the class. It
reads on an instance as a bound port slot, ``declared_ports`` reports it
under its name, it can drive and be driven, and it solves backwards
through exactly one unbound term. Anything that is not linear is a
``law=``, and a product of two coordinates is refused where it is
written.

Reading a port, a joint or another child off a child declaration in a
class body now yields a PATH REFERENCE instead of raising: naming a
place in the tree is what a declaration has always done. Reading a
declared PARAMETER sideways is still refused with the same message, and
so is reading a ``Driver``.

Three refusals keep a wrong drive network from becoming a pose, each its
own error kind exported from ``solid_node.motion.couplings`` and each
naming the node paths, the relation as written and the ends:
``UnreachedCoordinate``, ``DoublyBound`` (an author's binding, a wiring
or another relation already bound that coordinate — including two
relations that would agree, because the framework does not compare two
symbolic expressions to decide whether they do) and ``NotInvertible``.
Wirings are now solved together with the relations, in one fixpoint at
the end of the simulate phase, so a wiring whose source a relation
solves binds after it instead of refusing an unbound source; and at the
START of that phase the framework clears what it bound through a wiring
or a relation in the previous run, so each instant re-solves from the
author's fresh binding. Nothing an author's own code bound is ever
cleared. (OpenSpec change ``couplings``; ADR-089, extending ADR-061 and
ADR-066.)

**A joint says where a body may move.** ``solid_node.motion.joints`` now
holds the two one-coordinate lower pairs, ``Revolute`` and ``Prismatic``,
declared as a class attribute of the node they move:
``elbow = Revolute(axis=(0, 0, 1), at=(0, 160, 68), range=(-135, 135),
unit='deg')``. ``axis`` and ``at`` are stated in the PARENT's frame — the
frame the parent's ``render()`` places the node in, where MuJoCo and
Modelica state them too — and each component may be a number, a declared
parameter, a formula over them, or, for the whole argument, a callable of
the realized node; they resolve at realization and never enter a part's
build identity. A joint owns exactly one coordinate and that coordinate
is a port: reading the joint gives the port slot, ``declared_ports``
reports it under the joint's name, and assigning to it binds through the
one binding path ``connect()`` uses. Binding it PLACES the body: the
framework inverts the node's rest placement to carry the parent-frame
axis and anchor into the node's own frame and applies ordinary rotations
and translations there, so an axis that does not run through the moving
part's origin no longer needs the frame arithmetic every robot arm writes
by hand, and nothing new travels on the wire. A parent may hand one of
its coordinates down to a child declaration by naming a port or joint the
child declares — ``wheel = Arbor(index=index, turn=turn)`` — which is a
wiring rather than a parameter: absent from the child's parameters and
identity, rebound from the parent's end on every ``simulate()``, refused
at class definition when the child cannot receive it, and the coordinate's
one binder. A numeric binding outside a declared ``range`` raises
``JointRangeError`` naming the node, the joint, the value and the range;
a symbolic binding is not checked, because its value is not known at bind
time. Nothing is deprecated: a project goes on turning its parts by hand
in ``simulate()`` for as long as it likes, and both forms may sit on one
node. (OpenSpec change ``joints``; ADR-088, extending ADR-056 and
ADR-066.)

**Ports and the declared time base moved to a new** ``solid_node.motion``
**package.** ``solid_node.motion.ports`` is now the one home for
``Port``, ``BoundPort``, ``RotationalPort``, ``TranslationalPort``,
``SignalPort``, ``bind``, ``declared_ports``, ``Time`` and
``declared_time`` — the module that answers what moves and what drives
what, alongside the empty ``solid_node.motion.joints`` and
``solid_node.motion.couplings`` two later cycles will fill.
``solid_node.node`` no longer exports any of those six names and no
longer has ``ports`` or ``timebase`` submodules; there is no shim, alias,
or deprecation warning. ``from solid_node.node import RotationalPort,
SignalPort, Time`` now raises ``ImportError`` naming
``solid_node.motion.ports``; migrate to ``from solid_node.motion.ports
import RotationalPort, SignalPort, Time``. (OpenSpec change
``motion-package``; ADR-087, amending ADR-056 and ADR-072 on export
location only.)

**Simulation time boundaries now fail before effects.** ``Sim`` requires a
finite positive ``dt`` before binding its node, and instants, cadence periods,
run durations, and instruction durations require finite real seconds with
their declared sign and whole-tick constraints. A past absolute instant is
rejected while the current tick remains schedulable through ``run(0)``.
Zero-duration instructions now settle and bind every target immediately at
the current tick without advancing time or adding a trajectory entry.
(OpenSpec change ``validate-simulation-time-boundaries``; ADR-083.)

**New-project guidance now defers viewer details to development.** The
successful ``solid new`` message still shows how to enter the generated
directory and run ``solid develop``, but no longer promises a browser at a
hard-coded port. The development command owns viewer selection, configured
ports, and dependency diagnostics. (OpenSpec change
``make-scaffold-next-steps-viewer-neutral``.)

**A repeated subexpression is published once, not once per use.** Every
symbolic value in the framework is a solid2 ``OpenSCADConstant``, and
``OpenSCADConstant`` is string-eager: a value used twice is written out
twice, and a value reused at each of several nested levels is written
exponentially often. 3DPrintedClocks' grasshopper escapement
(``wall_clock_53_grasshopper``) found the far end of that: its published
``viewer.json`` was 31,638,555 bytes, of which 31,611,478 were operation
expression text — seven million written copies of 263 distinct
subexpressions — and the document would not animate in the browser
viewer. The export ``manifest.json`` and the normal-build ``viewer.json``
now gain an ordered top-level ``bindings`` table: a subexpression that
occurs more than once anywhere in the document's expressions is published
once, named, and referenced by name everywhere it occurred, except a bare
number or a bare driver id, which is shorter written out than referenced.
Rebuilding that same clock's document measured expression text falling
from 31,611,478 to 3,130 bytes and the document itself from 31,638,555 to
32,227 bytes, with 56 bindings published and the longest one 212
characters; every one of its 116 operation values, evaluated at three
points in the animation under the document's own OpenSCAD-degree
semantics, matched the flattened document's exactly. A document with
nothing to share is byte-identical to the one the framework has always
published. A document carrying a non-empty ``bindings`` table declares
schema **version 4**, and the bump is not additive: a consumer that
ignores ``bindings`` would resolve a reference to nothing and render a
wrong pose, so a consumer that cannot read version 4 refuses the document
rather than render it, in the same phase that already refuses an unknown
version. Sharing is detected at serialization by a new internal parser
(``solid_node/core/expressions.py``) reading the expression text the
producer already built; nothing about how a project writes kinematics, or
about solid2's own arithmetic, changes. An expression the parser cannot
read — reachable only through a hand-written ``scad_inline`` string
outside the grammar the two producers emit — is published verbatim and
unshared, with a warning, and never fails the build. The ``.scad`` path
is untouched: it reads operation and port values directly rather than
their serialized form, so generated SCAD and ``Solid2Node.as_number``'s
OpenSCAD round-trip are unaffected, and ``solid snapshot --renderer web``
keyframes and bakes constants, so it never carries a table and stays at
version 2/3 with any viewer. The producer cost is small against a CAD
build: two clean rebuilds of the grasshopper clock (STLs already current)
measured 17.6 s and 23.3 s of whole build time. **A viewer that has not
yet widened its accepted document versions to include 4 refuses a
version-4 document, loudly, in its own prepare phase, before the live
scene is touched** — until the paired ``solid-node-viewer`` change lands,
this is expected for nearly any animated model, not only a
grasshopper-sized one, because the sharing rule has no size threshold: a
subexpression as small as ``$t * loop`` reaching two operations is
already enough. (OpenSpec change ``expression-bindings``, ADR-080.)

**Empty non-rigid assemblies now build as empty groups.** A declarative repeat
resolved to zero, omission of every declared child, or an explicit empty child
list now passes through assembly and serialization as ``children: []`` and
produces no STL for the non-rigid group. A rigid fusion with no selected child
is rejected during validation because it cannot represent one solid.
(OpenSpec change ``support-empty-assemblies``; ADR-082.)

**All-model tests now continue after a model fails to build.** During
``solid test --all``, a failure while loading, constructing, keyframing,
rendering, assembling, or generating artifacts is counted once against the
declared model and the next model still runs. ``--failfast`` records that
failure before stopping, and both paths retain the command's single aggregate
report. (OpenSpec change
``continue-all-model-tests-after-build-failure``.)

**New-project scaffolds always use valid Python identifiers.** Names that
sanitize to a leading digit or Python keyword now gain a deterministic
``project_`` prefix before paths, modules, classes, and the manifest are
derived. For example, ``solid new 3d-printer`` creates
``project_3d_printer:Project3dPrinter``; established punctuation normalization
such as ``snowman-3`` to ``snowman_3:Snowman3`` is unchanged. (OpenSpec change
``normalize-scaffold-identifiers``.)

**Successful unchanged builds now clear prior failure status.** A complete
build removes ``errors.json`` after constructing its viewer document even when
those document bytes already match the published snapshot. The snapshot stays
untouched, while ``solid models`` transitions from ``failed`` to ``published``.
Development callbacks report that recovery after the build lock is released;
a true no-op with no prior error remains silent. (OpenSpec change
``clear-recovered-build-errors``.)

**Development watches now rebuild for every tracked source.** After successful
assembly, modifications to explicitly tracked OpenSCAD, JSCAD, STL, STEP, and
Python sources all end the current builder pass so the develop loop can reload
the model. The recursive recovery watch used after a failed load remains
limited to Python sources outside ``__pycache__`` to avoid rebuild noise.
(OpenSpec change ``watch-all-tracked-sources``.)

**Every tracked source now guards artifact currency.** A settled artifact must
match both the maximum source timestamp and a recorded metadata fingerprint of
each contributing file, so an edit to an older dependency cannot be hidden by
a future-dated source. Fingerprint changes invoke the existing node-scoped
content digest, preserving no-op timestamp rewrites, relocated projects, and
unrelated sibling-class edits without regenerating geometry. Legacy
digest-only sidecars validate and upgrade in place; malformed records rebuild.
(OpenSpec change ``guard-source-set-currency``; ADR-081.)

**Artifact-producing assembly now holds the project build lock.** Ordinary
builds acquire their selected build lock before assembly can materialize SCAD,
BREP, or STL files and keep it through viewer-document publication. The test
runner likewise holds one lock through keyframing, preliminary render,
assembly, and STL generation, then releases it before project tests execute.
A builder whose loaded sources change while it waits stands down before
rendering. (OpenSpec change ``lock-artifact-assembly``.)

**Static exports keep every model inside the requested output.** Model paths
are now derived from the same project-aware, selected build directory that
owns the artifacts, rather than from the command's working directory. Exporting
an explicit reference from a nested directory therefore retains the portable
``models/<source path>/<artifact>.stl`` layout. A custom node whose STL resolves
outside its build directory is rejected before the output changes, with a
controlled CLI diagnostic. (OpenSpec change ``confine-export-models``.)

**Build preparation preserves sibling data.** The one-time migration from the
retired symlink publication layout now moves only the directory referenced by
the build path. Ordinary preparation and migration leave every other
``<build>.`` sibling untouched, including user notes, backups, legacy-looking
directories, the project lock, and browser snapshot stages still being
captured. An orphan from the retired layout can therefore remain on disk when
its name is the only evidence of ownership. (OpenSpec change
``preserve-unowned-build-siblings``.)

**Failed OpenSCAD renders no longer publish empty geometry.** The asynchronous
STL render protocol now checks OpenSCAD's exit status before replacing the
published artifact. A failed render exits the build nonzero, records the
failure in ``errors.json``, removes its temporary output and render lock, and
leaves any previously published STL and viewer snapshot intact. (OpenSpec
change ``reject-failed-openscad-render``.)

**Reading a STEP document's assembly structure, and scaffolding source
from it.** ``StepAssembly(path)`` reads a document's products and every
occurrence of them, walked through nested sub-assemblies — each
occurrence's placement matrix in its parent's frame, its world matrix
composed outward, and, for every placement that is a proper rigid
transform, the exact ``(angle, axis)``/``translation`` pair that
reproduces it through the framework's own ``rotate`` then ``translate``.
The decomposition goes through OCCT's own quaternion
(``gp_Trsf.GetRotation().GetVectorAndAngle()``), never through the trace
and an ``acos``: measured over the Internal-Cycloidal-Actuator's 55
placements (27 of them exactly 180°, 2 the identity), the quaternion
route reproduces every matrix to 4.4e-16 and the trace route only to
3.0e-8 — thirty times outside the 1e-9 the contract asks, and wrong
exactly on the half-turns. A placement that is not proper — a mirror or
a scale — is reported with its determinant and scale factor and is not
decomposed, because ``rotate``/``translate`` cannot state one; the rest
of the document is unaffected. ``StepAssembly`` is not a node: it reads
through the same cached document ``StepNode`` does, so a process that
has already read a file for one pays nothing more for the other, and
reading the whole structure of the actuator's 35 MB document — 21
products, 55 occurrences — costs 0.042 s after the 11.10 s document
read is warm.

``solid import-step FILE [--into PACKAGE_DIR] [--model NAME]`` turns a
document into project-owned, declarative source in one shot: ``parts.py``
(one ``StepNode`` subclass per part, declaring ``step_source``, ``part``
and ``angular_deflection = 0.5`` under a comment) and ``assembly.py``
(one ``AssemblyNode`` per assembly product, one child declaration per
occurrence, and a ``render()`` placing each by ``rotate`` then
``translate`` at the document's own transform, under a comment naming
the occurrence and the file). The generated machine is at rest — no
driver, no ``simulate()`` — and the command never overwrites an
existing ``parts.py`` or ``assembly.py``, writes nothing when any
placement is improper, and prints the manifest lines rather than
editing ``pyproject.toml``. Born of the same two projects as ``StepNode``:
``Internal-Cycloidal-Actuator``'s design record named six placements
typed by hand into ``machine.py``, one of them (``Eccentric_Shaft``) an
axis sign that is not visible in the matrix at a glance, and a
recomposition test that existed only to check the typing; ``openvmp``
wrote the same occurrence walk against PartCAD's ``.assy`` format.
Scaffolded into a scratchpad project and built against this cycle: the
actuator document builds in 21.5 s, 20 distinct part artifacts (the
other 35 of 55 occurrences share theirs, as repeated placements of the
same product always have), 11.74 MiB of STL against the 19.91 MB one
part alone would cost at the inherited default; every one of the 55
generated leaves' composed world placements agrees with the reader's
own world matrix to within 4.93e-10 mm, the contract
``Internal-Cycloidal-Actuator``'s hand-written ``test_machine.py``
existed only to check by hand. See :ref:`import-step`. (OpenSpec change
``step-assembly-import``; ADR-079.)

**The STEP part, an exact external-file leaf.** ``StepNode`` reads one
product out of a STEP document as an ordinary part —
selected by ``part``, naming the product as the file carries it; a
document with exactly one candidate product (a bare single-part file,
or the commoner file in which an exporter wraps one part in an
assembly) needs no ``part`` at all, while a document of several never
hands its assembly root to a node by omission. A wrong or missing
``part`` fails with the document's own inventory — one line per
product, naming its kind, occurrence count, solid count, bounding box
and volume — so no separate inspection tool has to exist. The selected
geometry is always the product's own, unplaced shape, never an
occurrence's located copy; ``adjust(self, shape)`` corrects it in code,
and the module exports ``solids_from_faces(shape, tolerance)`` for
sewing a vendor part published as bare surfaces, called knowingly from
an ``adjust`` hook — a product that still holds no solid fails
admission naming the node, the file, the part and what it does hold,
and nothing is repaired silently. A subclass that declares no ``color``
takes it from the document — the product's own surface colour, else the
colour every occurrence of it agrees on, else none — converted from
XCAF's linear RGB to the sRGB the framework's ``color`` attribute
already is; a declared ``color`` wins and never opens the document. The
document is read and transferred at most once per file per process,
cached on the file's path and modification time, so several nodes over
one file share one read and a node whose artifacts are current triggers
none at all. Unlike ``StlNode``, this leaf is **exact**: it derives
``ExactLeafNode`` and so inherits ``shape()``, the ``.brep``, exact
fusion and :ref:`declared tessellation precision
<tessellation-precision>` at the same inherited defaults every exact
leaf has, whole. Born of two projects that had each written this reader
by hand — ``Internal-Cycloidal-Actuator`` (a 35 MB, 21-product Inventor
assembly) and ``openvmp`` (67 vendor STEP files) — both of which also
carried their own module-level document cache for the same reason this
leaf now has one built in. Measured on the actuator's own
``Output_Shaft`` through this leaf: 19.91 MB (398,184 triangles) at the
inherited default, against 1.76 MB (35,240 triangles) declaring
``angular_deflection = 0.5``, with an identical ``.brep`` between the
two; reading that 35 MB document costs 14 to 17 seconds once per
process, and a second node selecting from the same cached document
costs 0.0003 s. See :ref:`step-import`. (OpenSpec change
``step-part-leaf``; ADR-078.)

**Declared tessellation precision.** An exact leaf (``CadQueryNode``,
``Build123dNode``, ``Build123dSheetNode``) or a ``FusionNode`` fusing
exact children may now declare ``linear_deflection`` (mm) and
``angular_deflection`` (radians) as class attributes, shaping how finely
that node's own ``.stl`` is tessellated. A node declaring neither is
tessellated at ``linear_deflection = 0.1`` and ``angular_deflection =
0.1`` — the values the framework has always used — so an existing
project's artifacts do not change. The declaration is not a constructor
parameter and does not enter the node's artifact identity: editing it
rebuilds the same artifact in place through the ordinary node-scoped
content path (ADR-071), the way editing
:attr:`~solid_node.node.SheetLeafNode.thickness` does when it is
declared rather than passed. A ``FusionNode`` declares precision for its
own fused solid and does not inherit a child's. Only the mesh changes:
the ``.brep`` and ``shape()`` are identical whatever is declared, but
everything that reads the mesh — the viewer, the export, a faceted
``solid test`` run, and printed-piece identity (a fingerprint of built
content) — sees the declared precision, so redeclaring it gives a node a
new piece id. ``openvmp`` and ``Internal-Cycloidal-Actuator`` are the two
projects that asked for this, each having reached past the public API
into ``BRepMesh_IncrementalMesh`` to premesh a shape before ``render()``
returned it; Internal-Cycloidal-Actuator's design record measured the
cost on a vendor STEP part: 19.9 MB (398,184 triangles) at the
framework's default against 1.8 MB (35,776 triangles) at
``angular_deflection = 0.5``. See :ref:`tessellation-precision`.
(OpenSpec change ``declared-tessellation-precision``; ADR-077.)

**The expression vocabulary projects kept rebuilding.**
``solid_node.math`` now carries ``abs``, ``floor``, ``ceil``, ``sign``,
``min`` and ``max`` — the OpenSCAD builtins, emitted by name — plus
``clamp``, ``clamp01``, ``ramp``, ``lerp``, ``wrap``, ``piecewise`` and
``bump`` composed over them, and the vector helpers ``polar``, ``turn``,
``rotate_x``, ``rotate_y`` and ``rotate_z``. Each has the module's three
faces: a number in tests, a deferred OpenSCAD expression in the viewer,
and a dimension-checked formula in a declarative class body. Born of
thirteen project ``kinematics.py`` modules: four of them built a clamp
kit out of ``sqrt(x * x)`` believing the browser had no ``min``, ``max``
or ``floor`` — it has had all three all along — and four clock models
imported solid2's private ``OpenSCADConstant`` to emit ``floor``
themselves. An abacus clamp that published 123 characters of nested
``sqrt`` now publishes 44 of ``min(max(...))``.

There is deliberately no ``round`` (OpenSCAD, JavaScript and Python
round halves three different ways; ``floor(x + 0.5)`` is the half-up all
three agree on) and no ``mod`` (OpenSCAD spells it as the ``%``
operator, whose sign rule differs from Python's). ``floor`` and ``ceil``
take a dimensionless quantity, because a whole number bears no
dimension: count in the unit you mean, ``floor(travel / pitch)``. Every
name the module can emit is in ``solid_node.math.SYMBOLIC_BUILTINS`` and
is pinned by the cross-runtime parity fixture, which the generator now
refuses to write while one is uncovered. A call mixing animation time
with a declared parameter, which used to render the declaration's
``repr()`` into the published expression, now raises. See
:ref:`Non-linear kinematics <non-linear-kinematics>`. (OpenSpec change
``expression-math``; ADR-022, revised.)
**The mechanism laws, carried once.** ``solid_node.mechanisms`` holds
the textbook geometry thirteen projects' ``kinematics.py`` kept
rewriting, each in its own frame and sign convention: the external
spur-gear mesh and its inverse (``meshed_angle``, ``driving_angle``),
the lead screw (``screw_travel``, ``screw_angle``), the planar
slider-crank (``crank_pin``, ``crank_rod_angle``, ``piston_height``),
linear delta kinematics (``delta_carriage``, ``delta_rod``) and the
circle geometry a linkage asks for (``circle_intersection``,
``triangle_angle``, ``link_rise``). Every one is a composition over
``solid_node.math``, so it computes on numbers and builds the viewer's
expression on symbolic time or a driver, and emits no OpenSCAD builtin
that module does not already emit. A gear library's convention is two
argument values rather than a fork of the law: cq_gears' gap centre at
``180 / teeth``, MrBunsy's at ``gap_angle / 2``. There is no declared
(class-body) face — the laws carry degree literals the dimension
algebra cannot type as angles, so a declared token raises there and
``.value`` is the way through. Lifted from ``sandbox/gearbox``,
``3DPrintedClocks`` (``wall_clock_01`` and the grasshopper),
``v8-engine``, ``kossel``, ``openflexure-microscope``, ``Inmoov-sim``
and ``snappy-reprap``, and checked against each of their own functions.
(OpenSpec change ``mechanisms``.)

**Several models in one project.** A manifest may declare its models by
name in ``[tool.solid-node.models]``, with ``model`` naming the default
among them; a manifest without the table is unchanged. A declared name
is a node reference — ``solid build wall_clock_02`` — and each declared
model owns its own build directory, ``_build/<name>/``, with its own
``viewer.json``, ``errors.json`` and lock, so publishing one model never
sweeps another. ``solid models`` lists them with their state, as text or
``--json``, without importing project code; ``solid build --all`` and
``solid test --all`` walk every declared model and never stop at a
failing one. Born of ``3DPrintedClocks``: one repository, one shared
library, one model per clock. (OpenSpec change ``named-project-models``;
ADR-073.)

**A test run chooses its comparison kernel.** ``solid test`` compares on
the exact boundary-representation kernel by default, exactly as before,
or on the parts' meshes with ``--faceted`` — selected for a checkout by
``SOLID_TEST_KERNEL=faceted`` in its ignored ``.env``, so CI keeps the
exact kernel with no configuration. A faceted run answers every
intersection, containment, connectivity and weld question at
tessellation precision, carries one run-wide volume epsilon
(``--volume-epsilon``, ``SOLID_TEST_VOLUME_EPSILON``; refused by the
exact kernel), and names itself before the first build and on its
summary line. Nothing about the model, the build or ``node.exact``
changes between the two runs. On the v8-engine root suite, whose springs
made every comparison an OCCT Boolean, the faceted run takes 90 s where
the exact run took 28 minutes and reaches the same verdict on every
comparison at epsilon 0. ``solid new`` now ignores ``.env``. (OpenSpec
change ``faceted-test-kernel``.)

**A declared time base.** A root assembly can declare what one turn of
the animation timeline *is*: ``time = Time(loop=12 * 3600)`` says a turn
is twelve hours, and from then on ``self.time`` reads seconds everywhere
— ``$t * loop`` on the symbolic build path, so ``$t`` stays the 0..1
slider and the multiplication travels inside the published expressions;
the bound number under ``set_keyframe``, the testing decorators and a
stepped simulation, all of which state seconds. Every assembly below the
root reads the root's time base, and a declaration on a linked descendant
is refused when read. The documents ``solid build``, ``solid export`` and
the web snapshot publish carry ``animation.loop`` beside ``fps`` and
``frames`` (additive; an older viewer keeps playing ``frames / fps``),
and ``solid snapshot --time`` keeps its 0..1 meaning, landing on the
seconds that slider position means. A root that declares nothing is
unchanged. See :ref:`Declaring the time base <time-base>`. (OpenSpec
change ``declared-time-base``; ADR-072.)

Migrating a model to ``Time`` changes the meaning of every instant it
states: ``simulate()`` stops multiplying the fraction by a project
constant, tests stop dividing by it, and ``set_keyframe`` callers state
seconds.
**Several node classes in one file rebuild independently.** The
content-verified currency check beneath the mtime rule is now scoped to
the node: a source file that defines more than one node class contributes
to each node's digest only the text that node can see — the file minus
the other node classes' bodies, unless the rest of the file names them —
so editing one class re-derives that node and the fusions above it, and
merely restamps its neighbours. Shared module-level code still rebuilds
every node in the file. Nothing is required of a project's layout any
more: one node per file is no longer a premise of the cache. A file that
defines one node class digests exactly as before, so no existing build
directory rebuilds on upgrade; the nodes of a multi-node file rebuild
once. (OpenSpec change ``node-scoped-currency``; ADR-071.)

**The declarative node API.** A node class body can now *declare* its
parameters (``Length``, ``Angle``, ``Count``, ``Ratio``, ``Flag``,
``Scalar``), derive others as bare formulas over them, and declare its
children by constructing them in the class body — with literal lists and
``repeat(count)`` for identical units. A formula's dimensions are checked
on ``import``; ``sqrt`` and the degree trigonometry of ``solid_node.math``
take part. Each parent instance realizes its own children, top-down from
the root's values, so ``Engine(bore=32.0)`` moves the whole machine, and
``--set name=value`` on every node-loading command does the same from the
shell. An internal node's ``render()`` may return nothing, in which case
the children are the declared ones minus any it ``omit()``\ s; a pure
grouping node needs no ``render()`` at all. Ports bind by assignment.
See :doc:`Declaring a machine <declaring>`. (OpenSpec change
``declarative-node-api``.)

Nothing changes for a class that declares nothing. When migrating a
class, its artifacts re-key once if it used to omit a keyword from
``super().__init__()`` or passed an integer where a float kind now
resolves; the next build rebuilds them. A node class carrying its own
metaclass must now derive it from ``solid_node.node.declarative.NodeMeta``.

**render() builds the machine at rest; simulate() moves it.** An
assembly's ``render()`` declares structure and places what does not
move, reads no driver, time or port, and runs once per instance. The
new ``AssemblyNode.simulate()`` runs after it on every instant, under
symbolic ``$t`` or the bound state, reads drivers, ``self.time`` and
ports, and every operation it applies composes *inside* the part's
rest placement and is swept before the next run. ``omit()`` in
``simulate()`` raises. Nothing that worked stops working: a
``render()`` that reads a driver keeps re-running per instant as before,
and the build prints one ``FutureWarning`` per class naming the read and
``simulate()``. Placement in ``__init__`` is no longer recommended; it
still works. The rename of ``render()`` proposed by the design reference
is dropped: *render* also means *to make*. See :ref:`Rest and motion
<rest-and-motion>`. (OpenSpec change ``render-simulate-split``.)

**Build parameters have a module of their own.** ``Length``, ``Angle``,
``Count``, ``Ratio``, ``Scalar``, ``Flag``, ``Quantity`` and
``declared_parameters`` are imported from ``solid_node.parameters``, a
top-level peer of ``solid_node.simulation`` and ``solid_node.test``, and
are **no longer exported by** ``solid_node.node``. An import line now says
which of its names is a node kind and which is a knob on the machine:
parameters build the machine, drivers drive it. There is no re-export and
no deprecation path — the declarative parameter surface has never been
released, so the only code to update is code written against an unreleased
branch, and a second working path would defeat the point. Change
``from solid_node.node import CadQueryNode, Length`` to two lines. See
:doc:`Declaring a machine <declaring>`. (OpenSpec change
``build-parameters-module``.)

**Follow-ups from the first project migrations** (OpenSpec change
``declarative-node-api-fixes``). A list comprehension in a class body
over module-level values now declares children — it used to build
shared instances silently under Python 3.12's inlined comprehensions. A
``Flag`` passed to a declared child now resolves to the parent's
boolean, so a structural choice can live on the root and be set with
``--set``. A declarative node may define ``check()`` for guards over
several parameters at once; the framework calls it once the parameters
are resolved and before any child is realized. The declaring page says
where a once-only placement goes.

v0.6.0
------

Released on 01/Sep/2026

The release that makes a model a *machine*. Until now a solid-node model
moved as a function of one looping ``$t``; it can now declare named
inputs, be stepped deterministically in Python, and be driven by hand in
the viewer. Alongside that, three new kinds of part — laser-cut sheets,
imported STL meshes, and flexible parts whose shape is a function of
machine state — and an assembly assertion that knows about gravity. The
build and the CLI also got substantially faster on projects large enough
for it to matter. The narrative announcement is at
`docs/releases/release-0.6.md
<https://github.com/LibreSolid/solid-node/blob/main/docs/releases/release-0.6.md>`_.

**Breaking changes**

* **Reinstall required.** ``cadquery`` moves from 2.5 to 2.7 and
  ``build123d`` 0.10 joins it, so the shared ``cadquery-ocp`` binding
  moves from 7.7 to 7.8. The two versions of that large binary wheel
  cannot coexist: upgrade by reinstalling the environment rather than in
  place. No project source changes.
* The published document schema moves from version 1 to version 2 (a
  ``drivers`` table; operation expressions may name qualified driver ids
  as well as ``$t``), and a document containing a flexible part declares
  version 3. The producer emits the lowest version its content needs, and
  the bundled viewer renders versions 1, 2 and 3 — but a 0.5.x viewer has
  no version gate at all, so pointed at a 0.6 document it silently
  renders only the part of the machine it can evaluate. Hosts pinning
  their own copy of the bundle must upgrade it with the framework. The
  declared viewer API version is 5, and this release's viewer refuses an
  unreadable schema version by name.
* ``export_node`` now leaves the node in symbolic time rather than in
  whatever pose the caller left it. ``solid export`` and the build and
  snapshot paths produce byte-identical output; only a host calling
  ``export_node`` itself and reusing the node sees the difference.

**New features**

* **Named drivers.** An assembly declares its inputs as class attributes
  — ``x = Driver(default=0, range=(0, 200), unit='mm')`` — and reads
  them back as attributes. Assigning to one raises and names
  ``set_state``, reading an unbound one raises and names the driver, and
  a declaration that would shadow a node member fails at class-definition
  time. ``time`` is now one driver among several.
* **Instance-qualified driver ids.** Two instances of one class publish
  their same-named driver distinctly — ``set_state(**{'x_axis.motor':
  12.5})`` — with one dotted id used in the document, the simulation and
  instruction targets alike; an unqualifiable tree fails loudly.
* **Domain-typed ports.** ``Port`` with ``RotationalPort``,
  ``TranslationalPort`` and ``SignalPort``: unit-tagged value slots
  re-bound every render, with declared unit conversion and a causal
  ``connect()``.
* **A stepped simulation layer**, ``solid_node.simulation``: ``Driver``
  declarations and ``RampProgram``; ``Instruction`` targets in design
  units plus a duration; ``Sim``, a fixed-``dt`` loop with integer
  ticks, events, deferred ``at(t)`` actions, an ``every(period, fn)``
  cadence, per-tick snapshot binding and trajectory recording; and
  ``ScenarioTest``, one class running under plain pytest and under
  ``solid test`` alike. Integer-typed drivers ramp integer-exactly and
  land on target.
* **A driveable viewer with on-screen controls.** The widget evaluates
  driver expressions and shows one button per instruction and one slider
  (with numeric readout, in design units) per driver declared at the
  focused assembly layer, with a breadcrumb to move focus. Triggers ramp
  client-side over the declared duration, landing exactly on target.
  Only expressions whose free variables changed re-evaluate. Hosts get
  ``drivers()``, ``instructions()``, ``driver(id)``, ``setDriver(id,
  value)``, ``onDriverChange(fn)`` and ``trigger(name)`` on the mount
  handle, and ``driverControls: 'none'`` to suppress the chrome.
* ``Build123dNode``, a fifth leaf adapter backed by build123d — exact
  OCCT geometry, a ``.brep`` beside its STL, no OpenSCAD binary — and
  exact fusion across backends: CadQuery and build123d children fuse
  exactly together.
* **Sheet parts.** ``SheetLeafNode`` with ``Build123dSheetNode`` as its
  first backend: a laser-cut part authored as a 2D ``profile()`` plus a
  declared ``thickness``, writing a nominal kerf-free ``.dxf`` beside
  its STL and BREP under the same freshness guard.
* **Imported meshes.** ``StlNode`` wraps an ``.stl``; a
  non-watertight mesh fails at build (``require_watertight = False``
  admits one knowingly), a multi-body file is selected by ``body`` with
  a per-body inventory on omission, and ``adjust(self, mesh)`` corrects
  the mesh in code. An ``StlNode`` in a fusion routes that fusion
  through the faceted OpenSCAD/CGAL path.
* **Flexible parts.** ``FlexibleNode`` with ``MolejoNode`` as its first
  adapter: a spring, belt, loom or filament whose geometry is a pure
  function of its declared ports' bound values, travelling as a `molejo
  <https://molejo.readthedocs.io>`_ shape spec plus one expression per
  parameter rather than a mesh, evaluated in the browser only on frames
  its inputs changed. Exact geometry from molejo's OCCT evaluator; the
  OpenSCAD path gets per-binding snapshot meshes.
* **Assemblies are checked against gravity.**
  ``assertAssemblySupported`` proves support reachability (every solid,
  dropped along gravity, lands on something that leads to ground) and
  static equilibrium (push-only contact forces balance every solid's
  gravity wrench, force and torque, via one deterministic linear
  program), naming the unbalanced solids on failure. ``ground``,
  ``supports`` and ``stability_margin`` refine it; friction, adhesion
  and dynamics stay out of scope.

**Fixes**

* Artifact freshness no longer goes through floating-point mtimes:
  source times are read as integer nanoseconds and artifacts stamped
  with the exact value read, fixing spurious full rebuilds on
  millisecond-resolution filesystems. Freshness stays exact equality.
* ``manifold3d`` became a conditional dependency of the faceted mesh
  path, so an all-exact project runs its geometric assertions without
  the compiled wheel — including on platforms with no wheel at all.
* ``clear_keyframe()`` joins ``set_keyframe(time)`` as its explicit
  inverse, returning a subtree to symbolic ``$t``.
* The viewer's driver readout holds still under a drag: fixed decimal
  places, fixed-width figures, the unit in its own segment.
* The viewer reads a leading negative term the way it is written. Its
  expression parser took a unary operator's operand to be the whole
  expression beside it, so ``-100.0 + x`` was read ``-(100.0 + x)`` and
  the sign of a driver's coefficient changed. All 265 distinct
  expressions the Metamaquina 2 example publishes now agree between the
  Python producer and the viewer's parser, where one did not.
* The viewer refuses a flexible part's shape spec its bundled evaluator
  cannot read, by name and once at construction, as it already refused
  an unevaluable ``tech``. Such a spec previously escaped as a raw error
  inside the render loop, naming no node.

**Performance**

* The ``solid`` command imports commands, backends and the test
  framework at the point of use rather than all of them on every
  invocation: ``import solid_node.cli`` 3.48 s → 0.002 s, ``solid
  viewer`` 3.79 s → 0.044 s. Nothing became optional and no grammar,
  help, option, exit code or public API changed.
* The source-closure package lookup is indexed rather than rescanned
  per call. On a 567-node project a cold ``load_node`` goes 19.4 s →
  4.8 s and a no-op ``solid build`` 23.4 s → 8.0 s, every published
  artifact identical by SHA-256.
* An artifact whose sources were rewritten but not changed — by a
  clone, branch switch, stash pop or restore — is restamped rather than
  re-derived, on a digest of exactly the tracked sources consulted only
  when mtime equality fails. A 22-part CadQuery project rebuilt after a
  full timestamp rewrite goes 35.70 s → 5.83 s.

**Packaging and documentation**

* solid-node now depends on `molejo <https://pypi.org/project/molejo/>`_
  with its ``brep`` extra, and the bundled viewer on the ``molejo`` npm
  package, both pinned to molejo's minor — a molejo minor carries the
  shape-spec version it implements.
* molejo 0.2 renamed the token a document declares its spec version
  with, from an integer to the ``MAJOR.MINOR`` string of the release
  that minted it. solid-node never writes that field, and molejo 0.2
  reads both the versions this release can publish.
* The user documentation now tells the 0.6 story rather than the 0.3
  one: the entry surface leads with drivers, simulation and the
  driveable viewer, two new tutorials cover driving a machine and
  scenario testing, the guides' stale claims are corrected throughout,
  and `Metamaquina 2 <https://github.com/LibreSolid/Metamaquina2>`_ —
  a real open-hardware printer — joins the V8 engine as a second worked
  example.

v0.5.1
------

Released on 18/Aug/2026

**Fixes**

* The project's ``Homepage`` metadata named a repository URL that returns
  404. It now points at https://github.com/LibreSolid/solid-node.
* The Read the Docs build passed the ``root`` argument that v0.5.0 removed,
  failing every documentation build with
  ``Error loading node: No module named 'root'``. The V8 example export now
  resolves the model from its ``[tool.solid-node]`` manifest.

v0.5.0
------

Released on 17/Aug/2026

**Breaking changes**

* A project declares its model in a ``[tool.solid-node]`` table of its
  ``pyproject.toml``. The project root is discovered from the nearest
  ancestor manifest instead of the current working directory, so commands
  behave identically from a subdirectory.
* Node-scoped commands take an optional reference — ``package.module:Class``,
  a file path, or a path plus class — defaulting to the manifest's model.
  The fixed ``root/__init__.py`` entry point, the directory argument, and the
  ``NODE`` marker are removed.
* ``solid test`` loads every ``TestCase`` in a companion file instead of the
  first. A case beside a multi-node module MUST declare ``node = <Class>``:
  an undeclared one aborts the whole run before any test executes, naming the
  candidates. Single-node modules are unaffected. Cases that were silently
  not running will run — and may fail — for the first time.
* Intersection and connectivity assertions answer exactly when both compared
  nodes are exact, so verdicts change in both directions: real sub-facet
  interference now fails, and nominally exact fits that failed on facet phase
  now pass. ``volume_epsilon`` is ignored, with a warning, on a fully exact
  call.
* A failed build leaves a partially updated model rather than the previous
  complete artifact set; in exchange each artifact is written whole or not at
  all, and a successful build sweeps artifacts its manifest dropped.
* An all-exact ``FusionNode``'s STL bytes change — it is tessellated by OCCT
  rather than compiled through OpenSCAD.
* ``assertNoPairwiseIntersections`` is deprecated in favour of
  ``assertNoSolidInterference`` and warns about its quadratic leaf sweep.

**New features**

* ``solid build [reference]`` builds and publishes once, then exits; an
  unresolvable model exits with status 66 (``MODEL_NOT_FOUND``).
* ``solid develop --no-web`` runs the watch-and-rebuild loop with no viewer,
  and ``--callback URL`` announces each successful publication.
* ``solid snapshot --renderer web`` renders through the packaged viewer in
  headless Chromium with a real alpha channel. Optional install:
  ``pip install "solid-node[web-snapshot]"`` plus ``playwright install
  chromium``. It never falls back to OpenSCAD silently.
* ``solid viewer`` reports the installed viewer bundle's path and API version.
* Exact geometry: a read-only ``exact`` property, ``shape()`` returning the
  node's OCCT solid in its local frame, and a cached ``.brep`` artifact beside
  each exact rigid node's ``.stl``. Exact fusions compose with an OCCT fuse.
* Published documents carry a ``pieces`` inventory keyed on a content
  fingerprint of each built STL, with display name, source files, instance
  count, bounding extents, volume and watertightness, plus a ``piece``
  reference on every rigid node. Additive; no existing field changes meaning.
* New assertions ``assertNoDisconnectedSolids``, ``assertNoSolidInterference``
  and ``assertJoined``. ``solid new`` scaffolds ``test_solid_integrity`` and
  ``test_assembly_integrity``.
* OpenSCAD is required only by the paths that invoke it; an all-exact
  CadQuery project builds, tests and publishes without it, and a path that
  needs it says so instead of raising ``FileNotFoundError``.
* One reusable viewer package serves exports, the Sphinx directive and
  ``solid develop``. ``mount()`` returns a handle with targeted updates,
  assembly metadata, and subtree focus and visibility. Declared viewer API
  version 4; the published bundle, global, auto-mount attribute and query
  parameters are unchanged.
* The development viewer gains inherited colours, lights, a fitted camera and
  the shared animation controls; uncoloured exported models render with the
  normal-based material.
* Every successful build publishes a viewer-readable snapshot including the
  animation cadence (``fps``, ``frames``), so a host can serve the model from
  the build directory with no source import.

**Correctness and reliability**

* A node tracks the project modules its source imports, not just its own file
  (ADR-033), so editing a shared geometry module invalidates the nodes that
  import it. Note that ``assemble()`` may now call ``render()`` zero times,
  and geometry depending on something a static import walk cannot see can look
  current when it is not.
* Concurrent builds of a project are serialized with an advisory ``flock``,
  so a late-finishing build cannot overwrite a newer model. ``solid develop``
  and ``solid test`` release the lock before waiting and before testing.
* Self-contained exports resolve models beside their document rather than at
  the server root, fixing embedded examples served under a subdirectory.
* An explicit reference may name a node class defined in another
  project-local module.
* ``FusionNode`` rejects a non-rigid child instead of silently becoming
  non-rigid and producing no STL.
* A failed targeted viewer update leaves the rendered model on screen and the
  handle usable; geometry just fetched is not refetched.
* ``solid snapshot`` holds the build lock only while preparing its node, and
  defaults ``-o`` from the resolved node.

**Performance**

* The up-to-date check runs before ``render()``: a no-op rebuild of a
  CadQuery-heavy project fell from 19.8 s to 3.2 s.
* The viewer updates in place instead of rebuilding the scene, refetching
  geometry only where ``(model path, mtime)`` moved — an operations-only or
  colour-only edit costs no fetch.
* ``assertNoSolidInterference`` dropped its global volume certificate: 273 ms
  against 2 ms for the spatial path on a 125-solid, 1.02M-triangle assembly.
* Exact ``.brep`` artifacts cache far more cheaply than the STLs beside them
  (4 ms write, 2 ms read, 165 KiB against 112 ms, 9 ms, 469 KiB).

**Packaging, documentation, and maintenance**

* The built viewer bundle ships in source distributions and wheels, so a
  fresh installation has a viewer.
* New optional extra ``solid-node[web-snapshot]``.
* The development loop's per-node HTTP API under ``/node`` and the browser
  modules and dependencies that consumed it are removed. No published
  document, URL or CLI surface changes.
* Scaffolded projects ignore ``__pycache__/`` and ``_build*``; existing
  projects get ``_build*`` in ``.git/info/exclude`` on their next build.
* ``README.rst`` documents OpenSCAD as conditional and covers working on
  solid-node itself; the hosted documentation builds its embedded exports
  from source in CI.

v0.4.0
------

Released on 20/Jul/2026

**Breaking changes**

* The CLI is now command-first: ``solid <command> <node>``.
* ``solid new`` replaces the former solid-seed cloning workflow.

**New features**

* ``solid export`` generates a static viewer manifest and STL exports for a node tree.
* Exported models can be embedded with the standalone viewer widget and the
  ``.. solid-node::`` Sphinx directive.
* Added symbolic degree-aware math functions in ``solid_node.math``.
* Added ``assertBlockedBeyond`` and ``assertFreeWithin`` for kinematic-fit
  tests, plus ``along=`` support for translational perturbations.
* Added the ``NODE`` marker for choosing a node class from modules that define
  more than one.
* Node names now default from their parent attribute name.

**Correctness and reliability**

* Animation rendering is now idempotent across nested assemblies and multiple
  drivers.
* Node identity and artifact keys no longer collide across node classes,
  names, or positional/keyword parameter forms.
* Fixed animated rotation, translation reversal, operation deserialization,
  snapshots, testing-step offsets, and ``--failfast`` behavior.
* ``solid test`` now exits non-zero on failures and reports invalid test paths
  clearly.
* ``solid develop`` remains running after a broken reload and can launch the
  OpenSCAD viewer reliably.
* Improved mesh-intersection checks with configurable volume tolerance.

**Performance**

* Cached base meshes, loaded meshes, and Manifold objects.
* Composed transforms into one world matrix and added AABB broad-phase culling
  before exact intersection tests.

**Packaging, documentation, and maintenance**

* Migrated packaging to ``pyproject.toml`` and ensured compiled frontend assets
  ship in wheels.
* Relicensed the project from AGPL-3.0 to Apache-2.0, with updated attribution
  and NOTICE.
* Added comprehensive API, CLI, tutorial, testing, embedding, and architecture
  documentation.
* Removed obsolete CI configuration and refreshed contributor guidance.

v0.3.0
------

Released on 14/Jan/2026

**New Features**

* Snapshot CLI command for headless PNG rendering (ADR-019)
* Full CREDITS.md with license attribution for all dependencies

**Architecture Improvements (ADR-018)**

* Removed over-engineered WebSocket IPC (broker.py)
* Moved Git integration to solid-studio (git.py)
* Moved IDE refactoring features to solid-studio (refactor/)
* Removed dead code (exceptions.py, spatial.py)
* Framework is now lean and focused on core CAD functionality

**Maintenance**

* Added license headers to all source files
* Synchronized requirements.txt with setup.py
* Removed unused "unicorn" dependency

v0.2
----

Released on 25/Feb/2025

* JScadNode adapter for JSCAD backend support, plus further work on OpenScadNode
* API reference documentation building on Read the Docs

v0.1
----

After some evolution and several pre-releases (v0.0.1 through v0.0.8),
the project was documented and released as v0.1 with:

* Multi-backend support (SolidPython2, CadQuery, OpenSCAD)
* Web-based 3D viewer with React/Three.js
* Development server with hot-reload
* Test runner for CAD projects
* STL generation and optimization
