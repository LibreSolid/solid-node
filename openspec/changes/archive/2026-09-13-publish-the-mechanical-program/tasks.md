## 0. Before anything

- [x] 0.1 Work only in `solid-node/WTs/open-run-simulation` (branch
  `open-run-simulation`, base `9a05e90`), with `PYTHONPATH="$PWD"` and the
  workspace venv `/home/asa/devel/libresolid-studio/.venv/bin/python`.
  Confirm `git rev-parse --show-toplevel` prints that worktree and
  `python -c "import solid_node; print(solid_node.__file__)"` prints the
  WORKTREE path. Never write inside
  `/home/asa/devel/libresolid-studio/projects/`, inside
  `/home/asa/devel/libresolid-studio/solid-node-viewer/`, or in the pilot's
  primary `solid-node/` checkout.
- [x] 0.2 Record the FULL SUITE at the base (`python -m pytest -x -q`),
  exact counts, into `evidence.md`, beside cycle 3's recorded 2424 passed /
  5 skipped / 1295 subtests. Any failure here is pre-existing and must be
  shown to be so before task 10.
- [x] 0.3 Record the BASE document of the acceptance project: build
  `projects/Calculators/Pascaline-module/WTs/open-run-simulation` against
  this worktree and paste `viewer.json`'s version, byte count, binding
  count and the tens drum's rotation expression into `evidence.md`. That
  absolute carry reading is what this cycle removes. Output stays in that
  project's ignored `_build/`; nothing is committed there.
- [x] 0.4 Probe and paste the three facts the design is written against:
  (a) two `Sim`s over one `Train` raise `DoublyBound` naming `spindle`;
  (b) `set_state(**{'first.turn': 99.0})` on a `Train` with no `Sim` leaves
  `first.turn` at `0.0` and reports nothing; (c) naming every jump
  placeholder per-plan makes ONE `bindings` entry, `(65.54 * _j0)`, serve
  three different `floor` nodes of the Pascaline's three carry laws.

## 1. The document's version and the running instructions — RED FIRST

- [x] 1.1 `tests/test_running_document.py` (new): a running root's export
  manifest and a running root's built `viewer.json` each declare
  `version: 5` and carry a `program` key. RED.
- [x] 1.2 Same file: an UNTIMED root's and a LOOPING root's documents carry
  no `program` key, declare the version their content needs, and are
  BYTE-IDENTICAL to the document the base produced — compared against a
  document captured from the base commit, not against a re-derivation. RED
  on the second half only after task 3 lands; keep it in the suite from
  here so the byte comparison is the guard on every later task.
- [x] 1.3 Same file: a running root declaring `Instruction(by=...)` beside
  `Instruction(targets=...)` publishes BOTH under version 5, each entry
  carrying exactly one of the two keys, targets qualified. RED.
- [x] 1.4 Same file: an untimed root declaring only relative instructions
  still publishes an EMPTY instructions table. GREEN at the base; it pins
  the version 4 contract against the change.
- [x] 1.5 `RUNNING_DOCUMENT_VERSION = 5` in `serializer.py`;
  `document_version(root, bindings, program=None)` returns it when a
  program is given; `instructions_table(instructions, running=False)`
  publishes `by` when running. Turn 1.1, 1.3 green.

## 2. The bank poses the geometry — RED FIRST

- [x] 2.0b `program.coordinates` entries carry `domain` (`rotational` for
  every Pascaline dial and arbor coordinate; `translational` for a
  `Prismatic` fixture); the document carries no `dt`. RED: no `domain`.
- [x] 2.0c publication over a live run: a `Sim` over `Train` halfway
  through a ten-tick move, `serialize`/export the node in-process, assert
  the document is produced, `sim.state`, `sim.commands` and every slot's
  binder are unchanged, and the next `run()` continues the move. RED:
  `DoublyBound` from `bind()` over a run-owned slot.
- [x] 2.1 `tests/test_running_document.py`: a running `Train`'s document
  publishes the `first` arbor's rotation as the single name
  `first.turn`, not as `(crank * 2.0)`. RED.
- [x] 2.2 Same: the plain port `wheel.turn`'s pose is an expression over a
  bank id; the `Guarded` fixture's coordinate is published too; a `Free`
  joint's placement reads its six coordinate ids. RED.
