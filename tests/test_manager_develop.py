# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

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
