## Why

The browser viewer shipped inside solid-node under the framework's Apache-2.0
licence, which is why the features worth protecting under copyleft were kept
out of it. The viewer has now been extracted into `solid-node-viewer`, an
AGPL-3.0-only package of its own. solid-node must stop carrying it, install
it as an optional extra, and reach it only across a process boundary, so the
framework stays complete and useful without it and no AGPL code is imported
into an Apache program.

## What Changes

- **BREAKING** Remove the bundled viewer: `solid_node/viewers/widget/`,
  `solid_node/viewers/web/`, the frontend-building setuptools hooks, and the
  npm steps in CI and Read the Docs. Wheels and source distributions of
  solid-node carry no JavaScript.
- Add the `viewer` extra: `pip install "solid-node[viewer]"` installs
  `solid-node-viewer`. The existing `web-snapshot` extra becomes
  `solid-node-viewer[snapshot]`, where Playwright now lives.
- Locate the installed viewer through the `solid_node.viewer` entry point.
  `solid viewer`, `solid export`, the Sphinx directive and the web snapshot
  all resolve the bundle from that one lookup, and all name one remedy when
  it is absent: install the extra.
- **BREAKING** `solid develop` chooses its default viewer by what is
  installed: the web viewer when `solid-node-viewer` is present, the OpenSCAD
  GUI otherwise. `--web` and `--openscad` remain explicit and are never
  substituted; `--web` without the viewer fails naming the extra. The web
  viewer runs as the `solid-node-viewer serve` process on the project's build
  directory rather than as an in-process FastAPI app; `--web-dev` asks that
  process to start the viewer's npm dev server; `--debug-web` is removed,
  since a server in another process cannot be stepped into from this one.
- `solid snapshot --renderer web` keeps staging the photographed node itself
  and hands the staging directory to `solid-node-viewer capture`, passing the
  parsed camera as eye, target, up and field of view. The default renderer
  stays OpenSCAD.
- Move the parity-fixture generator out of the removed widget directory to
  `tools/`, where it keeps producing the numbers the viewer's suite pins.
- Retire the viewer-owned baseline specs (`viewer-package`,
  `viewer-assembly-navigation`, `web-viewer`) from this repository; they live
  on in solid-node-viewer. Mark the relocated ADRs and record the split in a
  new ADR. Update every user-facing page that installs, opens or embeds the
  viewer.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `viewer-distribution`: distributions no longer carry a bundle; the
  framework finds the installed viewer through the entry point and reports
  it; one remedy across channels names the `viewer` extra.
- `cli`: `develop` default follows installation, `--web` requires the
  viewer, `--web-dev` delegates, `--debug-web` removed; `viewer` reports the
  installed package; `snapshot --renderer web` runs the viewer's capture.
- `web-snapshot`: the renderer stages and the viewer photographs; remedies
  name the viewer extras.
- `export`: widget files are copied from the installed viewer; the
  missing-bundle failure names the extra.
- `sphinx-embedding`: widget-less exports are completed from the installed
  viewer package.
- `cli-startup-cost`: `solid viewer` loads the lookup, not the CAD stack and
  not the viewer's own code.
- `openscad-dependency`: `solid develop` needs the binary when it opens the
  OpenSCAD viewer by default, and says how to avoid that.
- `user-documentation`: the viewer pages state that the viewer is a separate
  AGPL package and how it is installed.
- `viewer-package`, `viewer-assembly-navigation`, `web-viewer`: every
  requirement REMOVED from this repository; they are owned by
  solid-node-viewer.

## Impact

`pyproject.toml`, `MANIFEST.in`, `requirements*.txt`, `.github/workflows/`,
`.readthedocs.yaml`; `solid_node/viewers/` (bundle lookup rewritten,
browser renderer reduced to staging plus delegation, widget and web
removed), `solid_node/manager/develop.py`, `manager/snapshot.py`,
`manager/viewer.py`, `core/export.py`, `sphinx.py`, `packaging.py`
(removed); tests for all of those, with the widget, web-viewer and
packaging suites leaving with the code; `docs/` (viewer, embedding, cli,
quickstart, index, status, README, HISTORY, architecture, ADR index, one
new ADR). Downstream: libresolid-studio's setup, bench script and floor
messages follow in its own change; solid-node-viewer 0.1.0 is the paired
release.
