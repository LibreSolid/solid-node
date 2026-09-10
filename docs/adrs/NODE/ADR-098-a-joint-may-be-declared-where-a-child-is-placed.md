# ADR-098: A Joint May Be Declared Where A Child Is Placed

**Status:** Accepted
**Date:** 2026-09-10
**Extends:**
- [ADR-097: A joint is stated in the frame of whoever declares it](./ADR-097-a-joint-is-stated-in-the-frame-of-whoever-declares-it.md) (builds the second declarer ADR-097 named and deliberately left unbuilt)
**Revives:**
- [ADR-094: An orbit carries a point and derives its radius](./ADR-094-an-orbit-carries-a-point-and-derives-its-radius.md) (the `_OWN_PLACED_ORIGIN` sentinel, for a site-declared `Orbit`'s defaulted `carries` only)
**Extends the slot of:**
- [ADR-093: The joints of one class compose in declaration order](./ADR-093-joints-of-one-class-compose-in-declaration-order.md) (a declaration site is the next writer after a subclass)
**Gives a spelling to:**
- [ADR-095: A free joint owns six coordinates](./ADR-095-a-free-joint-owns-six-coordinates.md) (the OTHER reading of a floating base's frame, left open there for the class-declared form)
**OpenSpec change:** `declaration-site-joint`

## Context and Problem Statement

ADR-097 built the first half of "a joint is stated in the frame of
whoever declares it": a class body's own statement about itself, read
in the body's own rest frame. It named the second declarer — a joint
passed as a keyword where a parent places a child, read in the parent's
frame, URDF's rule — and built no part of it, on purpose: *"this cycle
builds no second escape hatch."*

What is left over, measured in `evidence/sightings.md` against the
catalogue after ADR-097 landed, is fourteen live sightings in eight
projects of one shape ADR-097's own-frame rule cannot reach: **a body
whose freedom its own class cannot state, for a reason that has nothing
to do with arithmetic.**

- **OpenCycloid's twelve orbiting bodies are REFUSED by ADR-097, not
  merely misread.** Four `Orbit` declarations, both `at` and `carries`
  defaulted: under the own-frame rule the two defaults collapse onto one
  point, the carried point lies on the line, and every one of the twelve
  is refused at the first binding for a radius of zero. Ten of the
  twelve are `.repeat()` copies.
- **Four classes exist only to hold a joint** — openvmp's `Wheel` and
  `CameraArm`, OMX's `LeftFinger` and `RightFinger` — adding no geometry
  and no behaviour to their base.
- **Shared catalogue hardware cannot carry a joint at all**: InMoov's
  wrist axle is the catalogue `Bolt`; a joint on it would give every
  bolt in the hand a wrist freedom.
- **Ten anchors name a line of the ASSEMBLY**, not the body: the
  Internal Cycloidal Actuator's two disk `Orbit`s, InMoov's seven finger
  `Revolute`s, openflexure's gear-lock screw.
- **Five axes are unstateable as a literal**, because one class stands
  at two opposed placements: both Prusa belt-guide pairs, hangprinter's
  mirrored motor gear and roller pair, openvmp's two legs.
- **82 children a loop builds from data** have no class to declare
  anything on.

The sentence all of them want is the one URDF has had all along:

```python
output_pins = Pin(orbit=Orbit(axis=AXIS, unit='deg')).repeat(OUTPUT_PIN_COUNT)
gear_screws = GearLockScrew(orbit=Revolute(axis=(0, 0, 1), unit='deg')).repeat(2)
```

## Decision Drivers

- OpenCycloid is not a matter of elegance: it is a shipped machine that
  ADR-097 alone leaves unstateable. The window between the two cycles
  landing is otherwise a real regression.
- More than half of the sightings' site declarations carry **no anchor
  at all**, because a shared catalogue class's joint line so often runs
  through the placing assembly's own origin — the motor shaft, the fork
  pivot, the actuator axis, the drive axis.
- A `.repeat()` copy's `index` is stamped by `RepeatDeclaration.realize`
  AFTER the copy's own construction (ADR-096's own design, restated in
  `repeat-fan-out`'s finding): a class-body callable of a copy's `index`
  cannot resolve, and OpenCycloid's ten repeated bodies make a site
  joint on a repeat a requirement, not a convenience.
- Every rule this ADR states should be delivered by machinery the
  framework already has — `declared_joints`'s MRO walk, the descriptor
  protocol, `declared_ports`, `read_through` — rather than a second,
  parallel path built to answer for one more kind of declaration.

## Considered Options

1. **The declaration specializes the class it declares** (chosen): at
   class definition, a subclass carrying the site's joints is built once
   and shared by every child the site realizes, its identity (name,
   qualname, module, file) copied from the written class verbatim.
2. **Instance-level machinery**: the site's joints held in the child's
   own instance dict, with `__getattr__`/`__setattr__` hooks on the node
   base making an instance-level declaration answer like a class-level
   one, plus node-level `ports_of`/`joints_of` enumerators and a public
   `attach_joint`.
3. **A joint's operations composed outermost**, outside the child's rest
   placement, needing no inversion.

## Decision Outcome

Chosen option: **1, the declaration specializes the class it declares**,
with the joint's operations carried **innermost** (a restored `_carry`),
because it delivers every remaining rule — the slot, the clash, the
descriptor, the enumeration, the path — from machinery ADR-093 through
ADR-096 already built, at the cost of one identity check narrowing and a
bounded number of extra class-keyed cache entries.

### What a joint passed as a declaration keyword IS

```python
screw = ZScrew(turn=Revolute(axis=(0, 0, 1), unit='deg'))
```

`turn=` here is a **declaration of a freedom on the child**, contributed
by the site — not a wiring (a wiring hands a parent's OWN, already
declared coordinate down; a site joint declares a coordinate that did
not exist), not a parameter (filtered out before construction, exactly
as a wiring is, so it never reaches `resolve_parameters` or
`_canonical_serialization`), and not identity. The two are told apart
by the **value**, not the keyword: a coordinate the DECLARING class
already owns is a wiring, as today; a fresh `Joint(...)` built in the
keyword list, belonging to no class yet, is a site declaration. This
needed one refinement measured against the tree rather than argued from
it: `Joint` does not carry `_names_in_body` (unlike a `Declaration` or a
`DerivedCoordinate`), so a genuine wiring naming a SAME-BODY sibling
declared two lines earlier (`turn = Revolute(...)`, then
`Wheel(turn=turn)`) reads `turn.owner` as `None` too, `__set_name__`
being batched at class creation. `_in_current_body` closes the gap: a
joint already bound to a name in the class body that is CURRENTLY
EXECUTING is a same-body wiring reference whatever `.owner` reads right
now; a joint bound to no name anywhere is a fresh site declaration.

### The frame, and what each default means

A site-declared joint's `axis`, `at` and every further point are read
in the frame of the node that DECLARES it. `at` defaults to `(0, 0, 0)`,
the DECLARING PARENT's own origin — the opposite of a class-declared
joint's default and the same sentence: the declarer's own origin. A
child the parent TRANSLATES therefore SWINGS about the parent's origin,
not its own, unless `at` names the child's own placement — the case
openflexure's gear-lock screws and InMoov's seven finger joints want,
all anchorless at the site.

An `Orbit`'s `carries` keeps ADR-094's asymmetry: WRITTEN at a site it
is a point of the parent's frame, like `at`; DEFAULTED it is the
CHILD's own origin, never the parent's — ADR-094's `_OWN_PLACED_ORIGIN`
sentinel, revived here for exactly this default. OpenCycloid's four
defaulted `Orbit`s are the measurement that settles it: with `carries`
following `at` into the parent's frame, all four collapse onto the line
and the machine is unstateable in either cycle; with the asymmetry
restored, all four bind exactly as they did before ADR-097, one level
out. A `Free` declared at a site floats against the DECLARING PARENT's
frame — the other reading ADR-095 left open, given its own spelling
without overturning ADR-095's choice for the class-declared form.

### How a site joint's operations reach the child: innermost, carried

A site joint occupies a slot in ADR-093's single composition order and
its run goes in through `apply_joint_motion` exactly as a class joint's
does — but its declared arguments are in a DIFFERENT frame from the one
they are placed in, so `place` carries them through the inverse of the
child's own rest placement first: `Joint._carry`, ADR-097's own deletion,
restored, unedited in its arithmetic, and re-derived against ADR-097's
own pinned fixture (Thor's elbow) read the other way — the parent
states the same joint ADR-097 pinned on the class, and the framework
must reproduce the identical operations from it. The alternative,
option 3 (outermost, no inversion), is arithmetically equivalent
(`J·M ≡ M·(M⁻¹JM)` for a rigid rest placement `M` and a parent-frame
joint transform `J`) but was rejected: it would give a node two
composition zones instead of one, make the clash rule (a site
redeclaring a class joint) jump zones silently, depend on a position in
the operations list `render()` and the checkpoint index both disturb,
and need a second placement path per joint kind instead of riding
ADR-094's existing `axes()`/`carried_points()` seam. The one cost: a
rest placement the framework cannot evaluate numerically refuses binding
a SITE-declared joint by name (naming the node, the joint and the
operation), where ADR-097 already relaxed that refusal for a
class-declared one — two rules where ADR-097 left one, and it is
recorded as a narrowing rather than argued away.

### The slot: one composition order, site joints last

A site joint of a name the child's class already declares REPLACES that
declaration WHOLE — axis, anchor, unit and range together, a partial
override refused by construction since the site simply supplies a new
`Joint` object — and keeps that name's slot; a site joint of a new name
is appended after every class-declared joint, in keyword order. Both
are ADR-093's existing rule read one writer further out, delivered by
`declared_joints`'s existing base-first MRO walk with no new
enumerator: the specialization (below) is a subclass, so its own
attributes are visited last and a redeclared key keeps its dict
position.

### Callables: one argument, the realized declaring parent

A whole argument may be a callable of one argument, called with the
realized DECLARING PARENT — not the child, and not a `.repeat()` copy's
`index`, which is not yet assigned when a site's arguments resolve
(`ChildDeclaration.realize` resolves them eagerly, immediately after
the child's own construction, while `RepeatDeclaration.realize` assigns
`index` on the line after that returns). Measured against the four
sightings the campaign's own plan note predicted would need `index`: all
four need nothing, because the sign each copy would have supplied is
exactly what each copy's own carry produces. A per-copy site value is
therefore left unstated, deliberately, for its own future sighting —
the discipline `repeat-fan-out` applied to `count` and ADR-093 applied
to the slot keyword.

### The mechanism: the declaration specializes the child's class

At class definition, `ZScrew(turn=Revolute(...))` derives a class from
`ZScrew`, carrying `turn` as an ordinary class attribute, and realizes
the site's children as instances of THAT class — one specialization per
site, built once in `ChildDeclaration.__init__` (not `__set_name__`: a
declaration held in a literal list never receives `__set_name__`, and
the specialization must exist before a class body reads a path through
it on the very next line), shared by every child the site realizes.

**The specialization copies the declared class's `__qualname__`,
`__name__`, `__module__` and source file, deliberately.** A joint is not
identity: it says where a body may move, not what geometry is built, so
two children of one class differing only in the joints their sites
passed must key one printed artifact, exactly as `_canonical_serialization`
already keys identity by class-plus-arguments and the joint keyword
never reaches the constructor. `source_scope` and `get_source_file`
follow the same copy to the written class's own file.

Every other rule then comes for free: `Joint.__set_name__` fires when
the specialization is built and runs `_refuse_shadowing` against the
CHILD's own MRO (`type(...).__mro__[1:]` starts there) — the refusal
against a port, a parameter, a child declaration, a method or a
property the child already answers to, delivered with NO new check;
`declared_ports(type(node))` reports the coordinate, so `get_coordinate`,
`set_coordinate` and `capture_poses.py` see it unchanged, and the
`ports` and `couplings` capabilities need no delta at all;
`read_through(node_class, ...)` finds the joint on the declaration's
class, so a relation names it by path exactly as it names a
class-declared one. What does not come for free, and is added
explicitly: a constructor-signature check for a NON-declarative child
(`inspect.signature(node_class.__init__).parameters`), because a
site keyword colliding with a plain `**params`-catching `__init__`'s
named parameter leaves no class attribute for `_refuse_shadowing` to
see; and a coordinate-name collision check across a declaration's own
site joints and wirings, for the one case reachable only through
`**{...}` expansion (a `Free`'s own dotted sub-coordinate named again
as a second literal keyword).

**Rejected: option 2, instance-level machinery.** It reads more honest
(nothing synthetic) and is much larger: two hooks on a path every node
attribute assignment takes, two new enumerators, a second membership
rule for `get_coordinate`, edits to `couplings.py` so a path can find a
joint no class declares, and a fourth public name — all of it existing
only to reproduce, for one kind of declaration, what the class machinery
already does for the other.

## Consequences

- **`type(x) is C` stops holding for a child whose site gave it a
  joint.** `isinstance` holds, and nothing in the catalogue writes the
  identity check, but the framework does, once:
  `solid_node/node/internal.py:166` refuses a render returning its own
  type via `type(child) is type(self)`, and a site-jointed child of a
  parent's own class would slip past that guard. Pinned, not fixed, by
  `SpecializationOwnTypeGuardTest` — the ordinary case the guard still
  catches is unedited.
- **A reader who prints `type(child)` sees the written class's name for
  a class that is not the written class**, because the copy of name,
  module and file is total and deliberate. Model discovery
  (`node_classes_in`/`_defined_classes`) scans a MODULE's `__dict__`,
  and a specialization is never bound to one, so it is invisible there
  by construction; `SpecializationDiscoveryTest` asserts it.
- **Class-keyed caches gain one entry per declaration site, not per
  realized child.** `_declared_cache`, `_children_cache`,
  `declared_parameters`'s own cache and `_relations_cache` are all keyed
  by class object and populated lazily; `SpecializationCacheBoundTest`
  measures the bound directly.
- **A body whose rest placement carries a symbolic value may carry a
  CLASS joint and may not carry a SITE one.** Two rules where ADR-097
  left one; mitigated by naming both halves in the refusal message and
  by no project in the catalogue having such a placement under a site
  joint.
- **The frame does NOT follow the declarer for hand-written motion, and
  this ADR makes that visible rather than fixing it.** A parent's
  `self.child.rotate(...)` in its own `simulate()` composes INSIDE the
  child's rest placement and is read in the CHILD's frame, while a site
  joint the same parent declares is read in the PARENT's. After this
  change a project can write both on one child and get two frames from
  one author. Filed in `workflow/warts.md`, not fixed here.
- **openvmp's data-built parts get nothing from this ADR.** ADR-097
  already answers "give a realized child a freedom" for them (a
  project-side subclass with a declared parameter and a class-body
  callable); "let a relation NAME a child a loop builds from data" is a
  separate finding this ADR does not close, because a relation's path is
  class metadata checked at class definition, and a child built from a
  file at construction has no class-level name to check against.
- **Evidence, not proof of migration.** No project repository is edited;
  the evidence is a read-only overlay per project, at maximum deviation
  0 across every project the catalogue tracks that this cycle touches or
  measures directly, including the four ADR-097 leaves refused or wrong.
  The overlay proves the rewrite reproduces the reference pose; it does
  not migrate the project.
