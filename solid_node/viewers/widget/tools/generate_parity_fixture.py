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

It also carries the FLEXIBLE BINDING seam. A flexible part's geometry
reaches the browser as a spec plus one expression per shape parameter,
so between the two molejo evaluators sits a boundary this repository
owns: the expression is evaluated client-side and its value handed to
molejo-js, where the producer evaluated the same expression in Python
and handed its value to molejo-python. Vertex-for-vertex agreement
between the two evaluators is molejo's own parity contract, tested in
molejo's fixtures; what is pinned here is the binding in front of it,
on the real spring of `tests/flexible_project/spring.py`, at several
driver settings. Counts and topology are stored once rather than per
case, exactly as molejo's own fixtures store them: the claim under test
is that they never follow a parameter, and the format should not be
able to express its violation.

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
from solid_node.simulation.enumeration import (  # noqa: E402
    bind_declared_defaults,
)

from tests.flexible_project import spring as flexible_fixture  # noqa: E402

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

#: Valve lifts, in the driver's native millimetres: the spring at rest,
#: two intermediate settings and the declared extreme of its travel.
LIFTS = [0.0, 3.75, 6.0, 12.0]

#: How many of the spring's vertices the fixture pins, spread over the
#: whole array so a drift anywhere in the sweep is seen: the first ring,
#: quarter, half and three-quarter points, and the two cap centres,
#: which are the last two vertices molejo writes.
def sentinels(count):
    chosen = {0, 1, count // 4, count // 2, (3 * count) // 4,
              count - 2, count - 1}
    return sorted(chosen)


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


def find(node, name):
    """The first node called `name` in a serialized tree."""
    if node['name'] == name:
        return node
    for child in node.get('children', ()):
        found = find(child, name)
        if found is not None:
            return found
    return None


def flexible_spring(lift=None):
    """The fixture's engine, serialized at one binding.

    A fresh tree per binding, like the numeric expression walk above:
    what is read back is a render result, never a value recomputed a
    second way.
    """
    engine = flexible_fixture.Engine()
    bind_declared_defaults(engine)
    if lift is not None:
        engine.set_state(**{'valvetrain.lift': lift})
    return engine


def flexible_binding():
    """The spring's spec, its parameter expressions, and one case per
    lift: the value the producer bound, and what molejo-python made of
    the spec at that value."""
    engine = flexible_spring()
    with symbolic_document(engine) as (declarations, _):
        symbolic = find(serialize_node(engine, lambda rigid: rigid.name),
                        'spring')['flexible']

    shape = flexible_fixture.Spring().render()
    counts = None
    cases = []
    for lift in LIFTS:
        published = find(
            serialize_node(flexible_spring(lift), lambda rigid: rigid.name),
            'spring')['flexible']['params']
        values = {name: float(text) for name, text in published.items()}
        mesh = shape.evaluate(**values)
        vertices = mesh.vertices
        if counts is None:
            counts = (len(vertices), len(mesh.faces))
            indices = sentinels(counts[0])
        elif (len(vertices), len(mesh.faces)) != counts:
            raise SystemExit(
                'the spring changed vertex or face count between bindings; '
                'the declared tessellation this whole path rests on is not '
                'holding, and a fixture pinning it would be a lie')
        cases.append({
            'name': f'lift {lift:g} mm',
            'scope': {'time': 0.0, 'drivers': {'valvetrain': {'lift': lift}}},
            'params': values,
            'vertices': [[float(axis) for axis in vertices[index]]
                         for index in indices],
            'bbox': {
                'min': [float(axis) for axis in vertices.min(axis=0)],
                'max': [float(axis) for axis in vertices.max(axis=0)],
            },
        })

    return {
        'corpus': 'tests/flexible_project/spring.py',
        'node': 'spring',
        'tech': symbolic['tech'],
        'spec': symbolic['spec'],
        'expressions': symbolic['params'],
        'drivers': drivers_table(declarations),
        # The binding is float64 on both sides of the seam, so it is held
        # to the expression corpus's own bound. The GEOMETRY is compared
        # against a Float32Array, so it takes molejo's declared
        # JavaScript coordinate tolerance, applied by molejo's formula
        # (fixtures/README.md): |actual - expected| <= tol * (1 + |expected|).
        'tolerance': {'binding': 1e-9, 'js': 1e-6},
        # Once, not per case: the counts and the numbering follow the
        # DOCUMENT alone, and a format that could vary them per binding
        # would be able to express the very thing under test.
        'vertex_count': counts[0],
        'triangle_count': counts[1],
        'sentinels': indices,
        'cases': cases,
    }


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
        'flexible': flexible_binding(),
    }


def main():
    fixture = build()
    path = os.path.abspath(FIXTURE)
    with open(path, 'w') as handle:
        json.dump(fixture, handle, indent=2)
        handle.write('\n')
    powers = sum(1 for case in fixture['cases'] if '^' in case['expression'])
    flexible = fixture['flexible']
    print(f'{path}: {len(fixture["cases"])} expression cases '
          f'({powers} containing `^`), '
          f'{len(fixture["conversions"])} conversions, '
          f'{len(flexible["cases"])} flexible bindings of '
          f'{flexible["vertex_count"]} vertices '
          f'({len(flexible["sentinels"])} pinned)')


if __name__ == '__main__':
    main()
