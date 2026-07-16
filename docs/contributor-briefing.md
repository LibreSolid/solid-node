# Contributor briefing — working on the solid-node framework

Read this before changing framework code. It is the stable half of
every framework-work assignment; the other half is the issue spec you
were given.

## Layout

- `solid_node/node/` — the node tree: `base.py` (AbstractBaseNode:
  operations, mesh, artifact paths, checkpoints), `internal.py`,
  `assembly.py` (AssemblyNode: time, set_keyframe, idempotent renders),
  `fusion.py`, `leaf.py`, `adapters/` (CadQuery/Solid2/OpenScad/JScad
  backends), `operations.py` (Rotation/Translation: scad + mesh + serialized).
- `solid_node/manager/` — CLI commands (`develop`, `test`, `snapshot`,
  `new`), dispatched by `solid_node/cli.py`.
- `solid_node/core/loader.py` — node/test loading conventions.
- `solid_node/test.py` — the TestCase with mesh assertions.
- `solid_node/viewers/web/` — FastAPI backend + React/three.js app
  (`app/src/*.ts`, jest tests alongside).
- `tests/` — pytest suite. `tests/meta_project/` + `tests/test_meta.py`
  are the meta-test harness (below).
- `examples/gearbox/` — a real project used as regression canary.

## The meta-test harness

Unit tests with fake nodes cannot catch bugs in the render/keyframe/
mesh machinery — they stub exactly that layer. So behavior fixes are
TDD'd end-to-end: `tests/meta_project/` contains small but REAL
solid-node projects whose node tests are deliberately green (the
contract genuinely holds) or deliberately red (genuinely violated);
`tests/test_meta.py` runs `solid test` on each as a subprocess and
asserts every test is reported with the correct color, for the correct
reason (the assertion, not an ImportError or a vacuous pass).

For a behavior bug, write the adversarial PAIR when possible:

- a green fixture that fails on the broken framework (the correct
  behavior, stated as a contract), and
- a red fixture that PASSES on the broken framework — the case where
  the broken instrument lies (e.g. reports an intersecting mechanism
  as collision-free). This is the dangerous direction; do not skip it.

Fixtures are cheap: unit cubes (`tests/meta_project/parts.py`),
static or `self.time`-driven assemblies, mesh assertions on
`center_mass`/intersection.

## Discipline

1. Write the failing test FIRST (meta fixture for behavior, plain
   pytest for units/CLI), run it, watch it fail for the stated reason.
2. Implement the fix. Keep it minimal and in the framework's idiom.
3. Full gates, all must pass:
   - `.venv/bin/python -m pytest tests/ -q` (includes the meta harness)
   - gearbox canary, from `examples/gearbox/`, chained:
     `for f in root/__init__.py root/gear.py root/gear_pair.py root/shaft.py root/mounted_gear.py root/bushing.py root/supported_shaft.py root/housing_wall.py; do /home/asa/devel/solid-node/.venv/bin/solid test $f || break; done`
     (each run must end `0 failed`; `solid test` exits nonzero on failure)
   - frontend, only if you touched `viewers/web/app`: `npm test` there.
4. Never adjust a meta-test expectation or an existing test to make a
   fix pass. If an existing test encodes the OLD buggy semantics, say
   so explicitly in the commit message and update it in the same
   commit — the new semantics must be strictly safer.
5. One issue = one commit (plus a separate commit for its fixture if
   you prefer red-then-green history). Message style: imperative
   subject, body explains the failure mode and the fix, ending with
   `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` (or your
   model's name). Do not push.
6. Write every file complete and consistent — no staged half-edits.
7. Report honestly: if a gate fails, report the failure and stop;
   never mark done with red gates.

## Environment

- venv: `/home/asa/devel/solid-node/.venv` (editable install; the
  gearbox canary uses the same venv, so framework edits apply live).
- `openscad` is on PATH; headless rendering needs `xvfb-run -a`.
- Repo root is the cwd for pytest; `SOLID_BUILD_DIR` redirects build
  artifacts (the meta harness sets it to `tests/_build_meta`).
