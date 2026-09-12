# Open-run simulation: spike findings

Status: completed bounded investigation, 2026-09-12. Proposed design remains
unratified. This is evidence for framework/viewer changes, not their
implementation or a claim that the complete Curta now runs mechanically.

## Assessment

The stateful execution architecture is viable for the tested mechanical-law
class. One numeric program executes in Python, Node and a real browser worker;
the same kernel handles a disengaging transmission, a ratchet, a reduced Curta
carry chain and independent motor/steering/printer-style motion. There is no
calculator algorithm or numerical result feeding the wheels.

The difficult boundary is not just instruction parsing. Mechanical laws must
export their constraints, event boundaries, admissible transitions and local
memory. The spikes manually author that small numeric program; they do **not**
yet compile existing solid-node declarations into it. Existing absolute pose
formulas cannot automatically reveal their missing mechanical memory.

Proceed with the mechanical program and run-context architecture, subject to
the refinements below. Do not interpret this result as evidence for arbitrary
collision detection, full Curta conversion, real-time performance for every
model, or an independently ratified public API.

## Reproducibility and ownership

The whole investigation is contained in `workflow/open-run-simulation/`, on
framework `main` by the pilot's explicit folder-scoped authorization. Initial
framework commit: `518bed114c94697a58d95e85ad2831c8fcd9f3a3`. Inspected viewer:
`6fb082ba9823fb0839631bd4a3ecbf4a41b33b64`. Curta source:
`60979adbc795785fc51a28a386f85d1a49bfedf7`. No production code, accepted ADR,
baseline spec, viewer code or mechanical-project file was changed.

Commands, prerequisites and interpreter semantics are in
[spikes/README.md](../spikes/README.md). Source checksums, attribution and
measurement comparisons are in [provenance.json](provenance.json). The
generated [corpus.json](corpus.json) pins every tested numeric program and
action sequence; [python-results.json](python-results.json) pins the reference
snapshots. Browser evidence uses actual headless Chromium with SwiftShader,
not a mock DOM. It is not a GPU or cross-browser performance qualification.

## Mechanical evidence

All [17 native tests](native-tests.txt) pass.

| Mechanism / requirement | Observed result | Boundary of the proof |
| --- | --- | --- |
| Coupled pair | Source +10° moves wheel −20°; while open source +10° leaves wheel at −20°; closing aligned teeth causes no jump; driving the wheel solves backward | Ideal affine pair and prescribed sleeve transition, not contact inferred from arbitrary teeth |
| Phase compatibility | Closing at an incompatible phase is refused, with the pre-tick state restored | Phase guard is supplied by the fixture |
| Ratchet | +25° seats at 20°; reverse motion takes up 5° backlash then blocks; lifting permits reverse; lowering seats on the current tooth | Synthetic 10°-pitch ratchet, not the Curta's nonuniform closing tooth profile |
| Swept stop | A rack stops at its admitted limit even when a requested step extends beyond it; an independent motor continues | Analytic unilateral coordinate stop, not a mesh-wide collision sweep |
| Simultaneity | Consistent loops work, conflicting inputs/loops fail, dependent same-instant events settle, conflicting writes roll back | Piecewise-affine constraints and explicit surfaces; no general nonlinear closed-loop solver |
| Curta carry chain | Initial wheel angles `(324°, 324°, 0°)` become `(360°, 360°, 36°)` after 180° crank travel, including two successive carries inside one tick | Three-wheel reduced measured-contact rig, forward operation and only zero/one input row |
| Persistent reset state | First latch resets at crank ≈355.016°; second remains down across 360° and resets at ≈375.016° | Ideal instantaneous over-centre transition |
| Physical input disengagement | Moving the selector to the zero-tooth row prevents wheel movement while the crank continues | Selector travel is normalized 0–1 here; full 6 mm row spacing and nine rows remain project work |
| Concurrency | Motor, cam, steering/rack and coordinated screw drives advance in one run | Kinematics, not combustion, inertia, motor torque or extrusion |
| Pause/replay | A paused motion group retains progress while unrelated drives run; combined checkpoint replay produces identical state | Pause on public tick boundaries; blocked fractional-tick moves require explicit replanning |

### What makes the Curta fixture mechanical

The first transmission receives movement only while a drum tooth is engaged,
between crank 113.5° and 124.75°. Its ratio is 72° of transmission-shaft motion
per 11.25° of drum travel; the bevel relation gives 36° of wheel motion.

