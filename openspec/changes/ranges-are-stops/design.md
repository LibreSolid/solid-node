## Context

Cycle 1 made the run own every driver and joint coordinate and
integrate every continuous law over a tick. Cycle 2 made a law that
jumps integrate too, by cutting the tick's path at the crossings of its
jump surfaces and summing the branch-substituted law over the pieces.
Both left a joint's declared `range` exactly where cycle 1 put it: a
coordinate that would leave its range FAILS the tick.

`Run._check_spans` is the whole of it today:

```python
def _check_spans(self, committed, moved):
    for identifier, low, high, unit in self.spans:
        value = committed[identifier]
        if low <= value <= high:
            continue
        self._refuse(moved)
        raise JointRangeError(...)
```

so a machine that reaches a stop cannot be stepped past it. The bank
stands at the last admitted tick, the commands that moved retire
`refused`, and the caller's only recourse is to have asked for less.
That is a refusal of the AUTHOR's declaration, not a model of a
mechanical limit.

Two mechanisms in the campaign need the mechanical reading:

- the Pascaline module's ratchet — ten 36° teeth on the input arbor, a
  flexible blade, no pawl lift, so forward is free and reverse is
  blocked at the last seated tooth. The module declares
  `turn = Revolute(axis=(1, 0, 0))` with no range at all, and the blade
  is a `SignalPort` deflection: nothing in the model blocks reverse
  today, which its acceptance record states as an open gap;
- the spike's swept stop — a rack stopping at its limit inside a tick
  while an independent motor runs its full tick, with the rack's
  command reporting `blocked` and the admitted travel.

The spike proved both (`workflow/open-run-simulation/spikes/kernel.py`,
`stops`, `_velocities`'s blocked-group logic, `_step`'s stop
localization) and recorded the gap this cycle has to close: *"The
current spike deliberately refuses automatic continuation of a blocked
finite move; precise fractional progress/replanning remains a required
design item for production."*

The reverse refusal cycle 1 wrote says the same thing from the other
side:

```python
raise ValueError(
    f"move('{input_id}', ...) would travel backwards ... A "
    f'reverse move is refused in this cycle: reverse travel '
    f'meets no stop until a joint range becomes a physical stop.')
```

This cycle is the stop, and the reverse move follows from it.

Everything it needs is already in the tree. Cycle 2 established the
tick's PATH — the straight line in the sources' joint space,
parametrised by `t` in `[0, 1]` — the affine/searched split, and the
three tolerances (`_CROSSING_TOLERANCE`, `_SUBDIVISIONS`,
`_BISECTION_ROUNDS`). A stop is one more level quantity on that same
path: `V_c(t) − bound`, where `V_c` is the coordinate's value along the
tick. Nothing new is invented; the machinery is pointed at a second
kind of surface.

## Goals / Non-Goals

Goals:

- A joint's `range` is a physical stop under a running root: the
  coordinate stops AT the bound, inside the tick, and the tick commits.
- The stop stops the connected group and nothing else.
- A command on a stopped input retires `blocked`, reporting the travel
  it actually admitted, fractional within the tick and exact.
- A blocked command never resumes by itself.
- Reverse moves and reverse rates are admitted.
- A range bound may be an expression over the joint's own coordinate,
  evaluated at the committed state, so a ratchet's lower bound is the
  last seated tooth.
- Stops are recorded, bounded, beside the crossings.
- A tick without a stop costs what it costs today.

Non-Goals:

- No change to untimed or looping documents, where a range still
  REFUSES a binding outside it rather than clamping.
- No clamp anywhere. A stop is located and the motion is truncated at
  it; a value is never silently moved into range.
- No force, no detent, no contact state, no restitution. A stop is a
  kinematic bound on one coordinate.
- No `Driver` range clamping. It stays presentation metadata.
- No bound naming ANOTHER coordinate in this cycle (decision 10).
- No export of the program, no viewer, no memory, no declared events.
- No general collision or interference stop. A stop is declared on a
  coordinate, not found between two meshes.

## Decisions

### 1. What a stop is, and where the run notices it

A stop is a bound of a banked joint coordinate's declared range. Under
a running root, when the committed value of coordinate `c` at the end
of the stretch being integrated would lie outside a bound AND lie
further outside than it did at the START of that stretch, `c` reaches
that bound at a fraction `t*` of the tick and the motion is truncated
there for `c`'s group. For an unsegmented tick the stretch is the whole
tick; after a stop it is the remaining segment, and a coordinate frozen
by that stop does not move over it and so cannot stop again.

Detection is by the TICK'S COMMITTED VALUE, exactly the comparison
`_check_spans` makes today. That is deliberate:

- it costs what it costs today on a tick that does not block — one
  comparison per ranged coordinate, and this cycle's whole performance
  story rests on that;
- it needs no extra evaluation of anything.

