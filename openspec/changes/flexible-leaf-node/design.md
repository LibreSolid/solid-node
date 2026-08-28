# Design: the flexible leaf and the molejo adapter

## Two classes, one boundary

`FlexibleNode` owns everything the framework needs regardless of which
technology evaluates the shape: the non-rigid-leaf semantics, port-fed
parameters, the snapshot mesh path, document serialization, and the
loud failure modes. `MolejoNode` owns everything molejo-specific: the
`Shape` render contract, mesh evaluation, B-rep evaluation, and the
embedded spec format. This mirrors `ExactLeafNode`→`CadQueryNode` and
`SheetLeafNode`→`Build123dSheetNode` (ADR-053): an internal base
carrying the mechanics, a concrete adapter carrying the backend. The
"Leaf adapters are distinct types" requirement applies unchanged —
sharing the base never makes adapters interchangeable to a type test.

molejo is the only flexible technology today, so `FlexibleNode`'s
abstract surface is derived from what molejo needs, not invented ahead
of evidence. A second technology, if one ever arrives, will revise the
boundary from its own requirements.

## A third case in the rigidity story — deliberately

ADR-003/ADR-039 fix rigidity by type: leaves and fusions rigid,
assemblies non-rigid. A flexible leaf is the recorded exception both
ADRs anticipated: a **non-rigid leaf**. The consequences compose with
the existing rules rather than fighting them:

- `FusionNode` already rejects a non-rigid child, so a flexible leaf
  cannot be fused — mechanically correct: you cannot union a deforming
  spring into one printed solid.
- Non-rigid nodes already never produce a cached rigid STL, so the
  mtime-caching precondition ("rigid geometry is time-invariant") is
  untouched — the flexible leaf simply is not in the cached set.
- The topmost-rigid-node definition is unaffected: a flexible leaf is
  not rigid, so it is never a printed-solid boundary. It is not a
  printed piece and never joins the piece inventory.
- `time` on a flexible leaf still raises. Its shape is a pure function
  of its bound ports, nothing else (see next section), so the
  ADR-008/ADR-056 access restriction stands verbatim.

## Parameters arrive through ports, never constructors

The molejo parameters of a flexible leaf are fed exclusively by
declared ports, connected by the parent assembly in its `render()` —
the ADR-056 machinery, extended from "pose is a pure function of the
driver snapshot" to "shape is a pure function of the driver snapshot":

```python
class ValveSpring(MolejoNode):
    height = TranslationalPort(unit='mm')

    def render(self):
        return Shape(
            profile=Circle(radius=2.0),
            path=[Helix(radius=14.0, turns=6.5, height=P.height)],
            path_samples=240, profile_samples=16,
        )

class Valvetrain(AssemblyNode):
    lift = Driver(default=0.0, range=(0.0, 12.0), unit='mm')

    def render(self):
        spring = ValveSpring()
        self.connect(self.free_height_signal, spring.height)
        return [..., spring]
```

Why not constructor kwargs: every constructor parameter enters
`uniq_id` (ADR-026), so a continuously varying value would mint a new
artifact identity per frame. Port binding keeps `uniq_id` structural —
two `ValveSpring()` instances share one identity — while the values
flow through the same seam drivers already use. Under symbolic
serialization the bound port values are already driver-token
expression strings (ADR-056 stage 3a), so the document gets its
per-parameter expressions for free from ordinary solid2 arithmetic;
under a numeric snapshot they are plain numbers and the Python
evaluator runs.

Structural knobs that legitimately change the *spec* (a wire radius, a
coil count) remain ordinary constructor parameters: they change what
`render()` returns and therefore deserve a distinct `uniq_id`.

The port name is the parameter name. After `render()` returns the
shape, the base checks the shape's parameter names against the node's
declared ports: a shape parameter with no port, or a port naming no
shape parameter, fails loudly naming the node, the port, and the two
name sets. An unbound port at evaluation or serialization time fails
naming the node and the port — never a silent default, matching the
driver read discipline.

## The render contract is the backend object, like every adapter