- [x] 2.3 Same: a running root holding a FLEXIBLE leaf publishes a `params`
  expression over a bank id and an unchanged `spec`. Build the fixture from
  `tests/flexible_project`'s spring under a running root. RED.
- [x] 2.4 Same: after serialization the tree is left as it was found —
  every joint coordinate's value, binder, freshness marks and placement
  restored, and a second render reproduces the same pose. RED.
- [x] 2.5 Same: every free name every operation and `params` expression
  reads, closed over the bindings table, is the clock name, a `drivers`
  key, a `program.coordinates` key or a `program.intermediates` entry. RED.
- [x] 2.6 `symbolic_document`: under a running root, install a `RunBinder`
  as the root's `_run_binder` and bind every joint coordinate of each node
  to `symbol(<qualified id>)` inside the existing `visit(node, path)`
  callback — after that node's drivers, before anything renders — saving
  `(_value, binder, _enum_marker, _bound_by)` per slot; restore them in
  reverse, re-place each joint from what its coordinates then hold, and
  restore `_run_binder`. Turn 2.1–2.5 green.

## 3. The program in the document — RED FIRST

- [x] 3.1 `tests/test_running_document.py`: a running `Train`'s
  `program.coordinates` has exactly the bank's ids with the right `kind`,
  each joint coordinate's `unit` and each `initial` equal to
  `dict(sim.initial.bank)[id]`; `program.intermediates` holds the plain ports and
  nothing else. RED.
- [x] 3.2 Same: every `kind == "input"` id is a key of the document's own
  `drivers` table and every key of that table is such an id — the identity
  the design relies on instead of repeating the declaration.
- [x] 3.3 Same: `program.edges` matches `sim.program.edges` one for one, in
  the SAME order, with matching `kind`, `needs`, `gives`, `description` and
  `stated_by`; a law's `expressions` and `affine` match its graphs and
  `Edge.affine`; a wiring's `factor` and a formula's `factors`, `constant`
  and `slot` match the compiled edge. RED.
- [x] 3.4 Same, on `Window`: the published plan's `jumps` is the graph's
  postorder with `primitive`, `level`, `affine` and a `name` the SKELETON
  reads; on `Remainder`, the `%` node's skeleton carries the subtraction
  rather than the placeholder alone. RED.
- [x] 3.5 Same, the collision 0.4(c) found: a running root carrying THREE
  laws each with one `floor` publishes three DISTINCT placeholder names,
  and no bindings entry is referenced from two skeletons in place of two
  different jump nodes. RED — this is the test that would have caught the
  naive implementation.
- [x] 3.6 Same: `program.spans` on `Ratchet` carries an expression `low`
  and a `null` high; on `Swept` a numeric `high`; `program.sources` equals
  `sim.program.sources`; `program.identity` equals `sim.program.identity`;
  `program.limits` carries the five constants with the values
  `program.py` and `run.py` declare. RED.
- [x] 3.7 Same: no `program` expression carries producer-local sharing
  syntax (`let(`), and a subexpression shared between a law and its own
  plan's level appears once in `bindings`. RED.
- [x] 3.8 Same: a running model published twice is byte-identical, the
  program's ordering and its minted names included. RED.
- [x] 3.9 `Program.published()` in `program.py`: the projection, with
  document-wide placeholder minting (edge order, then postorder) under a
  prefix lengthened while any published id matches `<prefix>\d+`; the
  refusal of a node whose qualified id fell back to a class name.
  `serializer.program_block(program, initial)` assembling the object and
  handing its expression slots to `bind_document`, whose id set becomes
  drivers ∪ coordinates ∪ intermediates. `export.py` and `builder.py`
  compile the program for a running root and publish it. Turn 3.1–3.8
  green.
- [x] 3.10 The ACCEPTANCE case, as a PROBE rather than a suite test — the
  module lives in another repository and the framework's suite may not
  depend on it. Run
  `evidence/probe_placeholders.py simulation.pascaline Pascaline` against
  the module, and build it against this worktree, and assert by inspection:
  its document declares version 5; `program.coordinates` holds its nine
  joint coordinates and three drivers with their rest values; its three
  carry edges each carry one `floor` plan under three DISTINCT
  placeholders; and the tens drum's pose is the single name
  `tens.drum.turn`. Paste the output and the version 4 → version 5 byte
  comparison from 0.3 into `evidence.md`. Nothing is written or committed
  in the project.