Its limitation is stated openly: a coordinate that passes its bound and
returns INSIDE one tick is not stopped. That is the same class of
limitation cycle 2 already accepts for a level quantity that turns
twice inside one sub-interval, and it has the same answer — a smaller
`dt`. For a coordinate whose determiner is affine along the path (the
common case, and every case in the two originating projects) it cannot
happen at all, because `V_c` is then monotone in `t`.

*Rejected: sampling every ranged coordinate at `_SUBDIVISIONS` points
every tick to catch an excursion.* It would make every tick of a ranged
machine pay 64 evaluations per ranged coordinate for a case that cannot
arise for an affine determiner, and it would still only push the
limitation one resolution finer rather than remove it.

The direction test matters as much as the bound test. For the low
bound `B`, a stop occurs when

```text
V_c(1) < B   and   V_c(1) < v_c(0)
```

— outside, and moving further outside, both read over the stretch being
integrated. A coordinate already at or below
`B` that moves UP is free, which is what lets a blocked move be undone
by a move the other way; a coordinate that does not move at all is free
by the same test, which is why a frozen coordinate standing on its
bound raises nothing and divides by nothing. Symmetrically for the high
bound. Both bounds
stay INCLUSIVE, as the joints spec already says, so a tick landing
exactly on a bound is not a stop at all: the comparison
`low <= value <= high` passes and nothing happens. That is the whole of
"a move that lands exactly on the bound is `completed`".

### 2. Localizing `t*`: the coordinate's value along the path

`c`'s value along the tick is

```text
V_c(t) = v_c(0) + I_E(t)
```

where `v_c(0)` is the committed value at the tick's start and `I_E(t)`
is the increment `c`'s DETERMINER EDGE `E` gives over the path
truncated at `t`. Cycle 2 already computes exactly that: `E.increments`
reads its sources at `start` and at `start + delta`, and the truncated
path is the same call with every source delta multiplied by `t` —

```python
I_E(t) = E.increments(values, {key: delta[key] * t for key in ...})[c]
```

— because `_along(start, delta * t, s)` for `s` in `[0, 1]` IS the
tick's path up to `t`. So the truncated increment costs ONE edge
evaluation for a continuous law, and one jump-plan partition-and-sum
for a law that jumps. No new integration code.

`V_c` is continuous in `t`, `V_c(0) = v_c(0)` and `V_c(1)` is the
committed value the detection compared. The stop is the SMALLEST `t` in
`[0, 1]` at which `V_c(t)` reaches the bound; when `v_c(0)` is already
at or beyond it, `t* = 0`.

Three cases, decided at compile time by `Edge.affine`, the per-driven-end
classification computed with the existing `_affine_in_sources`:

1. **Affine, no jump plan.** `V_c` is linear in `t`, so
   `t* = (B − v_c(0)) / Δ_c` where `Δ_c` is the full-tick increment
   already computed. One division, EXACT, no extra evaluation. This is
   the ratchet, the rack, every wiring edge and every derived
   coordinate's linear formula.
2. **Affine skeleton with a jump plan.** `V_c` is piecewise affine in
   `t`, with breakpoints at the plan's own cuts. The cuts come from
   `JumpPlan.cuts()` — `_partition` made reachable, the same call the
   increment already makes — `V_c` is evaluated at each cut, and `t*`
   is solved linearly inside the piece that brackets the bound. Exact.
3. **Anything else.** `V_c` is sampled at `_SUBDIVISIONS` points of
   `[0, 1]`, the first sub-interval whose endpoints bracket the bound
   is taken, and `t*` is bisected to `_CROSSING_TOLERANCE` in at most
   `_BISECTION_ROUNDS` rounds — the same three tolerances, the same
   `_bisect` shape, the same documented guarantee as a searched jump
   crossing.

A banked joint coordinate that NO edge determines cannot move, so it
cannot leave its span; an input is never a joint coordinate (the run
refuses an id claimed twice), so a stop is always on a driven end.

*Rejected: defining `V_c(t)` as the increment a full PROGRAM pass gives
with every input's admission scaled by `t`.* It is exactly consistent
with the way a segment is later committed, and a chain of nonlinear
laws would land the stopped coordinate on its bound to the last bit
without the correction of decision 4. It costs a full program pass per
sample: up to `_SUBDIVISIONS + _BISECTION_ROUNDS` passes on a blocking
tick, about 137 ms at cycle 2's measured `Train` tick. The per-edge
model is the one the pilot's decision names ("its determiner edge's law
along the straight path in source space"), it is exact for every affine
chain, and decision 4 removes the only consequence of the difference.

