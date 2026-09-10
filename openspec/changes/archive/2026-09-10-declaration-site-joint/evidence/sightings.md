# Every sighting of the declaration-site joint, in the form it wants

Read-only survey, 2026-09-10, of the project repositories under
`/home/asa/devel/libresolid-studio/projects/`. Nothing was executed and
no project file was touched; every row is read off the source, with the
parent's `render()` traced to the placement it applies. It is the
companion to `joint-frame-follows-declarer/evidence/survey.md` (cycle 2),
which classified all 249 class-body declarations; this one takes only the
rows cycle 2 could not close, plus the ones cycle 2's own survey raised,
and writes each in the site form.

**The three sentences the plan note (`workflow/docs/motion-catalogue-2.md`
§3.3) gives as this cycle's examples do not all survive contact with the
source.** Two of the three are answered by cycle 2, and the third is
short of an argument. Section 5 says so with the numbers. The finding is
unaffected — it has eleven other sightings — but the examples are stale
and should not be repeated in a spec.

---

## 1. The reason a class cannot carry the joint

Cycle 2's rule (a class-body joint is stated in the body's own frame)
closes every sighting where the body's own origin IS the joint. What it
cannot close is a body that is not entitled to the declaration at all,
and the catalogue gives four distinct reasons.

### 1.1 The class is shared catalogue hardware

