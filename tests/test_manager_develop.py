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


def default_args(**overrides):
    values = dict(
        path='.',
        openscad=False,
        web=False,
        web_dev=False,
        debug_builder=False,
        debug_web=False,
    )
    values.update(overrides)
    return Namespace(**values)


class StartupFailureExitsCleanlyTest(TestCase):
    """Regression for improvements.md #7: a project already broken at
    `solid develop` launch used to leave the builder subprocess hung
    forever (no observer had started yet to notice a later fix), so
    the develop command never came back and never exited either.

    Only the very first builder attempt is "startup" and must fail
    fast: if it exits non-zero, `handle()` must tear down the other
    processes it started and exit -- not loop around treating the next
    attempt as a recoverable reload.
    """

    def test_first_run_failure_tears_down_other_processes_and_exits(self):
        develop = Develop()
        args = default_args()

        web_instance = MagicMock()
        builder_instance = MagicMock()
        builder_instance.join.return_value = None
        builder_instance.exitcode = 1

        with patch('solid_node.manager.develop.Process',
                   side_effect=[web_instance, builder_instance]) as mock_process:
            with self.assertRaises(SystemExit):
                develop.handle(args)

        self.assertEqual(mock_process.call_args_list, [
            call(target=develop.web),
            call(target=develop.builder, args=(False,)),
        ])
        web_instance.terminate.assert_called_once()
        web_instance.join.assert_called()


class ReloadFlagPassedOnSubsequentBuildsTest(TestCase):
    """Every builder_proc after the very first one is a WATCH-LOOP
    reload; only that path may treat an import failure as recoverable
    (Builder.is_reload), so Develop must tell it apart from startup."""

    def test_first_builder_invocation_is_not_flagged_as_reload(self):
        develop = Develop()
        args = default_args()

        web_instance = MagicMock()
        builder_instance = MagicMock(exitcode=0)
        builder_instance.join.side_effect = KeyboardInterrupt

        with patch('solid_node.manager.develop.Process',
                   side_effect=[web_instance, builder_instance]) as mock_process:
            with self.assertRaises(SystemExit):
                develop.handle(args)

        self.assertEqual(mock_process.call_args_list[1],
                          call(target=develop.builder, args=(False,)))

    def test_second_builder_invocation_is_flagged_as_reload(self):
        develop = Develop()
        args = default_args()

        web_instance = MagicMock()
        builder_1 = MagicMock(exitcode=0)
        builder_1.join.return_value = None
        builder_2 = MagicMock()
        builder_2.join.side_effect = KeyboardInterrupt

        with patch('solid_node.manager.develop.Process',
                   side_effect=[web_instance, builder_1, web_instance, builder_2]) as mock_process:
            with self.assertRaises(SystemExit):
                develop.handle(args)

        self.assertEqual(mock_process.call_args_list[1],
                          call(target=develop.builder, args=(False,)))
        self.assertEqual(mock_process.call_args_list[3],
                          call(target=develop.builder, args=(True,)))
