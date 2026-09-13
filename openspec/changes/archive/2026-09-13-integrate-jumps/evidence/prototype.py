# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""PROPOSAL EVIDENCE, not an implementation.

A standalone prototype of the segmented integrator of `design.md`
sections 3 to 5, written against the framework's own expression graph
(`solid_node.expression_graph`, `solid_node.scad_expression`,
`solid_node.math`) but OUTSIDE `solid_node/`, so that the worked
numbers in the design can be checked before a line of framework code is
written. The implementation lives in `solid_node/simulation/program.py`
and must reproduce these numbers through the framework's own evaluator,
not through this file.

Run from the worktree:

    PYTHONPATH="$PWD" python openspec/changes/integrate-jumps/evidence/prototype.py
"""

import math
import operator

import solid_node.math as degree_math
from solid_node.expression_graph import postorder
from solid_node.math import abs, clamp01, floor, sign, wrap
from solid_node.scad_expression import as_node, symbol

_JUMP_CALLS = ('floor', 'ceil', 'sign')
_JUMP_OPERATORS = ('%', '<', '<=', '>', '>=', '==', '!=')

_CROSSING_TOLERANCE = 1e-12
_SUBDIVISIONS = 64
_BISECTION_ROUNDS = 64
_MAX_CROSSINGS = 1000

_OPERATORS = {'+': operator.add, '-': operator.sub, '*': operator.mul,
              '/': operator.truediv, '%': math.fmod, '^': operator.pow,
              '<': operator.lt, '<=': operator.le, '>': operator.gt,
              '>=': operator.ge, '==': operator.eq, '!=': operator.ne}


def _is_jump(node):
    return ((node.kind == 'call' and node.op in _JUMP_CALLS)
            or (node.kind == 'binop' and node.op in _JUMP_OPERATORS))


def _evaluate(root, inputs, branches):
    """`root` over `inputs`, with every jump node in `branches` replaced
    by its branch: a constant for floor/ceil/sign/a comparison, and the
    integer quotient of a `%`, whose branch form is `a - q * b`."""
    values = {}
    for node in postorder([root]):
        if node in branches:
            kind, payload = branches[node]
            if kind == 'constant':
                values[node] = payload
            else:
                left, right = values[node.children[0]], values[node.children[1]]
                values[node] = left - payload * right
            continue
        args = [values[child] for child in node.children]
        if node.kind == 'num':
            values[node] = float(node.text)
        elif node.kind == 'name':
            values[node] = float(inputs[node.text])
        elif node.kind == 'binop':
            values[node] = _OPERATORS[node.op](*args)
        elif node.kind == 'unary':
            values[node] = -args[0] if node.op == '-' else +args[0]
        elif node.kind == 'call':
            values[node] = getattr(degree_math, node.op)(*args)
        else:
            raise ValueError(node)
    return values[root]


def _branches_at(root, jumps, inputs):
    """Every jump node's branch, read at one point, in postorder."""
    found = {}
    for node in postorder([root]):
        if node not in jumps:
            continue
        if node.kind == 'call':
            level = _evaluate(node.children[0], inputs, found)
            if node.op == 'floor':
                found[node] = ('constant', float(math.floor(level)))
            elif node.op == 'ceil':
                found[node] = ('constant', float(math.ceil(level)))
            else:
                found[node] = ('constant', float((level > 0) - (level < 0)))
        elif node.op == '%':
            left = _evaluate(node.children[0], inputs, found)
            right = _evaluate(node.children[1], inputs, found)
            if right == 0:
                raise ZeroDivisionError('a % b with b == 0 has no level')
            found[node] = ('quotient', math.trunc(left / right))
        else:
            left = _evaluate(node.children[0], inputs, found)
            right = _evaluate(node.children[1], inputs, found)
            found[node] = ('constant',
                           1.0 if _OPERATORS[node.op](left, right) else 0.0)
    return found


def _at(start, delta, t):
    return {name: start[name] + delta[name] * t for name in start}


def _level(node, inputs, branches):
    """The continuous quantity whose surfaces this node jumps at."""
    if node.kind == 'call':
        return _evaluate(node.children[0], inputs, branches)
    left = _evaluate(node.children[0], inputs, branches)
    right = _evaluate(node.children[1], inputs, branches)
    if node.op == '%':
        if right == 0:
            raise ZeroDivisionError('a % b with b == 0 has no level')
        return left / right
    return left - right


