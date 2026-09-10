# ADR-095: A Free Joint Owns Six Coordinates

**Status:** Accepted (the open question of which frame `at` and the translation read is closed by [ADR-097](./ADR-097-a-joint-is-stated-in-the-frame-of-whoever-declares-it.md): the declaring body's own rest frame; everything else below stands)
**Date:** 2026-09-10
**Extends:**
- [ADR-088: A joint owns one coordinate](./ADR-088-a-joint-owns-one-coordinate.md)
**Depends on:**
- [ADR-093: The joints of one class compose in declaration order](./ADR-093-joints-of-one-class-compose-in-declaration-order.md)
**Related:**
- [ADR-094: An orbit carries a point, and derives its radius](./ADR-094-an-orbit-carries-a-point-and-derives-its-radius.md)
- [ADR-089: `drives` relates two coordinates](./ADR-089-drives-relates-two-coordinates.md)
**OpenSpec change:** `free-joint`

## Context and Problem Statement

ADR-088 gave the framework one shape of joint: **one joint, one
coordinate**. `Joint.__init__` built `self.coordinate`, `declared_ports`
reported it under the joint's own name, and three separate seams —
`ports.declared_ports`, `couplings._coordinate_of` and
`declarative._coordinate_of` — all duck-typed on that singular
attribute.

A walking robot's chassis does not fit it. It has no parent to be
jointed to: it floats, six freedoms against the ground, of which the
hexapod uses four. The motion layer's own design record
(`workflow/archive/motion-layer-2026-09-09/joints-and-couplings.md`)
listed `Free` as "native joint, later" and said why:

> Free is what a walking robot's body sits on and has no composition.

What `projects/Robots/hexapod_spiderbot_model/simulation/spiderbot.py`
writes today, at lines 278-284, is the chassis pose applied by hand from
the root's `simulate()`:

```python
(self.chassis
 .rotate(self.roll, [1, 0, 0])
 .rotate(self.pitch, [0, 1, 0])
 .rotate(self.yaw, [0, 0, 1])
 .translate([0.0, 0.0, self.height]))
```

and `Chassis._to_chassis` (lines 146-163) hand-inverts exactly that
composition to bring a foot target on the ground into the chassis's
frame, so every leg solution in the model depends on it. ADR-093 already
lets the same machine be written as four joints in declaration order;
what four declarations plus four forwarding `SignalPort`s cannot say is
that this is ONE floating body. Neither MuJoCo's `free` nor Modelica's
`Joints.FreeMotion` says it that way, and the design record names both as
the targets this layer is meant to fit.

**No project asked for a `Free`.** One project has a floating body and
its reviewed proposal asked for four joints. This is the framework's own
choice, made because the two export targets each have one element for it
and because six freedoms on one body read better as one declaration; it
should be read as a framework choice, not as an empirical requirement.

## Decision Drivers

- One declaration for one floating body, and one entry in the
  declaration order ADR-093 composes by.
- A composition equal to what the hexapod hand-inverts, established by
  measurement before it was written rather than asserted afterwards.
- The smallest naming rule that lets `declared_ports`, `drives` and a
  relation path reach a coordinate that is not the whole joint.
- No change to how `Revolute`, `Prismatic` or `Orbit` place a body, and
  no change to the document, the CLI, the viewer or the parity corpus.
- Every "one coordinate" seam must REFUSE a joint that is several rather
  than mis-handle it.

## Considered Options

1. **`Free(at, angle_unit, length_unit)` owning six coordinates named
   `<joint>.<coordinate>`.** Chosen.
2. **Six bare names on the node** (`roll`, `pitch`, … reported
   unqualified). Rejected by the hexapod itself: its `Chassis` already
   declares `roll`, `pitch` and `yaw` as `SignalPort`s
   (`spiderbot.py:85-92`), so a `Free` claiming those names would
   collide with the very class it exists for.
3. **An underscore instead of a dot** (`pose_roll`). Rejected: it would
   be a legal keyword but a DIFFERENT name from the one the attribute
   read gives (`chassis.pose.roll`), so a coordinate would have two
   spellings and a refusal would have to guess which one was meant.
4. **A dotted WIRING keyword**, `Chassis(**{'pose.roll': roll})`.
   Measured to work — Python accepts a non-identifier `**` key and it
   reaches `ChildDeclaration._check_wiring` intact
   (`evidence/probe_wiring_keyword.py`) — and deliberately not offered:
   it would be the first non-identifier keyword in the API, it is
   unreadable at the call site, and no project asked for it.
5. **Four joints, as ADR-093 already allows.** Not rejected: it stays
   legal and correct, and it is what the hexapod writes today. What it
   cannot say is that the four are one body.
6. **A quaternion-valued `Free`.** Deferred, not decided; see
   Consequences.

## Decision Outcome

**`Free(at=(0, 0, 0), angle_unit='deg', length_unit='mm')`**, a fourth
declaration exported from `solid_node.motion.joints`, and the first joint
that owns more than one coordinate.

- **Six coordinates**: `roll`, `pitch` and `yaw`, rotational, carrying
  `angle_unit`; `x`, `y` and `z`, translational, carrying `length_unit`.
  Two unit labels because a joint's `unit` has always been "the label the
  coordinate carries", and with coordinates in two domains one label
  cannot serve.
- **The naming rule.** A joint owning ONE coordinate names it after the
  joint (unchanged). A joint owning SEVERAL names each
  `<joint name>.<coordinate name>` — `pose.roll`. That one string is the
  port's own `name`, the key `declared_ports` reports it under, and the
  tail of a relation path. There is no second spelling. It is not a
  Python identifier, so **an enumerated port name is no longer
  guaranteed to be one**, and a consumer reaches a coordinate by the name
  the enumerator reports rather than by `getattr` on the node.
- **Read on an instance, a `Free` yields a view** of the node's own six
  slots: `chassis.pose.roll` is that coordinate's `BoundPort` exactly as
  `wheel.turn` is a `Revolute`'s, and assigning to it binds through the
  one binding path and re-places the body. Assigning to the joint itself
  is refused by name, listing the six.
- **`coordinate` is ABSENT on a `Free`**, deliberately: anything reading
  it without checking gets an `AttributeError` rather than a wrong
  answer. `Joint` grows the general form, an ordered `coordinates`
  mapping of full name to port, which for a one-coordinate joint is
  `{name: coordinate}`.
- **No `axis`** — a free body turns about three directions, and they are
  the frame's own rather than an author's choice — and **no `range`**: a
  floating body has no travel to bound. Both are refused at the
  declaration, naming what a `Free` does take.
- **`at` keeps the meaning it has on every other joint**: a point in the
  PARENT's frame, defaulting to that frame's origin, resolved against the
  instance at realization, carried into the body's own frame by inverting
  the rest placement. It is the point the three rotations pass through.

**The composition is fixed by the contract**, innermost first, about the
carried anchor:

    R(roll, x̂) · R(pitch, ŷ) · R(yaw, ẑ) · T(x, y, z)

read as an APPLICATION order — the roll closest to the body, the
translation outermost — which as a matrix product acting on a point of
the body is `T · R_ẑ(yaw) · R_ŷ(pitch) · R_x̂(roll)`. The three
directions are the parent frame's own x̂, ŷ and ẑ, carried into the
body's frame through the SAME single inversion the anchor rides and
snapped to exact 0/±1, so the three angles are an **extrinsic x-y-z**
sequence — the same rotation the aircraft convention states as intrinsic
yaw, then pitch, then roll.

The run is up to SIX operations at ONE declaration slot: the centring
pair when the carried anchor is non-zero, the three rotations, and one
translation outermost. **An unbound coordinate places nothing** — no
rotation, and a plain numeric `0` in the component its direction reaches
— while still READING as unbound. That is not an exception to "an unbound
coordinate reads as unbound rather than as zero": the read is unchanged,
and "an unbound coordinate places nothing" is the rule an unbound
`Revolute` already obeys by never being placed at all. Only a free joint
has to state it, because its placement RUNS while some of its
coordinates are unbound — binding any of the six re-places the whole
joint from the values the six then hold, which is what makes six
coordinates one joint and why the composition never depends on the order
they were bound in.

**The three seams**, each measured on the tree before it was changed
(`openspec/changes/free-joint/evidence/probe_multi_coordinate_seams.py`):

| Seam | What it did with a six-coordinate joint | What it does now |
|---|---|---|
| `ports.declared_ports` | reported **nothing at all** for it | prefers a `coordinates` mapping whose keys are already full names, falling back to the singular `coordinate` for a derived coordinate |
| `couplings.read_through` / `PathRef` | raised the *parameter* refusal, `SidewaysReadError: … a sibling's parameter is not a value in a class body` | steps into the joint for one of its coordinates; `PathRef._walk` pops as many segments as the coordinate's name has parts; stopping on the joint, naming a part it does not own, or naming a node whose one joint is a `Free`, is refused listing the six |
| `ResolvedEnd.bind` / `Wiring.apply` | `setattr(node, 'pose.roll', v)` **silently created an instance attribute and bound nothing** | both bind through `ports.set_coordinate(node, name, value)`, which splits on the last dot |

`declarative._coordinate_of`/`_is_joint` learn the same seam, so a `Free`
passed whole as a child keyword is refused as a wiring source instead of
being taken for a parameter, and a name declared as both a `Free` and a
port is refused instead of the last assignment silently winning.

**Serialization is unchanged**: three ordinary rotations and one ordinary
translation, values carried unresolved, a plain `0` where no bound
coordinate reaches. No new document key and no new operation kind.

## Consequences

- **The composition was measured before it was written.** The hexapod's
  four hand-written operations equal `T · Rz · Ry · Rx` to **1.11e-16**
  over seven poses, two of them at gimbal lock, and `_to_chassis` inverts
  the same product to **1.42e-14 mm** over a probe point 100 mm out
  (`evidence/probe_matrix.py`, run before the proposal). The real `Free`
  reproduces that product to **1.11e-16** on an identity rest placement —
  the hand-written equivalent's own number — and to **2.84e-14** on a
  fixture whose parent both turns and moves the body, and the project's
  own `_to_chassis`, transcribed unchanged, round-trips the framework's
  placement to **1.42e-14 mm**, which is again the hand-written
  equivalent's number (`evidence/probe_free_matrix.py`).
- **A dotted name is a new kind of string in the port namespace.** Every
  consumer that assumed a port key is a Python identifier is now wrong
  where a `Free` is declared. The in-framework consumers are all changed
  here; `solid_node/node/flexible.py` still does
  `getattr(self, name)` over `declared_ports`, so a `Free` on a
  FLEXIBLE node would raise an `AttributeError` there. No node can be
  both today and none is; recorded rather than fixed blind.
- **Gimbal lock is real and inherited.** At `pitch = ±90°` roll and yaw
  are degenerate. The design record made `Spherical` quaternion-valued
  for exactly this reason and accepted Euler angles for `Free` anyway.
  The fixture includes `pitch = 90°` and `roll = 90°` poses, so the
  degenerate case is on the record as a measurement and as a picture
  rather than as an omission. Whether `Free`'s three angles should be a
  quaternion, and what a driver would then bind, is **open**.
- **The export mapping is open**, and `Free` is the joint where both
  targets have a native element, so it is the cheapest one to get wrong
  by guessing.
- **Whether `at` is read in the parent's frame or the body's own is
  open.** The hexapod cannot tell them apart: its chassis has an identity
  rest placement, so both readings give the same answer at every pose.
  The rule chosen is the parent's frame, by consistency with ADR-088, and
  the spec states it as a rule rather than as something the hexapod
  proved. A consequence worth seeing: a `Free()` with the DEFAULT anchor
  on a body its parent moves turns about the PARENT's origin, and emits
  the centring pair, exactly as a `Revolute` with a default `at` would.
- **The three translational coordinates displace along the three CARRIED
  directions**, the way a `Prismatic`'s value runs along its carried
  axis. On the identity rest placement — every case the evidence has —
  that is `translate([x, y, z])` verbatim, with a plain `0` per unbound
  component, which is what the spec states. The design did not say which
  frame the components are read in where the two differ; the reading
  chosen is the one the change's own acceptance test states (the anchored
  fixture equals the parent-frame product conjugated by its rest
  placement), and it is what makes a floating body float against the
  parent's frame rather than its own.
- **Six coordinates re-place on every binding.** Binding all six runs the
  placement six times, each rebuilding up to six operations and one 4×4
  inversion. Not a new cost per binding — every joint of every node
  re-inverts on every run today — but a 6× one for a floating body.
  Unmeasured; no bench exists.
- **Cycles 1 and 2 hold over the hardest joint the contract has.** A
  `Free` between a `Prismatic` and an off-origin `Revolute`, bound in
  scrambled orders with a hand-written rotation in the middle, keeps its
  five-operation run unbroken at its own slot, and a `Free` declared
  before an `Orbit` keeps the orbit's single translation outside it. No
  cycle-1 or cycle-2 test was edited.
- **Nothing existing moved.** No existing declaration, pose, document or
  test changes; the seams grow branches rather than changing behaviour
  for a one-coordinate joint, and the whole suite is green.
- **The hexapod's stage B is unblocked but not done.** It becomes one
  declaration plus four bindings in its own repository's own cycle. It
  was already refactorable under ADR-093, so nothing that was blocked
  after cycle 1 is unblocked by this one.
