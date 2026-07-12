# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import tempfile
from unittest import TestCase
from unittest.mock import patch, MagicMock
from solid_node.viewers.openscad import OpenScadViewer
from .base import BaseNodeTest
from . import flat_project


class OpenScadViewerPidTest(TestCase):
    """Regression for B15(a): OpenScadViewer.pid only caught
    (FileNotFoundError, TypeError), but an empty/corrupt pid file makes
    int() raise ValueError, which crashed both `pid` and `running`."""

    def setUp(self):
        patcher = patch('solid_node.viewers.openscad.load_node',
                        return_value=MagicMock())
        patcher.start()
        self.addCleanup(patcher.stop)

        self.viewer = OpenScadViewer('fake/project.py')
        fh = tempfile.NamedTemporaryFile(delete=False)
        fh.close()
        self.viewer.pid_file = fh.name
        self.addCleanup(lambda: os.path.exists(fh.name) and os.remove(fh.name))

    def test_empty_pid_file_returns_none_without_raising(self):
        open(self.viewer.pid_file, 'w').write('')

        self.assertIsNone(self.viewer.pid)

    def test_empty_pid_file_running_is_falsy(self):
        open(self.viewer.pid_file, 'w').write('')

        self.assertFalse(self.viewer.running)


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
