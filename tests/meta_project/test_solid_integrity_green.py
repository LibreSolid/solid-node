from solid_node.test import TestCase


class SolidIntegrityGreenTest(TestCase):

    def test_solid_integrity(self):
        self.assertNoDisconnectedSolids(self.node)
