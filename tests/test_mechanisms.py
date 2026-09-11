# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""solid_node.mechanisms: the textbook mechanism laws the framework
carries once, so thirteen projects' `kinematics.py` stop rewriting them.

Each law is a composition over `solid_node.math`, so it has that
module's two faces -- numbers under a keyframe, a deferred OpenSCAD
expression under symbolic time or a driver -- and emits no builtin
`solid_node.math` does not already emit. There is no third, declared
face: the laws carry degree literals (`180`, `360`) the dimension
algebra cannot type as angles, so a declared token reaching one raises
at class definition. All three of those are pinned below, alongside the
numbers and identities the `mechanisms` spec states.
"""

import inspect
import math as pymath
import re
from unittest import TestCase

from solid2 import get_animation_time
from solid2.core.object_base import OpenSCADConstant

from solid_node import math as snmath
from solid_node.math import cos, sin
from solid_node.mechanisms import (circle_intersection, crank_pin,
                                   crank_rod_angle, delta_carriage, delta_rod,
                                   driving_angle, link_rise, meshed_angle,
                                   piston_height, screw_angle, screw_travel,
                                   triangle_angle)
from solid_node.node import AssemblyNode
from solid_node.parameters import Angle, DimensionError
from tests.test_math import _expanded


# --- the evaluator, lifted from tests/test_math.py ------------------------

def _eval_openscad_expr(expr, t):
    """Tiny degree-aware evaluator for the OpenSCAD expression strings
    solid_node.math generates, substituting a numeric $t. Lifted
    verbatim from tests/test_math.py -- it is NOT part of the
    framework."""
    py_expr = _expanded(expr).replace('$t', repr(t))
    py_expr = re.sub(r'\bsin\(', 'DEGSIN(', py_expr)
    py_expr = re.sub(r'\bcos\(', 'DEGCOS(', py_expr)
    py_expr = re.sub(r'\btan\(', 'DEGTAN(', py_expr)
    py_expr = re.sub(r'\basin\(', 'DEGASIN(', py_expr)
    py_expr = re.sub(r'\bacos\(', 'DEGACOS(', py_expr)
    py_expr = re.sub(r'\batan2\(', 'DEGATAN2(', py_expr)
    py_expr = re.sub(r'\batan\(', 'DEGATAN(', py_expr)
    py_expr = re.sub(r'\bsqrt\(', 'DEGSQRT(', py_expr)

    env = {
        'DEGSIN': lambda x: pymath.sin(pymath.radians(x)),
        'DEGCOS': lambda x: pymath.cos(pymath.radians(x)),
        'DEGTAN': lambda x: pymath.tan(pymath.radians(x)),
        'DEGASIN': lambda x: pymath.degrees(pymath.asin(x)),
        'DEGACOS': lambda x: pymath.degrees(pymath.acos(x)),
        'DEGATAN2': lambda y, x: pymath.degrees(pymath.atan2(y, x)),
        'DEGATAN': lambda x: pymath.degrees(pymath.atan(x)),
        'DEGSQRT': pymath.sqrt,
    }
    return eval(py_expr, {'__builtins__': {}}, env)


class GearMeshTest(TestCase):
    """The external spur-gear mesh law, and its inverse."""

    def test_the_pair_is_meshed_at_the_reference_pose(self):
        # The driver stands with its referenced gap centre pointing
        # along the line of centres; the driven's referenced tooth tip
        # then points back along it, into that gap.
        for line, gap, tooth, z1, z2 in ((0.0, 0.0, 0.0, 12, 24),
                                         (30.0, 3.0, 22.5, 60, 8),
                                         (-71.0, 15.0, -7.5, 40, 10)):
            self.assertAlmostEqual(
                meshed_angle(line - gap, z1, z2, line, gap, tooth),
                line + 180 - tooth)

    def test_the_driven_counter_rotates_by_the_tooth_ratio(self):
        base = meshed_angle(0.0, 60, 8, 30.0, 3.0, 22.5)
        stepped = meshed_angle(1.0, 60, 8, 30.0, 3.0, 22.5)
        self.assertAlmostEqual(stepped - base, -7.5)

        for z1, z2 in ((12, 24), (40, 10), (7, 7)):
            self.assertAlmostEqual(
                meshed_angle(1.0, z1, z2) - meshed_angle(0.0, z1, z2),
                -z1 / z2)

    def test_the_cq_gears_convention_is_two_values(self):
        # cq_gears centres a tooth on local +X at zero, so a gap centre
        # sits at 180 / z; gearbox's conjugate_angle is this law with
        # driver_gap = 180 / z1 and driven_tooth = 0.
        self.assertAlmostEqual(meshed_angle(0, 12, 24, 0, 180 / 12, 0), 172.5)
        self.assertAlmostEqual(meshed_angle(30, 12, 24, 45, 15, 0), 225.0)

    def test_the_inverse_round_trips(self):
        self.assertAlmostEqual(meshed_angle(10, 60, 8, 30, 3, 22.5), 315.0)
        self.assertAlmostEqual(
            driving_angle(meshed_angle(10, 60, 8, 30, 3, 22.5),
                          60, 8, 30, 3, 22.5),
            10.0)
        for driver in (-90.0, -12.5, 0.0, 7.0, 123.75, 400.0):
            self.assertAlmostEqual(
                driving_angle(meshed_angle(driver, 12, 24, 45, 15, -7.5),
                              12, 24, 45, 15, -7.5),
                driver)

    def test_the_law_reads_no_gear_object(self):
        # Both references default to zero, so a caller that has none
        # states none.
        self.assertAlmostEqual(meshed_angle(0.0, 1, 1), 180.0)


class ScrewTest(TestCase):
    """The lead screw: right-hand, sign-neutral, lead per turn."""

    def test_one_turn_is_one_lead(self):
        self.assertAlmostEqual(screw_travel(360, 2.0), 2.0)
        self.assertAlmostEqual(screw_angle(1.0, 2.0), 180.0)

    def test_the_two_are_exact_inverses(self):
        for lead in (0.5, 2.0, 40.66, -1.25):
            for angle in (-720.0, -37.5, 0.0, 90.0, 1000.0):
                self.assertAlmostEqual(
                    screw_angle(screw_travel(angle, lead), lead), angle)

    def test_a_multi_start_lead_is_stated_not_assumed(self):
        # A four-start 1 mm-pitch screw advances 4 mm per turn: the
        # caller passes the lead, the function never multiplies a pitch.
        self.assertAlmostEqual(screw_travel(360, 4 * 1.0), 4.0)

    def test_handedness_is_the_callers_sign(self):
        # openflexure's column falls as its motor turns positively; that
        # is the machine's handedness, spelled as a minus in the caller.
        self.assertAlmostEqual(-screw_travel(180, 0.5), -0.25)
        self.assertAlmostEqual(screw_travel(180, 0.5), 0.25)
        signature = inspect.signature(screw_travel)
        self.assertEqual(list(signature.parameters), ['angle', 'lead'])


class CrankTest(TestCase):
    """The planar slider-crank, in the crank's own plane."""

    def test_top_quarter_and_bottom_dead_centre(self):
        radius, rod = 15.0, 60.0

        for angle, pin in ((0, (0.0, 15.0)),
                           (90, (-15.0, 0.0)),
                           (180, (0.0, -15.0))):
            across, along = crank_pin(angle, radius)
            self.assertAlmostEqual(across, pin[0])
            self.assertAlmostEqual(along, pin[1])

        self.assertAlmostEqual(crank_rod_angle(0, radius, rod), 0.0)
        self.assertAlmostEqual(crank_rod_angle(90, radius, rod),
                               -pymath.degrees(pymath.asin(0.25)))
        self.assertAlmostEqual(crank_rod_angle(90, radius, rod), -14.4775122)
        self.assertAlmostEqual(crank_rod_angle(180, radius, rod), 0.0)

        self.assertAlmostEqual(piston_height(0, radius, rod), 75.0)
        self.assertAlmostEqual(piston_height(90, radius, rod),
                               pymath.sqrt(3375))
        self.assertAlmostEqual(piston_height(90, radius, rod), 58.0947502)
        self.assertAlmostEqual(piston_height(180, radius, rod), 45.0)

    def test_the_small_end_stays_on_the_cylinder_axis(self):
        radius, rod = 15.0, 60.0
        for angle in (-135.0, -40.0, 0.0, 23.5, 90.0, 180.0, 271.25, 360.0):
            across, along = crank_pin(angle, radius)
            tilt = crank_rod_angle(angle, radius, rod)
            # A rod authored along the cylinder axis, from the pin, and
            # turned by `tilt` in the same rotational sense.
            end_across = across - rod * sin(tilt)
            end_along = along + rod * cos(tilt)
            self.assertAlmostEqual(end_across, 0.0)
            self.assertAlmostEqual(end_along,
                                   piston_height(angle, radius, rod))


