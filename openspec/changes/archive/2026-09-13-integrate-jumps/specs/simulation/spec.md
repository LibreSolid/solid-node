## MODIFIED Requirements

### Requirement: A continuous law is integrated over a tick and increments propagate

Under a running root the driven coordinate of a relation SHALL move BY the
change of its law along its sources' movement, from where it stood: over
one tick a CONTINUOUS law contributes exactly `f(end) − f(start)`, `f`
being the law's `forward` face — or its `inverse` face where the rest
render solved the relation backward — evaluated over the sources' values
at the start and at the end of the tick. This SHALL be exact across the
kinks of `abs`, `min` and `max` and of the compositions built on them
(`clamp`, `clamp01`, `ramp`, `piecewise`), because it is the difference
of two exact evaluations. A law whose increment is zero although its
source moved SHALL contribute nothing, which is what disengagement is.
A law whose expression contains a DISCONTINUOUS primitive SHALL
contribute the sum of its change over the continuous pieces between its
crossings, under the requirement "A jump is located inside the tick and
subtracted"; every other rule of this requirement applies to it
unchanged.

The tick SHALL be: every input's increment is the movement its active
command admits for the tick, zero with no command; increments SHALL then
propagate over the relation graph in the direction each relation was
solved by the rest render — forward through a law, backward through an
invertible one, identity through a wiring into a bank coordinate,
forward or backward through a derived coordinate's linear formula —
every source of a relation naming several being determined before it
contributes. A coordinate no increment reaches SHALL HOLD its committed
value. Two increments that disagree on one coordinate — beyond
`1e-9 · max(1, |a|, |b|)` — SHALL be a CONFLICT, refused naming the
formula or relation that predicted each and the coordinate; a joint
coordinate whose new value would leave its declared range SHALL be
refused naming the joint, the value and the range. A tick that fails
SHALL commit nothing: the bank, the tick count and the bound tree stand
as before, and every command that moved an input in that tick is
retired reporting `refused`. A tick that succeeds SHALL commit the
increments, advance the tick count, bind the whole snapshot through
`set_state` with `time` at `k*dt`, record if recording is on, and only
then run due actions and cadences.

Derived coordinates and plain ports SHALL NOT be stored: the ordinary
enumeration computes them from the run-bound terms on every tick.

#### Scenario: Moves accumulate and an affine chain follows

- **WHEN** a running root states `crank.drives(first.turn, ratio=2.0)`
  and `first.turn.drives(second.turn, ratio=-1.5)`, and the simulation
  moves `crank` by `10` over one second twice
- **THEN** the bank reads `crank == 20`, `first.turn == 40` and
  `second.turn == -60`, and the leaves stand at those angles

#### Scenario: A law with a kink integrates exactly

- **WHEN** `lever.drives(slide.travel, law=tooth_window)` carries
  `4 + 72 * clamp01((angle − 113.5) / 11.25)` and `lever` moves from
  `100` to `140` in eight ticks of five degrees
- **THEN** `slide.travel` reads exactly `13.6` after the third tick,
  `45.6` after the fourth, `76.0` from the fifth on, and stays `76.0`
  while the lever goes on to `140`

#### Scenario: Backward propagation through an invertible law

- **WHEN** a running root states `crank.drives(first.turn, ratio=2.0)`
  and `second.turn.drives(first.turn, ratio=4.0)`, so the rest render
  solved the second relation backward, and `crank` moves by `10`
- **THEN** `first.turn` reads `20` and `second.turn` reads `5`, the
  inverse of the affine law having propagated the increment

#### Scenario: An undriven joint holds while an unrelated input moves

- **WHEN** the crank of the same root moves while `lever` has no command
- **THEN** `slide.travel` and `lever` read exactly what they read before
  the move, on every tick

#### Scenario: Two inputs prescribing one rigid group inconsistently are refused

- **WHEN** a running root declares `wrist` and `tool` joints,
  `left = wrist + 2 * tool`, and states `wrist_in.drives(wrist)`,
  `wrist.drives(tool, ratio=1.0)` and `sum_in.drives(left)`, and the
  simulation moves `wrist_in` by `10` while `sum_in` has no command
- **THEN** the tick is refused naming `left`, the formula, the relation
  from `sum_in` and the two increments `0` and `30`; the bank, the tick
  count and the tree are unchanged; the move's handle reports `refused`
  with no travel admitted

#### Scenario: The same group moved consistently is admitted

- **WHEN** the same simulation moves `wrist_in` by `10` and `sum_in` by
  `30` over the same duration
- **THEN** every tick is admitted and the bank reads `wrist == 10`,
  `tool == 10` and the derived `left` reads `30`

