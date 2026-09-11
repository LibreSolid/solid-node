## Context

The cycle is standalone from framework `main` at
`748d6d9450169336d09065b1134c7febb743b4ab`. Construction-time expression
graphs (ADR-101) and backend-neutral materialization (ADR-102) have already
removed OpenSCAD from the framework's motion representation and geometry
broker roles. The remaining `solid develop --openscad` path constructs SCAD,
opens the OpenSCAD GUI, tracks its PID, and also acts as the automatic fallback
when the separately packaged browser viewer is absent.

OpenSCAD was solid-node's first reliable viewer. As the browser viewer gained
tree navigation, independent driver controls, instructions, and continuous
flexible-part evaluation, OpenSCAD became a snapshot-like geometric view of a
machine rather than a faithful interactive machine surface. The pilot has
accepted removing that GUI role for v0.7 and retaining OpenSCAD's modelling,
output, legacy-evaluation, and fixed-pose snapshot roles. The originating
memorandum is `workflow/docs/expression-graphs.md`.

## Goals / Non-Goals

**Goals:**

- Make the browser viewer the only interactive viewer launched by
  `solid develop`.
- Remove `--openscad`, its GUI process/PID lifecycle, and installation-based
  fallback without weakening `--no-web`.
- Give a missing browser viewer one early, actionable `viewer`-extra remedy.
- Preserve every selected OpenSCAD boundary that is not a GUI viewer.
- Explain the historical transition and breaking v0.7 migration in public
  release and user documentation.

**Non-Goals:**

- Removing `OpenScadNode`, `Solid2Node`, SolidPython compatibility, legacy
  SCAD-only adapters, SCAD generation, or OpenSCAD-backed STL production.
- Removing or changing the default of `solid snapshot --renderer openscad`.
- Changing the browser viewer package, its process/API contract, the document
  schema, or its AGPL process boundary.
- Publishing the viewer or framework, or changing the `viewer` and
  `web-snapshot` extras beyond their documentation.

## Decisions

### D1. `develop` has one interactive viewer and one viewerless mode

With no viewer flag, `solid develop` requires the installed browser viewer and
runs its existing `serve --build-dir` process. `--web` remains accepted as an
explicit spelling of the same mode, avoiding an unrelated CLI removal.
`--web-dev` retains its viewer-development behavior. `--no-web` remains the
explicit builder-only mode and requires no viewer package or viewer port.

`--openscad` is removed from the parser rather than retained as a deprecated
no-op or alias. An old invocation therefore fails as an unknown argument; the
v0.7 release note supplies the useful migration to ordinary `solid develop`
with `solid-node[viewer]`. Silently turning `--openscad` into the browser
viewer would contradict what the explicit option requested.

Alternative: keep OpenSCAD only as a fallback. Rejected because installation
would still choose between two materially different machine experiences and
the less faithful path would remain a supported product surface. Alternative:
remove `--web` now that it is the default. Rejected as needless additional
breakage.

### D2. Missing viewer discovery fails before development starts

Every browser-viewer mode resolves the installed bundle before it starts a
viewer or builder. If absent, it exits with the existing
`pip install "solid-node[viewer]"` remedy. `--no-web` bypasses bundle discovery
and continues to support callback-driven or externally hosted development.

This preserves the existing no-substitution rule while making it simpler:
there is no alternate interactive viewer to probe or launch. It also prevents
a watch loop from starting when the requested interactive result cannot be
shown.

### D3. Remove GUI-only code while retaining the snapshot renderer

Delete `OpenScadViewer`, `.openscad.pid`, `run_openscad_viewer`, the GUI
process branch in `Develop`, and their tests. Keep `OpenScadRenderer` in the
OpenSCAD viewer module (renaming or relocating the module is unnecessary
churn) and retain the current snapshot CLI, renderer default, xvfb behavior,
camera/options, and no-silent-substitution contract.

Browser and viewerless development continue to build with `scad_output=False`.
Ordinary `solid build`, direct SCAD APIs, explicit SCAD output, the OpenSCAD
snapshot renderer, and backend-owned OpenSCAD geometry still request SCAD or
the binary where their own contracts require it.

Alternative: remove the snapshot renderer with the GUI. Rejected for this
cycle because a fixed-pose renderer can faithfully consume the numerically
keyframed machine, remains the established agent visual-evidence path, and
offers renderer-specific controls the browser capture does not yet replace.
Its future is independent of interactive viewer fidelity.

### D4. Change current documentation, preserve historical records

The expression-graphs memorandum records that its first two stages completed
and that the viewer assessment ended in this decision. Current architecture,
package comments, README/quickstart, CLI and viewer documentation stop claiming
that OpenSCAD is a viewer or fallback. The unreleased v0.7 changelog explains
that OpenSCAD was the original reliable viewer, why the browser viewer now
replaces it, how to install that viewer, and which OpenSCAD capabilities remain.

Accepted historical ADRs and old release notes remain truthful records of the
system at the time. After implementation evidence confirms the final design,
a new ADR amends ADR-046, ADR-068, and ADR-102 and the architecture synthesis
is rewritten to describe the resulting boundary.

### D5. Prove both the removal and the retained boundary

Red-first CLI tests cover the old flag, default-without-viewer behavior, the
sole browser process, viewerless mode, callback validation, and SCAD-output
selection. Dependency tests prove GUI viewing has left OpenSCAD's requiring
set. Positive snapshot and modelling tests prove that removing the GUI class
did not remove `OpenScadRenderer`, its default, or OpenSCAD/Solid2 artifact
production. Documentation checks and focused searches distinguish current
claims from immutable historical records.

## Risks / Trade-offs

- **A plain framework installation no longer has an interactive viewer** →
  fail before starting development with the exact `viewer`-extra remedy and
  make the v0.7 migration prominent.
- **The viewer package is founded but not yet published** → treat an
  installable viewer distribution as a v0.7 release dependency, validate from
  the intended distribution source, and do not imply this framework cycle
  publishes it.
- **Users may read retained OpenSCAD snapshots as retained viewer support** →
  consistently call one an interactive viewer and the other a fixed-pose
  snapshot renderer.
- **Historical ADRs still describe the former fallback** → preserve them as
  history and add one implemented ADR that clearly amends their current
  consequences.

## Migration Plan

1. Release documentation tells `solid develop --openscad` users to install
   `solid-node[viewer]` and run `solid develop` (or `--web`).
2. Users who only need rebuilding without an interactive surface use
   `solid develop --no-web`; external hosts may retain `--callback`.
3. OpenSCAD model authors keep their existing node classes and tool
   installation. Snapshot users keep `solid snapshot` and
   `--renderer openscad` unchanged.
4. The v0.7 release is not represented as providing an installable interactive
   viewer until the separate viewer distribution is actually available.

## Open Questions

None. Removing the OpenSCAD snapshot renderer, changing snapshot defaults, or
retiring general SCAD output would require separate evidence and decisions.
