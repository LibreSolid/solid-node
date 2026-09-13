# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The two facts design section 8 is written against, at the cycle's base.

Run from the framework worktree root:

    PYTHONPATH="$PWD" python \
        openspec/changes/publish-the-mechanical-program/evidence/probe_ownership.py
"""

from solid_node.motion.ports import get_coordinate, run_owned
from solid_node.simulation import Sim
from solid_node.simulation.program import qualified_coordinates

from tests.running_project.machine import Train


def two_sims():
    """A second `Sim` over one tree is refused as doubly bound."""
    node = Train()
    first = Sim(node, 1 / 60)
    first.move('crank', by=20.0, duration=0.5)
    for _ in range(30):
        first._run.advance()
    print('first sim after 30 ticks:',
          {key: round(value, 3) for key, value in first.state.items()})
    try:
        Sim(node, 1 / 60)
    except Exception as failure:
        print(f'SECOND Sim REFUSED ({type(failure).__name__}): {failure}')
    else:
        print('SECOND Sim ACCEPTED -- the defect is gone')
    return node, first


def released(node, first):
    """...and the release design section 8.1 proposes makes it fresh."""
    node.__dict__.pop('_run_binder', None)
    for identifier, (owner, name) in qualified_coordinates(node).items():
        slot = get_coordinate(owner, name)
        if run_owned(slot):
            slot._value = None
            slot.binder = None
            slot._enum_marker = None
    second = Sim(node, 1 / 60)
    print('second sim after the release:',
          {key: round(value, 3) for key, value in second.state.items()})
    print('equals the first run\'s initial bank:',
          second.state == dict(first.initial.bank))


def hand_bound_coordinate():
    """A coordinate bound by hand, with no run, is silently overwritten."""
    node = Train()
    node.set_state(crank=0.0, lever=100.0, time=0.0)
    before = get_coordinate(node.first, 'turn')._value
    node.set_state(**{'first.turn': 99.0})
    after = get_coordinate(node.first, 'turn')._value
    print(f'first.turn at rest {before!r}; after set_state(first.turn=99.0) '
          f'{after!r} -- no error raised')


if __name__ == '__main__':
    node, first = two_sims()
    released(node, first)
    hand_bound_coordinate()
