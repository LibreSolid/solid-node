# Evidence — publish the mechanical program

Everything below was measured at this cycle's BASE, `9a05e90` (cycle 3's
implementation commit), in `solid-node/WTs/open-run-simulation`, with
`PYTHONPATH="$PWD"` and `/home/asa/devel/libresolid-studio/.venv/bin/python`.
`import solid_node` resolves to
`.../WTs/open-run-simulation/solid_node/__init__.py`.

This file records the PROPOSAL's probes. The baselines tasks 0.2, 0.3, 3.10
and 5.5 ask for — the full suite's counts, the module's before-and-after
document bytes, the corpus's size — belong to implementation and are
appended there.

## 1. The document a running root publishes today

The acceptance project's committed `_build/viewer.json`
(`projects/Calculators/Pascaline-module/WTs/open-run-simulation`), built
against this worktree:

```
format  solid-node-export
version 4
drivers ['hundreds_entry', 'tens_entry', 'units_entry']
instructions {}                      <- all three are `by=`, so all omitted
animation {'fps': 30, 'frames': 360}  <- no `loop`: running has none
bindings 147
bytes   30529
```

and the tens register's rotation operation resolves, through those
bindings, to the whole carry law evaluated ABSOLUTELY at the DIALS:

```
/Pascaline/tens/drum  ["r", "_b58", [1, 0, 0]]

_b58 = (_b2 + _b57)          # this column's dial, plus what units hands on
  _b2  = (36.0 * tens_entry)
  _b57 = ... _b6 + seven clamp01 segments ...
    _b6 = (65.54 * _b5)      # whole carries already made
      _b5 = floor(_b4)
        _b4 = (_b3 / 360.0)
          _b3 = (_b0 - 114.9)
            _b0 = (36.0 * units_entry)
    _b8 = (_b0 - _b7)        # the window's phase
      _b7 = (360.0 * _b5)
```

Fifty-seven of the document's 147 bindings are that one law, written as a
pose. That is the defect: a consumer moving `units_entry` reads the law AT
the new value instead of integrating ALONG the movement, so the register
snaps back at every carry window, and the `floor` it carries is a jump
nothing subtracts. It is also, exactly, what cycle 1 promised — "a running
root's document is byte-identical to an undeclared root's" — and what this
cycle replaces: under version 5 that operation is the single name
`tens.drum.turn`, and the law moves into `program`, where it is
integrated.

## 2. The compiled program the document does not carry

`Sim(Pascaline(), dt=1/60).program`:

```
<program of Pascaline: 18 coordinates, 9 edges>
inputs       hundreds_entry, tens_entry, units_entry   (dtype None, scale None, unit 'digit')
coordinates  hundreds.carry.turn  hundreds.drum.turn  hundreds.input.turn
             tens.carry.turn      tens.drum.turn      tens.input.turn
             units.carry.turn     units.drum.turn     units.input.turn
intermediates hundreds.stop.angle hundreds.wheel  tens.stop.angle  tens.wheel
              units.stop.angle    units.wheel
spans        ()
identity     62bb22d2e3742320248ab18069ef0d7cfeece0a317527d1efb728a2f33e68b4b
rest bank    every coordinate 0.0 or -0.0
```

Nine edges, all laws, in program order — three of them carrying a jump
plan with one `floor` each:

```
law [units_entry]                  -> [units.drum.turn]      affine (True,)   no plan
law [tens_entry, units.drum.turn]  -> [tens.drum.turn]       affine (False,)  plan
law [units.drum.turn]              -> [units.input.turn]     affine (True,)   no plan
law [hundreds_entry, tens.drum.turn] -> [hundreds.drum.turn] affine (False,)  plan
law [tens.drum.turn]               -> [units.carry.turn]     affine (True,)   no plan
law [tens.drum.turn]               -> [tens.input.turn]      affine (True,)   no plan
law [hundreds.drum.turn]           -> [tens.carry.turn]      affine (True,)   no plan
law [hundreds.drum.turn]           -> [hundreds.carry.turn]  affine (False,)  plan
law [hundreds.drum.turn]           -> [hundreds.input.turn]  affine (True,)   no plan
```

and the candidate table a stop's group is filtered out of:

