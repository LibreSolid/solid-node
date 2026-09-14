# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Regenerate the running mode's cross-runtime conformance corpus.

ADR-022 recorded one `$t` semantics reimplemented in several runtimes
that must agree function for function, and `generate_parity_fixture.py`
closed that from the producer's side. The RUN is the same shape of
problem one layer up: a published program is executed by the framework's
own run and, from cycle 5, by a worker in the browser, and nothing but a
corpus can say they agree.

So this writes `tests/running-corpus.json` from the framework's OWN run.
Every expected value in it is a value the run PRODUCED -- never one
recomputed a second way -- which is what makes a disagreement mean the
other runtime drifted. The framework's suite replays it
(`tests/test_running_corpus.py`); the viewer commits a copy and replays
it against the worker.

The machines are the fixtures cycles 1 to 3 already built
(`tests/running_project/machine.py`), one per shape the run has to be
answerable for: an affine chain with a kink and a wiring, each jump
primitive, a multi-source law with a gate, the Pascaline-shaped carry, a
ratchet whose bound is an expression over its own coordinate, a stop on
one group while another runs, two stops in one tick, and a fold and a
stop in one tick. Their scripts move, rate, trigger both instruction
forms, and take and restore a snapshot.

`uncovered_features` REFUSES to write a corpus that misses any of the
features the export capability lists, so the corpus's width is a
property of this tool rather than of whoever last edited the machine
list -- and the framework's suite tests that refusal directly, so the
width is visible without running this at all.

Run from the framework worktree root:

    PYTHONPATH="$PWD" python tools/generate_running_corpus.py [OUTPUT]