#### Scenario: A joint's range fails the tick in this cycle

- **WHEN** `first.turn` declares `range=(-90, 90)` and the crank is moved
  so that `first.turn` would reach `100`
- **THEN** the tick that would cross the range is refused naming
  `first.turn`, `100`, the range and the unit, and the bank stands at the
  last admitted tick

### Requirement: A relation's law is compiled to an expression over coordinate ids

At construction under a running root the system SHALL COMPILE the
relations the rest render solved into a program over the bank: each
relation's law SHALL be applied ONCE to a symbolic token per source
coordinate, in the direction the rest render solved it, and the
expression graph that application builds — over the qualified ids of
the sources — SHALL be what the run evaluates on every tick and what
the refusals below inspect. A graph containing a DISCONTINUOUS
primitive — a call to `floor`, `ceil` or `sign`, the `%` operator, or a
comparison — SHALL additionally be compiled into a JUMP PLAN: its jump
nodes in the graph's postorder, each with the level quantity whose
surfaces it crosses, the graph of that level quantity with the jump
nodes inside it replaced by branch placeholders, whether that level
quantity is AFFINE in the sources, and the SKELETON of the whole
expression with every jump node so replaced. A wiring into a bank
coordinate SHALL be an
identity edge and a derived coordinate a linear edge. A relation or
wiring none of whose driven ends is, or reaches through such
intermediates, a bank coordinate SHALL be left to the ordinary
enumeration. The program SHALL have an IDENTITY derived from the root
class, the bank's ids, the inputs' declarations and every edge's ends,
direction and expression.

The system SHALL refuse, at construction and by relation identity —
naming the relation as written and the class that stated it:

- a law that cannot be applied to symbols — one that raises when handed
  a symbolic token, returns something that is neither a number nor an
  expression, or whose expression holds text the framework cannot
  evaluate or a call outside the symbolic vocabulary — saying that a
  running law is an expression over its sources;
- a relation or wiring INTO a bank coordinate whose source is a
  coordinate the run does not own and no compiled edge computes — a
  plain port the author's `simulate()` binds — saying to state that
  value as a relation or a joint;
- a relation naming several driven ends of which some are bank
  coordinates and some are not;
- a law whose expression contains a DISCONTINUOUS primitive and none of
  whose driven ends is a coordinate the run owns — a plain port or a
  derived coordinate the ordinary enumeration recomputes from the bank
  on every tick — saying that a subtracted jump implies a history,
  that only a coordinate the run owns keeps one, and that the relation
  should be stated into the joint coordinate so the port follows it.

A law whose expression has no free coordinate — a constant — SHALL
compile and contribute a zero increment; a law that can move its
coordinate only by jumping SHALL be refused under the requirement "A
law that can only jump is refused as arithmetic".

#### Scenario: A running root with a floor in a law compiles

- **WHEN** a running root states `crank.drives(first.turn, law=window)`
  where the law's expression contains `floor(angle / 360)`
- **THEN** construction succeeds, the compiled graph names the source's
  qualified id, its jump plan holds one `floor` node whose level
  quantity is that qualified id divided by 360 and is AFFINE in the
  sources, and the same root without `Time.running()` poses exactly as
  before

#### Scenario: A jumping law into a plain port is refused

- **WHEN** a running root states `crank.drives(register, law=window)`
  where `register` is a plain port wired to a joint coordinate and the
  law's expression contains `floor`
- **THEN** construction is refused naming the relation and the port, and
  saying to state the relation into the joint coordinate the run owns;
  and the same relation stated into that joint coordinate compiles

#### Scenario: A law over stdlib math is refused as non-symbolic

- **WHEN** a running root's law computes `math.sin(angle)` from Python's
  standard library
- **THEN** construction is refused naming the relation and saying the law
  cannot be applied to symbols

#### Scenario: A relation sourced from an author-bound port is refused

- **WHEN** a running root's `simulate()` binds a plain port from its
  crank and a relation drives a joint from that port
- **THEN** construction is refused naming the relation and the port, and
  advising a relation or a joint

#### Scenario: A law with a kink compiles

- **WHEN** a running root's law is `4 + 72 * clamp01((angle − 113.5) / 11.25)`
- **THEN** construction succeeds and the compiled expression names the
  source's qualified id and only `min` and `max` among calls

### Requirement: Recording is explicit and bounded under a running root

Under a running root the simulation SHALL keep no per-tick record unless
asked: `Sim(..., record=None)` keeps nothing and `sim.trajectory` reads
empty; `record=N`, a positive integer, keeps a ring of the most recent
`N` `(tick, bank)` entries readable oldest first; any other value SHALL
be refused naming the option. Restore and reset SHALL clear the ring.
Unbounded recording SHALL NOT be offered under a running root.