```
units.drum.turn     <- units_entry
tens.drum.turn      <- tens_entry, units_entry
hundreds.drum.turn  <- hundreds_entry, tens_entry, units_entry
units.wheel, units.stop.angle, ...  <- (empty: no kept edge determines them)
```

Note the six intermediates with EMPTY candidate lists. The relations that
compute them — `drum.turn.drives(wheel)` and `drives(stop.angle)` — drive
plain ports that reach no bank coordinate, so `_reaching_the_bank` drops
them from the program entirely. They are not lost to the document: the
ordinary enumeration computes them from the bank, and under this cycle's
symbolic binding they publish as ordinary pose and `params` expressions
over `<column>.drum.turn`. That is the concrete case behind the design's
"a plain port is an intermediate, not a bank entry".

## 3. The placeholder collision

`evidence/probe_placeholders.py`, over the Pascaline's three carry laws.
With placeholders named as the COMPILER names them — `$j0` per plan —
and sanitized to `_j0`:

```
--- placeholders minted PER PLAN: 24 bindings
   a binding over a placeholder: _b6 = (65.54 * _j0)
   a binding over a placeholder: _b7 = (360.0 * _j0)
   tens.drum.turn:      plan.skeleton => (_b0 + (((((((_b6 + ...
   hundreds.drum.turn:  plan.skeleton => (_b9 + (((((((_b6 + ...
   hundreds.carry.turn: plan.skeleton => (-(((((((_b6 + ...
```

One binding, `_b6`, referenced from all three skeletons — three DIFFERENT
`floor` nodes of three different laws under one published name. A worker
resolving `_b6` would read one branch for all three carries.

Minted document-wide, as design section 1.3 requires:

```
--- placeholders minted DOCUMENT-WIDE: 25 bindings
   a binding over a placeholder: _b6  = (360.0 * _j0)
   a binding over a placeholder: _b14 = (360.0 * _j1)
   a binding over a placeholder: _b23 = (360.0 * _j2)
   tens.drum.turn:      plan.skeleton => (_b0 + ((((((((65.54 * _j0) + ...
   hundreds.drum.turn:  plan.skeleton => (_b8 + ((((((((65.54 * _j1) + ...
   hundreds.carry.turn: plan.skeleton => (-((((((((65.54 * _j2) + ...
   tens.drum.turn:      plan.jump _j0 floor affine=True => _b2
   hundreds.drum.turn:  plan.jump _j1 floor affine=True => _b10
   hundreds.carry.turn: plan.jump _j2 floor affine=True => _b19
```

Three names, three levels, one extra binding. Task 3.5 is the test.

Two further readings off the same run, quoted in design section 2: the
level quantity `_b2` is the law's own `floor` argument published once and
referenced from both the law and its plan; and `units.carry.turn` and
`tens.input.turn` are both `_b16 = (-1 * tens.drum.turn)`, two
coordinates driven by one published expression.

Also verified there: the program's expressions carry NO `let(...)` once
they pass through `bind_expressions`. Read straight off `Edge.graphs`,
`str(graph)` produces
`let(_s0 = (units.drum.turn - 114.9), _s1 = ...) (...)` — producer-local
sharing syntax the export spec forbids in a document — which is why the
program's expressions must go through the document's own binding pass and
not be stringified on their own.

## 4. Two `Sim`s over one tree

`evidence/probe_ownership.py`, over `tests/running_project/machine.Train`:

```
first sim after 30 ticks: {'crank': 20.0, 'first.turn': 40.0, 'lever': 100.0,
                           'second.turn': -60.0, 'slide.travel': 4.0,
                           'spindle': 20.0}
SECOND Sim REFUSED (DoublyBound): Train (Train).spindle is owned by the running
  simulation, and Train would bind it too. A coordinate has exactly one binder,
  and under a running root the run is it: a law stated imperatively in
  simulate() belongs in a relation, ...
```

The message is about `simulate()` and no `simulate()` is involved: the
binder that reaches `bind()` is the RELATION's, during the second `Sim`'s
own rest render, against a slot the FIRST run still owns. Which is why
admitting "a `RunBinder` over a `RunBinder`" would not fix it.

With the release design section 8.1 proposes — drop the root's
`_run_binder`, and clear `_value`, `binder` and `_enum_marker` on every
`run_owned` coordinate slot — applied before construction:

