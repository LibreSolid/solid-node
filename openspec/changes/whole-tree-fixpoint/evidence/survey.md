# Survey: what the catalogue does about the solve order

Read-only survey of the 27 simulation packages in the catalogue,
2026-09-10, in support of the change
`whole-tree-fixpoint`. No project file was modified. Four questions were
asked of every simulation package:

- **A** — a relation whose end only a DESCENDANT's relations solve. None
  exists (it is refused today), so the survey looks for the WORKAROUND:
  a ratio stated twice, a law re-sourced from a root driver with the
  conversion composed in, a chain pulled up a level, a forwarding port.
- **B** — a `simulate()` that READS a coordinate a relation binds, and
  WHO binds it. This is the list the change's timing touches.
- **C** — an author binding guarded by `if ... is None`.
- **D** — a subclass that re-binds or restates what a base's relation
  drives.

The measured framework behaviour the survey is read against is in the
probes beside this file (`probe_order.py`, `probe_unreached.py`,
`probe_stale.py`, `probe_own_read.py`, `probe_subclass.py`,
`probe_interleave.py`, `probe_state_order.py`).

## Totals

| | count |
|---|---|
| simulation packages surveyed | 27 |
| `drives` sentences in them | 676 — 438 in 3DPrintedClocks, 238 in the other 26 |
| **A** — workarounds for the missing tree fixpoint | **14 distinct, in 12 projects** |
| **B** — `simulate()` methods reading a coordinate | **31**, in 19 projects |
| B reads of a RELATION-bound coordinate, every one of them taken from an ANCESTOR's relation (must keep working) | **30**, in 9 projects |
| B reads of a coordinate the READING class's own relation binds — silently unbound today | **2 sites, in 3DPrintedClocks alone** (32 clocks and 5 clocks) |
| **C** — `is None`-guarded bindings | **8**, in 6 projects |
| C guards whose coordinate is an END of a relation of the reading class | **5** |
| **D** — a subclass replacing a base's relation | **0 — it is impossible; 3 projects took a workaround instead** |

## A. The workarounds for the missing tree fixpoint

| project | what it writes today | what it would rather write |
|---|---|---|
| **OpenTorque-Actuator** `reducer.py:56-58` + `actuator.py:32` | `CARRIER_RATIO` stated in two class bodies (a third time in `kinematics.py:6-9`) | `reducer.planet_1.orbit.drives(output_stack.planet_carrier_b.turn)` — the 8:1 stated once, inside the reducer that owns the tooth counts. Its archived proposal names `UnreachedCoordinate` as the reason it cannot. |
| **openflexure-microscope** `microscope.py:68-81`, `kinematics.py:172-195` | four laws sourced from the root `z_motor`, each composing `column_travel(steps)` — the gear ratio and screw pitch re-entered downstream of where `Axis` already states them | `z_axis.actuator.column.travel.drives(body.lower_strut.swing, law=k.strut_swing)` with `strut_swing` being just `z_strut_angle` |
| **openflexure-microscope** `axis.py:36-42` | the thread relation `actuator.leadscrew.turn.drives(actuator.column.travel, ratio=SCREW_PITCH/360)` pushed UP into `Axis`, reaching two levels in, with a comment saying why | `leadscrew.turn.drives(column.travel, ...)` in `Actuator`'s own body |
| **3DPrintedClocks** every one of 32 clocks | `train.centre.turn.drives(motion_works.minute_arbor)` — a second relation whose only job is to make the coordinate readable on `MotionWorks`; plus `seconds_hand.arbor` in 5 clocks (`shared/motion.py:552-554`, `:143-148`) | nothing: the two ports and the 37 forwarding sentences disappear |
| **3DPrintedClocks** clocks 52 and 54 | `calendar_hour_holder` (`shared/laws.py:212-217`) re-derives both motion-works meshes by sampling the built movement, because the day complication hangs off `Movement` and not off `MotionWorks` | `motion_works.hour_holder.turn.drives(day_complication...)`, the sentence the MOON complication already gets because it is a child of `MotionWorks` |
| **open_robot_actuator_hardware** `actuator.py:305` | `gear.spin.drives(pinion.spin)` hoisted into the root; the archived proposal quotes the refusal verbatim | the same sentence in `CenterStack`'s own body |
| **Thor** `art1.py:139-179`, `art4.py:170-219`, `base.py:115-133`, `art3.py:119-134` | four ratios (`ELBOW_RATIO`, `CROWN_RATIO`+`BELT_RATIO`, `BASE_RATIO`, `COLUMN_RATIO`) stated twice in one file, once as a relation and once recomputed in `simulate()`, with a comment naming the wart | read `self.drive`, `self.left`, `self.right` |
| **OpenCycloid** `actuator.py:72-73,152` + `stages.py:16,25,34` | `-1/REDUCTION` in three class bodies; three root sentences restated per standalone stage | `output.carrier.spin.drives(drive.stage_one.spin)` |
| **hangprinter** `winch.py:299-311` vs `:351-356` | `WinchABC` and `WinchD` are two independent classes with the same two relations copied, differing only in a sign | one base stating the pair, `WinchD` REPLACING the ratio |
| **hangprinter** `hangprinter.py:225-230`, `ceiling.py:8-11` | the root hand-binds each `winch.rotor.turn` two levels down, re-sourced from its own drivers; the ceiling's forwarding port was deleted to make it possible | the paid-out length stated in `Ceiling`, which owns `spool_sense()` |
| **Prusa3-vanilla** `zaxis.py:44`, `zscrew.py:18-24` | `ZSide.lift` is a ratio-1 forwarding port and `screw_angle` re-composes `x_lower_z`, the conversion `prusa_i3.py:61` already states | `xaxis.lift.drives(left.screw.spin, law=...)` — the nut rides the beam |
| **Prusa3-vanilla** `extruder.py:63-71` | `hob` composes `BIG_GEAR_PHASE`, a constant of the extruder's own gear pair, into a root law | `e.drives(...extruder.feed)` |
| **snappy-reprap** `snappy_reprap.py:185` | `z.drives(bridge.lift, ratio=z_screw.SCALE)` re-sourced from the driver; `SCALE` also on the `Driver` and in `z_screw.py` | `left_tower.lifter.screw.spin.drives(bridge.lift, ...)` |
| **Metamaquina2** `x_stage.py:93-100`, `y_axis.py:60-68`, `metamaquina2.py:359-360` | the belt rate and pulley phase written twice per class because the shaft must source both ends; `bars.angle`/`couplings.angle` driven from the root two levels down while `z_axis.py:19-24` says the axis is their home | `carriage.travel.drives(belt.clamp, ...)`; `bars.angle.drives(couplings.angle)` in `ZAxis` |
| **poseidon** `pump.py:92`, `poseidon.py:23-25` | the driver→carriage sentence in four class bodies, each reaching two levels down | `position.drives(mechanism.travel)` |
| **abacus** `column.py:84-92` | `Column.simulate()` re-binds its two ports TO THEIR OWN ALREADY-BOUND VALUE so that its own two relations do not raise `UnreachedCoordinate`; the comment says so | nothing — the re-binding line disappears |

