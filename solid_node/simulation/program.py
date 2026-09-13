# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The compiled program: a running root's relations as EXPRESSIONS over
coordinate ids.

Untimed and looping, a relation sets its driven coordinate to
``f(driver)``. Running, it contributes ``f(end) - f(start)`` over a tick,
from where the coordinate stood -- which is exact across the kinks of
``abs``, ``min`` and ``max`` and of the compositions built on them,
because it is the difference of two exact evaluations. Nothing about the
law changes; what changes is which of its two readings the run takes.

To take the difference of two evaluations the run has to be able to
EVALUATE the law at values of its own choosing, and a law is already an
expression builder: ``Affine.forward`` is ordinary arithmetic over
whatever it is handed, ``solid_node.math``'s primitives emit ``call``
nodes whose names are the closed list ``SYMBOLIC_BUILTINS``, and a
``symbol()`` builds the graph. So each law is applied ONCE here, to a
symbolic token per source coordinate, in the direction the REST RENDER
solved it, and the graph that application builds -- over the qualified
ids of its sources -- is what the run evaluates on every tick.

A DISCONTINUOUS primitive (``floor``, ``ceil``, ``sign``, ``%``, a
comparison) is a JUMP, and a graph carrying one is compiled a second
time, into a ``JumpPlan``: the jump nodes in the graph's postorder, each
with the LEVEL QUANTITY whose surfaces it crosses, and a SKELETON of the
whole law with every jump node replaced by a branch placeholder. Over a
tick the plan cuts the path at every crossing it meets, reads one branch
per jump node at each piece's midpoint -- which makes the law continuous
there -- and sums the branch-substituted law's change over the pieces.
So a jump never moves a part, and nothing in the sum ever spans one.

That application is also the inspection. What the expression cannot say
is refused by relation identity, at construction, rather than integrated
wrongly: a law that raises when handed a symbol, or whose graph holds
text the framework cannot evaluate, is not an expression over its
sources at all; an edge into a bank coordinate whose source nothing in
the program computes is a value stated in ``simulate()`` rather than as
a relation; a law that can move its coordinate only by JUMPING states
arithmetic rather than a mechanism; and a jumping law driving no
coordinate the run owns has nowhere to keep the history a subtracted
jump implies.

