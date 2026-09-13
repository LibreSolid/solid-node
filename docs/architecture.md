# solid-node Architecture

This is the synthesis document: the current architecture of solid-node
in one place. It sits between two other records and is derived from
them:

- **[`openspec/specs/`](../openspec/specs/)** — the behavioral
  contracts: what the system observably does, requirement by
  requirement.
- **[`docs/adrs/`](adrs/README.md)** — the decision log: each ADR is a
  delta explaining *why* one piece is the way it is.

ADRs accumulate; this document integrates. When an OpenSpec change is
archived and it shifted the structure described here, updating this
document is part of landing the change — same rule as the specs.

## The big picture

A solid-node project is a **Python program that evaluates to a tree of
nodes**. Leaves generate solid geometry; internal nodes compose and
place it. From that single tree, the framework derives everything else:

```
                     your_project.py
                           │  load_node()                (BUILD)
                           ▼
                      node tree                          (NODE)
       render/simulate → validate → native materialize
                           │
           ┌───────────────┼──────────────────┐
           ▼               ▼                  ▼
     optional SCAD      STL/BREP         serialized ops
      presentation    (OCCT / JSCAD /   ($t expressions)
      → OpenSCAD       imported mesh /        │
      where selected   manifold3d)             ▼
           │                            viewer.json / manifest.json
           ▼                            → solid-node-viewer (separate
      dev loop, OpenSCAD snapshot,        AGPL package, own process)
      export models                     evaluates $t per frame
```

Three architectural commitments shape almost every subsystem:

1. **Geometry follows the strongest backend path available**
   (ADR-004/044/045/046/047/102). Native preparation precedes optional SCAD
   presentation. Solid2 and raw `.scad` leaves render through OpenSCAD because
   it is their backend; faceted fusions compose current child meshes directly
   through Manifold. The OCCT backends — CadQuery and build123d — preserve
   BREP geometry, and all-exact fusions compose and tessellate in OCCT
   without OpenSCAD, whichever of the two produced each child. JSCAD produces
   its STL through its own `jscad` tool, and a flexible part through molejo's
   evaluators — mesh, STL and B-rep from one analytic spec.
   OpenSCAD is therefore conditional on
   the paths that invoke it, not a universal framework prerequisite. The same
   rule governs the `manifold3d` mesh engine (ADR-052/102): it decides faceted
   fusion and faceted comparison geometry, and is also required by
   `assertAssemblySupported`, whose statics phase is faceted for every body.
   Both tools are resolved once per process at
   the point of use and report by name when absent.
2. **The build artifact is the currency, mtime is its clock**
   (ADR-006/026/033/050/081). STLs are cached per parameter-hashed identity
   and validated by mtime *equality* against the max source mtime, in integer
   nanoseconds — never as a float, which cannot survive the `os.utime`
   round trip off a filesystem coarser than a nanosecond (ADR-050). That
   equality is guarded by a recorded metadata fingerprint of every tracked
   contributor, so a future-dated source cannot hide an edit to an older one
   (ADR-081). Base-mesh and Manifold caches key the path together with its
   strong observable identity — device, inode, size, integer-nanosecond mtime
   and ctime — so a same-size restored-mtime replacement cannot serve old
   faceted geometry (ADR-085). Artifact freshness remains the one invalidation
   concept the whole system shares. The source set behind
   that clock is a node's own file plus the project-local modules it
   imports, transitively (ADR-033), so a contributing module edit
   invalidates the nodes that read it — and only those. Beneath the
   clock, content decides: when the stamp or source fingerprint moved, a digest of what the
   node can see of its sources — its own file minus the sibling node
   classes it never names (ADR-071) — is what says whether the artifact
   is still the one those sources produce.
3. **One kinematic truth, recomputed absolutely, consumed everywhere**
   (ADR-023/027/028). A node's placement is its operation list. Every
   consumer — SCAD output, world-space meshes for assertions, the two
   browser renderers — folds that same list, own-ops-first then
   ancestors, later operations outermost. Nothing tracks incremental
   mutations; every consumer recomputes pose from declared state, which
   is what makes re-renders idempotent and caching safe.

## Subsystems

### Node model (NODE · spec `node-model`)

`AbstractBaseNode` roots a composite tree (ADR-001): `InternalNode`
subclasses return child lists from `render()`, `LeafNode` subclasses
return one geometry object, and validation enforces the split on every
assembly. Users implement `render()`; the framework owns the
non-overridable lifecycle. `_prepare()` renders/simulates, validates, links the
tree and materializes native artifacts; `assemble()` is the separately
memoized compatibility consumer that presents SCAD, imports optimized STL and
applies operations (ADR-002/102). Geometry-only consumers stop after native
preparation.

A node is authored in one of two forms, freely mixed in one tree. The
**constructor form** builds children in `__init__` and forwards
parameters to `super().__init__()`. The **declarative form** states
them in the class body: typed parameters (`Length`, `Angle`, `Count`,
`Ratio`, `Flag`, `Scalar`), derived parameters as bare formulas over
them, children as calls, ports, and **joints** — where the node itself
may move (ADR-088) — because every node class carries
`NodeMeta`, a call inside a node class body yields a `ChildDeclaration`
rather than an instance, recognized by the body's marked namespace on
the stack (ADR-061). Each parent instance realizes its own children
last in `__init__`, in declaration order, into its instance dict under
the declaring attribute, so naming, qualification and the serialized
document see the tree they always saw; a literal list declares
enumerated children and `repeat(count)` count-many identical ones,
named `<attr>-<index>` without renumbering. Tokens, a `Flag` among them, pass to children by
reference and resolve top-down from the root's values, so
`Engine(bore=32.0)` moves the whole machine and `--set bore=32.0` on any
node-loading command does the same from the shell. A parameter is a
data descriptor: the token on the class, a plain `float`, `int` or
`bool` on the instance, assignment refused, base attributes protected
from shadowing; a declaration without a default fails at
instantiation, never at class definition, when neither the parent nor
the caller supplies it. A guard over several parameters at once is the
node's `check()`, called once its parameters are resolved and before any
child is realized; an exception refuses the instance (ADR-065). A formula's dimension is a mapping from axis to
exponent — products add, quotients subtract, sums require equality,
`Angle` its own axis, `Count` and `Ratio` dimensionless — checked on
`import`, with `solid_node.math`'s emitted primitives carrying their own
rules and its compositions inheriting theirs, and a project free to
subclass `Quantity` with new exponents (ADR-062). By the time any `render()` runs every parameter is a plain
value; backends, `uniq_id` and the serializer never see a token. Reading
a parameter off a sibling declaration is refused: shared values are
declared on the ancestor and passed down. A keyword argument to a child
declaration whose VALUE is a port or joint declared on the same class is
a **wiring**, not a parameter (ADR-088): it never reaches
`resolve_parameters`, the child's construction or its identity, it is
validated against both ends at class definition, and the framework
rebinds the child's end from the parent's after every `simulate()` of
the parent. Every other keyword keeps the meaning it has, including the
`TypeError` an unknown one raises.

The public surface is split by concern above the node package, so an
import line says what each name is for: build parameters come from
`solid_node/parameters.py`, node classes from `solid_node/node/`, ports
and the declared time base from `solid_node/motion/ports.py`, runtime
inputs from `solid_node/simulation/`, the test case from
`solid_node/test.py` (ADR-062, amended). One module answers one question,
and a name is imported from the module that answers it (ADR-087) — the
rule the parameter split establishes and the motion package (below) is
built on. The parameter module holds the
declaration descriptor every other declaration follows, the exponent
algebra, the kinds and the parameter enumerator, and imports nothing at
all — not the framework, not a third party — because it is on the
import path of every node module in every project.
`solid_node/node/declarative.py` keeps the structural half, the child
declarations and `NodeMeta`, and imports the parameter module; the node
package exports no parameter kind, and `solid_node/math.py` reaches the
formula algebra sideways rather than down into the node package.

Automatic child names come from one parent-attribute snapshot per traversal.
Public direct attributes win in insertion order, then the first public
list/tuple membership supplies `<attr>-<index>`; private attributes and the
framework's linked `children` list never name. Every returned sibling is
linked from that common snapshot before recursion, so lookup is constant-time
per child and user code in an earlier child cannot rename a later sibling
mid-traversal. Reassignment, replacement and even same-length list reordering
are visible when the next traversal takes its new snapshot. An explicit
`name=` still wins and every link refreshes the parent.

On a declarative internal node `render()` places at rest and selects
and may return nothing, in which case the framework's render wrapper —
the same `__init_subclass__` hook that installs the lifecycle —
substitutes the realized declared children in declaration order minus
those `omit()` marked; a returned list keeps its contract untouched,
and a class with nothing to position needs no `render()` at all
(ADR-064). Declaration is independent of realized count: a zero repeat or
omission of every child substitutes `[]`, which an assembly carries through
its ordinary lifecycle and serializes explicitly as `children: []`
(ADR-082). An omitted child is not linked, built, exported, fused or
serialized. Structure varies with parameters, never with time: `omit()`
raises in `simulate()`, and on the legacy path the wrapper records the
omitted set of an instance's first render and raises on a later render
whose set differs. The reference's rename of `render()` is dropped
(ADR-066): *render* also means *to make*.

Two concrete internal nodes encode the **rigid/non-rigid** axis
(ADR-003): `FusionNode` (rigid union, no `time`) and `AssemblyNode`
(non-rigid, animatable). Rigidity is static and determined by node type;
a fusion rejects any non-rigid child during validation, enforcing "fuse
solids, then assemble them" (ADR-039). An empty assembly is valid grouping
and produces no STL of its own; an empty fusion is rejected before artifact
generation because a rigid fusion must denote at least one solid (ADR-082).
Only rigid nodes produce STLs, which
is why cached geometry must be time-invariant. A topmost rigid node is the
first rigid node on a branch below an assembly, or a rigid root itself; its
STL is the complete printed solid for that branch.

The axis has **three** cases, not two, because *leaf* and *rigid* are not
the same word (ADR-057). Beside the rigid leaves and the non-rigid
assembly stands one **non-rigid leaf** kind, `FlexibleNode`: a part whose
shape follows machine state. It composes with the rules above rather than
relaxing them — a fusion rejects it as it rejects any non-rigid child, it
enters no cached-artifact set so the time-invariance precondition is
untouched, it is never a topmost rigid node and contributes no printed
piece, and `time` raises on it as on any leaf.