A pin on the preceding wheel depresses the following lever. The measured pin
profile crosses the chosen over-centre height, `0.61 × 4.2 mm`, at wheel angle
≈335.393407°. That event retains the lever's lower detent. When the next carry
tooth passes, it can now engage the raised transmission. Its wheel's pin can
trip the next lever in turn. The carry windows are 146.375–157.625° and
166.375–177.625°. A later reset cam crosses a prescribed 1.85 mm lift threshold
and releases each detent. These are local mechanical events, not carry digits
computed from an operand or a register value.

`programs.py` reads the literal `PIN_DROP` and `RESET_LIFT` measurements using
AST extraction. It never imports `simulation.arithmetic`, `simulation.cycle`,
the Curta root or the page's existing logical calculator. Initial wheel angles
are a physical configuration; the interpreter does not know what their marks
mean. The renderer attaches static marks to rotating meshes and does not
calculate an answer to display.

The profile check independently compares the compiled profile to the project's
existing raw gauge records: 50 paired half/full-pin samples and 21 reset-cam
samples. Maximum compression errors are 0.000905336 mm and 0.000955659 mm,
within the recorded 0.001 mm compression bound. Minimum sampled clearance
margin in the pin envelope is 0.049365486 mm. This revalidates published
measurement reduction; it is **not a fresh exact-CAD sweep**, a continuous
clearance guarantee, or proof that the simplified instantaneous latch pose
clears every surrounding part. The original project measurement files and
methods are checksummed in the provenance record.

The source project's model/design attribution is Marcus Wu, CC BY-NC-SA 4.0.
No source CAD assets were copied into this experiment. Reuse of project-derived
geometry or profiles in a distributable framework example needs the appropriate
licensing review; this spike is not such a distribution decision.

### Negative controls and failures that improved the design

[baseline-red.txt](baseline-red.txt) records three real assertion failures
before the running kernel: absolute reposing loses retained position,
endpoint-only contact polling misses a whole tooth passage, and
`current_rate × total_time` rewrites past travel. The first uses the existing
`Affine.forward`; the other two are explicit inadequate implementation
surrogates, not allegations that current public APIs promise these behaviors.

[refinement-red.txt](refinement-red.txt) records three failures in the first
spike implementation: accepting misaligned re-engagement, retaining an obsolete
ratchet detent after release/reverse/lowering, and storing 100 completed
commands. Added phase admission, local reseating and retirement of completed
commands make those tests pass.

The native suite also removes a pin connection, reverses a transmission ratio,
and removes a tooth-enter event. Every deliberately broken mechanism changes
the observed wheel coordinates and is detected. These are separate negative
controls, not passing assertions that assume the model's output is correct.

[program-rollback-red.txt](program-rollback-red.txt) records a failed adapter
transaction test: the mechanical solver rolled back but the program cursor
had advanced. The corrected adapter snapshots/restores both together; the
browser's [G-code evidence](browser-gcode.json) includes that passing check.

## Python/browser execution and scripts

[Node](node-results.json) and [Chromium](browser-results.json) agree with the
Python executor across all 20 shared scenarios. Maximum observed numeric
difference is zero on this corpus; the comparison allows `1e-7` for float
values and requires equal discrete states, event identities/counts, errors,
motion status and checkpoint contents. This result does not establish parity
for untested operators, browsers or future native numerical solvers.

The browser publishes the same final state for one 240-tick batch and the
irregular batches `[1, 17, 3, 79, 2, 91, 47]`. One hundred extra renders do not
advance state. While the worker advances 30,000 ticks, the main-thread 10 ms
heartbeat fires 99 times over about 1.34 seconds: worker execution does not
block the UI in this small-rig test. No page errors were observed.

The [narrow G-code adapter](../spikes/gcode.mjs) runs this program in the browser
worker, through declared motor inputs and the same engine:

```gcode
G90
G1 X10 Y0 F600
G91
G1 X0 Y5 F300
```

