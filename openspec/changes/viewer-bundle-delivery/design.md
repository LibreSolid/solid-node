## Context

`solid_node/packaging.py` registers two setuptools hooks: an `sdist` that always
runs `npm ci && npm run build` in `solid_node/viewers/web/app`, and a `build_py`
that does the same only when `build/index.html` is missing. Both know one
frontend directory. The widget's `dist/solid-widget.js` is produced only by the
CI job or a developer running npm, and `MANIFEST.in` records that fact in a
comment rather than shipping the result.

Two Python modules independently compute the bundle path from their own file
location: `solid_node/core/export.py` (which raises `WidgetBundleMissing` with a
build hint) and `solid_node/sphinx.py` (which warns and leaves the export
incomplete). `sphinx.py` duplicates the constants deliberately, so that a
documentation build does not import the CAD runtime; that constraint survives
this change.

The viewer's API version has one declared source, `solidNodeViewerApi` in
`solid_node/viewers/widget/package.json`, injected into the bundle at build time
(ADR-035). Nothing on the Python side reads it today.

The consumer this change serves reaches the framework only through the `solid`
command (shop finding F-11), and the shop's test suite runs against a fake
`solid` executable. Whatever interface is added must therefore be a CLI surface
that a fake can reproduce in a few lines.

## Goals / Non-Goals

**Goals:**

- Every wheel and source distribution contains a built `solid-widget.js`.
- An installed framework can be asked, from outside Python, where its bundle is
  and which viewer API version it implements.
- One place in the framework knows how to answer that; export and Sphinx use it.

**Non-Goals:**

- Registry publication, renaming published artifacts, TypeScript declarations.
- Any change to the shop, to floor, or to what the viewer does.
- Making the development app consume the shared package (a later cycle).
- Turning packaging into a general frontend-plugin system: this change teaches
  the existing hooks about a second known directory, nothing more.

## Decisions

**One accessor module, `solid_node/viewers/bundle.py`, with no CAD imports.**
It exposes the bundle path, the index page path, whether the bundle is present,
and the declared API version read from the widget's `package.json`. Both
`core/export.py` and `sphinx.py` import it, so the two path computations and the
two "build it with npm" hints converge. It imports only the standard library,
which is what lets `sphinx.py` keep its no-CAD-runtime property; that property is
now enforced by the module's contents rather than by duplication.

Alternative rejected: leave the two constants in place and add a third for the
CLI. Three copies of a path that must agree with `MANIFEST.in` is the same
duplication this sprint exists to remove, one layer down.

**The API version is read from `package.json` at runtime, not baked into a
generated file.** `package.json` is already shipped inside the distribution and
is already the single declared source; a generated `dist/version.json` would add
a second artifact that can disagree with it and that only exists after a build.
Consequence: an installed framework can report the API version even when the
bundle is missing, which is what makes the missing-bundle error specific.

**`solid viewer` reports the bundle as JSON on stdout.** A new duck-typed
command class `Viewer` with `needs_node = False`, matching `New`. It prints one
JSON object with the absolute bundle path and the integer API version. When the
installation has no built bundle it writes the existing build hint to stderr and
exits 1, so a consumer distinguishes "no viewer here" from a parse failure
without matching on prose.

JSON rather than a bare path line: the consumer needs two values and will need
to tolerate a third, and a fake CLI reproduces a JSON literal as easily as a
path. Alternative rejected: separate `--path` and `--api-version` flags, which
makes every consumer invoke the process twice for one answer.

The name `viewer` rather than `widget`: `widget` names the published artifact
(kept by decision D-4), while the command answers a question about *the* viewer
that all three surfaces are converging on. `solid develop`'s web viewer is the
next consumer of exactly this bundle.

**Packaging builds the widget under the same rule as the development app.** The
`sdist` hook builds both; the `build_py` hook builds a frontend only when its
output is missing. `MANIFEST.in` keeps the existing `recursive-include` of the
widget directory — which already carries `dist/solid-widget.js` once it exists —
and its comment is corrected to say the bundle is built during packaging.

**Packaging behavior is proved without running npm.** The cycle's tests drive
the setuptools hooks with the frontend build call replaced by a recorder, and
assert which directories are built and under what condition; a separate test
asserts that a built bundle present in the tree is selected by the distribution's
file rules. Building a real distribution inside a bench would run `npm ci`
against `node_modules` symlinked from the primary checkout, which the framework's
own conventions forbid. Provenance of a real wheel is proved once, outside every
worktree, from the integrated content commit, as the sprint already requires.

## Risks / Trade-offs

- **A packaging regression only shows up at release time.** → The hook tests run
  in the ordinary suite, and the sprint's disposable-checkout wheel inspection
  is the acceptance evidence for this cycle.
- **`npm ci` during an sdist build now runs twice, lengthening release builds.**
  → Accepted; it is the same cost the development app already imposes, and the
  alternative is shipping a distribution that depends on a CI step having run.
- **Reading `package.json` at runtime couples the installed package to a file
  that looks like build metadata.** → It is already shipped and already the
  single declared version source; the accessor is the only reader, so replacing
  it later touches one module.
- **A wheel built from a checkout that already has a stale bundle keeps it**
  (the `build_py` hook builds only when the output is missing). → Pre-existing
  behavior for the development app, unchanged here; the release path builds from
  a clean checkout.