"""

import json
import os
import sys

ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
FIXTURE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    ROOT, 'tests', 'running-corpus.json')

sys.path.insert(0, ROOT)

from solid_node.core.serializer import (  # noqa: E402
    compiled_program, document_body, drivers_table, instructions_table,
    serialize_node, symbolic_document,
)
from solid_node.simulation import Sim  # noqa: E402
from solid_node.simulation.enumeration import (  # noqa: E402
    bind_declared_defaults,
)
from solid_node.simulation.run import _TOLERANCE  # noqa: E402

from tests.running_project import machine as machines  # noqa: E402


#: The keys of a published document the RUN is answerable for. `root`,
#: `pieces` and `animation` are left out on purpose: the tree and the
#: meshes are what the geometry tests cover, and what the run executes is
#: the program.
DOCUMENT_KEYS = ('format', 'version', 'drivers', 'instructions',
                 'bindings', 'program')

#: Every feature the corpus must exercise, as the export capability lists
#: them. A corpus missing one is refused rather than written.
REQUIRED = (
    'floor', 'ceil', 'sign', '%', 'a comparison',
    'a multi-source law',
    'a stop located inside a tick',
    'a bound stated as an expression',
    'a command retired blocked',
    'a rate',
    'a snapshot',
    'a restore',
    'a relative instruction',
    'an absolute instruction',
    'a tick carrying both a crossing and a stop',
)

COMPARISONS = ('<', '<=', '>', '>=', '==', '!=')


#: One entry per machine: its class name, its step size, how many ticks
#: to run, and the script applied BEFORE the tick each entry names.
CORPUS = (
    # The Curta bench's shape, at two step sizes: an affine chain, a
    # `clamp01` kink, a wiring into a plain port, a rate, both
    # instruction forms, and a snapshot restored a few ticks later.
    {'name': 'Train', 'dt': 0.05, 'steps': 30, 'script': [
        {'tick': 1, 'move': {'input': 'crank', 'by': 20.0,
                             'duration': 0.5}, 'handle': 'h0'},
        {'tick': 2, 'rate': {'input': 'lever', 'rate': 4.0},
         'handle': 'h1'},
        {'tick': 14, 'trigger': 'Advance', 'handles': ['h2']},
        {'tick': 20, 'snapshot': 'a'},
        {'tick': 25, 'restore': 'a'},
    ]},
    {'name': 'Train', 'dt': 0.1, 'steps': 20, 'script': [
        {'tick': 1, 'move': {'input': 'crank', 'to': 40.0,
                             'duration': 0.5}, 'handle': 'h0'},
        {'tick': 9, 'trigger': 'Wind', 'handles': ['h1', 'h2']},
    ]},
    # The pilot's illustration: one `floor` per crank revolution.
    {'name': 'Window', 'dt': 0.05, 'steps': 24, 'script': [
        {'tick': 1, 'move': {'input': 'crank', 'by': 500.0,
                             'duration': 1.0}, 'handle': 'h0'},
    ]},
    # The same window written with `%`.
    {'name': 'Remainder', 'dt': 0.05, 'steps': 24, 'script': [
        {'tick': 1, 'move': {'input': 'crank', 'by': 500.0,
                             'duration': 1.0}, 'handle': 'h0'},
    ]},
    # `wrap`, which is a `ceil`.
    {'name': 'Wrapped', 'dt': 0.05, 'steps': 20, 'script': [
        {'tick': 1, 'move': {'input': 'crank', 'by': 800.0,
                             'duration': 0.8}, 'handle': 'h0'},
    ]},
    # A `sign` that genuinely jumps.
    {'name': 'Throwing', 'dt': 0.05, 'steps': 20, 'script': [
        {'tick': 1, 'move': {'input': 'crank', 'by': 40.0,
                             'duration': 0.8}, 'handle': 'h0'},
    ]},
    # A comparison as a gate factor, over two sources, engaging
    # mid-tick.
    {'name': 'Clutch', 'dt': 0.05, 'steps': 24, 'script': [
        {'tick': 1, 'move': {'input': 'shaft', 'by': 60.0,
                             'duration': 1.0}, 'handle': 'h0'},
        {'tick': 4, 'move': {'input': 'sleeve', 'by': 2.0,
                             'duration': 0.4}, 'handle': 'h1'},
    ]},
    # The Pascaline-shaped carry, multi-source with a `floor` the
    # integration subtracts, at two step sizes.
    {'name': 'CarryLead', 'dt': 0.05, 'steps': 24, 'script': [
        {'tick': 1, 'move': {'input': 'column', 'by': 500.0,
                             'duration': 1.0}, 'handle': 'h0'},
        {'tick': 6, 'move': {'input': 'tens_entry', 'by': 2.0,
                             'duration': 0.4}, 'handle': 'h1'},
    ]},
    {'name': 'CarryLead', 'dt': 0.1, 'steps': 14, 'script': [
        {'tick': 1, 'move': {'input': 'column', 'by': 500.0,
                             'duration': 1.0}, 'handle': 'h0'},
    ]},
    # A bound stated as an expression over the joint's OWN coordinate:
    # reverse is blocked at the last seated tooth.
    {'name': 'Ratchet', 'dt': 0.05, 'steps': 20, 'script': [
        {'tick': 1, 'move': {'input': 'arbor', 'by': 10.0,
                             'duration': 0.2}, 'handle': 'h0'},
        {'tick': 8, 'move': {'input': 'arbor', 'by': -20.0,
                             'duration': 0.4}, 'handle': 'h1'},
    ]},
    # A stop on one group while an unrelated input runs its whole tick,
    # from an instruction that claims both.
    {'name': 'Swept', 'dt': 0.01, 'steps': 16, 'script': [
        {'tick': 1, 'trigger': 'Sweep', 'handles': ['h0', 'h1']},
    ]},
    # Two groups reaching two bounds at two fractions of one tick.
    {'name': 'TwoStops', 'dt': 0.05, 'steps': 12, 'script': [
        {'tick': 1, 'move': {'input': 'lever_in', 'by': 10.0,
                             'duration': 0.25}, 'handle': 'h0'},
        {'tick': 1, 'move': {'input': 'steer', 'by': 20.0,
                             'duration': 0.25}, 'handle': 'h1'},
    ]},
    # A `wrap` fold and a stop in ONE tick: the crossing is located
    # inside the segment before the stop and recorded at its fraction OF
    # THE TICK.
    {'name': 'StopAndJump', 'dt': 0.05, 'steps': 12, 'script': [
        {'tick': 1, 'move': {'input': 'crank', 'by': 30.0,
                             'duration': 0.05}, 'handle': 'h0'},
    ]},
)


def document_of(name):
    """The program-bearing keys of the document `name` publishes."""
    node = getattr(machines, name)()
    bind_declared_defaults(node)
    program, initial = compiled_program(node)
    with symbolic_document(node) as (declarations, instructions):
        root = serialize_node(node, lambda rigid: rigid.name,
                              graph_values=True)
        drivers = drivers_table(declarations)
        events = instructions_table(instructions, running=program is not None)
    body = document_body(node, root, drivers, events, program, initial)
    return {key: body[key] for key in DOCUMENT_KEYS if key in body}


def run_machine(entry):
    """One machine's whole run, tick by tick."""
    sim = Sim(getattr(machines, entry['name'])(), entry['dt'],
              record=entry['steps'] + 1)
    script = {}
    for action in entry['script']:
        script.setdefault(action['tick'], []).append(action)
    handles = {}
    snapshots = {}
    crossings_seen = 0
    stops_seen = 0
    ticks = []
    for step in range(1, entry['steps'] + 1):
        for action in script.get(step, ()):
            apply_action(sim, action, handles, snapshots)
        sim.run(entry['dt'])
        crossings = sim.crossings[crossings_seen:]
        stops = sim.stops[stops_seen:]
        crossings_seen = len(sim.crossings)
        stops_seen = len(sim.stops)
        ticks.append({
            'tick': sim.tick,
            'bank': sim.state,
            'crossings': [{'relation': one.relation,
                           'coordinate': one.coordinate,
                           'primitive': one.primitive,
                           'level': one.level,
                           't': one.t} for one in crossings],
            'stops': [{'coordinate': one.coordinate, 'bound': one.bound,
                       'value': one.value, 't': one.t,
                       'inputs': list(one.inputs)} for one in stops],
            'commands': [{'handle': handle, 'status': command.status,
                          'admitted': command.admitted}
                         for handle, command in handles.items()],
        })
    return ticks


