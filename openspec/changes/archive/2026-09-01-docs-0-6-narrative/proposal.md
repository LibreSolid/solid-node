## Why

0.6.0 (changelog recorded 2026-08-30 on the `release-0-6-0-packaging` branch)
turns a solid-node model into a *machine*: named drivers read as attributes,
domain-typed ports, a stepped simulation layer, a driveable viewer with
on-screen controls, three new leaf kinds (sheet, imported STL, flexible via
molejo), and a gravity/static-equilibrium assembly assertion. The published
documentation still tells the v0.3 story — "join several modelling
technologies and animate with `$t`" — and is unevenly migrated: pages touched
by recent feature cycles (`leaf-nodes`, `testing`'s gravity section) carry 0.6
material, while every framing page (`index`, `why-solid-node`, `quickstart`,
`viewer`, `embedding`, `fusion`, `assemblies`, `status-and-roadmap`, README)
is a release or more behind. The entire `solid_node.simulation` package
(`Sim`, `set_state`, `Instruction`, `ScenarioTest`, qualified enumeration)
appears in **no** user-facing page; `embedding.rst` states viewer API version
3 where the widget declares 5; `leaf-nodes.rst` says molejo is unpublished
when 0.6 makes it a hard PyPI dependency; and `docs/changelog.rst` has no
0.6.0 entry although `status-and-roadmap.rst` sends readers there.

## What Changes

- **Re-frame the narrative.** Rewrite the entry surface around "design and
  simulate machines": `index.rst` intro and toctree, `why-solid-node.rst`
  (full rewrite of the 10-line v0.3 stub), `quickstart.rst` (conditional
  OpenSCAD requirement, artifact inventory `.stl`/`.brep`/`.dxf`, a first
  driver as the payoff, upgrade/reinstall note), the README's user-facing
  section (tagline, layout including `solid_node/simulation/`, reinstall
  note), `status-and-roadmap.rst` (0.6 as released, refreshed roadmap from
  the changelog's deliberate deferrals).
- **Refresh the examples.** Bump the `docs/examples/v8-engine` submodule to
  its increment-9 head (`ef0b046`, the molejo flexible valve springs the
  changelog cites), add the Metamaquina2 printer
  (<https://github.com/LibreSolid/Metamaquina2>) as a second example
  submodule — a machine-level 0.6 showcase: X/Y/Z drivers with root
  instructions, three MolejoNode flexible parts (spring, GT2 belt,
  filament), legacy OpenSCAD sources wrapped through solid2 — and extend
  the Read the Docs live-export job to build both. Rewrite `examples.rst`
  around the two.
- **Two new tutorial pages.** *Driving a machine* — `Driver` declaration and
  attribute reads, `set_state`, instance-qualified ids, ports and
  `connect()`, instructions, and the viewer's layered controls; with a new
  committed driven-machine export under `docs/_exports/` (the two-axis
  printer from the changelog). *Simulating and testing scenarios* — `Sim`,
  `dt` and integer ticks, `at`/`every`/`trigger`/`run`, trajectories, and
  `ScenarioTest` under pytest and `solid test` alike.
- **Update every stale guide claim.** `animation.rst` (context-dependent
  `self.time`, trim its driver section to a pointer), `assemblies.rst`
  (drivers introduced where they are declared), `fusion.rst` (exact vs
  faceted fusion, "mesh" → "solid", the flexible-child refusal, the
  `StlNode` faceted downgrade), `node-tree.rst` (qualified driver ids as a
  naming rule, `.brep`/`.dxf` artifacts, integer-nanosecond freshness, ports
  outside the cache key), `viewer.rst` (the driving chrome), `embedding.rst`
  (API version 5, document schema versions 1/2/3, the full mount-handle
  driving API, `driverControls: 'none'`, a prominent warning that a 0.5.x
  viewer silently half-renders a 0.6 document, honest current limitations),
  `cli.rst` (prose touch-ups only; no flags changed), `leaf-nodes.rst`
  (remove "Installing molejo", molejo links to PyPI/readthedocs, base-class
  taxonomy `SheetLeafNode`/`FlexibleNode`, OCCT-family `fn` sentence, schema
  v3 note), `api-reference.rst` (new Ports and Simulation sections, the three
  missing leaf adapters, `set_state`, resolve the accumulate/reset
  contradiction).
- **Record the release in the docs.** A 0.6.0 entry in `docs/changelog.rst`
  mirroring the `HISTORY.rst` text recorded on the release branch, and
  `docs/releases/release-0.6.md` following the `release-0.5.md` template.
- **Keep the docs build honest.** Refresh `conf.py`'s
  `autodoc_mock_imports` for the 0.6 dependency set (build123d, scipy,
  rtree, molejo) without disturbing the bumpversion-managed `release` line.

Out of scope, flagged for the pilot: the version bump and `HISTORY.rst`
heading (owned by `release-0-6-0-packaging`); new Sphinx-directive or URL
options to preset drivers (framework features — documented as limitations
instead).

## Capabilities

### New Capabilities

- `user-documentation`: the published user-facing documentation set — what
  the narrative must cover for the release the package ships, the pages the
  toctree must offer, and the accuracy bar (version numbers, dependency
  claims, and compatibility warnings match the released behavior). Modeled
  on the `framework-contributor-guidance` precedent that put a prose
  deliverable under spec.

### Modified Capabilities

None. No runtime, CLI, viewer, or build behavior changes; the
`sphinx-embedding` capability is untouched.

## Impact

- `docs/*.rst` (all sixteen published pages, two new pages), `docs/index.rst`
  toctree, `docs/conf.py` (mock imports only), `docs/changelog.rst`,
  `docs/releases/release-0.6.md` (new), `docs/_exports/` (new committed
  driven-machine export, widget-less like the existing nineteen), `README.rst`
  (user-facing section), `.gitmodules` and `docs/examples/` (v8-engine bump,
  Metamaquina2 addition), `.readthedocs.yaml` (second live export; the
  OpenSCAD apt package and molejo for the export environment).
- No source, test, or Python-packaging changes. The Sphinx build itself must
  keep building without the CAD stack per the `sphinx-embedding` spec; the
  live example exports remain a Read the Docs `pre_build` concern, as the
  v8-engine export already is.
- Coordination: this cycle is based on `main` (`bd56aa6`), which predates the
  release branch's `HISTORY.rst` changelog commit; the `docs/changelog.rst`
  entry is authored here from that branch's text, so the two branches touch
  disjoint files and integrate cleanly in either order.
