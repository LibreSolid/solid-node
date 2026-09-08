# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Request-local source metadata sharing and its freshness boundaries."""

import os
import tempfile
from unittest import TestCase, mock

from solid_node import currency
from solid_node.source_generation import (
    SourceCensus, SourceChanged, SourceGeneration, current_phase,
)


class SourceCensusTest(TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name
        self.one = self.write('one.py', b'ONE = 1\n')
        self.two = self.write('two.py', b'TWO = 2\n')

    def write(self, name, content):
        path = os.path.join(self.root, name)
        with open(path, 'wb') as source:
            source.write(content)
        return path

    def test_overlapping_closures_observe_each_distinct_path_once(self):
        import solid_node.source_generation as source_generation

        observed = []
        resolved = []
        original = source_generation._observe_real_path
        original_realpath = os.path.realpath

        def counting(path):
            observed.append(path)
            return original(path)

        def counting_realpath(path, *args, **kwargs):
            resolved.append(os.path.abspath(os.fspath(path)))
            return original_realpath(path, *args, **kwargs)

        with mock.patch.object(source_generation, '_observe_real_path',
                               side_effect=counting), \
             mock.patch('os.path.realpath', side_effect=counting_realpath):
            census = SourceCensus(self.root)
            census.include([self.one, self.two])
            first = currency.source_fingerprint(
                [self.one, self.two], self.root, census=census)
            second = currency.source_fingerprint(
                [self.two, self.one, self.one], self.root, census=census)
            first_digest = currency.source_digest(
                [self.one, self.two], self.root, census=census)
            second_digest = currency.source_digest(
                [self.two, self.one, self.one], self.root, census=census)

        self.assertEqual(first, second)
        self.assertEqual(first_digest, second_digest)
        self.assertEqual(observed.count(original_realpath(self.one)), 1)
        self.assertEqual(observed.count(original_realpath(self.two)), 1)
        self.assertEqual(resolved.count(os.path.abspath(self.one)), 1)
        self.assertEqual(resolved.count(os.path.abspath(self.two)), 1)
        self.assertEqual(resolved.count(os.path.abspath(self.root)), 1)

    def test_digest_streams_without_retaining_foreign_source_bytes(self):
        binary = self.write('mesh.stl', b'x' * 1024 * 1024)
        census = SourceCensus(self.root)

        census.digest(binary)

        self.assertNotIn(os.path.realpath(binary), census._bytes)

    def test_failed_phase_entry_restores_context(self):
        missing = os.path.join(self.root, 'missing.py')
        with SourceGeneration(self.root) as generation:
            with self.assertRaises(FileNotFoundError):
                with generation.phase([missing], label='assembly'):
                    pass
            self.assertIsNone(current_phase())

    def test_repeated_phase_includes_remember_only_new_identities(self):
        with SourceGeneration(self.root) as generation:
            with generation.phase([], label='assembly') as phase, \
                 mock.patch.object(
                     generation, '_remember_observation',
                     wraps=generation._remember_observation) as remember:
                phase.include([self.one, self.two])
                for _ in range(100):
                    phase.include([self.two, self.one, self.one])

        self.assertEqual(remember.call_count, 2)

    def test_digest_later_census_observes_changed_metadata_afresh(self):
        before = SourceCensus(self.root)
        before.include([self.one])
        old = before[self.one]

        replacement = os.path.join(self.root, '.one.py')
        with open(replacement, 'wb') as source:
            source.write(b'ONE = 9\n')
        os.replace(replacement, self.one)

        after = SourceCensus(self.root)
        after.include([self.one])
        self.assertNotEqual(after[self.one], old)
        with self.assertRaises(SourceChanged):
            before.check_current(label='next_boundary')

    def test_digest_and_fingerprint_match_uncached_results(self):
        files = [self.one, self.two]
        uncached_fingerprint = currency.source_fingerprint(files, self.root)
        uncached_digest = currency.source_digest(files, self.root)

        census = SourceCensus(self.root)
        census.include(files)

        self.assertEqual(
            currency.source_fingerprint(files, self.root, census=census),
            uncached_fingerprint)
        self.assertEqual(currency.source_digest(
            files, self.root, census=census), uncached_digest)

    def test_missing_contributor_never_certifies_current(self):
        census = SourceCensus(self.root)
        census.include([self.one])
        os.remove(self.one)

        with self.assertRaises(SourceChanged):
            census.check_current(label='publication')
