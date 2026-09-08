# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Bounded exact-placement retention (P07)."""

import os
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import cadquery as cq
import numpy as np

import solid_node.exact as exact
from solid_node.manager import test as manager_test
import solid_node.test as test_module


class ExactPlacementCacheTest(TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        for cache in (exact._shape_cache, exact._shape_keys,
                      exact._bounds_cache, exact._placement_cache):
            cache.clear()
            self.addCleanup(cache.clear)

    def shape(self, name='shape', size=2):
        path = os.path.join(self.directory.name, f'{name}.brep')
        exact.write_brep(cq.Workplane('XY').box(size, size, size).val(),
                         path, 1 * 10 ** 9)
        return path, exact.cached_shape(path)

    @staticmethod
    def matrix(x=0.0):
        matrix = np.eye(4)
        matrix[0, 3] = x
        return matrix

    def test_unique_trajectory_is_bounded_at_the_configured_internal_limit(self):
        _, shape = self.shape()

        # `create=True` makes this exercise the legacy plain-dict seam too:
        # before WP8 the injected limit was ignored and ten entries remained.
        with patch.object(exact, '_PLACEMENT_CACHE_LIMIT', 3, create=True):
            for offset in range(10):
                exact.placed_shape(shape, self.matrix(offset))
                self.assertLessEqual(len(exact._placement_cache), 3)

        self.assertEqual(len(exact._placement_cache), 3)

    def test_hits_refresh_access_order_and_the_least_recent_entry_is_evicted(self):
        _, shape = self.shape()
        first, second, third = (self.matrix(offset)
                                for offset in (1, 2, 3))

        with patch.object(exact, '_PLACEMENT_CACHE_LIMIT', 2, create=True), \
                patch.object(exact, '_place', wraps=exact._place) as place:
            exact.placed_shape(shape, first)
            exact.placed_shape(shape, second)
            exact.placed_shape(shape, first)
            exact.placed_shape(shape, third)
            exact.placed_shape(shape, second)

        self.assertEqual(place.call_count, 4)
        self.assertEqual(len(exact._placement_cache), 2)

    def test_exact_matrix_bytes_distinguish_signed_zero(self):
        _, shape = self.shape()
        positive = self.matrix()
        negative = self.matrix()
        negative[0, 1] = -0.0

        with patch.object(exact, '_place', wraps=exact._place) as place:
            exact.placed_shape(shape, positive)
            exact.placed_shape(shape, negative)

        self.assertEqual(place.call_count, 2)
        self.assertEqual(len(exact._placement_cache), 2)

    def test_an_unstable_shape_is_never_retained(self):
        shape = cq.Workplane('XY').box(2, 2, 2).val()

        with patch.object(exact, '_place', wraps=exact._place) as place:
            exact.placed_shape(shape, self.matrix())
            exact.placed_shape(shape, self.matrix())

        self.assertEqual(place.call_count, 2)
        self.assertEqual(len(exact._placement_cache), 0)

    def test_rebuild_eagerly_evicts_old_placements_and_bounds(self):
        path, shape = self.shape('rebuilt', size=1)
        exact.placed_shape(shape, self.matrix(1))
        exact.cached_bounding_box(shape)

        exact.write_brep(cq.Workplane('XY').box(2, 2, 2).val(), path,
                         2 * 10 ** 9)
        rebuilt = exact.cached_shape(path)

        self.assertEqual(
            {key[0] for key in exact._placement_cache if key[0][0] == path},
            set())
        self.assertEqual(
            [key for key in exact._bounds_cache if key[0] == path], [])
        self.assertAlmostEqual(exact.placed_shape(rebuilt, self.matrix(1))
                               .Volume(), 8.0)

    def test_an_evicted_shape_held_by_a_caller_is_recomputed(self):
        _, shape = self.shape()
        first, second = self.matrix(1), self.matrix(2)

        with patch.object(exact, '_PLACEMENT_CACHE_LIMIT', 1, create=True), \
                patch.object(exact, '_place', wraps=exact._place) as place:
            retained_by_caller = exact.placed_shape(shape, first)
            exact.placed_shape(shape, second)
            recomputed = exact.placed_shape(shape, first)

        self.assertIsNot(retained_by_caller, recomputed)
        self.assertEqual(place.call_count, 3)
        self.assertAlmostEqual(recomputed.Volume(), retained_by_caller.Volume())

    def test_cached_evicted_and_uncached_occt_placements_keep_boolean_verdicts(self):
        _, cached_shape = self.shape('cached')
        raw_shape = cq.Workplane('XY').box(2, 2, 2).val()
        other = cq.Workplane('XY').box(2, 2, 2).val()
        matrix = self.matrix(0.5)

        cached = exact.placed_shape(cached_shape, matrix)
        cached_again = exact.placed_shape(cached_shape, matrix)
        uncached = exact.placed_shape(raw_shape, matrix)
        with patch.object(exact, '_PLACEMENT_CACHE_LIMIT', 1, create=True):
            exact.placed_shape(cached_shape, self.matrix(4))
            recomputed = exact.placed_shape(cached_shape, matrix)

        def verdict(shape):
            common = exact.intersect_shapes(shape, other, 'left', 'right')
            return exact.solid_count(common), exact.solid_volume(common)

        self.assertIs(cached, cached_again)
        self.assertIsNot(cached, recomputed)
        self.assertEqual(verdict(cached), verdict(uncached))
        self.assertEqual(verdict(cached), verdict(recomputed))

    def test_a_useful_working_set_hits_after_warmup(self):
        _, shape = self.shape()
        matrices = [self.matrix(offset) for offset in (1, 2, 3)]

        with patch.object(exact, '_PLACEMENT_CACHE_LIMIT', 3, create=True), \
                patch.object(exact, '_place', wraps=exact._place) as place:
            for _ in range(4):
                for matrix in matrices:
                    exact.placed_shape(shape, matrix)

        self.assertEqual(place.call_count, 3)

    def test_direct_isolation_reset_clears_placements(self):
        _, shape = self.shape()
        exact.placed_shape(shape, self.matrix())

        exact._reset_placement_cache()

        self.assertEqual(len(exact._placement_cache), 0)


class ManagedPlacementCacheResetTest(TestCase):

    def tearDown(self):
        test_module.set_comparison_policy(None)

    def test_new_managed_run_resets_exact_placement_retention(self):
        arguments = SimpleNamespace(kernel=None, volume_epsilon=None,
                                    failfast=False, set=None, all=False,
                                    path=None)

        with patch('solid_node.exact._reset_placement_cache') as reset, \
                patch('solid_node.manager.test.select_model',
                      side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                manager_test.Test().handle(arguments)

        reset.assert_called_once_with()
