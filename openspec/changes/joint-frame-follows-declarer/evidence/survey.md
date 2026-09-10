# Every class-body joint in the catalogue, and what its anchor means

Read-only survey, 2026-09-10, of the twenty-three project repositories
under `/home/asa/devel/libresolid-studio/projects/` that declare a joint.
Nothing was executed and no project file was touched: every row is read
off the source, with the parent's `render()` traced to the placement it
applies to the declaring body.

**Scope correction.** The plan note and the assignment say "the nineteen
projects on the motion layer". The tracker
(`libresolid-studio/docs/motion-general-refactor.md`) has **25 rows**:
20 `done`, 5 `deferred`. Of those 25, **20 declare joints** (the 5
deferred ones are at stage A and declare none). Two further projects
declare joints and are not in the tracker at all: **Thor** and
**3DPrintedClocks**, listed there as "out of scope (already migrated)",
and both are named sightings of this very finding. One more,
**YouCanBuildBiPed**, was built on the motion layer from the start and
was never in the campaign. So the surveyed population is **23 projects
and 249 class-body joint declarations**, not nineteen. The five deferred
projects are surveyed through their reviewed proposals' *intended*
joints, marked `(intended)` below and excluded from the totals.

## The classification

| tag | meaning | what the change does to it |
|---|---|---|
| `RESTATES` | the written `at` equals the translation the parent applies to this body | the `at` is deleted |
| `OWN-ORIGIN-ALREADY` | no `at` written, and the parent applies no translation | nothing |
| `ZERO-BUT-PLACED` | no `at` written, but the parent DOES translate the body | **the meaning changes**: "the parent's origin" becomes "my own origin" |
| `PARENT-FRAME-OFFSET` | a genuine parent-frame point that is not the body's placed origin | rewritten as `M_rest⁻¹ · at`; unchanged where the placement is the identity |
| `PARENT-KNOWLEDGE` | the anchor cannot be stated from the class at all | not migrated; cycle 3 |
| `PARENT-KNOWLEDGE-IN-SUBSTANCE` | the anchor names a line of the ASSEMBLY, and the class can only reach it by inverting its own rest placement by hand and typing the result | statable, but only as a hand-inverted literal; the clean form is cycle 3 |

A `ZERO-BUT-PLACED` row is INERT when the pose cannot move: a
`Prismatic` (whose anchor never enters its placement), or a `Revolute` /
`Orbit` whose placement translation is parallel to its own axis (sliding
the anchor along its own line changes nothing).

