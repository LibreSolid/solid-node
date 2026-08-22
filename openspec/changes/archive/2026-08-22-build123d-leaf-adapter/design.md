## Context

`LeafNode` subclasses adapt one CAD backend each. Two mechanisms matter for a
new one: `as_scad()`, which every adapter implements so the assembled document
stays complete, and the `exact-geometry` capability, which a
boundary-representation backend additionally implements as `exact` plus
`shape()`. `CadQueryNode` is currently the only adapter doing the second.

`solid_node/exact.py` is where exact geometry is traded. It holds shapes as
CadQuery `Shape` objects but performs the actual booleans and transforms
through OCP directly (`BRepAlgoAPI_Fuse`, `BRepAlgoAPI_Common`,
`BRepBuilderAPI_Transform`). The CadQuery layer is therefore thin: it supplies
`Shape.cast`, `Shape.importBrep`, `exportBrep`, `exportStl` and
`Compound.makeCompound`, and nothing else.

build123d is built on the same OCCT bindings and exposes the raw
`TopoDS_Shape` on every object as `.wrapped`. Its own documentation names
assignment through `.wrapped` as the supported way to move geometry between it
and CadQuery.

The constraint that shapes this change is packaging. `cadquery` and
`build123d` both depend on the `cadquery-ocp` distribution, which provides the
single importable `OCP` module. Their version ranges must intersect or the two
cannot be installed together:

| package | pin | resolved `cadquery-ocp` |
| --- | --- | --- |
| cadquery 2.5.2 (current) | `cadquery-ocp>=7.7,<7.8` | 7.7.2 |
| cadquery 2.6.1 / 2.7.0 | `cadquery-ocp>=7.8.1,<7.9` | 7.8.x |
| cadquery 2.8.0 | `cadquery-ocp>=7.9.3.1,<8.0` | 7.9.x |
| build123d ≤ 0.8.0 | `cadquery-ocp>=7.7.0` | any |
| build123d 0.9.1 / 0.10.0 | `cadquery-ocp>=7.8,<7.9` | 7.8.x |
| build123d 0.11.1 | `cadquery-ocp-novtk>=7.9,<8.0` | *different distribution* |

The current pin admits only build123d ≤ 0.8.0. The newest release of each
project cannot be combined at all: build123d 0.11.1 moved to
`cadquery-ocp-novtk`, a second distribution installing the same `OCP` package,
which would collide file-for-file with the `cadquery-ocp` that cadquery 2.8.0
requires.

## Goals / Non-Goals

**Goals:**

- A `Build123dNode` adapter with the same contract `CadQueryNode` has:
  SCAD emission, STL and BREP artifacts, `exact`, `shape()`, no OpenSCAD.
- A dependency set in which both OCCT backends are current and installable
  together, resolving the stale CadQuery pin as technical debt.
- Confidence that mixed-backend exact composition works, since the existing
  every-child-is-exact rule already permits it.

**Non-Goals:**

- Deprecating, replacing or discouraging `CadQueryNode`. build123d is
  documented as a fifth backend on equal footing.
- Making build123d optional. It joins the dependency set outright, like every
  other Python backend.
- Reworking `exact.py` to hold raw OCP shapes instead of CadQuery ones.
- Supporting build123d 0.11.x, which is unreachable while cadquery depends on
  `cadquery-ocp` rather than `cadquery-ocp-novtk`.
- Adapting a build123d-aware editor or viewer integration, the analogue of
  `CadQueryNode`'s CQ-editor metaclass.

## Decisions

### Pair cadquery 2.7.0 with build123d 0.10.0 on `cadquery-ocp` 7.8

The newest combination that resolves to one `OCP`. Rejected alternatives:

- **Keep cadquery 2.5.2, add build123d 0.8.0.** Resolves, and needs no
  CadQuery upgrade, but ships a backend far behind upstream and leaves the
  stale pin in place — the debt this change was asked to pay.
- **cadquery 2.8.0 with build123d 0.11.1.** Two distributions providing `OCP`;
  pip installs both and the later overwrites the earlier's files. Not a
  supportable configuration. Revisit when the two projects agree on one
  distribution again.
- **cadquery 2.6.1 with build123d 0.9.1.** Same OCP line, both a release
  behind the chosen pair, with no compensating benefit.

