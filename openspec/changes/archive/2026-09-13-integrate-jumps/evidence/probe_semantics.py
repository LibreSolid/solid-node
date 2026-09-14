# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Task 0.4: the two semantics design.md section 1's branch table is
written against, read off `GraphValue.evaluate` itself.

`%` must be `math.fmod` -- `a - b * trunc(a / b)`, the sign of the
DIVIDEND -- and a comparison must evaluate to a Python `bool` that
arithmetic reads as 1/0. Run from the worktree:

    PYTHONPATH="$PWD" python openspec/changes/integrate-jumps/evidence/probe_semantics.py
"""

import math

from solid_node.scad_expression import as_node, GraphValue, symbol

a, b = symbol('a'), symbol('b')

print('%% is math.fmod -- the sign of the DIVIDEND:')
for av, bv in ((7.0, 3.0), (-7.0, 3.0), (7.0, -3.0), (-7.0, -3.0),
               (0.5, 1.0), (-0.5, 1.0)):
    got = GraphValue(as_node(a % b)).evaluate({'a': av, 'b': bv})
    print(f'  {av:>5} % {bv:>5} = {got!r}   fmod {math.fmod(av, bv)!r}   '
          f"python's %% {av % bv!r}   equal to fmod: {got == math.fmod(av, bv)}")

print('trunc is 0 on the whole of (-1, 1), so a %% b is CONTINUOUS at zero')
print('  and jumps only at a NONZERO integer of a / b:')
for av in (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5):
    print(f'  {av:>5} % 1.0 = '
          f'{GraphValue(as_node(a % b)).evaluate({"a": av, "b": 1.0})!r}')

print('a comparison evaluates to a Python bool:')
for expression, text in ((a > b, 'a > b'), (a <= b, 'a <= b'),
                         (a == b, 'a == b'), (a != b, 'a != b')):
    value = GraphValue(as_node(expression)).evaluate({'a': 1.0, 'b': 0.5})
    print(f'  {text} at a=1.0 b=0.5 -> {value!r} ({type(value).__name__})')

gated = GraphValue(as_node(-2 * a * (b > 0.5)))
print('and arithmetic reads that bool as 1/0:')
for bv in (0.0, 1.0):
    print(f'  -2 * a * (b > 0.5) at a=10.0 b={bv} -> '
          f'{gated.evaluate({"a": 10.0, "b": bv})!r}')
