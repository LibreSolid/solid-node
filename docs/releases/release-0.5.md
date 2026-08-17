# solid-node 0.5.0 — release announcement

Released 17 August 2026. Full changelogs: [`HISTORY.rst`](../../HISTORY.rst)
and [`docs/changelog.rst`](../changelog.rst).

---

**The parametric CAD framework stops approximating.**

Since 0.4.0, 28 ratified change cycles landed. Three of them redefine what the
framework is: geometry is now answered *exactly*, a project is now *declared*
rather than guessed at, and there is now *one* viewer instead of three.

## Exact geometry — the big one

Every geometric question used to be mediated by a triangle mesh, even when your
CAD kernel could answer it exactly. Curved surfaces tessellate to chords, so two
parts that meet at a nominally perfect fit appear to interpenetrate the moment
their facet phases differ — which is the normal state of any assembly, because
assemblies rotate parts relative to one another.

A d=10 shaft in a d=10 bore: the exact Boolean common is 0 mm³. Rotate the shaft
7° and the mesh Boolean reports 0.060 mm³ of interference. That is a failing test
on a correct design, and the workarounds had already leaked out of test files and
into design documents — tessellation tolerances promoted to "master parameters",
epsilons threaded through a dozen assertion call sites.

0.5.0 routes every volume question through OCCT when both compared nodes are
exact. Nodes gain an `exact` property and a `shape()` accessor, and each exact
rigid node caches a `.brep` beside its `.stl`. **Verdicts change in both
directions** — real sub-facet interference now fails, and nominally exact fits
now pass — so retiring your epsilons is a deliberate, per-project act.

The B-rep artifact is *cheaper* than the STL next to it: 4 ms write / 2 ms read /
165 KiB, against 112 ms / 9 ms / 469 KiB.

## OpenSCAD is now optional

The last thing forcing an all-CadQuery project through OpenSCAD was fusion.
Exact composition removed it. An all-exact project now builds, tests, exports and
snapshots with OpenSCAD absent from the PATH — and a path that genuinely needs it
(Solid2 leaves, faceted fusions, the GUI viewer, the OpenSCAD snapshot renderer)
says what needed it and why, instead of a bare `FileNotFoundError` out of
`Popen`.

## Projects declare themselves

`root/__init__.py` is gone, and so is the `NODE` marker it made necessary. A
project declares its model in `[tool.solid-node]`, and every command takes an
optional reference:

```bash
solid build                              # the manifest's model
solid test windmill/sail.py              # a file
solid snapshot windmill.windmill:Sail    # any node, anywhere
```

The root is discovered from the nearest ancestor manifest rather than
`os.getcwd()`, so commands finally give the same answer from a subdirectory —
previously the source closure silently truncated there and reported stale
artifacts as current.

`solid test` also now loads **every** `TestCase` in a companion file rather than
the first. If you had extra cases quietly not running, they run now.

## Parts that are actually one part

Watertightness is a per-shell property: a component whose features never reached
each other is several disjoint closed shells, exports a valid STL, renders like a
part, and passes every check the framework used to offer. Three real projects
shipped parts in pieces through that gap.

New assertions, scaffolded into every new project by `solid new`:

```python
def test_solid_integrity(self):
    self.assertNoDisconnectedSolids(self.node)

def test_assembly_integrity(self):
    self.assertNoSolidInterference(self.node)
```

Plus `assertJoined(a, b, min_weld_volume=...)` — the one case where two features
are *required* to share volume.

## Printed-piece inventory

Published documents carry a `pieces` section: one entry per distinct printed
piece, identified by a content fingerprint of the built STL, with instance count,
bounding extents, volume and watertightness. Geometrically identical solids
collapse to one piece however the code was factored — in one gearbox, 24 artifact
keys are only 18 actual pieces — and mirrored parts stay distinct. Purely
additive.

## One viewer, updated in place

Three copies of the three.js renderer became one reusable package (declared API
version 4), consumed by static exports, the Sphinx directive and `solid develop`
alike. The development viewer inherits what it never had: colours, lights, a
fitted camera, animation controls.

It also stops tearing down the scene on every edit. A changed artifact is
refetched alone and swapped into the nodes referencing it; a document change
reconciles the tree, fetching only where `(model path, mtime)` genuinely moved.
An operations-only or colour-only edit costs no fetch at all. Previously a 113 MB,
55-STL assembly re-parsed and re-uploaded in full to show a one-leaf difference.

Hosts can also query the assembly tree and focus or hide subtrees through the
mount handle.

## Speed

| | before | after |
|---|---|---|
| No-op rebuild, CadQuery-heavy project | 19.8 s | 3.2 s |
| `assertNoSolidInterference`, 125 solids / 1.02M triangles | 273 ms | 2 ms |

The caching fix is the one that stings in hindsight: the up-to-date check ran
*after* `render()`, so caching saved almost nothing. It also now tracks the
modules your source imports — editing a shared `kinematics.py` used to move no
tracked mtime, so the watcher never saw the edit.

## New commands and flags

- `solid build` — build once, publish, exit. Exit 66 (`MODEL_NOT_FOUND`) for an
  unresolvable model.
- `solid develop --no-web` / `--callback URL` — headless watch loop for an
  external host that renders the build directory itself.
- `solid snapshot --renderer web` — headless Chromium capture with a real alpha
  channel, for compositing onto your own surface.
  `pip install "solid-node[web-snapshot]"`. Never falls back silently.
- `solid viewer` — reports the installed bundle's path and API version.

## Breaking changes at a glance

1. `[tool.solid-node]` manifest + references; `root/__init__.py`, the directory
   argument and `NODE` all removed.
2. `solid test` runs every `TestCase`; multi-node modules need `node = <Class>`.
3. Exact geometry changes assertion verdicts both ways; `volume_epsilon` is
   ignored (with a warning) on fully exact calls.
4. **A failed build now leaves a partially updated `_build`** rather than the
   previous complete set. In exchange, each artifact is written whole or not at
   all, and successful builds sweep dropped artifacts.
5. All-exact fusion STL bytes change (OCCT rather than CGAL tessellation) — piece
   ids for fusions go stale once.
6. `assertNoPairwiseIntersections` deprecated in favour of
   `assertNoSolidInterference`.

Also: concurrent builds are now serialized with an advisory `flock`, and
self-contained exports finally render when served from a subdirectory rather than
a server root — the bug that 404'd every mesh in the published V8 engine example.

---

## Where this release came from

Almost nothing above started as a design idea. 0.5.0 was driven by the
development of **LibreSolid Studio**, an agent-driven workshop for mechanical
design in which projects are actually built with solid-node — and in which a
framework change has to begin as evidence from one of those projects: the
epsilons that leaked out of test files into design documents, the component
that shipped as three disconnected shells, the 113 MB assembly that reloaded in
full to show one changed leaf, the shared `kinematics.py` whose edits the
watcher never saw, the published V8 engine that 404'd every mesh.

That is why the breaking changes above are as blunt as they are. Each one was
someone's afternoon first.

The Studio is not public yet. It will be, soon, under the same LibreSolid
umbrella as this framework.