Leaf adapters (ADR-004) wrap the backends: `Solid2Node`,
`CadQueryNode` and `Build123dNode` (both export to STL and re-import),
`OpenScadNode` (`scad_source` + module call), `JScadNode` (shells out to the
`jscad` CLI), `StlNode` (`stl_source`, a mesh materialized with
no backend at all), and `StepNode` (`step_source` + `part`, a STEP
document's own kernel writing its artifacts). Every node exposes derived read-only exactness (ADR-044): the
OCCT adapters are exact, the other leaf adapters are faceted, and an
internal node is exact only when every child is. Exactness does not require
one backend — every exact adapter converts its render result to one shared
OCCT shape at the adapter boundary, so the exact layer holds a single type and
a fusion may mix CadQuery and build123d children (ADR-047). Because that
conversion makes everything after it backend-neutral, the contract itself —
`exact`, `shape()`, native materialization and `as_scad()` presentation —
lives once on `ExactLeafNode`, the internal
base every exact adapter extends; each supplies only its `namespace` and any
validation its own API needs. Adapters remain distinct types regardless of the
bases they share. Because build123d
groups solids, sketches and curves under one namespace, `Build123dNode`
additionally rejects a render result that is not a solid, and accepts a
`BuildPart` builder by taking its finished `.part`.

One leaf kind has no modelling backend at all. `StlNode` is a part that
arrives as an STL mesh: it declares `stl_source` beside its wrapper
module, resolves and tracks it like `JScadNode` does its `.js`, and
materializes its own artifact through its native producer — selected body,
`adjust` correction, binary export, stamped with the source mtime, so no
external tool runs for the leaf at all (ADR-054). Three rules make the import
honest rather than credulous. A mesh that is not watertight is refused at
materialization, naming the file and the defect and writing nothing, unless
the node declares `require_watertight = False`; nothing is ever auto-repaired.
A multi-body file is a pack of parts, one of which the node selects by `body`,
a 0-based index into the components ordered by centroid (x, then y, then z),
with the failure of an unselected pack carrying the full inventory. And
normalization is code — an `adjust(self, mesh)` hook over the trimesh — not
constructor knobs. Because the wrapper module carries `body` and `adjust`, it
joins the node's tracked source set (ADR-055) — a rule `StepNode` below
also needs and for the same reason.
`StlNode` is faceted: `exact` is false, mesh-only is settled doctrine for
imported meshes, and a fusion containing one is faceted and unions through the
OpenSCAD/CGAL path (ADR-045).

A second external-file leaf reads the *other* file every vendor
publishes, and it is exact rather than faceted. `StepNode` declares
`step_source` beside its wrapper module exactly as `StlNode` declares
`stl_source`, and derives `ExactLeafNode` directly rather than writing
its own `as_scad()`: a STEP product is a boundary representation the
moment it is read, so `shape()`, the `.brep`, exact fusion and declared
tessellation precision (ADR-077) all come from that base whole, and no
external tool of any kind produces its artifacts. `part` selects one
product out of the document by name — the candidates being every
top-level XCAF label except a root that is itself an assembly, so a
bare single-part file and the commoner file wrapping one part in an
assembly root both select themselves, while a multi-component root is
never handed to a node by omission. A wrong or missing selection fails
with the document's own inventory — name, kind, occurrence count, solid
count, bounding box, volume, one line per product — the failure again
the discovery tool. The selected shape is always the product's own
frame, never an occurrence's placed copy; `adjust(self, shape)`
corrects it, and a shape holding no solid after `adjust` fails
admission naming what it does hold, with the explicit
`solids_from_faces(shape, tolerance)` helper the only sanctioned way to
turn a face-only vendor part into one. A subclass that declares no
`color` takes it from the document's own surface colour (converted from
XCAF's linear RGB to the framework's sRGB `#RRGGBB`) through a property
resolved lazily, so a build whose artifacts are current never opens the
file for it. The XCAF document itself is read and transferred at most once per
strong source observation per process. The read is bracketed and registered
with the active source generation, so replacement during transfer cannot enter
the cache or leave constructor geometry tied to another epoch. The cache uses
the source census's path/device/inode/size/mtime/ctime identity because the
read is expensive (11.79 s
measured on a 35 MB vendor assembly) and a project may hold many leaves
over one file (ADR-078).

The other half of a STEP document — where each product sits — is a
reader, not a node: `StepAssembly(path)`, in the same adapter module,
walks every occurrence through nested sub-assemblies over the identical
cached document, reporting each one's placement matrix, its world
matrix composed outward through its parents, and, for a proper rigid
placement, the exact `(angle, axis)`/translation pair that reproduces
it through the framework's own `rotate` then `translate` — decomposed
through OCCT's own quaternion (`gp_Trsf.GetRotation()`,
`GetVectorAndAngle`) rather than the trace and an `acos`, which is not
accurate enough at a 180° turn. A placement that is not proper — a
mirror or a scale, neither of which `rotate`/`translate` can state — is
reported with its determinant and scale factor and left undecomposed;
the rest of the document is unaffected. The CLI command `solid
import-step` turns this reader into project-owned source in one shot:
`parts.py` (one `StepNode` subclass per part) and `assembly.py` (one
`AssemblyNode` per assembly product, its children placed at the
document's own transforms, machine at rest — no driver, no
`simulate()`), never overwriting existing source and never touching
`pyproject.toml` (ADR-079).

One leaf kind names a *manufacturing method* rather than a backend.
`SheetLeafNode` — internal base, `Build123dSheetNode` its v1 adapter — is a
part cut from sheet stock, authored as a 2D `profile()` plus a declared
`thickness`. The base owns `render()`, which validates the profile and
extrudes it from the XY plane along +Z, so the solid in the tree and the file
a cutter consumes derive from one authored thing and cannot drift apart;
`profile()` is the only extension point (ADR-053). The profile contract is
the base's: exactly one planar face, one outer boundary with holes strictly
inside, on the XY plane, rejected naming the node and the offending type
before anything is written. `thickness` is required and positive at
construction, and as a constructor argument it keys artifacts like any other
parameter. The extrusion is an ordinary backend solid, so a sheet part is an
exact leaf in every respect above — `exact.py` needed no change, and a fusion
may mix a sheet part with any other exact child.

One leaf kind carries no solid at all. `FlexibleNode` — internal base,
`MolejoNode` its v1 adapter — is a part whose *geometry*, not merely whose
placement, is a function of machine state: a valve spring, a belt, a loom
(ADR-057). Its per-instant parameters arrive **through declared ports**,
connected by the parent assembly's `connect()` — ADR-056's guardrail
extended from *pose is a pure function of the driver snapshot* to *shape
is*. Constructor arguments stay structural, because every one of them
enters `uniq_id` (ADR-026) and a value that follows a cam would otherwise
mint an artifact identity per frame; `uniq_id` therefore stays structural
and two instances of one flexible class share it. The port name is the
parameter name, and the two name sets are checked in both directions
immediately after `render()`, an unbound port failing loudly rather than
defaulting. `MolejoNode.render()` returns a molejo `Shape`, validated by
the ordinary `namespace` mechanism: the render contract is the backend's
object, as for every other adapter. It is exact by type, `shape()`
evaluating the bound instant through molejo's B-rep evaluator and
recasting it into ADR-047's one currency, with the backend's declared
approximation surfaced as `shape_tolerance` (`1e-6` for a helix or spline
sweep, `0.0` where every surface is analytic) rather than hidden. Nothing
of that geometry is persisted: `shape()` computes on demand behind an
in-memory memo keyed on the binding, because `(path, mtime)` keying is
currency for a *source* and never for a *binding*.

Exact nodes expose unplaced BREP geometry through
`shape()`; placement remains the caller's responsibility through the same
composed matrices as the mesh path. An exact `FusionNode` fuses its placed
children in OCCT and represents that fuse in both BREP and STL (ADR-045).
Each adapter can still present SCAD, but artifact production follows its backend:
Solid2 and raw OpenSCAD leaves use OpenSCAD, CadQuery and build123d — sheet
parts included — use OCCT, JSCAD uses `jscad`, a flexible leaf uses molejo's
Python evaluator, and an imported mesh uses no
tool whatsoever (ADR-046). Emitting SCAD
does not itself require the OpenSCAD binary. A sheet leaf writes one artifact
the others do not: a nominal DXF of its profile, in millimeters with arcs
preserved, beside its `.stl` and `.brep` and under the same freshness rules,
which its skip guard also requires. A flexible leaf writes another: a
per-binding snapshot STL, so the assembled SCAD document and fixed-pose
OpenSCAD snapshot renderer stay complete — a snapshot camera, never
animation, the treatment drivers already receive. The camera declines where there is no instant to
photograph: a port fed by animation time, which nothing binds on this path
(ADR-008), yields no artifact and no geometry rather than failing the build
or inventing a moment. An unbound port, or one still carrying a raw driver
token the loader should have bound, is a wiring mistake and still fails
loudly (ADR-057).

