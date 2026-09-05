# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Root parameter overrides from the command line.

`--set name=value` is what makes a design parametric for a maker rather
than only for a Python caller. The value is parsed by the declared kind
and checked by the declared constraints, so the shell has exactly the
door Python has; an unknown name lists what can be set; a root that
declares nothing refuses the flag; and the develop loop carries the
overrides into every rebuild.
"""

import io
import os
import sys
from argparse import Namespace
from contextlib import redirect_stderr
from unittest import TestCase
from unittest.mock import MagicMock, patch

from solid_node.cli import manage
from solid_node.core.loader import load_node, parse_overrides
from solid_node.manager.build import Build, build_once
from solid_node.manager.develop import Develop, run_builder
from solid_node.parameters import ParameterError

from .base import BASEDIR, BaseNodeTest
from .declarative_project.engine import Engine
from .declarative_project.parts import Tower
from .declarative_project.windmill import Windmill
from .flat_project.simple_cylinder import SimpleCylinder

ENGINE = os.path.join(BASEDIR, 'declarative_project', 'engine.py:Engine')
WINDMILL = os.path.join(BASEDIR, 'declarative_project', 'windmill.py')
TOWER = os.path.join(BASEDIR, 'declarative_project', 'parts.py:Tower')


class ParseOverridesTest(TestCase):

    def test_values_are_parsed_by_kind(self):
        overrides = parse_overrides(Engine, ['bore=32.5', 'count=6'])
        self.assertEqual(overrides, {'bore': 32.5, 'count': 6})
        self.assertIs(type(overrides['count']), int)

        flags = parse_overrides(Windmill, ['guard_installed=false'])
        self.assertIs(flags['guard_installed'], False)
        self.assertIs(parse_overrides(
            Windmill, ['guard_installed=true'])['guard_installed'], True)

    def test_a_value_the_kind_refuses(self):
        with self.assertRaises(ParameterError) as ctx:
            parse_overrides(Engine, ['count=2.5'])
        self.assertIn('count', str(ctx.exception))
        with self.assertRaises(ParameterError) as ctx:
            parse_overrides(Windmill, ['guard_installed=maybe'])
        self.assertIn('true', str(ctx.exception))
        self.assertIn('false', str(ctx.exception))
        with self.assertRaises(ParameterError):
            parse_overrides(Engine, ['bore=wide'])

    def test_an_unknown_name_lists_the_settable(self):
        with self.assertRaises(ParameterError) as ctx:
            parse_overrides(Engine, ['boar=32.0'])
        message = str(ctx.exception)
        self.assertIn('boar', message)
        self.assertIn('bore', message)
        self.assertIn('count', message)

    def test_a_derived_name_is_not_settable(self):
        with self.assertRaises(ParameterError) as ctx:
            parse_overrides(Windmill, ['rotor_radius=100'])
        self.assertIn('derived', str(ctx.exception))

    def test_a_root_that_declares_nothing_refuses_the_flag(self):
        with self.assertRaises(ParameterError) as ctx:
            parse_overrides(SimpleCylinder, ['radius=2'])
        self.assertIn('SimpleCylinder', str(ctx.exception))

    def test_a_malformed_pair(self):
        with self.assertRaises(ParameterError):
            parse_overrides(Engine, ['bore'])
        self.assertEqual(parse_overrides(Engine, []), {})


class LoaderOverridesTest(BaseNodeTest):

    def test_a_build_at_another_bore(self):
        engine = load_node(ENGINE, overrides=['bore=32.0', 'count=4'])

        self.assertEqual(engine.bore, 32.0)
        self.assertEqual(len(engine.cylinders.units), 4)
        self.assertEqual(engine.block.bore, 32.0)
        self.assertNotEqual(engine.block.uniq_id, Engine().block.uniq_id)

    def test_a_constraint_from_the_shell(self):
        with self.assertRaises(ParameterError) as ctx:
            load_node(ENGINE, overrides=['count=1'])
        self.assertIn('count', str(ctx.exception))

    def test_a_node_without_a_default_loaded_directly(self):
        with self.assertRaises(ParameterError) as ctx:
            load_node(TOWER)
        self.assertIn('Tower', str(ctx.exception))
        self.assertIn('height', str(ctx.exception))

        tower = load_node(TOWER, overrides=['height=300'])
        # The loader imports by the project's dotted name, so the class
        # is a different object from this test module's import of it.
        self.assertEqual(type(tower).__name__, Tower.__name__)
        self.assertEqual(tower.height, 300.0)

    def test_no_overrides_loads_as_before(self):
        self.assertEqual(load_node(ENGINE).bore, 30.0)
        self.assertEqual(load_node(ENGINE, overrides=[]).bore, 30.0)


class CliFlagTest(TestCase):
    """`--set` is registered once beside the shared reference positional,
    so every node-scoped command has it and the others do not."""

    def test_every_node_command_accepts_set(self):
        for command, handler in (
                ('build', 'solid_node.manager.build.Build.handle'),
                ('develop', 'solid_node.manager.develop.Develop.handle'),
                ('export', 'solid_node.manager.export.Export.handle'),
                ('test', 'solid_node.manager.test.Test.handle'),
                ('snapshot', 'solid_node.manager.snapshot.Snapshot.handle')):
            argv = ['solid', command, 'model.py',
                    '--set', 'bore=32.0', '--set', 'count=6']
            with patch.object(sys, 'argv', argv), patch(handler) as handle:
                manage()
            args = handle.call_args[0][0]
            self.assertEqual(args.set, ['bore=32.0', 'count=6'], command)

    def test_the_flag_defaults_to_nothing(self):
        with patch.object(sys, 'argv', ['solid', 'build', 'model.py']), \
                patch('solid_node.manager.build.Build.handle') as handle:
            manage()
        self.assertEqual(handle.call_args[0][0].set, [])

    def test_commands_without_a_node_reject_it(self):
        stderr = io.StringIO()
        with patch.object(sys, 'argv', ['solid', 'viewer', '--set', 'a=1']), \
                redirect_stderr(stderr), self.assertRaises(SystemExit) as ctx:
            manage()
        self.assertEqual(ctx.exception.code, 2)


class ManagerOverridesTest(TestCase):

    def test_build_passes_overrides_to_the_builder(self):
        command = Build()
        command.path = 'model.py'
        command.overrides = ['bore=32.0']

        with patch('solid_node.manager.build.Builder') as builder:
            build_once(command.path, command.overrides)

        self.assertEqual(builder.call_args.kwargs['overrides'], ['bore=32.0'])
        self.assertEqual(builder.call_args.args[0], 'model.py')

    def test_build_handle_records_the_overrides(self):
        command = Build()
        current = MagicMock(exitcode=0)
        with patch('solid_node.manager.build.resolve_node'), \
                patch('solid_node.manager.build.Process',
                      return_value=current):
            command.handle(Namespace(path='model.py', set=['bore=32.0']))
        self.assertEqual(command.overrides, ['bore=32.0'])

    def test_develop_carries_overrides_into_every_builder(self):
        develop = Develop()
        develop.path = 'model.py'
        develop.overrides = ['bore=32.0']

        with patch('solid_node.manager.develop.Builder') as builder:
            run_builder(develop.path, develop.overrides, is_reload=True)

        self.assertEqual(builder.call_args.kwargs['overrides'], ['bore=32.0'])
        self.assertTrue(builder.call_args.kwargs['is_reload'])

    def test_develop_handle_records_the_overrides(self):
        develop = Develop()
        builder_instance = MagicMock()
        builder_instance.join.side_effect = KeyboardInterrupt
        args = Namespace(path='model.py', set=['bore=32.0'], openscad=False,
                         web=False, web_dev=False, debug_builder=False,
                         debug_web=False, no_web=True, callback=None)

        with patch('solid_node.manager.develop.Process',
                   return_value=builder_instance), \
                self.assertRaises(SystemExit):
            develop.handle(args)

        self.assertEqual(develop.overrides, ['bore=32.0'])

    def test_the_builder_loads_with_its_overrides(self):
        from solid_node.core.builder import Builder
        builder = Builder('model.py', watch=False, overrides=['bore=32.0'])
        self.assertEqual(builder.overrides, ['bore=32.0'])
