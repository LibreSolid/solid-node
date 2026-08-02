# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase
from unittest.mock import call, patch

from solid_node import packaging


class FrontendPackagingTest(TestCase):

    def test_source_distribution_builds_both_frontends(self):
        with patch('solid_node.packaging.build_frontend') as build:
            packaging.build_distribution_frontends()

        self.assertEqual(build.call_args_list, [
            call(packaging.DEVELOPMENT_VIEWER),
            call(packaging.WIDGET_VIEWER),
        ])

    def test_wheel_builds_only_frontends_with_missing_outputs(self):
        with patch('solid_node.packaging.build_frontend') as build:
            with patch.object(packaging.DEVELOPMENT_VIEWER, 'output_exists',
                              return_value=True), \
                 patch.object(packaging.WIDGET_VIEWER, 'output_exists',
                              return_value=False):
                packaging.build_missing_frontends()

        build.assert_called_once_with(packaging.WIDGET_VIEWER)
