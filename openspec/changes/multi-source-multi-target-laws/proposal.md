## Why

A relation reads ONE coordinate and binds ONE coordinate. A mechanism
often reads several and moves several, and every one of those is a
sentence the catalogue cannot write.

`workflow/warts.md` carries the finding with five sightings, and the
sentences the projects want are quoted there:

**The Pascaline's pawl is bilinear in two drums.** Its swing is
`PAWL_DEFLECTION * (climbing(count) + ratchet(next_count) * (1 - pushing(count)))`
— this position's drum and the next one's. Wanted:

```python
(count, next_count).drives(sautoir.pawl.swing, law=pawl_deflection)
```

Today, `Digit.simulate()` (`Vibecoded-demos/pascaline/pascaline/digit.py:96-113`)
binds a declared joint from that expression by hand, with the `count`
and `next_count` ports read back out of the node one line earlier.

**A delta printer's rod has four freedoms and three sources.** The Mini
Kossel is the one project in the catalogue whose remaining blocker the
campaign tracker names as this finding
(`libresolid-studio/docs/motion-general-refactor.md`, 2026-09-10:
"Still deferred: … kossel (multi-source relation)"; its other two gaps
are the own-placed-origin anchor and the declaration-site joint, which
cycles 2 and 3 close). Its stage-B
proposal names it as gap 4, "A relation reads one coordinate; the delta
reads three", and asks for:

```python
(x, y, z).drives((rod.spin, rod.lean, rod.swing, rod.rise), law=delta_rod)
(x, y, z).drives(towers.height, law=delta_carriage_law)
```

Today `Kossel.simulate()` (`3D-Printers/kossel/simulation/kossel.py:203-220`)
runs the delta inverse kinematics in a loop and writes the four bindings
out per rod, six times, plus three `connect()` calls for the carriages:

```python
for index, (tower, angle) in enumerate(zip(self.towers, TOWER_ANGLES)):
    height = delta_carriage(self.x, self.y, self.diagonal_rod,
                            self.delta_radius, angle, plane=plane)
    self.connect(height, tower.height)
    tilt, azimuth = delta_rod(self.x, self.y, self.diagonal_rod,
                              self.delta_radius, angle)
    spin = asin(sin(azimuth - angle) * cos(tilt))
    for side, rod in zip((-1, 1), self.rods[2 * index:2 * index + 2]):
        rod.rotate(spin, [0, 0, 1]).rotate(-tilt, [0, 1, 0])...
```

`rods = Rod(...).repeat(6)` and `towers = Tower(...).repeat(3)`, so both
sentences are ALSO broadcasts: cycle 1 (ADR-096) gives the law the copy,
and `rod.index` is the tower angle and the side.

**OpenFlexure's four flexure legs lean two ways from two coordinates.**
`MainBody.simulate()` (`Lab-Equipment/openflexure-microscope/simulation/microscope/body/body.py:87-100`):

```python
def _lean_leg(self, leg, dx, dy, angle):
    radial, tangential = k.leg_lean(dx, dy, angle)
    leg.rotate(radial, [0, 1, 0])
    leg.rotate(-tangential, [1, 0, 0])
```

over `driven_legs = FlexureLeg(levered=True).repeat(2)` and
`idle_legs = FlexureLeg(levered=False).repeat(2)`. `k.leg_lean` returns
BOTH rotations from BOTH stage coordinates in one call. Wanted:

```python
(stage.slide_x, stage.slide_y).drives((legs.lean, legs.tilt), law=leg_lean)
```

**InMoov's hand drives four repeated fingers from five drivers.** Cycle
1 moved this sighting here by name (`warts.md`, and `repeat-fan-out`
tasks §8.1): a broadcast has ONE source, and `Hand` has five —
`thumb`, `index`, `middle`, `ring`, `little` — one per copy. Today
`Hand.simulate()` (`Robotic-Hands/Inmoov-sim/Inmoov_sim/hand.py:305-315`)
writes ten `connect()` calls in a loop over `FRAMES`. Wanted:

```python
(thumb, index, middle, ring, little).drives(fingers.drive, law=by_finger)
```

with the law picking by `finger.index`.

## What it costs today

Measured on this tree (`evidence/probe_today.py`, `evidence/probe_returns.py`):

| Written | Today |
|---|---|
| `(a, b).drives(c, law=…)` | `AttributeError: 'tuple' object has no attribute 'drives'` |
| `(a & b).drives(c, law=…)` | `TypeError: unsupported operand type(s) for &: 'SignalPort' and 'SignalPort'` |
| `a.drives((b, c), law=…)` | `TypeError: (<path one.turn>, <path two.turn>) is not a coordinate, so it cannot be the driven end of a relation.` |
| a law whose `forward` returns four values | binds the TUPLE into the slot: `Rotation(1.0, 2.0, 3.0, 4.0)` — a pose nobody stated, refused by nothing |

## What Changes

**An end of a relation may be SEVERAL coordinates.** On the driven side
they are written as a tuple, which is where the ratified sentence
already puts them and which Python already delivers to the framework:
`a.drives((b, c, d), law=…)`. On the source side a tuple display cannot
carry a method and `tuple` cannot be given one (measured: `TypeError:
cannot set 'drives' attribute of immutable type 'tuple'`), so the same
group is written with `&` — `(x & y & z).drives(…)` — which adds no
name, no import and no second verb. See "Decisions for the pilot" (a):
this is the one place the cycle cannot spell the ratified sentence.

**The law is still a callable of two arguments, and its arguments still
name the OWNERS of the ends** (ADR-089). What generalizes is their
SHAPE: a side that names several coordinates is handed the tuple of
their owners, in the order written. A side that names one is handed that
one node, exactly as today.

**The law's `forward` takes one value per source and returns one value
per driven end.** Sources are spread positionally, so
`lambda x, y, z: …` is the mechanism's own function; the return is a
SEQUENCE of exactly m values in the order the ends were written (for one
driven end, the value itself, unchanged). A return that is not a
sequence of exactly m is refused by name, naming the relation, the law,
the ends as written and what came back — the silence
`probe_returns.py` measures is what that refusal replaces.

**One direction only.** A relation naming several ends is applied when
every source is bound, and is NEVER read backwards, whatever its law
offers — for the reason a broadcast is not: m values cannot be
un-mixed into n without the framework comparing or solving values, which
it does not do. Asked to, it refuses `NotInvertible` by name. `ratio=`
and `offset=` are refused with a group on either side, and so is a group
with NO `law=`: an affine law relates one value to one value.