class DeltaTest(TestCase):
    """Linear delta kinematics: the carriage, and the rod's two poses."""

    def test_a_rod_at_the_origin_at_the_towers_foot(self):
        self.assertAlmostEqual(delta_carriage(0, 0, 215, 100, 0),
                               pymath.sqrt(215 ** 2 - 100 ** 2))
        self.assertAlmostEqual(delta_carriage(0, 0, 215, 100, 0), 190.3287,
                               places=4)
        tilt, azimuth = delta_rod(0, 0, 215, 100, 0)
        self.assertAlmostEqual(tilt, pymath.degrees(pymath.asin(100 / 215)))
        self.assertAlmostEqual(tilt, 27.7177, places=4)
        self.assertAlmostEqual(azimuth, 180.0)

    def test_moving_toward_and_beside_the_tower(self):
        self.assertAlmostEqual(delta_carriage(10, 0, 215, 100, 0), 195.2562,
                               places=4)
        tilt, azimuth = delta_rod(10, 0, 215, 100, 0)
        self.assertAlmostEqual(tilt, 24.7465, places=4)
        self.assertAlmostEqual(azimuth, 180.0)

        self.assertAlmostEqual(delta_carriage(0, 10, 215, 100, 0), 190.0658,
                               places=4)
        tilt, azimuth = delta_rod(0, 10, 215, 100, 0)
        self.assertAlmostEqual(tilt, 27.8680, places=4)
        self.assertAlmostEqual(azimuth, 174.2894, places=4)

    def test_the_joint_plane_lifts_the_carriage(self):
        self.assertAlmostEqual(delta_carriage(0, 0, 215, 100, 0, 12.5),
                               12.5 + pymath.sqrt(215 ** 2 - 100 ** 2))

    def test_the_posed_rod_meets_both_joints(self):
        rod, radius, plane = 215.0, 100.0, 7.5
        for tower in (0.0, 120.0, 240.0, -37.0):
            for x, y in ((0.0, 0.0), (10.0, 0.0), (0.0, 10.0),
                         (-25.0, 40.0), (60.0, -15.0)):
                carriage = delta_carriage(x, y, rod, radius, tower, plane)
                tilt, azimuth = delta_rod(x, y, rod, radius, tower)

                # A unit vector along -Z, rotated by -tilt about Y, then
                # by azimuth about Z, scaled by the rod.
                vx, vy, vz = 0.0, 0.0, -1.0
                vx, vz = (vx * cos(-tilt) + vz * sin(-tilt),
                          -vx * sin(-tilt) + vz * cos(-tilt))
                vx, vy = (vx * cos(azimuth) - vy * sin(azimuth),
                          vx * sin(azimuth) + vy * cos(azimuth))
                vx, vy, vz = rod * vx, rod * vy, rod * vz

                dx = x - radius * cos(tower)
                dy = y - radius * sin(tower)
                self.assertAlmostEqual(vx, dx, places=6)
                self.assertAlmostEqual(vy, dy, places=6)
                self.assertAlmostEqual(vz, -(carriage - plane), places=6)