## 4. `time` under a running root — RED FIRST

- [x] 4.1 `tests/test_running_document.py`: a running root whose
  `simulate()` reads `self.time` publishes the free name `time`, declares
  `program.clock == "time"`, and NO expression anywhere in the document
  reads `$t`. RED. Add the fixture to `tests/running_project/machine.py`.
- [x] 4.2 `tests/test_running_simulation.py`: an unbound `time` read
  OUTSIDE the document producer still reads bare `$t` — cycle 1's preview,
  unchanged. GREEN at the base; it is the guard on 4.3.
- [x] 4.3 `symbolic_document` binds `time` to `symbol('time')` under a
  running root, through the same internal path, and restores it. Turn 4.1
  green without moving 4.2.
- [x] 4.4 `tests/test_running_simulation.py`: a running root declaring a
  driver whose qualified id is `time` is refused at `Sim` construction
  naming the id and the reservation. RED, then the refusal beside the
  existing driver/coordinate clash check in `Run.__init__`.

## 5. The conformance corpus — RED FIRST

- [x] 5.1 `tests/test_running_corpus.py` (new): load
  `tests/running-corpus.json`, and for each machine construct the `Sim`,
  apply each script entry before the tick it names, advance, and compare
  bank, crossings, stops and command outcomes tick by tick — exact for
  discrete state and list order, `1e-9` relative for floats. RED: no
  fixture yet.
- [x] 5.2 Same file: each machine's REAL published document reproduces the
  fixture's `program`, `drivers`, `instructions` and `bindings`. RED.
- [x] 5.3 Same file: `uncovered_features` is exercised directly — a corpus
  whose machines contain no `%` law is refused naming the uncovered
  feature; one covering everything is accepted. RED.
- [x] 5.4 `tools/generate_running_corpus.py` (new), modelled on
  `tools/generate_parity_fixture.py`: the machine list of design §7.2 plus
  whatever the guard demands, each with its `dt`(s) and script; the
  document's program-bearing keys embedded verbatim; every tick emitted,
  oldest first; `uncovered_features` refusing a thin corpus; output path
  defaulting to `tests/running-corpus.json`. Run it and COMMIT the
  fixture. Turn 5.1–5.3 green.
- [x] 5.5 Record in `evidence.md`: the fixture's byte size, the machine
  count, the tick count per machine, and the generator's runtime.

## 6. Two `Sim`s over one tree — RED FIRST

- [x] 6.1 `tests/test_running_simulation.py`: two `Sim`s constructed over
  ONE `Train` instance — the second after the first has moved its crank
  twenty ticks — both succeed, and the second's bank equals the first's
  `initial.bank`. RED with `DoublyBound`, as 0.4(a) records.
- [x] 6.2 Same file: the FIRST simulation, stepped after the second was
  constructed, refuses naming both and saying its bank no longer describes
  the tree. RED.
- [x] 6.3 Same file: the existing author-binding refusal (`HandBound`) is
  unchanged, and a `ScenarioTest` subclass over a running root runs two
  scenario methods off one built node. RED on the second half.
- [x] 6.4 `Sim.__init__` releases a previous run's ownership before
  `_bind_initial` — pop `_run_binder`, and for every joint coordinate whose
  slot is `run_owned` clear `_value`, `binder` and `_enum_marker`; `Run`
  checks before it binds that the root's `_run_binder` is still its own.
  Turn 6.1–6.3 green.

## 7. The viewer report, the warnings and the capture refusal — RED FIRST

- [x] 7.1 `tests/test_viewer_bundle.py`: `bundle.document_versions()`
  returns the report's `documentVersions`, and `[1, 2, 3, 4]` when the
  field is absent. RED.
- [x] 7.2 `tests/test_manager_viewer.py`: `solid viewer` prints the field
  when the installed viewer reports it. RED.