At 0.4 seconds it pauses with X at 4 mm and 60 ticks remaining in the first
motion. An independent motor and steering continue. Resume finishes at X=10,
Y=5 mm, and restoring the mid-program snapshot reproduces the complete final
state. An unsupported `G2` command is refused. The small parser uses the
standard distinction between [coordinated G1 movement and G90/G91 distance
modes](https://linuxcnc.org/docs/html/gcode/g-code.html); it deliberately does
not implement the complete language, modal G1 omission, unit switching, arcs,
homing, acceleration, extrusion or printer firmware compatibility.

The program adapter may compute an actuator trajectory because that is what
instructions request. It does not compute downstream mechanical outcomes.
Language state (mode, feed, cursor) is separate from mechanical state but
participates in the same run checkpoint and transaction boundary.

### Inspected pixels

Both [initial](browser-initial.png) and [after two carries](browser-two-carries.png)
screenshots were opened and visually inspected. Static wheel marks under the
pointers change from `0 9 9` to `1 0 0`, with the two carry latches retained in
their lower positions. No result label is substituted for wheel geometry.
An initial capture had illegible glyphs; camera distance and glyph sizing were
corrected and both images recaptured. These are explicitly schematic meshes,
not images of the original Curta assembly or proof of its non-interference.

## Memory, model size and long-running precision

At 2,000 / 20,000 / 100,000 ticks, Python retained traced allocations were
15,728 / 17,652 / 18,560 bytes. The 100,000-tick peak was 56,536 bytes. Node's
post-GC heap was approximately 4.57 / 4.59 / 4.59 MB. Both kept only 64 trace
records and 10 event-counter slots. Snapshot growth was hundreds of bytes,
reflecting numeric formatting and warmed state, not one record per tick.
See [Python](python-memory.json) and [Node](node-results.json) raw measurements.
This is empirical bounded-storage evidence over the measured interval, not a
claim that heap use is numerically constant or that deposited material and
explicit recordings can grow without cost.

Node took about 3.84 seconds for the 100,000-tick small-rig run. Python with
allocation tracing enabled took about 67 seconds; those timings are not a fair
language-speed comparison. Neither includes production geometry rendering.

[Synthetic size measurements](scale-results.json), 250 measured steps after
warmup, demonstrate both compact publication and a performance boundary:

| Coordinates | Relations | Numeric program bytes | Median step | p95 step |
| --- | --- | --- | --- | --- |
| 8 | 7 | 483 | 0.039 ms | 0.107 ms |
| 500 | 499 | 28,493 | 1.160 ms | 1.911 ms |
| 5,000 | 4,999 | 299,244 | 10.987 ms | 15.015 ms |

The fixtures are permanently engaged affine star graphs, without contact
events, geometry or rendering. At 240 ticks/second the budget is 4.167 ms per
tick: 500 coordinates fit this synthetic measurement; 5,000 do not. Production
work must compile sparse topology/execution plans, avoid whole-object cloning
in the hot path, update only affected groups, and benchmark actual exported
mechanisms. The data do not justify promising that the complete Curta fits.

[Large-origin precision stress](precision-results.json) found another real
limitation. With an initial crank winding of one billion turns, the same
half-turn caused about `4.79e-5°` wheel error; at one trillion turns it caused
about `0.00659°`. A local phase with a separately retained integer winding
remained equivalent to the small-origin case. This is a representation
experiment, **not** a trillion-turn endurance run, and the baseline interpreter
still uses ordinary unwrapped floats. Production needs explicit phase/winding
support, including rebasing dependent ratchet/contact memory and versioned
snapshot serialization, rather than eventually losing precision in huge angles.

## Recommended refinements and remaining gates

1. Keep the third user-visible mode, `Time.running()`, but give it a distinct
   run context. Do not modify the old solver by retaining all its bindings.
2. Make event localization and mechanically admissible engagement first-class
   law capabilities. Neither an absolute formula nor a bare boolean gate is
   sufficient. Begin with the validated piecewise-affine class and explicitly
   refuse unsupported laws/loops.
3. Retain bounded phases plus winding for periodic coordinates. This is an
   internal representation; the public clock and total travel still do not loop.
4. Use one run-level transaction/checkpoint containing mechanical state,
   command ownership/trajectory progress and each active instruction adapter's
   state. Distinguish user pause, whole-simulation pause, blocking and failure.
5. Compile the mechanical program once; execute it repeatedly in a worker.
   Separate a trusted Python build from the limited, validated numeric browser
   vocabulary. The prototype schema is not yet a hardened untrusted-document
   boundary, nor the actual solid-node expression compiler.
6. Make recording explicit and bounded; retire completed commands. A per-tick
   full trajectory is incompatible with the default open-run memory objective.
7. Keep Python/JS conformance as a gate. The corpus makes two runtimes plausible;
   it does not settle whether a future single compiled runtime is preferable.
8. Before claiming a real Curta run, migrate its actual independent selectors,
   all transmission/carry banks, reversal/lift/clear mechanisms and source
   geometry bindings. Prove engagement and swept clearance against the actual
   fitted geometry, not only this reduced timing model. Validate geometric
   initialization and retain continuous lever/profile motion around the ideal
   detent transitions.

Still unproven: general nonlinear contact/closed-loop solving; automatic law
compilation/export and full joint-frame parity; robust arbitrary initialization;
fractional blocked-motion recovery; continuous full-machine non-interference;
loads, impacts and spring dynamics; full-machine real-time behavior; hardware
GPU/Firefox/WebKit/mobile behavior; complete G-code compatibility; file-format
security and reload migration. These are explicit scope boundaries and next
validation gates, not hidden fallback logical simulations.