def _surfaces(node, low, high):
    """The surfaces of `node` strictly between two level values."""
    if node.kind == 'call' and node.op == 'sign':
        return [0.0] if low < 0 < high or high < 0 < low else []
    if node.kind == 'binop' and node.op != '%':
        return [0.0] if low < 0 < high or high < 0 < low else []
    lo, hi = (low, high) if low < high else (high, low)
    levels = [float(m) for m in range(math.floor(lo) + 1, math.ceil(hi))
              if lo < m < hi]
    if node.kind == 'binop' and node.op == '%':
        levels = [m for m in levels if m != 0.0]
    return levels


def increment(root, start, delta):
    """The CONTINUOUS part of `root`'s change over one tick."""
    if not any(delta.values()):
        return 0.0
    jumps = [node for node in postorder([root]) if _is_jump(node)]
    if not jumps:
        return (_evaluate(root, _at(start, delta, 1.0), {})
                - _evaluate(root, _at(start, delta, 0.0), {}))
    jump_set = set(jumps)
    cuts = [0.0, 1.0]
    for node in jumps:
        found = []
        for a, b in zip(cuts, cuts[1:]):
            inner = {k: v for k, v in
                     _branches_at(root, jump_set, _at(start, delta, (a + b) / 2)).items()
                     if k is not node}
            ua = _level(node, _at(start, delta, a), inner)
            ub = _level(node, _at(start, delta, b), inner)
            # Every level quantity exercised below is AFFINE along the
            # path, so the crossing is solved. `_bisect` is the branch
            # design.md section 4 takes for anything else; the
            # implementation must classify structurally rather than
            # assume, which is what task 3.4 is.
            for level in _surfaces(node, ua, ub):
                found.append(a + (b - a) * (level - ua) / (ub - ua))
        cuts = _merged(cuts + found)
        if len(cuts) - 2 > _MAX_CROSSINGS:
            raise ValueError(f'more than {_MAX_CROSSINGS} crossings in one tick')
    total = 0.0
    for a, b in zip(cuts, cuts[1:]):
        branches = _branches_at(root, jump_set, _at(start, delta, (a + b) / 2))
        total += (_evaluate(root, _at(start, delta, b), branches)
                  - _evaluate(root, _at(start, delta, a), branches))
    return total


def _merged(cuts):
    ordered = sorted(cuts)
    kept = [ordered[0]]
    for t in ordered[1:]:
        if t - kept[-1] > _CROSSING_TOLERANCE:
            kept.append(t)
    kept[-1] = 1.0
    return kept


def _bisect(node, start, delta, inner, level, a, b):
    for _ in range(_BISECTION_ROUNDS):
        if b - a <= _CROSSING_TOLERANCE:
            break
        mid = (a + b) / 2
        if ((_level(node, _at(start, delta, a), inner) - level)
                * (_level(node, _at(start, delta, mid), inner) - level) <= 0):
            b = mid
        else:
            a = mid
    return (a + b) / 2


##############################################
# The worked numbers of design.md


def _sweep(root, name, start, step, ticks, initial=0.0):
    value, source = initial, start
    trace = []
    for _ in range(ticks):
        value += increment(root, {name: source}, {name: step})
        source += step
        trace.append(value)
    return value, source, trace


