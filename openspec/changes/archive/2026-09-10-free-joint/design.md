## Context

Cycle 3 of the composed-joints campaign, on top of `joint-composition-order`
(ADR-093) and `orbit-joint` (ADR-094). The working note is
`workflow/docs/composed-joints.md` §6; the empirical entry is
`workflow/warts.md` lines 815-836; the design record that reserved the
primitive is `workflow/archive/motion-layer-2026-09-09/joints-and-couplings.md`
§1, whose pair table lists `Free | 6 | native joint, later | free |
Joints.FreeMotion`.

The framework today has exactly one shape of joint: **one joint, one
coordinate**. `Joint.__init__` (`solid_node/motion/joints.py:169-183`)
builds `self.coordinate = self.coordinate_kind(unit=self.unit)`;
`declared_ports` (`ports.py:338-366`) reports it through the duck-typed
`coordinate` attribute; `couplings._coordinate_of` (`couplings.py:92-101`)
reads the same attribute; `declarative._coordinate_of`
(`declarative.py:71-81`) states it a third time to avoid an import cycle.
`Free` is the first declaration that breaks that shape, and everything in
this design follows from deciding how a *second* coordinate of one joint
gets a name.

## Goals / Non-Goals

**Goals**

- One declaration for a floating body, with six coordinates that behave
  like every other coordinate in the layer.
- A composition fixed by the contract and equal to what the hexapod
  hand-inverts, proved by matrix comparison rather than by assertion.
- One contiguous run at one declaration slot, so ADR-093 is unchanged.
- The smallest naming rule that lets `declared_ports`, `drives` and a
  relation path reach a coordinate that is not the whole joint.

**Non-Goals**

- `Spherical`. It is the other half of the design record's "native joint,
  later" row and it needs a quaternion; nothing here decides it.
- A quaternion-valued `Free`. Open question 9, carried.
- A `range` on a `Free`. Open question 8, closed as *none*.
- Exporting a `Free` to MuJoCo or Modelica. The mapping is named in the
  open questions and designed nowhere.
- Any change to how `Revolute`, `Prismatic` or `Orbit` place a body.
- **A wiring keyword for a `Free` coordinate.** `Chassis(**{'pose.roll':
  roll})` would be the first non-identifier keyword in the API, it is
  unreadable, and no project asked for it. Both wiring roles are refused
  by name (§2). A project that later wants one is a new sighting.

## Decisions

### 1. The declaration

```python
pose = Free(at=(0, 0, 0), angle_unit='deg', length_unit='mm')
```

No `axis`: a free body turns about three, and they are the frame's own
x̂, ŷ, ẑ, not something an author chooses. No `range`. Two units, because
three of the coordinates are angles and three are lengths, and a joint's
`unit` has always been "the label the coordinate carries" — with six
coordinates in two domains, one label cannot serve.

`at` keeps the meaning it has on every other joint: a point in the
PARENT's frame, defaulting to that frame's origin, carried into the
node's own frame by inverting the rest placement. It is the point the
three rotations pass through.

The hexapod's chassis has NO rest placement of its own — `Chassis`
declares `body` and `legs` and its `render()` places only its children;
the root applies the pose to it as motion — so the inversion is the
identity and `at=(0, 0, 0)` is both the parent's origin and the body's
own placed origin. **The evidence therefore does not distinguish "the
parent's frame" from "the body's own frame" for this argument.** The rule
chosen is the parent's frame, because that is what ADR-088 says about
every joint argument and a second rule for one joint would be a trap.
Recorded as a limit of the evidence, not as a thing the hexapod proved.

### 2. The six coordinates and their names

Six ports, created by the declaration exactly as `Joint.__init__` creates
one today:

| name | kind | unit |
|---|---|---|
| `<joint>.roll` | `RotationalPort` | `angle_unit` |
| `<joint>.pitch` | `RotationalPort` | `angle_unit` |
| `<joint>.yaw` | `RotationalPort` | `angle_unit` |
| `<joint>.x` | `TranslationalPort` | `length_unit` |
| `<joint>.y` | `TranslationalPort` | `length_unit` |
| `<joint>.z` | `TranslationalPort` | `length_unit` |