This module is imported by ``Sim.__init__`` only when the root declares
``Time.running()``, so a model that declares no running time pays for
none of it (capability ``cli-startup-cost``).
"""

import hashlib
import math
import operator
from dataclasses import dataclass

from solid2.core.object_base import OpenSCADConstant

from solid_node.expression_graph import ExpressionNode, free_names, postorder
from solid_node.math import SYMBOLIC_BUILTINS
from solid_node.motion.couplings import (_solved_formulas, _wirings,
                                         CouplingError)
from solid_node.motion.joints import coordinates_of, declared_joints
from solid_node.node.qualified import driver_id, instance_path
from solid_node.scad_expression import GraphValue, as_node, symbol


# The primitives that JUMP, and are therefore recognized and planned for
# rather than integrated straight through. `floor`, `ceil` and `sign`
# jump by construction; `%` jumps at every period; a comparison is a
# step. `wrap()` is built on `ceil` and integrates through this list;
# `piecewise()` is a sum of `clamp01` terms and holds no jump node at
# all.
_JUMP_CALLS = ('floor', 'ceil', 'sign')
_JUMP_OPERATORS = ('%', '<', '<=', '>', '>=', '==', '!=')

# A comparison's level quantity is `a - b` and its one surface is zero,
# so its branch is the operator read against zero -- exactly what
# `GraphValue.evaluate` computes, whose `bool` arithmetic then reads as
# 1 or 0.
_COMPARISONS = {'<': operator.lt, '<=': operator.le, '>': operator.gt,
                '>=': operator.ge, '==': operator.eq, '!=': operator.ne}

# Three tolerances, and no more (design.md section 5).
#
# `_CROSSING_TOLERANCE` is stated in `t`, the tick's own dimensionless
# fraction, so one number serves a law over several sources with several
# units: it converts to each source's units by multiplying by that
# source's travel over the tick. It is the bisection's stopping bracket
# AND the width below which two crossings are one cut. The run calls two
# increments equal within `1e-9 * max(1, |a|, |b|)`, so a crossing
# located three orders finer than that can never manufacture a
# disagreement, and bisecting further is below the resolution of `t` as a
# double over a tick of unit travel.
#
# There is deliberately NO surface tolerance. The question "is this
# coordinate ON the surface" is never asked: a branch is read at a
# piece's midpoint, which is a point genuinely inside it.
_CROSSING_TOLERANCE = 1e-12

# How finely a level quantity that is NOT affine in the sources is
# sampled before each bracketed crossing is bisected. The search resolves
# any crossing pair separated by more than 1/64 of the tick's travel; a
# level quantity that turns twice inside one sub-interval is outside the
# guarantee, and the answer to that is a smaller dt.
_SUBDIVISIONS = 64

# 40 rounds already reach 2**-40 < 1e-12 from a unit bracket; this is the
# safety net, not the working number.
_BISECTION_ROUNDS = 64

# The per-graph per-tick bound on the partition. A thousand surfaces in
# one tick is a dt that is not resolving the mechanism, and an unbounded
# partition would be an unbounded per-tick cost inside a mode whose whole
# promise is bounded memory.
_MAX_CROSSINGS = 1000


class UnsupportedLaw(CouplingError):
    """A relation cannot be compiled into the running program, or cannot
    be integrated over a tick: its law is not an expression over its
    sources, is sourced from a coordinate the run does not own and no
    edge computes, can move its coordinate only by jumping, carries a
    jump with nowhere to keep its history, or divides by zero somewhere
    on the tick's own path.

    A declared range's BOUND is compiled by exactly the same rule and
    refused by the same kind: it is applied once to a symbolic token for
    the joint's own coordinate, and what the expression cannot say is
    refused here rather than evaluated wrongly every tick.
    """


class TooManyCrossings(CouplingError):
    """One tick would cut a law's path more times than the run admits.
    The tick committed nothing."""


@dataclass(frozen=True)
class Crossing:
    """One jump surface met inside one tick.

    `level` is the surface value in the LEVEL QUANTITY's own units -- the
    integer for `floor`, `ceil` and `%`, zero for `sign` and a
    comparison -- and `t` is the fraction of the tick at which it was
    reached. `relation` and `coordinate` are computed once at compile
    time, so appending an entry costs a tuple and no formatting.
    """

    tick: int
    relation: str
    coordinate: str
    primitive: str
    level: float
    t: float


@dataclass(frozen=True)
class Stop:
    """One declared bound reached inside one tick.

    `bound` is `'low'` or `'high'` and `value` is that bound EVALUATED
    for this tick -- a number for a number bound, the last seated tooth
    for a ratchet -- which is also the value the coordinate now holds,
    exactly. `t` is the fraction of the tick at which it was reached and
    `inputs` names the inputs the stop blocked, sorted.

    A stop is a BOUND OF A COORDINATE, which stops motion; a `Crossing`
    is a JUMP SURFACE of a law, which moves nothing. They answer
    different questions and live in different rings.
    """

    tick: int
    coordinate: str
    bound: str
    value: float
    t: float
    inputs: tuple


def qualified_coordinates(root):
    """Every JOINT COORDINATE in `root`'s linked tree, by qualified id.

    `{qualified_id: (node, name)}`, the id being the instance path
    joined with the name `coordinates_of` reports -- the joint's own for
    a joint owning one, `<joint>.<coordinate>` for each of a `Free`.
    Every linked node the walk reaches is visited, LEAVES INCLUDED,
    because a joint may be declared on a leaf; only an assembly has
    children to descend into, exactly as `drive_tree`'s own walk has it.

    Plain ports and derived coordinates are deliberately absent: they are
    calculations over the state, recomputed by the ordinary enumeration
    on every tick, and the run stores no calculation.
    """
    from solid_node.node.assembly import _rest_children

    found = {}

    def visit(node, path):
        for joint in declared_joints(type(node)).values():
            for name in coordinates_of(joint):
                found[driver_id(path, name)] = (node, name)
        if getattr(node, '_states', None) is None:
            return
        for child in _rest_children(node):
            visit(child, path + (child.name,))

    visit(root, ())
    return found


##############################################
# The jump plan


class _Jump:
    """One jump node of a law, as the plan carries it.

    `argument` is the node's LEVEL QUANTITY -- the continuous expression
    whose surfaces it crosses -- with every jump node INSIDE it already
    replaced by its own branch placeholder, so evaluating it on a piece
    where those branches are fixed is one ordinary evaluation.
    `placeholder` is the free name the skeleton reads this node's branch
    under.
    """

    __slots__ = ('primitive', 'placeholder', 'argument', 'affine')

    def __init__(self, primitive, placeholder, argument, affine):
        self.primitive = primitive
        self.placeholder = placeholder
        self.argument = argument
        self.affine = affine

    def __repr__(self):
        return (f'<{self.primitive} jump on {self.argument} '
                f'{"affine" if self.affine else "searched"}>')


class JumpPlan:
    """How a law that jumps is integrated over one tick.

    The tick moves the law's sources along the straight line from the
    values they hold to those values plus the increments they were
    given, parametrised by `t` in [0, 1] -- in the JOINT source space
    for a law naming several, which is what makes a gate closing while a
    shaft turns one question rather than two.

    That path is cut at every crossing of every jump surface it meets.
    On each open piece every jump node holds one BRANCH, read by
    evaluating its level quantity at the piece's MIDPOINT: a point
    genuinely inside the piece, so the value read there IS the branch,
    exactly, at any magnitude of source and from either direction of
    travel. The law with those branches substituted is continuous on the
    closed piece, so the increment is the plain sum of its change over
    the pieces -- with no epsilon, no one-sided limit rule and no
    direction test anywhere.
    """

    __slots__ = ('skeleton', 'jumps')

    def __init__(self, skeleton, jumps):
        self.skeleton = skeleton
        self.jumps = tuple(jumps)

    def __repr__(self):
        return f'<jump plan of {len(self.jumps)} nodes: {self.skeleton}>'

    ##############################################
    # The increment

    def increment(self, start, delta, described, coordinate,
                  crossings=None, tick=0):
        """The CONTINUOUS part of this law's change over one tick."""
        if not any(delta.values()):
            # A zero-length path contributes zero without evaluating
            # anything -- and must never reach the sum below, where a
            # one-point piece would read as minus a jump.
            return 0.0
        cuts = self._partition(start, delta, described, coordinate,
                               crossings, tick)
        total = 0.0
        for left, right in zip(cuts, cuts[1:]):
            branches = self._branches(start, delta, (left + right) / 2.0,
                                      len(self.jumps), described, coordinate)
            total += (self._substituted(start, delta, right, branches)
                      - self._substituted(start, delta, left, branches))
        return total

    def _substituted(self, start, delta, t, branches):
        values = _along(start, delta, t)
        values.update(branches)
        return self.skeleton.evaluate(values)

    def _branches(self, start, delta, t, count, described, coordinate):
        """Every jump node's branch at one point of the path, in
        postorder, so a node nested inside another's argument is
        determined first."""
        values = _along(start, delta, t)
        found = {}
        for jump in self.jumps[:count]:
            level = self._level(jump, values, described, coordinate)
            branch = _branch_of(jump, level)
            found[jump.placeholder] = branch
            values[jump.placeholder] = branch
        return found

    def _level(self, jump, values, described, coordinate):
        try:
            level = jump.argument.evaluate(values)
        except ZeroDivisionError:
            raise _no_level(jump, described, coordinate) from None
        if jump.primitive in ('floor', 'ceil', '%') \
                and not math.isfinite(level):
            # An integer branch cannot be read off an infinity or a nan,
            # and the arithmetic that would try raises something the
            # tick's rollback does not catch. Refuse it the same way.
            raise _no_level(jump, described, coordinate,
                            'a level quantity that is not a finite number')
        return level

    ##############################################
    # The partition

    def cuts(self, start, delta, described, coordinate):
        """The breakpoints this law's own jumps put on the tick's path.

        The partition the increment already builds, made reachable and
        recording nothing: between two consecutive cuts every jump node
        holds one branch, so a law whose SKELETON is affine has a value
        that is affine in `t` there -- which is what lets a stop on it be
        SOLVED piece by piece rather than searched (design.md section 2,
        case 2).
        """
        if not any(delta.values()):
            return (0.0, 1.0)
        return tuple(self._partition(start, delta, described, coordinate,
                                     None, 0))

    def _partition(self, start, delta, described, coordinate,
                   crossings, tick):
        """The tick's path, cut at every crossing of every jump surface.

        The jump nodes are taken in POSTORDER, so a node's level
        quantity is asked where it crosses only once every jump node
        inside it has already cut the path: on each pair of consecutive
        cuts those inner branches are constant, which is what makes the
        level quantity a continuous function of `t` there and the search
        below well-posed.
        """
        cuts = [0.0, 1.0]
        located = []
        for index, jump in enumerate(self.jumps):
            found = []
            for left, right in zip(cuts, cuts[1:]):
                inner = self._branches(start, delta, (left + right) / 2.0,
                                       index, described, coordinate)
                found.extend(self._crossings_of(
                    jump, start, delta, inner, left, right,
                    described, coordinate))
                if len(found) > _MAX_CROSSINGS:
                    raise _too_many(described, coordinate, jump, len(found))
            if not found:
                continue
            found = _deduplicated(found)
            cuts = _merged(cuts, [where for where, _level in found])
            if len(cuts) - 2 > _MAX_CROSSINGS:
                raise _too_many(described, coordinate, jump, len(cuts) - 2)
            located.extend((where, index, jump.primitive, level)
                           for where, level in found)
        if crossings is not None and located:
            # Sorted by the fraction of the tick, and by the graph's
            # postorder where two coincide, so the listing is
            # deterministic.
            located.sort(key=lambda entry: (entry[0], entry[1]))
            crossings.extend(
                Crossing(tick, described, coordinate, primitive, level, where)
                for where, _index, primitive, level in located)
        return cuts

    def _crossings_of(self, jump, start, delta, inner, left, right,
                      described, coordinate):
        """Where `jump` reaches one of its surfaces between two cuts."""
        if jump.affine:
            # An affine level quantity is determined everywhere on the
            # piece by its two endpoint values, so every surface between
            # them is SOLVED -- all of them, which is what makes a crank
            # that passes three tooth windows in one tick add three
            # throws rather than one.
            low = self._level_at(jump, start, delta, left, inner,
                                 described, coordinate)
            high = self._level_at(jump, start, delta, right, inner,
                                  described, coordinate)
            if high == low:
                return []
            found = []
            for level in _surfaces(jump, low, high, described, coordinate,
                                   inclusive=False):
                found.append((left + (right - left)
                              * (level - low) / (high - low), level))
            return found
        return self._searched(jump, start, delta, inner, left, right,
                              described, coordinate)

    def _searched(self, jump, start, delta, inner, left, right,
                  described, coordinate):
        """Anything else: sampled, bracketed and bisected."""
        width = (right - left) / _SUBDIVISIONS
        points = [left + width * step for step in range(_SUBDIVISIONS)]
        points.append(right)
        levels = [self._level_at(jump, start, delta, where, inner,
                                 described, coordinate) for where in points]
        found = []
        for step in range(_SUBDIVISIONS):
            low, high = levels[step], levels[step + 1]
            for level in _surfaces(jump, low, high, described, coordinate,
                                   inclusive=True):
                if low == level:
                    # A sample that IS on the surface is the crossing;
                    # there is nothing to bisect, and taking it exactly
                    # is what keeps the answer exact when a crossing
                    # falls on a sub-interval boundary.
                    found.append((points[step], level))
                elif high == level:
                    found.append((points[step + 1], level))
                else:
                    found.append((self._bisect(
                        jump, start, delta, inner, level, points[step],
                        points[step + 1], described, coordinate), level))
            if len(found) > _MAX_CROSSINGS:
                break
        return found

    def _bisect(self, jump, start, delta, inner, level, low, high,
                described, coordinate):
        below = self._level_at(jump, start, delta, low, inner,
                               described, coordinate) - level
        for _round in range(_BISECTION_ROUNDS):
            if high - low <= _CROSSING_TOLERANCE:
                break
            middle = (low + high) / 2.0
            here = self._level_at(jump, start, delta, middle, inner,
                                  described, coordinate) - level
            if here == 0.0 or (here < 0.0) != (below < 0.0):
                high = middle
            else:
                low, below = middle, here
        return (low + high) / 2.0

    def _level_at(self, jump, start, delta, t, inner, described, coordinate):
        values = _along(start, delta, t)
        values.update(inner)
        return self._level(jump, values, described, coordinate)