def main():
    angle = symbol('crank')

    print('design.md section 6 -- the Curta illustration, dt = 1/240')
    window = as_node(4 + 72 * clamp01(
        (angle - 360 * floor(angle / 360) - 113.5) / 11.25))
    pinion, crank, trace = _sweep(window, 'crank', 100.0, 1.5, 240, initial=4.0)
    print(f'  tick  10: {trace[9]!r}   tick  16: {trace[15]!r}   '
          f'tick  17: {trace[16]!r}')
    print(f'  tick 173: {trace[172]!r}  tick 174: {trace[173]!r}  '
          f'(the crossing tick)')
    print(f'  after one turn  (crank {crank}): pinion {pinion!r}')
    pinion, crank, _ = _sweep(window, 'crank', crank, 1.5, 240, initial=pinion)
    print(f'  after two turns (crank {crank}): pinion {pinion!r}')

    print('  three windows in ONE tick, move(by=1080, duration=0):')
    print('   ', 4.0 + increment(window, {'crank': 100.0}, {'crank': 1080.0}))

    print('design.md section 6 -- a wrapped law integrates to the travel')
    wrapped = as_node(2 * wrap(angle, 360.0))
    print('   ', increment(wrapped, {'crank': 100.0}, {'crank': 500.0}))

    print('design.md section 6 -- % agrees with floor')
    remainder = as_node(4 + 72 * clamp01(((angle % 360) - 113.5) / 11.25))
    print('   ', 4.0 + _sweep(remainder, 'crank', 100.0, 1.5, 240)[0])

    print('design.md section 6 -- sign that does not jump == its abs twin')
    reversing = as_node(5 * (angle - 50.0) * sign(angle - 50.0))
    kinked = as_node(5 * abs(angle - 50.0))
    print('   ', increment(reversing, {'crank': 40.0}, {'crank': 20.0}),
          increment(kinked, {'crank': 40.0}, {'crank': 20.0}))

    print('design.md section 6 -- a nested jump: alternate revolutions')
    w = floor(angle / 360)
    alternating = as_node(
        72 * clamp01((angle - 360 * w - 113.5) / 11.25)
        * (1 - (w - 2 * floor(w / 2))))
    value, crank = 0.0, 100.0
    for turn in range(4):
        value, crank, _ = _sweep(alternating, 'crank', crank, 1.5, 240,
                                 initial=value)
        print(f'  after turn {turn + 1}: {round(value, 9)!r}')

    print('design.md section 7 -- the clutch')
    shaft, sleeve = symbol('shaft'), symbol('sleeve')
    clutch = as_node(-2 * shaft * (sleeve > 0.5))
    for label, s0, d in (('open   ', {'shaft': 10.0, 'sleeve': 0.0},
                          {'shaft': 4.0, 'sleeve': 0.0}),
                         ('closed ', {'shaft': 10.0, 'sleeve': 1.0},
                          {'shaft': 4.0, 'sleeve': 0.0}),
                         ('closing', {'shaft': 10.0, 'sleeve': 0.0},
                          {'shaft': 4.0, 'sleeve': 1.0})):
        print(f'  {label}: {increment(clutch, s0, d)!r}')

    print("design.md section 6 -- handed_on's shape, fixture constants")
    below = symbol('below')
    for lead, want in ((0.0, 120.0), (0.5, 118.0)):
        turns = floor((below - 100.0) / 360.0)
        phase = below - 360.0 * turns
        advance = 60.0 * turns
        for st, wd, rise in ((100.0, 10.0, 20.0), (110.0, 40.0, 40.0)):
            advance = advance + rise * clamp01((phase - st + lead) / wd)
        root = as_node(advance)
        total, _, _ = _sweep(root, 'below', 100.0, 10.0, 72)
        print(f'  lead {lead}: two revolutions hand on {round(total, 9)!r} '
              f'(want {want})')

    print("design.md section 6 -- the MODULE's own constants")
    OPEN, THROW, LEAD = 115.0, 65.54, 0.10
    segments = ((115.0, 3.0, 4.10), (118.0, 6.0, 6.74), (124.0, 48.0, 47.88),
                (172.0, 6.0, 4.82), (178.0, 2.0, 1.28), (180.0, 1.0, 0.58),
                (181.0, 1.0, 0.14))
    turns = floor((below - OPEN) / 360.0)
    phase = below - 360.0 * turns
    advance = THROW * turns
    for st, wd, rise in segments:
        advance = advance + rise * clamp01((phase - st + LEAD) / wd)
    total, _, _ = _sweep(as_node(advance), 'below', 200.0, 10.0, 36)
    print(f'  one revolution hands on {total!r} against CARRY_THROW {THROW}; '
          f'deficit {THROW - total!r} = first_rise * lead / first_width = '
          f'{4.10 * LEAD / 3.0!r}')

    print('design.md section 11 -- the large origin')
    reference = _sweep(window, 'crank', 100.0, 1.5, 480, initial=4.0)[2]
    for winding in (1e3, 1e6, 1e9, 1e12, 1e13, 1e14):
        base = winding * 360.0
        trace = _sweep(window, 'crank', base + 100.0, 1.5, 480, initial=4.0)[2]
        deviation = max(math.fabs(x - y) for x, y in zip(reference, trace))
        print(f'  {winding:>9.0e} turns: ulp {math.ulp(base):.2e}  '
              f'max per-tick deviation {deviation:.3e}  final {trace[-1]!r}')


if __name__ == '__main__':
    main()
