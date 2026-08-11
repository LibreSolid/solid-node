# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase

from solid_node.core.camera import OPENSCAD_FOV, parse_camera


class CameraConversionTest(TestCase):
    def assertVectorAlmostEqual(self, actual, expected):
        for component, wanted in zip(actual, expected):
            self.assertAlmostEqual(component, wanted, places=9)

    def test_vector_camera_passes_eye_and_target_through(self):
        camera = parse_camera("10,-20,30,1,2,3")

        self.assertEqual(camera.eye, (10.0, -20.0, 30.0))
        self.assertEqual(camera.target, (1.0, 2.0, 3.0))
        self.assertEqual(camera.up, (0.0, 0.0, 1.0))

    def test_single_gimbal_rotation_matches_openscad_modelview(self):
        camera = parse_camera("1,2,3,90,0,90,10")

        self.assertVectorAlmostEqual(camera.target, (1.0, 2.0, 3.0))
        self.assertVectorAlmostEqual(camera.eye, (11.0, 2.0, 3.0))
        self.assertVectorAlmostEqual(camera.up, (0.0, 0.0, 1.0))

    def test_all_gimbal_rotations_preserve_distance_and_roll(self):
        camera = parse_camera("4,-2,7,32,41,73,125")

        offset = tuple(a - b for a, b in zip(camera.eye, camera.target))
        self.assertAlmostEqual(
            sum(value * value for value in offset) ** 0.5, 125.0, places=9
        )
        self.assertAlmostEqual(
            sum(value * value for value in camera.up) ** 0.5,
            1.0,
            places=9,
        )
        self.assertAlmostEqual(
            sum(a * b for a, b in zip(offset, camera.up)), 0.0, places=9
        )
        self.assertVectorAlmostEqual(
            camera.eye,
            (87.67888051761673, 45.14068824334161, 87.00375283236716),
        )
        self.assertVectorAlmostEqual(
            camera.up,
            (-0.7093469725637416, 0.5804125704526232, 0.3999351454614023),
        )

    def test_openscad_field_of_view_is_emitted(self):
        self.assertEqual(parse_camera("0,0,10,0,0,0").fov, OPENSCAD_FOV)
        self.assertEqual(OPENSCAD_FOV, 22.5)

    def test_wrong_number_count_is_clear(self):
        with self.assertRaisesRegex(ValueError, "6 numbers.*7 numbers"):
            parse_camera("1,2,3")

    def test_non_numeric_camera_is_clear(self):
        with self.assertRaisesRegex(ValueError, "numbers"):
            parse_camera("1,2,three,4,5,6")