**The naming rule, stated once and obeyed everywhere.** A joint's
coordinate is named `<joint name>` when the joint owns one, and
`<joint name>.<coordinate name>` when it owns several. That single string
is:

- the port's own `name`, set in `__set_name__` exactly as a
  one-coordinate joint sets its coordinate's name today
  (`joints.py:200-203`);
- the key `declared_ports` reports it under;
- the tail of a relation path: `chassis.pose.roll`.

It is deliberately **not** a wiring keyword. Measured
(`evidence/probe_wiring_keyword.py`): Python does accept a non-identifier
string as a `**` key and it reaches `ChildDeclaration._check_wiring`
intact, so `Chassis(**{'pose.roll': roll})` *could* be made to work — and
is not, because it would be the first non-identifier keyword in the API,
it is unreadable at the call site, and no project asked for it. Both
wiring roles are refused at class definition, naming the joint and
listing the six: passing the joint whole (`Chassis(pose=pose)`), and
naming one of its coordinates by the dotted name. What reaches such a
coordinate instead is an assignment on the instance
(`chassis.pose.roll = …`), a relation (`chassis.pose.roll` at either end
of `drives`), and a driver or an expression through those.

Alternatives rejected:

- **Six bare names on the node** (`roll`, `pitch`, … reported unqualified).
  Refused by the hexapod itself: `Chassis` already declares
  `roll = SignalPort(unit='deg')`, `pitch`, `yaw`
  (`spiderbot.py:85-92`). A `Free` that claimed those names would collide
  with the very class it exists for.
- **An underscore instead of a dot** (`pose_roll`). It would be a legal
  Python keyword, but it would be a *different* name from the one the
  attribute read gives (`chassis.pose.roll`), so a coordinate would have
  two spellings and a refusal would have to guess which one the author
  meant. Note that the dotted name being unusable as a keyword is
  precisely what this cycle accepts rather than works around: the wiring
  route is closed, not re-spelled.

### 3. `Joint` grows `coordinates`; `coordinate` stays for the ones that
have one

`Joint` gains an ordered mapping `coordinates: {full name -> Port}`. A
one-coordinate joint's is `{self.name: self.coordinate}`; a `Free`'s has
six entries. `coordinate` stays exactly what it is for `Revolute`,
`Prismatic` and `Orbit` and is **absent** on a `Free`, which is what
makes every "one coordinate" seam refuse a `Free` rather than
mis-handle it.

`declared_ports` prefers the new seam:

```python
owned = getattr(value, 'coordinates', None)      # a joint of any arity
if isinstance(owned, dict): ports.update(owned)  # keys are already full names
elif isinstance(getattr(value, 'coordinate', None), Port): ...  # derived coords
```

Still duck-typed, still no `isinstance(Joint)`, so `ports` still does not
import `joints` (`ports.py:346-353` states why). A derived coordinate
keeps the singular `coordinate` seam it has today and is untouched.

The same seam is added to `declarative._coordinate_of`/`_is_joint`
(`declarative.py:71-81`), which is not decoration: without it a `Free`
passed whole as a child keyword — `Chassis(pose=pose)` — is not
recognised as a coordinate and is silently taken for a **parameter**,
reaching the child's constructor; and `_refuse_coordinate_clash`
(`declarative.py:342-361`) returns early, so a class declaring `pose` as
both a `Free` and a port keeps whichever came last with no sign of the
other. Both are refused by name instead.

### 4. The placement

Read on an instance, `chassis.pose` yields a small **bound-coordinates
view** holding the node and the joint: reading `.roll` gives that
coordinate's `BoundPort` (so `chassis.pose.roll.value` reads exactly like
`wheel.turn.value`), and assigning `.roll` binds through `bind()` and
then re-places the body. Assigning `chassis.pose` itself is refused by
name, listing the six.

Re-placing on every binding is what makes six coordinates one joint: any
of the six changing rebuilds the whole run, from whatever the other five
currently hold. `Joint.clear` (`joints.py:352-366`) already drops the
previous run by recorded identity and tolerates a sweep having dropped
it, so the mechanism is the one that exists.

