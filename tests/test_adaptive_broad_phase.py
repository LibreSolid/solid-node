# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Adaptive broad-phase characterization for P05 (WP6)."""

import itertools
import random
from unittest import TestCase
from unittest.mock import patch

import numpy as np

import solid_node.test as test_module


def bounds(x0, x1, y0, y1, z0, z1):
    return (np.array([x0, y0, z0], float),
            np.array([x1, y1, z1], float))


def legacy_x_candidates(all_bounds):
    """The current X sweep, retained here as a test-only oracle."""
    order = sorted(range(len(all_bounds)),
                   key=lambda index: (all_bounds[index][0][0],
                                      all_bounds[index][1][0], index))
    active = []
    for current in order:
        current_min_x = all_bounds[current][0][0]
        active = [index for index in active
                  if all_bounds[index][1][0] >= current_min_x]
        for candidate in active:
            first, second = all_bounds[candidate], all_bounds[current]
            if (np.any(first[1] < second[0])
                    or np.any(second[1] < first[0])):
                continue
            yield min(candidate, current), max(candidate, current)
        active.append(current)


def independent_aabb_pairs(all_bounds):
    """Oracle deliberately independent of the implementation sweep."""
    return {
        (first, second)
        for first, second in itertools.combinations(range(len(all_bounds)), 2)
        if all(all_bounds[first][0][axis] <= all_bounds[second][1][axis]
               and all_bounds[second][0][axis] <= all_bounds[first][1][axis]
               for axis in range(3))
    }


