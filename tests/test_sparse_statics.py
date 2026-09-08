# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Sparse-storage equivalence for the static-equilibrium program."""

from dataclasses import dataclass
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

import solid_node.test as test_module

from .test_assembly_supported import SupportFixture, asserter


@dataclass(frozen=True)
class _SolveResult:
    """The observable LP result used to compare storage representations."""

    failures: tuple
    objective: float
    slack: np.ndarray
    coefficients: object
    equality: object
    target: np.ndarray
    tolerance: np.ndarray


def _dense_reference(bodies, contacts, declared, unit_gravity):
    """Planning-HEAD ``_unbalanced_bodies`` with its dense storage frozen.

    The row/column loops, scaling, objective, bounds and HiGHS invocation are
    copied from planning commit 4bcf4cb5.  Only the return value is expanded so
    tests can compare the optimized slack and constructed coefficients as well
    as the public failure classification.
    """
    free = [index for index, body in enumerate(bodies) if not body.anchored]
    if not free:
        return _SolveResult((), 0.0, np.zeros(0), np.zeros((0, 0)),
                            np.zeros((0, 0)), np.zeros(0), np.zeros(0))
    row_of = {index: 6 * position for position, index in enumerate(free)}
    rows = 6 * len(free)
    variables = len(contacts) + 6 * len(declared)
    matrix = np.zeros((rows, variables))
    target = np.zeros(rows)
    tolerance = np.zeros(rows)
    for position, index in enumerate(free):
        body = bodies[index]
        row = 6 * position
        target[row:row + 3] = -body.weight * unit_gravity
        scale = (test_module._BALANCE_TOLERANCE
                 * max(body.weight, test_module._BALANCE_TOLERANCE))
        tolerance[row:row + 3] = scale
        tolerance[row + 3:row + 6] = scale * max(body.diagonal, 1.0)
    for column, contact in enumerate(contacts):
        for index, sign in ((contact.supported, 1.0),
                            (contact.supporter, -1.0)):
            row = row_of.get(index)
            if row is None:
                continue
            force = sign * contact.normal
            matrix[row:row + 3, column] += force
            matrix[row + 3:row + 6, column] += np.cross(
                contact.point - bodies[index].center, force)
    for edge, (supported, supporter) in enumerate(declared):
        first = len(contacts) + 6 * edge
        for index, sign in ((supported, 1.0), (supporter, -1.0)):
            row = row_of.get(index)
            if row is None:
                continue
            center = bodies[index].center
            for axis in range(3):
                unit = np.zeros(3)
                unit[axis] = 1.0
                matrix[row:row + 3, first + axis] += sign * unit
                matrix[row + 3:row + 6, first + axis] += sign * np.cross(
                    -center, unit)
                matrix[row + 3:row + 6, first + 3 + axis] += sign * unit
    identity = np.eye(rows)
    objective = np.concatenate(
        [np.zeros(variables), 1 / tolerance, 1 / tolerance])
    equality = np.hstack([matrix, identity, -identity])
    solution = linprog(
        objective, A_eq=equality, b_eq=target,
        bounds=([(0.0, None)] * len(contacts)
                + [(None, None)] * (6 * len(declared))
                + [(0.0, None)] * (2 * rows)),
        method='highs')
    if not solution.success:
        raise AssertionError(
            "dense reference: the static equilibrium program did not solve "
            f"({solution.message})")
    slack = np.abs(solution.x[variables:variables + rows]
                   - solution.x[variables + rows:])
    failures = []
    for position, index in enumerate(free):
        row = 6 * position
        kinds = [kind for kind, block in (('force', slice(row, row + 3)),
                                          ('torque', slice(row + 3, row + 6)))
                 if np.any(slack[block] > tolerance[block])]
        if kinds:
            failures.append((index, ' and '.join(kinds)))
    return _SolveResult(tuple(failures), float(solution.fun), slack, matrix,
                        equality, target, tolerance)


def _production_result(bodies, contacts, declared, unit_gravity,
                       implementation=None):
    """Run production while retaining the exact program handed to HiGHS."""
    captured = {}

    def solve(objective, **keywords):
        solution = linprog(objective, **keywords)
        captured.update(objective=objective, solution=solution, **keywords)
        return solution

    implementation = implementation or test_module._unbalanced_bodies
    with patch.object(test_module, 'linprog', side_effect=solve):
        failures = implementation(bodies, contacts, declared, unit_gravity)

    rows = len(captured['b_eq'])
    variables = len(contacts) + 6 * len(declared)
    solution = captured['solution']
    slack = np.abs(solution.x[variables:variables + rows]
                   - solution.x[variables + rows:])
    equality = captured['A_eq']
    coefficients = equality[:, :variables]
    return _SolveResult(tuple(failures), float(solution.fun), slack,
                        coefficients, equality, captured['b_eq'],
                        1 / captured['objective'][variables:variables + rows])


def _body(name, *, weight=1.0, center=(0.0, 0.0, 0.0), diagonal=1.0,
          anchored=False):
    return test_module._Body(name, None, None, float(weight),
                             np.asarray(center, float), float(diagonal),
                             anchored)


