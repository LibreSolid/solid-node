# ADR-068: Optional Viewer Package Behind a Process Boundary

**Status:** Accepted
**Date:** 2026-09-05
**Change:** `optional-viewer-package`
**Amends:**
- [ADR-020: Static Export Channel with Embeddable, React-Free Viewer Widget](ADR-020-static-export-and-embeddable-viewer-widget.md)
- [ADR-035: Reusable viewer core and declared API version](ADR-035-reusable-viewer-core-and-declared-api.md)
- [ADR-036: Snapshot-served shared viewer shell](../VIEWER-WEB/ADR-036-snapshot-served-shared-viewer-shell.md)
- [ADR-041: Web snapshot renderer](../BUILD/ADR-041-browser-rendered-transparent-snapshots.md)

## Context

The browser viewer — the three.js widget, the React development shell, the
FastAPI development server and the Playwright capture — grew inside this
repository under its Apache-2.0 licence. The maintainer wants the viewer
under a copyleft licence (AGPL-3.0-only) while keeping the framework
Apache-2.0, so that a hosted product built on the viewer must share its
source while the framework stays freely adoptable. The viewer features
worth protecting were being held outside the framework for exactly that
reason, which left the framework's own viewer deliberately incomplete.

An AGPL work imported into an Apache program is, on the FSF's reading, one
combined work. An Apache program that optionally launches an AGPL program
through a documented interface, and is complete and useful without it, is
not. The boundary therefore had to be a process boundary, and the
framework had to stay whole with OpenSCAD alone.

## Decision

The viewer becomes `solid-node-viewer`, an independent repository and PyPI
package licensed AGPL-3.0-only, extracted with its history. solid-node
declares it as the `viewer` extra and reaches it in exactly two ways:

1. **A lookup.** The viewer registers the `solid_node.viewer` entry point,
   whose one entry resolves to a standard-library-only function returning
   the bundle path, the export page, the declared viewer API version and
   the package version. `solid_node/viewers/bundle.py` loads that entry
   and nothing else of the viewer; `solid viewer`, `solid export`, the
   Sphinx directive and the web snapshot all resolve the bundle through it
   and name one remedy when it is absent — install the extra.
2. **Processes.** `solid develop` runs the viewer's `serve --build-dir`
   command on the project's build directory, restarted per rebuild as the
   in-process server was; `solid snapshot --renderer web` stages the
   photographed node itself and runs the viewer's `capture` on the staging
   directory with the resolved camera. Both run as
   `sys.executable -m solid_node_viewer`, so the viewer beside the running
   interpreter is the one used.

`solid develop` chooses its default viewer by installation — the browser
viewer when the package is present, the OpenSCAD GUI otherwise — because a
development session's viewer has nothing downstream of it. `solid snapshot`
keeps OpenSCAD as its default regardless, because a snapshot's renderer
decides the pixels of images that are committed and compared (ADR-041's
no-substitution rule stands). `--debug-web` is removed: a server in another
process cannot be stepped into from this one.

The viewer-owned specs (`viewer-package`, `viewer-assembly-navigation`,
`web-viewer`) and the viewer-owned ADRs (012, 013, 014, 027, 036, 037, 020,
035, 042) are relocated to the viewer repository, the ADRs unchanged and
under their original numbers; the entries below remain in this index marked
*Relocated*. The parity-fixture generator stays here, under `tools/`,
because its numbers are this framework's render results.

## Alternatives considered

- **Import the viewer's server and renderer classes from the AGPL package.**
  Less refactoring; rejected because dynamic import is the combined-work
  case the split exists to avoid, and because it would bind the framework
  to the viewer's Python internals rather than to a command line.
- **Make the viewer package depend on solid-node** (for `get_build_dir`,
  the serializer). Rejected: the server needs only a directory and the
  capture only a staged document, so the dependency would have been
  convenience, and it would have made the viewer unusable by any other
  producer of the document format.
- **Keep the viewer inside the framework and dual-license.** Rejected: one
  repository cannot carry two licences honestly when its wheel is one
  artifact, and the protected features would have stayed outside.
- **Let `snapshot` follow installation too.** Rejected for the reason
  ADR-041 already gave: a default that follows availability is substitution
  by another name, and it would change committed images.

## Consequences

- solid-node's wheels and source distributions contain no JavaScript, and
  building them needs no npm. CI and Read the Docs install the viewer from
  its repository until it is published.
- A plain `pip install solid-node` is complete: OpenSCAD is its viewer and
  its snapshot renderer; `solid export --no-widget` works; everything that
  needs the browser viewer says so.
- The viewer API version and the document schema versions are unchanged,
  so exports, hosts and the shop floor keep working; `solid viewer` gains
  two fields.
- Two packages, one contract: the entry point name, its return shape and
  the three commands are named in both repositories' `viewer-distribution`
  specs and covered by tests on both sides.
- Code cannot flow from the viewer back into the framework without the
  copyright holder relicensing it. While the maintainer is the sole author
  that is a formality; it stops being one the day the viewer accepts an
  outside contribution.

## References

- `openspec/changes/archive/2026-09-05-optional-viewer-package/`
- `solid_node/viewers/bundle.py`, `solid_node/manager/develop.py`,
  `solid_node/viewers/browser.py`
- https://github.com/LibreSolid/solid-node-viewer — `viewer-distribution`
  spec and the relocated ADRs