The run, in list order — which is application order, innermost first,
because `_carry` and `_compose_world_matrix` premultiply
(`matrix = operation.matrix() @ matrix`, `joints.py:395-410`):

1. `Translation(-anchor)` — only when the carried anchor is non-zero;
2. `Rotation(roll, x̂_local)` — only when `roll` is bound;
3. `Rotation(pitch, ŷ_local)` — only when `pitch` is bound;
4. `Rotation(yaw, ẑ_local)` — only when `yaw` is bound;
5. `Translation(anchor)` — only when the carried anchor is non-zero;
6. `Translation([x, y, z])` — only when at least one of the three is
   bound; an unbound component is a plain numeric `0`, for the reason
   `Prismatic`'s is (`joints.py:611-620`): an expression multiplied by
   zero would put `$t`-shaped noise in two of three slots of every
   floating body's published document.

Up to **six** operations, not four. The settled direction said "up to
four operations"; that is right for `at` at the body's own placed origin,
which is the hexapod's case and the default, and the two centring
translations appear for a non-origin anchor exactly as a `Revolute`'s do
(`joints.py:571-583`). Stated here rather than reconciled quietly: it is
still ONE contiguous run at ONE slot, which is all ADR-093 asks.

x̂_local, ŷ_local, ẑ_local are the parent frame's three unit directions
carried into the node's own frame through the same single inversion the
anchor rides, and snapped to exact 0/±1 by `_snapped`. `Joint._carry`
takes one axis today; it is generalized to take a tuple, through a new
`axes(node)` hook that returns `(self.arguments(node)[0],)` for every
existing joint and the three unit directions for a `Free`. That mirrors
what cycle 2 did for points (`carried_points`, `joints.py:368-376`) and
keeps the one-inversion invariant.

