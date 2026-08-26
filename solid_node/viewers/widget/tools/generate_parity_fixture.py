# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Regenerate the widget evaluator's cross-runtime parity fixture.

ADR-022 records one `$t` semantics -- OpenSCAD's degree conventions,
with `^` as power -- reimplemented in several runtimes that must agree
function for function, and recorded that NOTHING enforced their
agreement. The expression spike measured the agreement at 2.5e-14 but
had to hand-copy the widget evaluator into JavaScript to do it, leaving
seam 7 open (spike/expressions/FINDINGS.md). This closes it from the
producer's side: the numbers below come from the framework's own
render, and `parity-fixture.test.ts` compares them against the SHIPPED
`evaluator.ts` module.

How the expected values are produced is the whole point. The same tree
is serialized twice:

  * bound to a numeric snapshot, so every operation holds the number
    Python computed through `solid_node.math` and solid2; and
  * in symbolic driver mode with symbolic animation time, so every
    operation holds the wire expression the document publishes.

The two walks have identical structure, so zipping them pairs each
expression with the producer's own value for it. Nothing here evaluates
an expression a second way -- an expected value is a render result, not
a reimplementation, which is what makes disagreement mean the client
drifted.

The corpus is the spike's two-axis machine
(`spike/expressions/machine_model.py`), whose `render()` deliberately
builds the five shapes ADR-022 is about: linear in a driver, a driver
through a port scale, a degree-trig chain, a `^` term, and one formula
mixing `$t` with a driver. The snapshots are the spike's, verbatim.

Beside the expressions the fixture carries design-to-native
conversions, because an instruction's target crosses the same boundary
and `Driver.native` is the one arithmetic the client must reproduce --
including Python's round-half-to-even on integer dtypes.

Run from the framework worktree root:

    PYTHONPATH="$PWD" python \\
        solid_node/viewers/widget/tools/generate_parity_fixture.py

The generated JSON is committed, so the TypeScript suite runs with no
Python and no CAD stack.
"""

import json
import os
import sys

ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 '..', '..', '..', '..'))
SPIKE = os.path.join(ROOT, 'spike', 'expressions')
FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'src', 'parity-fixture.json')

sys.path.insert(0, ROOT)
sys.path.insert(0, SPIKE)

from solid_node.core.serializer import (  # noqa: E402
    drivers_table, serialize_node, symbolic_document,
)
from solid_node.simulation.driver import Driver  # noqa: E402

from machine_model import Machine  # noqa: E402


# The spike's snapshots, verbatim: driver values in NATIVE units plus
# the animation instant, chosen to cover home, mid-travel, the declared
# extremes and a value below zero.
SNAPSHOTS = [
    {'x_axis.motor': 0,    'y_axis.motor': 8000, 'time': 0.0},
    {'x_axis.motor': 1234, 'y_axis.motor': 6543, 'time': 0.125},
    {'x_axis.motor': 4000, 'y_axis.motor': 400,  'time': 0.25},
    {'x_axis.motor': 8000, 'y_axis.motor': 3200, 'time': 0.37},
    {'x_axis.motor': -400, 'y_axis.motor': 111,  'time': 0.5},
    {'x_axis.motor': 6543, 'y_axis.motor': 1234, 'time': 0.75},
    {'x_axis.motor': 3200, 'y_axis.motor': 8000, 'time': 0.9},
]

# Design-unit targets an instruction might carry, through the axis
# driver's own declaration. The last two sit exactly on a half native
# unit, where Python rounds to even.
CONVERSION_TARGETS = [0.0, 100.0, 12.5, -5.0, 0.01, -0.01, 0.00625, 0.01875]

WHOLE_TARGETS = [0.5, 1.5, 2.5, -0.5, -1.5, 3.4, -3.6]


def scalars(node):
    """Every scalar an operation of `node` holds, keyed by position.

    A rotation holds one angle, a translation three components. The key
    is structural (node path, operation index, slot), so the numeric and
    symbolic walks of the same tree agree on it by construction.
    """
    found = {}

    def visit(data, path):
        for index, operation in enumerate(data['operations']):
            values = ([operation[1]] if operation[0] == 'r'
                      else list(operation[1]))
            for slot, value in enumerate(values):
                found[f'{path}#{index}.{slot}'] = value
        for child in data.get('children', ()):
            visit(child, f'{path}/{child["name"]}')

    visit(node, node['name'])
    return found


def document(node):
    return serialize_node(node, lambda rigid: rigid.name)


def numeric_scalars(snapshot):
    """What the producer computed for `snapshot`: every operation bound
    to numbers, animation time included."""
    machine = Machine()
    machine.set_state(**snapshot)
    return scalars(document(machine))


def symbolic_scalars():
    """What the producer publishes: every operation as its wire
    expression, drivers and `$t` both symbolic."""
    machine = Machine()
    with symbolic_document(machine) as (declarations, _):
        found = scalars(document(machine))
    return found, drivers_table(declarations)


def driver_scope(snapshot):
    """The snapshot as the client holds it: nested, because a qualified
    id is member access to the expression parser."""
    scope = {}
    for key, value in snapshot.items():
        if key == 'time':
            continue
        instance, name = key.rsplit('.', 1)
        scope.setdefault(instance, {})[name] = value
    return scope


def conversions():
    axis = Driver(default=8000, unit='ustep', dtype=int, scale=40.0 / 3200)
    whole = Driver(default=0, unit='step', dtype=int)
    free = Driver(default=0.0, unit='deg', dtype=float)
    published = drivers_table({'scaled': axis, 'whole': whole, 'free': free})
    cases = []
    for name, declaration in (('scaled', axis), ('whole', whole),
                              ('free', free)):
        targets = (CONVERSION_TARGETS if name == 'scaled'
                   else WHOLE_TARGETS)
        for target in targets:
            cases.append({
                'driver': published[name],
                'target': target,
                'native': declaration.native(target),
            })
    return cases


def build():
    symbolic, table = symbolic_scalars()
    cases = []
    for index, snapshot in enumerate(SNAPSHOTS):
        numeric = numeric_scalars(snapshot)
        if set(numeric) != set(symbolic):
            raise SystemExit(
                'the numeric and symbolic walks disagree on structure; '
                'the fixture would pair unrelated operations')
        scope = {'time': snapshot['time'], 'drivers': driver_scope(snapshot)}
        for key in sorted(symbolic):
            cases.append({
                'key': f'{index}|{key}',
                'expression': symbolic[key],
                'scope': scope,
                'expected': float(numeric[key]),
            })
    return {
        'generated_by':
            'solid_node/viewers/widget/tools/generate_parity_fixture.py',
        'corpus': 'spike/expressions/machine_model.py',
        'drivers': table,
        'cases': cases,
        'conversions': conversions(),
    }


def main():
    fixture = build()
    path = os.path.abspath(FIXTURE)
    with open(path, 'w') as handle:
        json.dump(fixture, handle, indent=2)
        handle.write('\n')
    powers = sum(1 for case in fixture['cases'] if '^' in case['expression'])
    print(f'{path}: {len(fixture["cases"])} expression cases '
          f'({powers} containing `^`), '
          f'{len(fixture["conversions"])} conversions')


if __name__ == '__main__':
    main()