`record=N` SHALL additionally keep a SECOND ring, of the most recent
`N` CROSSINGS located inside a tick, readable through `sim.crossings`
oldest first, each entry naming the tick, the relation as written, the
driven coordinate, the primitive that jumped, the surface value in the
level quantity's own units, and the fraction of the tick at which it
was crossed. Entries SHALL be appended in order of that fraction within
a tick, in the graph's postorder where two coincide, and in program
order across relations. `record=None` SHALL keep no crossings and build
none. Restore and reset SHALL clear both rings.

#### Scenario: Nothing is recorded by default

- **WHEN** a running simulation steps ten thousand ticks with no `record`
  option
- **THEN** `sim.trajectory` and `sim.crossings` are both empty and the
  run's memory does not grow with the tick count

#### Scenario: The crossing ring names the relation and stays bounded

- **WHEN** `Sim(node, dt, record=4)` runs a periodic law through six
  window boundaries
- **THEN** `sim.crossings` holds exactly four entries, the last four,
  each naming the relation as written, the driven coordinate, `'floor'`,
  the integer surface it crossed and a fraction in `[0, 1]`

#### Scenario: A ring keeps the most recent ticks

- **WHEN** `Sim(node, dt, record=64)` steps one hundred ticks
- **THEN** `sim.trajectory` holds exactly sixty-four entries, for ticks
  37 through 100, oldest first

#### Scenario: An invalid recording option is refused

- **WHEN** `record=0`, `record=-1`, `record=True` or `record='all'` is
  given
- **THEN** construction is refused naming `record`

## ADDED Requirements

### Requirement: A jump is located inside the tick and subtracted

Under a running root a law whose expression contains a DISCONTINUOUS
primitive SHALL contribute, over one tick, the CONTINUOUS part of its
change: the tick's path SHALL be cut at every crossing of every jump
surface it meets, and the law's change SHALL be summed over the pieces
between those cuts, so that no jump ever moves a part.

The PATH of a tick SHALL be the straight line from the values the law's
sources hold to those values plus the increments they were given,
parametrised by a fraction `t` in `[0, 1]` — in the JOINT space of the
sources for a law naming several. A tick in which no source moves SHALL
contribute zero without evaluating the law.

Each jump node SHALL have a LEVEL QUANTITY and a family of SURFACES:
`floor(x)` and `ceil(x)` over `x` at every integer; `sign(x)` over `x`
at zero; `a % b` over `a / b` at every NONZERO integer, the operator
being the remainder that takes the sign of the DIVIDEND and is
therefore continuous where `a / b` crosses zero; a comparison over
`a − b` at zero. `wrap()` SHALL be integrated as the `ceil` it is built
on, and `piecewise()` SHALL need nothing, being built on `clamp01`.

On each open piece between two cuts every jump node SHALL hold one
BRANCH — the integer for `floor` and `ceil`, `-1`, `0` or `+1` for
`sign`, the integer quotient for `%` so that the node reads `a − q·b`,
and `1` or `0` for a comparison — determined by evaluating its level
quantity at the MIDPOINT of that piece, in the graph's postorder so
that a jump nested inside another's argument is determined first. The
law with those branches substituted SHALL be continuous on the closed
piece, and the increment SHALL be the sum, over the pieces, of that
substituted law's value at the piece's end minus its value at the
piece's start. A piece's endpoints SHALL therefore carry the one-sided
values of the law, at the tick's own start and end as well as at each
cut.

Crossings SHALL be found for every jump node of the law, in the graph's
postorder, over each piece the nodes before it have already produced,
and ALL crossings of one node inside one piece SHALL be found — not
only the difference of the piece's endpoints. Where the level quantity
is AFFINE in the sources along the path the crossings SHALL be solved
exactly, every surface between the endpoint values included; otherwise
the piece SHALL be sampled at a fixed number of sub-intervals and each
bracketed crossing located by bisection to a stated tolerance, with the
limit of that search documented. Two crossings closer than the
tolerance SHALL be one cut, and several jump nodes crossing at one
fraction SHALL be one cut whose midpoint sample fixes every branch at
once.

A tick that would cut one law's path more than a stated maximum number
of times SHALL be refused naming the relation, the driven coordinate,
the primitive and the count, and SHALL commit nothing — the bank, the
tick count and the bound tree standing as before and the commands that
moved an input in it retired reporting `refused` — exactly as a
conflict does. A `%` whose divisor is zero anywhere the tick evaluates
SHALL be refused the same way.

#### Scenario: A periodic window advances once per revolution