**A relation resolves to one record holding all its ends**, n driver
ends and m driven ends, and under fan-out to one such record per copy
(ADR-096's shape, with one END-SET per copy rather than one end). All m
driven ends are CLAIMED before any is bound, so a doubly-bound target
refuses without leaving a half-applied law.

**Under a broadcast, every driven end must fan out over the SAME
repeated segment**, so `(rods.spin, rods.lean, rods.swing, rods.rise)`
over `.repeat(6)` is six records of four ends and one law call per copy.
Mixing a broadcast end with a plain one, or two different repeats, is
refused at class definition.

**A repeated SOURCE is still refused**, inside a group as outside it: a
source is one value and n copies hold n.

## Decisions for the pilot

**(a) The ratified source-side sentence cannot be spelled in Python, and
this proposal changes its spelling.** `(count, next_count).drives(…)`
requires `tuple` to carry `drives`; `tuple` is immutable and cannot be
given an attribute (measured). The four candidates were: `&` between
coordinates; a free function `drives((a, b), c, …)`; a wrapper noun
`Sources(a, b).drives(…)`; and a second verb on the driven end
(`c.driven_by((a, b), …)`). **`&` is chosen.** The free function is
refused by measurement, not taste: a class body that binds the name
`drives` shadows it, and InMoov's `Hand` — one of the four projects that
must write this sentence — declares `drives = Drive().repeat(5)`
(`hand.py:213`); the probe shows the free function becoming
`TypeError: 'list' object is not callable` inside such a body. A wrapper
noun adds an importable name and reads as framework jargon; a second
verb is exactly the "second vocabulary" ADR-089 refused. `&` adds no
name and reads as the ratified tuple does. The driven side keeps the
ratified tuple verbatim, and also accepts `&`, because the group and the
tuple mean one thing.

**(b) The law's two arguments become shaped rather than spread.** The
alternative — one positional argument per END, drivers then driven — was
weighed and is written out in `design.md` §3. It makes kossel's law
`def delta_rod(machine, _y, _z, rod, _lean, _swing, _rise)`: seven
parameters, five of them duplicates, because three sources share one
owner and four driven ends share another. The chosen shape makes it
`def delta_rod(sources, rods)` with `sources[0]` and `rods[0]`. Both are
predictable from the sentence and neither inspects the law. The chosen
one keeps ADR-089's sentence "a CALLABLE of two arguments" literally
true and keeps a six-source law from having a seven-parameter signature.
Confirm, because every law in the catalogue is project code.

**(c) A coordinate named on BOTH sides of one relation is refused at
class definition — for a relation naming several ends only.** For a
one-to-one relation `a.drives(a)` is unrefused today and deadlocks into
`UnreachedCoordinate`; widening the check to it is a strict improvement
this cycle does not measure against the catalogue, so it is recorded and
not taken. Say if it should be taken.

## Impact

- **Specs:** `couplings` — one ADDED requirement ("A relation may name
  several coordinates at each end") and four MODIFIED ("The law of a
  relation is an affine pair, or project code passed in";
  "Each end of a relation resolves to a coordinate, or to one per copy
  of a repeated child"; "Relations are solved from the bound side, at the
  end of the owning simulate phase"; "Three refusals keep a wrong drive
  network from becoming a pose"). `ports` is untouched: the group
  operator is relation vocabulary, and the requirement that says where
  the relation vocabulary lives is in `couplings`. `joints`,
  `node-model`, `declarative-nodes` and `simulation` are untouched.
- **ADRs:** one new ADR — a relation may name several coordinates at
  each end — extending ADR-089 (whose two-argument law it re-shapes),
  depending on ADR-096 (the copies and the per-copy law call) and citing
  the `whole-tree-fixpoint` ADR for the deferral it inherits.
- **Code:** `solid_node/motion/couplings.py` (the group and its
  refusals; `EndGroup`; `Relation.resolve` over n×m; `RelationRecord`
  carrying end TUPLES; `_step_relation`, `_claim` and `_refuse`
  generalized; the return-shape check), `solid_node/motion/ports.py`,
  `solid_node/node/declarative.py`, `solid_node/node/qualified.py` (the
  `&` operator beside `drives`, on exactly the declarations that already
  carry `drives`). `joints.py` and the serializer are untouched.
- **Tests:** `tests/test_couplings.py` (a new section), and
  `tests/coupling_project/` for a tree that states a two-source,
  four-target law over a repeat.
- **Projects:** none is edited. The evidence is the pose comparison over
  every project on the motion layer, base against head, at maximum
  deviation 0, plus four read-only overlays proving the four sentences
  above — kossel's being the strongest, because its stage A binds the
  same four coordinates by hand and its poses must come out identical.
- **Users:** none. The motion layer is unreleased
  (`docs/changelog.rst`, Unreleased); the catalogue is every reader
  there is. Every form this cycle gives a meaning to is a hard error
  today, so no project can have depended on it.
- **Dependencies:** cycle 1 (`repeat-fan-out`, ADR-096) must be on the
  branch — it is. Cycle 4 (`whole-tree-fixpoint`) lands FIRST: a record
  whose sources are not all bound DEFERS under its rule, and this
  cycle's delta for the two requirements cycle 4 also modifies is
  written on top of cycle 4's text. Cycles 2 and 3 are independent —
  they change where a joint's arguments are read, never what a relation
  names.
