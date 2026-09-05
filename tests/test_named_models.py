# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A project that declares several models by name.

One repository, one shared library, one model per machine -- the shape of
`3DPrintedClocks`, where every clock is a model under `design/` and all of
them import the same `clocks` package above. A manifest names those models
in `[tool.solid-node.models]`; each name is a reference; each model owns a
build directory of its own under the build root, so publishing one never
sweeps another; `solid models` lists them; `--all` walks them.

The fixture is a real CadQuery project in a directory each test owns,
because the proof that two models do not disturb each other is a
filesystem proof.
"""

import asyncio
import io
import itertools
import json
import os
import shutil
import sys
import tempfile
from argparse import Namespace
from contextlib import chdir, redirect_stderr, redirect_stdout
from unittest import TestCase
from unittest.mock import MagicMock, patch

from solid_node.core.builder import (
    Builder, BuildOutcome, get_build_dir, get_build_lock_path,
    unanchor_build_dir,
)
from solid_node.core.loader import (
    ProjectManifestError, discover_project, read_project, resolve_node,
    select_model,
)
from solid_node.manager.build import Build, MODEL_NOT_FOUND, build_once


PROJECT_NAMES = itertools.count()

SHARED = '''\
SIZE = 3.0
'''

CLOCK = '''\
import cadquery as cq

from solid_node.node import AssemblyNode, CadQueryNode

from ..shared import SIZE


class Plate(CadQueryNode):

    def render(self):
        return cq.Workplane('XY').box(SIZE, SIZE, {height})


class {klass}(AssemblyNode):

    def __init__(self):
        self.plate = Plate()
        super().__init__()

    def render(self):
        return [self.plate]
'''

COMPANION = '''\
from solid_node.test import TestCase

from .clock import {klass}


class ClockTest(TestCase):
    node = {klass}

    def test_it_has_a_plate(self):
        self.assertIsNotNone(self.node.plate)
'''


class NamedProjectTest(TestCase):
    """Two clocks, `a_clock` and `b_clock`, sharing one module."""

    def setUp(self):
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop('SOLID_BUILD_DIR', None)
        self.addCleanup(unanchor_build_dir)

        self.root = os.path.realpath(
            tempfile.mkdtemp(prefix='solid-node-named-'))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.package = f'named_fixture_{next(PROJECT_NAMES)}'
        self.addCleanup(self.forget_project)
        package_dir = os.path.join(self.root, self.package)
        os.makedirs(package_dir)
        open(os.path.join(package_dir, '__init__.py'), 'w').close()
        with open(os.path.join(package_dir, 'shared.py'), 'w') as source:
            source.write(SHARED)
        for name, klass, height in (('a_clock', 'AClock', 1.0),
                                    ('b_clock', 'BClock', 2.0)):
            model_dir = os.path.join(package_dir, name)
            os.makedirs(model_dir)
            open(os.path.join(model_dir, '__init__.py'), 'w').close()
            with open(os.path.join(model_dir, 'clock.py'), 'w') as source:
                source.write(CLOCK.format(klass=klass, height=height))
            with open(os.path.join(model_dir, 'test_clock.py'), 'w') as source:
                source.write(COMPANION.format(klass=klass))
        # A directory at the project root, for the name-collision rule.
        os.makedirs(os.path.join(self.root, 'docs'))
        self.write_manifest()
        self.build_root = os.path.join(self.root, '_build')

    def write_manifest(self, default='model = "a_clock"\n', extra=''):
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as manifest:
            manifest.write(
                '[tool.solid-node]\n' + default +
                '\n[tool.solid-node.models]\n'
                f'a_clock = "{self.package}.a_clock.clock:AClock"\n'
                f'b_clock = "{self.package}.b_clock.clock:BClock"\n' + extra)

    def reference(self, name):
        klass = {'a_clock': 'AClock', 'b_clock': 'BClock'}[name]
        return f'{self.package}.{name}.clock:{klass}'

    def forget_project(self):
        for name in list(sys.modules):
            if name == self.package or name.startswith(self.package + '.'):
                del sys.modules[name]

    def publish(self, reference, build_dir):
        """A complete build through the builder that publishes and sweeps."""
        self.forget_project()
        with chdir(self.root):
            builder = Builder(reference, build_dir=build_dir, watch=False)
            outcome = asyncio.run(builder._start())
        self.assertEqual(outcome, BuildOutcome.CURRENT)
        return builder

    def stls(self, directory):
        found = set()
        for folder, _, names in os.walk(directory):
            for name in names:
                if name.endswith('.stl'):
                    found.add(os.path.relpath(os.path.join(folder, name),
                                              directory))
        return found


class ManifestTest(NamedProjectTest):
    """Task 1.2: what the manifest declares, and what it may not."""

    def test_declares_two_models_and_a_default(self):
        with chdir(self.root):
            project = read_project()
        self.assertEqual([model.name for model in project.models],
                         ['a_clock', 'b_clock'])
        self.assertEqual([model.reference for model in project.models],
                         [self.reference('a_clock'), self.reference('b_clock')])
        self.assertEqual(project.default.name, 'a_clock')
        self.assertEqual(
            [model.build_dir for model in project.models],
            [os.path.join(self.build_root, 'a_clock'),
             os.path.join(self.build_root, 'b_clock')])
        self.assertEqual(project.root, self.root)

    def test_discover_project_reports_the_defaults_reference(self):
        """The `(root, reference)` contract every existing caller has."""
        with chdir(self.root):
            self.assertEqual(discover_project(),
                             (self.root, self.reference('a_clock')))

    def test_a_declared_name_resolves_to_its_class(self):
        with chdir(os.path.join(self.root, self.package)):
            klass, path, root = resolve_node('b_clock')
        self.assertEqual(klass.__name__, 'BClock')
        self.assertEqual(root, self.root)
        self.assertTrue(path.endswith(os.path.join('b_clock', 'clock.py')))

    def test_a_bare_word_that_is_not_a_name_is_a_qualifier(self):
        with chdir(self.root):
            # Read as the module `c_clock`, which does not exist -- not as
            # a missing model name.
            with self.assertRaises(ModuleNotFoundError):
                resolve_node('c_clock')

    def test_default_must_name_a_declared_model(self):
        self.write_manifest(default=f'model = "{self.reference("a_clock")}"\n')
        with chdir(self.root):
            with self.assertRaises(ProjectManifestError) as error:
                read_project()
        message = str(error.exception)
        self.assertIn('pyproject.toml', message)
        self.assertIn('a_clock', message)
        self.assertIn('b_clock', message)

    def test_an_empty_table_is_refused(self):
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as manifest:
            manifest.write('[tool.solid-node]\n[tool.solid-node.models]\n')
        with chdir(self.root):
            with self.assertRaises(ProjectManifestError) as error:
                read_project()
        self.assertIn('pyproject.toml', str(error.exception))

    def test_a_malformed_name_is_refused(self):
        self.write_manifest(extra=f'"design.c" = "{self.reference("a_clock")}"\n')
        with chdir(self.root):
            with self.assertRaises(ProjectManifestError) as error:
                read_project()
        self.assertIn('design.c', str(error.exception))

    def test_a_name_equal_to_a_root_directory_is_refused(self):
        self.write_manifest(extra=f'docs = "{self.reference("a_clock")}"\n')
        with chdir(self.root):
            with self.assertRaises(ProjectManifestError) as error:
                read_project()
        message = str(error.exception)
        self.assertIn('docs', message)
        self.assertIn('pyproject.toml', message)

    def test_a_single_model_manifest_is_unchanged(self):
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as manifest:
            manifest.write('[tool.solid-node]\n'
                           f'model = "{self.reference("a_clock")}"\n')
        with chdir(self.root):
            project = read_project()
            self.assertEqual(discover_project(),
                             (self.root, self.reference('a_clock')))
        self.assertFalse(project.named)
        self.assertEqual(len(project.models), 1)
        self.assertIsNone(project.models[0].name)
        self.assertEqual(project.models[0].build_dir, self.build_root)
        self.assertIs(project.default, project.models[0])


class SelectionTest(NamedProjectTest):
    """Task 1.3: a reference, or none, names a model and its directory."""

    def test_a_declared_name_selects_its_directory(self):
        with chdir(self.root):
            selection = select_model('b_clock')
        self.assertEqual(selection.reference, self.reference('b_clock'))
        self.assertEqual(selection.build_dir,
                         os.path.join(self.build_root, 'b_clock'))

    def test_no_reference_selects_the_default(self):
        with chdir(os.path.join(self.root, self.package)):
            selection = select_model()
        self.assertEqual(selection.reference, self.reference('a_clock'))
        self.assertEqual(selection.build_dir,
                         os.path.join(self.build_root, 'a_clock'))

    def test_a_sub_node_reference_builds_in_the_root(self):
        with chdir(self.root):
            selection = select_model(f'{self.package}.a_clock.clock:Plate')
            selection.anchor()
            self.assertEqual(get_build_dir(), self.build_root)
        self.assertEqual(selection.reference,
                         f'{self.package}.a_clock.clock:Plate')

    def test_anchoring_moves_the_build_directory_for_this_process(self):
        with chdir(self.root):
            select_model('b_clock').anchor()
            self.assertEqual(get_build_dir(),
                             os.path.join(self.build_root, 'b_clock'))
            self.assertEqual(os.environ['SOLID_BUILD_DIR'],
                             os.path.join(self.build_root, 'b_clock'))
            # A second selection in the same process starts from the
            # project's root again, not from the anchored directory.
            select_model('a_clock').anchor()
            self.assertEqual(get_build_dir(),
                             os.path.join(self.build_root, 'a_clock'))

    def test_no_reference_and_no_default_lists_the_names(self):
        self.write_manifest(default='')
        with chdir(self.root):
            with self.assertRaises(ProjectManifestError) as error:
                select_model()
            with self.assertRaises(ProjectManifestError):
                resolve_node()
        message = str(error.exception)
        self.assertIn('a_clock', message)
        self.assertIn('b_clock', message)


class PerModelBuildDirectoryTest(NamedProjectTest):
    """Task 1.4: each model publishes on its own."""

    def test_two_models_publish_side_by_side(self):
        a_dir = os.path.join(self.build_root, 'a_clock')
        b_dir = os.path.join(self.build_root, 'b_clock')

        self.publish(self.reference('a_clock'), a_dir)
        a_stls = self.stls(a_dir)
        self.assertTrue(a_stls)
        with open(os.path.join(a_dir, 'viewer.json')) as published:
            a_document = published.read()

        self.publish(self.reference('b_clock'), b_dir)

        self.assertEqual(self.stls(a_dir), a_stls,
                         "building the second model touched the first's")
        with open(os.path.join(a_dir, 'viewer.json')) as published:
            self.assertEqual(published.read(), a_document)
        self.assertTrue(self.stls(b_dir))
        with open(os.path.join(b_dir, 'viewer.json')) as published:
            for model in self._models(json.load(published)['root']):
                self.assertTrue(os.path.isfile(os.path.join(b_dir, model)))
                self.assertFalse(model.startswith('..'))

    def test_declared_models_do_not_share_a_lock(self):
        a_dir = os.path.join(self.build_root, 'a_clock')
        b_dir = os.path.join(self.build_root, 'b_clock')
        self.assertNotEqual(get_build_lock_path(a_dir),
                            get_build_lock_path(b_dir))
        self.assertEqual(get_build_lock_path(a_dir),
                         os.path.join(self.build_root, 'a_clock.lock'))

    def test_a_sub_node_build_does_not_sweep_the_models(self):
        a_dir = os.path.join(self.build_root, 'a_clock')
        self.publish(self.reference('a_clock'), a_dir)
        a_stls = self.stls(a_dir)
        lock = get_build_lock_path(a_dir)
        open(lock, 'a').close()

        self.publish(f'{self.package}.b_clock.clock:Plate', self.build_root)

        self.assertTrue(os.path.isfile(os.path.join(self.build_root,
                                                    'viewer.json')))
        self.assertEqual(self.stls(a_dir), a_stls,
                         'the root sweep reached into a model directory')
        self.assertTrue(os.path.isfile(lock),
                        'the root sweep removed a model lock')

    def _models(self, node):
        if 'model' in node:
            yield node['model']
        for child in node.get('children', []):
            yield from self._models(child)


class BuildCommandTest(NamedProjectTest):
    """Task 1.5: `solid build <name>`, the default, and `--all`."""

    def build(self, path=None, all_models=False, outcomes=(BuildOutcome.CURRENT,)):
        processes = [MagicMock(exitcode=outcome.value) for outcome in outcomes]
        stderr = io.StringIO()
        with chdir(self.root), redirect_stderr(stderr), \
                patch('solid_node.manager.build.Process',
                      side_effect=processes) as process:
            code = None
            try:
                Build().handle(Namespace(path=path, set=[], all=all_models))
            except SystemExit as exit:
                code = exit.code
        return code, process, stderr.getvalue()

    def test_a_name_builds_its_reference_in_its_directory(self):
        code, process, _ = self.build('b_clock')
        self.assertIsNone(code)
        self.assertEqual(process.call_args.kwargs['args'],
                         (self.reference('b_clock'), []))
        self.assertEqual(os.environ['SOLID_BUILD_DIR'],
                         os.path.join(self.build_root, 'b_clock'))

    def test_no_reference_builds_the_default(self):
        code, process, _ = self.build()
        self.assertIsNone(code)
        self.assertEqual(process.call_args.kwargs['args'],
                         (self.reference('a_clock'), []))
        self.assertEqual(os.environ['SOLID_BUILD_DIR'],
                         os.path.join(self.build_root, 'a_clock'))

    def test_no_reference_and_no_default_is_model_not_found(self):
        self.write_manifest(default='')
        code, process, stderr = self.build()
        self.assertEqual(code, MODEL_NOT_FOUND)
        self.assertFalse(process.called)
        self.assertIn('a_clock', stderr)
        self.assertIn('b_clock', stderr)

    def test_all_walks_every_model_in_order(self):
        anchored = []
        real_process = MagicMock(exitcode=BuildOutcome.CURRENT.value)

        def process(target, args):
            anchored.append((args[0], os.environ['SOLID_BUILD_DIR']))
            return real_process

        stderr = io.StringIO()
        with chdir(self.root), redirect_stderr(stderr), \
                patch('solid_node.manager.build.Process', side_effect=process):
            with self.assertRaises(SystemExit) as exit:
                Build().handle(Namespace(path=None, set=[], all=True))
        self.assertEqual(exit.exception.code, 0)
        self.assertEqual(anchored, [
            (self.reference('a_clock'), os.path.join(self.build_root, 'a_clock')),
            (self.reference('b_clock'), os.path.join(self.build_root, 'b_clock')),
        ])
        self.assertIn('a_clock', stderr.getvalue())
        self.assertIn('b_clock', stderr.getvalue())

    def test_all_continues_past_a_failing_model(self):
        code, process, stderr = self.build(
            all_models=True,
            outcomes=(BuildOutcome.FAILED, BuildOutcome.CURRENT))
        self.assertEqual(code, 1)
        self.assertEqual(process.call_count, 2)
        self.assertIn('a_clock', stderr)
        self.assertIn('b_clock', stderr)
        self.assertIn('failed', stderr)

    def test_all_takes_no_reference(self):
        code, process, _ = self.build('a_clock', all_models=True)
        self.assertEqual(code, 2)
        self.assertFalse(process.called)

    def test_all_in_a_single_model_project_is_refused(self):
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as manifest:
            manifest.write('[tool.solid-node]\n'
                           f'model = "{self.reference("a_clock")}"\n')
        code, process, stderr = self.build(all_models=True)
        self.assertEqual(code, 1)
        self.assertFalse(process.called)
        self.assertIn('declares no models', stderr)


class TestCommandTest(NamedProjectTest):
    """Task 1.6: `solid test --all` is one run over every model."""

    def test_all_runs_every_models_tests_as_one_run(self):
        from solid_node.manager.test import Test
        stdout = io.StringIO()
        self.forget_project()
        with chdir(self.root), redirect_stdout(stdout):
            code = None
            try:
                Test().handle(Namespace(path=None, set=[], all=True,
                                        failfast=False))
            except SystemExit as exit:
                code = exit.code
        self.assertIsNone(code, stdout.getvalue())
        self.assertIn('Ran 2 tests', stdout.getvalue())
        self.assertIn('2 passed', stdout.getvalue())
        self.assertTrue(self.stls(os.path.join(self.build_root, 'a_clock')))
        self.assertTrue(self.stls(os.path.join(self.build_root, 'b_clock')))
        self.assertEqual(self.stls(self.build_root)
                         - {path for path in self.stls(self.build_root)
                            if path.startswith(('a_clock', 'b_clock'))},
                         set(), 'a model built into the flat root')


class ModelsCommandTest(NamedProjectTest):
    """Task 1.7: `solid models` lists without importing the project."""

    def models(self, as_json=True):
        from solid_node.manager.models import Models
        stdout = io.StringIO()
        with chdir(self.root), redirect_stdout(stdout):
            Models().handle(Namespace(json=as_json))
        return json.loads(stdout.getvalue()) if as_json else stdout.getvalue()

    def test_lists_both_models_with_their_state(self):
        a_dir = os.path.join(self.build_root, 'a_clock')
        os.makedirs(a_dir)
        open(os.path.join(a_dir, 'viewer.json'), 'w').close()

        report = self.models()

        self.assertEqual(report['root'], self.root)
        self.assertEqual(report['build_root'], self.build_root)
        self.assertEqual(report['default'], 'a_clock')
        self.assertEqual(report['models'], [
            {'name': 'a_clock', 'reference': self.reference('a_clock'),
             'default': True, 'build_dir': a_dir, 'state': 'published'},
            {'name': 'b_clock', 'reference': self.reference('b_clock'),
             'default': False,
             'build_dir': os.path.join(self.build_root, 'b_clock'),
             'state': 'unbuilt'},
        ])
        self.assertNotIn(self.package, sys.modules)

    def test_a_failed_model_is_reported(self):
        b_dir = os.path.join(self.build_root, 'b_clock')
        os.makedirs(b_dir)
        open(os.path.join(b_dir, 'viewer.json'), 'w').close()
        open(os.path.join(b_dir, 'errors.json'), 'w').close()
        states = {model['name']: model['state']
                  for model in self.models()['models']}
        self.assertEqual(states, {'a_clock': 'unbuilt', 'b_clock': 'failed'})

    def test_text_lists_in_declaration_order(self):
        text = self.models(as_json=False)
        self.assertLess(text.index('a_clock'), text.index('b_clock'))
        self.assertIn('unbuilt', text)
        self.assertIn('default', text)

    def test_a_single_model_project_lists_one_entry(self):
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as manifest:
            manifest.write('[tool.solid-node]\n'
                           f'model = "{self.reference("a_clock")}"\n')
        report = self.models()
        self.assertIsNone(report['default'])
        self.assertEqual(report['models'], [
            {'name': None, 'reference': self.reference('a_clock'),
             'default': True, 'build_dir': self.build_root,
             'state': 'unbuilt'},
        ])

    def test_a_malformed_manifest_is_reported(self):
        from solid_node.manager.models import Models
        self.write_manifest(extra=f'docs = "{self.reference("a_clock")}"\n')
        stdout, stderr = io.StringIO(), io.StringIO()
        with chdir(self.root), redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as exit:
                Models().handle(Namespace(json=True))
        self.assertEqual(exit.exception.code, 1)
        self.assertEqual(stdout.getvalue(), '')
        self.assertIn('docs', stderr.getvalue())

    def test_models_is_a_registered_command(self):
        from solid_node.cli import COMMANDS
        self.assertIn('models', COMMANDS)


class BrokenModelTest(NamedProjectTest):
    """A model whose module does not import is that model's failure."""

    def setUp(self):
        super().setUp()
        with open(os.path.join(self.root, self.package, 'a_clock', 'clock.py'),
                  'w') as source:
            source.write('from solid_node.node import NoSuchThing\n')

    def test_build_all_reports_it_and_goes_on(self):
        current = MagicMock(exitcode=BuildOutcome.CURRENT.value)
        stderr = io.StringIO()
        self.forget_project()
        with chdir(self.root), redirect_stderr(stderr), \
                patch('solid_node.manager.build.Process',
                      return_value=current) as process:
            with self.assertRaises(SystemExit) as exit:
                Build().handle(Namespace(path=None, set=[], all=True))
        self.assertEqual(exit.exception.code, 1)
        self.assertEqual(process.call_args.kwargs['args'],
                         (self.reference('b_clock'), []))
        self.assertIn('a_clock', stderr.getvalue())
        self.assertIn('NoSuchThing', stderr.getvalue())
        self.assertTrue(os.path.isfile(os.path.join(
            self.build_root, 'a_clock', 'errors.json')))

    def test_test_all_counts_it_and_goes_on(self):
        from solid_node.manager.test import Test
        stdout, stderr = io.StringIO(), io.StringIO()
        self.forget_project()
        with chdir(self.root), redirect_stdout(stdout), redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as exit:
                Test().handle(Namespace(path=None, set=[], all=True,
                                        failfast=False))
        self.assertEqual(exit.exception.code, 1)
        self.assertIn('Ran 2 tests', stdout.getvalue())
        self.assertIn('1 failed', stdout.getvalue())
        self.assertIn('a_clock', stderr.getvalue())
