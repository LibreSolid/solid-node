# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
from unittest import TestCase
from unittest.mock import patch
from .base import BaseNodeTest
from . import flat_project


class StlGenerationLockedTest(BaseNodeTest):
    """Regression for B15(b): _stl_generation_locked's `os.kill(pid, 0)`
    only caught ProcessLookupError, so a PermissionError (pid belongs to
    another user, e.g. a real concurrent build) crashed instead of being
    treated as "process exists"."""

    def setUp(self):
        super().setUp()
        self.node = flat_project.SimpleCylinder()

    def test_empty_lock_file_is_not_locked(self):
        # Pin existing behavior: an empty/corrupt lock file is handled by
        # the existing ValueError catch and simply means "not locked".
        open(self.node.lock_file, 'w').write('')

        self.assertFalse(self.node._stl_generation_locked)

    def test_permission_error_from_kill_means_locked(self):
        open(self.node.lock_file, 'w').write('12345')

        with patch('solid_node.node.base.os.kill', side_effect=PermissionError):
            self.assertTrue(self.node._stl_generation_locked)
