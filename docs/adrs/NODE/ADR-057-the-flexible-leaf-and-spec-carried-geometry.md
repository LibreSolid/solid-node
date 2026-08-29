# ADR-057: The flexible leaf, whose geometry travels as a spec

**Status:** Accepted

**Date:** 2026-08-28

**Change:** `flexible-leaf-node`

**Depends on:**
- [ADR-003: Rigid vs non-rigid node distinction](ADR-003-rigid-vs-non-rigid-node-distinction.md)
- [ADR-004: Multi-CAD backend adapter pattern](ADR-004-multi-cad-backend-adapter-pattern.md)
- [ADR-008: Time-based animation system for assemblies](ADR-008-time-based-animation-system-for-assemblies.md)
- [ADR-026: Node identity — parameter-hashed artifact keys vs tree names](ADR-026-node-identity-parameter-hashed-artifact-keys-vs-tree-names.md)
- [ADR-039: Solid integrity at the topmost rigid node](ADR-039-solid-integrity-at-the-topmost-rigid-node.md)
- [ADR-044: Derived exact-geometry capability](ADR-044-derived-exact-geometry-capability.md)
- [ADR-047: One shared OCCT currency for every exact backend](ADR-047-shared-occt-currency-for-exact-backends.md)
- [ADR-053: The authored profile is a sheet part's single source of truth](ADR-053-authored-profile-as-the-sheet-part-source-of-truth.md)
- [ADR-056: Signals, drivers, ports, and stepped simulation](ADR-056-signals-drivers-ports-and-stepped-simulation.md)
- [ADR-034: Shared node-tree document schema](../EXPORT/ADR-034-shared-node-tree-document-schema.md)
- [ADR-035: Reusable viewer core and declared API version](../EXPORT/ADR-035-reusable-viewer-core-and-declared-api.md)

## Context and Problem Statement

A machine contains parts whose *shape*, not merely whose placement, is a
function of machine state: a valve spring compressed by a cam, a timing
belt following a moving idler, a cable loom dragged by a carriage. The
framework could not model any of them, and it said so in its own words —
`LeafNode.time` raised *"Implementing a FlexibleNode is in the roadmap"*,
and `docs/status-and-roadmap.rst` carried the FlexibleNode as roadmap
item 3.

The gap had already cost real designs. The v8-engine project was designed
*around* it: its `increment-7-valvetrain.md` records that flexible springs
cannot be modelled because "modeling an undeformed decorative spring would
create false interference", and increment 8 puts belts out of scope for
the same reason. Metamaquina2's belts exist today only as a scalar `scale`
on a port — correct kinematics with no body at all.

ADR-003 and ADR-008 both deferred time-dependent leaf geometry, and both
named why: a leaf that morphs breaks the mtime-caching precondition that
rigid geometry is time-invariant, and a mesh whose topology changes with a
parameter cannot be swapped into a viewer frame by frame. Neither was a
statement that the part kind was wrong; both were statements that the
representation was missing.

[molejo](https://github.com/LibreSolid/molejo) supplies it. A swept
flexible part is represented *analytically* — a closed profile carried
along a path at a declared tessellation — as a small serializable
document, with a Python evaluator producing deterministic meshes and STL,
a JavaScript evaluator producing three.js buffers cheaply enough to
re-evaluate every animation frame, an OCCT B-rep evaluator, and parity
fixtures pinning the runtimes to each other. That representation answers
both deferrals at once: there is no per-frame mesh to cache because the
viewer representation is the *spec*, and the tessellation is declared
rather than adaptive, so vertex count and ordering are
parameter-independent by construction.

What remained was a framework question in seven parts: where such a leaf
sits in the rigidity story, how per-instant values reach it without
destroying artifact identity, what its render contract is, what it writes
to disk, how it answers an exact question, what it publishes in the shared
document, and what the viewer does with that per frame.

## Decision Drivers

- ADR-056 had just delivered named scalar state end to end — declared
  drivers, typed ports, symbolic expressions in the document, client-side
  per-frame evaluation. Flexible geometry is that mechanism with
  `geometry = f(params)` where the existing path has
  `matrix = f(params)`; a second mechanism would be a second thing to
  keep in agreement.
- Every constructor parameter enters `uniq_id` (ADR-026). A continuously
  varying value must not reach a constructor, or each frame mints a new
  artifact identity.
- The mtime rule (ADR-006/050) answers whether a *source* changed. It
  cannot answer whether a *binding* changed, and must not be asked to.
- ADR-003's caching precondition — rigid geometry is time-invariant —
  must survive intact rather than be weakened for one node kind.
- The assembled SCAD document must stay complete: the OpenSCAD GUI can
  open any project.
- A consumer that cannot render a document should refuse it loudly, and
  should refuse nothing else. ADR-034 makes a new tree shape a breaking
  change; the drivers table established that emitting the lowest version
  the content needs is what keeps that promise narrow.
- Adapters are shaped alike: `render()` returns the backend's object
  (ADR-004), and an internal base carries the mechanics (ADR-053).

## Considered Options

1. **A non-rigid leaf whose parameters arrive through ports, whose
   geometry travels as an evaluator spec, and whose meshes are computed
   on demand** (Chosen)
2. Constructor-parameter binding, with one artifact per value
3. Serialized per-frame meshes — morph targets or frame swapping
4. Driver declarations on the leaf itself, rather than ports
5. A sidecar spec file beside the export's `models/`
6. A new extension-point verb instead of `render()`, as the sheet
   adapter's `profile()`
7. Bumping every document to version 3 unconditionally
8. Persisting the exact solid per binding, as every other exact node
   persists its `.brep`

## Decision Outcome

Chosen option: **a flexible leaf is a non-rigid leaf whose shape is a
pure function of its declared ports' bound values, and whose geometry
travels as its evaluator's spec rather than as any mesh.**
`FlexibleNode` (`solid_node/node/flexible.py`) is the framework-internal
base; `MolejoNode` (`solid_node/node/adapters/molejo.py`) is the v1
adapter, exactly the `SheetLeafNode`→`Build123dSheetNode` shape ADR-053
established.

Seven decisions follow, each recorded here because each was a place to be
silently wrong.

### A third case in the rigidity story, composing rather than fighting

ADR-003/ADR-039 fix rigidity by type: leaves and fusions rigid,
assemblies non-rigid. A flexible leaf is the recorded exception both ADRs
anticipated — **the one non-rigid leaf kind** — and every consequence
falls out of rules that already exist rather than out of new ones:

- `FusionNode` already rejects a non-rigid child, so a flexible leaf
  cannot be fused. That is mechanically right: you cannot union a
  deforming spring into one printed solid.
- Non-rigid nodes already produce no cached rigid STL, so the
  mtime-caching precondition is untouched. This leaf is simply not in the
  cached set; nothing about time-invariance was relaxed for it.
- A topmost rigid node is a rigid node under a non-rigid parent. A
  flexible leaf is not rigid, so it is never a printed-solid boundary,
  contributes no piece, and never joins the inventory.
- `time` still raises on it, as on any leaf. Its shape is a pure function
  of its bound ports and of nothing else, so the ADR-008/ADR-056 access
  restriction stands verbatim rather than needing an exemption.

The binary distinction is therefore preserved. What changed is that
"leaf" and "rigid" stopped being the same word.

### Parameters arrive through ports, never through constructors

Per-instant values reach a flexible leaf exclusively through declared
ports, connected by the parent assembly in its `render()` — ADR-056's
machinery, with its one guardrail extended from *pose is a pure function
of the driver snapshot* to **shape is a pure function of the driver
snapshot**:

```python
class Spring(MolejoNode):
    height = TranslationalPort(unit='mm')

    def render(self):
        return Shape(profile=Circle(radius=2.0),
                     path=[Helix(radius=14.0, turns=6.5, height=P.height)],
                     path_samples=240, profile_samples=16)


class Valvetrain(AssemblyNode):
    lift = Driver(default=0.0, range=(0.0, 12.0), unit='mm')

    def render(self):
        self.connect(FREE_HEIGHT - self.lift, self.spring.height)
        return [self.retainer, self.spring]
```

The alternative — a constructor kwarg — fails on ADR-026: every
constructor parameter enters `uniq_id`, so a spring that follows a cam
would mint a fresh artifact identity every frame, and the identity
concept that keys the whole build would be measuring the wrong thing. A
port binding keeps `uniq_id` **structural**: two `Spring()` instances
share one identity, and the values flow through the seam drivers already
use. Under symbolic serialization the bound values are already
driver-token expression strings (ADR-056 stage 3a), so the document's
per-parameter expressions come out of ordinary solid2 arithmetic for
free; under a numeric snapshot they are plain numbers and the Python
evaluator runs.

Structural knobs that legitimately change the *spec* — a wire radius, a
coil count — remain ordinary constructor parameters. They change what
`render()` returns and therefore deserve a distinct `uniq_id`; the line
is between what a maker re-authors and what a machine moves.

**The port name is the parameter name**, and the two name sets must agree
exactly, checked in both directions immediately after `render()`: a shape
parameter with no port would be fed by nothing, and a port naming no
parameter would bind a value no geometry follows. Both fail naming the
node, the offending name, and both sets. An unbound port at evaluation or
serialization fails naming the node and the port — never a silent
default, matching the driver read discipline.

### `render()` returns the backend object, like every other adapter

`MolejoNode.render()` returns a molejo `Shape`, authored with molejo's
Python constructors and validated by the established `namespace`
mechanism (`namespace = 'molejo'`). The spec never leaves Python as a
hand-written JSON document; `shape.to_dict()` is the serialization the
framework embeds.

A new extension-point verb was considered, on the sheet adapter's
precedent. It was rejected because the precedent does not apply: the
sheet base owns `render()` precisely because it derives *two* products —
a solid and a cut file — from one authored profile, and a subclass
overriding `render()` could describe a different part from the one it
cuts. A flexible leaf derives one product from one source, so `render()`
returning the backend's object *is* the established adapter contract, and
inventing a verb would have made the flexible leaf the odd adapter for no
gain.

### The SCAD path gets a per-binding snapshot

`as_scad()` evaluates the shape at the current numeric binding through
the backend and imports the resulting STL, exactly as the kernel-owned
adapters do, so the assembled document stays complete and the OpenSCAD
GUI can still open any project. Two things differ, both consequences of
the geometry being state-dependent:

**The artifact name carries a binding hash.** The snapshot is
`<basepath>-<binding_hash>.stl`, the hash covering the resolved
parameter values (`binding_hash` in `node/base.py`, beside
`_build_uniq_id`). Within one binding, ordinary mtime equality decides
*source* currency, exactly as for any adapter-owned artifact; a different
binding is a different file. This is the whole reason the hash exists:
mtime can answer whether the source changed and cannot answer whether the
binding did, and a single per-node name would have let a stale pose sit
behind a current-looking stamp.

**The post-build sweep collects the rest — from the tree, not the
document.** The published document is serialized symbolically: it
describes the machine, not the pose, so it *cannot* name the file the
assembled SCAD actually imported. The assembled tree can, and it is the
same tree the publication describes, so each flexible node's
`snapshot_file` joins the referenced set and every other binding's
snapshot is swept. One nuance is accepted and recorded rather than
hidden: a build whose *only* change is the binding writes no new document
(the document is symbolic and identical), so no sweep runs and the
superseded snapshot survives until the next document-changing build. It
is an unreferenced file of bounded size, collected on the next
publication.

OpenSCAD gets a snapshot camera, never animation — the treatment drivers
already receive. The loader's binding of declared driver defaults
(ADR-056 stage 3a) makes the driver-fed build path well-defined; an
evaluation reached with an unbound port fails loudly rather than
guessing.

**A part fed by animation time gets no snapshot, and that is not a
failure.** Time is the one value nothing binds here: an assembly nobody
keyframed animates symbolically by contract (ADR-008), so a part whose
geometry follows the crank — a valve spring — reaches `as_scad()`
holding an `OpenSCADConstant`. There is no instant to photograph. Two
options were rejected. Failing loudly, which this ADR originally
implied, stops `assemble()` before the build publishes `viewer.json` —
and the document is precisely where a flexible part is delivered, so an
OpenSCAD-GUI convenience would be gating the real path; v8-engine's
valve spring reproduced exactly that. Substituting `$t = 0` would have
the framework guess which moment of the cycle matters, and would cost
either an evaluator for OpenSCAD expression strings (none exists —
solid2's `OpenSCADConstant` only builds them) or a re-entrant re-render
of the parent assembly at time 0 mid-assembly. So the camera declines:
no artifact, no geometry, assembly proceeds. The exemption is keyed on
the `$t` token, not on symbolic-ness, because a port still carrying a
raw driver token means the loader's default binding was skipped — a
wiring mistake, which goes on failing loudly. A part with no instant and
a part nobody wired are different diagnoses and are reported
differently. The cost is confined to the `.scad` path: OpenSCAD shows
the machine without the flexible part, which is honest, since it could
not have animated a deforming part in any case. The published document
is untouched and carries the full symbolic expression for the consumer
to evaluate per frame.

### Exact geometry is computed on demand and never persisted

`MolejoNode.exact` is `True`, fixed by adapter type like every other
adapter's — not by installation state, and not by which instant is bound.
`shape()` evaluates the current binding through molejo's B-rep evaluator
and returns the OCCT solid, recast to the CadQuery `Shape` the exact
layer trades in, so ADR-047's single currency holds and a spring composes
with a CadQuery part by the ordinary rule. solid-node already ships an
OCCT kernel through CadQuery, so `molejo[brep]` adds no kernel weight;
conditioning exactness on an optional extra would have made `exact`
install-state dependent, which the exact-geometry contract forbids.

What it does **not** do is write a `.brep`, and that is a decision rather
than an omission. Every structure around persistence is about rigid
nodes: `_artifacts_are_current` requires a `.brep` only where a node is
both rigid and exact; the exact composition path fuses the shapes its
children *return* rather than files they wrote, and a fusion refuses a
flexible child outright; and the sweep spares every `.brep` by extension,
unconditionally — so per-binding breps would accumulate forever with
nothing empowered to collect them. Nothing downstream waits for that
file. Worse, the caching it would enable is keyed wrong: `cached_shape`
and `cached_base_mesh` key on `(path, mtime)`, which is currency for a
source and not for a binding. The saving that path exists for — an
assertion asking one pair the same question twice — is kept instead by an
in-memory memo keyed on `binding_hash`, which measures the right thing.

The approximation is surfaced, not hidden. `FlexibleNode.shape_tolerance`
reports the backend's declared tolerance at the current binding: molejo's
`1e-6` where a helix or spline sweep has no closed form the kernel can
hold, and `0.0` where every surface is analytic. That honesty is the
backend's contract, and a caller reading an exact answer deserves to know
how exact.

### The document carries a third node shape, at the version its content needs

The serialized tree gains `flexible` beside `model` and `children`:

```json
{
  "name": "spring", "type": "LeafNode", "color": null, "mtime": 1756,
  "operations": [],
  "flexible": {
    "tech": "molejo",
    "spec": { "molejo": 1, "...": "..." },
    "params": { "height": "(46.8 - valvetrain.lift)" }
  }
}
```

`flexible` is a **discriminator on the node itself**, read off `node.flexible`
exactly as `node.rigid` already is, so the document's shape follows the
node's kind rather than a type test in the producer. `type` keeps its
established meaning — the framework's node *kind*, `LeafNode`, declared
once per kind and never overridden by an adapter or a project class, so
the spring and the rigid CadQuery part beside it publish the same word.
(This change's own design sketch illustrated `"type": "ValveSpring"`; the
normative requirement that a manifest keeps "the same observable schema"
as `viewer.json` governed, and the illustration was wrong.)

`params` maps each parameter to its expression string and carries **the
same verbatim guarantee operation expressions carry**, structurally
rather than by a second implementation: `drive_tree` binds every declared
driver to its qualified token before serialization, so a tree bound to a
numeric snapshot by a simulation still publishes
`(46.8 - valvetrain.lift)` and not the constant that instant computed.
Every qualified id a `params` expression references appears in the
`drivers` table, by the existing rule now covering `params` too.

**Version 3 iff the content needs it.** A document containing at least
one flexible node declares 3; a document containing none serializes
byte-identically to the version 2 it always was. `document_version()`
reads it off the finished tree rather than tracking it while building, so
the three producers sharing that walk cannot disagree about what they
just emitted. Bumping unconditionally was rejected: a flexible-free
document is bit-identical to version 2, and claiming otherwise would make
old consumers refuse documents they render perfectly. ADR-034 requires
the bump for a new tree shape; the drivers-table precedent — empty table,
old document verbatim — is what makes emitting the lowest sufficient
version the right reading of that requirement.

The spec is embedded inline rather than written as a sidecar: a molejo
document is hundreds of bytes to a few kilobytes, inlining keeps the
export self-contained, and there is nothing to deduplicate into `models/`
because there is no mesh. A flexible leaf contributes no `models/` entry
and no piece.

### The widget evaluates shape the way it already evaluates pose

The widget bundles molejo's JavaScript evaluator (plain ESM, zero
dependencies) through the delivery path ADR-035 built, and per flexible
node parses its `params` once through the existing evaluator cache,
evaluates them in the existing scope (`$t` plus the nested driver map),
and hands the values to molejo.

**Buffers are allocated by molejo's first evaluation and refilled in
place.** The fixed counts derive from the spec, so only the first call
can know them; it allocates `positions`/`index` and writes the index,
and every later call handed that same object refills `positions` and
never touches the index. Nothing is reallocated and no attribute is
replaced, which is what makes re-evaluation affordable at frame rate.

**One gating rule over two dependency sets.** A node's operations decide
whether its *matrix* recomputes; a flexible node's `params` decide
whether its *geometry* does. Both now go through one helper,
`touchedBy(free, changed)`, so a driver named by no `params` expression
costs a spring nothing and the two dependency sets can never drift into
two rules.

**Flat shading, chosen rather than defaulted.** molejo emits no normals.
Computing vertex normals would round the rim: molejo's mesh is indexed
and shares its rim vertices between wall and caps, so smooth normals
would disagree with the rigid part beside it — an STL arrives
non-indexed, so its computed normals are already per-face. Shading from
the derivatives matches that look and spares an O(V) pass on every driven
frame.

**Version acceptance became a set, and the refusals are prepare-phase.**
The accepted set is recorded as `[1, 2, 3]` with a loud refusal naming
the version and the ones rendered. This fills a gap rather than
tightening one: the baseline loader had **no** version check at all —
`assertRenderable` never read `document.version`, so a schema this build
could not read was rendered as far as it happened to parse. A `flexible`
node whose `tech` the package cannot evaluate is refused the same way,
and both refusals happen in the prepare phase, before the live tree is
touched, so a rejected document leaves the scene it was going to replace
standing.

`solidNodeViewerApi` rises 4 → 5: rendering flexible documents is a
capability a host may require.

### The dependency gate is stated, not faked

molejo is unpublished. Development installs it editable from the molejo
checkout and links the npm package from the same checkout; the committed
`pyproject.toml` and widget `package.json` entries name published forms
that resolve only once the pilot decides to publish. Those entries and
the packaging rebuild are therefore gated on that decision rather than
faked with local paths in committed metadata. The same rebuild resolves a
live drift this change found and did not create: `package.json` declares
`solidNodeViewerApi: 5` while the shipped `dist/` bundle — a symlink into
the pilot's primary checkout, deliberately not rebuilt here — still
declares 4.

## Pros and Cons of the Options

### A non-rigid leaf, port-fed, geometry as a spec

- **Good**: Every existing rule composes unchanged — fusion rejection,
  cache exclusion, piece inventory, `time` restriction — instead of being
  weakened for one node kind
- **Good**: `uniq_id` stays structural, so artifact identity keeps
  measuring what it was built to measure
- **Good**: The viewer representation is small and parameter-independent,
  so shape animates at frame rate with no reallocation
- **Good**: One evaluation mechanism serves pose and shape, gated by one
  rule
- **Bad**: A flexible technology must supply *two* evaluators (mesh and
  browser) plus, for exactness, a third; molejo is the only one today and
  the abstract surface is derived from what it needs
- **Bad**: Snapshot artifacts multiply per binding, and one superseded
  file can outlive its build until the next document-changing publication

### Constructor-parameter binding, one artifact per value

- **Good**: No new binding seam; a value is just a parameter
- **Bad**: ADR-026 makes every constructor parameter an identity, so a
  continuously varying value mints an artifact per frame
- **Bad**: Reintroduces exactly the storage cost ADR-003 rejected when it
  turned down time-frozen snapshots

### Serialized per-frame meshes (morph targets, frame swapping)

- **Good**: Needs no evaluator in the client
- **Bad**: Dies combinatorially beyond one parameter — a loom following
  X, Y and Z needs a sampled grid — which is the precise failure the
  analytic representation exists to remove
- **Bad**: Breaks the mtime-caching assumptions ADR-003 named

### Driver declarations on the leaf itself

- **Good**: A leaf would carry its own inputs, with no parent wiring
- **Bad**: Extends `set_state`/`drive_tree` into leaves and creates a
  second way for state to reach geometry
- **Bad**: Ports already are the typed connection point, keep the leaf
  pure, and let the parent own the wiring, as ADR-056 designed

### A sidecar spec file beside `models/`

- **Good**: Symmetric with how meshes travel
- **Bad**: More moving parts in the export for a payload of a few
  kilobytes, with nothing to deduplicate

### A new extension-point verb instead of `render()`

- **Good**: Would read symmetrically with the sheet leaf
- **Bad**: The sheet base owns `render()` because it derives two products
  from one authored source; here there is one product, and `render()`
  returning the backend object is the established adapter contract

### Bumping every document to version 3

- **Good**: One number to reason about
- **Bad**: A flexible-free document is bit-identical to version 2;
  declaring otherwise makes old consumers refuse documents they render
  perfectly

### Persisting the exact solid per binding

- **Good**: Consistent with every other exact node's `.brep`
- **Bad**: The sweep spares `.brep` files by extension, so per-binding
  ones would accumulate with nothing able to collect them
- **Bad**: `(path, mtime)` keying is currency for a source, not for a
  binding, so the cache would answer the wrong question
- **Bad**: Nothing reads it — the composition path fuses returned shapes,
  and a fusion refuses a flexible child anyway

## Consequences

The framework can now model a part whose shape follows the machine, and
the viewer animates that shape client-side at the same cost it already
paid to animate pose. The v8-engine's valve spring and Metamaquina2's
belts become expressible; whether they are *correct* is project-side
evidence consuming this change, recorded in molejo's own
`define-swept-shape-spec` section 8 rather than here.

The rigid/non-rigid distinction now has three cases where it had two, and
the word "leaf" no longer implies "rigid". Every rule that reads `rigid`
was already reading the right thing, so nothing had to be taught the
difference; but a future node kind must state which of the two axes it
sits on rather than assume they coincide.

`base_mesh()` became the single seam every framed view goes through, so a
node kind whose geometry is not a cached artifact overrides one method
instead of each framing separately. That is a small generalization of the
base class that the next non-artifact node kind inherits.

Adding a second flexible technology costs one adapter: a `namespace`, a
`tech`, and five backend hooks. It also costs a JavaScript evaluator and
a `FLEXIBLE_TECHNOLOGIES` entry in the widget, which is the honest price
of geometry that must be evaluated on both sides. Until then the abstract
surface is derived from what molejo needs, not invented ahead of
evidence; a second technology will revise the boundary from its own
requirements.

Deliberately out of scope, each awaiting its own evidence: OpenSCAD
*animation* of flexible parts (snapshot substitution only, consistent
with ADR-056's treatment of drivers), any flexible part that is not a
sweep, and any UI beyond rendering the geometry.

## References

- `solid_node/node/flexible.py` — `FlexibleNode`, the parameter surface,
  the snapshot artifact, the binding memo
- `solid_node/node/adapters/molejo.py` — `MolejoNode`
- `solid_node/node/base.py` — `binding_hash`, `base_mesh`,
  `_atomic_write_bytes`
- `solid_node/core/serializer.py` — `document_version`,
  `FLEXIBLE_DOCUMENT_VERSION`, the `flexible` node shape
- `solid_node/core/builder.py` — `collect_snapshots` in the artifact
  sweep
- `solid_node/viewers/widget/src/flexible.ts` — `FlexibleShape`, the
  reused buffers, flat shading
- `solid_node/viewers/widget/src/tree.ts` — `touchedBy`, the one gating
  rule over both dependency sets
- `solid_node/viewers/widget/src/viewer.ts` — `RENDERED_VERSIONS` and the
  prepare-phase refusals
- `tests/flexible_project/spring.py` — the representative caller
- `tests/test_flexible_node.py`, `tests/test_molejo_adapter.py`,
  `tests/test_flexible_document.py`,
  `solid_node/viewers/widget/src/flexible.test.ts`
- `openspec/changes/flexible-leaf-node/`
