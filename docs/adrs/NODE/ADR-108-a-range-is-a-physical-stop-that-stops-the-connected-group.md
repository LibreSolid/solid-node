# ADR-108: A Range Is a Physical Stop That Stops the Connected Group

**Status:** Accepted
**Date:** 2026-09-13
**Depends on:**
- [ADR-105: The run owns the coordinates and binds them](./ADR-105-the-run-owns-the-coordinates-and-binds-them.md)
- [ADR-107: A jump is located inside the tick and subtracted](./ADR-107-a-jump-is-located-inside-the-tick-and-subtracted.md)
**Cites:**
- [ADR-083: Simulation time is finite, forward, and tick-aligned](./ADR-083-simulation-time-is-finite-forward-and-tick-aligned.md)
**OpenSpec change:** `ranges-are-stops`

## Context and Problem Statement

ADR-105 gave the run every driver and joint coordinate of the linked tree
and refused, by name, a tick that would leave one outside its declared
`range`:

```python
def _check_spans(self, committed, moved):
    for identifier, low, high, unit in self.spans:
        value = committed[identifier]
        if low <= value <= high:
            continue
        self._refuse(moved)
        raise JointRangeError(...)
```

The tick committed nothing, the bank stood at the last admitted tick and
every command that had moved retired `refused`. A machine that reaches a
stop was therefore a machine that could not be stepped past it — which is
a refusal of the AUTHOR's declaration rather than a model of a mechanical
limit. The same reasoning refused a reverse move outright, because
reverse travel met no stop to meet.

Two mechanisms of the open-run campaign need the mechanical reading, and
neither is expressible without it:

- the **Pascaline module's ratchet** — ten 36° teeth on the input arbor
  against a flexible blade with no pawl lift, so forward rotation is free
  and reverse is blocked at the last seated tooth. The module's own
  acceptance record states the gap: its blade-clearance samples "do not
  prove reverse blocking", and nothing in the model blocks reverse;
- the **spike's swept stop** — a rack that stops at its admitted limit
  inside a tick while an independent motor runs its full tick
  (`workflow/open-run-simulation/spikes/kernel.py`). The spike proved it
  with a unilateral coordinate stop, a blocked-group rule and a `blocked`
  status, and recorded the gap this decision closes: *"precise fractional
  progress/replanning remains a required design item for production."*

## Decision Drivers

- A declared range is the author's statement about where a coordinate may
  be. Under a running root the honest reading of it is a stop, not a
  refusal.
- A stop must stop what the stop actually holds and nothing else: an
  unrelated drive keeps running, and so does one coupled to the stopped
  coordinate only through a law that is currently disengaged.
- The caller must be able to replan from an exact number, which means the
  travel a blocked command actually made, fractional within the tick.
- A tick must stay ATOMIC and pure: one `set_state`, and a failure
  anywhere in it commits nothing.
- A tick that does not block must cost what it cost before. The whole
  running mode's per-tick budget rests on that.
- Nothing may be clamped. A value is never silently moved into range.

## Considered Options

1. **Keep the refusal** and leave a stop to the caller, who would have to
   compute the admitted travel itself. This is what cycles 1 and 2 did;
   it makes a limit unrepresentable and makes every reverse move a
   modelling problem.
2. **Clamp the coordinate** to its bound at the end of the tick. One
   line, and wrong: the group's other coordinates would stand where an
   unstopped tick put them, so the machine would be internally
   inconsistent — a rack at its limit with the pinion that drives it half
   a tooth past.
3. **Locate the stop inside the tick and truncate the group's motion
   there.** Chosen.

Within option 3, three sub-decisions had real alternatives:

- **What `V_c(t)` is.** Rejected: defining it as the increment a full
  PROGRAM pass gives with every input's admission scaled by `t`. It is
  exactly consistent with the way a segment is later committed, but it
  costs a full program pass per sample — up to
  `_SUBDIVISIONS + _BISECTION_ROUNDS` passes on a blocking tick, about
  137 ms at ADR-107's measured `Train` tick. The per-edge model is exact
  for every affine chain, and committing the stopped coordinate at its
  bound removes the only consequence of the difference.
- **What the group is.** Rejected: the spike's rule, zeroing the whole
  connected COMPONENT of an undirected velocity graph — the compiled
  program is directed and acyclic, and a component would stop inputs that
  cannot influence the stopped coordinate at all. Also rejected: the
  purely STATIC group, every input reaching it through the program —
  cheaper by one pass per candidate, and wrong in a stated direction,
  because it stops an input coupled only through a disengaged law, so an
  open clutch would stop its crank.