def _is_jump(node):
    return ((node.kind == 'call' and node.op in _JUMP_CALLS)
            or (node.kind == 'binop' and node.op in _JUMP_OPERATORS))


def _along(start, delta, t):
    """The sources at `t` along the tick's straight path.

    At `t == 1` this is exactly `start + delta`, the same float the
    caller computed, because it is the same arithmetic.
    """
    return {name: start[name] + delta[name] * t for name in start}


def _branch_of(jump, level):
    """What `jump` reads on a piece whose level quantity sits at
    `level` -- design.md section 1's branch column."""
    primitive = jump.primitive
    if primitive == 'floor':
        return float(math.floor(level))
    if primitive == 'ceil':
        return float(math.ceil(level))
    if primitive == 'sign':
        return float((level > 0) - (level < 0))
    if primitive == '%':
        # Not a constant but the integer QUOTIENT: with `q` fixed the
        # node reads `a - q * b`, which is continuous in `t`.
        return float(math.trunc(level))
    return float(_COMPARISONS[primitive](level, 0.0))


def _surfaces(jump, low, high, described, coordinate, inclusive):
    """`jump`'s surfaces between two values of its level quantity."""
    if jump.primitive == 'sign' or jump.primitive in _COMPARISONS:
        first, last = (low, high) if low <= high else (high, low)
        if first < 0.0 < last or (inclusive and first <= 0.0 <= last):
            return (0.0,)
        return ()
    first, last = (low, high) if low <= high else (high, low)
    if not math.isfinite(first) or not math.isfinite(last):
        raise _no_level(jump, described, coordinate)
    span = math.ceil(last) - math.floor(first) - 1
    if span > _MAX_CROSSINGS:
        raise _too_many(described, coordinate, jump, span)
    if inclusive:
        levels = [float(whole)
                  for whole in range(math.floor(first), math.ceil(last) + 1)
                  if first <= whole <= last]
    else:
        levels = [float(whole)
                  for whole in range(math.floor(first) + 1, math.ceil(last))
                  if first < whole < last]
    if jump.primitive == '%':
        # `fmod` is `a - b * trunc(a / b)`, and `trunc` is zero on the
        # whole of (-1, 1): the operator is CONTINUOUS where `a / b`
        # crosses zero and jumps only at a nonzero integer of it.
        levels = [level for level in levels if level != 0.0]
    return levels


def _deduplicated(found):
    """One entry per surface actually reached: a crossing that falls on
    a sub-interval boundary is located twice, from either side."""
    ordered = sorted(found, key=lambda entry: (entry[0], entry[1]))
    kept = []
    for where, level in ordered:
        if kept and kept[-1][1] == level \
                and where - kept[-1][0] <= _CROSSING_TOLERANCE:
            continue
        kept.append((where, level))
    return kept


def _merged(cuts, found):
    """The partition with `found` folded in: two cuts closer than the
    tolerance are ONE, and the partition always ends at exactly 1."""
    ordered = sorted(cuts + list(found))
    kept = [ordered[0]]
    for where in ordered[1:]:
        if where - kept[-1] > _CROSSING_TOLERANCE:
            kept.append(where)
    kept[-1] = 1.0
    return kept