`MolejoNode.render()` returns a molejo `Shape` (authored with molejo's
Python-first constructors), validated by the established `namespace`
mechanism (`namespace = 'molejo'`). This keeps the adapter shaped like
every other adapter — `render()` returns the backend's object — rather
than inventing a new extension-point verb. The spec never leaves
Python as a hand-written JSON document; `shape.to_dict()` is the
serialization the framework embeds.

## What the build path sees: per-binding snapshots

The assembled SCAD document should stay as complete as it honestly can
(the OpenSCAD GUI can open any project), so `as_scad()` on a flexible
leaf evaluates the shape at the current numeric binding through
molejo's Python evaluator and imports the resulting STL, exactly like
the kernel-owned adapters. Three differences, all consequences of the
geometry being state-dependent:

- **The artifact name carries a binding hash.** The snapshot STL is
  `<script>-<uniq_id>-<binding-hash>.stl`, where the hash covers the
  resolved parameter values. Within one binding the normal
  mtime-equality rule applies (a re-assembly at the same state does
  not re-evaluate); a different binding is a different artifact. The
  existing post-build sweep collects unreferenced snapshots.
- **Loader defaults make the driver-bound case well-defined.**
  `load_node` already binds declared driver defaults (ADR-056 stage
  3a), so every driver-fed port has a numeric snapshot; an evaluation
  reached with an unbound port still fails loudly rather than guessing.
- **A time-fed port has no instant, and the camera says so.** Animation
  time is the one thing the loader cannot bind: `self.time` is
  deliberately symbolic on the build path (`solid_node/math.py`), so a
  part whose geometry follows the crank — a valve spring — reaches
  `as_scad()` holding an `OpenSCADConstant`, not a number. There is no
  instant to photograph, and inventing one (`$t = 0`) would be the
  framework guessing which moment of the cycle matters. The camera
  emits no geometry for that leaf instead, and the build carries on.
  The exemption is keyed on animation time specifically, not on
  symbolic-ness: a port still carrying a raw driver token means the
  loader's default binding was skipped, which is a mistake and goes on
  failing loudly. A part with no instant and a part nobody wired are
  different diagnoses.

OpenSCAD gets a snapshot camera, never animation — the same treatment
drivers already get (numeric substitution, interactivity lost). Where
even a snapshot is undefined, it gets nothing, which is the honest
answer: OpenSCAD cannot show a deforming part in any case. This costs
the `.scad` path only. The published document is unaffected — it
carries the full symbolic expression, and the viewer re-evaluates the
spec per frame, which is where a flexible part is meant to be seen.

## The document carries the spec, not a mesh

The serialized tree gains a third node shape beside `model` and
`children`:

```json
{
  "name": "spring", "type": "ValveSpring", "color": null, "mtime": ...,
  "flexible": {
    "tech": "molejo",
    "spec": { "molejo": 1, ... },
    "params": { "height": "(46.8 - (valvetrain.lift * 1.0))" }
  }
}
```

- `spec` is the molejo document verbatim (`shape.to_dict()`).
- `params` maps each parameter to its expression string, produced by
  the same symbolic mode and carrying the same verbatim guarantee as
  operation expressions; every qualified id referenced must appear in
  the document's `drivers` table (existing rule, now covering `params`
  too).
- **Versioning:** a document containing at least one flexible node
  declares `version: 3`; a document containing none serializes exactly
  as today, `version: 2`. Rationale: ADR-034 makes a new tree shape a
  breaking change requiring a bump, while the drivers-table precedent
  (empty table ⇒ old document verbatim) shows the value of emitting the
  lowest version the content needs — an old consumer refuses only
  documents it genuinely cannot render. Consumers accept 2 and 3.

Export embeds the `spec` inline rather than writing a sidecar file:
the spec is small (a molejo document is a few hundred bytes to a few
kilobytes), inlining keeps the manifest self-contained, and there is
no artifact for `models/` deduplication because there is no mesh.

## The widget evaluates shape the way it evaluates pose

The widget bundles molejo's JavaScript evaluator (plain ESM, zero
dependencies; added to `package.json` and the license banner — the
delivery path ADR-035 built). Per flexible node it:

1. parses each `params` expression once (existing jokenizer cache),
   taking the union of free variables;
