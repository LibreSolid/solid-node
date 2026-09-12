# Mechanical execution spikes

Experimental, 2026-09-12. This folder tests the design in `../design.md` and is
not part of the installed framework or its public API.

Implemented proof: generic piecewise-affine mechanical relationships, localized
events, memory at physical detents, simultaneous inputs, checkpoints, program
pause/resume, Python/JavaScript parity and browser rendering. The reduced Curta
fixture uses measured physical phases and profiles from the independent project;
calculator arithmetic is absent from the execution path.

Start with [the findings and limits](../evidence/report.md). Neither this code
nor the schematic screenshots establish that the full Curta can run without
interference. This is not an automatically generated contact model.

## Reproduce

From this `spikes/` directory in the documented development workspace:

```sh
../../../../.venv/bin/python run.py
../../../../.venv/bin/python precision_probe.py
../../../../.venv/bin/python browser_probe.py
```

The first command runs the native tests, exports the JSON programs/corpus,
compares Node against Python, revalidates source contact measurements, measures
model-size scaling and runs 100,000 ticks under Python allocation tracing.
It takes roughly a minute on the measured host. `--skip-memory` omits the
Python endurance measurement for a fast rerun; Node still runs its 100,000 ticks.
Evidence is generated only under `../evidence/`.

The second command contrasts huge absolute-angle origins with phase-local
coordinates. It deliberately reports the baseline float's error rather than
claiming that problem was fixed in the kernel.

The third launches a temporary loopback server, runs actual Chromium worker
parity and a G-code adapter test, inspects rendering behavior and saves two
screenshots. It closes its browser and server when finished. For manual use:

```sh
../../../../.venv/bin/python browser_probe.py --serve --port 8765
```

Open the printed local URL. Run crank, pause, step half a turn, or reset. This
is a deliberately small demonstration UI, not a proposed replacement viewer.
The G-code probe runs in the worker through the harness, not through an editor
on this page. Its parser is intentionally limited to explicit `G90`, `G91` and
`G1 X/Y F` lines, with fixed millimetres and feed in millimetres per minute.

Requirements: the workspace Python environment, Node, installed Python
Playwright/Chromium, the viewer's installed three.js assets, and the Curta
source and measured evidence named in [provenance.json](../evidence/provenance.json).
No dependencies are installed by these scripts. Measured versions: Python
3.12.3, Node 24.11.1, Chromium 151.0.7922.34, three.js r156. The server exposes
only this experimental directory and the installed three.js asset directory,
not the workspace. No viewer code is copied or modified.

## Files

| File | Purpose |
| --- | --- |
| `programs.py` | Builds mechanical JSON fixtures; extracts literal measured profiles without importing the Curta runtime |
| `kernel.py`, `kernel.mjs` | Two generic interpreters of the same piecewise-affine program |
| `test_mechanics.py` | 17 native mechanical, transaction and negative-control tests |
| `conformance.mjs`, `node_probe.mjs`, `run.py` | Shared 20-scenario corpus, reference comparison and evidence collection |
| `worker.mjs` | Browser worker boundary, ordinary numeric programs in / snapshots out |
| `scene.mjs`, `index.html`, `browser_probe.py` | Schematic 3D poses, browser checks and screenshots |
| `gcode.mjs`, `gcode_probe.mjs` | Narrow command adapter, independent program pause and combined checkpoint/rollback proof |
| `scale_probe.mjs`, `precision_probe.py` | Explicit model-size and floating-point limitations |
| `baseline_red.py` | Intentionally failing pre-feature requirements probe; not included in the green suite |

## Experimental program semantics

`q` contains coordinates; `m` contains local mechanical memory. Declared
`inputs` alone can receive rates or finite motions. An active relation says
`velocity[b] = ratio * velocity[a]`, with reverse solving allowed. Disconnected
coordinates hold. Consistent affine loops work; conflicting drives/loops fail.

Events declare directed coordinate crossings, optional periods, predicates,
admissibility checks and atomic writes to named memory. The earliest crossing
subdivides a public tick. Enabled same-instant events settle in rounds reading
one pre-round state. Simultaneous conflicting writes fail. Each directed
surface fires once per arrival. Coordinate stops constrain motion paths and
block the connected driven group while unrelated groups continue.

The baseline kernel uses `1e-8` coordinate tolerance and `1e-12` second tolerance,
with limits of 1,000 subdivisions per tick and 64 settlement rounds. These
are experimental limits, not physical accuracy guarantees or unit-independent
production defaults. Initial mode flags must describe the supplied initial
configuration; no general initial-contact discovery is implemented. Relations
are affine, events have declared coordinate surfaces, and stop limits are
constant during each event interval. Arbitrary nonlinear geometry is outside
this grammar. Unsupported expression operators fail.

Snapshots include run identity, dt/tick, coordinates, relation memory, drives,
motion progress and bounded diagnostics. A failed mechanical tick restores its
pre-tick snapshot. The program adapter extends the transaction to its cursor
and modal state. Completed command records are retired on the next command.
The event trace is a 64-entry ring; event counts have one slot per event ID.
No operation history is added to the expression program.

A blocked finite move preserves actual attained positions and reports blocking;
this spike refuses automatic resume of a blocked move because it does not yet
retain coordinated fractional-tick progress. Ordinary program pause occurs at
tick boundaries and resumes exactly. Cancellation, motion blending, runtime
law compilation, nonlinear loops, a hardened wire schema and full model
initialization are not implemented.