def _too_many(described, coordinate, jump, count):
    return TooManyCrossings(
        f'{described}: over one tick {coordinate} would cross {count} '
        f"surfaces of {jump.primitive}, more than the {_MAX_CROSSINGS} a "
        f'single law is admitted in one tick. A dt that coarse is not '
        f'resolving the mechanism: the crossings between the frames are '
        f'what a jump law is FOR. Step in smaller ticks. The tick '
        f'committed nothing: the bank, the tick count and the tree stand '
        f'as they were.')


def _no_level(jump, described, coordinate, reason=None):
    what = reason or ('a divisor of zero' if jump.primitive == '%'
                      else 'a division by zero in its level quantity')
    return UnsupportedLaw(
        f"{described}: its {jump.primitive} meets {what} somewhere on this "
        f'tick\'s path, so there is no level quantity to locate a crossing '
        f'on -- fmod(a, 0) is nan and a / 0 is nothing at all. The tick '
        f'committed nothing and {coordinate} stands where it stood: state '
        f'the relation so the divisor never reaches zero.')


##############################################
# What the program is made of


class Edge:
    """One step of the program: what it reads, what it determines, and
    how.

    `needs` and `gives` are keys into the program's node table. `gives`
    is empty for a CHECK, which determines nothing and only compares what
    its formula predicts with what its coordinate received -- the one
    place a conflict can be detected in this cycle.
    """

    __slots__ = ('kind', 'needs', 'gives', 'graphs', 'plans', 'driven',
                 'names', 'factors', 'constant', 'slot_key', 'description',
                 'stated_by', 'affine')

    def __init__(self, kind, needs, gives, description, stated_by,
                 graphs=(), plans=(), driven=(), names=(), factors=(),
                 constant=0.0, slot_key=None):
        self.kind = kind
        self.needs = tuple(needs)
        self.gives = tuple(gives)
        self.graphs = tuple(graphs)
        # Empty for a law with no jump in it at all, so `increments` can
        # tell the two apart in one test and a continuous law pays
        # nothing for this cycle (design.md section 12).
        self.plans = tuple(plans)
        # The driven coordinates' qualified ids, aligned with `gives`,
        # computed here so a crossing entry costs a tuple and no lookup.
        self.driven = tuple(driven)
        self.names = tuple(names)
        self.factors = tuple(factors)
        self.constant = constant
        self.slot_key = slot_key
        self.description = description
        self.stated_by = stated_by
        # One flag per DRIVEN END, aligned with `gives`: whether this
        # edge's value is affine in its sources along the tick's path, so
        # a stop on that end can be SOLVED rather than searched. A wiring
        # and a formula are linear by construction; a law is read off its
        # graph, or off its SKELETON where it carries a jump plan, whose
        # branch placeholders are constants on a piece.
        self.affine = tuple(self._affine_ends())

    def _affine_ends(self):
        if self.kind != 'law':
            return [True] * len(self.gives)
        found = []
        for index, graph in enumerate(self.graphs):
            plan = self.plans[index] if self.plans else None
            if plan is not None:
                found.append(_affine_in_sources(as_node(plan.skeleton)))
            elif graph is None:
                # A constant law has zero slope everywhere, which is
                # affine and moves nothing.
                found.append(True)
            else:
                found.append(_affine_in_sources(as_node(graph)))
        return found

    def __repr__(self):
        return f'<{self.kind} edge {self.description}>'

    ##############################################
    # Evaluation

    def _inputs(self, values, deltas=None):
        """The graph's free names bound to the values its sources hold,
        optionally advanced by the tick's increments."""
        if deltas is None:
            return {name: values[key]
                    for name, key in zip(self.names, self.needs)}
        return {name: values[key] + deltas[key]
                for name, key in zip(self.names, self.needs)}

    def values(self, values):
        """What this edge's targets hold at the committed state."""
        if self.kind == 'law':
            inputs = self._inputs(values)
            return [(key, _evaluated(graph, inputs))
                    for key, graph in zip(self.gives, self.graphs)]
        if self.kind == 'wiring':
            factor = self.factors[0]
            return [(self.gives[0], values[self.needs[0]] * factor)]
        if self.kind == 'formula':
            return [(self.gives[0], self._linear(values))]
        return []

    def increments(self, values, deltas, crossings=None, tick=0):
        """What this edge's targets MOVE BY over the tick.

        A law with no jump in it is the difference of two exact
        evaluations, which is what makes a kink exact -- and that is the
        FIRST thing tested here, so a continuous law pays nothing for
        the jump machinery. A law that jumps takes its plan, which cuts
        the tick at every crossing and sums the pieces.
        """
        if self.kind == 'law':
            start = self._inputs(values)
            if not self.plans:
                end = self._inputs(values, deltas)
                return [(key,
                         _evaluated(graph, end) - _evaluated(graph, start))
                        for key, graph in zip(self.gives, self.graphs)]
            delta = {name: deltas[key]
                     for name, key in zip(self.names, self.needs)}
            end = self._inputs(values, deltas)
            found = []
            for index, key in enumerate(self.gives):
                plan = self.plans[index]
                if plan is None:
                    graph = self.graphs[index]
                    found.append((key, _evaluated(graph, end)
                                  - _evaluated(graph, start)))
                    continue
                found.append((key, plan.increment(
                    start, delta, self.description, self.driven[index],
                    crossings, tick)))
            return found
        if self.kind == 'wiring':
            return [(self.gives[0], deltas[self.needs[0]] * self.factors[0])]
        if self.kind == 'formula':
            return [(self.gives[0], self._linear(deltas, constant=0.0))]
        return []

    def cuts(self, values, deltas, index):
        """The breakpoints of the driven end at `index` along the tick's
        path, or `()` where that end carries no jump plan."""
        if self.kind != 'law' or not self.plans:
            return ()
        plan = self.plans[index]
        if plan is None:
            return ()
        start = self._inputs(values)
        delta = {name: deltas[key]
                 for name, key in zip(self.names, self.needs)}
        return plan.cuts(start, delta, self.description, self.driven[index])

    def _linear(self, held, constant=None):
        """The linear combination this formula edge states, in the
        direction the rest render resolved it.

        Forward, that is the formula itself. Backward into one term, it
        is the formula rearranged for that term -- exact, because a
        derived coordinate is a coefficient map and a constant, not an
        expression tree.
        """
        total = self.constant if constant is None else constant
        if self.slot_key in self.gives:
            for key, factor in zip(self.needs, self.factors):
                total = total + held[key] * factor
            return total
        # Backward: `gives` is the one term the formula solves for, and
        # `needs` carries the slot first, then the other terms.
        value = held[self.slot_key] - total
        own = None
        for key, factor in zip(self.needs, self.factors):
            if key == self.slot_key:
                continue
            if key == self.gives[0]:
                own = factor
                continue
            value = value - held[key] * factor
        return value / own

    def predicts(self, held, constant=None):
        """What a CHECK edge's formula says its coordinate should hold,
        or move by."""
        total = self.constant if constant is None else constant
        for key, factor in zip(self.needs, self.factors):
            if key == self.slot_key:
                continue
            total = total + held[key] * factor
        return total