2. on frames where none of those variables changed, does nothing —
   the existing change-set machinery extends to flexible nodes with
   the same rule operations use;
3. otherwise evaluates the expressions in the existing scope
   (`$t` + nested driver map) and calls molejo's `evaluate(spec,
   values, buffers)` into per-node reused buffers — molejo's declared
   contract is fixed vertex count/order and in-place buffer reuse, so
   no reallocation and no topology change ever happens at frame rate.

Cross-runtime numeric agreement between the two molejo evaluators is
pinned by molejo's own parity fixtures; what this repo owes is the
*binding* seam: the producer-generated parity fixture grows a case
proving that a parameter expression evaluated client-side and fed to
molejo-js agrees with the Python-side binding fed to molejo-python
within fixture tolerance, on a real spring document.

The loader refuses a `flexible` node whose `tech` it cannot evaluate,
naming the technology — same posture as refusing an undeclared driver
id: refuse loudly rather than render a wrong shape.

`solidNodeViewerApi` is raised 4 → 5: rendering flexible documents is
a capability a host may require.

## Exactness: molejo's B-rep evaluator, unconditionally

`MolejoNode.exact` is `True`, fixed by adapter type like every exact
adapter. `shape()` evaluates the current binding through
`molejo.brep.evaluate` and returns the OCCT solid. solid-node already
ships an OCCT kernel through its CadQuery/build123d dependencies, so
depending on `molejo[brep]` adds no new kernel weight; conditioning
exactness on an optional extra would have made `exact` install-state
dependent, which the exact-geometry spec forbids ("determined by its
adapter type"). Helix/spline sweeps carry molejo's declared
approximation tolerance; that honesty is molejo's contract and is
surfaced, not hidden.

## Dependency reality (pilot-gated)

molejo is unpublished. Development installs it editable from the
molejo checkout into the workspace venv, and the widget links the npm
package from the same checkout. The committed `pyproject.toml` and
widget `package.json` dependency entries only resolve once molejo is
published to PyPI and npm under the versions they name; publishing is
the pilot's explicit decision and gates the final packaging tasks.
This is stated in the tasks rather than hidden in a lockfile.

## Alternatives considered

- **Driver declarations on the leaf itself** (a leaf with `_states`) —
  rejected: it would extend `set_state`/`drive_tree` into leaves and
  create a second way for state to reach geometry. Ports already exist
  as the typed connection point, keep the leaf pure, and let the
  parent own the wiring, as ADR-056 designed.
- **Constructor-parameter binding with per-value artifacts** —
  rejected: ADR-026 makes every constructor parameter an identity;
  ADR-003 already rejected time-frozen snapshots for storage cost and
  cache breakage. (Structural knobs stay constructor parameters.)
- **Serializing per-frame meshes (morph targets / frame swapping)** —
  rejected: dies combinatorially beyond one parameter (a loom
  following X, Y, Z needs a sampled grid); this is the exact failure
  molejo exists to remove.
- **A sidecar spec file beside `models/`** — rejected: inlining keeps
  the export self-contained with fewer moving parts; specs are small.
- **Always bumping the document to version 3** — rejected: a
  flexible-free document is bit-identical to version 2; claiming
  otherwise would make old consumers refuse documents they render
  perfectly.
- **`exact` conditional on the `brep` extra** — rejected: forbidden by
  the exact-geometry contract and needless, since the OCCT kernel is
  already a solid-node dependency.
- **A new extension-point verb instead of `render()`** (like the sheet
  adapter's `profile()`) — rejected: the sheet base derives *two*
  products from one authored source, which is what justified owning
  `render()`; here `render()` returning the backend object is exactly
  the established adapter contract.

## Incidental findings

- The `viewer-package` baseline says the declared API version "SHALL
  be 3" while the shipped `package.json` declares 4 — the driver-API
  bump landed in code without the spec sync. This change's delta
  states 5 and corrects the drift it found.
- `leaf.py`'s `time` exception message ("Implementing a FlexibleNode
  is in the roadmap") becomes false the moment this lands; it is
  rewritten to point at `MolejoNode` and port-fed parameters, and the
  roadmap entry is updated.