Identity is split three ways. `uniq_id` (class qualname + canonicalized
params, 12-hex sha256, readable prefix) keys build artifacts —
parameters change, artifacts change; `name` (explicit or derived from
the parent attribute holding the child) addresses the tree for tests
and the viewer, and never touches geometry (ADR-026). On a declarative
class the params are the resolved, coerced declared values sorted by
name, computed by the framework through the same serialization, so a
class that forwarded everything keeps its key and no keyword can be
forgotten; repeated identical units share one key and one artifact
(ADR-063). A **piece** id
(12-hex sha256 of the built STL's bytes) identifies one thing to print,
so solids factored into different classes but building identical geometry
are one piece, while handed variants are two (ADR-043). Each answers a
different question — rebuild needed, addressed how, same thing to print —
and conflating any two produces silently wrong answers. A flexible leaf's
snapshot artifact adds a fourth key beside — never inside — `uniq_id`: a
`binding_hash` of its resolved parameter values, which is what makes a
changed *state* a different file rather than a rewrite of one whose mtime
already claims it is current (ADR-057).

### Kinematics (NODE · spec `kinematics`)

Transforms are first-class operation objects (ADR-023):
`Rotation`/`Translation` render for four consumers — `.scad()`,
`.mesh()`, `.serialized`, `.matrix()` (ADR-028) — plus `.reversed`.
`AssemblyNode` is the only animatable node, and it binds a
**multi-driver state snapshot** (ADR-056 stage 1): `set_state(**states)`
merges named plain-number driver values and propagates down the
rendered tree. `render()` reads a driver it declares **as an
attribute** — `x = Driver(...)` is read `self.x` (ADR-056, amended
2026-08-27) — which is
the only read there is; the snapshot has no mapping view. An unbound
read fails loudly naming `set_state`, assigning to a driver fails the
same way, and a driver declared over a name the node class already
carries fails at class-definition time. Every bound name must name a
declared driver, bare or qualified, because nothing could read an
entry with no declaration behind it; `time` is the exception, one
snapshot entry with the ADR-008 fallback to symbolic OpenSCAD `$t`
(0..1) when unbound, read through the `time` property. **What that
entry means is the root's to declare** (ADR-072): a root class may
carry `time = Time(loop=<seconds>)` — a frozen data descriptor bound to
the name `time`, refused under any other name or on a non-assembly,
readable off the class as `Root.time.loop` — and then `self.time` reads
seconds on every path: unbound, the symbolic product `$t * loop`, so
`$t` stays the 0..1 slider and published expressions carry the
multiplication; bound, whatever the binder stated in seconds
(`set_keyframe`, the testing decorators, `Sim`'s `k*dt`). One reader in
`solid_node/node/assembly.py` (`read_time`) serves the base property and
the descriptor: bound entry first, else walk `_parent` to the root of the
linked tree and scale by its declaration — a descendant reads what its
root reads with no state propagated, and a declaration on a node strictly
below the root is refused at the read naming both nodes. The walk relies
on the link every walker makes before recursing; a bare `render()` links
nothing, by contract, so a child rendered by hand before any walker
reached it is its own root for that read. An undeclared root is
unchanged. `set_keyframe(t)`/`clear_keyframe()` are the preserved
time-only surface — exactly `set_state(time=t)`/`clear_state('time')`.
Clearing is reversible by re-render: an operation records whatever
value `render()` computed, so a bound tree has no symbolic form left
to recover until it re-renders (ADR-051).

An entry is addressed to the whole tree or to one instance in it
(ADR-056 stage 3a). A **qualified driver id** is the dotted path of
linked child names from the addressing root plus the class-local
driver name — `x_axis.motor`; a root-declared driver keeps its bare
name. `set_state(**{'x_axis.motor': 8000})` reaches only that
instance's subtree, stripping the consumed segment as it descends, so
two instances of one class hold independent values for their
same-named driver. `time` remains the one global entry and propagates
flat. A bare project-driver name stays valid while exactly one
declared driver in the tree bears it; when two do, binding fails
naming both qualified ids rather than silently giving them one value.
The propagation walk links each child before recursing, exactly as the
scad and serializer passes do, because a name is derived by the parent
and an unlinked node has none. Qualification never falls back and never
sanitizes: a driver reachable only through an unlinked node, or through
a list-held child's `<attr>-<index>` name (a legal node name, an
illegal expression identifier), raises. `solid_node/node/qualified.py`
owns the id, the linked walk, and `DriverToken` — an `OpenSCADConstant`
subclass whose string *is* the qualified id, so ordinary solid2
arithmetic and `solid_node.math`'s degree trig retain native shared graphs
behind a compatibility facade until publication (ADR-101).
It also carries `DriverDeclaration`,
which is both the marker the node layer needs to recognize a
declaration and the data descriptor that hands its bound value back
(ADR-056 amendment) — the same responsibility over the same `_states` dict, and
the same shape `Port` already had. What a driver *means* stays in the
simulation layer, which subclasses it.

An assembly's lifecycle is **`render()` at rest, `simulate()` per
instant** (ADR-066). `render()` declares structure and places what does
not move, reads no driver, time or port, and runs once per instance;
`simulate()` — a no-op in the base — is run by the framework after it
on every enumeration of the children, under the current binding, and
is where drivers, `self.time` and ports are read. Both run inside the
wrapper `__init_subclass__` installs (`_lifecycle_render`), so every
walker still calls `render()` and gets a tree posed for the binding.
Operations applied in `simulate()` are **motion**: inserted at the head
of the node's single `operations` list, before every rest placement, so
composition in list order puts motion inside placement; they are tagged
with the simulating assembly (**animator-tagged idempotency**, ADR-023;
tag renamed from "driver" so that word can mean a simulation input) and
each run sweeps only its own tags before re-expressing pose absolutely.
Rest placement (untagged) survives; independent animators of one node
don't disturb each other. The phase stack lives in
`solid_node/node/phase.py`; `DriverDeclaration.__get__`,
`AssemblyNode.time` and `BoundPort.value` report a read to the innermost
render phase, and a `render()` whose first run read one keeps the
previous behaviour — re-run, tagged, swept — and warns once per class
with a `FutureWarning`. `omit()` in `simulate()` raises. Leaves never
simulate; a flexible leaf renders from its bound ports when the tree is
walked.

**Ports** (spec `ports`) are domain-typed connection points declared
as class attributes (`RotationalPort`, `TranslationalPort`,
`SignalPort`), exported from `solid_node/motion/ports.py` — the module
that answers what moves and what drives what, not `solid_node.node`,
which has no port or time-base export (ADR-087): stateless declarations
carrying domain, unit, direction,
and an optional design-units-per-native-unit scale, discoverable off
the class via `declared_ports()`, with per-instance value slots
materialized by descriptor. `connect(source, sink)` on internal nodes
is causal, immediate, per-render rebinding — value flows one way,
scaled by the sink; no flow variable exists yet (the bond-graph
extension ADR-056 reserves). The declared time base, `Time`, lives in
the same module for the same reason `Port` does: it is a declaration
descriptor with a per-instance value.

**Joints** (spec `joints`) are the three one-coordinate declarations,
`Revolute`, `Prismatic` and `Orbit`, and the one that is not a lower
pair, `Free`, exported from
`solid_node/motion/joints.py` and declared as a class attribute of the
node they move (ADR-088, ADR-094, ADR-095, ADR-097, ADR-098). **A joint is
stated in the frame of whoever declares it** (ADR-097): a joint written
in a CLASS BODY is the body's own statement about itself, so `axis` and
`at` are read in that body's OWN REST FRAME — the frame its own
`render()` states its geometry in, one rest placement away from the
parent's, and the frame MuJoCo's `<joint pos>` reads too — with an
optional `(lo, hi)` `range` and a `unit`; an `Orbit` states one further
own-frame point, `carries`; a `Free` states only `at`, with an
`angle_unit` and a `length_unit`, and takes no axis and no range. `at`
defaults to `(0, 0, 0)`, the body's own origin, so a joint whose line
runs through the body's own origin — a wheel on its own bearing, a gear
on its own axle — is written with no anchor at all; `Orbit`'s `carries`
defaults to `(0, 0, 0)` for the same reason. All of them resolve
per instance at realization, from numbers, tokens, derived formulas, or
a callable of the realized node, and are outside identity.

**A joint may also be declared at a DECLARATION SITE** (ADR-098): passed
as a keyword where a parent declares a child, it is the PARENT's own
statement about a child it is placing, read in the DECLARING PARENT's
frame — URDF's rule, the frame `render()`'s `translate`/`rotate` on that
child are written in — rather than the child's own. `at` defaults to
`(0, 0, 0)`, the DECLARING PARENT's own origin this time, so a child the
parent translates swings about the parent's origin unless `at` names the
child's own placement — the reading a shared catalogue class (a bought
bearing, a fastener) needs, since its own class body cannot state a line
belonging to the assembly that places it. An `Orbit`'s `carries` keeps
ADR-094's asymmetry: WRITTEN at a site it follows `at` into the parent's
frame; DEFAULTED it is still the CHILD's own origin, reviving ADR-094's
`_OWN_PLACED_ORIGIN` sentinel for exactly this case. A site joint may
ride a `.repeat()` — one declaration, every copy's arguments resolved
once against the same parent, each copy's own rest placement supplying
the number a sign, a flag or an index would otherwise have to. A site
joint of a name the child's class already declares REPLACES that
declaration WHOLE and keeps its slot (ADR-093's rule, one writer further
out); a site joint of a new name is appended after every class-declared
joint, in keyword order. A callable argument at a site is called with
the REALIZED DECLARING PARENT, never the child and never a `.repeat()`
copy's `index` (not yet assigned when a site's arguments resolve). The
declaration works by SPECIALIZING the child's class — a subclass built
once per site, carrying the site's joints as ordinary class attributes,
its `__qualname__`/`__name__`/`__module__`/source file copied from the
written class verbatim so a joint stays outside identity and `isinstance`
holds, though `type(x) is C` no longer does. Site-declared joints are the
one case whose operations ARE carried: through the inverse of the
child's own rest placement, since their arguments are stated in a
different frame from the one they are placed in — restoring the
inversion a class-declared joint does not need — so a rest placement
the framework cannot evaluate numerically refuses binding a
site-declared joint by name, where it would not refuse a class-declared
one on the same body.
A joint OWNS one or more coordinates and every one of them is a
**port**: `Joint`
holds a `Port` rather than subclassing one, `declared_ports()` reports
them through a duck-typed `coordinates` mapping (ports cannot import
joints, which import ports), and
`declared_joints()` is the sibling enumerator for the axis and the
anchor. **The naming rule**: a joint owning ONE coordinate names it
after the joint; a joint owning SEVERAL names each
`<joint name>.<coordinate name>` — `pose.roll` — and that one string is
the port's name, the enumerator's key and the tail of a relation path,
with no second spelling. An enumerated port name is therefore not
guaranteed to be a Python identifier, and a dotted one is deliberately
NOT a wiring keyword: both wiring roles are refused at class definition,
and such a coordinate is reached by assignment on the instance, by a
relation, or by a driver or an expression. A joint owning several does
not stand for any one of them: named as a relation end, or as the one
joint of a node named as one, it is refused listing what it owns.
Binding the coordinate PLACES the body, at the binding: the framework
uses the resolved axis, anchor and any further declared point AS THEY
RESOLVED, with no transformation — a joint's operations were always
placed innermost, before every rest operation, in the body's own frame,
so there is nothing to carry them through. The normalized axis is
snapped to an exact 0/1/−1 within `1e-9`; an anchor is published exactly
as the author wrote it. The framework applies ordinary
`Rotation`/`Translation` objects — `translate(-anchor)`,
`rotate(value, axis)`, `translate(anchor)` for a revolute, the two
centring translations omitted when every anchor component is zero
within `1e-9`; one `translate(value * axis)` for a prismatic; for an
orbit ONE translation, `(cos(value) − 1)·v + sin(value)·b`, where `v` is
the component of the carried point across the line and `b` is that
vector turned a quarter turn about it; and for a free joint up to SIX —
the centring pair around `rotate(roll, x̂)`, `rotate(pitch, ŷ)`,
`rotate(yaw, ẑ)` about the declaring body's own rest-frame's three unit
directions, then one translation outermost, `x`, `y` and `z` displacing
along those SAME rest-frame directions rather than along whatever the
rotations have just turned. A body its parent ROTATES therefore carries
its joint line WITH it: the line a class-body joint states is fixed in
the body, so one class placed at several sites, or several attitudes,
states one joint and gets the right line everywhere. An orbit is the
body carried round the line without turning: its coordinate is an
angle, its operation carries no rotation at all, and the point of the
body it carries is `carries`, defaulting to `(0, 0, 0)`, the body's own
origin. Its radius and phase are DERIVED from the point and the line
and can never be declared, so a project forbidden to type its bore
centre can still state the joint; a carried point ON the line derives a
radius of zero and is refused by name at the first binding, the one
joint refusal that is not made at realization. A rest placement the
framework cannot evaluate numerically no longer prevents a joint from
being bound: nothing inverts it, so nothing can fail to invert.

A `Free` is the six freedoms of a body with no parent to be jointed to —
a walking robot's chassis (ADR-095). Its composition is fixed by the
contract, innermost first,
`R(roll, x̂) · R(pitch, ŷ) · R(yaw, ẑ) · T(x, y, z)`, which as a matrix
product is `T · Rz(yaw) · Ry(pitch) · Rx(roll)`: the extrinsic x-y-z
sequence the aircraft convention states as intrinsic yaw, then pitch,
then roll, and the product the hexapod's chassis applies by hand and
inverts for every leg solution in the model. Binding ANY of the six
re-places the whole joint from the values the six then hold, so the
composition never depends on the order they were bound in; an UNBOUND
coordinate places nothing — no rotation, a plain numeric `0` in the
component its direction reaches — while still reading as unbound. The
whole run is one contiguous block at the joint's own declaration slot,
so a `Free` composes with a `Revolute`, a `Prismatic` or an `Orbit` on
the same body exactly as they compose with each other. `Free` carries
Euler angles and gimbal-locks at `pitch = ±90°`; a quaternion-valued
`Spherical` is the joint that does not exist yet.

The operations are always placed as motion, whatever phase is current
(`apply_joint_motion` in `node/base.py`, the joint's own seam, because `_place_operation`
appends outside a phase and a carried line must stay innermost);
under a `simulate()` phase they are tagged and swept like any motion.
A rest placement that is not numeric is refused by name rather than
placing the body about a wrong line, and a numeric binding outside the
declared range raises `JointRangeError`.

Several joints on one body — a disk that spins on its own centre while an
orbit carries it round another line, say — compose in **declaration
order**, innermost first (ADR-093): the first joint `declared_joints()` reports is applied
closest to the body and the last is outermost, whatever order their
coordinates were bound in — by hand, by a wiring, or by relations a
solver reached in an order the class body does not show — so a class
read top to bottom reads a machine from the body outward. Each joint's
operations are one contiguous run at its own slot, which is what makes
re-binding one joint of several, a sweep and re-bind, and two
assemblies animating different joints of one node all leave the
composition alone. A node's motion block therefore has two parts:
the joint block by declaration slot, then hand-written motion in call
order OUTSIDE it (`_insert_motion`, unchanged, is the hand-written
path). Hand-written motion and joint motion still coexist on one node —
nothing is deprecated.

**A relation** (spec `couplings`) says that one coordinate's motion IS
another's: `a.drives(b, ratio=…, offset=…, law=…)`, written as a
STATEMENT in a class body and recorded on the class (ADR-089). An END is
coordinates of five kinds — a port or joint of the declaring class, a
child declaration standing for its class's one joint, a path reference
through declared children (`shoulder.art2.art3.wrist`), a `Driver`
(a source only), and a derived coordinate — **and an end may be SEVERAL
of them at once** (ADR-100): a source group is written with `&`,
`(count & next_count).drives(pawl.swing, law=…)`; a driven group is
written as a tuple or with `&`, `x.drives((rod.spin, rod.lean), law=…)`.
`&` is free on every declaration that carries `drives`, chains flat
(`x & y & z` is one group of three), and is refused on anything that is
not a coordinate or on an already-stated relation (the missing-parens
case, `count & next_count.drives(...)`). A group names at least two
coordinates, none of them named twice, none of them named on both sides
of one relation naming several ends, and holds no other group. `drives`
states the MECHANICAL direction; which way the framework SOLVES it is
decided per run from whichever end is bound — except a relation naming
several ends, which is FORWARD ONLY, whatever its law offers, because
recovering n sources from m driven values would mean comparing or
solving values. The law is project code handed in: `law=` is a callable
of two arguments, called once per instance at realization, each argument
the realized OWNER of the coordinate its side names, or the TUPLE of
owners when that side names several. It returns anything with `forward`
and optionally `inverse` — the framework looks up no hook on any class
and never learns what a gear is. `forward` is called with one positional
argument per source and returns the driven value itself for one driven
end, or a SEQUENCE of exactly as many values, in written order, for
several — checked by name at every application, because a value slot
takes whatever is put into it and a wrong-shaped return would be a pose
nobody stated. A **derived coordinate**, a linear formula over
coordinates (`art3.elbow - shoulder`, `wrist + 2 * tool`), is itself a
coordinate: it owns a `Port` as a joint does, reads on an instance as a
bound slot, is reported by `declared_ports()`, and solves in both
directions through its one unknown — a group is never a term of one, and
a group is not itself a coordinate: the guidance a project follows is
that a LINEAR combination is a derived coordinate and keeps both
directions, and anything else is a `law=` over several sources and loses
the reverse.

