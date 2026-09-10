# Motion catalogue, second campaign: fan-out, frames, laws, the solver

**Status: provisional plan, 2026-09-10.** Nothing here is ratified. It
is the working document five OpenSpec cycles are cut from, in the order
of §3; where it and a baseline spec or an accepted ADR disagree, the
spec and the ADR are right and this note is stale. Each section's own
note will name the OpenSpec change that becomes the authority for it
once that cycle is proposed. The directions below were walked through
with the pilot finding by finding and ratified in conversation on
2026-09-10; this note is the durable record of that walkthrough, not
the authority — the cycles are.

Predecessor: `composed-joints.md` (ADR-093, ADR-094, ADR-095), whose
three cycles closed the composition-order, orbit and floating-body
findings. Research the directions are measured against:
`workflow/archive/motion-layer-2026-09-09/joints-and-couplings.md` and
`mechanics-ontology.md` — a joint is a Reuleaux pair, a coupling is one
verb `a.drives(b)`, a derived coordinate is a linear formula solved both
ways, and the framework holds no closure solver: a `law=` is the
project's function, called forward only.

---

## 1. The findings

All in `workflow/warts.md`, sections "3DPrintedClocks wall clock 01 and
Thor (2026-09-09)", "Motion catalogue refactor (2026-09-09)", "Inmoov-sim
stage B (2026-09-10)" and "hexapod_spiderbot_model stage B (2026-09-10)".
Deferred projects and their stage-B proposals:
`libresolid-studio/docs/motion-general-refactor.md`.

