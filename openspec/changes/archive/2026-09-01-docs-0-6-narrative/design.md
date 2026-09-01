# Design: v0.6 user-documentation overhaul

## Context

Four audits of the published docs against the 0.6.0 changelog (recorded on
`release-0-6-0-packaging`) found the doc set unevenly migrated: feature
cycles updated the pages they touched (`leaf-nodes.rst`, the gravity section
of `testing.rst`, parts of `animation.rst` and `api-reference.rst`), while
the framing pages still tell the v0.3 story and the simulation layer is
absent everywhere. Constraints: the docs build consumes committed exports
under `docs/_exports/` and must build without the CAD stack
(`sphinx-embedding` spec); `docs/conf.py`'s `release` line is
bumpversion-managed and must keep its exact search/replace shape; the cycle
is based on `main` (`bd56aa6`), which the release branch's `HISTORY.rst`
commit is not on.

## Goals / Non-Goals

**Goals**: every published page's claims true for 0.6.0; the machine
narrative on the entry surface; the motion/simulation surface fully
documented; the release recorded in `docs/changelog.rst` and
`docs/releases/`; the embedding compatibility warning present.

**Non-Goals**: the version bump and `HISTORY.rst` heading (release branch);
new framework features
(Sphinx driver options, snapshot driver flags — documented as limitations);
restructuring `leaf-nodes.rst` (717 lines) or `testing.rst` (555 lines)
into multiple pages — recorded as candidate follow-ups to keep this cycle
reviewable and inbound links stable.

## Decisions

1. **Two new pages, placed where the tutorial flow needs them.** The
   Tutorial toctree becomes `leaf-nodes, assemblies, animation, driving,
   fusion, testing, scenarios`. *Driving a machine* (`driving.rst`) sits
   after `animation` so `$t` motion is learned first and drivers arrive as
   its generalization; *Simulating and testing scenarios* (`scenarios.rst`)
   sits after `testing` because `ScenarioTest` composes over the `TestCase`
   machinery that page teaches. Alternative — growing `animation.rst` and
   `testing.rst` in place — rejected: each would double and bury its
   existing tutorial.
2. **One authoritative home per concept, cross-referenced elsewhere.** The
   driver-control chrome (sliders, buttons, layer scoping, breadcrumb) is
   described once in `driving.rst`; `viewer.rst` and `embedding.rst` get
   short sections that link there. Ports vocabulary (`Port` domains, units,
   causal `connect()`) moves to `driving.rst`; the `MolejoNode` section of
   `leaf-nodes.rst` trims to a reference. The mount-handle JavaScript API is
   documented in `embedding.rst` (its only audience is hosts), not a
   separate JS-reference page.
3. **The driven demo is the changelog's own example.** A small two-axis
   printer (two instances of one `Axis` class, one instruction) written
   inline in `driving.rst`, exported by hand with `solid export` and
   committed widget-less under `docs/_exports/`, like the nineteen existing
   demos. It demonstrates drivers, qualified ids, and instruction buttons
   in one model; `tests/meta_project/axis.py` is the reference for realistic
   `Driver(dtype=int, scale=...)` declarations.
4. **The changelog entry is authored from the release branch's text.** This
   cycle writes the `docs/changelog.rst` 0.6.0 entry (and
   `docs/releases/release-0.6.md`, on the `release-0.5.md` template) from
   `release-0-6-0-packaging`'s `HISTORY.rst`; that branch touches only
   `HISTORY.rst` and packaging metadata, so the branches modify disjoint
   files and integrate in either order.
5. **Docs describe the release, not the `main` snapshot.** `main` still
   lacks the molejo packaging dependency (it lands with the release branch),
   but the docs state molejo as a hard dependency because that is 0.6.0's
   truth. The pilot integrates both branches before tagging.
6. **`api-reference.rst` grows by autodoc, not prose.** New `Ports` and
   `Simulation` sections and the three missing leaf adapters are autodoc
   directives over existing docstrings (`set_state` alone carries a 40-line
   docstring); `conf.py`'s `autodoc_mock_imports` gains the 0.6 imports
   (`build123d`, `scipy`, `rtree`, `molejo`) so RTD keeps building without
   the CAD stack.
7. **A new spec capability governs the doc set.** `user-documentation`
   follows the `framework-contributor-guidance` precedent: requirements
   describe what a reader must find, phrased durably ("the released
   version") so the spec survives 0.7.
8. **Both examples follow the existing submodule + live-export pattern.**
   The v8-engine submodule bumps to `ef0b046` (increment 9, the molejo
   flexible valve springs the changelog cites, making its anecdote
   reproducible from the pinned source). Metamaquina2
   (`github.com/LibreSolid/Metamaquina2`) joins as a second submodule under
   `docs/examples/` with its own `pre_build` export in `.readthedocs.yaml`.
   Two environment consequences, both confined to the RTD job: the export
   environment needs molejo (both examples now evaluate MolejoNode leaves at
   export time — molejo is not yet in `requirements.txt`, which is what RTD
   installs) and the OpenSCAD binary via `build.apt_packages` (Metamaquina2's
   leaves read the original `.scad` sources through solid2's `import_scad`).
   Alternative — committing a Metamaquina2 export like the tutorial demos —
   rejected: a full printer's STL set would bloat the repository, and the
   live-export pattern already exists for exactly this case.

## Risks / Trade-offs

- [Prose accuracy cannot be tested red-first] → Verification is a
  requirements review: each spec scenario is checked against the built HTML,
  plus a full `sphinx-build` with warnings treated as errors for link and
  directive integrity, run on the committed exports only.
- [Docs claims depend on the unmerged release branch] → Decision 5;
  integration-order independence per decision 4; the proposal flags it to
  the pilot.
- [New export must not drag the CAD stack into RTD] → The export is built
  locally and committed; the Sphinx directive completes widget files from
  the installed package, per the existing spec.
- [Deferred page splits leave two long pages] → Their stale statements are
  still fixed in place; splits recorded as follow-up candidates.
- [RTD build cost grows: a second live export, one requiring OpenSCAD] →
  Both exports are timed during apply by running the same commands locally;
  if the Metamaquina2 export proves too slow for the RTD job, the fallback
  (a committed export, or embedding only a subassembly) goes back to the
  pilot as a choice rather than being decided silently.

## Open Questions

None. (The v8-engine submodule question from the first draft was resolved
by the pilot: the example repositories are pushed and both bumps are in
scope.)