- **WHEN** a running root states
  `crank.drives(pinion.turn, law=periodic_window)` carrying
  `4 + 72 * clamp01((angle − 360 * floor(angle / 360) − 113.5) / 11.25)`,
  the crank rests at `100`, `dt` is `1/240`, and the simulation moves
  `crank` by `360` over one second, twice
- **THEN** `pinion.turn` reads `4` before the first move, `76` after it
  and `148` after the second, and the tick in which the crank passes
  `360` contributes exactly zero

#### Scenario: A tick that passes three windows adds three throws

- **WHEN** the same root is given `move('crank', by=1080, duration=0)`
  from a crank of `100`
- **THEN** `pinion.turn` reads `220`, three crossings are located inside
  that one tick, and the crank stands at `1180`

#### Scenario: A gate holds open and re-engages without a jump

- **WHEN** a running root states
  `(shaft.turn & sleeve.travel).drives(wheel.turn, law=clutch)` carrying
  `-2 * shaft * (sleeve > 0.5)`, and the shaft turns by `4` over a tick
  in which the sleeve stands at `0`, then over a tick in which it
  stands at `1`, then over a tick in which it travels from `0` to `1`
- **THEN** `wheel.turn` moves by `0`, then by `-8`, then by `-4` — the
  travel after engagement only — and never by the value the gate factor
  would have jumped to

#### Scenario: A wrapped law integrates to the unwrapped travel

- **WHEN** a running root's law is `2 * wrap(angle, 360)` and the crank
  travels `500` degrees from `100`
- **THEN** the driven coordinate gains exactly `1000`, and the two
  `ceil` crossings inside that travel contribute nothing of their own

#### Scenario: A remainder window and a floor window agree

- **WHEN** two running roots carry the same tooth window, one written
  with `angle − 360 * floor(angle / 360)` and one with `angle % 360`,
  and both cranks are moved through one revolution from `100`
- **THEN** both driven coordinates read the same value at every tick

#### Scenario: A sign that does not jump integrates as its continuous twin

- **WHEN** a running root's law is `5 * (x − 50) * sign(x − 50)` and a
  second root's is `5 * abs(x − 50)`, and both are driven across `50`
- **THEN** both driven coordinates read the same value at every tick,
  the crossing of `sign` having been located and contributed nothing

#### Scenario: A jump nested in another jump's argument

- **WHEN** a running root's law engages only on alternate revolutions,
  `72 * clamp01((angle − 360 * w − 113.5) / 11.25) * (1 − (w − 2 * floor(w / 2)))`
  with `w = floor(angle / 360)`, and the crank is moved through four
  revolutions from `100`
- **THEN** the driven coordinate reads `72` after the first revolution,
  `72` after the second, `144` after the third and `144` after the
  fourth

#### Scenario: The same movement split differently gives the same answer

- **WHEN** one running simulation takes a revolution of the crank in a
  single tick, another in twelve, and another in two hundred and forty
- **THEN** all three leave the driven coordinate at the same value

#### Scenario: A tick that would cross too many surfaces is refused

- **WHEN** a periodic law is driven far enough in one tick to cross more
  surfaces than the stated maximum
- **THEN** the tick is refused naming the relation, the coordinate, the
  primitive and the count; the bank, the tick count and the tree are
  unchanged; and the move's handle reports `refused`

### Requirement: A law that can only jump is refused as arithmetic

Under a running root the system SHALL REFUSE, at construction and by
relation identity — naming the relation as written and the class that
stated it — a law that can move its driven coordinate only by jumping:
the law's expression with every jump node, and the whole argument
subtree beneath it, replaced by a constant SHALL be examined, and a law
whose expression so reduced holds no free coordinate SHALL be refused.
The message SHALL say that every jump is subtracted, so such a law can
never move the coordinate, and that it states arithmetic rather than a
mechanism.

A law whose reduced expression still holds a free coordinate SHALL
compile, whatever else it contains.

#### Scenario: A law that is only a step counter is refused

- **WHEN** a running root states `crank.drives(dial.value, law=counter)`
  whose expression is `floor(turns)`
- **THEN** construction is refused naming that relation and saying the
  law can only jump and states arithmetic rather than a mechanism

#### Scenario: A jump beside a sloped term compiles

- **WHEN** a running root's law is `9 * enabled + floor(turns)` over two
  sources
- **THEN** construction succeeds, because `enabled` still carries slope,
  and moving `turns` alone moves the coordinate not at all

#### Scenario: A periodic window is not a law that only jumps

- **WHEN** a running root's law is
  `4 + 72 * clamp01((angle − 360 * floor(angle / 360) − 113.5) / 11.25)`
- **THEN** construction succeeds, the reduced expression still naming
  `angle`
