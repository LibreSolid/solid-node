## Why

OpenSCAD is declared as a blanket installation requirement — `README.rst`
tells every user to put it on the PATH, and `node-model` ratifies all leaf
adapters as "compiled through OpenSCAD as the universal target". For a large
and growing share of projects that is no longer true.

Traced with a wrapper binary on the PATH, after the `exact-brep-geometry`
cycle:

- `projects/snowman` (CadQuery leaves and a `FusionNode`) builds with **zero**
  OpenSCAD invocations and writes four `.brep` artifacts. The fusion was the
  last invocation in an all-CadQuery project, and exact composition removed
  it.
- `projects/snowman-3` (Solid2 leaves) makes **seven**, and must keep doing so.

Eleven of the eighteen projects in the catalogue are pure CadQuery, including
every substantial one — `v8-engine`, `gearbox`, `american-windmill`, `guitar`,
`dutch-windmill`, `windmill`. None of them needs OpenSCAD to build, test, or
publish, yet all of them are told to install it, and a user without it gets a
bare `FileNotFoundError` out of `Popen` rather than an explanation.

This is the remaining half of ADR-004's accepted cost. `exact-brep-geometry`
addressed the precision half; this cycle addresses the dependency half, and
leaves the multi-backend promise itself intact — OpenSCAD stays required by
every path that genuinely uses it.

## What Changes

- **New**: an explicit contract for when OpenSCAD is needed. It is required by
  the paths that invoke it — rendering a `Solid2Node` or `OpenScadNode` leaf's
  STL, rendering a faceted fusion's STL, evaluating a `Solid2Node` symbolic
  value, the OpenSCAD GUI viewer, and the OpenSCAD snapshot renderer — and by
  nothing else. A project whose model is entirely exact SHALL build, test, and
  publish with OpenSCAD absent from the PATH.
- **Deferred, and stated as such**: `JScadNode` is not on that list. It renders
  its own STL through the separate `jscad` binary, so it never reaches
  OpenSCAD — but it carries the identical problem with a different tool.
  Extending the same enumeration, guarantee and actionable failure to `jscad`
  is left to a later cycle so this one keeps a single external tool in scope.
- **New**: when a path needs OpenSCAD and it is not available, the framework
  SHALL fail with an actionable error naming what needed it and why, rather
  than a bare `FileNotFoundError` from a subprocess launch. It SHALL NOT
  substitute another renderer or a mesh path, consistent with the existing
  no-silent-substitution rule.
- **Modified**: `node-model` stops describing OpenSCAD as the universal
  compilation target for all adapters. Mesh-backend adapters still compile
  through it; an exact adapter's artifacts are produced by its own kernel.
  `as_scad()` remains on every adapter — the SCAD document is still written,
  and the OpenSCAD GUI viewer still consumes it.
- **Modified**: `solid develop --openscad` and `solid snapshot --renderer
  openscad` report the missing tool clearly instead of failing obscurely.
- **Modified**: `README.rst` states OpenSCAD as conditional on the backends a
  project uses rather than as a blanket requirement.
- **Unchanged deliberately**: `--renderer` keeps defaulting to `openscad`. An
  exact project on a machine without OpenSCAD passes `--renderer web`
  explicitly and is told so by the error. Changing the default would silently
  alter the appearance of every existing project's snapshots — different
  background and colour scheme — and the shop's recorded visual evidence
  depends on that continuity. Selecting a renderer by availability was
  rejected for the same reason the web renderer already refuses to fall back
  to OpenSCAD: no silent substitution.

**BREAKING**: none for a working installation. A user who has OpenSCAD
installed sees no behavioural change at all; this cycle only removes an
obligation and improves a failure message.

## Capabilities

### New Capabilities

- `openscad-dependency`: which paths require the OpenSCAD binary, the
  guarantee that an all-exact project requires none of them, and the
  actionable-failure contract when a required path cannot find it.
  Cross-cutting, in the manner of `exact-geometry` and `printed-pieces`.

### Modified Capabilities

- `node-model`: OpenSCAD is the compilation target for mesh-backend adapters
  rather than for all adapters universally; an exact adapter produces its
  artifacts through its own kernel while still emitting SCAD.
- `build-pipeline`: the asynchronous STL render protocol names the
  availability contract for the subprocess it launches.
- `cli`: `solid snapshot --renderer openscad` reports a missing binary
  actionably, naming `--renderer web` as the alternative.
- `web-snapshot`: the renderer-choice requirement gains the symmetric failure
  for the OpenSCAD renderer that it already specifies for the web renderer.
- `web-viewer`: `solid develop --openscad` reports a missing binary
  actionably.

## Impact

- `solid_node/node/base.py` — `stl_builder_command_for` and the
  `StlRenderStart` launch path.
- `solid_node/node/adapters/solid2.py` — `as_number`'s subprocess.
- `solid_node/viewers/openscad.py` — `OpenScadViewer` and `OpenScadRenderer`.
- `solid_node/manager/snapshot.py` — the renderer selection error path.
- `README.rst` — the stated requirement.
- `docs/adrs/` — ADR-004's "universal compilation target" decision is
  superseded in part; the multi-backend adapter pattern it established stands.
- No dependency is added or removed from `pyproject.toml`; OpenSCAD was never
  declared there, which is precisely why the obligation lived only in prose.
- Validating callers: `projects/snowman` (all-exact, must build with OpenSCAD
  removed from the PATH) and `projects/snowman-3` (Solid2, must still work and
  must fail actionably when OpenSCAD is absent).