```
second sim after the release: {'crank': 0.0, 'first.turn': 0.0,
                               'lever': 100.0, 'second.turn': -0.0,
                               'slide.travel': 4.0, 'spindle': 0.0}
equals the first run's initial bank: True
```

## 5. A coordinate bound by hand, with no run

Same probe:

```
first.turn at rest 0.0; after set_state(first.turn=99.0) 0.0 -- no error raised
```

`set_state` accepts a joint coordinate id under a running root — cycle 1's
`CoordinateDelivery` opened that door for the run — and with no run to own
the slot, the enumeration `set_state` itself runs immediately recomputes
`first.turn` from the drivers. The requested value is discarded silently.
This is why `solid snapshot --drive` refuses a coordinate id by name
(design section 8.2) rather than accepting one and lying, and it is
recorded as a cycle-1 hole found here: whether `set_state` should refuse a
coordinate entry when no run owns the tree is a question for the pilot,
not a change this cycle makes.

## 6. The consumer, as it stands

Read-only, in `solid-node-viewer/WTs/open-run-simulation`:

- `widget/src/viewer.ts`: `RENDERED_VERSIONS = [1, 2, 3, 4]`, and
  `assertRenderable` refuses any other version by name — "declares document
  version N, which this viewer does not render; it renders versions 1, 2,
  3, 4 ... refusing it rather than rendering part of a machine it does not
  understand." So the refusal the decision asks for is ALREADY the shipped
  behaviour for a version 5 document; this cycle does not have to build it,
  only to make the version mean what it says.
- `widget/src/drivers.ts:268`: `Object.entries(instruction.targets)` runs
  when a button is pressed. A version 4 entry carrying `by` and no
  `targets` would spread to `{}` at load and throw at the click. That is
  the measured reason the relative form stays omitted below version 5.
- `widget/package.json`'s `solidNodeViewerApi` is `7`, and
  `solid_node_viewer/bundle.py::describe()` reports `path`, `index`,
  `apiVersion` and `version` — and no document-version list. Hence
  `documentVersions`, and hence the `[1, 2, 3, 4]` default for every viewer
  released so far.

# Implementation — measured while applying the change

Same worktree, same interpreter. Everything below was produced during
implementation, in the order `tasks.md` asks for it.

## 0.2 The full suite at the base

`9a05e90`, before any production change:

```
2424 passed, 5 skipped, 50 warnings, 1295 subtests passed in 323.02s
```

Exactly cycle 3's recorded 2424 / 5 / 1295. No pre-existing failure.

## 0.3 The acceptance project's document at the base

`projects/Calculators/Pascaline-module/WTs/open-run-simulation`, built
against this worktree with `PYTHONPATH` set to it
(`_build/viewer.json`, the project's own ignored output; nothing written
or committed there):

```
format       solid-node-export
version      4
drivers      ['hundreds_entry', 'tens_entry', 'units_entry']
instructions {}                       <- all three are by=, so all omitted
animation    {'fps': 30, 'frames': 360}
bindings     147
program?     False
bytes        30529
/Pascaline/tens/drum operations
    [['r', '_b58', [1, 0, 0]], ['t', ['0', '44.0', '17.96']]]
```

The tens register's rotation is `_b58`, the whole carry law read
ABSOLUTELY at the dials. That is what this cycle removes.

## 0.4 The three probes the design is written against

(a) and the release, `evidence/probe_ownership.py`:

```
first sim after 30 ticks: {'crank': 20.0, 'first.turn': 40.0, 'lever': 100.0,
                           'second.turn': -60.0, 'slide.travel': 4.0,
                           'spindle': 20.0}
SECOND Sim REFUSED (DoublyBound): Train (Train).spindle is owned by the running
  simulation, and Train would bind it too. ...
second sim after the release: {'crank': 0.0, 'first.turn': 0.0, 'lever': 100.0,
                               'second.turn': -0.0, 'slide.travel': 4.0,
                               'spindle': 0.0}
equals the first run's initial bank: True
```

(b) a coordinate bound by hand with no run, same probe:

```
first.turn at rest 0.0; after set_state(first.turn=99.0) 0.0 -- no error raised
```

(c) the placeholder collision, `evidence/probe_placeholders.py
simulation.pascaline Pascaline` run from the module's worktree against
this one:

```
<program of Pascaline: 18 coordinates, 9 edges>
--- placeholders minted PER PLAN: 24 bindings
   a binding over a placeholder: _b6 = (65.54 * _j0)
   a binding over a placeholder: _b7 = (360.0 * _j0)
   tens.drum.turn:      plan.skeleton => (_b0 + (((((((_b6 + (4.1 * min(max(...
   hundreds.drum.turn:  plan.skeleton => (_b9 + (((((((_b6 + (4.1 * min(max(...
   hundreds.carry.turn: plan.skeleton => (-(((((((_b6 + (4.1 * min(max(...
--- placeholders minted DOCUMENT-WIDE: 25 bindings
   a binding over a placeholder: _b6  = (360.0 * _j0)
   a binding over a placeholder: _b14 = (360.0 * _j1)
   a binding over a placeholder: _b23 = (360.0 * _j2)
   tens.drum.turn:      plan.jump _j0 primitive=floor affine=True => _b2
   hundreds.drum.turn:  plan.jump _j1 primitive=floor affine=True => _b10
   hundreds.carry.turn: plan.jump _j2 primitive=floor affine=True => _b19
```

One binding, `_b6 = (65.54 * _j0)`, serving three different `floor`
nodes under per-plan names; three distinct names and three levels
document-wide. Task 3.5 is the test.

## The base documents the byte-identity guard compares against

Captured at `9a05e90` by a throwaway script that assembles exactly what
`export_node` and `_write_viewer_snapshot_with_inventory` assemble, minus
the two producer-owned keys (the model paths a producer chooses, and
`pieces`), and committed as `tests/base_documents/*.json`:

```
tests/base_documents/driverless.json     version 2, 0 bindings, 4071 bytes
tests/base_documents/drivers.json        version 4, 5 bindings, 3931 bytes
tests/base_documents/flexible.json       version 4, 1 bindings, 2064 bytes
tests/base_documents/sharing.json        version 4, 4 bindings, 2684 bytes
tests/base_documents/looping.json        version 4, 1 bindings, 2473 bytes
tests/base_documents/untimed_train.json  version 4, 1 bindings, 2453 bytes
```

Regenerating them at the base a second time reproduced all six byte for
byte. One field is normalized in the capture and in the test: each node's
`mtime`, which is the SOURCE FILE's modification time and therefore a
property of the checkout rather than of the document schema. Nothing else
is touched.

## The RED run, before any production change

Every test this cycle adds, run on the unchanged tree at `9a05e90`:

```
tests/test_running_document.py  tests/test_running_corpus.py
tests/test_viewer_bundle.py     tests/test_manager_viewer.py
tests/test_browser_renderer.py  tests/test_export.py
tests/test_build_publication.py tests/test_docs_exports.py
tests/test_snapshot.py          tests/test_cli.py
tests/test_running_simulation.py

86 failed, 213 passed, 1 skipped, 65 subtests passed
```

The 86 are this cycle's; the 213 are those files' existing tests, which
stay green throughout. One line of RED per claim:

| Test | RED on the unchanged tree |
| --- | --- |
| `VersionTest::a_running_export_declares_version_five` | `AssertionError: 4 != 5` |
| `VersionTest::a_running_build_declares_version_five` | `AssertionError: 4 != 5` |
| every other `test_running_document.py` test | `ImportError: cannot import name 'compiled_program' from 'solid_node.core.serializer'` — the producer has no compiled program to publish |
| `ReservedClockNameTest::a_driver_qualifying_to_time_is_refused` | `AssertionError: ValueError not raised` |
| `OneTreeOneOwnerTest::a_second_simulation_over_one_tree_starts_fresh` | `DoublyBound: Train (Train).spindle is owned by the running simulation, and Train would bind it too.` |
| `OneTreeOneOwnerTest::a_released_simulation_refuses_to_advance` | same `DoublyBound`, at the second construction |
| `OneTreeOneOwnerTest::two_scenarios_of_one_class_run_off_one_built_node` | same `DoublyBound`, on the second scenario |
| `DocumentVersionsTest` (5 tests) | `AttributeError: module 'solid_node.viewers.bundle' has no attribute 'document_versions'` / `'unreadable_document'` |
| `UnreadableDocumentRefusalTest` (3 tests) | `AttributeError: ... does not have the attribute 'document_versions'` |
| `RunningPublicationWarningTest` (2 tests) | `AttributeError: ... does not have the attribute 'unreadable_document'` |
| `RunningSnapshotWarningTest` (2 tests) | `AttributeError: module 'solid_node.core.builder' has no attribute 'viewer_bundle'` |
| `EmbeddedExportVersionWarningTest` (2 tests) | `AttributeError: ... does not have the attribute 'document_versions'` |
| `SnapshotDriveTest` (8 tests) | `AttributeError: 'Snapshot' object has no attribute 'drives'` / `SnapshotOptionError` does not exist |
| `SnapshotDriveOptionTest` (2 tests) | `solid: error: unrecognized arguments: --drive units_entry=3` |
| `CorpusReplayTest`, `CorpusDocumentTest` | `FileNotFoundError: tests/running-corpus.json` |
| `CoverageGuardTest` (3 tests) | `ModuleNotFoundError: No module named 'tools.generate_running_corpus'` |