Stated as a boundary, and carried into ADR-108: `t*` is EXACT when
every edge between the pushing inputs and `c`'s determiner is affine —
the ratchet, the rack, every wiring and every linear formula, and both
originating projects. For a NONLINEAR upstream edge the group's OTHER
coordinates are stopped at a `t*` located on the linearized upstream
path, while `c` itself is committed at its bound exactly; a smaller
`dt` shrinks that difference, and the full-program search stays the
documented exact alternative.

### 3. The connected group: the inputs that push the stopped coordinate

When `c` stops, these stop with it:

- every INPUT whose movement over the current stretch actually PUSHES
  `c`. The CANDIDATES are the inputs that reach `c` through the compiled
  program — a static table, `Program.sources`, computed once — and a
  candidate is IN the group when, with its own admission for the stretch
  applied and every other input's set to zero, the program's edges
  between it and `c` give `c` a nonzero increment;
- and, by propagation, everything those inputs alone determine.

The candidate table is computed ONCE, at compile time, in one pass over
the already topologically ordered edges:

```python
sources[key] = frozenset({identifier})          # for each input
for edge in program.edges:                      # already ordered
    reached = union(sources[key] for key in edge.needs)
    for key in edge.gives:
        sources[key] |= reached
```

A `check` edge gives nothing and contributes nothing to it.

The contribution test runs only on a BLOCKING tick, once per candidate
with a nonzero admission over the stretch, as one propagation over the
edges between that candidate and `c`; a non-blocking tick pays nothing.
It is well defined at `t* = 0` because it uses the stretch's REQUESTED
admissions, not the travel admitted so far (which is zero there). An
input coupled to `c` only through a law that is currently disengaged —
an open clutch, a carry outside its window — contributes nothing and is
NOT stopped: the crank keeps turning while the wheel behind the open
clutch stands at its stop, and a column's ratchet blocking does not
stop the previous column's dial unless the carry is in its window. A
multi-source law whose contributions are not separable (a product of
two moving sources) counts an input as pushing whenever its motion
alone changes `c`, which is the honest kinematic answer for an engaged
coupling.

The second half — "everything those inputs alone determine" — needs no
computation at all: the stopped inputs' admissions are set to ZERO for
the rest of the tick and the ordinary propagation of cycles 1 and 2
does the rest. A coordinate fed only by stopped inputs receives zero
and HOLDS; a coordinate fed by a stopped input and a free one receives
what the free one contributes, because a multi-source law reads its
whole source vector and one of them stopped moving. Nothing in the
propagation, the conflict test or the rollback changes.

The candidate table is a property of the PROGRAM, which is what cycle 4
publishes; the contribution test is a property of the tick, and the
browser worker runs the same test over the same table.

*Rejected: the spike's rule, zeroing the whole connected COMPONENT of
the relation graph.* The spike works over undirected velocity
components; the compiled program is directed and acyclic, and a
component would stop inputs that cannot influence `c` at all — the
motor beside the rack, if anything anywhere coupled them.

*Rejected: the purely STATIC group, every input reaching `c` through
the program.* Cheaper by one pass per candidate on a blocking tick, but
wrong in a stated direction: it stops an input coupled to `c` only
through a disengaged law, so an open clutch would stop its crank. The
adversarial review of this proposal required the contribution test;
the static table stays as the candidate set.

### 4. The tick becomes segments, and the tick stays atomic

A tick with one stop is integrated as TWO sub-ticks:

- segment A over `[0, t*]`: every input's admission for the tick
  multiplied by `t*`;
- segment B over `[t*, 1]`: the stopped inputs' admission zero, every
  other input's multiplied by `1 − t*`.

Each segment is integrated by exactly the procedure cycles 1 and 2
state — the same edge order, the same propagation, the same conflict
test, the same jump partition over its own shorter path. The pass is
today's `integrate` body lifted into one method; the segment loop is
the only new control flow.

The STOPPED coordinate is committed AT its bound, exactly, rather than
at what segment A's arithmetic produced for it. The reason is not
tidiness: `Run.bind()` delivers the bank through `set_state`, and a
joint coordinate binding goes through the joint's own range check. A
localization that left the coordinate a few ulps outside its bound
would make the very tick that was supposed to stop it raise
`JointRangeError` from the binding. Committing the bound is what makes
the stop land ON the surface by construction, and it absorbs the
per-edge model's only inexactness (decision 2's rejected alternative).
Its cost is that the group's other coordinates may stand a few ulps
from perfect consistency with the stopped one; that is far inside the
`1e-9` relative agreement the run already calls equal, and no conflict
is raised because the correction happens after propagation.

The tick remains ATOMIC. The bank, the commands' admitted travel and
the two record rings are STAGED across the segments and applied only
when every segment has succeeded. A conflict, a `TooManyCrossings` or
an unintegrable law in ANY segment refuses the whole tick: the bank,
the tick count and the tree stand as before, the commands that moved
retire `refused`, and nothing is recorded. One `set_state` per tick,
as the purity contract requires.