**A relation whose driven end passes through a `.repeat()`ed child is a
BROADCAST** (ADR-096): it resolves to one relation per realized copy, at
the position its declaration was written, in copy order, so the fixpoint
still runs one flat pass. `law=` is called once per COPY rather than
once per instance — the owner of the driven coordinate under a broadcast
is the copy, which is what lets a per-copy sign, phase or rank be one
attribute read, the copy's `index` (a plain 0-based instance attribute
`RepeatDeclaration.realize` stamps AFTER construction — never a declared
parameter, never part of identity, never a child name); `ratio=`/`offset=`
resolve once against the declaring instance and the resulting `Affine`
is shared by every copy. A repeated end is a driven end only: named as a
source it is refused at class definition, and once bound it is never
read backwards, whatever its law offers — the n copies would have to
agree on one source value, which the framework does not decide by
comparing values. `get_coordinate(node, name)`, exported beside
`set_coordinate`, is the matching reader for any name `declared_ports`
reports, plain or dotted. A driven GROUP fans out the same way, one
record per copy holding that copy's several driven ends, provided every
member passes through the SAME repeated segment (a group mixing a
broadcast with a plain end, or two different repeats, is refused at
class definition); the record's `copy` is the node the repeated segment
itself realized, which can differ from a member's own owner when the
path continues past the repeat (`legs.femur.lift`'s copy is the leg, not
the femur).

**The simulate phase runs in a fixed order** (ADR-099 over ADR-089):
first the framework CLEARS the value and binder record of every
coordinate this assembly bound during its PREVIOUS phase — the author's
own `simulate()` included — without which a value slot would still hold
the last instant's value, or a rest-default joint would keep a stale
number once its swept motion had already gone; then the author's
`simulate()`; then the class's wirings and relations, ATTEMPTED
TOGETHER to a fixpoint, each relation applied from whichever end is
bound and each wiring binding as soon as its source is. What one
instance's own attempt cannot reach is DEFERRED rather than refused. A
slot some OTHER assembly has already (re)bound in the CURRENT
enumeration is left uncleared — a coordinate's own `_enum_marker` says
which enumeration last bound it, so a stale record from this assembly's
own PREVIOUS phase never wipes out a value another assembly's phase,
earlier in the same cascade, just produced. All of it happens while the
phase is still that assembly's, so a relation's motion is tagged and
swept exactly as a hand-written rotation is.

**One ENUMERATION is one tree pass** (ADR-099): the outermost `render()`
call that finds none already open OWNS it, and drives every assembly's
phase in the subtree it renders — parents before children, declaration
order among siblings, linking each node's children before attempting
its own relations so a refusal names them by path — before that call
returns. Because each instance attempts its own relations in its own
phase and phases run parent-first, an ancestor's relation reaching a
coordinate by path still binds it before the descendant's own relations
run — the 30-site guarantee the catalogue depends on, unchanged. Once
every phase in the subtree has run, the pass propagates over everything
DEFERRED to a fixpoint, in tree order, and only then refuses
`UnreachedCoordinate` or `NotInvertible` for what is left; a
`DoublyBound` coordinate is never deferred, because it is a
contradiction and not a question of timing, and refuses where it is
found. A READ of a coordinate a relation, a derived formula or a wiring
binds is recorded while it is unbound and judged the same way, at the
end of the pass: bound afterward by that binder — refused, naming both
classes; bound afterward by the reading class's OWN author code instead
— not refused, which is the rest-default guard the catalogue's own
sites write. A subclass assigning a relation to a name a base already
used REPLACES it, at the base's position in the enumeration (the rule a
redeclared joint already obeys, ADR-093); a bare statement, or a name no
base used, stays additive. A node's phase, once run, is marked against
the enumeration so a walker that revisits it while that SAME enumeration
is still open does not run it again; the mark is not honoured against a
merely-remembered PAST enumeration, because `set_state`/`clear_state`
and `qualified.drive_tree` may bind a fresh snapshot and call `render()`
again with none currently open. `set_state`/`clear_state` and
`drive_tree` therefore deliver their whole snapshot over the tree AT
REST first — a rest-only descent, no phase touched — and enumerate
exactly ONCE afterward, so a descendant simulates against the binding
just requested rather than the previous one.

World pose is one composed 4×4 matrix — own operations then ancestors,
premultiplied (ADR-028) — recomputed on *every* access because
operation values can be animated expressions and the operations list
is mutated by design. The base mesh under it is cached per strong artifact
observation, and each caller still receives a mutable copy (ADR-085, amending
ADR-028).

### Simulation (NODE · spec `simulation`)

`solid_node/simulation/` is the layer that *produces* driver
snapshots (ADR-056 stage 2); `solid_node/node/` never imports it, so
a node without drivers pulls none of it in. `Driver` is a frozen
class-attribute declaration on an assembly (default, range, unit,
optional `dtype=int` for discrete devices, optional scale in design
units per native unit), discovered off the class MRO exactly like
`declared_ports` and read off an instance exactly like a port
(ADR-056 amendment); all mutable state — current value, active program —
lives in the per-simulation bank a `Sim` builds, so two simulations
share nothing and there is nothing to reset. `RampProgram` advances
state as a pure function of the tick (`start + delta*k//n` for
integer drivers — integer-exact, exact landing), which is what makes
two runs of one scenario comparable with `==`. `Instruction` records
design-unit targets plus a duration; conversion to native state
happens once, at trigger time, through the driver's declared scale.

`simulation/enumeration.py` is the **one authority** on what drivers a
machine has (ADR-056 stage 3a). `declared_drivers(cls)` reads a single
class, which stops being enough the moment a machine is built out of
mechanisms — a printer's drivers live on its axes and its root may
declare none. `qualified_drivers(root)` walks the linked tree and
returns `{qualified_id: Driver}`, binding each declaration's own
default as it descends because finding children means rendering.
Everything that names a driver reads it: the `Sim` bank,
instruction-target resolution, the loader's opening snapshot, and the
serialized document's driver table — so the id in the document and the
key in the bank are the same string by construction rather than by two
implementations agreeing. `qualified_instructions(root)` does the same
for instructions, which are declared with class-local target names and
qualify by their declaring node's path.

`Sim` is the fixed-`dt` loop: instants become integer tick counts the
moment they are stated (rejected if not whole — the ADR-050 reasoning
applied to simulated time). Public time values are finite real seconds,
excluding booleans; `dt` is strictly positive, while run and instruction
durations are nonnegative (ADR-083). Those boundaries are validated before
state changes. Absolute `at(t)` scheduling rejects a tick already passed but
accepts the current tick, whose deferred actions can fire through `run(0)`.
A zero-duration instruction settles and binds its complete target snapshot at
the current tick without adding a trajectory entry. Construction enumerates
the whole linked tree and binds every declared default through `set_state` by
qualified id before the first render, so a driverless root with driver-declaring
children simulates. The bank, trajectory, programs, and instruction
targets all key by qualified id, and `trigger('x_axis.Home')` ramps
only that instance. Each tick advances programs and binds the full
snapshot together with the global `time` entry set to the exact
instant `k*dt` **in seconds**, computed from the integer tick count
and never accumulated — so under a simulation `self.time` reads the
stepped clock, while the normalized 0..1 `$t` animation path outside
simulations is untouched. Then it records the trajectory and runs
deferred `at(t)` actions (`.trigger(name)`, `.run(fn)`) and cadence
`every()` slots, each accounting its own cost — ticks are free,
cadence budgets assertion cost. `ScenarioTest` composes over the CAD
`TestCase`: one class runs unchanged under pytest and the `solid
test` runner, building STLs only when `meshes = True`.

Known stage boundaries (ADR-056 stage 3c+ territory): `range` is
declarative metadata, not a clamp; `Driver.scale` and `Port.scale`
remain two declarations; a driver on a list-held child is forbidden
rather than sanitized; the viewer's `trigger` runs one instruction's
ramps and nothing sequences them — programs and G-code are a later
layer, and determinism belongs to `Sim`, not to the client animation.

### Build pipeline (BUILD · spec `build-pipeline`)

Nodes are addressed by **reference** — a declared model name, a qualifier
(`package.module:Class`), a filesystem path, or a path plus class —
dynamically imported and resolved against a project root discovered
from the nearest ancestor `pyproject.toml` carrying `[tool.solid-node]`
(ADR-005, superseded by project-manifest-node-references). A bare path
to a file defining several node classes must name the one meant in the
reference; implicit discovery remains limited to classes defined in the
loaded file. Artifacts remain keyed to the selected class's real
implementation source. The source set tracks that implementation/import
closure, so an edit to it invalidates and reloads the active node.

A project has one model, `model = "package.module:Class"`, or several
declared by name in `[tool.solid-node.models]`, with `model` then naming
the default by its key (ADR-073). A name is one word, so it is never
mistaken for a qualifier or a path, and it may not equal a directory at
the project root. The **build root** is `$SOLID_BUILD_DIR` (default
`_build`, resolved against the discovered project root rather than the
working directory). A single model builds in the root itself; a declared
model owns `<build root>/<name>/`, with its own published document,
errors file, lock and sweep, so publishing one model never disturbs
another. A sub-node reference builds in the root, whose sweep does not
descend into a model's directory. Every command selects before it loads:
the selection turns a name, or the default, into the concrete reference
and the directory it owns, anchored for the process and inherited by the
fresh interpreters it starts. Within a build directory artifacts mirror
the source layout, basename `<script>-<uniq_id>`.

Loading a node also **binds its declared driver defaults** across the
tree by qualified id, before the first render (ADR-056 stage 3a), so a
driver-declaring project builds, tests, and serves through the CLI
without restating its declarations in `__init__`. A tree that declares
no driver is left strictly alone — not bound, not even walked, since
the walk renders — so a driverless project loads exactly as it always
did. The binding lives in the loader, which may import
`solid_node/simulation/`; the node layer never does, and a hook there
for the simulation layer to register into would hide that dependency
rather than place it.

Project-local source execution belongs to one request-local **source
generation** (ADR-084). The loader observes and coherently reads the selected
entry/facade and every project module before executing its bytes, then requires
an uncached post-load identity match; it does not trust timestamp-and-size
`.pyc` validity. Late imports join the same handshake while external packages
keep Python's ordinary import behavior. Artifact-producing phases share one
distinct-path source census internally and compare fresh uncached observations
at their boundaries. Assembly seals the recursively discovered Python and
foreign SCAD/JS/STL/STEP contributors; later retained passes, asynchronous
renderer waits and publication must still match that generation. A missing,
replaced, retargeted, newly selected or changed contributor returns
`SOURCE_CHANGED` before a stale document can be published.

STL generation is asynchronous only at an actual OpenSCAD backend:
`StlRenderStart` carries that spawned process, PID lock files guard concurrency,
and `build_stls()` loops until nothing is stale. Exact and imported producers
run natively; faceted fusion unions current child meshes through Manifold in
dependency order. The metadata-only currency path is
**artifact mtime equality plus source-set fingerprint equality** — generated
files are back-dated with `os.utime` to the max source mtime (ADR-006), and a
sidecar records path, filesystem identity, size, mtime, and change time for
every member of `node.files` (ADR-081): the node's own source
plus its project-local import closure, unioned upward from children
(ADR-033) — and, for an imported mesh, the closure of the wrapper module
that declares it as well, since the mesh file has no imports of its own to
walk and the wrapper is where its geometry-affecting code lives (ADR-055).
Both sides of that equality are integer nanoseconds
(`st_mtime_ns`, `os.utime(ns=…)`), so the back-date is a fixed point at
whatever resolution the filesystem stores — a float stamp is not, and on a
millisecond-resolution filesystem it left every artifact permanently stale
and this loop non-terminating (ADR-050).

