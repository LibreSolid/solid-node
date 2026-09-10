## Why

A walking robot's chassis has no parent to be jointed to. It floats: six
freedoms against the ground, of which a hexapod uses four. Nothing in the
framework says that. The motion layer's own design record
(`workflow/archive/motion-layer-2026-09-09/joints-and-couplings.md`, the
pair table) listed `Free` as "native joint, later" and said plainly why:

> Free is what a walking robot's body sits on and has no composition.

The gap is recorded in `workflow/warts.md` under the hexapod's entry
(lines 815-836), which cycle 1 closed only halfway:

> **FIXED for the composition half (cycle `joint-composition-order`,
> ADR-093). A floating body's attitude is the same composition gap, from
> the other side.** … The four-declaration form above is exactly what the
> contract now guarantees, so the hexapod is unblocked by ADR-093. The
> `Free` joint it may still prefer is a separate, unbuilt primitive and
> stays open.

What the hexapod writes today, in
`projects/Robots/hexapod_spiderbot_model/simulation/spiderbot.py:278-284`,
is the chassis pose applied by hand from the root's `simulate()`:

```python
(self.chassis
 .rotate(self.roll, [1, 0, 0])
 .rotate(self.pitch, [0, 1, 0])
 .rotate(self.yaw, [0, 0, 1])
 .translate([0.0, 0.0, self.height]))
```

and `Chassis._to_chassis` (`spiderbot.py:146-163`) hand-inverts exactly
that composition to bring a foot target on the ground into the chassis's
frame, so every leg solution in the model depends on it. Stated as four
separate joints — the form ADR-093 now guarantees — it costs the class
four declarations plus four more `SignalPort`s to carry the same numbers
down, and it says *four independent freedoms* where the machine has *one
floating body*. Neither MuJoCo nor Modelica says it that way: MuJoCo's
`free` and Modelica's `Joints.FreeMotion` are one element each, and the
design record names both as the targets this layer is meant to fit.

Measured, not assumed (`evidence/probe_matrix.py`, seven poses including
two at gimbal lock):

- the framework's composition of those four hand-written operations
  equals `T(0,0,h) · Rz(yaw) · Ry(pitch) · Rx(roll)` to a maximum
  absolute deviation of **1.11e-16**;
- `Chassis._to_chassis` is the exact inverse of that same transform, to
  **1.42e-14 mm** over a probe point 100 mm out.

So the composition a `Free` must produce is settled by measurement before
a line of it is written.

## What Changes

- **`Free(at=(0, 0, 0), angle_unit='deg', length_unit='mm')`**, a fourth
  declaration exported from `solid_node.motion.joints`. It is the first
  joint that owns **more than one coordinate**: six, reachable as
  attributes of the joint read on an instance — `chassis.pose.roll`,
  `.pitch`, `.yaw` (rotational, `angle_unit`) and `chassis.pose.x`,
  `.y`, `.z` (translational, `length_unit`).
- **Each of the six is an ordinary coordinate.** Bindable by assignment,
  nameable as either end of `drives` by its dotted path, readable by a
  driver or an expression, published like any other bound value. Nothing
  about a `Free` coordinate is special except where it is *named* — and
  one thing it is deliberately NOT: a wiring target (see Non-goals).
- **The naming rule.** A joint owning ONE coordinate keeps reporting it
  under the joint's own name (unchanged). A joint owning several reports
  each under **`<joint name>.<coordinate name>`** — one dot. For
  `pose = Free(...)` the six names are `pose.roll`, `pose.pitch`,
  `pose.yaw`, `pose.x`, `pose.y`, `pose.z`, in that order. That one name
  is the port's `name`, the key in `declared_ports`, and the tail of a
  relation path.
- **The composition is fixed by the contract**, innermost first, about
  `at`: `R(roll, x̂) · R(pitch, ŷ) · R(yaw, ẑ) · T(x, y, z)` — read as an
  application order, which as a matrix product is
  `T · R_ẑ(yaw) · R_ŷ(pitch) · R_x̂(roll)`, the product measured above.
  The three directions and the anchor are read in the PARENT's frame and
  carried into the body's own by inverting the rest placement, exactly as
  a `Revolute`'s `axis` and `at` are. It is one contiguous run at one
  declaration slot, so ADR-093's contract covers it unchanged.
- **An unbound coordinate contributes no motion** — angle 0, offset 0 —
  while still *reading* as unbound, which is the same rule an unbound
  `Revolute` already obeys: an unbound coordinate places nothing. The
  hexapod binds four of six.
- **No `range` on a `Free`**: a floating body has no travel to bound.
- **Naming the joint itself, or a node whose only joint is a `Free`, as
  a relation end is refused by name, listing the six.** The "a node
  stands for its ONE joint" rule is unchanged; it simply does not apply
  to a joint that is not one coordinate.
- **Non-goal: a `Free` coordinate is not reachable by a WIRING keyword.**
  `Chassis(**{'pose.roll': roll})` would be the first non-identifier
  keyword in the API, it is unreadable, and no project asked for it.
  Passing the joint whole (`Chassis(pose=pose)`) and passing a dotted
  name are BOTH refused at class definition, naming the joint, listing
  the six and saying they are bound by assignment or by relation. A
  project that later wants a `Free` coordinate wired downward is a new
  sighting, not a gap this cycle leaves open.