| Finding | Sightings | Cycle |
|---|---|---|
| A relation cannot fan out over a `.repeat()` child | OpenCycloid (4 bearings, 6 pins, per-copy sign/phase), abacus (4 earth beads, law reads rank), OpenFlexure (identity: 3 nuts, lock screws), fender-bender (5 channels), InMoov (`Hand.simulate()`'s ten `connect()`s), V8 (8 units, per-unit phase) | 1 (InMoov's ten `connect()`s: 1+5, a per-copy SOURCE) |
| A dotted coordinate name is written but not read by name | hexapod (`capture_poses.py`) | 1 |
| A joint's `at` cannot mean the body's own placed origin | Thor (13 catalogue parts), V8 (4 timing gears), Poseidon, OMX, hexapod (`Femur.lift`, `Tibia.knee` restate the parent's translate), Pascaline (`Pawl.swing`), fender-bender | 2 |
| A joint belongs to the declaration site as often as to the class | Poseidon (`ThreadedRod`), OMX (`VisualPack`, two three-line subclasses), Prusa i3 (`±17` by the parent's flag), OpenVMP (two `Link` subclasses, `CameraArm` sign = parent's handedness × own; 82 data-built parts), InMoov (wrist group under a conditional `present()`) | 3 |
| A relation chain must be stated in one class body / an ancestor cannot source from a descendant-solved coordinate / a class's own derived coordinate is unbound in its own `simulate()` | clock 01 (`centre.drives(third)` in `Train`), OpenTorque (1:8 ratio stated twice), OpenFlexure (root sourcing `column.travel`; thread ratio pushed up into `Axis`), Thor (motor pulleys turned nothing, caught by pose comparison) | 4 |
| A subclass cannot restate a NAMED relation of its base | OpenTorque preview (`motor_rotor.spin` from a different source) | 4 |
| An author-bound joint keeps its value but loses its motion between runs | Prusa i3 (37.5, 70.4, 0.05 mm on the second render), hangprinter winches (masked by a zero default) | 4 |
| A relation reads one coordinate; a law may need several, and drive several | Pascaline pawl (this drum and the next), kossel (three carriage travels → each rod's spin, lean, swing, rise), OpenFlexure legs (two rotations from a multi-source law) | 5 |
| A bare number cannot be added to a dimensioned token | Pascaline (`CHANNEL_Y[1] - CHANNEL_Y[0] - SLIDE_WIDTH - 2 * clearance`) | folded, §4 |

Out of this campaign: the two exact-negative performance levers still
listed under "wall clock 02" (exact-solid index bounds; mesh-distance
tier and parallel booleans), and the subclass-inner-joint slot keyword
(absorbed by InMoov; waits for a second sighting, as ADR-093 intended).

## 2. What is and is not a primitive

Measured against the research: none of the five cycles adds a kind of
pair or a kind of coupling. Fan-out is multiplicity on the declaration
layer (Modelica's `for`-connect over component arrays; MuJoCo's
`replicate`). The frame rule is a statement about WHERE a pair is
described (MuJoCo: a joint's position is in the body's own frame,
default the body origin; URDF: a joint's origin is in the parent's
frame — the two rules the two declaration sites map onto). The
declaration-site keyword is the URDF rule made available where the
parent already knows the placement. Multi-source and multi-target laws
are still one verb with the project's closure; the framework inverts
nothing it did not already. The solver change is a fixpoint over the
tree instead of over one node's relations, the analytic-loop aggregate
Modelica handles by flattening. The stale-motion item is a correctness
bug in the existing contract, not a design.

## 3. The ratified directions, in cycle order

### 3.1 Cycle 1 — fan-out over repeated children (+ the dotted reader)

**Refined 2026-09-10 while proposing the cycle; the OpenSpec change
`repeat-fan-out` is the authority for this section from here on.** Four
things the walkthrough assumed turned out not to hold against the tree
and the catalogue, and each is marked below with the evidence that
forced it. Everything else stands as ratified.

Today: `RepeatDeclaration.realize` (`solid_node/node/declarative.py`)
returns identical copies with no index; children are named `attr-i`;
`RepeatDeclaration.__getattr__` raises `SidewaysReadError`; the
couplings solver refuses a path through a repeated declaration
(`couplings.py`, spec scenarios "A path through a repeated child is
refused" and "A relation places a repeated child"). Every project above
binds its copies in a `for` loop in `simulate()`.

Ratified:

- Each copy realized by `.repeat(n)` carries its `index` (0-based),
  readable on the realized node.
  **Refined: the copy carries its index and NOT the count.** A declared
  parameter is a data descriptor, and the abacus's `Frame` declares
  `halves = FrameHalf(count=count, ...).repeat(2)` where `FrameHalf`
  itself declares `count = Count(9, min=1)`: a framework-set `count` on
  that copy would be silently invisible behind the declaration
  (measured, `evidence/probe_shadow.py`), and reserving the name would
  refuse a repeat the catalogue already contains. No law in any sighting
  reads the count — OpenCycloid's sign, the abacus's rank, the V8's
  phase table and fender-bender's channel offset all read the index and
  take the count from a module constant or a parent parameter. `count`
  waits for its own sighting, as ADR-093 made the slot keyword wait.
  `index` is clash-free across the whole catalogue today (the only
  `index` declarations are 3DPrintedClocks' arbor ranks, and no clock
  uses `.repeat()` at all); a repeated class that does declare `index`
  is refused where the repeat is written.
- `a.drives(children.joint, ...)` with a repeated driven end means n
  relations, one per copy. With `ratio=`/`offset=` every copy gets the
  same linear formula. With `law=` the law is called once per copy and
  is handed THAT copy as the driven node, so `bead.index` is one
  attribute read away. Fan-out never inverts: a repeated end may only be
  driven, never a source (a source has one value, n copies have n).
  **Refined: no law signature changes.** ADR-089 already hands `law=`
  the realized nodes that OWN the two coordinates; the copy IS the
  owner of the driven coordinate, so a broadcast calls the existing
  two-argument callable once per copy instead of once per instance.
- ~~The identity form is a wiring keyword on the repeat:
  `.repeat(n, travel=column.travel)`, the weakest form and the one to
  build first.~~ **Withdrawn: it is already the contract, and the rest
  of it is the broadcast.** `Bead(travel=earth).repeat(4)` binds all
  four copies from the parent's own coordinate today, in the fixpoint,
  waiting for a source a relation solves — measured on this tree,
  `evidence/probe_wiring_repeat.py`, and already specified (ports,
  "A repeated child is wired per instance"). What a wiring cannot do is
  take its source from a PATH (`column.travel` where `column` is a
  child), because a wiring is downward-only by ADR-089; that case is
  exactly a broadcast relation with the default ratio of one, which
  this cycle builds. Adding `.repeat(n, keyword=...)` would be a second
  spelling for the first case and no help with the second, so the cycle
  adds no keyword.
- The refusal scenarios flip to broadcast scenarios; a path through a
  repeated child on the SOURCE side stays refused, by name.
  **Refined: the flip is stated once, for a repeated segment ANYWHERE
  in the path.** A path may pass through at most ONE repeated segment —
  `beads.travel`, `column.beads.travel`, `legs.femur.lift` are all one
  fan-out — and a second is refused by name. Stating it per position
  would have left `column.beads.travel` refused for no reason a reader
  could give.
- Not covered, on purpose: the Pascaline's eight-way carry (each copy a
  structurally different expression) and OpenVMP's data-built children
  (cycle 3). Both stay separate findings.
  **Refined: InMoov's ten `connect()`s join that list.** `Hand` drives
  each of its four repeated fingers from a DIFFERENT driver
  (`thumb`, `index`, `middle`, `ring`, `little`), and a broadcast has
  one source. The sighting closes with cycle 5's tuple source — the law
  handed all five and picking by `finger.index` — not with this cycle.
  The finding table's row lists it under cycle 1; it belongs under 1+5.

Rider: `get_coordinate(node, 'pose.roll')` exported beside
`set_coordinate`, returning the bound slot, and the ports spec saying a
name the enumerator reports is a name the framework can read back. A
name the enumerator does NOT report is refused by name rather than
answered with `None`, because `set_coordinate` on such a name silently
creates an instance attribute today and a reader that answered `None`
would make the pair silently wrong in both directions. Fan-out's
per-copy laws are the next consumer of the enumerator, which is why it
rides here.

Validation project: OpenCycloid stage B (fan-out and orbit together);
abacus when an agent is free.

### 3.2 Cycle 2 — a joint is stated in the frame of whoever declares it

Today: a joint's `axis` and `at` are stated in the PARENT's frame and
carried into the body by inverting the rest placement (`Joint.place` /
`_carry`, `joints.py`; joints spec, "centring translations omitted when
the local anchor is zero"). A class therefore repeats its parent's
`translate` as its own `at`, and a design-placed part cannot anchor on
its own origin at all.

Ratified, as a contract change like ADR-093's:

- A joint declared in a CLASS BODY is stated in that body's OWN frame,
  axis and anchor both. `at` defaults to the body's own origin, so
  `turn = Revolute(axis=(0, 0, 1))` on a pinion spins it about the line
  through its own placed origin, wherever the parent put it — MuJoCo's
  rule. No sentinel is needed: in the body's own frame that point IS the
  origin. This deletes every `at` that repeats a parent's translate and
  closes the own-placed-origin finding for all its sightings.
- A joint declared at a DECLARATION SITE (cycle 3) is stated in the
  declaring PARENT's frame — URDF's rule. The frame follows the
  declarer.
- `Orbit` and `Free` keep their internals; only the frame their
  arguments are read in follows the same rule.
- Proof: the proposer's first task is a survey of the 19 projects on
  the motion layer for a class-declared `at` or `axis` that GENUINELY
  needs the parent's frame (as opposed to restating the parent's
  placement). The pose comparison over all 19 projects, before and after
  each project's `at` is rewritten, is the evidence; a project whose
  joint cannot be restated in its own frame is the input to cycle 3, not
  a reason to keep the old rule.

Validation project: V8 stage B (timing gears, then the rods with the
orbit); Thor's thirteen parts; fender-bender after cycles 1 and 2.

### 3.3 Cycle 3 — the declaration-site joint keyword

Ratified, on top of 3.2:

    leadscrew = ThreadedRod(turn=Revolute(axis=(1, 0, 0), at=(LEADSCREW_START_X, *DRIVE_AXIS_YZ)))
    screw = ZScrew(turn=Revolute(axis=(0, 0, 1), at=lambda parent: (parent.side * 17, 0, 0)))
    gear = WristGear(turn=Revolute(axis=wrist_axis, at=wrist_anchor, unit='deg'))

- A joint passed as a declaration keyword declares a freedom on the
  child (it is not a wiring, which binds one), resolved on the child
  like a wiring is today, stated in the declaring parent's frame.
  Callables are evaluated against the REALIZED parent, so a parent's
  flag or handedness can enter.
- The same keyword is accepted where a loop constructs children from
  data (OpenVMP's `StepPart` per `.assy` entry), and a relation can
  reach such a child by its realized name. This is the data-built joint
  finding; it is the same mechanism seen from `render()`.
- A class-declared joint of the same name and a site-declared one:
  the site wins, the way a redeclared port wins (to be confirmed by the
  proposer against ADR-093's slot rule).

Validation project: Prusa i3 Z screws; OpenVMP drive train; InMoov
wrist group; Poseidon and OMX cleanup.

### 3.4 Cycle 4 — a whole-tree fixpoint, and two riders

Today: relations are solved per instance at the end of its own simulate
phase, children after parents (couplings spec, "Within one pass the
order SHALL be declaration order"); `UnreachedCoordinate` is raised at
the end of a node's own fixpoint. `clear_solved()` runs before the
author's `simulate()` and the fixpoint after it.

Ratified:

- A parent's fixpoint DEFERS an unreached relation until its descendants
  have solved, then re-runs once over the tree; `UnreachedCoordinate` is
  raised only when the whole tree's fixpoint leaves a relation unreached.
  This makes clock 01's `centre.drives(third)` in `Train`, OpenTorque's
  single 1:8 statement and OpenFlexure's root sentence
  `z_axis.actuator.column.travel.drives(body.lower_strut.swing, law=...)`
  work as written.
- A node's own derived coordinate read inside its own `simulate()` is
  REFUSED by name (the read names the coordinate and states the
  two-phase order), never an empty slot that turns nothing.
- Rider (a): a subclass may REPLACE a named relation of its base, the
  way a redeclared port wins. The relation's name is the attribute it
  was assigned to; an unnamed relation is additive as today.
- Rider (b): an author-bound joint whose coordinate keeps its value
  between runs while its motion is swept. Ratified fix: the value is
  cleared with the swept motion (or the read of a stale value is
  refused by name; the proposer chooses and says why), so the
  `if value is None: bind` guard behaves on the second render exactly
  as on the first. Proof: Prusa i3's second-render pose comparison
  (37.5, 70.4, 0.05 mm today) goes to 0; hangprinter's winch guard
  covered by a test with a non-zero default.

Validation project: OpenFlexure (root sentence restored, legs from a
multi-source law after cycle 5); clock 01's chain back into `Train`;
OpenTorque preview; Prusa i3 and hangprinter second render.

### 3.5 Cycle 5 — multi-source and multi-target laws

Ratified:

    (count, next_count).drives(sautoir.pawl.swing, law=pawl_deflection)
    (x, y, z).drives((rod.spin, rod.lean, rod.swing, rod.rise), law=delta_rod)
    (x, y, z).drives((rods.spin, rods.lean, rods.swing, rods.rise), law=delta_rod)   # fan-out, cycle 1

- A tuple of coordinates on the source side; the law is handed all
  sources in the order written (plus the driven node, as today).
- A tuple on the driven side; the law returns one value per driven end
  in the order written. Ratified over four closures because four
  closures are a cost of comprehension and tokens (pilot, 2026-09-10).
- One direction only: a multi-source or multi-target relation is never
  inverted, like any non-affine law; asked to, the solver refuses by
  name. Under fan-out the law sees the copy, as in cycle 1.
- The existing refusal of a bare node with several joints as an end
  stays: ends are coordinates, named one by one.

Validation project: kossel stage B (needs cycles 1 and 5, and 2 for
the rods' anchors); the Pascaline's pawl; OpenFlexure's four legs.

## 4. Folded, not cycles

- **Bare number + dimensioned token.** Keep the refusal — a bare number
  has no unit and refusing it is the algebra's point — and sharpen the
  message to name the wrap (`Length(27.0)`). Rides in whichever cycle
  first touches `solid_node/node/parameters.py`, else the last.
- **Dotted reader** — cycle 1, §3.1.
- **Data-built children** — cycle 3, §3.3.

## 5. Discipline for this campaign (pilot, 2026-09-10)

One worktree, `solid-node/WTs/motion-catalogue-2` (branch of the same
name, base main 5b28510, slot 4), cycles sequential and stacked, each
fast-forwarded into main after review. An Opus subagent proposes each
framework cycle and a Sonnet subagent implements it; for each project
resumed against an integrated cycle, ONE Sonnet subagent both proposes
and implements stage B; the orchestrating session reviews every
proposal before the planning commit and every implementation before
sync and archive, and that review is the ratification gate. Every agent
runs at high reasoning and is given the empirical evidence (the finding,
the project's sentence, the pose-comparison tool). One heavy test
process at a time. Nothing is pushed.
