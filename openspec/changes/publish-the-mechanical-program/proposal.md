## Why

Cycles 1 to 3 built a machine that runs in Python: the run owns the bank,
a law is integrated along the tick, a jump is subtracted and a range is a
physical stop. Nothing of that reaches the browser. The document a running
root publishes today is BYTE-IDENTICAL to an untimed root's — cycle 1 said
so deliberately — which means its pose expressions are the law evaluated
ABSOLUTELY at the driver values. The Pascaline module's own `viewer.json`,
built from this worktree, publishes the whole carry law as the tens
register's ANGLE — fifty-seven of its 147 bindings, resolving to

    _b0 = (36.0 * units_entry)
    _b6 = (65.54 * floor(((_b0 - 114.9) / 360.0)))
    _b58 = ((36.0 * tens_entry) + _b6 + seven clamp01 segments)

A viewer moving `units_entry` would make the tens column SNAP back at every
carry window, because the law would be read AT the new value rather than
integrated ALONG the movement, and the `floor` it carries is a jump nothing
subtracts. An absolute reading is exactly what the whole campaign exists to
replace. The document cannot express the machine, and an old viewer cannot
tell that it cannot.

The campaign's goal is the module simulated in the browser
(`workflow/open-run-simulation/roadmap.md`, "Execution, 2026-09-13"). Cycle
5 writes the browser worker in `solid-node-viewer`; it can only be written
against a published contract, and there is none. This is that contract.

The authority is the pilot's decision of 2026-09-13 in
`workflow/open-run-simulation/design.md`, "a law is integrated, not
declared", item 10: *"The document publishes the compiled program:
coordinate table, inputs, relation expression graphs over coordinate ids,
instructions, initial state, under a version an old viewer refuses. The
browser worker integrates with the same rule over the expression evaluator
the widget already has. Python and browser share a conformance corpus."*
Item 8's relative instruction is published here too — cycle 1 deliberately
omitted it from the table and said which change would publish it. The
cycle split is the roadmap's: this is cycle 4, it depends on cycles 2 and
3, and the viewer is cycle 5.

Three defects the module's own migration exposed are fixed in passing,
because each of them is on the path from here to the browser.

## What Changes

- **A running root's document carries the compiled program.** Beside the
  geometry it already publishes, a root declaring `Time.running()`
  publishes a `program` object: the coordinate table with each bank id's
  kind and rest value, the intermediates the program computes, the edges
  in program order with their expressions and jump plans, the spans, the
  candidate table, the instructions in both forms, the program identity,
  and the tolerances and limits the algorithm is defined by. Every
  expression travels in the document's existing expression language and
  through its existing `bindings` table — no new syntax, no `let(...)`,
  nothing published twice.
- **A committed bank poses the geometry.** Under a running root the
  symbolic serialization binds every JOINT COORDINATE to a token of its
  own qualified id beside every driver, so a joint's placement publishes
  as that coordinate's id and every plain port, derived coordinate and
  flexible `params` expression publishes as an expression over the bank.
  A worker evaluates the document's existing pose expressions from the
  bank it just committed; nothing about how a pose is expressed changes.
- **Document version 5, and an old viewer refuses it by name.** A running
  root's document declares `version: 5` and carries `program`. An untimed
  or looping root's document is unchanged — `version: 2`, `3` or `4` and
  byte-identical to today's. The shipped viewer already refuses a version
  it does not list, naming the version and the ones it renders, which is
  the refusal the decision asks for.
- **The producers say what they can and cannot serve.** The framework asks
  the installed viewer which document versions it renders, through the
  existing `solid_node.viewer` entry point, and: `solid build`,
  `solid develop` and `solid export` publish a version 5 document and WARN
  when the installed viewer cannot read it; the Sphinx directive warns about
  a committed export it embeds under the same rule; and `solid snapshot
  --renderer web` REFUSES by name before starting the browser, because a
  capture is a one-shot that would otherwise fail inside a headless page.
- **`solid snapshot` can pose a running root.** A new `--drive
  NAME=VALUE`, repeatable, binds declared drivers by qualified id before
  the image is taken — the rest pose at those driver values, which is
  admissible by construction. A joint coordinate id is refused by name: a
  coordinate's value is what the run makes of it, and a bank with history
  is the browser's (cycle 5) or a scenario's. `--time` on a running root
  is refused non-zero, naming `--drive`: a running root has no timeline.
- **`time` under a running root leaves the document.** Cycle 1's bare-`$t`
  preview stays exactly as it is for every Python read. In a version 5
  document the clock is published as the program's own name, `time`, which
  a worker binds to elapsed simulation seconds and every consumer without
  a run binds to zero. `$t` therefore never appears in a version 5
  document from this source, and a driver or coordinate whose qualified id
  is `time` is refused by name.
- **A conformance corpus pins the two runtimes to each other.** A
  generator writes a JSON fixture from the framework's own run over eight
  or more small running roots — the coverage guard decides how many —
  each with a command script and its banks, crossings, stops and command
  outcomes tick by tick. The framework's
  suite replays it; the viewer commits a copy and replays it against the
  worker. Exact for discrete state, `1e-9` relative for floats — the run's
  own agreement tolerance.