def apply_action(sim, action, handles, snapshots):
    if 'move' in action:
        request = dict(action['move'])
        handles[action['handle']] = sim.move(request.pop('input'), **request)
    elif 'rate' in action:
        handles[action['handle']] = sim.rate(action['rate']['input'],
                                             action['rate']['rate'])
    elif 'trigger' in action:
        issued = sim.trigger(action['trigger'])
        for handle, command in zip(action['handles'], issued):
            handles[handle] = command
    elif 'snapshot' in action:
        snapshots[action['snapshot']] = sim.snapshot()
    elif 'restore' in action:
        sim.restore(snapshots[action['restore']])
    else:
        raise SystemExit(f'unknown script action {action!r}')


def uncovered_features(machines):
    """Every feature of `REQUIRED` no machine in `machines` exercises.

    Mirrors `generate_parity_fixture.uncovered_builtins`: the inventory
    is stated here rather than inferred, so adding a machine cannot
    narrow the corpus by accident and removing one cannot narrow it at
    all -- this refuses to write instead.
    """
    seen = set()
    for entry in machines:
        program = entry['document'].get('program') or {}
        for edge in program.get('edges', ()):
            if edge['kind'] == 'law' and len(edge['needs']) > 1:
                seen.add('a multi-source law')
            for plan in edge.get('plans') or ():
                if plan is None:
                    continue
                for jump in plan['jumps']:
                    primitive = jump['primitive']
                    seen.add('a comparison' if primitive in COMPARISONS
                             else primitive)
        for span in (program.get('spans') or {}).values():
            for side in ('low', 'high'):
                if isinstance(span[side], dict):
                    seen.add('a bound stated as an expression')
        for instruction in entry['document'].get('instructions', {}).values():
            seen.add('an absolute instruction' if 'targets' in instruction
                     else 'a relative instruction')
        for action in entry['script']:
            for key, feature in (('rate', 'a rate'),
                                 ('snapshot', 'a snapshot'),
                                 ('restore', 'a restore')):
                if key in action:
                    seen.add(feature)
        for tick in entry['ticks']:
            if tick['stops']:
                seen.add('a stop located inside a tick')
            if tick['stops'] and tick['crossings']:
                seen.add('a tick carrying both a crossing and a stop')
            for command in tick['commands']:
                if command['status'] == 'blocked':
                    seen.add('a command retired blocked')
    return [feature for feature in REQUIRED if feature not in seen]


def build():
    documents = {}
    found = []
    for entry in CORPUS:
        name = entry['name']
        if name not in documents:
            documents[name] = document_of(name)
        found.append({
            'name': name,
            'dt': entry['dt'],
            'steps': entry['steps'],
            'document': documents[name],
            'script': entry['script'],
            'ticks': run_machine(entry),
        })
    missing = uncovered_features(found)
    if missing:
        raise SystemExit(
            f'the corpus exercises neither {", nor ".join(missing)}, so it '
            f'would pin a run narrower than the one this framework can '
            f'execute; add a machine to CORPUS that does')
    return {
        'generated_by': 'tools/generate_running_corpus.py',
        'corpus': 'tests/running_project/machine.py',
        'tolerance': {'float': _TOLERANCE},
        'machines': found,
    }


def main():
    fixture = build()
    path = os.path.abspath(FIXTURE)
    with open(path, 'w') as handle:
        json.dump(fixture, handle, indent=2)
        handle.write('\n')
    ticks = sum(len(entry['ticks']) for entry in fixture['machines'])
    names = sorted({entry['name'] for entry in fixture['machines']})
    print(f'{path}: {len(fixture["machines"])} scenarios over '
          f'{len(names)} machines ({", ".join(names)}), {ticks} ticks, '
          f'{os.path.getsize(path)} bytes')


if __name__ == '__main__':
    main()
