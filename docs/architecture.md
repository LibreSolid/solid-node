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
         render() → simulate() → validate() → as_scad()
                           │
           ┌───────────────┼──────────────────┐
           ▼               ▼                  ▼
      .scad files     world meshes      serialized ops
      → openscad      (trimesh /        ($t expressions)
      → .stl cache    manifold3d)             │
      (BUILD)         (TEST-FRAMEWORK)        ▼
           │                            web viewer / widget
           ▼                            evaluate $t per frame
      dev loop, OpenSCAD snapshot,      (VIEWER-WEB, EXPORT,
      export models                      MATH)
```

Three architectural commitments shape almost every subsystem:

1. **Geometry follows the strongest backend path available**
   (ADR-004/044/045/046/047). Every backend still produces SCAD and an STL.
   Solid2 and raw `.scad` leaves, and faceted fusions containing them, render
   through OpenSCAD. The OCCT backends — CadQuery and build123d — preserve
   BREP geometry, and all-exact fusions compose and tessellate in OCCT
   without OpenSCAD, whichever of the two produced each child. JSCAD produces
   its STL through its own `jscad` tool, and a flexible part through molejo's
   evaluators — mesh, STL and B-rep from one analytic spec.
   OpenSCAD is therefore conditional on
   the paths that invoke it, not a universal framework prerequisite. The same
   rule governs the `manifold3d` mesh engine (ADR-052): it decides faceted
   geometry, so it is required by comparisons involving a part without exact
   geometry and by `assertAssemblySupported`, whose statics phase is faceted
   for every body — and by nothing else. Both are resolved once per process at
   the point of use and report by name when absent.
2. **The build artifact is the currency, mtime is its clock**
   (ADR-006/026/033/050). STLs are cached per parameter-hashed identity and
   validated by mtime *equality* against the max source mtime, in integer
   nanoseconds — never as a float, which cannot survive the `os.utime`
   round trip off a filesystem coarser than a nanosecond (ADR-050). Caches
   at every layer — meshes, Manifolds, HTTP responses — key on the same
   `(artifact, mtime)` signal, so artifact freshness is the one
   invalidation concept the whole system shares. The source set behind
   that clock is a node's own file plus the project-local modules it
   imports, transitively (ADR-033), so a contributing module edit
   invalidates the nodes that read it — and only those.
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
non-overridable `assemble()` pipeline — render → validate → `as_scad`
→ SCAD generation → optimized STL import → apply operations — memoized
per instance (ADR-002).

A node is authored in one of two forms, freely mixed in one tree. The
**constructor form** builds children in `__init__` and forwards
parameters to `super().__init__()`. The **declarative form** states
them in the class body: typed parameters (`Length`, `Angle`, `Count`,
`Ratio`, `Flag`, `Scalar`), derived parameters as bare formulas over
them, and children as calls — because every node class carries
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
`import`, with `solid_node.math`'s functions carrying their own rules
and a project free to subclass `Quantity` with new exponents
(ADR-062). By the time any `render()` runs every parameter is a plain
value; backends, `uniq_id` and the serializer never see a token. Reading
a parameter off a sibling declaration is refused: shared values are
declared on the ancestor and passed down.

The public surface is split by concern above the node package, so an
import line says what each name is for: build parameters come from
`solid_node/parameters.py`, node classes from `solid_node/node/`,
runtime inputs from `solid_node/simulation/`, the test case from
`solid_node/test.py` (ADR-062, amended). The parameter module holds the
declaration descriptor every other declaration follows, the exponent
algebra, the kinds and the parameter enumerator, and imports nothing at
all — not the framework, not a third party — because it is on the
import path of every node module in every project.
`solid_node/node/declarative.py` keeps the structural half, the child
declarations and `NodeMeta`, and imports the parameter module; the node
package exports no parameter kind, and `solid_node/math.py` reaches the
formula algebra sideways rather than down into the node package.

On a declarative internal node `render()` places at rest and selects
and may return nothing, in which case the framework's render wrapper —
the same `__init_subclass__` hook that installs the lifecycle —
substitutes the realized declared children in declaration order minus
those `omit()` marked; a returned list keeps its contract untouched,
and a class with nothing to position needs no `render()` at all
(ADR-064). An omitted child is not linked, built, exported, fused or
serialized. Structure varies with parameters, never with time: `omit()`
raises in `simulate()`, and on the legacy path the wrapper records the
omitted set of an instance's first render and raises on a later render
whose set differs. The reference's rename of `render()` is dropped
(ADR-066): *render* also means *to make*.

Two concrete internal nodes encode the **rigid/non-rigid** axis
(ADR-003): `FusionNode` (rigid union, no `time`) and `AssemblyNode`
(non-rigid, animatable). Rigidity is static and determined by node type;
a fusion rejects any non-rigid child during validation, enforcing "fuse
solids, then assemble them" (ADR-039). Only rigid nodes produce STLs, which
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
`jscad` CLI), and `StlNode` (`stl_source`, a committed mesh materialized with
no backend at all). Every node exposes derived read-only exactness (ADR-044): the
OCCT adapters are exact, the other leaf adapters are faceted, and an
internal node is exact only when every child is. Exactness does not require
one backend — every exact adapter converts its render result to one shared
OCCT shape at the adapter boundary, so the exact layer holds a single type and
a fusion may mix CadQuery and build123d children (ADR-047). Because that
conversion makes everything after it backend-neutral, the contract itself —
`exact`, `shape()`, `as_scad()` — lives once on `ExactLeafNode`, the internal
base every exact adapter extends; each supplies only its `namespace` and any
validation its own API needs. Adapters remain distinct types regardless of the
bases they share. Because build123d
groups solids, sketches and curves under one namespace, `Build123dNode`
additionally rejects a render result that is not a solid, and accepts a
`BuildPart` builder by taking its finished `.part`.

One leaf kind has no modelling backend at all. `StlNode` is a part that
arrives as a committed STL mesh: it declares `stl_source` beside its wrapper
module, resolves and tracks it like `JScadNode` does its `.js`, and
materializes its own artifact from it inside `as_scad()` — selected body,
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
joins the node's tracked source set, the only leaf for which that is true
(ADR-055).
`StlNode` is faceted: `exact` is false, mesh-only is settled doctrine for
imported meshes, and a fusion containing one is faceted and unions through the
OpenSCAD/CGAL path (ADR-045).

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
Each adapter still emits SCAD, but artifact production follows its backend:
Solid2 and raw OpenSCAD leaves use OpenSCAD, CadQuery and build123d — sheet
parts included — use OCCT, JSCAD uses `jscad`, a flexible leaf uses molejo's
Python evaluator, and an imported mesh uses no
tool whatsoever (ADR-046). Emitting SCAD
does not itself require the OpenSCAD binary. A sheet leaf writes one artifact
the others do not: a nominal DXF of its profile, in millimeters with arcs
preserved, beside its `.stl` and `.brep` and under the same freshness rules,
which its skip guard also requires. A flexible leaf writes another: a
per-binding snapshot STL, so the assembled SCAD document stays complete for
the OpenSCAD GUI — a snapshot camera, never animation, the treatment
drivers already receive. The camera declines where there is no instant to
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
(0..1) when unbound, read through the `time` property. `set_keyframe(t)`/`clear_keyframe()` are the preserved
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
arithmetic and `solid_node.math`'s degree trig build the wire
expression with no new operators. It also carries `DriverDeclaration`,
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
`SignalPort`): stateless declarations carrying domain, unit, direction,
and an optional design-units-per-native-unit scale, discoverable off
the class via `declared_ports()`, with per-instance value slots
materialized by descriptor. `connect(source, sink)` on internal nodes
is causal, immediate, per-render rebinding — value flows one way,
scaled by the sink; no flow variable exists yet (the bond-graph
extension ADR-056 reserves).

World pose is one composed 4×4 matrix — own operations then ancestors,
premultiplied (ADR-028) — recomputed on *every* access because
operation values can be animated expressions and the operations list
is mutated by design. The base mesh under it is cached per
`(stl_file, mtime)`.

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
applied to simulated time); construction enumerates the whole linked
tree and binds every declared default through `set_state` by qualified
id before the first render, so a driverless root with driver-declaring
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

Nodes are addressed by **reference** — a qualifier
(`package.module:Class`), a filesystem path, or a path plus class —
dynamically imported and resolved against a project root discovered
from the nearest ancestor `pyproject.toml` carrying `[tool.solid-node]`
(ADR-005, superseded by project-manifest-node-references). A bare path
to a file defining several node classes must name the one meant in the
reference; implicit discovery remains limited to classes defined in the
loaded file. Artifacts remain keyed to the selected class's real
implementation source. The source set tracks that implementation/import
closure, so an edit to it invalidates and reloads the active node.
Artifacts land under `$SOLID_BUILD_DIR` (default `_build`, resolved
against the discovered project root rather than the working directory),
mirroring the source layout, basename `<script>-<uniq_id>`.

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

STL generation is normally asynchronous: `StlRenderStart` carries a spawned
`openscad` process, PID lock files guard concurrency, and
`build_stls()` loops until nothing is stale. Staleness is **mtime
equality** — generated files are back-dated with `os.utime` to the max
source mtime (ADR-006), taken over `node.files`: the node's own source
plus its project-local import closure, unioned upward from children
(ADR-033) — and, for an imported mesh, the closure of the wrapper module
that declares it as well, since the mesh file has no imports of its own to
walk and the wrapper is where its geometry-affecting code lives (ADR-055).
Both sides of that equality are integer nanoseconds
(`st_mtime_ns`, `os.utime(ns=…)`), so the back-date is a fixed point at
whatever resolution the filesystem stores — a float stamp is not, and on a
millisecond-resolution filesystem it left every artifact permanently stale
and this loop non-terminating (ADR-050).

OpenSCAD availability is resolved once per process, at the first operation
that actually requires it (ADR-046). Mesh-backend STL rendering, faceted
fusion, Solid2 symbolic-value evaluation, the OpenSCAD GUI viewer, and the
OpenSCAD snapshot renderer are the complete requiring set. A missing binary
raises one actionable error naming the operation and remedy before subprocess
launch; an all-exact build never performs the check.

A rigid, optimizing **leaf** whose artifacts are current assembles by
importing its STL — `render()` and `as_scad()` never run (ADR-033), so
the check happens before the expensive work rather than after it.
Internal nodes always render: their file set is the union of their
children's and is only known by walking them. The adapters that write
their artifact inside `as_scad()` — CadQuery, build123d, sheet, JSCAD — carry
the same guard, for nodes that opt out of optimization. A flexible leaf
carries it per binding: mtime equality decides *source* currency within one
binding exactly as elsewhere, and a different binding is a different file
rather than a question mtime is asked and cannot answer (ADR-057).

The dev loop (ADR-007) is a **single-shot builder** under watchdog:
build, watch `node.files` per-file, exit on change, get respawned by
`solid develop` (which also restarts the viewer process). `solid build`
uses the same builder passes without a viewer or watch loop. Every one of
those subprocesses starts from a **fresh interpreter**, not a fork of the
command process (ADR-067): a command resolves the model in its own process to
report a missing one, that import runs geometry and leaves OCCT's OpenMP
worker team live, and a forked child would inherit the team's bookkeeping
without its threads and stop forever on the first parallel tessellation. A
fresh child is handed its target instead of inheriting it, so every subprocess
target is a module-level function taking plain values. Candidate
builds publish `viewer.json` with the versioned `solid-node-export` tree
schema, linked node names, per-node `mtime`, and build-root-relative model
paths, so private NodeAPI consumers can serve a completed build without
loading project Python (ADR-031/034). Sharing that schema marker with export
does not make a build publication portable: it copies no meshes and retains
its private `viewer.json` document boundary.
artifacts write directly into one ordinary build directory. Each artifact is
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
(ADR-018). A broken initial build kills develop; a broken reload falls back to
a broad recursive watch and keeps the loop alive.

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
`snapshot`, `new` (offline scaffold), `export`, `viewer`. Every command
that loads a node takes `--set name=value`, registered once beside the
shared reference positional: the loader parses each value by the root's
declared kind and constructs the root with the overrides, the develop
loop carries them into every builder it starts, and an unknown or derived
name fails listing what is settable (ADR-062). Only the invoked
command's module is imported, and the node and simulation packages resolve
their exports on first access, so a command pays for the backends it uses and
not for the rest (ADR-059) — `solid viewer` answers from the installed bundle
alone. Top-level `-h` is the exception: it renders every command's docstring,
so it loads them all. Snapshot has an explicit renderer choice
(ADR-021/041/046): OpenSCAD remains the external-tool default with xvfb
fallback, while the
optional `web` renderer captures the packaged viewer in sandboxed headless
Chromium to produce a true-alpha PNG. Unsupported renderer-specific options
are rejected rather than ignored or substituted. If the default OpenSCAD
renderer is unavailable, the command names `--renderer web` but does not
select it silently. `./.env` is read with
`setdefault` semantics (real environment wins), carrying
`SOLID_NODE_PORT` / `SOLID_NODE_FRONTEND_PORT` / `SOLID_BUILD_DIR`.

### Test framework (TEST-FRAMEWORK · spec `test-framework`)

Test-driven CAD is the framework's reason to exist: contracts about
geometry, checked on the real meshes. Tests live in companion files or
on the node via `TestCaseMixin` (ADR-010), run by `solid test` — which
builds first, then runs `test_` methods per declared animation instant
(`@testing_instant` / `@testing_steps`, ADR-011) with operation
checkpoints restored between instants.

Collision assertions (ADR-009/044) select the strongest shared representation:
intersection-volume and connectivity questions use placed OCCT shapes when
both operands are exact and retain trimesh/Manifold for mixed or faceted
pairs. That selection reaches the placement step too (ADR-052): a solid is
placed into the spatial index from its cached bounds alone, and its Manifold
is built only when a comparison really reads it, so an all-exact assembly
builds none and needs no mesh engine. Distance and containment assertions
remain mesh-sampled. This includes the
**paired kinematic fit contract** (ADR-025): `assertBlockedBeyond` +
`assertFreeWithin` perturb a part along its working degree of freedom
(rotational `axis=` or translational `along=`, injected in the local
pre-placement frame, always restored) — fit is certified only by the
pair. `volume_epsilon` separates real interference from boolean noise,
with a deliberately strict default: a flush contact that is non-empty
at exactly 0.0 mm³ **is** a foul until the test opts into an epsilon.

The shared intersection path (ADR-029/044) caches one Manifold per
`(stl_file, mtime)` (watertightness checked once, at fill), culls
provably disjoint pairs with a conservative world-AABB broad-phase,
and reads `is_empty()`/`volume()` straight off lazy-transformed Manifolds —
verdict-identical to the naive faceted path. Exact pairs share the same AABB
broad phase, then use OCCT common and interpret “contains no solid” as empty;
kernel failure raises and never falls back. `volume_epsilon` is ignored with a
warning when every comparison in a call was exact.

The root-level integrity boundary is the first rigid node on every branch
(ADR-039/040). Connectivity is deliberately solid-local.
`assertNoDisconnectedSolids(node)` explicitly checks that every printed solid
in a selected subtree is one connected body; it reads each topmost rigid
node's local STL. `assertNoSolidInterference(node)` is its world-space
assembly complement: zero or one selected solid passes without geometry work;
otherwise a sweep-and-prune index over conservative world AABBs emits the
potentially interacting pairs, and each is settled by an exact same-kernel
intersection — the sole verification path, with no whole-assembly measurement.
Exact zero-volume boundary contact passes, every positive candidate volume
fails, and no public volume epsilon or private numerical tolerance is exposed.
Correctness rests on the broad phase being complete, which is proved by
framework tests rather than re-checked at runtime (ADR-040). The old all-leaf
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
anything by itself. The broad phase is the same sweep-and-prune, run over the
displaced and placed boxes at once so an emitted cross-half pair is exactly a
directed overlap; exact pairs still route to the kernel. Zero or one selected
solid passes without geometry work; a zero `gravity`, a non-positive
`max_drop`, a negative `stability_margin`, and an unresolvable
`ground`/`supports` entry are loud errors.

When reachability holds, a second phase proves frictionless static equilibrium
(ADR-049): that push-only normal forces over the detected interfaces balance
every non-anchored solid's weight and its torque about its own centre of mass,
decided by one deterministic `scipy.optimize.linprog` HiGHS solve of the
L1-relaxed feasibility program. Interfaces are extracted by meshing each
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

### Viewers (VIEWER-WEB · spec `web-viewer`)

`solid develop` serves a FastAPI + Uvicorn app (ADR-015, post-018 the
only HTTP service): static React build by default, npm-proxy under
`--web-dev`. It serves the current atomically published build directory
under `/build/` and the installed shared viewer bundle under `/_viewer`.
The server does not import project source; an absent build or bundle leaves
the reload socket and build-error endpoint available, with a bundle remedy
for the browser shell to display.

The browser app is a small React shell (ADR-013, amended by ADR-036). It
loads the shared viewer bundle, mounts it against `/build/viewer.json` with
inline autoplay controls, names the tab from the snapshot, and uses the
mount handle's `manifestChanged()` after `/ws/reload` reports a successful
build. The shared viewer reconciles the document in place and refetches only
geometry whose `(model path, mtime)` identity changed (ADR-037); the canvas,
viewpoint, animation clock, and unchanged meshes survive. `reload()` remains
available for a host that explicitly needs a complete replacement.
Tree traversal, world-matrix composition, expression evaluation, animation,
stale-load disposal, and targeted-update failure containment live once in the
reusable viewer package (ADR-035/037), not in the development app.

A sibling OpenSCAD GUI viewer (`--openscad`) and the headless
snapshot renderers cover non-interactive cases. The browser snapshot renderer
renders any stale artifact of the photographed node, serializes that node's
tree into a temporary sibling and hardlinks its artifacts there, all while
holding the project build lock, then releases the lock and serves that pinned
staging tree on an ephemeral loopback port. It never republishes or sweeps the
build itself: the published document belongs to the producer serving it, so a
snapshot of one part leaves the rest of the project intact. Playwright
captures only the transparent canvas under Chromium/SwiftShader; staging is
removed after either success or failure (ADR-041).

### Export and embedding (EXPORT · specs `export`, `sphinx-embedding`)

`solid export` (ADR-020/034/035/042) emits a self-contained static artifact:
`manifest.json` (`format: solid-node-export`, at the versioned tree-document
schema shared with `viewer.json` — `version: 2`, or `3` when the tree holds
a flexible node; not a portability claim),
deduplicated `models/*.stl`, and a
React-free three.js **widget** whose side-effect-free imperative core mounts a
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
set `[1, 2, 3]` — a check the loader previously did not perform at all —
and a `flexible` node whose `tech` this build cannot evaluate, each named
in the error.
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

Every producer — export, build snapshot, browser snapshot — also publishes a
**printed-piece inventory** (ADR-043): a top-level `pieces` list beside `root`,
one entry per distinct built artifact content, carrying `id`, `name`,
contributing `sources` and `models`, `count`, bounding `size`, `volume`, and
`watertight`, with every rigid node carrying the `piece` id that resolves into
it. Facts are read from the artifact's own base mesh, so no pose or `$t` leaks
into them. The section is additive; a consumer reading only the
tree is unaffected.

The Sphinx extension (`.. solid-node:: <export-dir>`) embeds exports
as iframes, copies them at `html-collect-pages`, and completes missing
widget files from the installed package — docs build without the CAD
stack.

### Expression math (MATH · in spec `kinematics`)

There is exactly one expression semantics: **OpenSCAD's degree
conventions**, with `^` as power (ADR-022, revised). `solid_node/math.py`
is the dual-mode source of truth (numeric under keyframes, deferred
OpenSCAD expressions when symbolic). Three runtimes must agree —
`math.py`, OpenSCAD, and the one TypeScript evaluator in the shared
viewer package — and since ADR-056 stage 3b the same semantics govern
**driver expressions** too: a qualified id resolves through a nested
driver map, needing no grammar extension.

That agreement is **enforced**, not documented: `parity-fixture.test.ts`
runs the shipped evaluator against `parity-fixture.json`, whose expected
values are producer values — one numeric render of a tree paired by
structure with one symbolic serialization of it, so nothing recomputes
an expression a second way. `tools/generate_parity_fixture.py`
regenerates it from the ADR-056 expression spike's corpus (182 cases:
linear driver terms, port scales, degree-trig chains, `^` terms, mixed
`$t`-and-driver formulas), and it pins `Driver.native`'s design-to-native
conversion, integer round-half-to-even included, for the same reason.

## Load-bearing invariants

The short list that changes must not silently break:

- An artifact is fresh **iff** its mtime equals the node's max source
  mtime, compared as integer nanoseconds and never as a float
  (ADR-050); an exact node requires both STL and BREP current, and every
  cache keys on that signal (ADR-006/028/029/044). Equality, not
  tolerance: a window wide enough to absorb a filesystem's timestamp
  quantum is a window in which a real edit is invisible. When and only
  when that equality fails, a content-verified fallback compares a digest
  of the node's tracked sources against the digest recorded beside the
  artifact when it was written; identical sources restamp rather than
  re-derive, so a clone, a branch switch or a stash pop costs a settled
  rebuild instead of a full one (ADR-060). The fallback reads nothing on
  the fresh path and is strictly stricter than the rule it stands behind
  — byte equality rather than timestamp equality — so it cannot report a
  changed source current.
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
  its artifact path — an artifact that cannot be read gets no piece id
  rather than borrowing one (ADR-043).
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
  cached as nothing, and printed as nothing (ADR-057).
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
- **Create React App is deprecated** (ADR-013): the dev viewer's
  toolchain carries migration debt (Vite or similar).
- **Sequential STL rendering**: `build_stls` renders one STL at a
  time; cold builds could parallelize `openscad` jobs
  (`docs/performance-improvement.md` §4–5, unscheduled).

## Map

| Subsystem | Code | Spec capability | ADRs |
|---|---|---|---|
| Node model | `solid_node/node/`, `solid_node/exact.py` | `node-model`, `exact-geometry`, `flexible-parts` | 001–004, 006, 026, 044–045, 047, 053–055, 057 |
| Build parameters | `solid_node/parameters.py`, `node/declarative.py` | `declarative-nodes` | 061–065 |
| Kinematics | `node/operations.py`, `node/assembly.py`, `math.py` | `kinematics` | 008, 022, 023, 028 |
| Build pipeline | `solid_node/core/` | `build-pipeline` | 005–007, 018, 026 |
| CLI | `cli.py`, `solid_node/manager/` | `cli` | 021, 024 |
| Test framework | `solid_node/test.py`, `manager/test.py` | `test-framework` | 009–011, 025, 029, 040, 048 |
| Web viewer | `solid_node/viewers/web/` | `web-viewer` | 012–015, 018, 036 |
| Export & widget | `core/export.py`, `core/serializer.py`, `viewers/widget/` | `export`, `viewer-package` | 020, 034, 035, 051, 057 |
| Sphinx embedding | `solid_node/sphinx.py` | `sphinx-embedding` | 020 |