One consequence is stated rather than hidden: the detection pass runs
over the FULL tick path, so a law that cannot be integrated somewhere
between `t*` and `1` refuses the tick even though the stopped group
never travels there. Cycle 2 already refuses a tick whose path meets a
zero divisor; a stop does not rescue it. Open question 4.

### 5. Several stops in one tick

After segment B is integrated, it is examined for a stop exactly as the
full tick was, and the process repeats on the remainder. Within ONE
examination several coordinates may be outside their bounds; each is
localized and the SMALLEST `t*` is taken. Two stops whose `t*` are
within `_CROSSING_TOLERANCE` of each other are ONE event — one entry
per stopped coordinate in the record, one segment boundary, the union
of their groups stopped together — whether they are on one group or on
two. Ties are therefore never resolved by ordering; there is no
ordering to get wrong.

The iteration terminates for a reason that needs no constant: every
event stops at least one input that was moving (a coordinate that left
its bound was moved by something, and everything that moves it is in
its group), and a stopped input stays stopped for the rest of the tick.
So a tick has at most as many stop events as it has inputs admitting
travel, and at most one more segment than that. The loop carries that
count as its bound and raises an internal refusal if it is ever
exceeded, which would mean the invariant is broken rather than the
model is coarse.

*Rejected: taking every simultaneous out-of-range coordinate as one
event regardless of `t*`.* Cheaper by one localization per extra
coordinate, and wrong: the rack that reaches its limit a quarter of the
way through the tick would otherwise go on driving its group until the
lever reached its own limit later in the same tick.

### 6. `blocked`: what it means, and what it admits

At a stop event, every ACTIVE command whose input is in the stopped
group is retired with status `blocked`:

- `status` becomes `blocked`, the command leaves `sim.commands`, and
  the input's ownership is released, so a new command may be issued at
  once. This is the same retirement `refused` performs, with a
  different word and a different meaning: `refused` says the tick did
  not happen, `blocked` says it did and the machine would not go
  further.
- `admitted` is the travel the command ACTUALLY made, in design units:
  the travel it admitted on every completed tick before this one, plus
  `t*` of the travel it was admitting on this one. It is fractional
  within the tick and it is the number the caller replans from. This is
  the spike's recorded design item — "precise fractional progress" —
  and it is the whole of the answer to it.
- a `rate` on a stopped input is retired `blocked` too, with the travel
  it had made. A rate is not a promise of a total, but it is a command,
  and the one thing this cycle will not do is let a machine push
  silently against a stop for ever.

A blocked command NEVER resumes. There is no backlog anywhere: nothing
remembers the travel it did not make, and a later tick that could move
does not move it. The caller issues a new command, which may move away
from the stop (free, up to whatever it meets next) or push into it
again and be blocked at once with `admitted == 0`. That rule is the
spike's, made permanent: `pause(group, False)` there raises on a
blocked group because a blocked move needs an explicit replan.

*Rejected: keeping a blocked move active and letting it resume when the
bound moves away.* It is the auto-resume the spike refused. A move
whose remaining travel is waiting for a mechanism to release is a
promise the run cannot keep honestly: it would have to decide when a
stop has "gone", it would resume in a direction the caller stated
ticks ago, and a run with one blocked move quietly pending is exactly
the hidden backlog the pilot's decision rules out.

*Rejected: `blocked` per rigid group rather than per command,* the
question cycle 1 left open. Each command reports for ITSELF, because a
command owns one input and a group is not a thing a caller holds. The
group is visible in the stop record, which names the inputs it blocked.

### 7. An instruction naming several inputs

`trigger(name)` returns a TUPLE of handles, one per input the
instruction names, and each reports for itself. An instruction naming
two inputs where only one is stopped therefore reports one `blocked`
handle with fractional admitted travel and one `completed` handle with
its full travel. The free input is NOT held back to keep the
instruction's inputs in step: an instruction is a set of simultaneous
requests, not a rigid group, and cycle 1 already made each of its
commands an independent owner of its own input.

No summary object is owed. The tuple IS the report, and adding a
second status vocabulary over it — an instruction-level `blocked` —
would have to answer "blocked when how many of them blocked?" with an
arbitrary rule. A caller that wants the instruction's verdict writes
`any(h.status == 'blocked' for h in handles)`, which is exact and says
what it means.

### 8. Reverse moves are admitted

The three refusals in `Run.move` and `Run.rate` go. A negative `by`, a
`to` below the committed value and a negative `rate` are ordinary
requests; they meet stops exactly as forward ones do, by the same
comparison against the other bound.

Two details come with them:

- `RampProgram` already distributes a negative delta correctly: its
  integer form is `start + (delta * k) // ticks`, whose floor division
  on a negative delta stays monotone, never passes the target in
  between, and lands exactly on it at `k == n` (`-10` over four ticks
  gives `-3, -5, -8, -10`). It does FRONT-LOAD a reverse ramp where a
  forward one back-loads it, and it is left exactly as it is: a
  downward `targets=` ramp already exists under a looping root, so its
  distribution is ratified behaviour and a cycle about stops does not
  touch it.
- `Command._cumulative` floors a rate's cumulative travel for an
  integer input. Floor on a negative rate makes the state LEAD the
  ideal by up to one native unit where a positive rate LAGS it. It
  becomes `math.trunc`, which is identical for every value the current
  behaviour admits — a negative rate is refused today, so nothing
  already ratified changes — and makes the two directions round the
  same way. Neither choice affects a stop: the travel admitted up to a
  stop is the distance to the bound, whatever the distribution.

A `Driver`'s own declared `range` is untouched: it is presentation
metadata in design units and nothing clamps to it, because a machine
driven past its declared travel is a crash a simulation must be able to
SHOW. A stop is a joint's, not a driver's.

### 9. An expression-valued range

**Declaration.** Either bound of the `(lo, hi)` pair may be:

- a number, a declared-parameter token or a derived formula — today's
  meaning, unchanged;
- `None`, meaning unbounded on that side;
- a CALLABLE OF ONE ARGUMENT, which the framework applies once to the
  joint's own coordinate and which returns an expression in
  `solid_node.math`'s vocabulary.

The ratchet is then

```python
class InputArbor(AssemblyNode):
    turn = Revolute(axis=(1, 0, 0),
                    range=(lambda turn: 36 * floor(turn / 36), None))
```

which reads as what it is: the lower bound is the last seated tooth,
and there is no upper bound because forward rotation is free.

The form is a callable INSIDE the pair, which is what keeps it apart
from the callable `range` the joints spec already admits —
`range=lambda node: (lo, hi)`, called with the realized declarer and
returning numbers. The two are distinguished by POSITION, not by arity:
a callable given as the whole `range` is the node form; a callable
given as a bound is the expression form. Nothing existing changes
meaning.

*Rejected: a new keyword, `detent=` or `stop=`, beside `range=`.* A
joint would then have two ways to say where it may travel, they would
have to be reconciled (which wins? do they intersect?), and untimed
posing would have to choose one. A range is already the declaration of
where a coordinate may be; this makes its bound able to depend on where
the coordinate IS.

*Rejected: a bound stated as an expression directly,
`range=(36 * floor(turn / 36), None)`, with `turn` a module-level
token.* There is no such token at class-body time: the joint owns the
coordinate and names it only when `__set_name__` runs. A callable of
one argument is how the class body can refer to a coordinate that does
not exist yet, and it is exactly how `at=lambda node: ...` already
refers to a node that does not exist yet.

**Compile.** Under a running root the bound is compiled ONCE, at `Sim`
construction, exactly as a law is: applied to `symbol(name)` for the
coordinate's qualified id, the graph walked for raw text and for calls
outside `SYMBOLIC_BUILTINS`, refused by joint and node identity when it
is neither a number nor an expression over that one coordinate. Jumps
are ALLOWED and need no plan: the bound is EVALUATED at one point per
tick, never integrated, so `floor` means `floor` and nothing is
subtracted. That asymmetry with a law is the point — a law's jump would
move a part, a bound's jump is the tooth pitch.

The compiled bound joins the program: `Program.spans` carries, per
banked coordinate, the low and high bound as a number, `None`, or a
graph, and `Program.described()` names them, so the program IDENTITY
changes when a range changes and a snapshot cannot be restored into a
machine whose stops have moved.

**Evaluate.** The bound is evaluated ONCE PER TICK, at the tick's
START, from the committed bank — before any segment, so every segment
of a tick sees the same number and the localization of decision 2 has a
constant to solve against. Within a tick the bound is a number; between
ticks it follows the machine. The self-reference is well defined
because the value it reads is committed and the value it bounds is not
yet.

That quantizes the detent to the tick, which is correct rather than
merely tolerable: the arbor that advances past a tooth during tick `k`
is bounded during tick `k` by the tooth it started on, and by the new
one from tick `k+1`. It cannot be exploited by the same command, which
moves one way; a second input driving the same coordinate in the same
tick would be a conflict or a multi-source law, and the bound it sees
is still the committed one.

**Untimed and looping.** A callable bound is evaluated at THE VALUE
BEING BOUND, and the binding is refused when the value is outside the
evaluated pair — exactly the meaning a number bound has, with the bound
computed from the same value. For the ratchet the check always passes,
because `36 * floor(v / 36) <= v` for every `v`. That is not an
accident of the example: a bound that is not satisfied at its own
argument is not a detent, it is a declaration that forbids every value,
and the bind-time refusal is what says so by name. A symbolic binding
is still not checked, because its value is not known there.

