# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The conformance corpus: what pins the two runtimes to each other.

ADR-022's pattern, repeated for the run. `tests/running-corpus.json` is
written by `tools/generate_running_corpus.py` from the framework's OWN
run, so every expected value in it is a value the producer PRODUCED and
never one recomputed a second way -- which is what makes a disagreement
mean the consumer drifted. The framework replays it here; the browser
worker replays the same file in `solid-node-viewer` (cycle 5).

Agreement is EXACT for discrete state -- tick numbers, statuses, every
coordinate, relation, primitive, bound side and input name, every list
ORDER and a crossing's surface level -- and within `1e-9` RELATIVE for
floats, which is `run.py`'s own `_TOLERANCE`: the window inside which
the run itself declines to distinguish two increments.
"""

import json
import os
from unittest import TestCase

from solid_node.simulation import Sim

from .base import BaseNodeTest

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'running-corpus.json')


def corpus():
    with open(CORPUS) as handle:
        return json.load(handle)


def machine_class(name):
    from .running_project import machine as module

    return getattr(module, name)


class CorpusReplayTest(BaseNodeTest):
    """(5.1) The framework reproduces its own corpus, tick by tick."""

    def setUp(self):
        super().setUp()
        self.corpus = corpus()
        self.tolerance = self.corpus['tolerance']['float']

    def close(self, left, right, where):
        window = self.tolerance * max(1.0, abs(left), abs(right))
        self.assertLessEqual(abs(left - right), window, where)

    def replay(self, entry):
        """Construct, script and step one machine exactly as the
        generator did, and compare every tick."""
        sim = Sim(machine_class(entry['name'])(), entry['dt'],
                  record=len(entry['ticks']) + 1)
        script = {}
        for action in entry['script']:
            script.setdefault(action['tick'], []).append(action)
        handles = {}
        snapshots = {}
        crossings_seen = 0
        stops_seen = 0
        for step, expected in enumerate(entry['ticks'], 1):
            # A script entry is applied BEFORE the step it names, in
            # array order. The STEP is the position in the run, not the
            # tick: a restore takes the clock backwards, and what the
            # fixture lists is every step the run took.
            for action in script.get(step, ()):
                self.apply(sim, action, handles, snapshots)
            sim.run(entry['dt'])
            crossings = sim.crossings[crossings_seen:]
            stops = sim.stops[stops_seen:]
            crossings_seen = len(sim.crossings)
            stops_seen = len(sim.stops)
            self.compare(entry['name'], expected, sim, handles,
                         crossings, stops)

    def apply(self, sim, action, handles, snapshots):
        if 'move' in action:
            request = dict(action['move'])
            input_id = request.pop('input')
            handles[action['handle']] = sim.move(input_id, **request)
        elif 'rate' in action:
            request = dict(action['rate'])
            handles[action['handle']] = sim.rate(request['input'],
                                                 request['rate'])
        elif 'trigger' in action:
            issued = sim.trigger(action['trigger'])
            for handle, command in zip(action['handles'], issued):
                handles[handle] = command
        elif 'snapshot' in action:
            snapshots[action['snapshot']] = sim.snapshot()
        elif 'restore' in action:
            sim.restore(snapshots[action['restore']])
        else:
            self.fail(f'unknown script action {action!r}')

    def compare(self, name, expected, sim, handles, crossings, stops):
        where = f'{name} tick {expected["tick"]}'
        self.assertEqual(sim.tick, expected['tick'], where)
        bank = sim.state
        self.assertEqual(sorted(bank), sorted(expected['bank']), where)
        for coordinate, value in expected['bank'].items():
            self.close(bank[coordinate], value, f'{where} {coordinate}')

        self.assertEqual(len(crossings), len(expected['crossings']), where)
        for found, want in zip(crossings, expected['crossings']):
            self.assertEqual(found.relation, want['relation'], where)
            self.assertEqual(found.coordinate, want['coordinate'], where)
            self.assertEqual(found.primitive, want['primitive'], where)
            self.assertEqual(found.level, want['level'], where)
            self.close(found.t, want['t'], f'{where} crossing t')

        self.assertEqual(len(stops), len(expected['stops']), where)
        for found, want in zip(stops, expected['stops']):
            self.assertEqual(found.coordinate, want['coordinate'], where)
            self.assertEqual(found.bound, want['bound'], where)
            self.assertEqual(list(found.inputs), want['inputs'], where)
            self.close(found.value, want['value'], f'{where} stop value')
            self.close(found.t, want['t'], f'{where} stop t')

        self.assertEqual([entry['handle'] for entry in expected['commands']],
                         [handle for handle in handles], where)
        for entry in expected['commands']:
            command = handles[entry['handle']]
            self.assertEqual(command.status, entry['status'],
                             f'{where} {entry["handle"]}')
            self.close(command.admitted, entry['admitted'],
                       f'{where} {entry["handle"]} admitted')

    def test_the_framework_reproduces_its_own_corpus(self):
        for entry in self.corpus['machines']:
            with self.subTest(machine=entry['name'], dt=entry['dt']):
                self.replay(entry)

    def test_every_step_is_present(self):
        """Not a sample: every step the run took is listed, oldest first.

        A divergence that heals between two samples is a divergence, so
        the fixture may never SKIP FORWARD. It may go backwards, at a
        step whose script restores a snapshot -- that is the clock being
        put back, not a tick going unrecorded.
        """
        for entry in self.corpus['machines']:
            with self.subTest(machine=entry['name'], dt=entry['dt']):
                self.assertEqual(len(entry['ticks']), entry['steps'])
                restored = {action['tick'] for action in entry['script']
                            if 'restore' in action}
                previous = 0
                for step, item in enumerate(entry['ticks'], 1):
                    if step in restored:
                        previous = item['tick']
                        continue
                    self.assertEqual(item['tick'], previous + 1,
                                     f'{entry["name"]} step {step}')
                    previous = item['tick']


class CorpusDocumentTest(BaseNodeTest):
    """(5.2) The fixture carries the document it was run against, so it
    cannot drift from the producer it claims to come from."""

    def test_each_machines_real_document_reproduces_the_fixtures(self):
        from .test_running_document import document
        from solid_node.simulation.enumeration import bind_declared_defaults

        for entry in corpus()['machines']:
            with self.subTest(machine=entry['name'], dt=entry['dt']):
                node = machine_class(entry['name'])()
                bind_declared_defaults(node)
                published = document(node)
                for key in ('format', 'version', 'drivers', 'instructions',
                            'bindings', 'program'):
                    self.assertEqual(published.get(key),
                                     entry['document'].get(key), key)


class CoverageGuardTest(TestCase):
    """(5.3) The corpus's width is visible without running the
    generator: the guard is under direct test."""

    def test_the_committed_corpus_covers_every_stated_feature(self):
        from tools.generate_running_corpus import uncovered_features

        self.assertEqual(uncovered_features(corpus()['machines']), [])

    def test_a_corpus_with_no_remainder_law_is_refused(self):
        from tools.generate_running_corpus import uncovered_features

        machines = [entry for entry in corpus()['machines']
                    if entry['name'] != 'Remainder']
        missing = uncovered_features(machines)
        self.assertIn('%', missing)

    def test_a_corpus_with_no_rate_is_refused(self):
        from tools.generate_running_corpus import uncovered_features

        machines = []
        for entry in corpus()['machines']:
            copy = dict(entry)
            copy['script'] = [action for action in entry['script']
                              if 'rate' not in action]
            machines.append(copy)
        self.assertIn('a rate', uncovered_features(machines))
