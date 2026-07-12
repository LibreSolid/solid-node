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

from argparse import Namespace
from unittest import TestCase
from unittest.mock import patch, MagicMock, call
from solid_node.manager.develop import Develop


class OpenscadProcessStartedTest(TestCase):
    """Regression test for B4: `--openscad` built
    `Process(target=self.openscad)` but never called `.start()` on it, so
    the OpenSCAD viewer process was constructed and immediately discarded --
    the viewer window never opened.
    """

    def test_openscad_process_is_constructed_and_started(self):
        develop = Develop()
        args = Namespace(
            path='.',
            openscad=True,
            web=False,
            web_dev=False,
            debug_builder=False,
            debug_web=False,
        )

        openscad_instance = MagicMock()
        builder_instance = MagicMock()
        # Ends the otherwise-infinite builder loop, mirroring how a real
        # KeyboardInterrupt during builder_proc.join() causes handle() to
        # exit via sys.exit(0).
        builder_instance.join.side_effect = KeyboardInterrupt

        with patch('solid_node.manager.develop.Process',
                   side_effect=[openscad_instance, builder_instance]) as mock_process:
            with self.assertRaises(SystemExit):
                develop.handle(args)

        self.assertEqual(mock_process.call_args_list[0], call(target=develop.openscad))
        openscad_instance.start.assert_called_once()