- [x] 7.3 `tests/test_browser_renderer.py`: the web renderer on a running
  root, with a viewer reporting versions 1–4, fails naming version 5, the
  viewer's versions and its package version, starts no browser, writes no
  image and leaves no staging directory; with a viewer reporting 5 it
  stages and captures as before; an untimed root is unaffected. RED.
- [x] 7.4 `tests/test_export.py` and `tests/test_build_publication.py`: a
  version 5 document published against a viewer that cannot read it emits
  ONE warning naming the three facts, and the document is written anyway.
  RED.
- [x] 7.4b `tests/test_docs_exports.py`: the Sphinx directive embedding a
  committed version 5 export, against a viewer reporting versions 1–4,
  WARNS naming the export, the version and the viewer's versions, and does
  NOT fail the build; it loads no CAD runtime to do so. RED.
- [x] 7.5 Implement: `bundle.document_versions()`; the refusal in
  `viewers/browser.py`; one warning helper called by `export_node`, by
  `_write_viewer_snapshot_with_inventory` and by `sphinx.py` off the
  version of the manifest the directive already opens. Turn 7.1–7.4b
  green.

## 8. `solid snapshot --drive` and `--time` — RED FIRST

- [x] 8.1 `tests/test_snapshot.py` and `tests/test_cli.py`: `--drive
  units_entry=3` poses the named driver and leaves the rest at their
  defaults; a name that is no declared driver fails listing the tree's
  drivers and writes no image; a name that is a joint coordinate of a
  running root is refused by name, quoting the reason 0.4(b) records. RED.
- [x] 8.2 Same: `--time 0.5` on a running root fails naming `--drive`;
  `--time 0.0` (and the default) is accepted and keyframes zero; `--time`
  under a looping and an undeclared root is unchanged. RED.
- [x] 8.3 Implement in `manager/snapshot.py`: the `--drive` option on that
  command alone, applied through `set_state` after `load_node`; the
  coordinate refusal; the `--time` refusal on a running root. Turn 8.1–8.2
  green.

## 9. Docs and the record

- [x] 9.1 `docs/scenarios.rst`: fix the dangling
  ``:doc:`solid_node.math <math>``` to ``:doc:`solid_node.math
  <api-reference>``` (cycle 1's leftover), and add a subsection on what a
  running root publishes and what a viewer must be able to read.
- [x] 9.2 `docs/viewer.rst` and `docs/embedding.rst`: document version 5,
  the directive's warning about an embedded running export,
  the `program` object, the refusal an old viewer makes, and that a browser
  that runs the machine is the viewer package's own next release.
- [x] 9.3 `docs/cli.rst`: `--drive`, and `--time` on a running root.
- [x] 9.4 `docs/api-reference.rst`: `Program.published()` and the corpus
  generator; `docs/changelog.rst`; `docs/architecture.md`'s Export and
  Simulation sections.
- [x] 9.5 `docs/expression-graphs.rst`: the program's expressions share the
  document's bindings table, and placeholders are a published name kind.
- [x] 9.6 ADR-110 (EXPORT) and ADR-111 (EXPORT) as design §11 states them,
  with `docs/adrs/README.md`'s index updated in chronological order; a
  dated amendment on ADR-105 for the ownership repair.
- [x] 9.7 `workflow/open-run-simulation/roadmap.md`: the cycle-4 line —
  what landed, the suite counts, the module's document before and after,
  the corpus's size, what cycle 5 takes verbatim, and the open questions
  carried to the pilot.

## 10. Close

- [x] 10.1 Full suite, exact counts, against 0.2's baseline. Every failure
  explained; no test deleted or weakened to pass.
- [x] 10.2 The UNTIMED byte-identity check of 1.2 passes against documents
  captured from the base commit, for at least: a driverless tree, a
  driver-declaring tree, a flexible tree, a sharing tree and a looping
  root.
- [x] 10.3 `openspec validate publish-the-mechanical-program --strict`
  passes; `evidence.md` carries every probe, count and measurement this
  file asks for.
- [x] 10.4 Nothing is written in `projects/`, in `solid-node-viewer/`, or
  in the primary `solid-node/` checkout; `git status` in this worktree
  shows only this cycle's files.
