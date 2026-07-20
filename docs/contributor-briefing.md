# Contributor briefing — working on the solid-node framework

This is a compact orientation to the framework and its verification tools. For
the current architecture, read [the architecture synthesis](architecture.md).
For observable contracts, read the relevant record in
[`openspec/specs/`](../openspec/specs/); for the reasoning behind an accepted
architectural choice, read [`docs/adrs/`](adrs/README.md).

## Layout

- `solid_node/node/` — the node tree: `base.py` defines
  `AbstractBaseNode`; `internal.py`, `assembly.py`, `fusion.py`, and `leaf.py`
  define the tree roles; `adapters/` contains CAD backends; and
  `operations.py` defines transformations.
- `solid_node/manager/` and `solid_node/cli.py` — the `solid` command and its
  commands, including development, testing, snapshots, scaffolding, and
  export.
- `solid_node/core/loader.py` — node and test loading conventions.
- `solid_node/test.py` — mesh-oriented test cases and assertions.
- `solid_node/viewers/web/` — the FastAPI backend and React/three.js viewer;
  browser tests live with the application.
- `tests/` — the Python test suite. `tests/meta_project/` with
  `tests/test_meta.py` forms the end-to-end meta-project harness.

## Choosing evidence

Use direct pytest coverage for local units and CLI behavior. Use the
meta-project harness when the claim depends on real node loading, rendering,
keyframes, meshes, or the `solid test` subprocess path. Fake nodes and mocks
are useful at a local boundary but cannot establish that the real rendering and
test pipeline behaves correctly.

The meta-project harness runs small real solid-node projects. Their tests may
be deliberately green, proving the stated contract, or deliberately red,
proving that an invalid project is rejected for the intended reason rather
than because of an import error or vacuous pass.

For behavior defects, create the adversarial pair when practical:

- a valid fixture that fails on the broken framework; and
- an invalid fixture that incorrectly passes on the broken framework.

The second fixture guards the dangerous direction: a broken instrument that
claims a mechanism is safe or valid when it is not. Small fixtures, static or
`self.time`-driven assemblies, and mesh assertions make these contracts easy
to isolate.

## Verification principles

1. Establish red evidence through the real failing path, then make the
   smallest change that restores the recorded contract.
2. Run focused tests while iterating, then the relevant Python suite. Run
   browser tests when changing the web application.
3. Keep existing expectations unless they encode the behavior being replaced;
   when they do, update the expectation together with the changed contract.
4. Report what ran, why it failed before the change, and any remaining blind
   spots or environmental failures.

## Runtime prerequisites

- OpenSCAD must be available to render geometry. Headless snapshot work may
  require `xvfb-run -a`.
- Run pytest from the repository root. `SOLID_BUILD_DIR` controls where build
  artifacts are written; the meta-project harness uses its own build location.
- Use an environment that executes the source tree under test. The active
  development environment determines how that environment is provisioned.