A producer recipe mismatch is first a hard cache miss for artifacts whose
production semantics changed; faceted fusion includes child recipes so nested
caches migrate. A timestamp or fingerprint mismatch then invokes the node-scoped content digest
(ADR-060/071/102). Equal content restamps the artifact and refreshes the sidecar
without rendering, which preserves cheap clone, checkout, relocation, and
sibling-only changes. A legacy digest-only sidecar follows this path once and
upgrades in place. Settled checks stat tracked files and read the sidecar, but
never read source contents or parse Python.

OpenSCAD availability is resolved once per process, at the first operation
that actually requires it (ADR-046/102). Solid2/raw-SCAD STL rendering, a
declared legacy SCAD-only adapter, Solid2 symbolic-value evaluation, and the
OpenSCAD snapshot renderer are the complete requiring set. A missing binary
raises one actionable error naming the operation and remedy before subprocess
launch; an all-exact build never performs the check.

A rigid, optimizing **leaf** whose artifacts are current assembles by
importing its STL — `render()` and `as_scad()` never run (ADR-033), so
the check happens before the expensive work rather than after it.
Internal nodes always prepare: their file set is the union of their
children's and is only known by walking them. Native adapter materializers —
CadQuery, build123d, sheet, JSCAD and imported STL — carry the same guard for
nodes that opt out of optimization. A flexible leaf
carries it per binding: mtime equality decides *source* currency within one
binding exactly as elsewhere, and a different binding is a different file
rather than a question mtime is asked and cannot answer (ADR-057).

`solid build` and the watchdog-driven development loop start one builder per
sealed source generation (ADR-084, amending ADR-067). Every child still starts
from a **fresh interpreter**, never a fork of the command process: parent model
resolution may initialize OCCT's OpenMP team, whose bookkeeping a fork would
inherit without its threads and then deadlock on parallel tessellation. A fresh
child receives a module-level target and plain reconstructable values. Within
one stable generation it retains the same loaded root and complete assembly
across all sequential artifact passes; source change or failure ends reuse of
that tree, so the next build attempt again has fresh native and module state.
A failed development reload writes `errors.json`, releases the build lock and
performs no more geometry while that same child remains solely as a recovery
watch over known source locations and the broad Python area; repair ends it
`SOURCE_CHANGED`. Candidate
builds publish `viewer.json` with the versioned `solid-node-export` tree
schema, linked node names, per-node `mtime`, and build-root-relative model
paths, so private NodeAPI consumers can serve a completed build without
loading project Python (ADR-031/034). Sharing that schema marker with export
does not make a build publication portable: it copies no meshes and retains
its private `viewer.json` document boundary.

SCAD publication distinguishes time-invariant and state-dependent producers
(ADR-086). Rigid base SCAD may be reused immediately only when the canonical
path's *currently published* full timestamp/digest/fingerprint identity
matches. Every non-rigid, non-flexible instance still renders and composes its
own model, but its assembly phase keeps only the immutable final desired
text/stamp/digest/fingerprint per canonical path, ordered by each path's last
occurrence. After a fresh pre-flush check it compares and atomically publishes
those final values under the active census and project lock, then checks the
source generation again. Body/pre-flush failure discards them; flush error
uses the ordinary assembly failure path. Flexible bindings and direct calls
outside the assembly phase remain immediate.

Artifacts write directly into one ordinary build directory. Each artifact is
written to a temporary sibling and replaced with `os.replace`; OpenSCAD renders
to a temporary STL and publishes it only on completion. `viewer.json` is the
manifest and is written last, so it never names a partial artifact; a later
sweep removes files it no longer names. A build whose artifacts are all current
still republishes that manifest when it no longer matches the model, since the
pass that renders an artifact exits before writing the document. The project
lock serializes builders, while readers remain lock-free. This intentionally
permits a mixed model during a build and a failed build can leave partial new
work, but no reader sees a torn file (ADR-038, reversing ADR-030 and
superseding ADR-032). Errors go to an atomically written `errors.json` in the
build dir — file-based IPC, no broker
(ADR-018). A broken initial build kills develop; a broken reload waits outside
the lock for a relevant repair, then exits `SOURCE_CHANGED` so the supervisor
starts a fresh child and source generation.

An exact rigid node has a private `.brep` beside its `.stl` (ADR-044). Both
must match the node mtime for the build to be current; the BREP is spared by
the artifact sweep but is never named in a viewer or export document. That
freshness rule is why a flexible leaf persists no exact geometry at all: the
`.brep` requirement is scoped to nodes that are both rigid and exact, the
sweep spares `.brep` files unconditionally by extension so per-binding ones
could never be collected, and nothing reads them anyway — the exact
composition path fuses the shapes children *return*, and a fusion refuses a
flexible child (ADR-057). An
all-exact fusion is the exception to the subprocess protocol: it writes its
BREP and tessellates its fused shape synchronously in process (ADR-045).
Every exact artifact's STL, a leaf's or a fusion's, is written without the
zero-area triangles OCCT's mesher emits, so the mesh engine's edge pairing
sees only the surface (ADR-074). The tessellation itself is at whatever
`linear_deflection` (mm) and `angular_deflection` (rad) an `ExactLeafNode`
or `FusionNode` subclass declares as a class attribute — 0.1 and 0.1,
the framework's historical values, when it declares neither — read and
validated once, immediately before each write (ADR-077). Precision is
not artifact identity and rides the node's own source set instead
(ADR-071), so redeclaring it rewrites the same `.stl` in place; the
`.brep` and `shape()` are unaffected, and a fusion's declaration shapes
only its own fused solid, never a child's.

The artifact sweep learns one thing from the tree rather than from the
document. A flexible leaf's snapshot is addressed by its binding, and the
published document is symbolic — it describes the machine, not the pose —
so it cannot name the file the assembled SCAD imported. The assembled tree
can, and it is the same tree that publication describes, so each flexible
node's `snapshot_file` joins the referenced set and every other binding's
snapshot is swept. A build whose only change is the binding writes no new
document and therefore runs no sweep, so one superseded snapshot survives
until the next document-changing build (ADR-057).

Publication enforces build mechanics and model validity, not project-selected
geometry contracts. It therefore does not count STL components or invoke
whole-solid connectivity assertions. The incomplete-render guard remains: a
manifest may not name a rigid artifact that has not been written, independently
of any geometric test (ADR-039, amended 2026-08-10).

### CLI (BUILD · spec `cli`)

`solid <command> <path>` — command-first grammar since 0.4, with an
exit-2 migration guard for the old order (ADR-024). Commands are a
duck-typed registry naming where each lives: `build`, `develop`, `test`,
`snapshot`, `new` (offline scaffold), `export`, `viewer`, `models`.
`models` lists a project's models from the manifest and their build
directories alone — `unbuilt`, `published` or `failed` — as text or
`--json`, importing no project code; `build --all` and `test --all` walk
every declared model in order and never stop at a failing one (ADR-073).
Every command
that loads a node takes `--set name=value`, registered once beside the
shared reference positional: the loader parses each value by the root's
declared kind and constructs the root with the overrides, the develop
loop carries them into every builder it starts, and an unknown or derived
name fails listing what is settable (ADR-062). Only the invoked
command's module is imported, and the node and simulation packages resolve
their exports on first access, so a command pays for the backends it uses and
not for the rest (ADR-059) — `solid viewer` answers from the viewer's entry
point alone. Top-level `-h` is the exception: it renders every command's
docstring, so it loads them all. The test framework defers the same way by a
different mechanism (ADR-069): a module's own call sites are global reads,
which PEP 562 never sees, so `solid_node.test` binds its seven
`solid_node.exact` names to deferred callables that import on first call and
replace themselves unless patched. A faceted-only project runs its whole suite
without importing cadquery. Snapshot has an explicit renderer choice
(ADR-021/041/046/068): OpenSCAD remains the external-tool default with xvfb
fallback, whether or not the browser viewer is installed, while the
optional `web` renderer stages the node and has the installed viewer package
photograph it in sandboxed headless Chromium to produce a true-alpha PNG.
Unsupported renderer-specific options are rejected rather than ignored or
substituted. If the default OpenSCAD renderer is unavailable, the command
names `--renderer web` but does not select it silently; if the viewer is
not installed, `--renderer web` names the `viewer` extra. `./.env` is read with
`setdefault` semantics (real environment wins), carrying
`SOLID_NODE_PORT` / `SOLID_NODE_FRONTEND_PORT` / `SOLID_BUILD_DIR`.

### Test framework (TEST-FRAMEWORK · spec `test-framework`)

Test-driven CAD is the framework's reason to exist: contracts about
geometry, checked on the real meshes. Tests live in companion files or
on the node via `TestCaseMixin` (ADR-010), run by `solid test` — which
builds first, then runs `test_` methods per declared animation instant
(`@testing_instant` / `@testing_steps`, ADR-011) with operation
checkpoints restored between instants.

Collision assertions (ADR-009/044) select the strongest shared representation
the run allows: intersection-volume and connectivity questions use placed
OCCT shapes when both operands are exact and retain trimesh/Manifold for
mixed or faceted pairs. Which kernel a run compares on is the run's property,
not the model's (ADR-073): `solid test` resolves one comparison policy —
`--exact`/`--faceted`, else `SOLID_TEST_KERNEL` from the project's ignored
`.env`, else exact — and a faceted run answers every one of those questions
on meshes, reads no `shape()`, applies one run-wide volume epsilon to every
engine verdict after the memo is read, and labels itself before the first
build and on its summary line. The exact run is unchanged, `node.exact`
still reports the geometry's capability, and the build does not depend on
the kernel. That selection reaches the placement step too (ADR-052): a solid is
placed into the spatial index from its cached bounds alone, and its Manifold
is built only when a comparison really reads it, so an all-exact assembly
builds none and needs no mesh engine. Distance and containment assertions
remain mesh-sampled. This includes the
**paired kinematic fit contract** (ADR-025): `assertBlockedBeyond` +
`assertFreeWithin` perturb a part along its working degree of freedom
(rotational `axis=` or translational `along=`, injected before every
operation of the node so the direction is the node's own and all of its
rotations carry it, ADR-075; always restored) — fit is certified only by the
pair. `volume_epsilon` separates real interference from boolean noise,
with a deliberately strict default: a flush contact that is non-empty
at exactly 0.0 mm³ **is** a foul until the test opts into an epsilon.

The shared intersection path (ADR-029/044) caches one Manifold per strong
artifact observation — canonical path, device, inode, size, nanosecond mtime
and change time — built at the first faceted read and judged there by
the engine's own `status()` (ADR-074): a mesh Manifold refuses raises by
file name with the engine's reason, a mesh trimesh doubts and the engine
accepts is compared, and selection, the broad phase and the exact path
never judge a mesh at all. It culls provably disjoint pairs with a
conservative world-AABB broad-phase of its own — always world axis here,
whatever indexing frame the whole-assembly interference index below may
have chosen for its own candidates (ADR-091) — and reads
`is_empty()`/`volume()` straight off lazy-transformed Manifolds —
verdict-identical to the naive faceted path. Exact pairs share the same
world-AABB
broad phase, then a second exact-negative tier (ADR-092) may decide the
pair empty before any boolean: each solid's face boxes
(`BRepBndLib.Add_s(face, box, False)`, a pure function of the exact
surface, cached once per shape identity) are compared in one solid's own
frame, enlarging only the other solid's boxes by a fixed margin, and if
none meet, a containment guard — one representative vertex of every
solid of each shape classified against every solid of the other, in both
directions — tells a genuinely disjoint pair from one solid wholly inside
another before reporting it empty; disjoint face boxes alone are never
by themselves a verdict, because two closed solids with disjoint
boundaries may still be nested rather than separate. Anything the tier
cannot prove — a faceless or solid-less shape, a vertex-less solid, a
non-finite relative placement, or any classification that is not
strictly outside — falls through to OCCT common exactly as before, and
flush contact still reaches the kernel because touching face boxes count
as meeting, and interpret "contains no solid" as empty there; kernel
failure raises and never falls back. `volume_epsilon` is
ignored with a warning when every comparison in a call was exact.