- **What a blocked command does next.** Rejected: keeping it active and
  letting it resume when the bound moves away. That is the auto-resume
  the spike refused: the run would have to decide when a stop has "gone",
  it would resume in a direction the caller stated ticks ago, and one
  blocked move quietly pending is exactly the hidden backlog the design
  rules out.

## Decision

**Under a running root a joint's declared `range` is a PHYSICAL STOP,
located inside the tick. The tick commits and the tick count advances.**

**Detection** is by the tick's committed value, exactly the comparison
ADR-105 already made, plus a DIRECTION test: a coordinate stops at a
bound when it ends the stretch being integrated outside that bound AND
further outside than it stood at the start of that stretch. A coordinate
at or beyond a bound that moves the other way is free, and one that does
not move is free, so a frozen coordinate standing on its bound raises
nothing. Both bounds stay INCLUSIVE, so a tick landing exactly on a bound
is not a stop at all. A bound stated as `None` is unbounded on that side.

**Localization.** The coordinate's value along the tick is `v(0)` plus
the increment its DETERMINER EDGE gives over the tick's path truncated at
`t` — the same straight path in the sources' joint space that ADR-106 and
ADR-107 integrate over, so a law that jumps contributes its
subtracted-jump increment here too. `t*` is the smallest fraction at
which that value reaches the bound, and `0` when the coordinate already
stands at or beyond it. Three cases, decided at compile time by
`Edge.affine`, the per-driven-end classification computed with ADR-107's
own `_affine_in_sources`: an affine edge with no jump plan is one
division, EXACT; an affine SKELETON with a jump plan is piecewise affine
with breakpoints at the plan's own cuts, solved linearly inside the piece
that brackets the bound, EXACT; anything else is sampled at
`_SUBDIVISIONS` points and bisected to `_CROSSING_TOLERANCE` in at most
`_BISECTION_ROUNDS` rounds. No fourth tolerance is introduced, and there
is deliberately none on the bound itself.

**The group** a stop stops is every INPUT whose own movement over the
stretch actually PUSHES the stopped coordinate, together with everything
those inputs alone determine. The CANDIDATES are the inputs that reach it
through the compiled program — `Program.sources`, a static table computed
once, in one pass over the already ordered edges, a `check` edge
contributing nothing — and a candidate with a nonzero admission over the
stretch is IN the group when, with its own admission applied and every
other input's set to zero, the program's edges between it and the
coordinate give it a nonzero increment. That test runs on BLOCKING TICKS
ONLY, once per such candidate. The second half needs no computation: the
stopped inputs' admissions are set to zero for the rest of the tick and
the ordinary propagation does the rest.

**Segments.** A tick with one stop is integrated as two sub-ticks —
`[0, t*]` with every input's admission multiplied by `t*`, then
`[t*, 1]` with the stopped inputs admitting nothing and the others
multiplied by `1 − t*` — each by exactly the procedure ADR-105 to
ADR-107 state, its own jump partition included. The remainder is examined
again and the process repeats, the EARLIEST `t*` always taken first; two
stops whose fractions are within `_CROSSING_TOLERANCE` are ONE event,
stopping the union of their groups at one boundary, so ties are never
resolved by ordering. The iteration is bounded by the number of inputs
admitting travel, because every event stops at least one moving input and
a stopped input stays stopped.

**The stopped coordinate is committed AT its bound, exactly**, rather
than at what the segment's arithmetic produced. That is not tidiness:
`Run.bind()` delivers the bank through `set_state`, and a joint
coordinate binding goes through the joint's own range check, so a
localization leaving the coordinate a few ulps outside would make the
very tick that stopped it raise `JointRangeError` from the binding.

**The tick stays ATOMIC.** The bank, the commands' admitted travel and
the three record rings are STAGED across the segments and applied only
when every segment has succeeded. A conflict, a `TooManyCrossings` or an
unintegrable law in ANY segment refuses the whole tick: nothing is
committed, nothing is recorded, and the commands that moved retire
`refused`. One `set_state` per tick, as ADR-105's purity contract
requires.

**`blocked`** is what a command on a stopped input retires with — the
word ADR-105 reserved, adding none to the vocabulary. It leaves
`sim.commands`, releases its input, and reports the travel it ACTUALLY
made: every completed tick's travel plus `t*` of the stopping tick's. A
blocked command NEVER resumes; there is no backlog anywhere. A `rate` on
a stopped input is retired `blocked` too. Where one instruction names
several inputs, each command reports for itself and no instruction-level
summary is owed.

**Reverse requests are admitted.** A negative `by`, a `to` below the
committed value and a negative `rate` are ordinary, and meet a stop
exactly as forward ones do. `Command._cumulative` truncates toward zero
rather than flooring, so the two directions round alike on an integer
input.