Projects with no A-workaround: science-jubilee (3 orthogonal relations),
Internal-Cycloidal-Actuator (one class holds every moving child),
open_manipulator, BCN3D-Moveo, HACKberry, AlbertPro, YouCanBuildDog,
hexapod, openvmp, Inmoov, openarm, pascaline, fender-bender, kossel,
v8-engine — the last four state no relation over the affected coordinates
at all.

## B. Every `simulate()` that reads a coordinate

The change alters WHEN a relation-bound coordinate becomes readable, so
this list is what it is answerable to. Twenty-seven of the thirty-one
reads take a coordinate an ANCESTOR's relation bound, which works today
because a parent solves before a child simulates and which this change
must not disturb.

| project | site | reads | bound by |
|---|---|---|---|
| hexapod | `spiderbot.py:141,146,154,165,167,170,173,219` (8 reads in `Chassis.simulate()`) | `gait_phase`, `stride`, `reach`, `pose.z`, `pose.yaw`, `pose.pitch`, `pose.roll`, `wave` | the ROOT's eight relations |
| Thor | `base.py:126`, `art1.py:160-179`, `art3.py:130`, `art4.py:207-219`, `art56.py:136`, `gripper.py:128` | six joints | the root's relations |
| openvmp | `robot.py:130,134` (`Leg`), `:244` (`Side`), `:359-381` (`Don1`) | `turn`, `foot.knee`, `hip.roll` | the root's relations |
| Prusa i3 | `xaxis.py:208`, `yaxis.py:181`, `extruder.py:257`, `zaxis.py:66` | `carriage.travel`, `carriage.slide`, `bolt.spin`, `lift` | the root's relations |
| Metamaquina2 | `z_bars.py:61`, `z_couplings.py:54` (unguarded) | `angle` | the root's relations, two levels up |
| snappy-reprap | `cable_chain.py:258,266` (unguarded) | `offset` | a parent's / the root's relation |
| openflexure | `actuator.py:69`, `motor_drive.py:59` | `column.travel`, `shaft_pin.turn` | an ancestor's relation |
| YouCanBuildDog | `leg.py:98` (on the BASE class) | `swing` | the root's relation |
| 3DPrintedClocks | `motion.py:334,515,647,704,1015,1042,1052,1091`, `pendulum.py:181-233` | drop, rod turns, seconds | an ancestor's relation or an ancestor's `simulate()` |
| openflexure | `body.py:80-83` | three stage coordinates | the parent's `simulate()` |
| kossel, v8-engine, fender-bender, pascaline, abacus, hangprinter | `tower.py:205`, `cylinder_unit.py:64`, `valve_motion.py:61`, `channel.py:49`, `digit.py:86-89`, `column.py:79`, `winch.py:330,371` | ports and joints | an ancestor's or the reading class's own AUTHOR code |
| **3DPrintedClocks** | **`shared/motion.py:1062` (32 clocks) and `:1070` (5 clocks)** | **`self.arbor(minute_index).turn.value`, `self.arbor(seconds_index).turn.value`** | **the READING class's own relation — unbound at the read, so both assignments write `None` into ports nothing drives.** The only sighting of finding (iii) in the catalogue, and it is the one place the read refusal bites. |