def _contact(point, normal, supported, supporter):
    return test_module._Contact(np.asarray(point, float),
                                np.asarray(normal, float),
                                supported, supporter)


class DenseSparseGeneratedEquivalenceTest(TestCase):

    def assertEquivalent(self, bodies, contacts=(), declared=(),
                         gravity=(0.0, 0.0, -1.0)):
        gravity = np.asarray(gravity, float)
        dense = _dense_reference(bodies, contacts, declared, gravity)
        actual = _production_result(bodies, contacts, declared, gravity)

        self.assertEqual(actual.failures, dense.failures)
        self.assertAlmostEqual(actual.objective, dense.objective, places=10)
        np.testing.assert_allclose(actual.slack, dense.slack,
                                   rtol=1e-10, atol=1e-12)
        np.testing.assert_array_equal(actual.target, dense.target)
        np.testing.assert_array_equal(actual.tolerance, dense.tolerance)
        actual_coefficients = (actual.coefficients.toarray()
                               if sparse.issparse(actual.coefficients)
                               else actual.coefficients)
        np.testing.assert_array_equal(actual_coefficients,
                                      dense.coefficients)
        return actual

    def test_generated_feasible_infeasible_and_declared_wrench_systems(self):
        free = _body('free')
        anchor = _body('anchor', anchored=True)
        feasible = self.assertEquivalent(
            [free, anchor], [_contact((0, 0, 0), (0, 0, 1), 0, 1)])
        force_failure = self.assertEquivalent(
            [free, anchor], [_contact((0, 0, 0), (1, 0, 0), 0, 1)])
        torque_failure = self.assertEquivalent(
            [_body('free', diagonal=10), anchor],
            [_contact((1, 0, 0), (0, 0, 1), 0, 1)])
        declared = self.assertEquivalent([free, anchor], declared=[(0, 1)])

        self.assertEqual(feasible.failures, ())
        self.assertEqual(force_failure.failures, ((0, 'force'),))
        self.assertEqual(torque_failure.failures, ((0, 'torque'),))
        self.assertEqual(declared.failures, ())

    def test_force_and_torque_classification_agrees_near_tolerance(self):
        weight = 1_000_000.0
        diagonal = 10.0
        free = _body('near', weight=weight, diagonal=diagonal)
        anchor = _body('anchor', anchored=True)

        force_cases = []
        for side in (0.999, 1.001):
            normal = np.array(
                [test_module._BALANCE_TOLERANCE * side, 0.0, 1.0])
            normal /= np.linalg.norm(normal)
            force_cases.append(self.assertEquivalent(
                [free, anchor], [_contact((0, 0, 0), normal, 0, 1)]))

        lever_threshold = test_module._BALANCE_TOLERANCE * diagonal
        torque_below = self.assertEquivalent(
            [free, anchor],
            [_contact((lever_threshold * 0.999, 0, 0),
                      (0, 0, 1), 0, 1)])
        torque_above = self.assertEquivalent(
            [free, anchor],
            [_contact((lever_threshold * 1.001, 0, 0),
                      (0, 0, 1), 0, 1)])

        self.assertEqual(force_cases[0].failures, ())
        self.assertEqual(force_cases[1].failures, ((0, 'force'),))
        self.assertEqual(torque_below.failures, ())
        self.assertEqual(torque_above.failures, ((0, 'torque'),))

    def test_cancellation_and_repeated_construction_are_deterministic(self):
        body = _body('self-supported', center=(3.0, -2.0, 1.0))
        self_contact = _contact((8.0, 5.0, -4.0),
                                (1e16, 1.0, -1e-16), 0, 0)
        results = [self.assertEquivalent([body], [self_contact], [(0, 0)])
                   for _ in range(5)]

        first = results[0]
        for result in results[1:]:
            self.assertEqual(result.failures, first.failures)
            self.assertEqual(result.objective, first.objective)
            np.testing.assert_array_equal(result.slack, first.slack)
            np.testing.assert_array_equal(result.equality.toarray()
                                          if sparse.issparse(result.equality)
                                          else result.equality,
                                          first.equality.toarray()
                                          if sparse.issparse(first.equality)
                                          else first.equality)