def _evaluated(graph, inputs):
    if graph is None:
        # A law whose expression has no free coordinate -- a constant --
        # has zero slope everywhere, so it contributes nothing. It moves
        # nothing by JUMPING either, and untimed it legitimately pins its
        # driven coordinate, so it is not refused: the running reading
        # (the coordinate holds where the rest render put it) is the same
        # statement.
        return 0.0
    return graph.evaluate(inputs)


class Program:
    """A running root's relations, compiled once, in order.

    `identity` is what a snapshot is checked against: a digest of the
    root class, the bank's ids, the inputs' declarations and every edge's
    ends, direction and expression, so a snapshot cannot be restored into
    a tree whose kinematics have moved on.
    """

    def __init__(self, root, inputs, coordinates, nodes, edges, spans=()):
        self.root_class = type(root)
        self.inputs = tuple(inputs)
        self.coordinates = tuple(coordinates)
        self.nodes = nodes
        self.edges = tuple(edges)
        self.determiner = {key: edge for edge in self.edges
                           for key in edge.gives}
        # Every banked coordinate whose joint declares a range, each
        # bound a number, `None`, or a compiled graph over the
        # coordinate's own id.
        self.spans = tuple(spans)
        self.sources = _reaching_inputs(self.nodes, self.edges)
        self.identity = hashlib.sha256(
            self.described().encode()).hexdigest()

    def described(self):
        """The canonical listing the identity is taken of, and what a
        message about the program prints."""
        lines = [f'root {self.root_class.__module__}.'
                 f'{self.root_class.__qualname__}']
        for identifier, declaration in self.inputs:
            lines.append(f'input {identifier} dtype={declaration.dtype!r} '
                         f'scale={declaration.scale!r}')
        for identifier in self.coordinates:
            lines.append(f'coordinate {identifier}')
        for identifier, low, high, unit in self.spans:
            # A changed range changes the identity, so a snapshot cannot
            # be restored into a machine whose stops have moved.
            lines.append(f'span {identifier} {_written(low)} to '
                         f'{_written(high)} {unit or "units"}')
        for edge in self.edges:
            ends = (f'{[self.nodes[key].name for key in edge.needs]} -> '
                    f'{[self.nodes[key].name for key in edge.gives]}')
            if edge.kind == 'law':
                how = ' | '.join('constant' if graph is None else str(graph)
                                 for graph in edge.graphs)
            elif edge.kind == 'wiring':
                how = f'identity * {edge.factors[0]!r}'
            else:
                how = (f'{list(edge.factors)!r} + {edge.constant!r} '
                       f'on {self.nodes[edge.slot_key].name}')
            lines.append(f'{edge.kind} {ends} {how} [{edge.description}]')
        return '\n'.join(lines)

    def __repr__(self):
        return (f'<program of {self.root_class.__name__}: '
                f'{len(self.nodes)} coordinates, {len(self.edges)} edges>')


def _written(bound):
    """One bound as the identity prints it."""
    if bound is None:
        return 'unbounded'
    if isinstance(bound, GraphValue):
        return str(bound)
    return repr(bound)


def _reaching_inputs(nodes, edges):
    """Every INPUT that reaches each node key through the program: the
    CANDIDATE table a stop's group is filtered out of.

    One pass over the already topologically ordered edges, so it costs
    the program once and nothing per tick. A CHECK edge determines
    nothing and contributes nothing. Being reached is necessary and not
    sufficient: whether a candidate actually PUSHES a stopped coordinate
    is a property of the tick, tested there, because an input coupled
    only through a disengaged law reaches it and moves it not at all.
    """
    found = {key: (frozenset({key[1]}) if node.kind == 'input'
                   else frozenset())
             for key, node in nodes.items()}
    for edge in edges:
        if edge.kind == 'check':
            continue
        reached = frozenset().union(*(found[key] for key in edge.needs)) \
            if edge.needs else frozenset()
        for key in edge.gives:
            found[key] |= reached
    return found


class _Node:
    """One coordinate the program computes over: a bank id, or an
    INTERMEDIATE a compiled edge determines."""

    __slots__ = ('key', 'name', 'kind')

    def __init__(self, key, name, kind):
        self.key = key
        self.name = name
        self.kind = kind

    def __repr__(self):
        return f'<{self.kind} {self.name}>'


##############################################
# Compiling


def compile_program(root, inputs, coordinates):
    """The program of `root`, read off what the REST RENDER solved.

    `inputs` is `{qualified id: Driver}` and `coordinates` is
    `{qualified id: (node, name)}`; together they are the bank.
    """
    nodes = {}
    for identifier, _declaration in inputs.items():
        nodes[('input', identifier)] = _Node(
            ('input', identifier), identifier, 'input')
    bank_keys = set(nodes)
    for identifier, (node, name) in coordinates.items():
        from solid_node.motion.ports import get_coordinate

        slot = get_coordinate(node, name)
        key = ('slot', id(slot))
        nodes[key] = _Node(key, identifier, 'bank')
        bank_keys.add(key)

    candidates = []
    for assembly, path, records, formulas, wirings in _units(root):
        for record in records:
            edge = _relation_edge(root, assembly, record, nodes, bank_keys)
            if edge is not None:
                candidates.append(edge)
        for wiring in wirings:
            edge = _wiring_edge(root, assembly, wiring, nodes)
            if edge is not None:
                candidates.append(edge)
        for formula in formulas:
            edge = _formula_edge(root, assembly, formula, nodes)
            if edge is not None:
                candidates.append(edge)

    kept = _reaching_the_bank(candidates, bank_keys)
    _refuse_opaque(kept, bank_keys, nodes)
    ordered = _ordered(kept, nodes)
    return Program(root, sorted(inputs.items()), sorted(coordinates),
                   nodes, ordered, _compiled_spans(coordinates))


##############################################
# The span table