- **Serialization is unchanged**: three ordinary rotations and one
  ordinary translation, values carried unresolved, zero components a
  plain `0`. Verified by probe before this proposal was written
  (`evidence/probe_serial.py`); no new document key and no new operation
  kind.

Three seams have to change to carry a dotted coordinate name, and each
was **measured on the current tree** rather than assumed
(`evidence/probe_multi_coordinate_seams.py`):

| Seam | Today, with a six-coordinate joint | Why |
|---|---|---|
| `declared_ports` (`solid_node/motion/ports.py:338-366`) | reports **nothing at all** for it — measured: `declared_ports : []` | the duck-typed seam is the singular `coordinate` attribute |
| `read_through` (`solid_node/motion/couplings.py:488-536`) | raises the wrong refusal — measured: `SidewaysReadError: cannot read 'pose' off the Chassis declaration … a sibling's parameter is not a value in a class body … Chassis declares: no port, joint or child` | `_coordinate_of` returns None, so the joint falls through to the parameter branch |
| `ResolvedEnd.bind` / `Wiring.apply` (`couplings.py:934-951`, `1090-1094`) | `setattr(node, 'pose.roll', value)` **silently creates an instance attribute** — measured: `'turn.roll' in node.__dict__ is True` | the binding seam assumes a name that is a plain attribute |

## Capabilities

### New Capabilities

(none — `Free` is a fourth declaration inside the existing `joints`
capability, not a new one)

### Modified Capabilities

- `joints`: "One-coordinate joint declarations" is RENAMED to "Joint
  declarations" and gains `Free` and its signature; "A joint owns one
  coordinate, and that coordinate is a port" is RENAMED to "A joint owns
  one or more coordinates, and each is a port" and gains the six
  coordinates, the dotted naming rule and the refusal to bind the joint
  as a whole; "Binding a joint places the body" gains the free joint's
  placement and its unbound-is-identity rule; "Joint arguments resolve
  against the instance at realization" gains a `Free`'s `at` and its
  absent `axis` and `range`; "A joint takes part in a relation" gains the
  two refusals for a joint that is not one coordinate.
- `ports`: "Domain-typed ports" gains the dotted enumeration rule for a
  joint that owns several coordinates; "A coordinate may be wired down to
  a child declaration" states that a wiring keyword is an identifier and
  refuses a joint owning several coordinates in either wiring role —
  passed whole, or named by the dotted name of one of its coordinates.
- `couplings`: "Each end of a relation resolves to one coordinate" gains
  the path grammar for a coordinate whose name has more than one segment,
  and the refusal for a path that stops on a multi-coordinate joint.

The `node-model` and `simulation` specs are not changed.

## Impact

- `solid_node/motion/joints.py` — a new `Free` class; `Joint` grows a
  `coordinates` mapping (the general form of `coordinate`) and an `axes`
  hook beside the existing `carried_points`; `_carry` generalized to
  carry several axes through the one inversion it already computes.
  `Revolute`, `Prismatic` and `Orbit` place their bodies with the same
  code as before.
- `solid_node/motion/ports.py` — `declared_ports` reads the new
  `coordinates` seam; a `set_coordinate(node, name, value)` helper that
  binds through a dotted name.
- `solid_node/motion/couplings.py` — `read_through` and
  `PathRef.__getattr__` step into a multi-coordinate joint;
  `PathRef._walk` pops as many segments as the coordinate's name has
  parts; `_the_one_joint` refuses a multi-coordinate joint by name;
  `ResolvedEnd.bind` and `Wiring.apply` bind through `set_coordinate`.
- `solid_node/node/declarative.py` — its local `_coordinate_of`/`_is_joint`
  learn the same seam, so a `Free` passed whole as a child keyword is
  refused as a wiring source instead of being taken for a parameter, a
  dotted wiring keyword is refused by the same message rather than by
  "declares no port or joint of that name", and a name declared as both a
  `Free` and a port is still refused.
- `tests/test_joints.py`, `tests/test_couplings.py`, `tests/test_ports.py`
  — a new section for the free joint, the hexapod's matrix at seven poses
  as a fixture, and a `Free` added to the cycle-1 and cycle-2 composition
  fixtures so ADR-093's contract is proved over a joint that places four
  operations and owns six coordinates.
- `docs/api-reference.rst` (Joints), `docs/driving.rst` (a passage with
  the hexapod chassis as the example), `docs/changelog.rst` `Unreleased`,
  `docs/architecture.md` §Joints, and a new ADR-095 under
  `docs/adrs/NODE/` with its index row.
- `workflow/warts.md` — the hexapod's floating-chassis half marked fixed.
- `workflow/docs/composed-joints.md` §6 and §7 — §6 marked taken up, open
  questions 7 and 8 closed, 9 carried.
- **Downstream, not in this cycle:** the hexapod's chassis becomes one
  declaration at stage B; it is already refactorable under ADR-093, so
  nothing is unblocked by this cycle that was blocked after cycle 1.
- No CLI, no document format, no viewer, no serialization change; nothing
  is deprecated, and no existing project's pose moves.