Three of the new tests are GREEN at the base on purpose, and are the
guards on the ones beside them:

- `ReservedClockNameTest::the_python_preview_of_an_unbound_clock_is_unchanged`
  — cycle 1's bare `$t` preview, which only the document producer leaves
  behind;
- `DocumentVersionsReportTest::the_report_carries_the_document_versions`
  — `solid viewer` is a pass-through of the report, so a field the viewer
  adds reaches a host through it unchanged;
- `EmbeddedExportVersionWarningTest::the_extension_loads_no_cad_runtime`
  — the Sphinx extension imports nothing of `solid_node` but
  `solid_node.viewers`.

### The behavioural RED, read straight off the unchanged producer

The tests above fail at the seam the cycle introduces; this is the same
absence stated as behaviour, produced by the base producer over the
framework's own fixtures:

```
Train    version 4 keys ['animation', 'bindings', 'drivers', 'format',
                         'instructions', 'root', 'version']
         program key present: False
         instructions {"Park": {"targets": {"crank": 40.0}, "duration": 0.5}}
         first  ops [['r', '_b0', [0, 0, 1]]]          <- _b0 = (crank * 2.0)
         slide  ops [['t', ['(4 + (72 * min(max(((lever - 113.5) / 11.25), 0.0), 1.0)))', ...
Window   version 2 program key present: False
         pinion ops [['r', '(4 + (72 * min(max((((crank - (360 * floor((crank / 360)))) - 113.5) / 11.25), 0.0), 1.0)))', [0, 0, 1]]]
ThreeCarries version 4 bindings 45
         trail  ops [['r', '(4 + (72 * min(max((((_b44 - (360 * floor((_b44 / 360)))) ...
Clocked  version 2
         flag   ops [['r', '(30.0 * $t)', [0, 0, 1]]]
         carries $t: True
Ratchet  version 2 program key present: False
         wheel  ops [['r', 'arbor', [1, 0, 0]]]
```

Every one of those poses is the law read ABSOLUTELY at a driver, `floor`
included, with no program beside it and no coordinate to integrate along.

## 3.10 The acceptance case, end to end

The Pascaline module rebuilt from its own worktree against this one, with
the implementation in place. Its `_build/viewer.json` is the project's
ignored output; nothing was written or committed there, and
`git status --short` in the module's worktree is empty afterwards.

The build said one thing on its way past:

```
WARNING - core.builder - this model needs document version 5, and the
  installed browser viewer renders 1, 2, 3, 4 (solid-node-viewer 0.1.0).
  The document is published anyway: the build, its artifacts, the tests
  and a viewerless watch loop are unaffected by a browser that cannot
  render, and the document's own refusal is the consumer's to make.
```

and wrote:

```
format        solid-node-export
version       5
bytes         32994                (version 4: 30529  -> +2465, +8.1%)
bindings      50                   (version 4: 147    -> -97)
drivers       ['hundreds_entry', 'tens_entry', 'units_entry']
instructions  {"Add hundred": {"by": {"hundreds_entry": 1.0}, "duration": 1.0},
               "Add one":     {"by": {"units_entry": 1.0},    "duration": 1.0},
               "Add ten":     {"by": {"tens_entry": 1.0},     "duration": 1.0}}
                               <- all three published now; the table was EMPTY
program.identity 62bb22d2e3742320248ab18069ef0d7cfeece0a317527d1efb728a2f33e68b4b
                               <- the identity `Sim(Pascaline()).program` reports
program.clock    time
program.coordinates  12
   hundreds_entry      {'kind': 'input', 'initial': 0.0, 'domain': None}
   tens_entry          {'kind': 'input', 'initial': 0.0, 'domain': None}
   units_entry         {'kind': 'input', 'initial': 0.0, 'domain': None}
   hundreds.carry.turn {'kind': 'coordinate', 'initial': -0.0, 'unit': 'deg', 'domain': 'rotational'}
   hundreds.drum.turn  {'kind': 'coordinate', 'initial':  0.0, 'unit': 'deg', 'domain': 'rotational'}
   hundreds.input.turn {'kind': 'coordinate', 'initial': -0.0, 'unit': 'deg', 'domain': 'rotational'}
   tens.carry.turn     {...}   tens.drum.turn  {...}   tens.input.turn  {...}
   units.carry.turn    {...}   units.drum.turn {...}   units.input.turn {...}
program.intermediates ['hundreds.stop.angle', 'hundreds.wheel',
                       'tens.stop.angle', 'tens.wheel',
                       'units.stop.angle', 'units.wheel']
program.spans   {}
program.edges   9
program.limits  {'crossing_tolerance': 1e-12, 'subdivisions': 64,
                 'bisection_rounds': 64, 'max_crossings': 1000,
                 'agreement': 1e-09}
```

Nine joint coordinates, three drivers, six intermediates, nine edges --
the program `evidence.md` section 2 read off `Sim(Pascaline())`, now in
the document, under the same identity digest.

Three carry plans, three DISTINCT placeholders, three distinct levels:

```
tens.drum.turn      _j0 floor level=_b29 affine=True
hundreds.drum.turn  _j1 floor level=_b37 affine=True
hundreds.carry.turn _j2 floor level=_b44 affine=True
```

and the registers' poses are the single names their coordinates carry:

```
/units/drum     [['r', 'units.drum.turn',    [1, 0, 0]], ['t', ['0', '44.0', '17.8']]]
/tens/drum      [['r', 'tens.drum.turn',     [1, 0, 0]], ['t', ['0', '44.0', '17.96']]]
/hundreds/drum  [['r', 'hundreds.drum.turn', [1, 0, 0]], ['t', ['0', '44.0', '18.12']]]
```

against the base's `['r', '_b58', [1, 0, 0]]`, which resolved to the
whole carry law over the dials. The law has moved into `program`, where
it is integrated.

The module's three FLEXIBLE stops follow the bank by the same rule: each
one's molejo `bend` parameter is an expression over `_b1 = (10 * _b0)`,
`_b0 = (-1 * units.drum.turn)` -- a bank id, through the document's own
table. And the whole document carries no `$t` and no `let(`.

The framework's suite pins this SHAPE rather than this project
(`AcceptanceShapeTest` in `tests/test_running_document.py`): the module
lives in another repository and the suite may not depend on it, so the
fixture `ThreeCarries` reproduces the chain -- three carry laws each with
one `floor`, every register posed by its own coordinate, every
coordinate rotational, the candidate table widening column by column --
and the module's own nine coordinates and three plans are this probe.

## 5.5 The conformance corpus

```
tests/running-corpus.json: 13 scenarios over 11 machines
  (CarryLead, Clutch, Ratchet, Remainder, StopAndJump, Swept, Throwing,
   Train, TwoStops, Window, Wrapped), 260 ticks, 170449 bytes
generator runtime 1.28 s
```

| Machine | dt | ticks |
| --- | --- | --- |
| `Train` | 0.05 | 30 |
| `Train` | 0.1 | 20 |
| `Window` | 0.05 | 24 |
| `Remainder` | 0.05 | 24 |
| `Wrapped` | 0.05 | 20 |
| `Throwing` | 0.05 | 20 |
| `Clutch` | 0.05 | 24 |
| `CarryLead` | 0.05 | 24 |
| `CarryLead` | 0.1 | 14 |
| `Ratchet` | 0.05 | 20 |
| `Swept` | 0.01 | 16 |
| `TwoStops` | 0.05 | 12 |
| `StopAndJump` | 0.05 | 12 |