Verdicts are memoized within a run (ADR-070, amended by ADR-090). The
identity of an intersection question is `(both geometry identities,
evaluation path, the run's placement quantum, the relative rigid placement
quantised to it)` — the relative matrix `inv(M1) @ M2` divided by the
quantum and rounded to integer cell indices, so a pair carried together by a
shared parent is the same question even though composing the parent's
placement through each child's own chain leaves float noise between the two
matrices, while a pair that genuinely moved relative to each other is not.
The quantum is a stated property of the run (`placement_quantum`,
`--placement-quantum`, `SOLID_TEST_PLACEMENT_QUANTUM`), resolved and
validated before the kernel is chosen and carried by both kernels' policies;
its default of 1e-9 mm merges only placements IEEE 754 arithmetic could not
have told apart in the first place, and `0` restores the exact-bytes key
ADR-070 specified. This is a judgement about arithmetic noise, not about
material: deciding that two placements differing by a real, INTENDED amount
are one question stays the judgement `volume_epsilon` exists to leave with
the project, and remains untouched by the quantum. Exact and faceted entries
never serve one another, a node with no file identity is never cached, a
relative matrix carrying a non-finite entry is never cached either, and
entries are evicted when a geometry identity changes, on the same discipline
as the Manifold cache.
Bounding boxes, and the per-face bounding boxes the exact-only face-box
tier above reads, share those stable geometry identities. Exact placements use a
512-entry LRU keyed by stable shape identity and the exact placement-matrix
bytes, with no rounding; eviction merely recomputes the same placement and a
new managed `solid test` run starts empty. A stock `FlexibleNode` keeps a
separate 64-entry LRU of evaluated mesh, bounds and Manifold results keyed by
its full source identity, canonical structural identity, exact binding and
serialized shape specification. A subclass that overrides the stock flexible
evaluation seam is conservatively uncached, and flexible intersection verdicts
remain uncached: the per-instance final binding can still change between
comparisons.

The root-level integrity boundary is the first rigid node on every branch
(ADR-039/040). Connectivity is deliberately solid-local.
`assertNoDisconnectedSolids(node)` explicitly checks that every printed solid
in a selected subtree is one connected body; it reads each topmost rigid
node's local STL. `assertNoSolidInterference(node)` is its world-space
assembly complement: zero or one selected solid passes without geometry work;
otherwise the whole-assembly index takes its conservative bounds in a chosen
INDEXING FRAME (ADR-091) — the world frame, or the placement frame of one of
the assembly's `_INDEXING_FRAME_CANDIDATES` largest topmost solids by
local-bounds diagonal, whichever scores the smallest total (padded) box
volume, ties resolved to the earliest candidate with world first. A bound
taken in a non-world frame is enlarged by a fixed absolute margin
(`_INDEXING_FRAME_MARGIN`) absorbing the extra inversion and matrix product
the frame change costs in float residue, so a flush-contact pair does not
fall through it; world boxes are never padded, so an assembly that gains
nothing from the choice is indexed exactly as it is today. The choice can
only change which candidate pairs are emitted, never a verdict — a bound
taken in any invertible frame remains a superset of the solid's placed
geometry expressed in that frame, so box disjointness in one common frame
stays a necessary condition for intersection whichever frame was chosen.
Given that box list, a sweep-and-prune index estimates interval pressure on
X, Y and Z, chooses the least-pressure axis (X, then Y, then Z on ties), and
emits the potentially interacting pairs in the historical X-order before each
is settled by an exact same-kernel
intersection — the sole verification path, with no whole-assembly measurement.
Exact zero-volume boundary contact passes, every positive candidate volume
fails, and no public volume epsilon or private numerical tolerance is exposed.
A finite negative faceted candidate also passes this assembly-only decision:
it does not report positive shared material. The raw engine emptiness and
signed volume remain intact for strict pairwise and fit assertions, whose
non-empty contact still fouls. Non-finite candidate volumes still fail, and
exact-representation candidate decisions are unchanged. The candidate's
existing representation tag carries this distinction even in a mixed assembly.
Correctness rests on the broad phase being complete in whichever frame it
indexed, which is proved by
framework tests rather than re-checked at runtime (ADR-040). Up to 8,192
accepted candidates are buffered to restore that order; at the cap the buffer
is discarded and the original streaming X sweep is used, preserving bounded
memory and the same candidate set. The old all-leaf
`assertNoPairwiseIntersections` sweep remains deprecated and
behavior-compatible.

`assertAssemblySupported(node, gravity=(0, 0, -1), max_drop=1.0, ground=None,
supports=None, stability_margin=0.0)` asks the physical inverse over the same
selection and the same
placement (ADR-048): not whether two parts share material, but whether any part
is floating. A solid is directly supported by another when, displaced by
`max_drop` along the normalized gravity vector — one world-frame translation
folded into the placement matrix — it intersects that solid with positive
volume; zero-volume contact after the drop is not a hold. Those edges form a
support graph, seeded by the solids within `max_drop` of the assembly's
furthest extent along gravity (or by an explicit `ground`, resolved up from a
feature or down through an assembly), and groundedness propagates from
supporter to supported, so a mutual-lean cycle is grounded exactly when a
member reaches ground. `supports=[(supported, supporter), ...]` declares holds
the drop cannot prove — press fits, glue, friction — without grounding
anything by itself. This assertion's own boxes stay world-axis always, never
in an indexing frame chosen for the interference assertion above, because
gravity is a world-frame fact (ADR-048) and a projection along it is only
meaningful in that frame. The broad phase is the same sweep-and-prune, run over the
displaced and placed boxes at once so an emitted cross-half pair is exactly a
directed overlap; exact pairs still route to the kernel. Zero or one selected
solid passes without geometry work; a zero `gravity`, a non-positive
`max_drop`, a negative `stability_margin`, and an unresolvable
`ground`/`supports` entry are loud errors.

When reachability holds, a second phase proves frictionless static equilibrium
(ADR-049): that push-only normal forces over the detected interfaces balance
every non-anchored solid's weight and its torque about its own centre of mass,
decided by one deterministic `scipy.optimize.linprog` HiGHS solve of the
L1-relaxed feasibility program. Its constraint matrix is assembled sparsely:
each contact or declared wrench contributes only to its affected solid rows,
per-cell contributions are accumulated in the historical deterministic order,
and CSR identity and horizontal blocks preserve the same equations and
diagnostics without allocating the dense mostly-zero matrix. Interfaces are extracted by meshing each
displaced intersection and classifying its faces to the supporter's boundary by
nearest surface, so contact points and normals sit on the supporter's real,
undisplaced surface; gravity-perpendicular faces are discarded as walls the
displacement drove into. Detection runs the drop sweep and a symmetric lift
sweep through the same broad phase, the lift contributing contacts only so a
snug hole's upper wall can complete a couple, never support-graph edges.
Contact extraction and mass properties (placed facets, uniform unit density, so
weight is volume) are faceted even for exact pairs, whose edge existence still
routes to the kernel. With `ground=None` a virtual floor slab in the gravity
frame is the sole anchored body, so a default seed must balance on its real
footprint; an explicit `ground` anchors exactly the resolved solids and no
floor exists. A declared `supports` edge carries a free six-component wrench.
`stability_margin` shrinks each patch toward its centroid first. The failure
names each unbalanced solid and whether force or torque does not close, and
points at `supports=`. The assertion now claims support reachability, force
balance, torque balance and toppling over the detected contacts; friction,
adhesion, purely lateral wall reactions, single-solid floor toppling and
dynamics remain outside it.

All three integrity assertions run only when ordinary project test source
calls them. `solid new` declares the connectivity and interference pair as two
counted companion tests; non-test commands do not load that companion. `assertJoined(a, b,
min_weld_volume=...)` checks the separate pairwise claim that two named
features meet directly. It composes operations only below their enclosing
topmost rigid node, excluding whole-solid placement and every animated
ancestor. That frame is meaningful only within one part, so the assertion
refuses a pair drawn from two different solids instead of comparing them at
their own origins. Collision remains world-framed and time-dependent.

### Viewers (VIEWER-WEB · specs `viewer-distribution`, `cli`)

The browser viewer is not in this repository. It is `solid-node-viewer`, an
independent AGPL-3.0-only package installed through the `viewer` extra
(ADR-068/103); the framework is Apache-2.0 and complete for non-interactive
use without it. The OpenSCAD CLI remains the default fixed-pose snapshot
renderer, not an interactive viewer.
The framework touches the viewer in exactly two ways. `solid_node/viewers/
bundle.py` loads the viewer's `solid_node.viewer` entry point — a
standard-library-only function returning the bundle path, the export page
and the declared API version — and nothing else of it; `solid viewer`,
`solid export`, the Sphinx directive and the web snapshot all resolve the
bundle there and name one remedy when it is absent. Everything else runs the
viewer as a separate process through `sys.executable -m solid_node_viewer`.

`solid develop` opens only the browser viewer and fails before starting
development processes with the `viewer`-extra remedy when its package is
absent; `--web` remains an explicit spelling of the default, and `--no-web`
runs the builder watch loop without viewer discovery. The browser viewer is
the viewer's `serve --build-dir` process on the project's atomically published
build directory, restarted after each completed build as the in-process server
was, so the reload channel's
"greet a reconnecting browser with `reload`" contract is unchanged. The
server, the React development shell, the bundle routes and the reload and
build-error surfaces are specified in the viewer's `development-server`
capability; how the widget renders — tree traversal, world-matrix
composition, expression evaluation, animation, targeted in-place updates —
in its `viewer-package` capability. Those decisions (ADR-012/013/014/027/
035/036/037/042) are relocated to the viewer repository under their
original numbers.

The browser snapshot renderer keeps the half that knows what a node is: it
renders any stale artifact of the photographed node, serializes that node's
tree into a temporary sibling and copies each artifact from the same pinned,
strongly observed snapshot used for its piece facts, all while holding the
project build lock. It validates the observation after each copy, then releases
the lock and runs the viewer's
`capture` on that pinned staging directory with the image size, the animation
instant and the camera it resolved from OpenSCAD's syntax. It never
republishes or sweeps the build itself: the published document belongs to the
producer serving it, so a snapshot of one part leaves the rest of the project
intact. The viewer adds the bundle and a mount page, serves the directory on
an ephemeral loopback port and captures only the transparent canvas under
Chromium/SwiftShader; staging is removed after either success or failure
(ADR-041/068).

### Export and embedding (EXPORT · specs `export`, `sphinx-embedding`)

`solid export` (ADR-020/034/035/042) emits a self-contained static artifact:
`manifest.json` (`format: solid-node-export`, at the versioned tree-document
schema shared with `viewer.json` — `version: 2`, `3` when the tree holds a
flexible node, or `4` when its expressions share a subexpression (ADR-080);
not a portability claim),
deduplicated `models/*.stl`, and — copied from the installed viewer
package — a React-free three.js **widget** whose side-effect-free imperative core mounts a
published tree into a host and returns a lifecycle handle; its published entry
auto-mounts `data-solid-widget` containers, animates `$t` client-side (play/
pause + timeline when animated), and honors `?t=`/`?autoplay=0`. The browser
global exposes API version 5 so a host can check compatibility before mounting.
The handle exposes immutable assembly metadata and host-controlled subtree
focus and visibility by root-relative name path. Those inspection controls are
session state: they neither mutate nor unload the published tree, and valid
paths survive targeted updates while removed paths are discarded.
Hosts may supply camera position/target, an up direction, and field of view;
the latter two retain Z-up/50° defaults when absent. OpenSCAD camera conversion
is isolated as pure math and supplies the browser renderer with eye, target,
up, and OpenSCAD's 22.5° perspective field of view (ADR-041).