Verified empirically in a clean virtualenv on Python 3.11: `cadquery==2.7.0`
and `build123d==0.10.0` install together on `cadquery-ocp` 7.8.1.1.

### Keep CadQuery `Shape` as the exact currency; convert at the adapter boundary

`Build123dNode.shape()` returns `cq.Shape.cast(rendered.wrapped)`. Everything
downstream — placement, fuse, common, BREP persistence, volume and solid
counting — is then the code that already exists, unchanged, and mixed-backend
composition needs no special case at all.

The alternative, restating `exact.py` in terms of raw `TopoDS_Shape`, would
remove a dependency the module barely uses but would rewrite working,
specified code for no behavioural gain, and cadquery remains a dependency
regardless because `CadQueryNode` needs it.

Verified empirically: casting a build123d part through `.wrapped` reproduces
its volume exactly (109292.037 both sides), survives a BREP write/read
roundtrip at the same volume, exports STL, and fuses with a CadQuery shape
through `BRepAlgoAPI_Fuse` into a single solid.

### Validate the render result by shape kind, not namespace alone

Namespace validation cannot carry this adapter. build123d's solids, sketches
and curves all live under the `build123d` namespace — `Part` and `Compound` in
`build123d.topology.composite`, `Solid` in `build123d.topology.three_d`,
`Rectangle` in `build123d.objects_sketch`, `Line` in
`build123d.objects_curve`, and the `BuildPart` builder in
`build123d.build_part`. `namespace = 'build123d'` therefore admits all of
them, and a returned sketch would otherwise fail later and less legibly, in
the STL export.

The adapter accepts a solid (`Part`, `Solid`, `Compound`) or a `BuildPart`,
from which `.part` is taken, and rejects anything else naming the node and the
offending type. Accepting the builder is deliberate: `with BuildPart() as p:`
is build123d's headline idiom and returning `p` rather than `p.part` is the
mistake a user makes first.

### Convert once, in `exact.py`

`shape_from_rendered` already normalises a CadQuery render — unwrapping
`.vals()`, compounding several shapes into one. The build123d unwrapping
belongs beside it, so both adapters call one function and the persistence path
(`write_brep`, `write_stl`) stays identical for both.

## Risks / Trade-offs

- **The CadQuery upgrade breaks existing behaviour.** This is the real risk of
  the change; the new adapter is additive and can only fail on its own. The
  framework's CadQuery surface is small and fully enumerated above, and every
  call in it has been exercised against 2.7.0 — but project-level regressions
  in `Workplane` (84 uses across tests and the v8-engine example) would not
  show up there. → The existing suite is the gate: it must pass on the new
  pins before the adapter work is called done, and the v8-engine example is
  the representative caller.
- **Reinstalling the shared workspace venv disturbs pilot-controlled state.**
  The bench uses the workspace venv, so upgrading in place would change the
  primary checkout's environment and every other bench's mid-cycle. → Validate
  this cycle in an isolated virtualenv built from the bench, and leave the
  workspace venv to the pilot at integration.
- **Users upgrading solid-node get a forced OCP change.** `cadquery-ocp` is a
  large binary wheel; the upgrade is not free and cannot be partial, since one
  `OCP` serves both backends. → Call it out in the release notes as a required
  reinstall rather than an in-place upgrade.
- **The pinned pair goes stale as the two projects diverge again.** build123d
  0.11 already moved to a distribution cadquery does not use. → Pin both
  exactly rather than optimistically, and treat a future realignment as its
  own cycle with its own evidence.
- **`shape()` for a build123d node holds a CadQuery object.** Anyone reading
  `exact.py` sees a CadQuery type returned from a build123d node, which reads
  oddly until they know both wrap one `TopoDS_Shape`. → Say so in the module,
  at the conversion.

## Migration Plan

1. Raise the pins in `pyproject.toml`; reinstall.
2. Run the existing suite on the new pins before writing the adapter, so a
   CadQuery regression is attributed to the upgrade and not to the new code.
3. Add the adapter red-first.
4. On integration, the pilot reinstalls the workspace venv.

Rollback is the pin revert: the adapter is additive, and no existing project
source changes.

## Open Questions

None outstanding. The version pairing, the equal-footing framing, and mixed
exactness were decided by the pilot before this proposal.
