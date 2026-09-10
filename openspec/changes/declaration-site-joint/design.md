## Context

Cycle 2 (`joint-frame-follows-declarer`) states the rule this cycle is
the other half of: **a joint is stated in the frame of whoever declares
it.** It builds the first half — a joint written in a CLASS BODY is the
body's own statement about itself, read in the body's own rest frame,
`at` defaulting to the body's own origin, MuJoCo's rule. It names this
cycle as the second half — a joint written at a DECLARATION SITE is the
parent's statement about a child it is placing, read in the declaring
parent's frame, `at` defaulting to the parent's origin, URDF's rule — and
leaves it entirely unbuilt, on purpose: *"this cycle builds no second
escape hatch."*

What is left over is not a tidy-up. Cycle 2's survey of 249 class-body
declarations found the strict count of anchors a class cannot state at
all to be **zero**, and the count in substance to be **ten**: the
Internal Cycloidal Actuator's two disk `Orbit`s, InMoov's seven finger
`Revolute`s, openflexure's `GearLockScrew`. It found **five axes** that
one class cannot state as a literal because it stands at two opposed
placements. And this cycle's own survey (`evidence/sightings.md`) adds a
fourth kind cycle 2 did not count, because it is not a value at all: a
class that is **not entitled to the declaration** — shared catalogue
hardware, and four subclasses whose entire body is one joint.

The finding has fourteen live sightings after cycle 2, in eight
projects, and one of them is not a matter of elegance at all: OpenCycloid
declares `Orbit(axis=AXIS)` with both `at` and `carries` defaulted on
twelve bodies, and under cycle 2's rule those two defaults collapse onto
one point, so every one of the twelve is REFUSED at binding for a radius
of zero. A machine that is on the motion layer today becomes unstateable
between the two cycles unless this one lands. It also has three
dead ones: `evidence/sightings.md` §5 measures the plan note's three
example sentences (`workflow/docs/motion-catalogue-2.md` §3.3) against
the source and finds two of the three answered by cycle 2 and the fourth,
the Internal Cycloidal Actuator's, short of an argument it cannot do
without. The examples are stale; the finding is not.

`evidence/sightings.md` is the empirical basis of every decision below.

## Goals / Non-Goals

**Goals**

- A joint passed as a keyword where a parent DECLARES a child is a
  declared freedom of that child, stated in the DECLARING parent's frame,
  `axis` and `at` alike, `at` defaulting to the parent's own origin.
- A shared catalogue class carries no joint and is still given one, per
  site, by the assembly that places it.
- The same joint, at one declaration, over every copy a `.repeat()`
  realizes, each copy carried through its own rest placement — which
  OpenCycloid's ten repeated orbiting bodies make a requirement rather
  than a convenience.
- A relation may name a site-declared coordinate by path, from the class
  body that declares the site.
- No project's pose moves: maximum deviation 0 across the catalogue.

**Non-Goals**

- Any change to a CLASS-declared joint. Cycle 2 settled it and this cycle
  does not touch its frame, its default, its resolution or its
  composition.
- Any new API for a child a loop builds from DATA. Decision 9 measures
  that case and finds it already answered by cycle 2 and ADR-088, with a
  project-side subclass and one declared parameter.
- Letting a relation NAME such a child
  (`base['motion-front-wormgear/worm'].spin`). Decision 9 says why, and
  says plainly that openvmp does not get the sentence it asked for.
- A per-copy site-joint value read off a `.repeat()` copy's `index`.
  Decision 5: no sighting needs one, and it waits for its own sighting
  as `count` did in cycle 1.
- Deprecating the hand-written `rotate`, changing the document, the
  serializer, the viewer, the parity corpus or the CLI.

## Decisions

### 1. What a joint passed as a declaration keyword IS

    screw = ZScrew(turn=Revolute(axis=(0, 0, 1), unit='deg'))

`turn=` here is **a declaration of a freedom on the child**, contributed
by the site. Three things it is not, each for a reason the framework
already has a name for:

- **It is not a wiring.** A wiring hands a parent's OWN, already declared
  coordinate down to a coordinate the child already declares, and BINDS
  it at the end of every simulate (`ports`, "A coordinate may be wired
  down to a child declaration"). A site joint declares a coordinate that
  did not exist and binds nothing. The two are told apart by the VALUE,
  not by the keyword: a coordinate DECLARED ON THE DECLARING CLASS is a
  wiring source, as today; a joint object declared on NO class — a
  `Revolute(...)` constructed in the argument list, whose `owner` is
  still `None` — is a site declaration. A joint declared on some THIRD
  class, passed here, is refused (decision 10): one declaration object
  belongs to one class.
- **It is not a parameter.** It is filtered out of the declaration's
  keyword arguments exactly as a wiring is, so it never reaches
  `resolve_parameters`, never reaches the child's constructor, and never
  enters `_canonical_serialization`. This matters twice over: OMX's
  `VisualPack` and openvmp's `Link` are NON-declarative classes whose
  `__init__` would otherwise be handed an argument it has no name for,
  and two instances differing only in a site joint must share one
  artifact.
- **It is not identity.** Same reason, stated as the rule the joints spec
  already carries for a class-declared joint's arguments: a joint says
  where a body may move, not what geometry is built.

It is, precisely, the thing `declared_joints` already reports for a class
— stateless declaration metadata, one object shared by every child the
site realizes, with the resolved arguments and the bound value living in
each realized child's own instance dict. The site is simply a second
place the framework reads such metadata from.

**Today this spelling is already refused, loudly, at class definition**,
which is why nothing silent is being changed. `ChildDeclaration.__init__`
classifies any coordinate-valued keyword as a wiring, and `_check_wiring`
answers:

> `Foo.screw`: the coordinate wired as 'turn' is not declared on `Foo` —
> it is declared on no class here. A wiring hands a parent's OWN
> coordinate to a child; declare it on `Foo` and wire that.

That message becomes wrong the day this cycle lands, and the branch it
sits on is where the new path forks.

### 2. The frame, and what the default means

A site-declared joint's `axis`, its `at`, and every further point or
direction it declares are read in **the frame of the node that declares
it** — the parent whose class body the site is written in, which is the
frame that parent's own `render()` states its geometry in, and therefore
the frame the parent's `translate` and `rotate` on this child are written
in. URDF's rule, where a `<joint><origin>` is in the parent link's frame.

`at` defaults to `(0, 0, 0)`, **the DECLARING PARENT's own origin**.

That default is the opposite of a class-declared joint's and it is the
same sentence: *the declarer's own origin*. What it means for a child the
parent TRANSLATES is worth stating in words, because it is the half a
reader gets wrong: the joint's line passes through the **parent's**
origin, not the child's, so a child the parent has moved 20 mm along `y`
SWINGS about the parent's origin rather than spinning on its own centre.
That is not a hazard here, it is the whole point — it is what
openflexure's two gear-lock screws want (both carried round the motor
shaft, which is the motor drive's own origin, from ±3.9 mm away), and
what InMoov's seven finger joints want (all turning about the fork pivot,
which is the finger's own origin, from up to 59.97 mm away). Eleven of
this cycle's twenty live sightings are written with **no anchor at all**.

An `Orbit`'s `carries` is the one argument that does NOT follow that
rule, and the exception is ADR-094's, not this cycle's. `carries` names a
point OF THE BODY, not a point of the line; ADR-094 gave it the sentinel
default `_OWN_PLACED_ORIGIN`, "the body's own placed origin", precisely
because in the parent's frame that point is not a number until the body
is placed. Cycle 2 deleted the sentinel as redundant — in the body's own
frame that point IS `(0, 0, 0)`. At a declaration site it is redundant
again, and **the sentinel comes back**:

- a WRITTEN `carries` is a point of the declaring parent's frame, like
  `at`;
- a DEFAULTED `carries` is the CHILD's own origin.

Defaulting it to the parent's origin instead would be nonsense twice
over: it names a point that is not of the body at all, and with `at` also
defaulted it would always lie ON the line, so every defaulted site
`Orbit` would be refused for a radius of zero.

**OpenCycloid is the measurement that settles it, and it is not close.**
That machine has four `Orbit` declarations over twelve bodies, every one
of them `Orbit(axis=AXIS, unit='deg')` with both `at` and `carries`
defaulted (`evidence/sightings.md` §3.4). Under cycle 2's own-frame rule
the two defaults collapse onto one point and all twelve are REFUSED at
the first binding for a radius of zero — a harder failure than the ten
anchors of cycle 2's survey, which merely read wrong. Under the rule
above, the same four declarations move to the site UNCHANGED: `at`
defaults to the drive's own origin, which is the drive axis; `carries`
defaults to each child's own origin, which is the bore centre, the
bearing's centre, the pin's centre. Ten radii and ten phases stay derived
and untyped — including the six output pins' 60° spacing and the four
eccentric bearings' two signs — exactly as that project's own comment
boasts today: *"Neither number is typed anywhere."* If `carries` followed
`at` into the parent's frame, that machine would be unstateable in either
cycle.

The Internal Cycloidal Actuator is the same rule read the other way and
is worth keeping beside it: its disks' own origins are 3.9974 mm and
3.9488 mm off the actuator axis while their BORE centres are 2.000 mm off
it, so the default — the disk's own origin — is the wrong point for that
machine, by 2 mm and a phase, and it writes `carries=DISK_n_BORE_CENTRE`
at the site, the expression it already computes
(`evidence/sightings.md` §3.2). Two machines of the same kind, one taking
the default and one overriding it, which is what a default should look
like. The plan note's example sentence omits the override; that omission
is silent, and stating the default is what makes it visible.

A `Free` declared at a site floats against the DECLARING PARENT's frame:
its three rotational directions are the parent's x̂, ŷ, ẑ and its three
translational coordinates displace along those same directions. Cycle 2
left open "whether `Free`'s three translational coordinates should float
against the body's own frame (chosen there) or against the parent's (the
more usual reading of a floating base)". This cycle does not overturn
that choice; it gives the other reading its own spelling, at the site,
under the one rule. No project has a `Free` at a site today, so this is a
rule, not a measurement.

### 3. How its operations reach the child: INNERMOST, carried

This is the decision the rest hangs on, and there are exactly two
candidates.

**Chosen: innermost, in the child's rest frame, by carrying the declared
parent-frame arguments through the inverse of the child's rest placement
at BINDING time.** This is `Joint._carry` — the forty lines cycle 2
deleted — restored, unchanged in arithmetic, and applied to
site-declared joints only. A site joint occupies a slot in the same
single composition order ADR-093 defines (decision 4), and its run goes
in through `apply_joint_motion` exactly as a class joint's does.

**Rejected: outermost, outside the rest placement, in the parent's
frame** — appending `translate(-at)`, `rotate(value, axis)`,
`translate(at)` to the END of the child's operations list, where the
parent's frame is already the current frame and no inversion is needed.

The rejection needs care, because outermost is superficially the more
honest reading and it is arithmetically equivalent where both are
defined. For a rigid rest placement `M` and a joint transform `J` stated
in the parent's frame, outermost composes `J·M` and innermost composes
`M·(M⁻¹JM)` = `J·M`. Same pose, every time. So the choice is not about
geometry; it is about five things that are not geometry.

1. **ADR-093 has ONE composition law and outermost needs a second
   zone.** Today a node's operations read, innermost first,
   `[joint block, by declaration slot][hand-written motion][rest]`.
   Outermost puts site joints on the FAR SIDE of the rest placement, so a
   node would carry joints in two zones and "which of my freedoms is
   innermost" would depend on where each joint was WRITTEN rather than on
   its slot. The clash rule makes that concrete and fatal: a site joint
   that redeclares a class-declared joint of the same name (decision 7)
   would jump zones, and every remaining freedom of that body would
   silently recompose around it. Under innermost the redeclaration keeps
   the slot, and nothing moves. InMoov's `MiddlePhalanx` is the live case
   — `pip` then `mcp`, both redeclared at the site — and the actuator's
   disk is the one where the order is worth a full eccentricity
   (ADR-093's sighting 4).
2. **Outermost is not a stable position, and the framework says so
   twice.** Rest operations are APPENDED by `_place_operation` while the
   parent's `render()` runs, so a joint bound before or during that
   render — a legacy render, an author's binding in `__init__`, a test
   perturbation — would end up buried INSIDE the placement and silently
   wrong, and keeping it outermost would mean teaching the generic
   operation path about a joint zone. ADR-093's own closing note records
   the second: `save_checkpoint`/`restore_checkpoint` index from the END
   of the operations list while motion inserts at the head — a mismatch
   it declined to fix, and one that outermost would walk straight into.
   Innermost has no such hazard: `apply_joint_motion` inserts at a slot
   at the head, and re-binding returns the run to its own slot whatever
   has been appended since. That is a promise the joints spec already
   makes and this cycle would rather keep than qualify.
3. **What outermost actually buys is a narrower thing, better refused by
   name.** The only cases where the two differ are the ones where `M` is
   not numerically evaluable at binding — a rest placement carrying a
   symbolic value. Cycle 2 relaxed exactly that refusal for class-declared
   joints (it deleted the inversion, so nothing could fail to invert).
   This cycle brings the refusal back for SITE-declared joints only, by
   name, naming the node, the joint and the operation whose `matrix()`
   carried a non-number — and it is the same message, with one clause
   changed from "the parent's frame" to "the declaring parent's frame".
   Trading a composition law for one refusal is the wrong way round.
4. **ADR-094's seam is built for the inversion, and both other joint
   kinds ride it.** `Joint.axes(node)` and
   `Joint.carried_points(node, anchor)` exist to say which DIRECTIONS and
   which POINTS a subclass's `placement` takes, so that they all ride
   ONE inversion. Restoring `_carry` restores that seam whole: an
   `Orbit`'s anchor and carried point, and a `Free`'s three directions,
   compose at a site with no per-kind knowledge, and `Free.axes`'s three
   literal unit directions become the parent's three directions by being
   carried, with not a line changed. Outermost would need a second
   placement path, per joint kind, that composes against the placed body.
5. **The catalogue writes the inversion by hand and asks for it.**
   openvmp's `spin()` (`link.py:116-129`) is `_carry` open-coded, with
   its own docstring saying why: *"Each part's motion is applied in its
   own frame, inside its rest placement, so the line is carried back
   through that placement first."* hangprinter's `winch.py:57-64`
   documents the carry as the mechanism one declaration relies on to
   serve a mirrored and an unmirrored leaf. Those are the two projects
   whose sightings this cycle exists for.

The costs, stated up front: `numpy` returns to `joints.py`; the carry
runs once per binding of a site joint; and the refusal cycle 2 deleted
returns for site joints, so a body whose rest placement carries a
symbolic value may carry a CLASS joint and may not carry a SITE one.
Cycle 2's own design predicted the return —*"Cycle 3 will want the
inversion back … It is re-added there, against the joint that needs it"* —
and pinned its acceptance so that it is re-derived against a number and
not from memory: Thor's elbow, `(0, 1, 0)` about `(0, 0, 81.5)`,
`tests/test_joints.py`. Task 1.1 restores it against that fixture first,
red.

### 4. The slot: one composition order, site joints last

A realized node's joints are enumerated as **the class's declaration
order, with the site's contribution folded in**:

- a site joint whose name the class already declares REPLACES that
  declaration and **keeps its slot**;
- a site joint of a new name is appended AFTER every class-declared
  joint, in the order the keywords were written.

Both halves are ADR-093's existing rule read one level further out. Its
enumeration is base-first through the MRO so that "a subclass
redeclaring an inherited joint keeps the base's slot while taking its own
arguments"; a declaration site is the next writer after the subclass, so
its redeclaration keeps the slot and its new joints come last. Read
outward from the body: the body's own freedoms first, then the freedom
the assembly grants it.

Two measurements say this is the right way round.

- The Internal Cycloidal Actuator declares `spin` then `orbit` on the
  disk and its comment says why: *"They compose in DECLARATION order,
  innermost first: `spin` closest to the body, then `orbit` outside it …
  The other order would land the bore centre at `R_spin(delta) + c0`
  instead of `c0 + delta`."* Under this cycle `spin` stays on the class
  (slot 0) and `orbit` moves to the site (slot 1) — the same order,
  preserved by the rule rather than by luck.
- InMoov's `MiddlePhalanx` declares `pip` (`:35`) then `mcp` (`:36`) and
  the site redeclares both. Keeping the class's slots keeps `pip`
  innermost, which is what the finger does.

No new enumerator answers this. Under decision 6 the site's joints ARE
class metadata on the class the declaration realizes, and
`declared_joints` already walks `reversed(__mro__)` assigning into a
dict — so a redeclared name reuses its key and keeps its position, and a
new name lands after the class's in the order the keywords were written.
Both halves of this rule are the enumerator's existing behaviour read one
writer further out; nothing is added to make them true.

### 5. Callables: one argument, the realized declaring parent

    at=lambda parent: (parent.dir * parent.side * CAMERA_OFFSET[0], …)

A whole argument — `axis`, `at`, `carries` or `range` — may be a callable
of ONE argument. For a class-declared joint the framework calls it with
the realized node that owns the joint; for a site-declared joint it calls
it with **the realized node that DECLARES the joint**. One sentence,
both sites: *the callable is handed the declarer, in whose frame the
value it returns is read.*

**When.** At the child's realization, immediately after the child is
constructed, inside `ChildDeclaration.realize`. Eagerly, not lazily, for
the reason `resolve_declared_joints` resolves eagerly: an argument that
cannot resolve should name the class, the joint and the argument at the
earliest point a value could be wrong.

**What it may read.** The declaring parent, at that moment, has its
declared parameters resolved, its `check()` run, everything its own
`__init__` set, and the children declared BEFORE this one realized. It
has NOT run `render()`, so nothing computed there and no placement exists
yet — including this child's own. It has not realized its later children,
and its relations have not resolved. openvmp's `CameraArm` is the
sighting and it needs exactly the first bucket: `parent.dir` and
`parent.side`, two `Count` parameters of `Camera`.

**What it may NOT read, and the trap that is worth naming.** The child's
placement. The arguments resolve before the parent places the child; the
CARRY happens later, at binding, when the placement exists. Those are two
different moments and conflating them is how a reader concludes that the
site form is impossible. It is not: resolution is early, carrying is
late.

**A `.repeat()` copy's `index` is NOT handed to the callable**, although
the campaign's plan note assumed it would be. Cycle 2 predicted three of the five mirrored axes and openflexure's
`GearLockScrew` anchor would need a per-copy callable of `index`;
measured at the site, **all four need nothing**, because the sign the
copy would have supplied is exactly what each copy's own carry produces
(`evidence/sightings.md` §3.3, §4). The callable is therefore handed the
declarer and only the declarer, and the copy waits for its own sighting —
the discipline cycle 1 applied to `count` and ADR-093 applied to the slot
keyword. If a per-copy site value is ever sighted, the shape it should
take is a callable of the copy, which is the class-declared form the
framework already has.

### 6. The mechanism: the declaration SPECIALIZES the child's class

A joint is class metadata everywhere else in the framework — a data
descriptor, enumerable off a class, shared by every instance. The
question this cycle has to answer is how a declaration SITE puts one on a
child without making it something else.

**Chosen: the declaration specializes the class it declares.** At class
definition, `ZScrew(turn=Revolute(...))` derives a class from `ZScrew`
carrying `turn` as an ordinary class attribute, marked site-declared, and
realizes its children as instances of THAT class. One specialization per
declaration site, created once and shared by every child the site
realizes — so a `.repeat(6)` has six children of one class, exactly as it
has today.

Two things about it are deliberate rather than tolerated.

**The specialization copies the declared class's `__qualname__`,
`__name__`, `__module__` and source file.** That is not a lie about what
the class is; it is the identity rule this cycle already has to state.
Build identity is `_canonical_serialization`'s `klass.__qualname__` plus
the constructor arguments (`base.py:446-465`), and a joint is NOT
identity — it says where a body may move, not what geometry is built — so
two children of one class differing only in the joints their sites passed
MUST key one artifact. Copying the qualified name is what makes that
true, and it is the same reason the joint keyword never reaches the
constructor. `source_scope` scopes a digest by `klass.__name__`
(`node/sources.py:175`) and `get_source_file` reads
`inspect.getfile(self.__class__)`, so both follow the copy to the written
class's own file.

**Every other rule then comes for free, and that is the argument.**
`declared_joints` walks `reversed(__mro__)` and assigns into a dict, so a
site joint of a name the class declares reuses that key and KEEPS its
slot, and a site joint of a new name lands after the class's, in keyword
order — decision 4 and decision 7 are delivered by the enumerator that
already exists, not by a second rule beside it. `Joint.__set_name__`
fires when the specialization is built and runs `_refuse_shadowing`
against the child's own MRO, which is decision 10's central refusal.
The descriptor protocol gives `self.turn` and `self.turn = value`, so
openflexure's `screw.orbit = self.shaft_pin.turn.value` binds and places
without a line of new machinery. `declared_ports(type(node))` reports the
coordinate, so `get_coordinate`, `set_coordinate` and the campaign's own
`capture_poses.py` see it unchanged — and therefore the `couplings` and
`ports` capabilities need no delta at all, and no node-level enumerator
is invented. `read_through(node_class, ...)` finds the joint on the
declaration's class, so `screw.turn` and `pins.orbit` are paths checked
at class definition, where they are written.

What DOES change is small and local: the declaration builds and holds the
specialization; a site-marked joint is skipped by the eager resolution in
the child's constructor and resolved instead in `realize`, against the
parent; and `Joint.place` carries a site-marked joint's arguments.

**Rejected: instance-level machinery** — the site joints held in the
child's instance dict, with `__getattr__` and `__setattr__` hooks on the
node base to make an instance-level declaration behave like a class-level
one, plus node-level `ports_of`/`joints_of` enumerators and a public
`attach_joint`. It reads more honest (nothing synthetic) and it is much
larger: two hooks on a path every node attribute assignment takes, two
new enumerators, a second membership rule for `get_coordinate`, edits to
`couplings.py` so a path can find a joint no class declares, and a fourth
public name. Every one of those exists only to reproduce, for one kind of
declaration, what the class machinery already does for the other. Its one
apparent advantage was decision 9, and decision 9 measured it away.

**What the specialization costs, stated exactly.** `type(x) is ZScrew` is
false for a child whose site gave it a joint (`isinstance` holds, and the
framework itself contains one such check, `internal.py:166`'s guard
against a render returning its own type — which a site-jointed child of
its parent's own class would now slip past). Every class-keyed cache in
the framework gains one entry per declaration site, which is bounded by
the source and is the same order as the number of child declarations
already cached. A specialization is not bound in any module namespace, so
`_defined_classes` (`core/loader.py:200-204`) cannot see it and nothing
that enumerates a project's models can reach it — which is right, and is
worth asserting rather than assuming (task 3.7).

### 7. The clash rule: the site wins, in the class's slot

A site-declared joint of the same name as one the child's class declares
REPLACES it for that child, and takes its arguments, its unit and its
range from the site. It keeps the class's SLOT (decision 4).

The precedent is exact and there are two of them: a wiring keyword may
name a joint the child declares and feeds it instead of the class's
binder; and ADR-093 already says that "a subclass redeclaring an
inherited joint keeps the base's slot while taking its own arguments".
A declaration site is one writer further out than a subclass, and the
same sentence applies.

Consequence worth stating: the replacement is WHOLE, never partial. A
site `Orbit` does not inherit the class `Orbit`'s `carries`; if the site
declares the joint, the site declares all of it. InMoov's finger and the
actuator's disk are both migrations of this shape, and the second is why
the rule matters — a partial override would have let the actuator's site
`Orbit` silently keep a `carries` stated in the disk's frame while its
`axis` was read in the assembly's.

### 8. A site joint on a `.repeat()`

**Required, not optional.** Cycle 2 left it as an open question —
*"whether cycle 3 should let a declaration-site joint be passed to a
`.repeat()`, which is what the five axes really want"* — because at that
point it was an elegance: four of the five unstateable axes and
openflexure's tenth anchor would rather have it than a per-copy callable.
OpenCycloid makes it a requirement. Ten of that machine's twelve orbiting
bodies are `.repeat()` copies of two catalogue classes
(`eccentric_bearings` ×4, `output_pins` ×6), and after cycle 2 those
orbits are refused at binding; without a site joint on a repeat, a
shipped machine that is on the motion layer today cannot be stated at
all.

    stage_one = CycloidalDiskStageOne(orbit=Orbit(axis=AXIS, unit='deg'))
    eccentric_bearings = RadialBearing(inner_diameter=17.1, outer_diameter=26.0,
                                       width=5.0,
                                       orbit=Orbit(axis=AXIS, unit='deg')).repeat(4)
    output_pins = Pin(orbit=Orbit(axis=AXIS, unit='deg')).repeat(OUTPUT_PIN_COUNT)
    gear_screws = GearLockScrew(orbit=Revolute(axis=(0, 0, 1), unit='deg')).repeat(2)
    rollers = RollerBearing(spin=Revolute(axis=SHAFT_AXIS, at=BELT_ROLLER_AXIS, unit='deg')).repeat(2)
    guides = XGuide(spin=Revolute(axis=(0, 1, 0), at=(X_IDLER[0], 0.0, X_IDLER[1]), unit='deg')).repeat(2)

The second line is also where the keyword split has to be exact: three
real parameters and one joint in one call, the three reaching the
constructor and entering identity, the fourth reaching neither.

**One declaration, n copies, one set of resolved arguments, n carries.**
`.repeat(n)` is a wrapper over the same `ChildDeclaration`, so the joint
is declared once and every copy realizes with it, exactly as every copy
realizes with the same class. The arguments resolve once per copy against
the same declaring parent and therefore resolve to the same numbers; what
differs per copy is the CARRY, through that copy's own rest placement.
That is precisely the difference the sightings need, and it costs
nothing: hangprinter's two rollers are placed `R([90,0,0])` and
`R([-90,0,0])`, Prusa's two guides `Rx(-90)` and `Rx(+90)`, and one
parent-frame axis produces the opposite own-frame axes at the two sites
without a sign, a flag or an index.

The rule composes with cycle 1 without a special case: a relation may
broadcast onto a site-declared coordinate of a repeat, because a
broadcast is resolved per copy and each copy owns its own slot.
OpenCycloid drives both of its repeats that way today
(`actuator.py:88`, `:117`):

    eccentric_shaft.spin.drives(eccentric_bearings.orbit)
    carrier.spin.drives(output_pins.orbit)

and both resolve with nothing added: `RepeatDeclaration.node_class`
delegates to the declaration it wraps, which under decision 6 is the
specialization, so `read_through` finds `orbit` on it and the terminal of
a `BroadcastRef` is an ordinary class-declared joint.

Ten radii and ten phases of that machine stay DERIVED under this rule:
one declaration, n copies, one set of resolved arguments, and each copy's
own carry producing its own number out of its own rest placement — the
four bearings' two signs and the six pins' 60° spacing among them. That
is the strongest single demonstration in the catalogue that the carry
(decision 3) is doing real work rather than restating a literal.

### 9. A child a loop builds from data: already answered, by cycle 2

openvmp builds 82 children in `Link.__init__` from a `.assy` file, one
generic `StepPart` or `SubAssembly` per entry, named by the file, and
moves eight of them through `spin()` (`link.py:116-129`) — `Joint._carry`
open-coded, docstring included. The first draft of this design read that
as a second half of the finding needing a second API. Measured against
cycle 2's rule, it is not.

**Under cycle 2 a class-body joint is stated in the body's OWN frame, and
a data-built part already knows its own frame.** `spin()`'s arithmetic
exists only to map a line from the LINK's frame back into the part's; the
part's axis in its own STEP frame is the constant the project already
has. So the project writes a subclass with a declared parameter and
ADR-088's callable — vocabulary that shipped two cycles ago:

    class TurningPart(StepPart):
        spin_axis = Vector((0, 0, 1))
        spin_point = Vector((0, 0, 0))
        spin = Revolute(axis=lambda node: node.spin_axis,
                        at=lambda node: node.spin_point, unit='deg')

and its loop builds `TurningPart(placement.part, name=child_name,
spin_axis=..., spin_point=...)` for the entries that turn, `StepPart` for
the rest. All 82 parts keep their generic class; the ones that move get a
real coordinate, enumerable, bindable, range-checked and placed at its own
slot; and `spin()`'s frame arithmetic is deleted because there is nothing
left to carry.

So this cycle adds NO API for the data-built case, and the case is not a
reason to prefer instance-level machinery over the specialization
(decision 6). What openvmp still cannot write is the OTHER half of what
it asked for (`…/archive/2026-09-09-move-onto-motion/proposal.md:225-231`):

```python
    front.yaw.drives(base['motion-front-wormgear/worm'].spin, ratio=WORM_GEAR_TEETH)
```

A relation is class metadata whose every segment is checked at CLASS
DEFINITION against the class the previous segment names — that check is
what turns a misspelled path into an error where it is written instead of
a wrong pose. A child built from a file at construction time has no
class-level name to check, so no cycle in this campaign reaches it and
those eight sites stay bindings in the parent's own `simulate()` rather
than relations. **A relation cannot name a child a loop builds from
data** is a separate finding and stays open (tasks 9.6).

### 10. What is refused, by name

| written | refused because | where |
|---|---|---|
| a keyword naming a PORT the child declares | a joint owns a port of that name, and the two cannot share it — the joints spec's existing "A joint and a port cannot share a name", one level out | class definition |
| a keyword naming a PARAMETER the child declares, or a named parameter of a non-declarative child's `__init__` | the keyword is stripped before construction, so the child would be built WITHOUT that parameter — different geometry, silently. openvmp's `Link(dir=…)` and OMX's `VisualPack(filename=…)` are why this is checked against the constructor signature and not only against the class attributes | class definition |
| a keyword naming any other attribute of the child class — a child declaration, a method, a property | reading the joint on the node would hide it for good: `Joint._refuse_shadowing`'s rule, run against the CHILD's MRO instead of the declaring class's | class definition |
| a joint declared on a THIRD class passed as a keyword | a declaration object belongs to one class; naming it here would give two classes one `name`, one `owner` and one coordinate declaration | class definition |
| two site joints of one name, or a site joint whose name collides with a coordinate another site joint of the same declaration owns (a `Free`'s `pose.roll` against a `Revolute` named `pose.roll` through `**{…}`) | one name, one coordinate | class definition |
| a site joint AND a wiring naming the same coordinate | reachable only through `**{…}` expansion, since one keyword cannot be both; a coordinate has one declaration and one binder | class definition |
| binding a site joint whose rest placement carries a value the framework cannot evaluate | decision 3's restored refusal, naming the node, the joint and the operation | binding |

**One blind spot, recorded rather than papered over.** A `Joint`
constructed in a class body and passed to something that is NOT a node
declaration — `helper = SomeHelper(turn=Revolute(...))`, where
`SomeHelper` is a plain Python class — is invisible to the framework:
no `ChildDeclaration` is made, the joint is an ordinary argument, and
nothing can be said about it. The framework refuses what it can see and
this is not in that set. It is worth knowing that the same is true today
of a `Port` declaration handed to a plain class.

### 11. What this does NOT change

- A class-declared joint: its frame, its `(0, 0, 0)` default, its
  resolution against its own node, and the fact that the framework
  transforms its arguments in no way. Cycle 2's rule stands verbatim.
- Composition order (ADR-093), what a joint owns (ADR-088), an orbit's
  derived radius and phase (ADR-094), a `Free`'s six coordinates
  (ADR-095), the broadcast (ADR-096), the couplings solver's pass order,
  the document, the serializer, the viewer, the parity corpus, the CLI.
- The wiring path. A coordinate-valued keyword that names a coordinate
  the declaring class declares still means what it means today, and the
  `TypeError` an unknown keyword raises is untouched.

## Risks / Trade-offs

- **`type(x) is C` stops holding for a child whose site gave it a
  joint.** `isinstance` holds and nothing in the catalogue writes the
  identity check, but the framework does, once: `internal.py:166` refuses
  a render that returns its own type, and a site-jointed child of a
  parent's own class would slip past that guard. Narrow, and named rather
  than discovered.
- **The specialization carries a copied qualified name.** Deliberately —
  it is what makes a joint not be identity (decision 6) — but it means a
  reader who prints `type(child)` sees the written class's name for a
  class that is not the written class. Mitigated by the copy being total
  (name, module, file) so nothing a message, path or digest reads can
  disagree, and by task 3.7 asserting the class is invisible to model
  discovery.
- **The refusal cycle 2 deleted comes back, for site joints only.** A
  body whose rest placement carries a symbolic value may carry a class
  joint and may not carry a site one. Two rules where cycle 2 left one.
  Mitigated by the message naming both halves, and by the fact that no
  project in the catalogue has such a placement under a site joint.
- **Two projects write one declaration twice.** hangprinter's `MotorGear`
  and openvmp's `Leg` move from one class declaration to two declaration
  sites (`WinchABC`/`WinchD`; `left_leg`/`right_leg`). The site form is
  not always shorter, and this is where it is longer.
- **The plan note's examples are stale.** Two of §3.3's three sentences
  are cycle 2's work and one is short of an argument
  (`evidence/sightings.md` §5). The proposal carries this to the pilot
  rather than quietly writing better examples, because §3.3 is also where
  Poseidon and the Prusa Z screws are named as validation projects and
  they should not be.
- **The frame does NOT follow the declarer for hand-written motion, and
  this cycle makes that visible.** A parent's `self.child.rotate(...)` in
  its own `simulate()` is inserted inside the child's rest placement and
  is therefore read in the CHILD's frame, while a site joint the same
  parent declares is read in the PARENT's. After this cycle a project can
  write both on one child and get two frames from one author. No sighting
  is harmed by it today; it is a new finding, and it belongs in
  `workflow/warts.md`, not in a silent corner of this design.
- **The evidence is a read-only overlay, not the projects.** As cycle 2:
  no project repository is edited, so no project is PROVED migrated. What
  is proved is that the rewrite reproduces its poses.

## Migration Plan

No project is edited by this cycle. Per sighting, from
`evidence/sightings.md`, for the projects' own stage-B cycles:

0. **OpenCycloid's four orbit declarations** → moved to the site
   UNCHANGED, two of them on a `.repeat()`; ten radii and ten phases stay
   derived and untyped, and the twelve bodies cycle 2 refuses bind again.
1. **Four subclasses-for-metadata** (openvmp `Wheel`, `CameraArm`; OMX
   `LeftFinger`, `RightFinger`) → delete the subclass, move its joint
   text verbatim into the parent's declaration site. `CameraArm` also
   sheds an `__init__` override and two instance attributes.
2. **InMoov's wrist axle** → a site joint on the shared catalogue
   `Bolt`, replacing three hand-written operations.
3. **The seven finger `Revolute`s** → site declarations with NO anchor;
   the `pip`/`dip` anchors move to the site keeping their original
   finger-frame values instead of being rewritten as negations.
4. **The two disk `Orbit`s** → site declarations, `at` omitted,
   `carries` written as the expression the project already derives. No
   literal the project's ratified spec forbids is typed.
5. **openflexure's `GearLockScrew`** → one site declaration on the
   `.repeat(2)`, no anchor, no index, no callable; the `GearLockScrew`
   subclass can then be deleted in favour of the catalogue screw.
6. **The five axes** → the parent-frame axis returns, at the site;
   rows 1, 2 and 4 on a `.repeat()`, rows 3 and 5 written at two sites.
7. **openvmp's data-built parts** → a project-side `TurningPart`
   subclass with two declared parameters and ADR-088's callable, built
   by the existing loop; `spin()`'s frame arithmetic deleted. This needs
   nothing from this cycle beyond cycle 2, and the relations the project
   wants are NOT delivered by either.

## Open Questions

- **The plan note's three example sentences and two of its four named
  validation projects.** `evidence/sightings.md` §5. For the pilot: the
  note is stale, and this cycle proposes the corrected list (Prusa's belt
  guides not its Z screws; openvmp; InMoov's axle and fingers; OMX; the
  actuator; openflexure; hangprinter — and not Poseidon).
- **Should a relation be able to name a child a loop builds from data?**
  openvmp's written-down sentence. Not this cycle; a finding of its own.
- **The parent's hand-written motion is read in the child's frame while
  the parent's site joint is read in the parent's.** A new finding this
  cycle exposes. Should the frame follow the declarer there too?
- **Does a site-declared `Free` close ADR-095's open question or merely
  give the second reading a spelling?** No project measures it.
- **`Prismatic` at a site.** Its `at` does not affect its placement, so
  the frame rule reaches only its `axis` — and an axis IS carried, so
  OMX's two mirrored finger axes are carried per site. The anchor is
  carried for a reader and an exporter, as today. Worth confirming that
  carrying a `Prismatic`'s unused anchor cannot fail where the placement
  is symbolic; task 1.9.
