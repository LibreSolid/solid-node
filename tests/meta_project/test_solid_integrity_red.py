from solid_node.test import TestCase


class SolidIntegrityRedTest(TestCase):

    def test_solid_integrity(self):
        self.assertNoDisconnectedSolids(self.node)