- **Three fixes.** (a) A second `Sim` over a tree a previous running `Sim`
  bound is no longer refused as doubly bound: constructing a simulation
  RELEASES a previous run's ownership of that tree, and the released run
  refuses to advance rather than fighting the new one. (b) `solid
  snapshot` gains `--drive`, above. (c) `docs/scenarios.rst`'s dangling
  `:doc:`solid_node.math <math>`` reference from cycle 1 is corrected.

What does NOT change: the Python run's semantics — every rule of cycles 1,
2 and 3 about the bank, integration, propagation, jumps, stops, commands,
snapshot and recording; untimed and looping documents, in every byte; the
`drivers` table, the `bindings` contract, the expression language and its
name grammar; the tree shape and operation serialization; the Apache /
AGPL process boundary, across which nothing moves. No viewer code is
written here and none is imported. The browser worker, the running
controls and the non-wrapping clock are cycle 5's, in the viewer's own
repository.

## Capabilities

### New Capabilities

None. The published program is a mode of the existing `export` document
contract, which `build-viewer-artifacts` shares; the corpus is a new
requirement inside `export`, beside the shared-subexpression contract it
extends.

### Modified Capabilities

- `export`: the manifest contract gains version 5 and the `program`
  object, field by field; a new requirement states how a committed bank
  poses the geometry; a new requirement states the conformance corpus and
  its tolerances; the instructions table publishes both forms under
  version 5 and keeps omitting the relative form under version 4.
- `build-viewer-artifacts`: the published `viewer.json` carries the same
  `program` under the same version rule, and the producer warns when the
  installed viewer cannot read what it just wrote.
- `viewer-distribution`: the viewer report carries the document versions
  the installed viewer renders, and a framework channel that needs one
  reads it there; a report without the field means versions 1 to 4.
- `web-snapshot`: the renderer refuses a document the installed viewer
  cannot read, by name, before the browser starts.
- `cli`: `solid snapshot` gains `--drive` and refuses a non-zero `--time`
  on a running root; `solid build`, `solid develop` and `solid export`
  warn on a version 5 document the installed viewer cannot read.
- `sphinx-embedding`: the directive warns, without failing the build, when
  the committed export it embeds declares a version the installed viewer
  cannot read.
- `simulation`: one simulation owns a tree at a time — constructing a new
  one releases the previous run's ownership, and a released run refuses to
  advance; a driver or joint coordinate whose qualified id is `time` is
  refused at construction.

## Impact

- `solid_node/core/serializer.py`: `RUNNING_DOCUMENT_VERSION = 5`;
  `document_version` takes the program; `symbolic_document` binds joint
  coordinates symbolically under a running root and restores them;
  `instructions_table` publishes `by` under version 5; a new
  `program_block` building the published program from `Program`;
  `bind_document` takes the program's expression slots and the full id set.
- `solid_node/simulation/program.py`: `Program.published()` — the
  projection this cycle publishes, including document-wide placeholder
  minting for jump nodes; the refusal of an id that cannot be qualified
  and of the reserved id `time`.
- `solid_node/simulation/sim.py`, `run.py`, `solid_node/motion/ports.py`:
  a simulation releases a previous run's ownership at construction; a run
  whose ownership was taken over refuses to advance.
- `solid_node/core/export.py`, `solid_node/core/builder.py`: compile the
  program for a running root, publish it, warn when the installed viewer
  cannot read the version just written.
- `solid_node/viewers/bundle.py`: `document_versions()` off the viewer
  report, defaulting to `[1, 2, 3, 4]`.
- `solid_node/viewers/browser.py`, `solid_node/manager/snapshot.py`,
  `solid_node/cli.py`: the web-snapshot refusal, `--drive`, the `--time`
  refusal on a running root.
- `solid_node/sphinx.py`: one warning off the version of the manifest the
  directive already opens; no CAD runtime loaded to produce it.
- `tools/generate_running_corpus.py` (new) and `tests/running-corpus.json`
  (new, generated and committed); `tests/running_project/machine.py` gains
  nothing — the corpus reuses the fixtures cycles 1 to 3 already built.
- Tests: a new `tests/test_running_document.py` and
  `tests/test_running_corpus.py`; `tests/test_document_drivers.py`,
  `tests/test_export.py`, `tests/test_snapshot.py`,
  `tests/test_browser_renderer.py`, `tests/test_viewer_bundle.py` and
  `tests/test_manager_viewer.py` gain cases; every other suite unchanged.
- Docs: `docs/viewer.rst`, `docs/embedding.rst`, `docs/scenarios.rst`,
  `docs/cli.rst`, `docs/api-reference.rst`, `docs/changelog.rst`,
  `docs/architecture.md`, and `workflow/open-run-simulation/roadmap.md`'s
  cycle-4 line.
- The viewer repository: NOTHING is written there by this cycle. The
  contract this change publishes is what cycle 5's proposal takes
  verbatim, and the corpus fixture is copied there by that cycle.
