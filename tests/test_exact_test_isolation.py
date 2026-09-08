# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Regression proof for exact-cache cleanup owned by test fixtures."""

import os
import tempfile
from unittest import TestCase

import cadquery as cq
import numpy as np

from solid_node.exact import (
    _bounds_cache,
    _placement_cache,
    _shape_cache,
    _shape_keys,
    cached_bounding_box,
    cached_shape,
    placed_shape,
    shape_identity,
    write_brep,
)
from tests.exact_test_support import clear_exact_shape_caches


class ExactCacheFixtureIsolationTest(TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(clear_exact_shape_caches)
        clear_exact_shape_caches()

    def test_historical_shape_only_fixture_cleanup_leaves_no_orphans(self):
        """A retained shape reset must drop every side registry too.

        The three affected fixtures formerly called only ``_shape_cache.clear``.
        A shape kept by a test after that cleanup must be classified as raw,
        not retain a stale file identity through an id-keyed side registry.
        """
        path = os.path.join(self.directory.name, 'fixture-shape.brep')
        write_brep(cq.Workplane('XY').box(2, 2, 2).val(), path, 1 * 10 ** 9)
        shape = cached_shape(path)
        cached_bounding_box(shape)
        placed_shape(shape, np.eye(4))

        clear_exact_shape_caches()

        self.assertEqual(_shape_keys, {})
        self.assertEqual(_bounds_cache, {})
        self.assertEqual(_placement_cache, {})
        self.assertIsNone(shape_identity(shape))
        first = placed_shape(shape, np.eye(4))
        second = placed_shape(shape, np.eye(4))
        self.assertIsNot(first, second)
        self.assertEqual(_placement_cache, {})