Regenerating it writes the same 170,449 bytes. The coverage guard
accepted it on the first run -- every one of the fifteen features the
export capability lists is exercised -- and the framework replays all 260
ticks exactly for discrete state and within `1e-9` relative for floats.

## Deviations, and the one schema change

### Schema change: an INPUT's `domain` is `null`

Design section 10 item 4 (review-added) says every `program.coordinates`
entry publishes a DOMAIN, "for every input and joint coordinate". The
tree contradicts it: a `Driver` declaration
(`solid_node/simulation/driver.py`) states `default`, `range`, `unit`,
`dtype` and `scale`, and no domain — the domain is a PORT-kind property,
and a driver is not a port. The Pascaline's dials are in `digit`, which
is neither an angle nor a length, so deriving one from the unit would be
a guess the framework makes nowhere else.

So every entry carries the field and an input's value is `null`.
Corrected in `design.md` section 1.1 and section 10 item 4, and in the
`export` delta's paragraph and its "Coordinates publish their domain"
scenario, BEFORE the field was implemented. Recorded as a new open
question (design section 10 item 7): giving `Driver` a declared
`domain=` is strictly additive and is what a jog control for an input
actually wants.

### The web-snapshot document declares 5 and bakes its instant

Design section 6.3 says the web renderer refuses a document the installed
viewer cannot read, "before the browser starts", and the web-snapshot
delta says it compares "the schema version of the document it is about
to stage". For that comparison to be about anything, the staged document
of a running root has to BE a version 5 document, so it declares 5,
carries `program`, and carries the `drivers` table the program's inputs
declare (otherwise the two tables would not name the same ids).

Its poses stay NUMERIC. A capture bakes one instant — that is this
producer's ratified posture, the reason it keyframes deliberately and the
reason `--drive` works under it — so a staged document does NOT satisfy
the export delta's "A committed bank poses the geometry", which binds the
export and build producers. Stated here rather than silently: the
alternative was a staged version 4 document, which would have made the
refusal a false one (an old viewer renders a baked document perfectly),
and the delta's own sentence rules it out.

### A running root the run cannot be constructed over cannot be published

The program a document publishes is the program the run executes, and
`program_of` gets both from the run's own construction — so the published
identity is the run's by construction rather than by two implementations
agreeing. The consequence is that a running root the run REFUSES — one
whose rest render leaves a joint coordinate unbound, the `Sixfree`
shape cycle 1 left as an open question — now fails to build or export,
with the run's own message naming the coordinate. Before this cycle such
a project built a version 4 document happily and could not be simulated
at all. Pinned by
`RefusalTest::test_a_root_the_run_refuses_cannot_be_published`; worth the
pilot's attention, because it is the one behaviour change a project
outside the campaign could meet.

### `time` as a qualified id is refused at a seam no declaration reaches

Design section 4 asks for the refusal at `Sim` construction, and that is
where it is (`Run.__init__`, beside the driver/coordinate clash). No
DECLARATION can reach it today: on the root, the name `time` is taken by
the `Time` declaration itself, and a child-declared driver qualifies to
`<child>.time`. The test therefore patches the driver enumeration to
produce the id, which is exactly what the refusal defends against — an
enumeration that produced it — and says so in its own name.

### A wiring's own stale value is no longer a double binding

`_step_wiring` refused a target that already held a value, whoever had
put it there. Publication restores every coordinate it bound, including
one a wiring had bound, and that value survives the next enumeration's
`clear_solved` because the assembly's own record of having bound it was
replaced during publication. The refusal then fired naming ONE wiring
twice — "first.turn would be bound by the wiring Wired.relay -> turn of
first and by the wiring Wired.relay -> turn of first". A wiring binds its
target once per enumeration (`applied`), so what it finds there can only
be its own earlier binding; `_restated` now recognizes that and the
refusal keeps its meaning for everything else.

### `drive_tree`'s `visit` hook gains the children

Design section 3 puts the coordinate binding inside `visit(node, path)`.
A LEAF holds no snapshot, so the walk never visits one on its own — and a
joint may be declared on a leaf (`tests/running_project/parts.py`'s
`Arbor`). Rather than deriving the structure a second time, which for a
LEGACY render (`_rest` re-runs the author's `render()` when it read a
driver) would hand back a different generation of children, the walk now
passes the children it is about to descend into: `visit(node, path,
children)`. Two in-framework callers, both updated.
