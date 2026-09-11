# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""`solid develop`: a builder loop beside a viewer it does not own.

The web viewer is solid-node-viewer's `serve` command, launched with Popen
through this interpreter; the builder and the OpenSCAD viewer are spawned
children handed module-level targets. Whether the browser viewer is the
default depends on whether that package is installed. Every test here patches the lookup and
the process constructors, so the suite says the same thing with or without
the viewer present.
"""

import argparse
import io
import sys
from argparse import Namespace
from contextlib import redirect_stderr
from unittest import TestCase
from unittest.mock import patch, MagicMock, call

from solid_node.core.builder import BuildOutcome
from solid_node.manager.develop import Develop, run_builder, run_openscad_viewer
from solid_node.openscad import OpenScadUnavailable

VIEWER = [sys.executable, '-m', 'solid_node_viewer']
BUILD_DIR = '/work/project/_build'


def default_args(**overrides):
    values = dict(
        path='.',
        openscad=False,
        web=False,
        web_dev=False,
        debug_builder=False,
        no_web=False,
        callback=None,
    )
    values.update(overrides)
    return Namespace(**values)


class DevelopHarness(TestCase):
    """Patch the seams every scenario shares."""

    def setUp(self):
        self.develop = Develop()
        self.develop.parser = argparse.ArgumentParser()
        patches = [
            patch('solid_node.manager.develop.has_bundle', return_value=True),
            patch('solid_node.manager.develop.get_build_dir', return_value=BUILD_DIR),
            patch('solid_node.manager.develop.require_openscad'),
            patch('solid_node.manager.develop.Popen'),
            patch('solid_node.manager.develop.Process'),
        ]
        (self.has_bundle, self.get_build_dir, self.require_openscad,
         self.popen, self.process) = (p.start() for p in patches)
        for p in patches:
            self.addCleanup(p.stop)

    def builders(self, *exitcodes):
        """Builder processes ending in one whose join interrupts the loop."""
        instances = []
        for code in exitcodes:
            instance = MagicMock(exitcode=code)
            instance.join.return_value = None
            instances.append(instance)
        last = MagicMock()
        last.join.side_effect = KeyboardInterrupt
        instances.append(last)
        return instances

    def run_develop(self, args, *exitcodes, openscad=False):
        instances = self.builders(*exitcodes)
        if openscad:
            instances.insert(0, MagicMock())
        self.process.side_effect = instances
        with self.assertRaises(SystemExit):
            self.develop.handle(args)


class DefaultViewerTest(DevelopHarness):

    def test_the_web_viewer_is_the_default_when_installed(self):
        self.run_develop(default_args())
        self.popen.assert_called_once_with(
            VIEWER + ['serve', '--build-dir', BUILD_DIR])
        self.require_openscad.assert_not_called()

    def test_openscad_is_the_default_when_the_viewer_is_not_installed(self):
        self.has_bundle.return_value = False
        self.run_develop(default_args(), openscad=True)
        self.popen.assert_not_called()
        self.assertEqual(self.process.call_args_list[0], call(target=run_openscad_viewer, args=('.', [])))
        self.require_openscad.assert_called_once()

    def test_nothing_to_open_fails_before_any_process(self):
        self.has_bundle.return_value = False
        self.require_openscad.side_effect = OpenScadUnavailable('the OpenSCAD viewer', 'it launches OpenSCAD')
        with redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit):
            self.develop.handle(default_args())
        message = errors.getvalue()
        self.assertIn('pip install "solid-node[viewer]"', message)
        self.assertIn('OpenSCAD', message)
        self.popen.assert_not_called()
        self.process.assert_not_called()


class ExplicitViewerTest(DevelopHarness):

    def test_web_without_the_viewer_fails_naming_the_extra(self):
        self.has_bundle.return_value = False
        with redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit):
            self.develop.handle(default_args(web=True))
        self.assertIn('pip install "solid-node[viewer]"', errors.getvalue())
        self.popen.assert_not_called()
        self.process.assert_not_called()

    def test_openscad_alone_suppresses_the_web_viewer(self):
        self.run_develop(default_args(openscad=True), openscad=True)
        self.popen.assert_not_called()
        self.assertEqual(self.process.call_args_list[0], call(target=run_openscad_viewer, args=('.', [])))
        self.assertEqual(
            self.process.call_args_list[1],
            call(target=run_builder, args=('.', [], False, None, True)))

    def test_openscad_and_web_together_open_both(self):
        self.run_develop(default_args(openscad=True, web=True), openscad=True)
        self.popen.assert_called_once()
        self.assertEqual(self.process.call_args_list[0], call(target=run_openscad_viewer, args=('.', [])))

    def test_web_dev_asks_the_viewer_to_start_its_frontend(self):
        self.run_develop(default_args(web_dev=True))
        self.popen.assert_called_once_with(
            VIEWER + ['serve', '--build-dir', BUILD_DIR, '--start-frontend'])

    def test_debug_web_is_no_longer_an_option(self):
        parser = argparse.ArgumentParser()
        Develop().add_arguments(parser)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(['--debug-web'])


class OpenscadProcessStartedTest(DevelopHarness):
    """Regression for B4: `--openscad` once built the process and never
    started it, so the window never opened."""

    def test_openscad_process_is_constructed_and_started(self):
        openscad_instance = MagicMock()
        builder = MagicMock()
        builder.join.side_effect = KeyboardInterrupt
        self.process.side_effect = [openscad_instance, builder]
        with self.assertRaises(SystemExit):
            self.develop.handle(default_args(openscad=True))
        self.assertEqual(self.process.call_args_list[0], call(target=run_openscad_viewer, args=('.', [])))
        openscad_instance.start.assert_called_once()


class ViewerProcessLifecycleTest(DevelopHarness):

    def test_first_run_failure_tears_down_the_viewer_and_exits(self):
        builder = MagicMock(exitcode=1)
        builder.join.return_value = None
        self.process.side_effect = [builder]
        with self.assertRaises(SystemExit):
            self.develop.handle(default_args())
        self.assertEqual(self.process.call_args_list, [
            call(target=run_builder, args=('.', [], False, None, False)),
        ])
        web = self.popen.return_value
        web.terminate.assert_called_once()
        web.wait.assert_called()

    def test_the_viewer_restarts_after_each_rebuild(self):
        self.run_develop(default_args(), BuildOutcome.RENDERED.value)
        # Started once, restarted once after the completed build; the
        # interrupt that ends the loop terminates the second one too.
        self.assertEqual(self.popen.call_count, 2)
        self.assertEqual(self.popen.return_value.terminate.call_count, 2)

    def test_first_builder_invocation_is_not_flagged_as_reload(self):
        self.run_develop(default_args())
        self.assertEqual(self.process.call_args_list[0],
                         call(target=run_builder,
                              args=('.', [], False, None, False)))

    def test_second_builder_invocation_is_flagged_as_reload(self):
        self.run_develop(default_args(), 0)
        self.assertEqual(self.process.call_args_list[1],
                         call(target=run_builder,
                              args=('.', [], True, None, False)))

    def test_callback_is_passed_to_the_builder(self):
        self.run_develop(default_args(callback='http://listener/build-ready'))
        self.assertEqual(self.process.call_args_list[0], call(
            target=run_builder,
            args=('.', [], False, 'http://listener/build-ready', False),
        ))


class NoWebModeTest(DevelopHarness):
    """`--no-web` runs the builder watch loop alone, for a host that
    publishes its own view of the completed build directory."""

    def test_no_web_starts_the_builder_without_a_viewer(self):
        self.run_develop(default_args(no_web=True))
        self.popen.assert_not_called()
        self.assertEqual(self.process.call_args_list, [
            call(target=run_builder, args=('.', [], False, None, False)),
        ])

    def test_no_web_does_not_need_the_viewer_or_openscad(self):
        self.has_bundle.return_value = False
        self.require_openscad.side_effect = OpenScadUnavailable('the OpenSCAD viewer', 'it launches OpenSCAD')
        self.run_develop(default_args(no_web=True))
        self.assertEqual(self.process.call_count, 1)

    def test_no_web_passes_the_callback_to_the_builder(self):
        self.run_develop(default_args(no_web=True, callback='http://listener/build-ready'))
        self.assertEqual(self.process.call_args_list, [
            call(target=run_builder,
                 args=('.', [], False, 'http://listener/build-ready', False)),
        ])

    def test_no_web_reload_cycle_does_not_restart_a_viewer(self):
        self.run_develop(default_args(no_web=True), BuildOutcome.SOURCE_CHANGED.value)
        self.popen.assert_not_called()
        self.assertEqual(self.process.call_args_list, [
            call(target=run_builder, args=('.', [], False, None, False)),
            call(target=run_builder, args=('.', [], True, None, False)),
        ])

    def test_no_web_rejects_an_explicit_web_request(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.develop.handle(default_args(no_web=True, web_dev=True))
        self.popen.assert_not_called()