**Export (cycle 4).** A compiled bound is an expression over coordinate
ids, which is exactly what a law is in the published program. It is
published beside the coordinate table, under the same version, and the
browser worker evaluates it at the committed state each tick and
localizes the stop with the same three tolerances. Nothing about this
cycle's shape makes that harder; the reason the bound is a GRAPH rather
than a Python callable at run time is precisely that cycle 4 has to be
able to publish it.

### 10. Whether a bound may name another coordinate

Not in this cycle. The Pascaline needs only the self-reference; the
spike's ratchet fixture also carries a `lift`, a second coordinate that
releases the pawl, and that is the shape the general form would take.

The obstacle is naming, not semantics. Evaluating a bound over several
coordinates at the committed state is the same rule and the same
evaluation; what is missing is how a class body names a coordinate that
is not the joint's own. A joint is class metadata resolved against its
DECLARER at realization, before the tree is linked and before any
qualified id exists, so `lambda turn, lift: ...` has no namespace to
resolve `lift` in — the declarer's own subtree is not linked yet, and a
qualified id is not a Python parameter name.

The smallest form that would serve both, when it comes, is a bound that
names what it reads:

```python
range=(Bound(lambda turn, lift: ..., reads=('turn', 'pawl.lift')), None)
```

resolved against the declarer's subtree at `Sim` construction, where
the ids exist. That is a new declaration object, a new resolution rule
and a new refusal surface — a cycle's worth — and it is strictly
additive: a one-argument callable keeps meaning what it means here.
Deferring it costs this campaign nothing and costs a future pawl-lift
model one migration of one line.

### 11. The worked example: the ratchet, with numbers

A fixture arbor whose driver drives its joint at ratio `1.0`, with
`range=(lambda turn: 36 * floor(turn / 36), None)`, `dt = 0.1`:

| Start | Request | Bound this tick | `t*` | Admitted | Status | `turn` after |
| --- | --- | --- | --- | --- | --- | --- |
| `40` | `by=+20`, 1 tick | `36` | — | `+20` | `completed` | `60` |
| `40` | `by=−10`, 1 tick | `36` | `0.4` | `−4` | `blocked` | `36` |
| `36` | `by=−10`, 1 tick | `36` | `0` | `0` | `blocked` | `36` |
| `36` | `by=+4`, 1 tick | `36` | — | `+4` | `completed` | `40` |
| `40` | `by=−10`, 1 tick | `36` | `0.4` | `−4` | `blocked` | `36` |

Read down the last three rows: the forward move from the seated tooth
is free, and the reverse that follows blocks at the same tooth again,
admitting the 4° it had gained. That is retention.

The same reverse move at three cadences, which is the cadence
independence a stop has to have:

| Duration | Ticks | Per tick | Blocking tick | `t*` in it | Total admitted |
| --- | --- | --- | --- | --- | --- |
| `0.1` | 1 | `−10` | 1 | `0.4` | `−4.0` |
| `0.4` | 4 | `−2.5` | 2 | `0.6` | `−4.0` |
| `4.0` | 40 | `−0.25` | 17 | `0` | `−4.0` |

The 40-tick row is the interesting one: tick 16 lands `turn` on exactly
`36.0`, which is INSIDE the inclusive bound, so that tick is ordinary
and the command is still `active`; tick 17 would take it to `35.75`,
`t*` is `0`, and the command retires `blocked` having admitted `−4.0`.
Every cadence blocks at the same coordinate value and admits the same
travel.

And the tooth advances with the arbor: from `turn = 75` the bound
evaluates to `36 * floor(75 / 36) = 72`, so a reverse blocks at `72`.

### 12. The swept stop

A rack with `range=(None, 50)` standing at `45`, driven at ratio `1.0`
by `steer`; a motor driving an unrelated wheel at ratio `3.0` under
`rate('motor', 90)`; `dt = 0.1`.

`move('steer', by=10, duration=0.1)` would take the rack to `55`. The
rack stops at `50` with `t* = 0.5`; the steering command retires
`blocked` having admitted `5.0` of the `10` requested; the motor's
command is untouched and the wheel gains its full `90 · 0.1 · 3 = 27`
degrees for that tick. The rack does not move on any later tick of the
same command, because there is no later tick of it: it is retired.

### 13. A stop and a jump crossing in one tick, and the record

The two do not interact mathematically. Each segment partitions its own
shorter path at the crossings it meets, so a crossing before `t*` is
integrated in segment A and one after it in segment B — and one after
`t*` on a STOPPED law simply never happens, because its sources stopped
moving.

They interact in the RECORD, and the fix is one line of arithmetic. A
`Crossing`'s `t` is documented as "the fraction of the tick", and a
segment's partition is in the fraction of the SEGMENT. Each located
fraction is mapped back to the tick before it is recorded:

```text
t_tick = t0 + t_segment * (t1 - t0)
```

for a segment spanning `[t0, t1]`. With a crank resting at `130`,
driving `first.turn` at ratio `1.0` under `range=(None, 145)` and
driving `wrapped.turn` by `2 * wrap(angle, 90)` whose fold falls at
`135`, one tick of `+20` stops at `t* = 0.75`; the fold sits at `1/3`
of segment A and at `0.25` of the tick, and `0.25` is what is recorded.
Without the mapping, the same crossing would be reported at a different
fraction depending on whether a stop happened to cut the tick after it
— which would make the record useless to the viewer that cycle 5 will
feed. The ordering sentence in the
recording requirement gains one clause: entries are appended segment by
segment, so within one relation the fractions still ascend across the
tick.

Stops go in a THIRD ring, `sim.stops`, not into `sim.crossings`:

- a crossing is a JUMP SURFACE of a law, whose `level` is a value of
  that law's level quantity and which moves nothing; a stop is a BOUND
  of a coordinate, which stops motion. They answer different questions.
- cycle 2's own open question notes a reader COUNTING THROWS off
  `sim.crossings`; mixing a second primitive into that ring would break
  every such reader, and `record=N` would then bound the two kinds
  against each other.

Each entry names the tick, the coordinate, which bound it reached and
its evaluated value, the coordinate's value (which is that bound), the
fraction `t*` of the tick, and the inputs the stop blocked. It is
appended, like a crossing, only when the tick commits.

*Rejected: one ring with a distinct primitive name, `'stop'`.* Cheaper
by one deque and one property, and it makes `sim.crossings` a mixed
vocabulary whose every consumer has to filter.

### 14. Tolerances

No new tolerance. `_CROSSING_TOLERANCE` is the bisection's stopping
bracket for a searched stop AND the width in `t` below which two stops
are ONE event; `_SUBDIVISIONS` is the sampling of a non-affine
`V_c`; `_BISECTION_ROUNDS` is its safety net. They are stated in `t`,
the tick's own dimensionless fraction, which is why one number serves a
stop on a coordinate in degrees and a stop on a coordinate in
millimetres.

There is deliberately no tolerance on the BOUND itself. "Is this
coordinate on its stop" is never asked as a comparison with slack: the
detection is the inclusive comparison that already exists, and a
stopped coordinate is committed at the bound exactly, so the next tick's
question is answered by arithmetic rather than by an epsilon.

### 15. Performance

Cycle 2 measured one `Train` tick at 1.07 ms and a jump-carrying law at
1.3× its continuous twin on a non-crossing tick.

- **A tick with no stop pays what it pays today**: one inclusive
  comparison per ranged coordinate — the loop that is already there —
  plus, for each EXPRESSION bound, one graph evaluation per tick. There
  is no ranged coordinate in `Train`, so the expectation is no
  measurable change, and the task list records it against the same
  fixture and the same method.
- **A blocking tick on an affine chain** costs one division for the
  localization and two extra propagation passes (segments A and B)
  instead of one, so under 3× one tick, once, at the stop.
- **A blocking tick on a non-affine chain** costs up to
  `_SUBDIVISIONS + _BISECTION_ROUNDS` EDGE evaluations — not program
  passes — plus the same two propagation passes.
- **A tick with `S` stops** costs `2S + 1` propagation passes, and `S`
  is bounded by the number of inputs admitting travel.
- Memory is flat: three bounded rings instead of two, and the group
  table is compile-time and proportional to the program.

### 16. Module layout

- `solid_node/motion/joints.py` keeps everything about what a range IS
  and nothing about how a run uses it. `_span` stops evaluating a bound
  that is a callable and stops rejecting `None`, returning the pair as
  declared; the `lo <= hi` check applies where both are numbers.
  `_refuse_out_of_range` evaluates a callable bound at the value being
  bound. No import of the simulation layer, as now.
- `solid_node/simulation/program.py` owns the compile: the span table,
  the bound graphs, `Program.sources`, `Edge.affine`, `JumpPlan.cuts`,
  the `Stop` record. It already owns the coordinate table and the
  identity, and a stop is a property of the program.
- `solid_node/simulation/run.py` owns the tick: the segment loop, the
  per-tick evaluation of the bounds, the localization, the group, the
  blocking, the staging, the third ring, and the two lifted refusals.
  `integrate`'s current body becomes `_pass`, unchanged; everything new
  is around it.
- `solid_node/simulation/sim.py` gains `sim.stops` and nothing else.

### 17. What stays untouched