**The handle also drives the document** (ADR-056 stage 3b). A document
whose `drivers` table is non-empty loads and renders at the pose its
expressions evaluate to under the declared defaults; what is refused is
a document naming an id its own table does not declare, which has no
value to bind. The handle exposes `drivers()` and `instructions()`
verbatim, `driver(id)`/`setDriver(id, value)` in **native** driver
units (a `range` never clamps, and an unknown id fails loudly listing
the declared ones), `onDriverChange(fn)` — once per changed driver per
frame, synchronously on `setDriver`, returning an unsubscribe — and
`trigger(name)`, which converts the instruction's design-unit targets
through the driver table and ramps each target driver linearly from its
current value over the declared duration, returning `{done, cancel()}`.
Ramps advance on wall-clock elapsed time in the existing animation
loop: endpoints and duration are contract (integer dtypes are whole at
every frame and land exactly on target), intermediate values are
sampling, and a new trigger replaces an active ramp from where it
stands, as `Sim`'s programs do. Determinism stays with the Python
simulation; the client is an animation. Which operations recompute is
decided by the **free variables of their parsed expressions**, not by a
substring test: a driver change re-evaluates exactly the operations
naming it, `$t` operations keep animating from the time transport, and
a driver named `total` is never found inside a function name.

**The widget evaluates shape per frame the way it evaluates pose**
(ADR-057). It bundles molejo's JavaScript evaluator through the ADR-035
delivery path, and per flexible node parses its `params` once through the
existing expression cache, evaluates them in the existing scope (`$t` plus
the nested driver map), and hands the values to molejo. Buffers are
allocated by molejo's *first* evaluation — only that call can know the
counts, which the spec fixes — and every later binding refills the same
`Float32Array` in place, leaving the index untouched: no reallocation and
no topology change ever happens at frame rate. Gating is **one rule over
two dependency sets**: `touchedBy(free, changed)` decides both whether a
node's matrix recomputes, from its operations' free variables, and whether
its geometry does, from its `params`' — so a driver named by no `params`
expression costs a spring nothing and the two sets cannot drift into two
rules. The surface is shaded **flat**, which is a decision rather than a
default: molejo emits no normals, its mesh is indexed and shares rim
vertices between wall and caps so computed vertex normals would round the
rim, an STL arrives non-indexed and therefore already looks flat, and
skipping the pass spares O(V) work per driven frame. Two refusals stand in
the prepare phase, before the live tree is touched, so a rejected document
leaves the standing scene intact: a document version outside the accepted
set — `[1, 2, 3]` at this writing, and, once the paired viewer change
(ADR-080) that evaluates a `bindings` table lands, `[1, 2, 3, 4]` — a check
the loader previously did not perform at all — and a `flexible` node whose
`tech` this build cannot evaluate, each named in the error. Until that
viewer change lands, a version-4 document — which this framework can
already publish — is refused here by design (ADR-080): silently ignoring
`bindings` would resolve a reference to nothing and render a wrong pose, so
a version bump forces the loud refusal instead.
The tree
walk is the same rigid-stops/non-rigid-recurses rule as the NodeAPI;
operations ship as raw expression strings. Both producers use the same core
serializer, which links rendered children before recursion and includes
`mtime`; export alone maps and copies rigid models beneath `models/`.

The serializer is a pure walk: **which time a document is written in is a
producer decision** (ADR-051). `export_node` clears any keyframe before
serializing, so `manifest.json` carries `$t` whatever the caller did to the
node, and leaves it in symbolic time; the builder never keyframes; the browser
snapshot keyframes deliberately and bakes one instant through `math.py`, whose
degree semantics are the ADR-022 source of truth. A new producer states its own
time contract.

**Schema version 2 extends that guarantee from `$t` to named drivers**
(ADR-056 stage 3a). `symbolic_drivers(node)` is a serialization *mode*,
not a relaxed validator: it binds every declared driver of the tree to
its qualified `DriverToken` through an internal path — `set_state`'s
numbers-only contract is untouched, which is what keeps a bound pose a
pure function of numbers — serializes, then restores exactly the
snapshot each node held and re-renders under it. So a document
serialized from a numerically stepped node still publishes
`(x_axis.motor * 0.1125)` rather than the constant that instant
computed. Beside `root` it publishes a **`drivers` table**: qualified
id → `default`, `range`, `unit`, `dtype`, `scale`, straight from the
declaration, presentation metadata only (`range` is never a clamp), and
every id any serialized expression references appears in it. The export
manifest and the normal-build `viewer.json` use the mode; the browser
snapshot does not, because it photographs one instant on purpose — its
document names no driver, so its table is empty. A tree declaring no
drivers is not walked at all and serializes the version 1 document with
an empty table added, which is why consumers gate on the table rather
than the number: an empty one renders exactly as version 1, a non-empty
one is refused by a consumer that cannot evaluate driver expressions
rather than rendered at a wrong pose. The `.scad` path is unchanged —
bound drivers collapse to numerals because Python evaluates eagerly,
and `$t` stays live.

Beside it, still within `version: 2`, the document publishes an
**`instructions` table** (ADR-056 stage 3b): qualified instruction name
→ design-unit targets keyed by qualified driver id, plus a duration,
verbatim from the declarations the same tree walk found. The key is
additive rather than a version bump because an instruction targets a
driver, so a document carrying instructions necessarily carries a
non-empty `drivers` table, which a consumer without driver evaluation
already refuses loudly — no consumer can misread it. Targets stay in
design units: the conversion to native state belongs to the driver
declaration, and the client performs it exactly once, exactly as
`Driver.native` does.

**`animation.loop` is the third additive key** (ADR-072). Every producer
builds its `animation` object through one helper (`animation_block`) that
reads `declared_time(type(root))` and adds `loop` — the declared seconds
one turn of `$t` covers — beside `fps` and `frames` when the root declares
a time base, and omits it otherwise, so an undeclared root's document is
byte-identical to before. The key needs no version: the tree shape and the
operation serialization do not change, the expressions already carry
`$t * loop`, and a consumer ignoring it plays `frames / fps` as it always
did. `solid snapshot --time` keeps its 0..1 meaning and keyframes
`fraction * loop` in Python when a base is declared; the renderers' `$t`
is untouched.

**Schema version 3 adds a third node shape** (ADR-057). Beside a `model`
reference and a list of `children`, a node may carry `flexible`: the
evaluating technology (`tech`), the shape spec verbatim as the adapter
serialized it (`spec`, inlined — a molejo document is a few kilobytes and
there is no mesh to deduplicate), and a `params` table of one raw
expression string per shape parameter. The producer reads that shape off
`node.flexible` exactly as it reads `node.rigid`, so the document's shape
follows the node's kind rather than a type test; `type` keeps publishing
the framework node *kind* (`LeafNode`), unchanged. `params` expressions are
produced by the same symbolic mode as operations and carry the same
verbatim guarantee structurally — `drive_tree` binds every declared driver
before serialization — so a snapshot-bound tree still publishes
`(46.8 - valvetrain.lift)` rather than the constant that instant computed,
and every id they reference appears in the `drivers` table. A flexible leaf
contributes no `models/` entry and no piece: its geometry *is* the spec.
The version is a property of the **content**, not of the producer:
`document_version()` reads it off the finished tree, so a document with no
flexible node stays byte-identical to the version 2 it always was and an
old consumer refuses only what it genuinely cannot render. Consumers accept
1, 2 and 3.

**Schema version 4 publishes each subexpression more than one operation or
`params` entry uses, once, as a named `bindings` table** (ADR-080). Sharing
begins during construction (ADR-101): `solid_node/expression_graph.py` owns
immutable native scalar nodes independent of any modelling backend;
`solid_node/scad_expression.py` supplies the SolidPython compatibility facade.
Arithmetic retains references, not expanded strings. Values own their graphs,
and compiler tables are publication-local, with no global strong graph arena.
`solid_node/core/expressions.py` collects native `operations` and flexible
`params` together with legacy scalar text. Iterative postorder interning and
root/edge occurrence analysis preserve deep chains and repeated operands;
discarded temporaries do not count as uses. The compiler rewrites
every occurrence of a subexpression that repeats — except a bare number or a
bare driver id, shorter written out than referenced — into a reference to a
named entry. `bindings` is a top-level array beside `drivers` and
`instructions`, each entry `{name, expression}`, ordered so an entry names
only `$t`, a declared driver id, or an **earlier** entry: a consumer
evaluates it in one forward pass, before any operation or `params`
expression, into the same scope it already builds for `$t` and drivers.
Names are `_b0`, `_b1`, … in table order, under a prefix lengthened by a
leading underscore whenever a declared driver id would otherwise collide
with one — deterministically, so a legal model is never refused for a
driver's name. A reference is the binding's name written where an
expression would be, resolved exactly as `$t` and a driver id are: **a name
resolves as a binding before it is judged an undeclared driver**, and
dependence flows through it, so an operation whose whole expression is a
binding name over `$t` is still time-dependent and one over a driver still
depends on that driver. An expression the parser cannot read — outside the
grammar two producers emit, reachable only through a hand-written
`scad_inline` string — is published verbatim and unshared, with a warning,
never failing the build; the producer refuses to publish only when the
table it would write is wrong (an entry naming a later entry, a name
colliding with a driver id, a rewrite that does not reproduce what was
built), which is a framework defect, never a project's. The version, like
the drivers table before it, is read off the finished document rather than
declared while building it: non-empty `bindings` → **4**; empty → the
version the tree's shape already needed (2, or 3 with a flexible leaf),
with the key omitted entirely, so a document with nothing to share is
byte-identical to the one published before this existed. Unlike the
additive keys above, this bump is not additive — a consumer ignoring
`bindings` would resolve a reference to nothing and render a wrong pose —
so it is a genuine refusal for a consumer that cannot read version 4, by
design, in the phase that already refuses an unknown version. **SCAD output
uses self-contained local scalar closures**, never the document's table.
`str`, `.value` and standalone operation serialization emit compact `let`
bindings when needed; bare and unshared expressions keep their spelling.
Local names avoid free inputs. The iterative closure importer recovers
supported legacy wrappers and standalone round-trips, lowering them to the
existing viewer language, not forwarding `let` to JSON. Numeric operation
placement refuses unresolved inputs; normal poses still rerun project laws
with numbers, and legacy Solid2 numeric evaluation remains available.
Flexible time detection follows graph inputs and diagnostics are bounded
before rendering. `solid snapshot --renderer web` keyframes and bakes constants
before serializing, so its staged document shares nothing, carries no
table, and stays at version 2 or 3. The independent viewer's current content
accepts versions 1, 2, 3 and 4; expression graphs require no viewer change.
OpenSCAD remains a supported backend, and the SCAD-centred assembly lifecycle
is not replaced by this cycle.

Every producer — export, build snapshot, browser snapshot — also publishes a
**printed-piece inventory** (ADR-043): a top-level `pieces` list beside `root`,
one entry per distinct built artifact content, carrying `id`, `name`,
contributing `sources` and `models`, `count`, bounding `size`, `volume`, and
`watertight`, with every rigid node carrying the `piece` id that resolves into
it. Expensive content-derived facts live in a private versioned sidecar keyed
by the artifact's strong observation and current currency record (ADR-085).
The internal identity is the full content digest; a collision in its public
short prefix is refused rather than merged. Current tree metadata is always
serialized afresh. Facts and any export or snapshot staging bytes are read or
copied from one pinned artifact snapshot with a fresh post-read identity check,
so metadata and bytes cannot describe different file generations. Build and
browser-snapshot producers hold the project lock for that operation; direct
export relies on the pinned validation and retries without acquiring it. No
pose or `$t` leaks into the facts. The section is additive; a consumer reading
only the tree is unaffected.

The Sphinx extension (`.. solid-node:: <export-dir>`) embeds exports
as iframes, copies them at `html-collect-pages`, and completes missing
widget files from the installed package — docs build without the CAD
stack.

### Expression math (MATH · in spec `kinematics`)

There is exactly one expression semantics: **OpenSCAD's degree
conventions**, with `^` as power (ADR-022, revised). `solid_node/math.py`
is the source of truth, and every function in it wears **three faces**:
numeric on plain numbers (keyframes, tests), a deferred OpenSCAD
expression when any argument is symbolic (the build and viewer path),
and a dimension-checked `Formula` when any argument is a declared
parameter (ADR-062). Three runtimes must agree — `math.py`, OpenSCAD,
and the one TypeScript evaluator in the viewer package — and since
ADR-056 stage 3b the same semantics govern **driver expressions** too: a
qualified id resolves through a nested driver map, needing no grammar
extension.