**The sixth tag is a sub-tag, and it is the one the first draft of this
survey got wrong.** A `ZERO-BUT-PLACED` row that DOES change a pose was
first reported as "write the anchor the old rule implied", as though the
class could say it. Most of them cannot, in the sense that matters: the
line the anchor names is not a feature of the body at all — it is the
ACTUATOR's axis, the FORK's pivot, the motor SHAFT — and the only way a
class body reaches it is to invert its own placement by hand and type the
number that falls out. That is the parent's knowledge wearing a literal,
and in one case it is a literal the project's own ratified spec forbids
(`Actuators/Internal-Cycloidal-Actuator`: "neither the rest bore centre
nor the journal position may be written as a literal anywhere in the
project"). These rows are counted as `PARENT-KNOWLEDGE-IN-SUBSTANCE`
beside the strict count, and their real migration is cycle 3's
declaration-site keyword, where the parent states the joint in the frame
it already holds.

## Totals

| | count |
|---|---|
| projects surveyed | 23 (+5 deferred, through their proposals) |
| class-body joint declarations | **249** |
| `RESTATES` | **69** |
| `OWN-ORIGIN-ALREADY` | **64** |
| `ZERO-BUT-PLACED` | **47** — of which **35 inert**, **12 change a pose** (10 of those `PARENT-KNOWLEDGE-IN-SUBSTANCE`, 2 a fix) |
| `PARENT-FRAME-OFFSET` | **69** — of which **62 with an identity placement** (value unchanged) |
| `PARENT-KNOWLEDGE`, strictly (the anchor cannot be stated at all) | **0** |
| `PARENT-KNOWLEDGE-IN-SUBSTANCE` (statable only as a hand-inverted literal) | **10** |
| declarations whose rest placement includes a ROTATION | 34 |
| … whose axis is INVARIANT under it (rotation about the joint's own line) | 11 |
| … whose axis must be REWRITTEN as a literal | 18 |
| … whose axis becomes UNSTATEABLE as a literal (one class, opposed placements) | **5** |
| joints today HAND-WRITTEN that the rule newly makes declarable | **≥ 30** |

Per project:

| project | joints | RESTATES | OWN-ORIG | ZERO-BUT-PLACED (pose-changing) | PARENT-FRAME-OFFSET | axis rewritten / unstateable |
|---|---|---|---|---|---|---|
| 3DPrintedClocks | 56 | 14 | 29 | 7 (2) | 6 | 0 / 0 |
| Robots/YouCanBuildDog | 35 | 0 | 1 | 0 | 34 (all identity) | 0 / 0 |
| Lab-Equipment/openflexure-microscope | 19 | 2 | 8 | 9 (1) | 0 | 0 / 1 anchor |
| Robotic-Hands/Inmoov-sim | 18 | 4 | 3 | 8 (**7**) | 3 | 0 / 0 |
| 3D-Printers/Prusa3-vanilla | 12 | 0 | 0 | 3 (0) | 9 | 7 / **2** |
| Actuators/OpenTorque-Actuator | 9 | 1 | 3 | 5 (0) | 0 | 0 / 0 |
| Robotic-Arms/openarm | 9 | 9 | 0 | 0 | 0 | 0 / 0 |
| Vibecoded-demos/pascaline | 8 | 4 | 3 | 1 (0) | 0 | 0 / 0 |
| Robotic-Arms/BCN3D-Moveo | 7 | 7 | 0 | 0 | 0 | 0 / 0 |
| Actuators/Internal-Cycloidal-Actuator | 7 | 0 | 0 | 5 (**2**) | 2 | 0 / 0 |
| 3D-Printers/hangprinter | 7 | 2 | 3 | 0 | 2 | 2 / **2** |
| Robots/openvmp | 7 | 6 | 0 | 0 | 1 | 2 / **1** |
| Robotic-Arms/Thor | 6 | 4 | 1 | 0 | 1 | 3 / 0 |
| Robotic-Arms/open_manipulator | 6 | 6 | 0 | 0 | 0 | 0 / 0 |
| Lab-Equipment/poseidon | 6 | 2 | 1 | 3 (0) | 0 | 0 / 0 |
| Robots-Bipedal/YouCanBuildBiPed | 6 | 0 | 0 | 0 | 6 (all identity) | 0 / 0 |
| Robotic-Hands/HACKberry | 5 | 2 | 0 | 0 | 3 | 2 / 0 |
| Actuators/open_robot_actuator_hardware | 5 | 2 | 3 | 0 | 0 | 1 / 0 |
| 3D-Printers/snappy-reprap | 5 | 0 | 0 | 5 (0) | 0 | 0 / 0 |
| 3D-Printers/Metamaquina2 | 5 | 0 | 2 | 1 (0) | 2 | 1 / 0 |
| Robots/hexapod_spiderbot_model | 4 | 2 | 2 | 0 | 0 | 0 / 0 |
| Robots/AlbertPro | 4 | 2 | 2 | 0 | 0 | 0 / 0 |
| Lab-Equipment/science-jubilee | 3 | 0 | 3 | 0 | 0 | 0 / 0 |
| **total** | **249** | **69** | **64** | **47 (12)** | **69** | **18 / 5** |

The bulk rows are uniform and are cited as groups rather than
transcribed: YouCanBuildDog's 34 leg joints (`simulation/parts.py:56-368`,
`chassis.py:107`) all sit on bodies with an identity rest placement;
3DPrintedClocks' `TurningSpringPart` (12 sites) and `SlidingPulleyPart`
(11 sites) likewise; openarm's nine are one factory
(`simulation/arm.py:30`, `gripper.py:23`) whose `at` callable is in
every case the expression the parent's `translate` uses two lines away.
Every row below is one that is NOT uniform: it deletes something
interesting, changes a pose, or costs something.

---

## 1. What the change deletes

### 1.1 An `at` that restates the parent's translate — 69 sites

The plain form, seven projects that write the placement twice:

| where | joint | `at` | the placement it restates |
|---|---|---|---|
| `Robotic-Arms/BCN3D-Moveo/simulation/moveo.py:35,53,63,73,83` + `parts.py:160,173` | 5 chain joints + 2 finger pivots | `(0, 0, CHAIN_OFFSETS_MM[n])`, `(±22, 0, 62)` | `place_next_link(child, CHAIN_OFFSETS_MM[n])` / `translate((±22, 0, 62))` |
| `Robotic-Arms/open_manipulator/simulation/open_manipulator_x.py:23-82` | 6 | `JOINTS["jointN"].origin_mm` | `translate(JOINTS["jointN"].origin_mm)` — the SAME expression |
| `Robotic-Arms/Thor/simulation/art1.py:104`, `art2.py:120`, `art4.py:134`, `art56.py:110` | 4 | `YAW_ANCHOR`, `ARM_ORIGIN`, `FOREARM_ORIGIN`, `(0,0,WRIST_HEIGHT)` | the parent's `translate(...)` with the same constant |
| `Robots/hexapod_spiderbot_model/simulation/leg.py:213,143` | `Femur.lift`, `Tibia.knee` | `(COXA_LENGTH, 0, FORK_MID)`, `(FEMUR_LENGTH, 0, 0)` | `leg.py:337`, `leg.py:265` — identical vectors, 123 lines apart in one file |
| `Vibecoded-demos/pascaline/pascaline/spindle.py:27`, `accumulator.py:34`, `sautoir.py:28` | 3 | `(0, WHEEL_Y, 0)`, `(0,0,AXLE_Z)`, `(-PIVOT_DX,0,PIVOT_Z)` | `digit.py:78,79,83` — the source comments say "exactly" |
| `Lab-Equipment/poseidon/simulation/hardware.py:61,101` | `ShaftCoupling.turn`, `ThreadedRod.turn` | `(COUPLING_START_X, *DRIVE_AXIS_YZ)` etc. | `pump.py:61,62` — the pump's layout constants live inside bought-hardware classes only for this |
| `Lab-Equipment/openflexure-microscope/.../body/z_links.py:25,52` | two Z struts | `(0, Z_PIVOT_Y, UPPER/LOWER_Z_FLEX_Z)` | `body/body.py:47,48`; the project's proposal says the anchors were "chosen so no centring translation is emitted at all" |
| `Robots/openvmp/simulation/don1/robot.py:77,113,155,179,210,233` | 6 | incl. `dir * END_OFFSET`, `side * VISION_REACH` | `robot.py:92,218,190,219,240,357` |

The sharp form, where restating the placement costs a **callable, a
class attribute or a re-run solver**:

| where | what the `at` is | what deleting it also deletes |
|---|---|---|
| `Vibecoded-demos/pascaline/pascaline/pawl.py:29-39` | `profiles.hinge(next_base, receiving_circle, carry_pin_circle, CARRY_PIN_RADIUS, contact)` evaluated TWICE (once per component) | a five-argument geometric solver run twice more per pawl; `Sautoir.render()` already ran it (`sautoir.py:39-42`) |
| `Robots/AlbertPro/simulation/leg.py:29`, `sourced.py:109` | `lambda node: layout.KNEE_POS[node.LEG]` | the callable, and the reason `LowerLeg*`/`SourcedLower*` (8 subclasses) carry `LEG` at all |
| `Robots/openvmp/simulation/don1/robot.py:155-164` | `CameraArm`: `axis=lambda node: (0, -node._hand, 0)`, `at=lambda node: (node._end*node._hand*CAMERA_OFFSET[0], …)` | both callables, `_end`, `_hand` and the whole `__init__` override — and the **axis collapses to the literal `(1, 0, 0)` for all four corners** |
| `3DPrintedClocks/simulation/shared/motion.py:114-118` | `MotionWorksPart`: `lambda node: motion_works_offset(node.built)+(0.0,) if node.index == 1 else (0,0,0)` | the index-branching lambda; the joint becomes `Revolute(axis=Z, unit='deg')` |
| `3DPrintedClocks/.../motion.py:579,956`; `wall_clock_22/clock.py:59`, `41:183`, `49:102`, `51:114` | `lambda node: assemblies.anchor_bearing(node.built)` / `arbor_bearing(node)` | the lambda; `place_movement`/`place_train_arbor` already translate by the same value |
| `3DPrintedClocks/wall_clock_52/clock.py:178-196`, `54:176-194` | day-complication parts selecting a position by index | four index-selecting lambdas, and the round trip in `parts.py:157-173` that de-translates each part into its own frame so the assembly can re-translate it |
| `3DPrintedClocks/wall_clock_53_grasshopper/parts.py:128`, `wall_clock_54/parts.py:63` | `drawn_position("G"/"P")` | the lambda; `assemblies.Escapement.render` already applies it |
| `Robotic-Arms/openarm/simulation/arm.py:30`, `gripper.py:23` | 9 anchors, all `lambda node: ARM_JOINTS[_side(node.left)][n].origin` / `seated_finger_origin(node.left, n)` | nine anchor callables; the `axis`/`range` callables stay (handedness is real) |
| `Robotic-Hands/HACKberry/simulation/imported/assembly.py:193` | `lambda node: other_closure_anchor(node.occurrence)`, which ADDS `OTHER_FINGER_OCCURRENCES[n]` — the PARENT's placement table | `other_closure_anchor()`, `_translated()` and `THUMB_OPPOSITION_ANCHOR` in `layout.py`; the anchor becomes the raw measured `DIGIT_PIVOTS[...][0]` |
| `tests/joint_project/arm.py:88` (the framework's own fixture) | `at=lambda node: node.built.bearings[node.index]` | the callable that restates `ArborStack.render()`'s `translate([0, PITCH*index, 0])` |

### 1.2 A joint that cannot be declared at all today — ≥ 30 sites

These are hand-written `rotate`/`translate` calls that exist **because**
one class is placed at several points and a class attribute cannot hold
several anchors. Every one becomes `turn = Revolute(axis=…, unit='deg')`
with no `at`.

| where | how many | what stands there today |
|---|---|---|
| `Robotic-Arms/Thor/simulation/{base,art1,art3,art4,art56}.py` | **13** | one hand `rotate(..., [0,0,1])` each, sign from `placing.axis_sign`; the originating sighting. Verified: all thirteen parts are authored concentric about their own origin and all thirteen rotate about their own `+Z`. The sign stays where it already is — in the parent's relation `ratio=` — because `PulleyGT2` and `Art56SmallGear` each appear at BOTH signs and one class body could not say both. |
| `Vibecoded-demos/v8-engine/v8_engine/final_drive/timing_drive.py:52-58` | **4** | the four timing gears (two classes, four placements from `FACE_CENTRES`/`IDLER_CENTERS`/`CAM_CENTERS`, two of them `.repeat(2)` copies for which no per-instance `at` is expressible at all). The project's own note calls this "the eighth sighting". Bonus: because the new joints emit ONE rotation and no centring pair, `test_absolute_body_angles_follow_released_spigots` (`test_timing_drive.py:82-89`), which reads `operations[0].angle`, does not have to change. |
| `3D-Printers/Prusa3-vanilla/simulation/zaxis.py:65-69` | **2** | the two Z screws — the wart's "sharpest form". `ZScrew` is drawn along its own `+Z` from its own origin and placed by a pure `translate([±17, 0, 75])`, so `Revolute(axis=(0,0,1), unit='deg')` with no `at` states both sides. **The wart's claim that no recorded fix reaches it is now wrong; the Prusa proposal itself already conceded the own-origin mode "would".** |
| `3D-Printers/Metamaquina2/metamaquina2/z_axis/z_bars.py:59-61`, `z_couplings.py:52-54` | **4** | Z bars and couplings, `(±offset, -XZStage_offset, BAR_BASE)` per copy. The rule removes ONE of two blockers; the fan-out over `.repeat()` (cycle 1) removes the other. |
| `Lab-Equipment/openflexure-microscope/.../body/body.py:93-97` | **4** | the four flexure legs, `.repeat(2)` copies seated at four polar angles; the leg's own origin IS its lower hinge line, and the two hand `rotate`s are exactly the two `Revolute`s. The proposal asks for it by name, spelling the missing feature `at=OWN_PLACED_ORIGIN`. |
| `Robotic-Hands/Inmoov-sim/Inmoov_sim/forearm.py:250-291` | **3 of 4** | the wrist group. `WristGear.turn` and `WristClevis.turn` become `Revolute(axis=(0,0,1))` with no `at`; `Hand.turn` becomes `Revolute(axis=(1,0,0), at=(0, WRIST_SEAT[1], WRIST_SEAT[2]))` — literally what `_about_axis()` writes by hand — and the conditional `present()` stops contaminating it, because a rest operation no longer enters a joint's frame. The `axle` needs cycle 3 (it is the shared catalogue `Bolt`). |
| `3DPrintedClocks/simulation/shared/pendulum.py:188-190,223-225` | **4** | the bob's rating button and nyloc (placed `rotate(±90,[1,0,0])`, so their own `+Z` maps onto opposite parent directions — the clocks' miniature of `axis_sign`), the bob slide, and clock 48's threaded rod turn+slide |
| `3D-Printers/kossel` (intended) | — | `GT2Pulley.spin`'s `at` callable AND its hand-inverted axis `(0,-1,0)` both collapse to `Revolute(axis=(0,0,1), unit='deg')`; and the rods' per-copy ball station moves out of `simulate()` back into `render()` where it belongs, which the proposal says it could not do because "each of the rod's four joints would need `at` at that copy's own placed origin, which is per-copy metadata a `.repeat(6)` cannot carry" |
| `3D-Printers/fender-bender` (intended) | — | `Channel.tilt`, whose proposal writes the pseudo-constant `at=OWN_PLACED_ORIGIN` and says plainly "there is no way to write it". One of that project's three blockers. |
| `Robots/openvmp/simulation/don1/link.py:110-129` | 8 `spin()` sites | not unblocked (the children are built from `.assy` data — cycle 3), but `spin()` and `axis_of()` exist ONLY to carry a line into and out of a part's own frame, and under this rule they cancel: what one would write is the part's own STEP-frame axis. A two-primitive gap becomes a one-primitive gap. |

### 1.3 A live contradiction inside one project that the rule settles

`3DPrintedClocks` contains two families of clock written for two
different readings of the same declaration:

- clocks 22, 41, 49, 51 write `at=lambda node: arbor_bearing(node)` on a
  leaf that `place_train_arbor` has already translated by that same
  bearing — the inverting reading;
- **clock 48** (`wall_clock_48/clock.py:135-140`) writes NO `at`, with
  this comment: *"This leaf is placed at its bearing by the containing
  fixed-rod arbor, so its own freedom is about its local origin. Using
  the plate-frame bearing here applies that offset twice (invisible on
  arbor zero, whose bearing happens to be the origin) and separates the
  anchor wheel from its independently modelled pallet pins."*

Under today's rule exactly one of the two families is wrong wherever the
bearing is not the origin, and clock 48's anchor arbor is at index 5.
Under the proposed rule clock 48 becomes correct by construction and the
other four delete their `at`. **This is the one place in the catalogue
where the change is expected to MOVE a pose, and to move it towards what
the project says it wants** — see §3.

---

## 2. What the change costs

### 2.1 `ZERO-BUT-PLACED` that changes a pose — 12 sites, 10 of them `PARENT-KNOWLEDGE-IN-SUBSTANCE`

These are joints written today with no `at` on a body the parent
translates off the joint's line. They must ACQUIRE an `at` — the old
rule's anchor, expressed in the body's rest frame — or the machine poses
wrongly and nothing says so.

**And in ten of the twelve the class cannot honestly supply it.** The
line each of them names belongs to the assembly, not to the body: the
actuator's axis, the finger fork's pivot, the motor shaft. Writing it in
the body's rest frame means computing `M_rest⁻¹ · (0,0,0)` by hand and
typing the result — the parent's knowledge, frozen as a literal in the
child, which is the exact shape of the thing cycle 3 exists to remove.
For the Internal Cycloidal Actuator it is worse than inelegant: its
ratified spec forbids that literal outright. So the "what to write"
column below is what the cycle-2 OVERLAY derives mechanically to prove
the poses (see `tasks.md` §7.2); it is NOT what any of these three
projects should commit. Their clean form is
`disk = Disk(orbit=Orbit(axis=(0, 1, 0)))` at the site that already
knows the actuator axis — cycle 3.

| where | joints | what to write |
|---|---|---|
| `Robotic-Hands/Inmoov-sim/Inmoov_sim/fingertip.py:58,73`, `finger.py:56,62,73,80`, `middle_phalanx.py:36` | **7** `Revolute`s (`mcp` on the fingertips, the four fork fasteners, the middle phalanx) | `PARENT-KNOWLEDGE-IN-SUBSTANCE`: the anchor is the FORK's pivot, and the only class-side spelling is `at=(0, -34.99, 1.01)` or `at=(0, -59.97, 2.03)` — the negated placement, typed. Guarded, after the fact, by `test_hand.py:229-237` and the reach assertions at `:65,144` |
| `Actuators/Internal-Cycloidal-Actuator/simulation/actuator/parts.py:129,179` | **2** `Orbit`s (the two cycloidal disks) | `PARENT-KNOWLEDGE-IN-SUBSTANCE`, and the severest: today the missing `at` names the actuator axis; the disks' own origins are **3.9974 mm** and **3.9488 mm** off it, so the disks would be carried round a circle at twice the true 2.000 mm eccentricity at a wrong phase. The rest-frame anchors are `(0.144329, 5.25, -3.994785)` and `(-0.630029, -2.75, -3.898174)` — **literals this project's ratified spec forbids**, so the overlay DERIVES them and the project does not commit them. Their `carries` simplifies in the same edit to the spec's own literal `(0, 0, -2.000)` — but **must stay written**: the default carried point is the body's own origin, which is not the bore. Guarded by `test_machine.py:700-730` |
| `Lab-Equipment/openflexure-microscope/.../motors/small_gear.py:89` | **1** `GearLockScrew.orbit` | the screw ORBITS the motor shaft 3.9 mm away; rest-frame it is `at=(0, ∓3.9, 0)`, and the sign differs between the two `.repeat(2)` copies → a callable of `node.index` (cycle 1). The shaft is the motor's, not the screw's: `PARENT-KNOWLEDGE-IN-SUBSTANCE` |
| `3DPrintedClocks/wall_clock_48/clock.py:140,164` | **2** (`TurningArbor` at index 5, `TurningPalletPin`) | nothing: this is §1.3, the case the change fixes |

The other **35** `ZERO-BUT-PLACED` rows are inert and need no edit: 23
`Prismatic`s (poseidon 3, snappy 3, Prusa 3, openflexure 4, Metamaquina
1, pascaline 1, Inmoov 0, jubilee 0, clocks 0, …) plus 12 `Revolute`s
whose placement translation runs along their own axis (OpenTorque 5, ICA
3, openflexure 4, Inmoov 1 `Pulley.spin`, snappy 2, clocks' 5
`TurningChainPart` whose translation is numerically zero).

### 2.2 An axis that becomes unstateable as a literal — 5 declarations

The mirror image of the anchor win, and the finding the ratified
direction did not have. Where **one class is placed at several sites with
OPPOSED rotations**, today's parent-frame axis states one machine
direction that is right everywhere; the own-frame axis is `Rᵀ · axis` and
is different per site.

| where | placements | own-frame axis per site | what it is today |
|---|---|---|---|
| `3D-Printers/Prusa3-vanilla/simulation/xaxis.py:88` `XGuide.spin` (`.repeat(2)`) | `along_y` / `along_minus_y` (`xaxis.py:184,185`) | `(0,0,1)` / `(0,0,-1)` | one literal `(0,1,0)`; both guides are bound to the same value and must turn the same way — under the new rule they would counter-rotate |
| `3D-Printers/Prusa3-vanilla/simulation/yaxis.py:86` `YGuide.spin` (`.repeat(2)`) | `along_x` / `along_minus_x` (`yaxis.py:160,161`) | `(0,0,1)` / `(0,0,-1)` | as above |
| `3D-Printers/hangprinter/simulation/winch.py:147` `MotorGear.turn` | `MOTOR_GEAR` / `MOTOR_GEAR_MIRRORED` (`winch.py:322`) | `(0,0,1)` / `(0,0,-1)` | `winch.py:57-64` states the choice as a design decision: *"Declaring a leaf's joint about this shared axis, rather than about the leaf's own placed +Z, is what lets one declaration serve both the unmirrored and the mirrored leaf"* |
| `3D-Printers/hangprinter/simulation/winch.py:156` `RollerBearing.spin` | `BELT_ROLLERS[0]` = Rx(+90) / `[1]` = Rx(−90) (`winch.py:323,367`) | `(0,0,-1)` / `(0,0,1)` | one literal; both rollers bound to the same value |
| `Robots/openvmp/simulation/don1/robot.py:113` `Leg.turn` | left Rz(180°) / right Rz(0°) (`robot.py:218`) | `(0,+1,0)` / `(0,-1,0)` | one literal `(0,-1,0)`; `Leg.simulate()` already re-applies the handedness by hand at `robot.py:129-130` |

Every one of the five has a working path with **no new framework
feature**: the whole `axis` argument may already be a callable of the
realized node (ADR-088), and each of these bodies can tell its own site
apart — `MotorGear` from its own declared `mirrored` parameter, `Leg`
from its own `side`, and the three `.repeat()` cases from the copy's
`index`, which **cycle 1 of this campaign puts on the copy and which
lands before this cycle**. The cost is real and is stated as such: a
literal becomes a callable, in five places, and gets its literal back in
cycle 3 where the parent states the joint at the site it places the child.

Eleven further rotated placements are harmless because the rotation is
ABOUT the joint's own line (OpenTorque's three 120°-clocked planets, the
ICA's five, snappy's pinion, openflexure's four): the axis is invariant
and one declaration keeps serving every site. Eighteen more need a
one-time literal rewrite, computed in the per-project rows: Thor's
`Art2.shoulder` `(0,1,0)→(0,0,1)`, `Art3.elbow` `(0,0,1)→(0,1,0)`,
`Art4.yaw` `(0,0,-1)→(0,0,1)` (a sign flip), `Art56.wrist`
`(0,1,0)→(1,0,0)`; HACKberry's two thumb phalanges `(1,0,0)→(0,0,1)`;
Prusa's `SmallGear`/`BigGear` `(0,-1,0)→(0,0,1)` and `HobbedBolt`
`(0,-1,0)→(0,0,-1)`, `XPulley` `(0,1,0)→(0,0,-1)`, `XIdler`
`(0,1,0)→(0,0,1)`, `YPulley` `(1,0,0)→(0,0,-1)`, `YIdler`
`(1,0,0)→(0,0,1)`; Metamaquina's `YPulley` `(-1,0,0)→(0,0,1)`;
open_robot's `CenterPinion` `(0,0,1)→(0,1,0)`; OpenVMP's `Wheel.spin`
`(0,-1,0)→(0,0,1)` (which its own test already states own-frame,
`test_robot.py:345`).

### 2.3 An anchor that has to be recomputed — 7 sites

`PARENT-FRAME-OFFSET` rows whose placement is not the identity. All
seven rewrite cleanly and the new number is usually the one the project
would rather have written:

| where | today | own-frame |
|---|---|---|
| `Robotic-Arms/Thor/simulation/art3.py:91` `Art3.elbow` | `(0, 160, 68)` | `(0, 0, 81.5)` — `ELBOW_PIVOT` in Thor's own `art2.py` |
| `Actuators/Internal-Cycloidal-Actuator/.../parts.py:119,169` `spin` ×2 | `DISK_n_BORE_CENTRE`, derived by `_bore_centre()` from the placement | `BORE_AXIS_POINT = (0, 0, -2.000)` — the project's own spec literal; `_rotate_y`, `_bore_centre` and the two derived constants become unnecessary |
| `Robots/openvmp/.../robot.py:89` `Foot.knee` | `KNEE_SHAFT = (0, -316.4, 108.8)` | `(0, -8.906, 7.276)` — the blueprint's 11.5 mm knee error, carried through Rx(−39°) |
| `Robotic-Hands/Inmoov-sim/.../fingertip.py:57`, `finger.py:72,79` | `PROXIMAL_JOINT` | `(0, -24.98, 1.02)` = `−MIDDLE_JOINT` |
| `Robotic-Hands/HACKberry/.../assembly.py:567` `RTV7.opposition` | `THUMB_OPPOSITION_ANCHOR` | `(-32.4536, -101.7362, -1.1549)` = `DIGIT_PIVOTS['thumb_opposition'][0]`, the raw measurement |

The remaining 62 `PARENT-FRAME-OFFSET` rows sit on bodies with an
IDENTITY rest placement — YouCanBuildDog's 34, YouCanBuildBiPed's 6,
3DPrintedClocks' 6, HACKberry's `RIV7`, and the rest — so the parent's
frame IS the body's own frame and the written value is already right.
**Nothing changes for them, in either direction.** They are the reason
the change is a smaller edit than the totals suggest.

### 2.4 Tests that read a joint's arguments

Only one test in the catalogue asserts `.axis` and `.at` off a realized
joint: `Robots-Bipedal/YouCanBuildBiPed/simulation/test_assembly.py:103-111`,
`test_motion_uses_current_revolute_joints_at_measured_pivots`. All six of
that project's bodies have an identity rest placement, so all five
assertions stay true. It is nonetheless the tripwire: run it.

Two more assert a RESOLVED anchor geometrically and would fail on a
mistake in §2.1: `Robots/AlbertPro/simulation/test_leg.py:109-124`
(the knee, to 0.001 mm) and
`Actuators/Internal-Cycloidal-Actuator/.../test_machine.py:700-730`
(the disks at 2.000 mm). `3DPrintedClocks/simulation/shared/testing.py:235-251`
(`test_rod_turns_use_the_rods_geometric_centreline`, "a parallel but
offset axis makes the rod orbit instead of spin") is the only test in the
catalogue written directly against the `ZERO-BUT-PLACED` failure mode,
and it guards the pendulum rod alone.

---

## 3. What the survey says about the rule

**The catalogue splits cleanly, and the split is the ontology.**

- A joint whose line runs THROUGH the body it moves — a wheel on its own
  bearing, a gear on its own axle, a pinion, a pulley, a screw, a link
  hinged at its own origin — wants the body's frame. That is 69
  `RESTATES`, 64 `OWN-ORIGIN-ALREADY` and the ≥ 30 joints that cannot be
  declared at all today: **133 of 249 declarations plus ~30 hand-written
  rotations**, every one of them simpler or newly possible.
- A joint whose line runs SOMEWHERE ELSE — a body carried round a remote
  axis, or several copies of one class sharing one machine line — wants
  the parent's frame. That is the 12 pose-changing `ZERO-BUT-PLACED`
  rows and the 5 unstateable axes: **17 declarations**, every one of them
  worse.

Ten to one, by count, and by kind the first family is the one the
framework exists to make easy. But the second family is real and
concentrated — the ten anchors sit in three projects (the Internal
Cycloidal Actuator, InMoov, openflexure) and the five axes in three more
(Prusa, hangprinter, OpenVMP) — and the change does not
make it impossible — it makes it a hand-inverted literal, or a callable,
until cycle 3 gives it the declaration site, which is where a statement
about a body's placement belongs.

**Two things in the evidence contradict the ratified direction and are
recorded rather than smoothed over.**

*First, the count of anchors that need the parent's frame is 0 only by
the letter of the tags.* The plan note's §3.2 says the survey should look
for "a class-declared `at` or `axis` that GENUINELY needs the parent's
frame (as opposed to restating the parent's placement)", and expects the
answer to be "none, or cycle 3's". Strictly, `PARENT-KNOWLEDGE` is **0**
across 249 shipped declarations: there is no anchor a class cannot write
down at all. In substance it is **10** — the Internal Cycloidal
Actuator's two disk `Orbit`s, InMoov's seven finger `Revolute`s and
openflexure's `GearLockScrew.orbit` — each of which can be written only
by inverting the body's own placement by hand and typing the result. That
is the parent's knowledge frozen into the child, it is the shape cycle 3
exists to remove, and for the Internal Cycloidal Actuator the required
literal is one its ratified spec forbids. Reporting those ten as "write
this anchor" would have made the change look cheaper than it is.

*Second, the note does not anticipate an AXIS case at all*, and **five
axes genuinely need the parent's frame** (§2.2). Two of the three
projects that hold them documented the choice in prose as a deliberate
use of the parent frame (`hangprinter/simulation/winch.py:57-64`,
`Prusa3-vanilla/.../proposal.md:96-101`). They have two bridges, neither
of them new machinery: a callable of the body's own parameter or of the
copy's `index`, or — better where the sign belongs to the site — the
PARENT supplying it in the relation, which is what Thor already does with
`ratio=`. Both belong in the ADR as the honest cost of the change.

**A second thing worth the pilot's decision.** The change is expected to
produce a **non-zero pose deviation in 3DPrintedClocks wall clock 48**,
because that clock is written against the new reading and is (by its own
comment) wrong under the old one. Every other project must compare at
maximum deviation 0 after its rewrite. Clock 48's deviation is the fix,
not a regression — but it is the one row where "nothing else moved"
cannot be the acceptance, and the project's own tests, not the pose
comparison, have to say whether the new pose is right.

## 4. The deferred five, through their proposals

Not counted in the totals; recorded because three of them are blocked on
this finding and two are made worse by it.

| project | intended joints | what the rule does |
|---|---|---|
| `Vibecoded-demos/v8-engine` | 14 (9 statable, 5 blocked) | **unblocks the four timing gears outright** (PARENT-KNOWLEDGE → no `at`), one `RESTATES` deleted (`Camshaft`), no pose change anywhere. The connecting rods stay blocked on the fan-out, not on this. |
| `3D-Printers/kossel` | 9 (33 freedoms) | deletes `CarriageAssembly.travel`'s `at`, deletes `GT2Pulley`'s `at` callable AND rewrites its hand-inverted axis to `(0,0,1)`, and lets the six rods' per-copy ball station move from `simulate()` into `render()`. Still deferred on the multi-source delta law (cycle 5). |
| `3D-Printers/fender-bender` | 5 (2 ready, 3 blocked) | fixes one of three blockers — `Channel.tilt`'s per-copy own origin, which its proposal spells `at=OWN_PLACED_ORIGIN`. Still deferred on composition order (done) and fan-out (cycle 1). |
| `Vibecoded-demos/abacus` | 1 (`Bead.travel`, 35-45 copies) | neutral on the anchor (a `Prismatic`), but **rewrites the axis** `(0,1,0)` → `(0,0,1)` — the bore axis the bead's own `render()` builds about, which the proposal calls the honest spelling for "a class that has no idea which way its column points". Still deferred on fan-out. |
| `Actuators/OpenCycloid` | 11 | **the worst case in the catalogue.** Both disks' `orbit`, `RadialBearing.orbit` (4 copies at ±2.5 mm) and `Pin.orbit` (27 copies on a 20 mm circle) all rely today on the default `at` meaning the drive axis; the proposal states that reliance in writing (`proposal.md:97-99, 304-312`). Under the new rule each would orbit about its own origin, i.e. not move. Both disks' `spin`, by contrast, is IMPROVED — the proposal's whole "move the 2.5 mm eccentricity from `simulate()` into `render()`" manoeuvre exists only to manufacture what the rule gives directly. Since the project is deferred and unimplemented, nothing regresses; its stage-B proposal must be re-cut against the new rule, and its `.repeat()` copies get their per-copy anchors from cycle 1's `index`. |