class LinkageTest(TestCase):
    """Circle-circle intersection, the law of cosines, and a link's rise."""

    def test_two_circles_cross_on_the_side_asked_for(self):
        left = circle_intersection((0, 0), 5, (8, 0), 5, 1)
        right = circle_intersection((0, 0), 5, (8, 0), 5, -1)
        self.assertAlmostEqual(left[0], 4.0)
        self.assertAlmostEqual(left[1], 3.0)
        self.assertAlmostEqual(right[0], 4.0)
        self.assertAlmostEqual(right[1], -3.0)

        turned = circle_intersection((1, 1), 5, (1, 9), 5, 1)
        self.assertAlmostEqual(turned[0], -2.0)
        self.assertAlmostEqual(turned[1], 5.0)

    def test_the_intersection_is_on_both_circles(self):
        for side in (1, -1):
            point = circle_intersection((3.0, -2.0), 45.0, (33.0, 38.0), 20.0,
                                        side)
            self.assertAlmostEqual(
                pymath.hypot(point[0] - 3.0, point[1] + 2.0), 45.0, places=6)
            self.assertAlmostEqual(
                pymath.hypot(point[0] - 33.0, point[1] - 38.0), 20.0,
                places=6)

    def test_the_grasshoppers_nib_is_a_circle_intersection(self):
        nib = circle_intersection((0, 0), 45, (30, 40), 20, 1)
        self.assertAlmostEqual(nib[0], 10.3625, places=4)
        self.assertAlmostEqual(nib[1], 43.7906, places=4)

    def test_a_right_triangle(self):
        self.assertAlmostEqual(triangle_angle(5, 3, 4), 90.0)
        self.assertAlmostEqual(triangle_angle(3, 4, 5), 36.8698976)
        self.assertAlmostEqual(link_rise(5, 3), 4.0)

    def test_an_unreachable_configuration_is_not_guarded(self):
        with self.assertRaises(ValueError):
            link_rise(3.0, 5.0)
        with self.assertRaises(ValueError):
            triangle_angle(100.0, 3.0, 4.0)


# --- the two faces --------------------------------------------------------

