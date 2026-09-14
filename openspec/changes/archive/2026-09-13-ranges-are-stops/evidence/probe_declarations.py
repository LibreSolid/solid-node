# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Task 0.4: the three facts design.md sections 8 and 9 are written
against, read off the UNCHANGED tree.

1. `Joint._span` today REJECTS `None` as a bound and EVALUATES a
   callable bound (so both forms of section 9 are new);
2. `RampProgram` with a NEGATIVE delta lands exactly on its target at
   `k == ticks`, for both dtypes, and stays monotone in between;
3. `solid_node.math.floor` applied to a float returns a number, and
   applied to `symbol('turn')` builds a `floor` CALL NODE -- which is
   what lets a bound be compiled exactly as a law is.

Run from the worktree:

    PYTHONPATH="$PWD" python \
        openspec/changes/ranges-are-stops/evidence/probe_declarations.py
"""

from solid_node.math import floor
from solid_node.motion.joints import Revolute
from solid_node.node import AssemblyNode
from solid_node.scad_expression import as_node, symbol
from solid_node.simulation.driver import RampProgram


print('1. Joint._span on the unchanged tree')
for label, declared in (('range=(0, None)', (0, None)),
                        ('range=(None, 50.0)', (None, 50.0)),
                        ('range=(lambda turn: 36 * floor(turn / 36), None)',
                         (lambda turn: 36 * floor(turn / 36), None))):
    class Probe(AssemblyNode):
        turn = Revolute(axis=(1, 0, 0), range=declared, unit='deg')

    try:
        node = Probe()
        span = type(node).__dict__['turn'].arguments(node)[2]
        print(f'   {label:52s} -> {span!r}')
    except Exception as failure:
        print(f'   {label:52s} -> {type(failure).__name__}: {failure}')

# And the form that is NOT new: a callable given as the WHOLE range,
# called with the realized declarer and returning numbers.
class WholeRange(AssemblyNode):
    turn = Revolute(axis=(1, 0, 0), range=lambda node: (-90, 90), unit='deg')


whole = WholeRange()
print(f'   range=lambda node: (-90, 90)  (the NODE form, unchanged)   -> '
      f'{type(whole).__dict__["turn"].arguments(whole)[2]!r}')

print()
print('2. RampProgram over a NEGATIVE delta')
for dtype in (float, int):
    ramp = RampProgram(0, -10, 4, dtype)
    values = [ramp.value_at(k) for k in range(5)]
    print(f'   dtype={dtype.__name__:5s} 0 -> -10 over 4 ticks: {values}')
    assert values[-1] == -10
ramp = RampProgram(0, 10, 4, int)
print(f'   dtype=int   0 ->  10 over 4 ticks: '
      f'{[ramp.value_at(k) for k in range(5)]}')

print()
print('3. solid_node.math.floor')
print(f'   floor(40 / 36)                = {floor(40 / 36)!r} '
      f'({type(floor(40 / 36)).__name__})')
built = floor(symbol('turn') / 36)
node = as_node(built)
print(f'   floor(symbol("turn") / 36)    = {built} '
      f'-> node kind={node.kind!r} op={node.op!r}')
bound = 36 * floor(symbol('turn') / 36)
print(f'   36 * floor(symbol("turn")/36) = {bound}')