A relation lowers into that same arithmetic: `Affine(ratio, offset)`
computes `ratio * driver + offset` and `(driven - offset) / ratio` with
ordinary operators, so a `DriverToken` or `$t` rides through either face
as a deferred graph value and a plain number stays a number
(ADR-089). The backward face uses more of solid2's operator surface than
the forward one — a number on the left, `/`, unary negation — and that
dependency is pinned by a test evaluating the PUBLISHED string through
the same parity helper as the rest of this section. A chain solved
backwards through several stages nests one wrapping per stage, and
ADR-080's interner publishes each distinct subexpression once.

The module is split in two, and the split is load-bearing.
**Primitives** are what it emits as an OpenSCAD call: the degree
trigonometry, `sqrt`, and the direct builtins `abs`, `floor`, `ceil`,
`sign`, `min` and `max`. Each carries a dimension rule in
`function_formula`. **Compositions** — `clamp`, `clamp01`, `ramp`,
`lerp`, `wrap`, `piecewise`, `bump`, and the vector helpers `polar`,
`turn`, `rotate_x`, `rotate_y`, `rotate_z` — are built from those and
carry no rule, so each has exactly one definition and its declared face
is the same function as the other two; what they do to dimensions is a
consequence of the primitives' rules and the algebra's. The consequence
a caller meets is that a bound, period or centre stated as a bare number
against a dimensioned quantity is refused, exactly as `length + 1` is.

A name enters the vocabulary only if all three runtimes compute it
identically, which is why there is no `round` (OpenSCAD rounds halves
away from zero, JavaScript toward +infinity, Python to even) and no
`mod` (OpenSCAD spells it as the `%` operator, whose sign rule differs
from Python's). `SYMBOLIC_BUILTINS` in `math.py` is the single inventory
of every name that may be emitted; `_symbolic_call` refuses any other.

That agreement is **enforced**, not documented: `parity-fixture.test.ts`
runs the shipped evaluator against `parity-fixture.json`, whose expected
values are producer values — one numeric render of a tree paired by
structure with one symbolic serialization of it, so nothing recomputes
an expression a second way. `tools/generate_parity_fixture.py`
regenerates it from **two** corpora — the ADR-056 expression spike's
two-axis machine (linear driver terms, port scales, degree-trig chains,
`^` terms, mixed `$t`-and-driver formulas) and
`tests/expression_project/vocabulary.py`, which puts every remaining
emitted builtin on the wire under a driver bound negative as well as
positive — for 421 cases in all. The generator reads `SYMBOLIC_BUILTINS`
and **refuses to write while any emitted name is uncovered**, so the
enforcement cannot silently narrow; `tests/test_expression_corpus.py`
says the same in the framework's own suite. The fixture also pins
`Driver.native`'s design-to-native conversion, integer
round-half-to-even included, for the same reason. The fixture itself is
committed in the viewer repository (ADR-068), so widening the vocabulary
is one change here and one there.

### Mechanisms (MATH · in spec `mechanisms`)

`solid_node/mechanisms/` carries the textbook mechanism laws that a
project's own `kinematics.py` kept rewriting (ADR-076): the external
spur-gear mesh and its inverse, the lead screw, the planar slider-crank,
linear delta kinematics, and the circle geometry a linkage asks for. One
module per family — `gears`, `screws`, `cranks`, `deltas`, `linkages` —
with the family's frame, zero and sign stated once at its top, and an
eager flat re-export whose names are unique across families.

Three properties make it a subsystem rather than a utility drawer. Every
law is a **composition over `solid_node.math`** and arithmetic, so it has
that module's numeric and symbolic faces and emits **no OpenSCAD builtin
the parity corpus above does not already pin** — the `mechanisms` spec
requires that, so a law wanting a new builtin must go through `math.py`
first. A gear library's convention enters as **reference angles**
(`driver_gap`, `driven_tooth`), not as a fork of the law or a read of a
gear object. And there is **no declared face**: the laws carry degree
literals the ADR-062 algebra cannot type as angles, so a declared token
reaching one raises `DimensionError` at class definition, with `.value`
as the documented way through.

These laws are the arithmetic a project's `law=` callable COMPOSES when
it states a relation (ADR-089) — `meshed_angle` and `driving_angle` are
one affine pair, which is why a project that adopts `drives` writes only
the forward reading and lets the framework invert it. That does not make
them vocabulary: the framework still looks nothing up here, and a law is
a value the project passes in.

## Load-bearing invariants

The short list that changes must not silently break:

- An artifact is fresh **iff** its mtime equals the node's max source
  mtime, compared as integer nanoseconds and never as a float, **and** the
  recorded metadata fingerprint of every tracked source equals its current
  path identity, size, mtime and change time (ADR-050/081); an exact node
  requires both STL and BREP current, and every
  cache keys on that signal (ADR-006/028/029/044). Equality, not
  tolerance: a window wide enough to absorb a filesystem's timestamp
  quantum is a window in which a real edit is invisible. When and only
  when either equality fails, a content-verified fallback compares a digest
  of the node's tracked sources against the digest recorded beside the
  artifact when it was written; identical sources restamp rather than
  re-derive, so a clone, a branch switch or a stash pop costs a settled
  rebuild instead of a full one (ADR-060). The fresh path reads source
  metadata and the small sidecar but no source contents; the fallback is
  strictly stricter than the rule it stands behind
  — byte equality rather than timestamp equality — so it cannot report a
  changed source current. The digest is scoped to the node (ADR-071): a
  file that defines several node classes contributes to each node's digest
  the file minus the other node classes' bodies, except any the retained
  text names as an identifier or a string, and an internal node's digest
  covers the union of its children's scopes. Two nodes sharing a file
  therefore rebuild independently, an edit to code they share rebuilds
  both, and a single-class file digests byte for byte as before. One node
  per file is not a premise of the cache; what remains true of a
  multi-node file is a property of node references (a bare path to it is
  ambiguous), not of currency.
- A loaded tree belongs to one sealed source generation. Project Python is
  executed from coherently observed bytes, all consumed Python and foreign
  contributors retain their canonical targets and strong identities, and
  every producing phase and asynchronous wait rechecks them before stale work
  can publish (ADR-084). The F04 project lock spans assembly, artifact work and
  publication, not callbacks, project tests or development recovery waits.
- A node's source set is its own file plus the project-local modules it
  imports, transitively — never the `__init__.py` of a package the walk
  merely traverses, which would make every node depend on every file
  (ADR-033). The set over-approximates on purpose: a spurious rebuild is
  cheap, a stale model is not — which is why a leaf whose source is a
  foreign file adds the closure of the python module wrapping it when that
  module carries geometry-affecting code (ADR-055). Resolving the package a
  file was imported as, which the closure needs for relative imports, reads a
  one-shot index of the loaded module table keyed on the exact set of module
  names, so building a closure does not scale with what the interpreter has
  imported and cannot answer from a superseded module set (ADR-058).
- `name=` never influences geometry or `uniq_id`; any parameter change
  changes the artifact key (ADR-026), and on a declarative class the
  framework computes the key from every declared value, so none can be
  left out (ADR-063). A declaration is realized per parent instance;
  a class body never holds a node instance (ADR-061). Piece identity is the converse: it
  derives from built content only, never from a class, its parameters, or
  its artifact path. Piece facts and staged bytes come from one strongly
  observed pinned artifact snapshot; an artifact that changes or cannot be
  read gets no piece id rather than borrowing one (ADR-043/085).
- Re-rendering an instant is absolute, never cumulative; only
  driver-tagged operations are swept (ADR-023).
- All pose consumers compose own-ops-first, ancestors after, later
  operations outermost — Python and both browsers alike (ADR-027/028).
- A non-empty, zero-volume **faceted** flush contact fouls at
  `volume_epsilon=0`; exact boundary contact contains no solid and is empty.
  Kinematic fit still needs the Blocked **and** Free pair (ADR-025/029/044).
- The `solid-node-export` format/version identifies a shared tree-document
  schema; breaking its tree shape or operation serialization means bumping the
  version and updating every producer and consumer together. A producer emits
  the **lowest version its content needs**, so a consumer refuses exactly the
  documents it genuinely cannot render and no others (ADR-057). Portability stays
  producer-specific: `manifest.json` is copied and portable, `viewer.json` is
  build-root-relative and private (ADR-020/031/034).
- Every expression evaluator — of `$t` or of a driver id — uses degree
  trig and treats `^` as power, and the client's agreement with the
  producer's numerics is held by the parity fixture (ADR-022).
- A `range` is presentation metadata. Nothing in the framework, the
  simulation, or the viewer clamps a driver to it (ADR-056).
- Users never override `assemble()`; rigid geometry is time-invariant
  (ADR-002/003). Structure varies with parameters, never with time: a
  render that omits a different set of declared children than the
  instance's first render raises (ADR-064). A part whose shape follows machine state is therefore
  not rigid — the one non-rigid leaf kind — and it is fused by nothing,
  persisted as nothing, and printed as nothing. Its stock evaluated geometry
  may be memoized only by the complete binding and shape identity; its verdicts
  are never reused (ADR-057).
- A topmost rigid node is the boundary of one printed solid, not a guarantee
  that its geometry is connected. Whole-solid integrity is an explicit
  project assertion; connectivity uses the solid-local frame and collision
  uses the world frame (ADR-039, amended 2026-08-10).

## Known gaps and tensions

- **OpenSCAD is outside the parity fixture** (ADR-022): the corpus pins
  the TypeScript evaluator to Python's numerics, and the `.scad`
  boundary is exercised by rendered spike snapshots rather than by a
  test. Closing it needs OpenSCAD in the loop, which nothing yet
  requires.
- **Create React App is deprecated** (ADR-013, now in solid-node-viewer):
  the development shell's toolchain carries migration debt (Vite or similar),
  owed by the viewer repository.
- **The viewer is installed from Git in CI and on Read the Docs** until
  solid-node-viewer is published on PyPI.
- **Sequential STL rendering**: `build_stls` renders one STL at a
  time; cold builds could parallelize `openscad` jobs
  (`docs/performance-improvement.md` §4–5, unscheduled).

## Map

| Subsystem | Code | Spec capability | ADRs |
|---|---|---|---|
| Node model | `solid_node/node/`, `solid_node/exact.py` | `node-model`, `exact-geometry`, `flexible-parts`, `step-assembly` | 001–004, 006, 026, 044–045, 047, 053–055, 057, 077, 078, 079, 082 |
| Build parameters | `solid_node/parameters.py`, `node/declarative.py` | `declarative-nodes` | 061–065, 082 |
| Kinematics | `node/operations.py`, `node/assembly.py`, `motion/ports.py`, `math.py` | `kinematics` | 008, 022, 023, 028, 087, 088 |
| Motion | `solid_node/motion/` | `ports`, `joints`, `couplings` | 056, 072, 087, 088, 089, 096, 100 |
| Mechanisms | `solid_node/mechanisms/` | `mechanisms` | 022, 076 |
| Build pipeline | `solid_node/core/` | `build-pipeline` | 005–007, 018, 026, 038, 067, 080, 081, 084, 086 |
| CLI | `cli.py`, `solid_node/manager/` | `cli` | 021, 024, 068, 079, 103 |
| Test framework | `solid_node/test.py`, `manager/test.py` | `test-framework` | 009–011, 025, 029, 040, 048, 052, 070, 073 |
| Viewer lookup & snapshot staging | `solid_node/viewers/bundle.py`, `viewers/browser.py`, `viewers/openscad.py` | `viewer-distribution`, `web-snapshot` | 015, 018, 041, 068, 103 (the viewer itself: solid-node-viewer) |
| Export | `core/export.py`, `core/serializer.py`, `core/expressions.py` | `export` | 020, 034, 043, 051, 057, 068, 080, 085 |
| Sphinx embedding | `solid_node/sphinx.py` | `sphinx-embedding` | 020 |