Thor's `art1.py:167-172` and `art4.py:210-212` carry comments saying they
deliberately do NOT read their own derived coordinate for this reason.

## C. Author bindings guarded by `is None`

| project | site | default | the coordinate is |
|---|---|---|---|
| Prusa i3 | `xaxis.py:208-211` | non-zero (`carriage_x(TRAVEL/2)`) | the SOURCE end of `XAxis`'s three relations |
| Prusa i3 | `yaxis.py:181-184` | non-zero | the source end of `YAxis`'s three relations |
| Prusa i3 | `extruder.py:257-260` | non-zero (`BIG_GEAR_PHASE`) | the source end of `Extruder`'s two relations |
| Prusa i3 | `zaxis.py:66-69` | zero | no relation's end |
| hangprinter | `winch.py:329-333`, `:370-374` | zero | the source end of the winch's two relations |
| abacus | `column.py:79-81` | non-zero, time-varying | the source ends of `Column`'s two relations |
| kossel | `tower.py:196-207` | non-zero | no relation's end (a `connect()`) |
| fender-bender | `channel.py:48-52` | non-zero, time-varying | no relation's end |
| v8-engine | `cylinder_unit.py:61`, `valve_motion.py:58` | non-zero, time-varying | no relation (project not migrated) |
| 3DPrintedClocks, Thor | `motion.py:70-72` `value_or_zero`, `placing.py:87-95` `bound` | zero | read fallbacks, not re-application guards |

**Five of these guards read a coordinate that is an END of a relation of
the reading class.** They are the measurement that decides the refusal
moment for finding (iii): a refusal AT THE READ would refuse all five,
none of which is a defect — in each the author binds the coordinate
himself on the next line, and the relation reads it as its source.

**Only Prusa i3's three and hangprinter's two bind INSIDE the guard**,
which is the shape that stops re-applying on the second render
(`probe_stale.py` reproduces it exactly: value `37.5` survives, operations
swept, the body back at rest).

## D. A subclass replacing a base's relation

Zero sightings, because it is impossible. What the catalogue does instead:

- **OpenTorque** `reducer.py:82-88` — `ReducerPosePreview` is deliberately
  a SIBLING of `ReducerPreview` rather than a subclass, "because a
  subclass could not replace the relation"; `ActuatorPosePreview`
  (`actuator.py:47-51`) can override its base only because the base binds
  in `simulate()` instead of stating `input_angle.drives(motor_rotor.spin)`.
- **hangprinter** `winch.py` — `WinchABC` and `WinchD` copied rather than
  inherited.
- **snappy-reprap** — `XAxis` and `YAxis` copy one sentence, the comment
  conceding "The same sentence as XAxis's".
- **3DPrintedClocks** — subclasses that ADD relations work and are used
  (`MoonMotionWorks(MotionWorks)` in three clocks); the same chain is
  inlined rather than subclassed in a fourth, so one repository states one
  mechanism two ways.

A subclass naming an inherited declaration already writes it qualified —
`shared.TrainArbor.turn.drives(...)` (wall clock 28, `clock.py:109-115`),
`MotionWorks.hour_holder.drives(...)` (three clocks) — which is what
`probe_subclass.py` measures: a subclass body cannot see the base's
declarations by their bare names, and needs no new vocabulary to name them.

## What the probes measured

| probe | result |
|---|---|
| `probe_order.py` | the current order of events for a three-level tree, per enumeration entry point: sweep, rest, clear, `simulate()`, SOLVE — per node, parents fully solved before a child's phase begins |
| `probe_unreached.py` | both refused shapes reproduce verbatim: an ancestor sourcing from a descendant-solved coordinate, and a chain stated one level down. Both messages name the ends as `column (Leaf).turn` rather than by path, because the root's solve runs before its children are linked |
| `probe_stale.py` | `value=37.5 operations=['Translation[37.5,0,0]']` on the first run; `value=37.5 operations=[]` on the second and third |
| `probe_own_read.py` | the own derived coordinate reads as `<rotational port left of Art4: None>`, `rotate(None, ...)` appends a `Rotation` that turns nothing, and the same coordinate reads `18.0` after the run. A joint coordinate the class's own relation binds behaves identically — the two are one case |
| `probe_subclass.py` | `declared_relations(Preview)` reports `['drive', 'drive']` and the solve raises `DoublyBound` naming both |
| `probe_interleave.py` | for a root with two subtrees, the walk reads the FIRST subtree's geometry before the SECOND subtree's `simulate()` runs. A binding delivered after the walk has passed a body is a pose nobody sees — which is why a deferred relation cannot be solved lazily |
| `probe_state_order.py` | when the root's phase runs, a child's driver snapshot is `{}` on the first `set_state` and holds the PREVIOUS pose on the second. Any design in which the root's render drives its descendants' phases has to move the snapshot ahead of the enumeration |
