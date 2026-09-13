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