#: A driving value that is valid for every law below, as a plain number
#: and as a linear expression in $t hitting the same values.
SAMPLES = (20.0, 30.0, 40.0, 50.0)
TIMES = (0.0, 1 / 3, 2 / 3, 1.0)


def _drive(t):
    return 20.0 + 30.0 * t


#: Every exported law, closed over everything but its driving argument.
LAWS = (
    ('meshed_angle', lambda d: meshed_angle(d, 12, 24, 30.0, 15.0, 7.5)),
    ('driving_angle', lambda d: driving_angle(d, 12, 24, 30.0, 15.0, 7.5)),
    ('screw_travel', lambda d: screw_travel(d, 2.0)),
    ('screw_angle', lambda d: screw_angle(d, 2.0)),
    ('crank_pin', lambda d: crank_pin(d, 15.0)),
    ('crank_rod_angle', lambda d: crank_rod_angle(d, 15.0, 60.0)),
    ('piston_height', lambda d: piston_height(d, 15.0, 60.0)),
    ('delta_carriage', lambda d: delta_carriage(d, 10.0, 215.0, 100.0, 0.0,
                                                5.0)),
    ('delta_rod', lambda d: delta_rod(d, 10.0, 215.0, 100.0, 0.0)),
    ('circle_intersection',
     lambda d: circle_intersection((0.0, 0.0), 45.0, (d, 40.0), 20.0, 1)),
    ('triangle_angle', lambda d: triangle_angle(d, 40.0, 50.0)),
    ('link_rise', lambda d: link_rise(60.0, d)),
)


def _parts(result):
    return result if isinstance(result, tuple) else (result,)


class SymbolicFaceTest(TestCase):
    """A law riding a symbolic driver builds an expression and raises
    nothing, and the expression names only builtins solid_node.math
    already emits."""

    #: The builtins the base module's own `_symbolic_call` sites use,
    #: read from its source so this test cannot drift from it.
    EMITTED = set(re.findall(r"_symbolic_call\('(\w+)'",
                             inspect.getsource(snmath)))

    def test_the_module_emits_the_names_we_think_it_does(self):
        # A subset, not an equality: `solid_node.math`'s inventory of
        # builtins may grow, and this package does not care that it
        # does. What must hold is that the degree trig and `sqrt` these
        # laws are composed of are in it -- the real guard is
        # `test_a_law_rides_through_a_symbolic_driver` below, which
        # holds every law's emitted names to whatever the inventory is.
        self.assertTrue(
            {'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2', 'sqrt'}
            <= self.EMITTED,
            'solid_node.math stopped emitting {}'.format(
                {'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
                 'sqrt'} - self.EMITTED))

    def test_a_law_rides_through_a_symbolic_driver(self):
        symbol = _drive(get_animation_time())

        for name, law in LAWS:
            with self.subTest(law=name):
                for part in _parts(law(symbol)):
                    self.assertIsInstance(part, OpenSCADConstant)
                    called = set(re.findall(r'([A-Za-z_]\w*)\s*\(', _expanded(part)))
                    self.assertTrue(
                        called <= self.EMITTED,
                        '{} emits {}'.format(name, called - self.EMITTED))

    def test_the_piston_expression_is_cos_sin_and_sqrt(self):
        symbol = _drive(get_animation_time())
        expression = _expanded(piston_height(symbol, 15.0, 60.0))
        self.assertEqual(
            set(re.findall(r'([A-Za-z_]\w*)\s*\(', expression)),
            {'cos', 'sin', 'sqrt'})
        self.assertIn('$t', expression)


class NumericSymbolicAgreementTest(TestCase):
    """Each law's two faces agree: the expression evaluated at a sampled
    $t equals the numeric call at the same driving value."""

    def test_every_law_agrees_with_itself(self):
        symbol = _drive(get_animation_time())

        for name, law in LAWS:
            with self.subTest(law=name):
                symbolic = _parts(law(symbol))
                for t in TIMES:
                    numeric = _parts(law(_drive(t)))
                    self.assertEqual(len(symbolic), len(numeric))
                    for built, expected in zip(symbolic, numeric):
                        self.assertAlmostEqual(
                            _eval_openscad_expr(str(built), t), expected,
                            places=9)


class DeclaredFaceTest(TestCase):
    """There is no third face: a declared token reaching a law raises
    the algebra's own dimension error at class definition, and `.value`
    is the documented way through."""

    def test_a_declared_angle_is_refused(self):
        with self.assertRaises(DimensionError):
            class Pair(AssemblyNode):
                theta = Angle(10.0)
                driven = meshed_angle(theta, 12, 24)

    def test_the_escape_hatch_computes_a_static_phase(self):
        class Pair(AssemblyNode):
            theta = Angle(10.0)
            driven = meshed_angle(theta.value, 12, 24)

        self.assertAlmostEqual(Pair().driven, 175.0)