def _compiled_spans(coordinates):
    """`(qualified id, low, high, unit)` for every banked coordinate
    whose joint declares a range, resolved ONCE.

    Each bound is a number, `None` for unbounded on that side, or an
    expression GRAPH over the coordinate's own qualified id -- compiled
    here exactly as a law is, and for the same two reasons: what the
    expression cannot say is refused now rather than every tick, and a
    graph is what cycle 4 can publish beside the coordinate table.
    """
    found = []
    for identifier, (node, name) in sorted(coordinates.items()):
        for joint in declared_joints(type(node)).values():
            if name not in joint.coordinates:
                continue
            span = joint.arguments(node)[2]
            if span is not None:
                found.append((identifier,
                              _compiled_bound(span[0], identifier, node,
                                              joint, 'lower'),
                              _compiled_bound(span[1], identifier, node,
                                              joint, 'upper'),
                              joint.unit))
            break
    return tuple(found)


def _compiled_bound(bound, identifier, node, joint, side):
    """One declared bound as the run reads it: `None`, a float, or an
    expression graph over `identifier` alone."""
    def refuse(detail):
        raise UnsupportedLaw(
            f"{type(node).__name__}.{joint.name}: its {side} bound -- "
            f"the range of the coordinate '{identifier}' -- {detail}")

    if bound is None:
        return None
    if isinstance(bound, bool):
        refuse(f'is {bound!r}, which is neither a number nor an expression.')
    if isinstance(bound, (int, float)):
        return float(bound)
    if not callable(bound):
        refuse(f'resolved to {bound!r}, which is neither a number nor a '
               f"callable of the joint's own coordinate.")
    try:
        returned = bound(symbol(identifier))
    except Exception as failure:
        refuse(f'cannot be applied to a symbol '
               f'({type(failure).__name__}: {failure}). A bound is an '
               f'expression over the joint\'s own coordinate: it is applied '
               f'once, to a token for that coordinate, and the graph it '
               f'builds is what the run evaluates at the start of every '
               f'tick. Write it with solid_node.math, whose primitives are '
               f'symbolic.')
    if isinstance(returned, bool):
        refuse(f'returned {returned!r}, which is neither a number nor an '
               f'expression.')
    if isinstance(returned, (int, float)):
        return float(returned)
    if not isinstance(returned, OpenSCADConstant):
        refuse(f'returned {returned!r}, which is neither a number nor an '
               f"expression over the joint's own coordinate.")
    root = as_node(returned)
    for item in postorder([root]):
        if item.kind == 'raw':
            refuse(f'carries the text {item.text!r}, which the framework '
                   f'cannot evaluate.')
        if item.kind == 'call' and item.op not in SYMBOLIC_BUILTINS:
            refuse(f'calls {item.op!r}, which is outside the symbolic '
                   f'vocabulary the run can evaluate.')
    names = free_names(root)
    if not names <= {identifier}:
        others = ', '.join(sorted(names - {identifier}))
        refuse(f'reads {others}, and a bound in this release is an '
               f"expression over the joint's OWN coordinate alone. A bound "
               f'naming a second coordinate needs a declaration that says '
               f'what it reads, resolved against the declarer subtree; it '
               f'is not in this release.')
    # A JUMP is admitted and needs no plan: a bound is EVALUATED at one
    # point per tick and never integrated, so `floor` means `floor` and
    # nothing is subtracted. That asymmetry with a law is the point -- a
    # law's jump would move a part, a bound's jump is the tooth pitch.
    return GraphValue(root)


def _units(root):
    """Every assembly of the linked tree with what its own rest render
    recorded: its relation records, the derived coordinates it solves and
    its wirings, in tree order."""
    from solid_node.node.assembly import _rest_children

    found = []

    def visit(node, path):
        if getattr(node, '_states', None) is None:
            return
        records = node.__dict__.get('_relations', ())
        found.append((node, path, records,
                      _solved_formulas(node, records), _wirings(node)))
        for child in _rest_children(node):
            visit(child, path + (child.name,))

    visit(root, ())
    return found


def _register(nodes, root, end):
    """`end`'s program node, created on first sight."""
    if end.is_driver:
        key = ('input', _qualified(root, end))
    else:
        key = ('slot', id(end.slot))
    found = nodes.get(key)
    if found is None:
        found = nodes[key] = _Node(key, _qualified(root, end), 'intermediate')
    return found


def _qualified(root, end):
    from solid_node.node.qualified import DriverIdError

    try:
        return driver_id(instance_path(end.node, root), end.name)
    except DriverIdError:
        return f'{type(end.node).__name__}.{end.name}'


def _relation_edge(root, assembly, record, nodes, bank_keys):
    """One relation as an edge, in the direction the rest render solved
    it -- or `None` when the rest render left it to no one."""
    if record.direction not in ('forward', 'backward'):
        return None
    if record.direction == 'forward':
        sources, targets = record.driver_ends, record.driven_ends
    else:
        sources, targets = record.driven_ends, record.driver_ends
    source_nodes = [_register(nodes, root, end) for end in sources]
    target_nodes = [_register(nodes, root, end) for end in targets]

    banked = [node.key in bank_keys for node in target_nodes]
    if any(banked) and not all(banked):
        raise UnsupportedLaw(
            f'{record.described()}, stated by {type(assembly).__name__}: '
            f'its driven ends are '
            f'{", ".join(node.name for node in target_nodes)}, of which the '
            f'running simulation owns only some. A relation drives one '
            f'group; state the rest as joints, or as a relation of their '
            f'own.')

    compiled = _law_graphs(assembly, record, source_nodes,
                           len(target_nodes))
    graphs = [graph for graph, _plan in compiled]
    plans = [plan for _graph, plan in compiled]
    if any(plan is not None for plan in plans) and not any(banked):
        # A subtracted jump implies a HISTORY, and an intermediate keeps
        # none: the ordinary enumeration recomputes it absolutely from
        # the bank on every tick, so its value would snap by the
        # accumulated jumps while the joint behind it moved smoothly.
        raise UnsupportedLaw(
            f'{record.described()}, stated by {type(assembly).__name__}: '
            f'its law contains a jump and its driven ends are '
            f'{", ".join(node.name for node in target_nodes)}, none of '
            f'which the running simulation owns. A subtracted jump implies '
            f'a history, and only a coordinate the run owns keeps one -- a '
            f'plain port and a derived coordinate are calculations the '
            f'ordinary enumeration recomputes from the bank on every tick, '
            f'so this one would snap while the joint behind it moved '
            f'smoothly. State the relation into the joint coordinate and '
            f'let the port follow it.')
    return Edge('law', [node.key for node in source_nodes],
                [node.key for node in target_nodes],
                record.described(), type(assembly).__name__,
                graphs=graphs,
                plans=plans if any(plan is not None for plan in plans) else (),
                driven=[node.name for node in target_nodes],
                names=[node.name for node in source_nodes])