**Stops are recorded, bounded.** `record=N` keeps a THIRD ring,
`sim.stops`, beside the trajectory and the crossings: tick, coordinate,
which bound, that bound's evaluated value, the fraction of the tick and
the inputs blocked. A stop is a bound of a coordinate, which stops
motion; a crossing is a jump surface of a law, which moves nothing. They
answer different questions and a reader counting throws off
`sim.crossings` must not have to filter. `record=None` keeps and builds
none.

## Consequences

- **The group rule is the tested one, not the wired one.** An input
  reaches the stopped coordinate through the program and is still not
  stopped when its own motion does not change it: the crank behind an
  open clutch keeps turning and goes on driving its flywheel while the
  wheel stands at its stop, and closing the gate makes the same tick stop
  both. The cost is one sub-program propagation per candidate with a
  nonzero admission, on a blocking tick only — measured at 1 pass on a
  one-input group and 2 on `OpenGate`, whose stopped wheel has three
  candidates, two of them moving and one of them pushing — and a
  non-blocking tick pays nothing at all.
  A multi-source law whose contributions are not separable counts an
  input as pushing whenever its motion ALONE changes the coordinate,
  which is the honest kinematic answer for an engaged coupling.
- **The exactness boundary is stated, not hidden.** `t*` is EXACT when
  every edge between the pushing inputs and the stopped coordinate's
  determiner is affine — every ratio, every wiring, every derived
  coordinate's linear formula, and both originating projects. For a
  NONLINEAR upstream edge the group's OTHER coordinates are stopped at a
  `t*` located on the linearized upstream path, while the stopped
  coordinate itself is committed at its bound EXACTLY; a smaller `dt`
  shrinks that difference, and the full-program search remains the
  documented exact alternative. The corresponding cost of committing the
  bound is that the group's other coordinates may stand a few ulps from
  perfect consistency with it — far inside the `1e-9` relative agreement
  the run already calls equal, and applied after propagation, so no
  conflict is raised.
- **A tick that does not block costs what it cost.** `Train` measures
  1.065 ms/tick against ADR-107's recorded 1.044–1.057 on the same probe,
  and the deterministic count is identical: one propagation pass, eight
  graph evaluations. A blocking tick costs `2S + 1` propagation passes
  for `S` stops — 3 for one, 5 for two — plus the localization, which is
  one division on an affine chain and up to
  `_SUBDIVISIONS + _BISECTION_ROUNDS` EDGE evaluations (not program
  passes) on any other: 206 graph evaluations and 5.1× one tick on the
  `40 * sin(x)` fixture, paid once, at the stop.
- **An excursion inside one tick is not seen.** A coordinate that leaves
  its range and returns within one tick is not stopped, because detection
  is by the tick's committed value. It cannot happen for an affine
  determiner, where the value is monotone in `t`; for any other the
  answer is a smaller `dt`, exactly as it is for ADR-107's level quantity
  that turns twice inside one sub-interval. Sampling every ranged
  coordinate every tick was rejected: it would make every tick of a
  ranged machine pay 64 evaluations per coordinate for a case that cannot
  arise where it matters, and would only push the limit one resolution
  finer.
- **The detection pass walks the whole tick.** A law that cannot be
  integrated somewhere between `t*` and `1` refuses the tick even though
  the stopped group never travels there. ADR-107 already refuses a tick
  whose path meets a zero divisor; a stop does not rescue it. Open
  question, recorded in the change.
- **A stop on an integer input leaves the driver between steps.** `t*` of
  a tick's travel is not a whole native unit, so a stepper stopped at a
  physical limit banks a fractional position. That is honest — the stop
  is where the machine stopped — and it is in tension with the driver
  declaration's promise that an integer driver counts whole native units.
  Open question, recorded in the change.
- **A blocked command loses its remaining travel**, by design, and the
  caller has the exact number to replan from. A caller that wants a retry
  writes the retry; the run will not.
- **`Program` grows two compile-time tables** — the candidate sets and
  the span table — both proportional to the program and neither growing
  with the tick count. Both are properties of the PROGRAM, so they travel
  into the cycle that publishes it, and a browser worker runs the same
  contribution test over the same table.
- **`Program.identity` changes for any root that declares a range**,
  because the spans now enter `described()`. That is the point: a
  snapshot cannot be restored into a machine whose stops have moved. A
  root with no ranged coordinate is unaffected.
- **Snapshot and restore need nothing new.** A blocked command is retired
  when it blocks, so a snapshot taken afterwards carries no entry for it,
  and one taken before replays to the same block with the same admitted
  travel and the same recorded stop.
- **No collision, no force, no contact state.** A stop is a kinematic
  bound on one declared coordinate, not a limit found between two meshes.