| where | the body | why the class may not carry it |
|---|---|---|
| `Robotic-Hands/Inmoov-sim/Inmoov_sim/forearm.py:147-150` | `axle = Bolt(length=WRIST_AXLE_LENGTH, diameter=…, head=…, head_height=…)` | `Bolt` is the shared fastener catalogue class. A joint on it would give **every bolt in the hand** a wrist freedom. |
| `Lab-Equipment/openflexure-microscope/simulation/microscope/motors/motor_drive.py:31` | `gear_screws = GearLockScrew().repeat(2)` | `GearLockScrew` subclasses the catalogue `No2SelfTapScrew` precisely to hold one joint (`small_gear.py:77-89`); the subclass exists for the declaration and nothing else. |
| `Robotic-Arms/open_manipulator/simulation/open_manipulator_x.py:22-37` | `LeftFinger`, `RightFinger` | two **three-line subclasses of `VisualPack`** whose entire body is one `Prismatic`. The module docstring says so at `:5-7`. |
| `Robots/openvmp/simulation/don1/robot.py:74-77, 148-164` | `Wheel`, `CameraArm` | two subclasses of `Link` that add no geometry and no behaviour — only joint metadata. openvmp's own change record calls them out: `openspec/changes/archive/2026-09-09-move-onto-motion/proposal.md:200-202`. |
| `Actuators/OpenCycloid/simulation/hardware.py:25, 54` | `RadialBearing.orbit`, `Pin.orbit` | two bought-hardware catalogue classes carrying a joint MOST of their instances do not use: the casing bore and the output bearing are "left unbound where a bearing does not move", and 21 of the 27 pins likewise (the source's own comments at `:20-24` and `:49-53`). The declaration is on the class because there was nowhere else to put it. |

### 1.2 The line belongs to the assembly, not to the body

The ten `PARENT-KNOWLEDGE-IN-SUBSTANCE` anchors of cycle 2's survey
(§2.1). Section 3 writes all ten in the site form.

### 1.3 The parent's frame is conditional

`Robotic-Hands/Inmoov-sim/Inmoov_sim/forearm.py:250-291`. The forearm's
own docstring is the requirement, verbatim (`:254-265`):

> Everything else this node moves is declared: the pinion turns with the
> shaft through the relation above, and every pin below the wrist is a
> joint on the body it moves. These four are not, and the reason is the
> presentation turn. A joint states its axis in the frame the PARENT
> places the body in, and this parent's frame is conditional — the
> palm's when `presented` is false, the viewer's when it is true — so a
> `turn` on the gear, the clevis, the bolt or the hand could only be
> stated by hard-coding one of the two, by giving three catalogue classes
> a flag they have no use for, or by naming a group node that would
> rename every leaf under the forearm. **What this wants is a joint
> stated where the child is placed, by the parent that knows its own
> frame; the framework does not offer one yet.**

Measured correction to that paragraph: **cycle 2 answers three quarters
of it.** `present()` (`hand.py:91-95`) is a rest operation, and under
cycle 2 a rest operation no longer enters a class-body joint's frame, so
`WristGear.turn` and `WristClevis.turn` become
`Revolute(axis=(0, 0, 1), unit='deg')` and `Hand.turn` becomes
`Revolute(axis=(1, 0, 0), at=(0, WRIST_SEAT[1], WRIST_SEAT[2]))` — cycle
2's survey row, `evidence/survey.md:161`. What is left for this cycle is
the **axle**, and it is left for reason 1.1, not for the conditional
frame.

### 1.4 One class stands at two opposed placements

Cycle 2's five axes (its survey §2.2). Section 4 writes all five.

---

## 2. Two Link subclasses, two three-line subclasses, one arm — deleted

### 2.1 `Robots/openvmp` `Wheel` — `robot.py:74-77`, used at `:84`

```python
class Wheel(Link):
    """The wheel link, spinning in the foot's bearings."""

    spin = Revolute(axis=(0, -1, 0), at=WHEEL_OFFSET, range=WHEEL_RANGE, unit='deg')
```

`WHEEL_OFFSET` is a point of the **foot's** frame. In the site form the
subclass disappears and the declaration moves into `Foot`'s body:

```python
    wheel = Link('link-wheel',
                 spin=Revolute(axis=(0, -1, 0), at=WHEEL_OFFSET,
                               range=WHEEL_RANGE, unit='deg'))
```

Same axis, same anchor, same range: the text does not change, only where
it is written. That is the shape of most of this cycle's migration.

### 2.2 `Robots/openvmp` `CameraArm` — `robot.py:148-164`

```python
class CameraArm(Link):
    """The camera link, tilted by the base's servo."""

    #: The tilt, stated in the camera assembly's frame: the sign of both
    #: the axis and the anchor is the end's handedness (front/rear) times
    #: the side's (left/right), which only the declaring parent knows, so
    #: both arguments are callables of the realized node.
    tilt = Revolute(axis=lambda node: (0.0, -node._hand, 0.0),
                    at=lambda node: (node._end * node._hand * CAMERA_OFFSET[0],
                                     CAMERA_OFFSET[1], CAMERA_OFFSET[2]),
                    range=SERVO_RANGE, unit='deg')

    def __init__(self, assembly, dir, side, name=None):
        # read by the joint callables above, which resolve at realization,
        # after these are set and before the joint is resolved
        self._end, self._hand = dir, side
        super().__init__(assembly, name=name, dir=side)
```

The docstring states the finding in its own words: *"which only the
declaring parent knows"*. The declaring parent is `Camera`
(`robot.py:167-190`), which declares `dir` and `side` as `Count`
parameters at `:171-172` and places the arm at `:190`:

```python
        self.camera.rotate(self.side * -90, Z).translate([self.dir * self.side * x, y, z])
```

In the site form, `Camera`'s body:

```python
    camera = Link('link-camera', dir=side,
                  tilt=Revolute(axis=lambda parent: (0.0, -parent.side, 0.0),
                                at=lambda parent: (parent.dir * parent.side * CAMERA_OFFSET[0],
                                                   CAMERA_OFFSET[1], CAMERA_OFFSET[2]),
                                range=SERVO_RANGE, unit='deg'))
```

Deleted with it: the `CameraArm` class, its `__init__` override, and the
two instance attributes `_end` and `_hand` that exist only for the two
lambdas to read (`robot.py:163`; no other reader in the repository). The
callables stop reaching into the child for the parent's knowledge and
read the parent directly, which is the whole of the change.

### 2.3 `Robotic-Arms/open_manipulator` `LeftFinger` / `RightFinger` — `open_manipulator_x.py:22-37`

```python
class LeftFinger(VisualPack):
    travel = Prismatic(
        axis=JOINTS["gripper_left_joint"].axis,
        at=JOINTS["gripper_left_joint"].origin_mm,
        range=JOINTS["gripper_left_joint"].millimetres,
        unit="mm",
    )


class RightFinger(VisualPack):
    travel = Prismatic(…"gripper_right_joint"…)
```

`layout.py:51-52` gives the two axes as `(0.0, 1.0, 0.0)` and
`(0.0, -1.0, 0.0)` — mirrored in the URDF — and the parent applies a pure
translation, so cycle 2 does **not** merge them: two placements, two
literal axes, two subclasses. In the site form, `Link5Assembly`'s body:

```python
    left_finger = VisualPack("gripper_left_palm.stl",
                             travel=Prismatic(axis=JOINTS["gripper_left_joint"].axis,
                                              at=JOINTS["gripper_left_joint"].origin_mm,
                                              range=JOINTS["gripper_left_joint"].millimetres,
                                              unit="mm"))
    right_finger = VisualPack("gripper_right_palm.stl",
                              travel=Prismatic(…"gripper_right_joint"…))

    left_finger.travel.drives(right_finger.travel)
```

Two subclasses deleted. Note the relation at `open_manipulator_x.py:52`,
which names **two site-declared coordinates by path** — the reason this
cycle has a `couplings` delta and not only a `joints` one.

`VisualPack` (`parts.py:34-42`) declares no parameters and no children:
it is a NON-DECLARATIVE node with a positional `filename` and a
`**params`-free `__init__`. A site joint therefore has to work on a class
the declarative layer knows nothing about, and the keyword has to be
stripped before the constructor is called or `filename` would be joined
by an unexpected `travel`.

---

## 3. The ten anchors cycle 2 leaves behind, in the site form

Cycle 2's `ZERO-BUT-PLACED`-and-pose-changing rows that it classifies
`PARENT-KNOWLEDGE-IN-SUBSTANCE` (its survey §2.1, its design §4 and §8).

### 3.1 InMoov's seven finger `Revolute`s

Every one of them is the anchorless `mcp = Revolute(axis=_HINGE,
unit='deg')` (`_HINGE = (1, 0, 0)`, `fingertip.py:31`), and its line is
the **fork's pivot**, which is the declaring `Finger`'s own origin:

| declaration | file:line | the child, and the parent's placement |
|---|---|---|
| `Fingertip.mcp` | `fingertip.py:58` | `Finger.distal`, `translate(MIDDLE_JOINT)` then `translate(PROXIMAL_JOINT)` (`finger.py:163-164`) |
| `ThumbFingertip.mcp` | `fingertip.py:73` | `Thumb.distal`, `translate(THUMB_PROXIMAL_JOINT)` (`thumb.py:48`) |
| `ProximalForkBolt.mcp` | `finger.py:56` | `Finger.pip_bolt`, `place(part, seat)` then `translate(PROXIMAL_JOINT)` (`finger.py:168-171`) |
| `ProximalForkNut.mcp` | `finger.py:62` | `Finger.pip_nut`, same |
| `MiddleForkBolt.mcp` | `finger.py:73` | `Finger.dip_bolt`, `place(part, seat)`, `translate(MIDDLE_JOINT)`, `translate(PROXIMAL_JOINT)` (`finger.py:173-177`) |
| `MiddleForkNut.mcp` | `finger.py:80` | `Finger.dip_nut`, same |
| `MiddlePhalanx.mcp` | `middle_phalanx.py:36` | `Finger.middle`, `translate(PROXIMAL_JOINT)` (`finger.py:161`) |

with, from `params.py:147-170`,
`PROXIMAL_JOINT = (0.0, 34.99, -1.01)`,
`MIDDLE_JOINT = (0.0, 24.98, -1.02)`,
`THUMB_PROXIMAL_JOINT = (0.0, 34.99, -1.01)` and
`_DISTAL_JOINT = (0.0, 59.97, -2.03)` (`fingertip.py:34`).

**In the site form every one of the seven is written with no anchor at
all**, because `at` at a declaration site defaults to the DECLARING
parent's origin, which is exactly the fork pivot:

```python
    middle = MiddlePhalanx(mcp=Revolute(axis=_HINGE, unit='deg'),
                           pip=Revolute(axis=_HINGE, at=PROXIMAL_JOINT, unit='deg'))
    distal = Fingertip(mcp=Revolute(axis=_HINGE, unit='deg'),
                       pip=Revolute(axis=_HINGE, at=PROXIMAL_JOINT, unit='deg'),
                       dip=Revolute(axis=_HINGE, at=_DISTAL_JOINT, unit='deg'))
```

Two things to read off that. First, **not one number is typed that is
not already in the file**: `PROXIMAL_JOINT` and `_DISTAL_JOINT` are the
finger's own constants, in the finger's own frame, where cycle 2 would
have had the fingertip write their negations `(0, -24.98, 1.02)` and
`(0, -59.97, 2.03)` (cycle 2's survey §2.3). Second, the site
declarations of `pip` and `mcp` REPLACE the class's, and
`middle_phalanx.py:35-36` declares `pip` then `mcp`, so under the slot
rule of decision 4 the composition is unchanged: `pip` innermost, `mcp`
outside it.

### 3.2 The Internal Cycloidal Actuator's two disk `Orbit`s

`Actuators/Internal-Cycloidal-Actuator/simulation/actuator/parts.py:118-128`
(disk 1) and `:168-178` (disk 2):

```python
    spin = Revolute(axis=ACTUATOR_AXIS, at=DISK_1_BORE_CENTRE, unit='deg')
    orbit = Orbit(axis=ACTUATOR_AXIS, carries=DISK_1_BORE_CENTRE, unit='deg')
```

`DISK_n_BORE_CENTRE` is **derived**, not typed: `_bore_centre()` computes
it from the STEP document's own placement, because that project's
ratified spec (`disk-ring-engagement`) says *"Neither the rest bore
centre nor the journal position SHALL be written as a literal"*.

Cycle 2 splits the pair. `spin` becomes clean in the disk's own frame —
`at=BORE_AXIS_POINT`, the project's own spec literal `(0, 0, -2.000)`
(cycle 2's survey §2.3). `orbit` cannot follow it: its line is the
ACTUATOR's axis, and the disks' own origins stand **3.9974 mm** and
**3.9488 mm** off it, so a defaulted own-frame anchor would carry them
round a circle at twice the true 2.000 mm eccentricity at a wrong phase.

In the site form, in the assembly's body:

```python
    disk_one = CycloidalDisk1(orbit=Orbit(axis=ACTUATOR_AXIS,
                                          carries=DISK_1_BORE_CENTRE, unit='deg'))
    disk_two = CycloidalDisk2(orbit=Orbit(axis=ACTUATOR_AXIS,
                                          carries=DISK_2_BORE_CENTRE, unit='deg'))
```

`at` is omitted — the actuator axis runs through the assembly's own
origin, which is what the class's comment already says (`parts.py:126`:
*"`at` is omitted: the actuator axis passes through the parent frame's
origin"*). `carries` **must stay written**: the point the orbit carries
is the disk's BORE centre, and the default — the disk's own origin — is
3.9974 mm away from it. The expression is the one the project already
computes, moved from the class body to the site, so no forbidden literal
is typed and `_bore_centre()` survives for the orbit while cycle 2
retires it for the spin.

The plan note's example sentence,
`disk_one = CycloidalDisk(orbit=Orbit(axis=(0, 1, 0)))`, is short by that
`carries=`. Section 5.

### 3.3 openflexure's `GearLockScrew` — the cleanest row in the survey

`Lab-Equipment/openflexure-microscope/simulation/microscope/motors/small_gear.py:77-89`:

```python
class GearLockScrew(No2SelfTapScrew):
    """One of the two self-tappers that lock the small gear to the
    motor shaft, off-axis at ``(0, +-SCREW_Y, ...)`` in the motor
    drive's frame.

    Its only freedom is to orbit the shaft axis with the gear: the
    joint's axis and anchor are the shaft's, at the motor drive's own
    frame origin, which the screw's own placed position does not lie
    on -- exactly the case a `Revolute` exists for, so no `at` is
    needed here.
    """

    orbit = Revolute(axis=(0, 0, 1), unit='deg')
```

The parent, `motor_drive.py:31` and `:50-52`:

```python
    gear_screws = GearLockScrew().repeat(2)
        …
        for screw, sign in zip(self.gear_screws, (-1, 1)):
            screw.translate([0, sign * SCREW_Y,
                             L.motor_shaft_z(self.tilted) + SCREW_HEAD_Z])
```

In the site form:

```python
    gear_screws = GearLockScrew(orbit=Revolute(axis=(0, 0, 1),
                                               unit='deg')).repeat(2)
```

**One declaration, two copies, no sign, no index, no `at`** — the shaft
axis is the line through the motor drive's own origin, and it is the same
line for both copies whatever the parent translates them by. Cycle 2's
survey predicted this row would need *"a callable of `node.index`
(cycle 1)"*; measured against the site rule it needs neither the callable
nor the index. It is also the sighting that settles cycle 2's open
question about a site joint on a `.repeat()` (decision 8).

`motor_drive.py:57-60` also binds the coordinate by ASSIGNMENT on the
realized child:

```python
        for screw in self.gear_screws:
            screw.orbit = self.shaft_pin.turn.value
```

so a site-declared coordinate has to answer to `child.name = value` and
not merely to a relation.

### 3.4 OpenCycloid: four orbit declarations cycle 2 does not misread but REFUSES

`Actuators/OpenCycloid`, stage B committed at `47a2a16` on its own main
and archived at `d7122e1`. Four `Orbit` declarations, twelve moving
bodies, every one of them `Orbit(axis=AXIS, unit="deg")` with **both
`at` and `carries` defaulted**:

| declaration | file:line | bodies | the parent's placement |
|---|---|---|---|
| `CycloidalDiskStageOne.orbit` | `simulation/printed.py:162` | 1 | `self.stage_one.translate((0.0, -ECCENTRIC_RADIUS, 0.0))` (`actuator.py:91`) |
| `CycloidalDiskStageTwo.orbit` | `simulation/printed.py:177` | 1 | `self.stage_two.translate((0.0, ECCENTRIC_RADIUS, 0.0))` (`actuator.py:92`) |
| `RadialBearing.orbit` on `eccentric_bearings = RadialBearing(inner_diameter=17.1, outer_diameter=26.0, width=5.0).repeat(4)` (`actuator.py:59-61`) | `hardware.py:25` | 4 | `bearing.translate((0.0, -sign * ECCENTRIC_RADIUS, index * 5.0))`, sign `+1` for copies 0-1 and `−1` for 2-3 (`actuator.py:93-95`) |
| `Pin.orbit` on `output_pins = Pin().repeat(OUTPUT_PIN_COUNT)` (`actuator.py:108`) | `hardware.py:54` | 6 | `pin.translate((R·cos(phase), R·sin(phase), 3.0))`, `phase = index * 60° − 90°` (`actuator.py:126-133`) |

Today every one of them works, and the disk's own comment
(`printed.py:157-161`) says exactly why:

> `carries` is left unstated: it defaults to this node's own placed
> origin, which the framework resolves to exactly `(0, 0, 0)` in this
> node's own frame with no arithmetic — the bore centre — and derives
> the 2.5 mm radius and the −90 deg phase from it and the drive axis.
> **Neither number is typed anywhere.**

That is ADR-094's `_OWN_PLACED_ORIGIN` doing the one job it was built
for, against `at` defaulting to the parent's origin, which is the drive
axis.

**Under cycle 2's rule the two defaults collapse onto one point.** `at`
becomes the body's own origin and `carries` becomes the body's own
origin, so the carried point lies ON the line, the radius is zero, and
the joint is refused at the first binding — cycle 2's own task 2.2, "A
defaulted carried point still refuses at binding when it lies on the
line", fired on twelve bodies of a shipped machine. This is a harder
failure than the ten anchors of §3.1-3.3, which read wrong: these do not
read at all.

In the site form all four are written **exactly as they are today**, one
level out:

```python
    stage_one = CycloidalDiskStageOne(orbit=Orbit(axis=AXIS, unit="deg"))
    stage_two = CycloidalDiskStageTwo(orbit=Orbit(axis=AXIS, unit="deg"))
    eccentric_bearings = RadialBearing(inner_diameter=17.1, outer_diameter=26.0,
                                       width=5.0,
                                       orbit=Orbit(axis=AXIS, unit="deg")).repeat(4)
    output_pins = Pin(orbit=Orbit(axis=AXIS, unit="deg")).repeat(OUTPUT_PIN_COUNT)
```

`at` defaults to `CycloidalDrive`'s / `OutputModule`'s own origin, which
is the drive axis; `carries` defaults to each CHILD's own origin, which
is the point that rides the circle. **Ten radii and ten phases stay
derived and untyped**, including the six output pins' 60° spacing and the
four bearings' two signs — one declaration each, four copies and six
copies, every copy's own number falling out of its own rest placement.

Three things this sighting settles that nothing else in the catalogue
does:

1. **It is the decisive measurement for what a DEFAULTED `carries` means
   at a site** (design decision 2). If `carries` followed `at` into the
   parent's frame, all four of these would default onto the line and be
   refused, and the machine would be unstateable in either cycle.
2. **It makes the site joint on a `.repeat()` a hard requirement, not an
   open question.** Ten of the twelve bodies are repeat copies of two
   catalogue classes; without a site joint on a repeat, OpenCycloid
   cannot be stated after cycle 2 at all.
3. **It puts a site joint on a declaration that also carries real
   PARAMETERS.** `RadialBearing(inner_diameter=17.1, outer_diameter=26.0,
   width=5.0, orbit=Orbit(...))` mixes three parameters and one joint in
   one call, so the keyword split has to be exact: the three reach the
   constructor and enter identity, the fourth reaches neither.

And both repeats are driven by a BROADCAST whose path ends on a
site-declared coordinate (`actuator.py:88`, `:117`):

```python
    eccentric_shaft.spin.drives(eccentric_bearings.orbit)
    carrier.spin.drives(output_pins.orbit)
```

so `RepeatDeclaration.__getattr__`, not only `ChildDeclaration`'s, has to
find a site joint held on the declaration it wraps.

For completeness: cycle 2 handles the disks' other joint cleanly. `spin =
Revolute(axis=AXIS, at=(0.0, ∓ECCENTRIC_RADIUS, 0.0))` (`printed.py:155,
173`) exists only to name the parent's translate, and its comment says
so; cycle 2 deletes the anchor. So the disk ends up with one class joint
and one site joint, `spin` at slot 0 and `orbit` at slot 1 — the same
declaration order the source's comment at `printed.py:138-143` insists
on, preserved by the slot rule (design decision 4).

---

## 4. Cycle 2's five axes, in the site form

Every one is a class placed at two opposed attitudes, where cycle 2's
own-frame rule leaves the axis unstateable as one literal (cycle 2's
survey §2.2, its design decision 3). At a declaration site the axis is
the PARENT's again, and each copy's own carry supplies the sign.

| # | today | the site form |
|---|---|---|
| 1 | `XGuide.spin = Revolute(axis=(0, 1, 0), at=(X_IDLER[0], 0.0, X_IDLER[1]), unit='deg')` (`Prusa3-vanilla/simulation/xaxis.py:88`), `guides = XGuide().repeat(2)` (`:135`), copies placed `along_y` = Rx(−90) and `along_minus_y` = Rx(+90) (`:184-185`) | `guides = XGuide(spin=Revolute(axis=(0, 1, 0), at=(X_IDLER[0], 0.0, X_IDLER[1]), unit='deg')).repeat(2)` in `XAxis`'s body |
| 2 | `YGuide.spin = Revolute(axis=(1, 0, 0), at=(0.0, Y_IDLER[0], Y_IDLER[1]), unit='deg')` (`yaxis.py:86`), `.repeat(2)` (`:105`), copies placed `along_x` = Ry(+90) and `along_minus_x` = Ry(−90) (`:160-161`) | `guides = YGuide(spin=Revolute(axis=(1, 0, 0), at=(0.0, Y_IDLER[0], Y_IDLER[1]), unit='deg')).repeat(2)` in `YAxis`'s body |
| 3 | `MotorGear.turn = Revolute(axis=SHAFT_AXIS, at=tuple(float(v) for v in layout.MOTOR_SHAFT), unit='deg')` (`hangprinter/simulation/winch.py:148-149`), placed `MOTOR_GEAR` or `MOTOR_GEAR_MIRRORED` (`layout.py:207-209`) | `motor_gear = MotorGear(mirrored=left_handed, turn=Revolute(axis=SHAFT_AXIS, at=MOTOR_SHAFT, unit='deg'))` in `WinchABC`'s body, and the unmirrored twin in `WinchD`'s |
| 4 | `RollerBearing.spin = Revolute(axis=SHAFT_AXIS, at=BELT_ROLLER_AXIS, unit='deg')` (`winch.py:159`), `rollers = RollerBearing().repeat(2)` (`:294`), copies placed `R([90,0,0])` and `R([-90,0,0])` (`layout.py:216-221`) | `rollers = RollerBearing(spin=Revolute(axis=SHAFT_AXIS, at=BELT_ROLLER_AXIS, unit='deg')).repeat(2)` |
| 5 | `Leg.turn = Revolute(axis=(0, -1, 0), at=SIDE_OFFSET, range=THIGH_RANGE, unit='deg')` (`openvmp/simulation/don1/robot.py:113`), legs placed `rotate(90 + 90 * side, Z)` — 180° left, 0° right (`:220`) | `left_leg = Leg(side=1, turn=Revolute(axis=(0, -1, 0), at=SIDE_OFFSET, range=THIGH_RANGE, unit='deg'))` and the same text on `right_leg`, in `Hip`'s body |

Two of the five projects wrote the reason down as a design decision, and
hangprinter's is the framework's own carry described from the outside
(`winch.py:57-64`):

> The direction every motor gear and both belt roller bearings turn
> about, in every winch: the motor shaft's own axis, the winch frame's
> Y. Declaring a leaf's joint about this shared axis, rather than about
> the leaf's own placed +Z, is what lets one declaration serve both the
> unmirrored and the mirrored leaf: **the framework carries this
> direction into each body's own frame and finds the local axis mirrored
> gears turn about there too.**

Cost to record: rows 3 and 5 move ONE class declaration into TWO
declaration sites (`WinchABC`/`WinchD`; `left_leg`/`right_leg`), so the
text is written twice where it is written once today. Rows 1, 2 and 4
ride a `.repeat()` and are written once.

---

## 5. Where the evidence contradicts the plan note

`workflow/docs/motion-catalogue-2.md` §3.3 gives three example sentences.
Measured against the source, after cycle 2:

1. `leadscrew = ThreadedRod(turn=Revolute(axis=(1, 0, 0), at=(LEADSCREW_START_X, *DRIVE_AXIS_YZ)))`
   — **cycle 2 already fixes this, better.** `poseidon/simulation/hardware.py:96-103`
   writes `at=(LEADSCREW_START_X, *DRIVE_AXIS_YZ)` and
   `pump.py:62` writes `self.leadscrew.translate([LEADSCREW_START_X, drive_y, drive_z])` —
   the same three numbers, so it is a `RESTATES` row and cycle 2 DELETES
   the anchor outright, leaving `turn = Revolute(axis=(1, 0, 0), unit='deg')`
   on the class. The site sentence would put the layout constants BACK,
   at the site instead of in the hardware module. Same for
   `ShaftCoupling` (`hardware.py:56-63`, `pump.py:61`).
   Poseidon should not be listed as a validation project for this cycle.

2. `screw = ZScrew(turn=Revolute(axis=(0, 0, 1), at=lambda parent: (parent.side * 17, 0, 0)))`
   — **cycle 2 already fixes this too, and `ZScrew` has no joint today at
   all.** `Prusa3-vanilla/simulation/zscrew.py:27-33` declares no joint;
   the parent hand-writes `self.screw.rotate(screw_angle(z), [0, 0, 1])`
   (`zaxis.py:69`) after placing it at
   `translate([self.inboard * 17.0, 0, Z_SCREW_BOTTOM])` (`zaxis.py:51,58`).
   The screw turns on its own centreline through its own origin, so
   under cycle 2 the class writes `turn = Revolute(axis=(0, 0, 1), unit='deg')`
   and needs no anchor and no flag. Cycle 2's own tasks §8.6 already
   records this ("correct the Prusa i3 entry … it does"). Prusa i3 IS a
   validation project for this cycle, but for its **belt guides** (§4
   rows 1-2), not for its Z screws.

3. `gear = WristGear(turn=Revolute(axis=wrist_axis, at=wrist_anchor, unit='deg'))`
   — **three quarters of the wrist group is cycle 2's** (§1.3). What is
   left is the `axle`, and it is left because `Bolt` is shared catalogue
   hardware, not because the frame is conditional.

And the fourth, from §3.3's prose rather than its examples:

4. `disk_one = CycloidalDisk(orbit=Orbit(axis=(0, 1, 0)))` — **short by
   its `carries=`** (§3.2). Written as given, the orbit would carry the
   disk's own origin, 3.9974 mm off the actuator axis, instead of its
   bore centre 2.000 mm off it: a circle of twice the true eccentricity,
   at a wrong phase, and no refusal — the two points are distinct, so the
   radius is not zero and nothing is caught. That is the sharpest single
   reason this cycle must state what a defaulted `carries` means at a
   site (decision 3).

None of the four weakens the finding. The finding's live sightings, after
cycle 2, are **fourteen, in eight projects**: four
subclasses-for-metadata and two catalogue classes carrying a joint most
of their instances do not use (§1.1, §2); ten anchors whose line is the
assembly's (§3.1-3.3); OpenCycloid's four orbit declarations, which cycle
2 refuses outright (§3.4); five axes at opposed placements (§4); and
openvmp's data-built parts (§6). More than half of the site declarations
the migration writes carry **no anchor at all** — every one of InMoov's
seven finger `mcp`s, openflexure's screw pair, and all four of
OpenCycloid's orbits — and not one sighting needs a number the project
does not already have.

---

## 6. openvmp's data-built children: what the keyword cannot reach

`Robots/openvmp/simulation/don1/link.py:28-45` builds children **in
`__init__`**, from a `.assy` file, one generic `StepPart` or
`SubAssembly` per entry, named by the file (`unique_names`, `link.py:9-16`):

```python
        self.placements = blueprints.load(assembly, **params)
        self.parts = []
        for placement, child_name in zip(self.placements, unique_names(self.placements)):
            if placement.part:
                child = part_node(placement.part, name=child_name)
            else:
                child = SubAssembly(placement.assembly, name=child_name, **placement.params)
            self.parts.append(child)
```

82 placed parts at runtime. Eight literal `spin(...)` call sites move
them (`robot.py:129,136,140,143,246,371,376,380`; two are inside `for`
loops, which is why the project's own record says nine). `spin` itself
(`link.py:116-129`) is **`Joint._carry` open-coded**:

```python
def spin(link, paths, angle, line):
    """Turn the parts at ``paths`` by ``angle`` about ``line`` (link frame).

    Each part's motion is applied in its own frame, inside its rest
    placement, so the line is carried back through that placement first.
    """
    import numpy as np
    for path in paths:
        m = transform_of(link, path)
        rotation, position = m[:3, :3], m[:3, 3]
        local_direction = rotation.T @ line.direction
        local_point = rotation.T @ (line.point - position)
        rotate_about(node_at(link, path), angle, local_direction.tolist(),
                     local_point.tolist())
```

— the parent's frame line, carried through the inverse of the child's
rest placement, applied innermost. Written by hand, in a project, because
the framework offered no joint that could be stated there.

The project's own statement of what it cannot write
(`openspec/changes/archive/2026-09-09-move-onto-motion/proposal.md:210-231`):

> A joint is class metadata, and a relation's path is checked against
> declared children. The blueprint links' children are neither …

```python
    # a joint on a body the blueprint placed, named as the file names it
    front.yaw.drives(base['motion-front-wormgear/worm'].spin,
                     ratio=WORM_GEAR_TEETH)
```

**The declaration keyword does not reach this** — there is no declaration
to hang a keyword on — and, measured, it does not need to. Two things are
being asked for and they are not the same size.

*Give a realized child a freedom.* **Cycle 2 already does it, and this
cycle adds nothing.** `spin()`'s whole arithmetic is the map from the
LINK's frame back into the part's; under cycle 2 a class-body joint is
stated in the body's OWN frame, and the part's axis in its own STEP frame
is the constant the project already holds (`REX_SHAFT_AXIS` and its
siblings). So the project writes one subclass with two declared
parameters and ADR-088's callable — vocabulary that shipped two cycles
ago:

```python
class TurningPart(StepPart):
    spin_axis = Vector((0, 0, 1))
    spin_point = Vector((0, 0, 0))
    spin = Revolute(axis=lambda node: node.spin_axis,
                    at=lambda node: node.spin_point, unit='deg')
```

and its existing loop builds `TurningPart(placement.part, name=child_name,
spin_axis=..., spin_point=...)` for the entries that turn and `StepPart`
for the rest. All 82 parts keep their generic class; the ones that move
get a real coordinate — enumerable, bindable, range-checked, placed at
its own slot — and `spin()`, `axis_of` and `transform_of` are deleted
because there is nothing left to carry.

*Let a relation NAME such a child by its realized name.* **No cycle in
this campaign does it.** A relation is class metadata whose every segment
is checked at class definition against the classes the path names, and a
child built from a file at construction has no class-level name to check.
`base['motion-front-wormgear/worm']` stays unwritable, and the project
keeps binding those coordinates from its own `simulate()`.

Said plainly so the reviewer can weigh it: **openvmp's data-built parts
are a cycle-2 migration, not a cycle-3 one, and the sentence the project
wrote down is a separate finding that stays open.**
