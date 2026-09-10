"""The REAL `Free`, measured at the seven poses `probe_matrix.py`
measured the hexapod's four hand-written calls at.

Same fixtures the cycle's tests use, so the numbers below are the ones
`test_the_composition_is_the_one_the_hexapod_hand_inverts`,
`test_the_anchored_composition_is_the_same_product_conjugated` and
`test_the_hexapods_own_inverse_round_trips` assert with `atol=1e-12` and
`1e-9`.

    PYTHONPATH=<worktree> python probe_free_matrix.py
"""
import numpy as np

from solid_node.node.base import _compose_world_matrix
from tests.test_joints import (FREE_AT, FREE_POSES, AnchoredBench,
                               FloatingBench, _anchored_rest, _free_pose,
                               _to_chassis)

PROBE = np.array([37.0, -91.5, 12.25, 1.0])

worst_plain = worst_anchored = worst_inverse = 0.0
print(f'{"roll":>8}{"pitch":>8}{"yaw":>9}{"h":>9}   '
      f'{"identity rest":>14}  {"turned+moved rest":>18}  '
      f'{"_to_chassis (mm)":>17}')
for roll, pitch, yaw, height in FREE_POSES:
    bench = FloatingBench()
    bench.set_state(roll=roll, pitch=pitch, yaw=yaw, height=height)
    placed = _compose_world_matrix(bench.chassis)
    expected = _free_pose(roll, pitch, yaw, (0.0, 0.0, height))
    plain = float(np.max(np.abs(placed - expected)))

    anchored = AnchoredBench()
    anchored.render()
    body = anchored.body
    body.pose.roll = roll
    body.pose.pitch = pitch
    body.pose.yaw = yaw
    body.pose.z = height
    turned = float(np.max(np.abs(
        _compose_world_matrix(body)
        - _free_pose(roll, pitch, yaw, (0.0, 0.0, height),
                     anchor=FREE_AT, rest=_anchored_rest()))))

    world = placed @ PROBE
    back = _to_chassis(world[:3], roll, pitch, yaw, height)
    inverse = float(np.max(np.abs(back - PROBE[:3])))

    worst_plain = max(worst_plain, plain)
    worst_anchored = max(worst_anchored, turned)
    worst_inverse = max(worst_inverse, inverse)
    print(f'{roll:8}{pitch:8}{yaw:9}{height:9}   '
          f'{plain:14.3e}  {turned:18.3e}  {inverse:17.3e}')

print()
print('max |Free - NumPy product|, identity rest      =', worst_plain)
print('max |Free - NumPy product|, turned+moved rest  =', worst_anchored)
print('max |_to_chassis(Free(p)) - p| (mm)            =', worst_inverse)
