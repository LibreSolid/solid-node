## Why

build123d is an actively developed OCCT-based parametric CAD library that
covers the same modelling ground as CadQuery with a different, more regular
API. The pilot surveyed available modelling technologies and found reported
evidence that build123d produces substantially fewer errors than CadQuery when
a coding agent writes the model. Because solid-node projects are increasingly
modelled by agents, a backend that agents get right more often is directly
useful to the framework's users, and the framework already has every mechanism
a B-rep backend needs — it only lacks the adapter.

Adding it forces a dependency decision the framework has been deferring:
solid-node pins `cadquery==2.5.*`, which pins `cadquery-ocp>=7.7,<7.8`, while
every build123d release from 0.9 onward requires `cadquery-ocp>=7.8`. The two
backends bind the same `OCP` module, so they cannot be installed together
until the CadQuery pin moves. That stale pin is pre-existing technical debt;
this change pays it down rather than shipping the new backend against a
two-year-old build123d.

## What Changes

- Add `Build123dNode`, a fifth `LeafNode` adapter backed by build123d,
  exported from `solid_node.node` alongside the existing four.
- `Build123dNode` is exact: it exposes `shape()`, persists a `.brep`
  artifact, and requires no OpenSCAD binary — the same contract
  `CadQueryNode` has under the `exact-geometry` capability.
- `Build123dNode.render()` accepts a build123d `Part`, `Solid` or `Compound`,
  or a `BuildPart` builder whose finished `.part` is taken. A render that
  produces a sketch or a curve is rejected with an error naming the node,
  because a leaf must produce a solid.
- Exact composition across backends is confirmed and kept: a `FusionNode`
  mixing `CadQueryNode` and `Build123dNode` children remains exact and fuses
  to a single solid. This follows from the existing every-child-is-exact rule
  and requires no new rule.
- **BREAKING** (dependency, not API): raise the CadQuery pin from
  `cadquery==2.5.*` to `cadquery==2.7.*` and add `build123d==0.10.*`, so both
  OCCT backends share `cadquery-ocp` 7.8. Existing project source is
  unaffected; existing environments must reinstall.
- Document build123d as a fifth backend in the modelling guide and API
  reference, on equal footing with the other four — not as a replacement for
  `CadQueryNode`.

## Capabilities

### New Capabilities

None. build123d support extends the existing multi-backend adapter
requirement rather than introducing a new capability.

### Modified Capabilities

- `node-model`: the enumerated set of leaf adapters gains `Build123dNode`;
  render validation gains a solid-shaped-result rule, because build123d's
  sketch and curve objects share the `build123d` namespace with its solids
  and so are not excluded by namespace validation alone.
- `exact-geometry`: the enumeration of which adapters are exact gains
  `Build123dNode` as a second exact adapter, and the existing composition rule
  is stated to hold across a mixture of exact backends.
- `openscad-dependency`: the enumeration of paths requiring the OpenSCAD
  binary is unchanged, and `Build123dNode` is named among the adapters that do
  not require it, so the all-exact-project guarantee covers it.

## Impact

- **New code**: `solid_node/node/adapters/build123d.py`; export in
  `solid_node/node/__init__.py`.
- **Changed code**: `solid_node/exact.py` gains the conversion from a
  build123d result to the OCCT shape the module already trades in; the
  backend-name lookup in `AbstractBaseNode.generate_stl` is unaffected because
  `Build123dNode` never reaches it.
- **Dependencies**: `cadquery` 2.5 → 2.7, new `build123d` 0.10,
  transitively `cadquery-ocp` 7.7 → 7.8. The workspace venv shared by the
  primary checkout and every bench must be reinstalled; validating this cycle
  in an isolated environment avoids disturbing pilot-controlled state until
  the change integrates.
- **Docs**: `docs/leaf-nodes.rst` (fifth backend section with the same
  box-with-hole example), `docs/api-reference.rst`, `README.rst` backend list.
- **Risk**: the CadQuery upgrade is the substantive risk, not the new adapter.
  The framework's CadQuery surface is small and enumerable — `Workplane`,
  `Shape.cast`, `Shape.importBrep`, `exportBrep`, `exportStl`,
  `Compound.makeCompound`, `Workplane.vals` — and all of it has been exercised
  against 2.7.0. The existing suite must confirm it end to end.