class DenseSparseExistingFixtureTest(SupportFixture):
    """Run every statics-specific real-geometry fixture through both LPs."""

    def _paired(self, action, *, fails=False):
        original = test_module._unbalanced_bodies
        comparisons = []

        def compare(bodies, contacts, declared, unit_gravity):
            dense = _dense_reference(bodies, contacts, declared, unit_gravity)
            actual = _production_result(bodies, contacts, declared,
                                        unit_gravity, original)
            self.assertEqual(actual.failures, dense.failures)
            self.assertAlmostEqual(actual.objective, dense.objective, places=8)
            np.testing.assert_allclose(actual.slack, dense.slack,
                                       rtol=1e-8, atol=1e-10)
            comparisons.append((actual.failures, actual.objective))
            return list(actual.failures)

        # Keep the bound implementation stable while the module name is
        # patched; `_production_result` invokes this planning-descendant body
        # directly, avoiding recursion through the characterization wrapper.
        with patch.object(test_module, '_unbalanced_bodies', side_effect=compare):
            if fails:
                with self.assertRaises(AssertionError):
                    action()
            else:
                action()
        self.assertTrue(comparisons)
        self.assertIs(original, test_module._unbalanced_bodies)

    def test_existing_balanced_unbalanced_and_counterweight_fixtures(self):
        cases = [
            ('stack', lambda: asserter.assertAssemblySupported(self.stack()[2]),
             False),
            ('one-end bar', lambda: asserter.assertAssemblySupported(
                self.one_end_bar()[2]), True),
            ('two-end bar', lambda: asserter.assertAssemblySupported(
                self.two_end_bar()[1]), False),
            ('offset stack', lambda: asserter.assertAssemblySupported(
                self.offset_stack()[1]), True),
            ('beam alone', lambda: asserter.assertAssemblySupported(
                self.counterweighted(weight=False)[1]), True),
            ('counterweighted beam', lambda: asserter.assertAssemblySupported(
                self.counterweighted()[1]), False),
            ('overhead couple', lambda: asserter.assertAssemblySupported(
                self.pinned_block()[1], max_drop=0.5), False),
            ('top-heavy seed', lambda: asserter.assertAssemblySupported(
                self.tippy_pair()[2]), True),
            ('boundary balance', lambda: asserter.assertAssemblySupported(
                self.boundary_balance()[1]), False),
            ('positive margin', lambda: asserter.assertAssemblySupported(
                self.boundary_balance()[1], stability_margin=0.5), True),
        ]
        for name, action, fails in cases:
            with self.subTest(name=name):
                self._paired(action, fails=fails)

    def test_declared_wrench_and_exact_support_fixtures(self):
        post = self.block('post', (-1, 1), (-5, 1))
        fitted = self.block('fitted', (1, 3), (-1, 1))
        # Reuse the support fixture's assembly double rather than depending on
        # any production construction path outside the assertion under test.
        from .test_assembly_integrity import Assembly
        declared_root = Assembly('declared', (post, fitted))
        self._paired(
            lambda: asserter.assertAssemblySupported(
                declared_root, supports=[(fitted, post)]))

        base = self.exact_block('exact_base', (-1, 1), (-1, 1))
        top = self.exact_block('exact_top', (-1, 1), (1, 3))
        exact_root = Assembly('exact', (base, top))
        self._paired(lambda: asserter.assertAssemblySupported(exact_root))


class _GuardedNumpy:
    """Delegate NumPy except for the legacy dense allocation signatures."""

    def __init__(self):
        self.two_dimensional_zeros = []
        self.dense_identities = []

    def __getattr__(self, name):
        return getattr(np, name)

    def zeros(self, shape, *arguments, **keywords):
        if isinstance(shape, tuple) and len(shape) == 2:
            self.two_dimensional_zeros.append(shape)
            raise AssertionError(f'dense coefficient allocation {shape}')
        return np.zeros(shape, *arguments, **keywords)

    def eye(self, size, *arguments, **keywords):
        self.dense_identities.append(size)
        raise AssertionError(f'dense identity allocation {size}x{size}')


class SparseAllocationTest(TestCase):

    def test_production_hands_highs_one_sparse_equality_matrix(self):
        actual = _production_result(
            [_body('free'), _body('anchor', anchored=True)],
            [_contact((0, 0, 0), (0, 0, 1), 0, 1)], (),
            np.array([0.0, 0.0, -1.0]))

        self.assertTrue(sparse.issparse(actual.coefficients))
        self.assertTrue(sparse.issparse(actual.equality))
        self.assertEqual(actual.equality.shape, (6, 13))
        self.assertLessEqual(actual.equality.nnz,
                             actual.coefficients.nnz + 12)

    def test_one_thousand_bodies_never_attempt_dense_slack_blocks(self):
        free_count = 1000
        rows = 6 * free_count
        dense_slack_risk = 2 * rows * rows * np.dtype(float).itemsize
        self.assertEqual(dense_slack_risk, 576_000_000)
        bodies = [_body(f'body-{index}') for index in range(free_count)]
        guarded = _GuardedNumpy()
        captured = {}

        def solve(objective, **keywords):
            captured.update(objective=objective, **keywords)
            return SimpleNamespace(success=True, message='not solved',
                                   x=np.zeros(len(objective)))

        with patch.object(test_module, 'np', guarded), \
                patch.object(test_module, 'linprog', side_effect=solve):
            failures = test_module._unbalanced_bodies(
                bodies, (), (), np.array([0.0, 0.0, -1.0]))

        self.assertEqual(guarded.two_dimensional_zeros, [])
        self.assertEqual(guarded.dense_identities, [])
        # The solver is deliberately replaced: this test stops at the program
        # boundary and asks only what storage reached it.
        self.assertEqual(failures, [])
        equality = captured['A_eq']
        self.assertTrue(sparse.issparse(equality))
        self.assertEqual(equality.shape, (rows, 2 * rows))
        self.assertEqual(equality.nnz, 2 * rows)
