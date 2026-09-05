## Context

Today the viewer is four things inside `solid_node/viewers/`: the TypeScript
widget built to `dist/solid-widget.js`, the Create React App development shell,
the FastAPI `WebViewer` that `solid develop` runs as a `multiprocessing` child,
and the Playwright half of `BrowserRenderer`. Five framework channels consume
the bundle by path: `solid viewer`, `solid export`, the Sphinx directive, the
development server and the web snapshot. solid-node-viewer 0.1.0 now carries
all of it, relicensed, and exposes exactly two things to a framework: the
`solid_node.viewer` entry point, whose one entry resolves to a standard-library
function returning `{path, index, apiVersion, version}`, and the
`solid-node-viewer` console script with `describe`, `serve --build-dir DIR` and
`capture STAGING -o PNG`.

Constraints: the framework must import none of the viewer's code, so the
licence boundary is a process boundary; it must stay fully functional with
OpenSCAD alone; the default snapshot renderer is unchanged; the shop floor
parses `solid viewer`'s JSON and must keep working; PyPI rejects direct-URL
dependencies, so the extra names the package and only CI installs it from Git
until it is published.

## Goals / Non-Goals

**Goals:** a framework with no JavaScript in it; one lookup and one remedy
for the viewer across every channel; `develop` and `snapshot` using the viewer
as a subprocess; honest defaults that follow installation for `develop` and
never for `snapshot`; documentation that says where the viewer comes from.

**Non-Goals:** changing the viewer API, the document schema, or what the
browser shows; making the viewer package depend on solid-node; publishing.

## Decisions

- **Discovery by entry point, not by import name.** `solid_node/viewers/bundle.py`
  loads the `solid_node.viewer` group with `importlib.metadata` and calls the
  entry; `installed()` returns the mapping or `None`. The alternative of
  `importlib.util.find_spec('solid_node_viewer')` binds the framework to the
  package's import name and reads nothing about what it declares. The
  entry-point callable imports only the standard library, so the framework
  runs no viewer code beyond a path lookup.
- **Subprocesses through the interpreter, not PATH.** `develop` and the web
  snapshot run `[sys.executable, '-m', 'solid_node_viewer', ...]`. The viewer
  installed beside the interpreter running `solid` is the one asked, as the
  shop already insists for `solid` itself; a `solid-node-viewer` script
  earlier on PATH from another environment cannot be picked up by accident.
- **`develop` defaults follow installation; `snapshot` defaults do not.**
  A development session's viewer is a workbench choice with nothing
  downstream of it, so "web if you installed it, OpenSCAD otherwise" is what
  a maker means. A snapshot's renderer decides the pixels of images that get
  committed and compared, so `web-snapshot`'s rule stands: OpenSCAD unless
  asked, and never substituted. Explicit `--web` without the viewer fails
  naming the extra; explicit `--openscad` without the binary fails as today.
- **The server restarts as a subprocess, every rebuild, as before.** The reload
  contract relies on the server greeting a reconnecting browser with
  `reload`; keeping the per-cycle restart keeps that behaviour with no state
  to carry. `Popen` replaces `Process`; terminate-and-respawn is unchanged.
  `--debug-web` goes: the documented way to step into the server is to run
  `solid-node-viewer serve --build-dir _build` under a debugger.
- **Staging stays, capture leaves.** `BrowserRenderer` still builds the
  artifacts under the build lock, serializes the photographed node into its
  own staging directory and hard-links the models — everything that knows
  what a node is — and then runs `capture` on the directory with `--imgsize`,
  `--time` and, when a camera was requested, `--view`, `--up`, `--fov` from
  the framework's own `parse_camera`. The viewer never learns OpenSCAD's
  camera syntax; the framework never learns Playwright.
- **One remedy.** `missing_bundle_remedy()` now says
  `pip install "solid-node[viewer]"`. The npm build hint is gone from the
  framework: there is nothing here to build.
- **The parity generator moves, not leaves.** Its numbers are render results
  of this framework; `tools/generate_parity_fixture.py` writes to a path
  given on the command line, and the viewer repository commits the output.
- **Records.** The three viewer-owned specs are removed here with a pointer;
  `viewer-distribution` is rewritten around the lookup; the relocated ADRs
  keep their entries with a *Relocated* note; ADR-067 records the boundary.

## Risks / Trade-offs

- [The viewer package renames the entry point or a command] → both are named
  in `viewer-distribution` on both sides and covered by tests on both sides;
  `solid viewer` fails loudly rather than reporting a stale path.
- [A maker with neither viewer nor OpenSCAD runs `solid develop`] → one
  message names both ways out; the build loop is not started on a viewer that
  cannot open.
- [CI and Read the Docs cannot install the viewer from PyPI yet] → they
  install it from its Git repository until it is published; the extra itself
  stays a plain name.
- [Two processes instead of one] → `develop` already restarted the viewer per
  cycle; the only new failure mode is the viewer command missing, which is
  the same condition as the bundle missing and gets the same remedy.

## Migration Plan

Installations that want the web viewer run `pip install "solid-node[viewer]"`;
those that want the web snapshot add `solid-node-viewer[snapshot]` and
`playwright install chromium`. `solid develop --debug-web` users run the
viewer's `serve` command directly. Hosts that pinned their own copy of
`solid-widget.js` are unaffected: the bundle's names and API are unchanged.