def _law_graphs(assembly, record, source_nodes, count):
    """The law applied ONCE to a symbolic token per source, checked to be
    an expression the run can evaluate, and compiled into a jump plan
    where it jumps: one `(graph, plan)` per driven end."""
    def refuse(detail):
        raise UnsupportedLaw(
            f'{record.described()}, stated by {type(assembly).__name__}: '
            f'{detail}')

    tokens = [symbol(node.name) for node in source_nodes]
    try:
        if record.direction == 'backward':
            returned = record.law.inverse(tokens[0])
        else:
            returned = record.law.forward(*tokens)
    except Exception as failure:
        refuse(f'the law {record.law!r} cannot be applied to symbols '
               f'({type(failure).__name__}: {failure}). A running law is '
               f'an expression over its sources: it is applied once, to a '
               f'token per source, and the graph it builds is what the run '
               f'integrates. Write it with solid_node.math, whose '
               f'primitives are symbolic.')

    if count == 1:
        returned = (returned,)
    else:
        try:
            length = len(returned)
        except TypeError:
            length = None
        if length != count:
            refuse(f'the law {record.law!r} returned {returned!r} for '
                   f'{count} driven ends, which is not a sequence of '
                   f'exactly {count} values.')
    return [_graph_of(value, refuse) for value in returned]


def _graph_of(value, refuse):
    """`value` as the expression graph the run evaluates and the JUMP
    PLAN beside it, `(None, None)` for a constant, or the refusal naming
    what it is instead."""
    if isinstance(value, bool):
        refuse(f'the law returned {value!r}, which is neither a number nor '
               f'an expression.')
    if isinstance(value, (int, float)):
        return None, None
    if not isinstance(value, OpenSCADConstant):
        refuse(f'the law returned {value!r}, which is neither a number nor '
               f'an expression over its sources.')
    root = as_node(value)
    jumps = []
    for item in postorder([root]):
        if item.kind == 'raw':
            refuse(f'its expression carries the text {item.text!r}, which '
                   f'the framework cannot evaluate: a running law is an '
                   f'expression over its sources.')
        if item.kind == 'call' and item.op not in SYMBOLIC_BUILTINS:
            refuse(f'its expression calls {item.op!r}, which is outside '
                   f'the symbolic vocabulary the run can evaluate.')
        if _is_jump(item):
            jumps.append(item)
    if not jumps:
        return GraphValue(root), None
    if _only_jumps(root):
        refuse('its expression can move its driven coordinate only by '
               'jumping: with every jump node and the whole argument '
               'subtree beneath it replaced by a constant, no free '
               'coordinate is left. Every jump is subtracted -- a jump '
               'never moves a part -- so this law can never move anything '
               'at all. It states arithmetic, not a mechanism: give the '
               'coordinate a relation that carries slope, or leave the '
               'count to the code that reads the machine.')
    return GraphValue(root), _plan_of(root, jumps)


def _plan_of(root, jumps):
    """The jump plan of a graph: the skeleton, and the jump nodes in the
    graph's postorder with their level quantities."""
    placeholders = {node: ExpressionNode(
        'name', text=f'${"q" if node.op == "%" else "j"}{index}')
        for index, node in enumerate(jumps)}
    skeleton = _skeleton(root, placeholders)
    planned = []
    for node in jumps:
        argument = _argument_graph(node, skeleton.replaced)
        planned.append(_Jump(node.op, placeholders[node].text,
                             GraphValue(argument),
                             _affine_in_sources(argument)))
    return JumpPlan(GraphValue(skeleton.root), planned)


class _Rewritten:
    """A graph with every jump node replaced, and the replacement map
    the argument graphs are cut from."""

    __slots__ = ('root', 'replaced')

    def __init__(self, root, replaced):
        self.root = root
        self.replaced = replaced


def _skeleton(root, placeholders):
    """`root` with every jump node replaced by its branch placeholder --
    and every `%` node by `a - q * b`, which is what a fixed quotient
    leaves of it.

    Memoised BY NODE IDENTITY, because `postorder` visits each reachable
    identity once: a subgraph two consumers share stays ONE node with one
    branch, which is the sharing ADR-080 introduced surviving into the
    plan for free.
    """
    replaced = {}
    for node in postorder([root]):
        if node in placeholders:
            if node.op == '%':
                left = replaced.get(node.children[0], node.children[0])
                right = replaced.get(node.children[1], node.children[1])
                replaced[node] = ExpressionNode('binop', '-', (
                    left, ExpressionNode('binop', '*',
                                         (placeholders[node], right))))
            else:
                replaced[node] = placeholders[node]
        elif node.children:
            children = tuple(replaced.get(child, child)
                             for child in node.children)
            if children != node.children:
                replaced[node] = ExpressionNode(
                    node.kind, node.op, children, node.text)
    return _Rewritten(replaced.get(root, root), replaced)


def _argument_graph(node, replaced):
    """`node`'s LEVEL QUANTITY -- the continuous quantity whose surfaces
    it crosses -- with the jump nodes INSIDE it already replaced."""
    parts = [replaced.get(child, child) for child in node.children]
    if node.kind == 'call':
        return parts[0]
    if node.op == '%':
        return ExpressionNode('binop', '/', (parts[0], parts[1]))
    return ExpressionNode('binop', '-', (parts[0], parts[1]))


def _affine_in_sources(root):
    """Whether `root` is AFFINE in the sources along the path, so its
    crossings can be solved rather than searched.

    Structural and computed once: numbers, source names, branch
    placeholders (constants on a piece), unary minus, `+` and `-` of
    affine operands, `*` with a constant operand and `/` by one. A call,
    a power, or a product of two moving operands is not affine, and
    falls to the search -- correct but slower, which is why
    `floor(max(x, 0))` is searched although it is piecewise affine.
    """
    degree = {}
    for node in postorder([root]):
        degree[node] = _degree_of(node, degree)
    return degree[root] in ('constant', 'affine')


def _degree_of(node, degree):
    if node.kind == 'num':
        return 'constant'
    if node.kind == 'name':
        # A branch placeholder is a constant on the piece being cut; a
        # source name is what moves along the path.
        return 'constant' if node.text.startswith('$') else 'affine'
    if not node.children:
        return None
    children = [degree[child] for child in node.children]
    if all(child == 'constant' for child in children):
        return 'constant'
    if node.kind == 'unary':
        return children[0] if children[0] == 'affine' else None
    if node.kind != 'binop':
        return None
    left, right = children
    moving = ('constant', 'affine')
    if node.op in ('+', '-'):
        return 'affine' if left in moving and right in moving else None
    if node.op == '*':
        if (left == 'constant' and right in moving) \
                or (right == 'constant' and left in moving):
            return 'affine'
        return None
    if node.op == '/':
        return 'affine' if right == 'constant' and left in moving else None
    return None


