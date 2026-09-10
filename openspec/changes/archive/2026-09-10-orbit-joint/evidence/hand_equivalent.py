"""What the hand-written equivalents of an Orbit fail, today.

Run from the worktree with PYTHONPATH="$PWD".
"""
import math
import numpy as np
from solid2 import cube

from solid_node.motion.joints import Prismatic, Revolute
from solid_node.motion.couplings import Affine
from solid_node.node import Solid2Node
from solid_node.node.base import _compose_world_matrix

LIFT = [0.0, -2.5, 0.0]


class ByRevolute(Solid2Node):
    """What OpenCycloid and the Internal Cycloidal Actuator write today:
    the orbit IS a Revolute, so it drags the attitude with it."""
    orbit = Revolute(axis=(0, 0, 1), unit='deg')
    def render(self):
        return cube(2, center=True)


class ByPrismatics(Solid2Node):
    """What YouCanBuildDog writes today: two Prismatics with a
    trigonometric law each."""
    across = Prismatic(axis=(0, 1, 0), unit='mm')
    along = Prismatic(axis=(1, 0, 0), unit='mm')
    def render(self):
        return cube(2, center=True)


def report():
    rest = np.eye(4); rest[:3, 3] = LIFT

    print('1. The attitude, with the orbit written as a Revolute')
    for angle in (0, 17, 90, 213.5, 360):
        body = ByRevolute()
        body.translate(LIFT)
        body.orbit = angle
        block = _compose_world_matrix(body)[:3, :3]
        print(f'   theta={angle:>6}: max |R - R_rest| = '
              f'{np.max(np.abs(block - rest[:3, :3])):.6f}')
    print('   -- the acceptance is atol=0. A Revolute fails it at every '
          'angle but the identity.\n')

    print('2. The operations a hand-written equivalent produces')
    body = ByPrismatics()
    body.translate(LIFT)
    body.across = 2.5 * (math.cos(math.radians(40)) - 1)
    body.along = 2.5 * math.sin(math.radians(40))
    print('   two Prismatics ->',
          [op.serialized for op in body.operations][:2])
    print('   an orbit is ONE operation; this is two, in two slots, and '
          'each carries a number the project computed rather than the '
          'angle it means.\n')

    print('3. The inverse')
    law = Affine(ratio=2.0)
    print('   Affine(ratio=2.0).invertible =', law.invertible)
    def swung(driver, driven):
        return lambda theta: 2.5 * math.sin(math.radians(theta))
    record = Affine(ratio=1.0)
    print('   a trigonometric law= callable, as the dog writes it, is a '
          'plain function: solid_node.motion.couplings refuses to solve '
          'it backwards (test_couplings::'
          'test_a_non_invertible_law_needed_backwards_is_refused).')
    print('   So the dog\'s 40 Prismatics cannot be driven from the foot.\n')

    print('4. The cycloidal identity, with the orbit written as a Revolute')
    ANGLE, T = 15.042379656, (0.897397081, -5.25, 3.895358836)
    B, C0, RED = (0.0, 0.0, -2.0), (0.378316, -5.25, 1.963896), 8

    def rot_y(p, a):
        r = math.radians(a); x, y, z = p
        return (x*math.cos(r) + z*math.sin(r), y,
                -x*math.sin(r) + z*math.cos(r))

    def matrix_rot(deg, axis):
        axis = np.array(axis, float); axis = axis/np.linalg.norm(axis)
        a = math.radians(deg)
        K = np.array([[0, -axis[2], axis[1]],
                      [axis[2], 0, -axis[0]],
                      [-axis[1], axis[0], 0]])
        m = np.eye(4)
        m[:3, :3] = np.eye(3) + math.sin(a)*K + (1-math.cos(a))*K@K
        return m

    def matrix_t(v):
        m = np.eye(4); m[:3, 3] = v; return m

    class DiskRevolutes(Solid2Node):
        spin = Revolute(axis=(0, 1, 0), at=C0, unit='deg')
        orbit = Revolute(axis=(0, 1, 0), at=(0, 0, 0), unit='deg')
        def render(self):
            return cube(2, center=True)

    for theta in (17.0, 90.0):
        disk = DiskRevolutes()
        disk.rotate(ANGLE, [0, 1, 0])
        disk.translate(list(T))
        disk.spin = -theta/RED
        disk.orbit = theta
        got = _compose_world_matrix(disk)

        centre = C0
        sigma = -theta/RED
        orbited = rot_y(centre, theta)
        delta = tuple(o-c for o, c in zip(orbited, centre))
        own = rot_y(delta, -ANGLE)
        carry = tuple(b+d for b, d in zip(B, own))
        want = (matrix_t(T) @ matrix_rot(ANGLE, (0, 1, 0)) @ matrix_t(carry)
                @ matrix_rot(sigma, (0, 1, 0)) @ matrix_t(-np.array(B)))
        print(f'   theta={theta}: max |R_got - R_want| = '
              f'{np.max(np.abs(got[:3,:3]-want[:3,:3])):.6f}, '
              f'max |p_got - p_want| = '
              f'{np.max(np.abs(got[:3,3]-want[:3,3])):.6f} mm')
    print('   -- a Revolute in the orbit\'s place is off in BOTH blocks; '
          'the project pays for it with a ratio=-(1 + 1/REDUCTION).')


report()