class AdaptiveBroadPhaseTest(TestCase):

    def test_pressure_counts_touching_and_degenerate_intervals_inclusively(self):
        all_bounds = [
            bounds(0, 1, 0, 0, 0, 1),
            bounds(1, 2, 0, 0, 0, 1),
            bounds(2, 2, 0, 0, 0, 1),
        ]

        order, pressure = test_module._axis_order_and_pressure(all_bounds, 0)

        self.assertEqual(order, [0, 1, 2])
        self.assertEqual(pressure, 2)

    def test_zero_x_pressure_keeps_the_existing_x_fast_path(self):
        all_bounds = [bounds(index * 3, index * 3 + 1, 0, 1, 0, 1)
                      for index in range(8)]

        with patch('solid_node.test._axis_order_and_pressure',
                   wraps=test_module._axis_order_and_pressure) as pressure:
            self.assertEqual(list(test_module._bounds_candidates(all_bounds)), [])

        self.assertEqual([call.args[1] for call in pressure.call_args_list], [0])

    def test_y_or_z_separation_avoids_x_quadratic_candidate_checks(self):
        for axis in (1, 2):
            for count in (128, 256, 512, 1024):
                with self.subTest(axis=axis, count=count):
                    # Every interval overlaps on X, while every pair is
                    # separated on Y or Z. The legacy X sweep asks every pair
                    # the full-AABB question; the sparse-axis sweep has none.
                    spans = []
                    for index in range(count):
                        low = [0, 0, 0]
                        high = [1, 1, 1]
                        low[axis] = index * 3
                        high[axis] = index * 3 + 1
                        spans.append(bounds(*low, *high))
                    with patch('solid_node.test._boxes_disjoint',
                               wraps=test_module._boxes_disjoint) as disjoint:
                        candidates = list(test_module._bounds_candidates(spans))

                    self.assertEqual(candidates, [])
                    self.assertEqual(disjoint.call_count, 0)

    def test_nonzero_equal_pressure_ties_select_x(self):
        all_bounds = [bounds(0, 1, 0, 1, 0, 1) for _ in range(3)]

        with patch('solid_node.test._sweep_candidates',
                   wraps=test_module._sweep_candidates) as sweep:
            self.assertEqual(list(test_module._bounds_candidates(all_bounds)),
                             list(legacy_x_candidates(all_bounds)))

        self.assertEqual([call.args[1] for call in sweep.call_args_list], [0])

    def test_adaptive_candidates_keep_exact_legacy_x_set_and_order(self):
        touching = [
            bounds(0, 1, 0, 1, 0, 1),
            bounds(1, 2, 0, 1, 0, 1),       # face touch
            bounds(1, 2, 1, 2, 0, 1),       # edge touch
            bounds(1, 2, 1, 2, 1, 2),       # vertex touch
            bounds(0.25, 0.75, 0.25, 0.75, 0.25, 0.75),  # containment
            bounds(0, 1, 0, 1, 0, 0),       # zero extent
            bounds(0, 1, 0, 1, 0, 1),       # coincidence
            bounds(0, 1, 8, 9, 0, 1),
        ]
        rng = random.Random(725)
        randomized = []
        for _ in range(24):
            low = [rng.randrange(-4, 5) for _ in range(3)]
            width = [rng.randrange(0, 4) for _ in range(3)]
            randomized.append(bounds(low[0], low[0] + width[0],
                                     low[1], low[1] + width[1],
                                     low[2], low[2] + width[2]))

        for name, all_bounds in (('adversarial', touching),
                                 ('randomized', randomized)):
            for permutation in (list(range(len(all_bounds))),
                                list(reversed(range(len(all_bounds))))):
                with self.subTest(case=name, permutation=permutation[:3]):
                    permuted = [all_bounds[index] for index in permutation]
                    self.assertEqual(list(test_module._bounds_candidates(permuted)),
                                     list(legacy_x_candidates(permuted)))

    def test_exhaustive_and_multi_seed_aabb_oracle_matches_candidates(self):
        # The 3×3×3 positions enumerate each axis's separated, touching and
        # overlapping relation for unit boxes. The oracle is pairwise AABB
        # comparison rather than either sweep implementation.
        exhaustive = [bounds(x, x + 1, y, y + 1, z, z + 1)
                      for x, y, z in itertools.product((0, 1, 3), repeat=3)]
        randomized = []
        for seed in (7, 19, 73, 211):
            rng = random.Random(seed)
            case = []
            for _ in range(20):
                low = [rng.randrange(-5, 6) for _ in range(3)]
                width = [rng.randrange(0, 4) for _ in range(3)]
                case.append(bounds(low[0], low[0] + width[0],
                                   low[1], low[1] + width[1],
                                   low[2], low[2] + width[2]))
            randomized.append(case)

        # These are already world AABBs of rotated boxes. Their conservative
        # enlargement is intentional input to the candidate index.
        rotated = [
            bounds(-1.42, 1.42, -1.42, 1.42, -1, 1),
            bounds(0.9, 2.9, 0.9, 2.9, -1, 1),
            bounds(4, 6, -1, 1, -1, 1),
        ]
        for case in [exhaustive, rotated, *randomized]:
            for permutation in (list(range(len(case))),
                                list(reversed(range(len(case))))):
                permuted = [case[index] for index in permutation]
                with self.subTest(size=len(case), first=permutation[:2]):
                    emitted = list(test_module._bounds_candidates(permuted))
                    self.assertEqual(set(emitted),
                                     independent_aabb_pairs(permuted))
                    self.assertEqual(emitted, list(legacy_x_candidates(permuted)))

    def test_dense_adaptive_candidates_fall_back_to_legacy_x_stream(self):
        # Three true overlaps make Y the least-pressure axis, while the
        # additional Y-separated boxes inflate only X pressure. A two-entry
        # buffer must abandon the adaptive materialization before returning.
        all_bounds = [bounds(0, 1, 0, 1, 0, 1) for _ in range(3)]
        all_bounds.extend(
            bounds(0, 1, 10 + index * 3, 11 + index * 3, 0, 1)
            for index in range(5))

        with patch.object(test_module, '_ADAPTIVE_CANDIDATE_BUFFER_LIMIT', 2,
                          create=True), \
                patch('solid_node.test._sweep_candidates',
                      wraps=test_module._sweep_candidates) as sweep:
            candidates = list(test_module._bounds_candidates(all_bounds))

        self.assertEqual(candidates, list(legacy_x_candidates(all_bounds)))
        # The selected Y sweep buffers only up to its cap, then its partial
        # list is discarded and the output comes solely from a streamed X
        # sweep. No selected-axis pair has been yielded to the caller first.
        self.assertEqual([call.args[1] for call in sweep.call_args_list], [1, 0])

    def test_support_candidates_keep_legacy_x_direction_and_order(self):
        dropped = [
            bounds(0, 1, 0, 1, 0, 1),
            bounds(0, 1, 5, 6, 0, 1),
        ]
        placed = [
            bounds(0, 1, 0, 1, 0, 1),
            bounds(0, 1, 5, 6, 0, 1),
            bounds(0, 1, 10, 11, 0, 1),
        ]
        all_bounds = dropped + placed
        expected = []
        for first, second in legacy_x_candidates(all_bounds):
            if first < len(dropped) <= second and second - len(dropped) != first:
                expected.append((first, second - len(dropped)))

        self.assertEqual(list(test_module._support_candidates(dropped, placed)),
                         expected)