Untimed and looping documents, `Time(loop=)`, and the untimed meaning
of a numeric range (refuse the binding, never clamp). The bank, the
binder, `set_state` delivery, the compile step's node classification,
edge ordering, the program's acyclicity refusal. Propagation, hold,
conflict, rollback. The four other command statuses, the one-owner
rule, per-tick admission as a pure function of the tick count,
`Instruction(by=)`, zero-duration moves. Snapshot, restore, reset and
the trajectory ring — a blocked command is retired when it blocks, so
a snapshot taken afterwards simply carries no entry for it, and a
snapshot taken BEFORE the block replays to the same block. Jumps'
rules entirely. The document schema, the export, the viewer. No
memory, no declared events, no `Running` object.

### 18. Decisions that become ADRs after implementation

- **ADR-108: A range is a physical stop that stops the connected
  group.** Under a running root a joint's declared range is a
  mechanical limit located inside the tick rather than a refusal of the
  tick; the coordinate stops at its bound, every input whose movement
  pushes it stops with it (the candidates being the inputs that reach
  it through the compiled program), an input coupled only through a
  disengaged law and every unrelated input run their full tick, `t*`
  is exact over affine upstream edges and first-order otherwise, and the command that pushed retires `blocked` with
  the travel it actually admitted and no backlog. Depends on ADR-105
  and ADR-107; cites ADR-083.
- **ADR-109: A range bound may be an expression evaluated at the
  committed state.** A bound may be a callable of the joint's own
  coordinate returning an expression in the symbolic vocabulary,
  compiled once like a law, evaluated at the start of every tick from
  the committed bank under a running root and at the value being bound
  everywhere else; jumps are admitted in it because it is evaluated,
  never integrated. Depends on ADR-106; cites ADR-076 and ADR-088.

## Risks / Trade-offs

- **The contribution test costs a pass per pushing candidate on a
  blocking tick.** Bounded by the number of inputs admitting travel;
  a non-blocking tick pays nothing. Measured in the evidence.
- **An excursion inside one tick is not seen.** A coordinate that
  leaves its range and returns within one tick is not stopped. It
  cannot happen for an affine determiner; for any other, the answer is
  a smaller `dt`, as it is for a jump surface crossed twice inside one
  sub-interval.
- **The detection pass walks the whole tick.** A law that cannot be
  integrated between `t*` and `1` refuses the tick even though the
  stopped group never travels there. Open question 4.
- **A fractional native value on an integer input.** A stop at `t*`
  admits `t*` of a tick's travel, which for an integer driver is not a
  whole native unit. The state is then a stepper stopped between steps,
  which is honest — the stop is where the machine stopped — but the
  driver declaration says an integer driver counts whole native units.
  Open question 2.
- **The stopped coordinate is committed at its bound.** A correction of
  at most the localization's own error, applied after propagation, so
  the group's coordinates may stand a few ulps from exact consistency
  with it. Within the `1e-9` relative tolerance the run already calls
  agreement, and the alternative — binding a value a few ulps outside
  the bound — raises from `set_state`.
- **A blocked command loses its remaining travel.** By design, and the
  caller has the exact number to replan from. A caller that wants to
  retry writes the retry; the run will not.
- **Two more compile-time tables.** `Program.sources` and the span
  table grow the program by a set per node and a pair per ranged
  coordinate. Both are proportional to the program and neither grows
  with the tick count.

## Migration Plan

Nothing to migrate in the framework. Two behaviours change for anyone
who already writes a running root:

- a joint range that used to fail the tick now stops the group. A model
  that RELIED on the refusal — there is none in the tree but the
  fixture — reads its stop from `sim.stops` or from the command's
  `blocked` status instead;
- a reverse move that used to raise now runs.

Both are strictly more capable, and no document changes shape. The
Pascaline module adds one `range=` to one joint in its own repository.
`tests/running_project/machine.py::Ranged` changes meaning rather than
disappearing, so the refusal's disappearance is visible in the diff.

## Open Questions

1. Should a stop also be reported through `sim.commands`' handle for an
   input whose group stopped but which had NO command — that is, should
   the run offer a "which inputs are standing against a stop" read at
   all? This cycle reports a stop only through the record and the
   commands that existed.
2. Should a stop on an INTEGER-dtype input admit only whole native
   units, flooring `t*` of the tick's travel, rather than leaving the
   driver between steps? This cycle leaves it between steps and says
   so.
3. Resolved in review: the group is the inputs that push the stopped
   coordinate, tested per candidate of the static table (decision 3).
4. Should the detection probe stop at the first stop rather than
   integrating the whole tick, so a law that cannot be integrated past
   `t*` does not refuse a tick the machine would never have reached?
   This cycle probes the whole tick (decision 4).
5. Should an expression bound be admitted UNTIMED at all, or only under
   a running root? This cycle admits it everywhere, evaluated at the
   value being bound, so that one declaration poses and runs.
6. Should `sim.stops` be on by default under a running root rather than
   tied to `record=N`? It is tied, exactly as the crossing ring is, so
   a run that records nothing pays nothing.
