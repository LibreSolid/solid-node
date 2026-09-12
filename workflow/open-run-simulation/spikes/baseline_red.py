"""Intentional failing requirements probe, BEFORE the running kernel exists.

This is not a claim that the current affine API promises retained state.
It demonstrates why absolute posing/endpoint-only polling cannot implement it.
Run separately from the green suite; the three assertion failures are evidence.
"""
import unittest
from solid_node.motion.couplings import Affine


class DesiredRunningBehaviour(unittest.TestCase):
    def test_reengagement_does_not_repose_previous_travel(self):
        pair = Affine(-2, 0)
        driven = pair.forward(10)
        # Open the coupling, turn the source 10 -> 20, then close it.
        # An absolute relation immediately jumps the retained -20 to -40.
        driven = pair.forward(20)
        self.assertEqual(driven, -20)

    def test_contact_between_frame_endpoints_is_not_lost(self):
        contact = lambda angle: 113.5 <= angle < 124.75
        driven = 0
        # The contact covers 11.25 degrees even though neither endpoint sees it.
        if contact(180):
            driven += 180 * 6.4
        self.assertAlmostEqual(driven, 72)

    def test_current_rate_does_not_rewrite_prior_motion(self):
        # First second at 10 degrees/s, second at 20 degrees/s.
        elapsed, current_rate = 2, 20
        position = elapsed * current_rate
        self.assertEqual(position, 30)


if __name__ == '__main__':
    unittest.main(verbosity=2)