Because the axes are fixed directions of the parent's frame rather than
the body's rotating axes, the three angles are an **extrinsic x-y-z**
sequence, which is the same rotation as the intrinsic yaw-pitch-roll
(z-y'-x'') convention an aircraft uses. That is what the hexapod means by
roll, pitch and yaw, and it is what its inverse computes.

### 5. The composition, measured against the hexapod before it is written

`evidence/probe_matrix.py`, run on this worktree, composes the four
operations the hexapod applies by hand and compares them with a NumPy
product, at seven poses including `pitch=90°` and `roll=90°`:

```
roll=      0 pitch=     0 yaw=      0 h=      0  ops-vs-numpy=0.000e+00  to_chassis-roundtrip=0.000e+00
roll=     12 pitch=     8 yaw=     25 h=    165  ops-vs-numpy=0.000e+00  to_chassis-roundtrip=0.000e+00
roll=    -15 pitch=   -15 yaw=      0 h=     70  ops-vs-numpy=0.000e+00  to_chassis-roundtrip=1.421e-14
roll=      5 pitch=    -3 yaw=    180 h=    120  ops-vs-numpy=8.674e-19  to_chassis-roundtrip=7.105e-15
roll=     90 pitch=     0 yaw=     45 h=    100  ops-vs-numpy=0.000e+00  to_chassis-roundtrip=3.553e-15
roll=      0 pitch=    90 yaw=     30 h=     60  ops-vs-numpy=0.000e+00  to_chassis-roundtrip=5.329e-15
roll=  -33.3 pitch=  21.7 yaw= -119.9 h= 143.25  ops-vs-numpy=1.110e-16  to_chassis-roundtrip=7.105e-15

max |framework composition - NumPy product| = 1.1102230246251565e-16
max |_to_chassis(forward(p)) - p|          = 1.4210854715202004e-14
```

So the target is `T(x,y,z) · Rz(yaw) · Ry(pitch) · Rx(roll)`, and
`Chassis._to_chassis` (`spiderbot.py:146-163`) is its inverse. The
cycle's fixture asserts the `Free`'s composed matrix against that product
at these seven poses with `atol=1e-12`, and the implementer records the
measured maximum. The prediction is ~1e-16 for the hexapod's own case,
where the rest placement is the identity and `np.linalg.inv` is exact;
the fixture with a non-trivial rest placement will be looser and its own
measured maximum is what the evidence records.

### 6. An unbound coordinate is the identity — and this is not an exception

The joints spec says a joint read on an instance is a slot whose value
"is unbound rather than zero". That is about the READ, and it is
unchanged: `chassis.pose.x.value` is `None` until something binds it, and
`declared_ports` reports it as an unbound port.

What is new is that a `Free`'s placement RUNS while some of its
coordinates are unbound, because binding `pose.roll` re-places the whole
joint. The rule chosen is the one every other joint already obeys, stated
per coordinate instead of per joint: **an unbound coordinate places
nothing.** An unbound `Revolute` applies no rotation — not because
anything decided so, but because `place` is never called for it. A
`Free`'s unbound `roll` applies no rotation for the same reason, stated
explicitly because the code now has to decide. The hexapod binds four of
six and the two it leaves alone contribute an identity, which is what a
robot that does not translate sideways means.

Open question 7 is therefore closed as IDENTITY, and the spec says it is
the same rule per coordinate rather than an exception to one.

### 7. Relation paths and the two refusals

**The path grammar.** A coordinate occupies as many trailing segments of
a relation path as its name has dot-separated parts: one for a port or a
one-coordinate joint, two for a `Free`'s coordinate. `PathRef._walk`
(`couplings.py:437-449`) pops exactly one segment today; it pops
`name.count('.') + 1` instead. Nothing else in the walk changes, and an
ordinary path behaves identically because an ordinary name has no dot.

So `chassis.pose.roll` walks to the realized `chassis` and resolves the
`pose.roll` port on it. Reaching it needs two small steps:

- `read_through(Chassis, 'pose', …)` must return the `Free`. Today it
  raises the *parameter* refusal (measured, §Why of the proposal), because
  `_coordinate_of` is None for it. It gains a branch for a joint that owns
  several coordinates, beside the branches for a port, a joint and a
  child declaration.
- `PathRef.__getattr__` (`couplings.py:418-430`) must step from that
  `Free` to `roll`. Today it raises *"cannot read 'roll' through
  wheel.turn: that path already names a coordinate, and a coordinate has
  no parts"* (measured). A joint that owns several coordinates DOES have
  parts, and an unknown part is refused by name listing the six.

**Refusal 1 — the joint itself.** `chassis.pose.drives(...)`, or
`pose.drives(...)` in the class's own body, is refused naming the six:
a relation has one end and a `Free` is six.

**Refusal 2 — the node.** `_the_one_joint` (`couplings.py:471-486`)
returns the single declared joint of a child's class. When that one joint
is a `Free`, the node does not stand for one coordinate either, and the
refusal lists the six. Note it would otherwise pass `len(joints) == 1`
and return a declaration with no coordinate — a wrong pose, not an error.

### 8. Binding through a dotted name

`ResolvedEnd.bind` (`couplings.py:934-951`) and `Wiring.apply`
(`couplings.py:1090-1094`) both bind by `setattr(node, name, value)`,
deliberately, so a relation and a wiring take the same path an author's
assignment takes. With a dotted name that call **silently creates an
instance attribute and binds nothing** — measured:
`'turn.roll' in node.__dict__ is True` after `setattr(node, 'turn.roll', 3.0)`.

A `set_coordinate(node, name, value)` helper in `solid_node.motion.ports`
splits on the LAST dot, walks the head with `getattr` and assigns the
tail, so `pose.roll` reaches the bound-coordinates view's setter and an
ordinary name behaves exactly as `setattr` does now. Both call sites use
it. It lives in `ports` because that is where `bind` lives and because it
needs nothing from `joints`.

Closing the wiring route (§2) does NOT make this helper unnecessary:
`ResolvedEnd.bind` is the relation path, and a relation binds a dotted
coordinate. `Wiring.apply` uses it too, because one binding seam is the
point — a wiring will simply never carry a dotted name past the class
definition refusal.

### 9. Serialization, verified rather than assumed

`evidence/probe_serial.py` writes the hexapod's four operations by hand,
with two of the six freedoms left at zero, and serializes:

```json
"operations": [
 ["r", "5.0", [1, 0, 0]],
 ["r", "0.0", [0, 1, 0]],
 ["r", "0.0", [0, 0, 1]],
 ["t", ["0", "0", "120.0"]]
]
```

Ordinary `r` and `t` entries, values carried as strings through the
existing unresolved-value path, a zero component the plain string `'0'`,
no new key and no new operation kind. A `Free` publishes exactly this.

### 10. What the hexapod then writes

```python
class Chassis(AssemblyNode):
    pose = Free(angle_unit='deg', length_unit='mm')

    body = Body()
    legs = Leg().repeat(6)
    ...

class Spiderbot(AssemblyNode):
    def simulate(self):
        self.chassis.pose.roll = self.roll
        self.chassis.pose.pitch = self.pitch
        self.chassis.pose.yaw = self.yaw
        self.chassis.pose.z = self.height
```

replacing the four chained calls at `spiderbot.py:280-284`. `pose.x` and
`pose.y` stay unbound; `_to_chassis` can then read `self.pose.roll.value`
instead of the forwarded `SignalPort`s. **This is stage B and belongs to
the project's own cycle, not this one.** The hexapod is already
refactorable under ADR-093, so nothing waits on this change; what it buys
is one declaration where four freedoms said four.

## Risks / Trade-offs

- **A dotted name is a new kind of string in the port namespace.** Every
  consumer that assumed a port key is a Python identifier is now wrong.
  The audit is small (the enumerator's consumers are wiring, relations
  and the class-body refusals, all touched here), but a project's own
  tooling that iterates `declared_ports` and calls `getattr` will break
  on a `Free`. Mitigated by the fact that no project declares one yet.
- **Six coordinates re-place on every binding.** Binding all six runs the
  placement six times, each rebuilding up to six operations and one 4x4
  inversion. `Joint.arguments` caches the resolved arguments per instance
  (`joints.py:322-331`) but `_carry` re-inverts every time — as it does
  today for every joint of every node on every run. Not a new cost per
  binding; a 6x one for a floating body. Nobody has measured it and no
  bench exists; recorded as a known unmeasured cost, not as "fine".
- **Gimbal lock is real and inherited.** At `pitch = ±90°` roll and yaw
  are degenerate. The design record made `Spherical` quaternion-valued
  for exactly this reason and accepted Euler angles for `Free` anyway,
  which is a contradiction the pilot ratified knowingly; see open
  question 9. The probe includes `pitch=90` and `roll=90` poses so the
  fixture at least *records* the composition there rather than avoiding
  it.
- **`coordinate` absent on `Free` is a deliberate `AttributeError`
  surface.** Anything reading `joint.coordinate` without checking gets an
  exception rather than a wrong answer. That is the intent; the three
  in-framework readers are all changed here.

## Migration Plan

None. `Free` is a new name. No existing declaration, pose, document or
test changes, and the three seams grow branches rather than changing
behaviour for a one-coordinate joint — which the full suite, plus the
cycle-1 and cycle-2 sections unedited, is what proves.

## Open Questions

- **A quaternion `Free` (carried, was §7 question 9).** MuJoCo's `free`
  carries a quaternion; Modelica's `FreeMotion` has its own angle
  sequence. Six Euler coordinates are lossy at gimbal lock and the design
  record says so while insisting `Spherical` must be native and
  quaternion-valued. What a driver would bind for a quaternion, and
  whether `Free`'s three angles should become one, is not settled and the
  hexapod does not need it settled. **Open.**
- **The export target.** Neither the MuJoCo nor the Modelica mapping is
  designed here, and `Free` is the one joint where both targets have a
  native element, so it is the cheapest one to get wrong by guessing.
  **Open.**
- **Is `at` the parent's frame or the body's own?** The hexapod cannot
  tell them apart (§1): its chassis has an identity rest placement. The
  rule chosen is the parent's frame, by consistency with ADR-088. What
  would settle it: a floating body whose parent's `render()` actually
  places it somewhere. **Open, and named in the spec as the rule rather
  than as evidence.**
- **Wiring a `Free` coordinate downward. CLOSED for this cycle as
  REFUSED BY NAME.** The dotted keyword works (measured) and is
  deliberately not offered: it would be the first non-identifier keyword
  in the API and no project asked for it. Both wiring roles are refused
  at class definition. A project that later needs one is a new sighting,
  and it arrives with a real call site to judge the spelling against.