def _only_jumps(root):
    """Whether the law's CONTINUOUS SKELETON -- every jump node reduced
    to what a FIXED BRANCH leaves of it -- has no free coordinate left.

    `floor(turns)` reduces to a constant and is refused;
    `9 * enabled + floor(turns)` keeps `enabled` and is not, because
    `enabled` still carries slope.

    Four of the five primitives reduce to a constant, so the node and
    the whole argument subtree beneath it go. `%` does not: its branch
    is the integer QUOTIENT, and with that fixed `a % b` reads
    `a - q * b`, which still carries `a`'s slope. Reducing it to a
    constant would refuse `angle % 360` -- the tooth window written with
    the operator instead of the `floor`, which design.md section 6
    requires to read the same at every tick as the `floor` spelling
    does, and which moves by far more than jumping.
    """
    constant = ExpressionNode('num', text='0')
    replaced = {}
    for node in postorder([root]):
        if _is_jump(node):
            if node.op == '%':
                left = replaced.get(node.children[0], node.children[0])
                right = replaced.get(node.children[1], node.children[1])
                replaced[node] = ExpressionNode('binop', '-', (
                    left, ExpressionNode('binop', '*', (constant, right))))
            else:
                replaced[node] = constant
        elif node.children:
            children = tuple(replaced.get(child, child)
                             for child in node.children)
            if children != node.children:
                replaced[node] = ExpressionNode(
                    node.kind, node.op, children, node.text)
    return not free_names(replaced.get(root, root))


def _wiring_edge(root, assembly, wiring, nodes):
    """A wiring as the forward-only identity edge it already is."""
    source = _slot_node(nodes, root, wiring.slot)
    target = _slot_node(nodes, root, wiring.target)
    factor = 1.0 if wiring.target.scale is None else wiring.target.scale
    return Edge('wiring', [source.key], [target.key],
                wiring.described(), type(assembly).__name__,
                factors=[factor], names=[source.name])


def _slot_node(nodes, root, slot):
    key = ('slot', id(slot))
    found = nodes.get(key)
    if found is None:
        from solid_node.node.qualified import DriverIdError

        try:
            name = driver_id(instance_path(slot.node, root), slot.name)
        except DriverIdError:
            name = f'{type(slot.node).__name__}.{slot.name}'
        found = nodes[key] = _Node(key, name, 'intermediate')
    return found


def _formula_edge(root, assembly, formula, nodes):
    """A derived coordinate as the LINEAR edge it is, in the direction
    the rest render resolved it -- or as a CHECK when its slot and every
    term were bound by others, which is the one place two inputs
    prescribing one rigid group can be caught."""
    slot = formula.slot_of(assembly)
    slot_node = _slot_node(nodes, root, slot)
    terms = formula.resolved_terms(assembly)
    term_nodes = [(_register(nodes, root, end), float(coefficient))
                  for end, coefficient in terms]
    constant = float(formula.resolved_constant(assembly))
    described = f"the derived coordinate '{formula.described()}' " \
                f'({formula.written})'

    if slot.binder is formula:
        return Edge('formula', [node.key for node, _ in term_nodes],
                    [slot_node.key], described, type(assembly).__name__,
                    factors=[factor for _, factor in term_nodes],
                    constant=constant, slot_key=slot_node.key)
    for (node, _factor), (end, _coefficient) in zip(term_nodes, terms):
        if end.slot is not None and end.slot.binder is formula:
            needs = [slot_node.key] + [other.key for other, _ in term_nodes
                                       if other is not node]
            factors = ([0.0] + [factor for other, factor in term_nodes
                                if other is not node])
            # The solved-for term's own coefficient travels with it, so
            # `_linear` can divide by it.
            needs.append(node.key)
            factors.append(next(factor for other, factor in term_nodes
                                if other is node))
            return Edge('formula', needs, [node.key], described,
                        type(assembly).__name__, factors=factors,
                        constant=constant, slot_key=slot_node.key)
    needs = [slot_node.key] + [node.key for node, _ in term_nodes]
    factors = [0.0] + [factor for _, factor in term_nodes]
    return Edge('check', needs, (), described, type(assembly).__name__,
                factors=factors, constant=constant, slot_key=slot_node.key)


def _reaching_the_bank(candidates, bank_keys):
    """The edges that matter: one determining a coordinate the run owns,
    one determining anything such an edge reads, and a CHECK over what
    those produce.

    A relation or wiring whose driven ends are all outside the bank and
    reach no bank coordinate -- a pulley driving a belt's plain port --
    is left to the ordinary enumeration, which recomputes it from the
    run-bound sources on every tick.
    """
    matters = set(bank_keys)
    kept = []
    changed = True
    while changed:
        changed = False
        for edge in candidates:
            if edge in kept:
                continue
            reached = (set(edge.needs) if edge.kind == 'check'
                       else set(edge.gives))
            if not (reached & matters):
                continue
            kept.append(edge)
            matters.update(edge.needs)
            matters.update(edge.gives)
            changed = True
    return kept


def _refuse_opaque(kept, bank_keys, nodes):
    """An edge reading a coordinate the run does not own and no kept edge
    computes is refused by name: a plain port the author's `simulate()`
    binds is a value stated imperatively, not a relation the run can
    integrate."""
    computed = {key for edge in kept for key in edge.gives}
    for edge in kept:
        for key in edge.needs:
            if key in bank_keys or key in computed:
                continue
            raise UnsupportedLaw(
                f'{edge.description}, stated by {edge.stated_by}: it is '
                f'sourced from {nodes[key].name}, which the running '
                f'simulation does not own and no relation computes -- a '
                f'plain port an author\'s simulate() binds. The run '
                f'integrates relations over drivers and joint '
                f'coordinates, so state that value as a relation, or give '
                f'the part a joint.')


def _ordered(kept, nodes):
    """The edges in an order where every edge's sources are determined
    before it runs: Kahn over the ends each edge determines.

    A coordinate no edge determines is resolved from the start -- it is
    an input, or it HOLDS -- so an edge waits only on the ends something
    else in the program moves.
    """
    determiner = {}
    for edge in kept:
        for key in edge.gives:
            determiner[key] = edge
    resolved = {key for key in nodes if key not in determiner}
    order = []
    remaining = list(kept)
    while remaining:
        ready = [edge for edge in remaining
                 if all(key in resolved for key in edge.needs)]
        if not ready:
            stuck = ', '.join(edge.description for edge in remaining)
            raise UnsupportedLaw(
                f'the relations {stuck} form a cycle the run cannot order: '
                f'each waits on a coordinate another determines. A running '
                f'program is acyclic, because the rest render solved every '
                f'relation in one direction.')
        for edge in ready:
            order.append(edge)
            remaining.remove(edge)
            resolved.update(edge.gives)
    return order
