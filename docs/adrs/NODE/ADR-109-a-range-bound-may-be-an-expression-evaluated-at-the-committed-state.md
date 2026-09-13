# ADR-109: A Range Bound May Be an Expression Evaluated at the Committed State

**Status:** Accepted
**Date:** 2026-09-13
**Depends on:**
- [ADR-106: One law, two readings — a relation is inspected as an expression](./ADR-106-one-law-two-readings.md)
**Cites:**
- [ADR-076: Mechanism laws as compositions over expression math](../MATH/ADR-076-mechanism-laws-as-compositions-over-expression-math.md)
- [ADR-088: A joint owns one coordinate](./ADR-088-a-joint-owns-one-coordinate.md)
**OpenSpec change:** `ranges-are-stops`

## Context and Problem Statement

ADR-088 gave a joint an optional `(lo, hi)` `range` whose bounds are
resolved to plain numbers at realization, from a number, a declared
parameter or a derived formula. ADR-108 made that range a physical stop
under a running root. Between them they cover a hard limit — a rack's
travel, an elbow's swing — and nothing else.

A RATCHET is not a hard limit. The Pascaline module's input arbor carries
ten 36° teeth against a flexible blade with no pawl lift: forward
rotation is free and reverse is blocked at the LAST SEATED TOOTH, which
is a different number every tooth. A detent is a force this kinematic
model does not have; a stop at the last seated tooth is a kinematic
statement of the same fact, and it is a bound that depends on where the
coordinate IS:

```text
lower bound of turn  =  36 * floor(turn / 36)
```

A number cannot say that, and neither can a callable of the realized
NODE — the form ADR-088 already admits — because the node is realized
long before the coordinate has a value, and the bound has to be read
again every time the arbor advances past a tooth.

The second gap is smaller and older: `range` has always required both
bounds. A rack that may not go below zero and may travel as far above it
as the mechanism takes it has to invent an upper number, and an invented
number is a stop that is not there.

## Decision Drivers

- The declaration must read as what it is. `36 * floor(turn / 36)` is the
  seated tooth, written once, in the class body.
- One declaration must pose and run. The same `range=` has to mean
  something under an untimed root, where a range refuses a binding, and
  under a running one, where it stops a coordinate.
- The bound must be PUBLISHABLE. The cycle that exports the compiled
  program has to carry it, which means it must end up as an expression
  graph over coordinate ids, not as a Python callable.
- A self-reference must be well defined, not circular.
- Nothing existing may change meaning. A callable already means something
  in `range=`.

## Considered Options

1. **A new keyword beside `range=`** — `detent=`, `stop=`. Rejected: a
   joint would then have two ways to say where it may travel, they would
   have to be reconciled (which wins? do they intersect?), and untimed
   posing would have to choose one. A range is already the declaration of
   where a coordinate may be; this makes its bound able to depend on
   where the coordinate IS.
2. **A bound stated as an expression directly**,
   `range=(36 * floor(turn / 36), None)` with `turn` a module-level
   token. Rejected: there is no such token at class-body time. The joint
   owns the coordinate and names it only when `__set_name__` runs.
3. **A callable of one argument INSIDE the pair.** Chosen. It is exactly
   how `at=lambda node: ...` already refers to a node that does not exist
   yet, and it is how a class body can refer to a coordinate that does
   not exist yet.
4. **A bound that may name ANY coordinate**, which the spike's own
   ratchet fixture wants (it carries a `lift` that releases the pawl).
   Deferred — see the consequences.

## Decision

**Either bound of a joint's `(lo, hi)` `range` MAY be `None`, meaning
unbounded on that side, or a CALLABLE OF ONE ARGUMENT, which the
framework applies once to the joint's OWN coordinate and which returns an
expression in `solid_node.math`'s vocabulary.**

```python
class InputArbor(AssemblyNode):
    turn = Revolute(axis=(1, 0, 0),
                    range=(lambda turn: 36 * floor(turn / 36), None))
```

The form is a callable INSIDE the pair, which is what keeps it apart from
the callable `range` ADR-088 already admits — `range=lambda node: (lo,
hi)`, called with the realized declarer and returning numbers. **The two
are told apart by POSITION, not by arity**, so nothing existing changes
meaning. `Joint._span` carries both new forms through unevaluated, and
the `lo <= hi` ordering check applies where both bounds resolve to
numbers at realization and is checked where each bound is evaluated
otherwise.

**Where the bound is USED, it is applied.** There are exactly two such
places, and they agree:

- **At binding time**, everywhere, the callable is applied to THE VALUE
  BEING BOUND, and the binding is refused when the value lies outside the
  pair so evaluated — exactly the meaning a number bound has, with the
  bound computed from the same value. The refusal names the evaluated
  bound beside the joint, the value, the unit and the node, and refuses
  likewise when the evaluated pair is reversed or is not a number. For a
  ratchet the check always passes, because `36 * floor(v / 36) <= v` for
  every `v`; that is not an accident of the example, because **a bound
  that is not satisfied at its own argument is not a detent — it is a
  declaration that forbids every value**, and the bind-time refusal is
  what says so by name at the first binding. A symbolic binding is still
  not checked, because its value is not known there.
- **Under a RUNNING root**, additionally, the bound is compiled ONCE at
  `Sim` construction and EVALUATED ONCE PER TICK, at the tick's start,
  from the committed bank.

**Compile.** The bound is compiled exactly as ADR-106 compiles a law:
applied to `symbol(name)` for the coordinate's qualified id, the graph
walked for raw text and for calls outside `SYMBOLIC_BUILTINS`, refused by
joint and node identity when it is neither a number nor an expression
over that ONE coordinate. **Jumps are ALLOWED and need no plan**: the
bound is evaluated at one point per tick and never integrated, so `floor`
means `floor` and nothing is subtracted. That asymmetry with a law is the
point — a law's jump would move a part, a bound's jump is the tooth
pitch. The compiled span table joins the program: `Program.spans` carries
each banked coordinate's low and high bound as a number, `None` or a
graph, and `Program.described()` names them.

**Evaluate.** Once per tick, at the tick's START, before any segment, so
every segment of one tick sees the same number and ADR-108's localization
has a constant to solve against. Within a tick the bound is a number;
between ticks it follows the machine. The self-reference is well defined
because the value it reads is COMMITTED and the value it bounds is not
yet.

## Consequences

- **The ratchet is expressible, and it retains.** From `40`, a reverse of
  `-10` blocks at exactly `36` having admitted `-4`; a further reverse
  blocks at once with `0`; `+4` is free; the reverse after that blocks at
  `36` again. From `75` the bound evaluates to `72`, so the tooth advances
  with the arbor. The Pascaline module's own migration is one `range=` on
  one joint in its own repository.
- **The detent is quantized to the tick, which is correct rather than
  merely tolerable.** The arbor that advances past a tooth during tick
  `k` is bounded during tick `k` by the tooth it started on, and by the
  new one from tick `k+1`. It cannot be exploited by the same command,
  which moves one way; a second input driving the same coordinate in the
  same tick would be a conflict or a multi-source law, and the bound it
  sees is still the committed one.
- **One declaration poses and runs.** The untimed reading is the same
  rule with the same evaluation at a different point, so a project does
  not carry two declarations or a running-only one. The alternative —
  admitting an expression bound only under a running root — would have
  made a model that poses refuse to pose.
- **A bound is publishable.** It is an expression over coordinate ids,
  which is exactly what a law is in the published program, so the cycle
  that exports the program publishes it beside the coordinate table under
  the same version and a browser worker evaluates it at the committed
  state each tick. That is the reason the bound is a GRAPH at run time
  rather than a Python callable.
- **`Program.identity` changes for any root that declares a range**,
  because the spans enter `described()`. A snapshot therefore cannot be
  restored into a machine whose stops have moved — which is the point,
  and which a root with no ranged coordinate is unaffected by.
- **A bound may NOT name a second coordinate in this release.** The
  obstacle is naming, not semantics: evaluating a bound over several
  coordinates at the committed state is the same rule and the same
  evaluation, but a joint is class metadata resolved against its DECLARER
  at realization, before the tree is linked and before any qualified id
  exists, so `lambda turn, lift: ...` has no namespace to resolve `lift`
  in. The smallest form that would serve is a bound that names what it
  reads — `Bound(lambda turn, lift: ..., reads=('turn', 'pawl.lift'))`,
  resolved against the declarer's subtree at `Sim` construction, where
  the ids exist. That is a new declaration object, a new resolution rule
  and a new refusal surface, and it is strictly ADDITIVE: a one-argument
  callable keeps meaning what it means here, so deferring it costs a
  future pawl-lift model one migration of one line. The refusal names the
  other coordinates it read.
- **A non-blocking tick pays one graph evaluation per expression bound**
  — three instead of two on the ratchet fixture's single-law machine.
  A number bound costs nothing at all, and a machine with no ranged
  coordinate costs nothing either.
