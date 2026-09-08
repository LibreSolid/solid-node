# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The source identity represented by live project classes.

These tests use tiny temporary projects because their purpose is to replace
source while it is being imported.  No repository fixture is mutated.
"""

import os
import py_compile
import shutil
import sys
import tempfile
import time
from contextlib import chdir
from importlib import import_module
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from subprocess import CalledProcessError
from types import SimpleNamespace
from unittest import TestCase, mock

from solid_node import currency
from solid_node.core.builder import Builder, BuildOutcome
from solid_node.core.loader import load_node, project_source_generation
from solid_node.node import JScadNode
from solid_node.node.base import StlRenderStart
from solid_node.source_generation import SourceChanged, SourceGeneration


MODEL = '''\
from solid2 import cube
from solid_node.node import Solid2Node
from .dimensions import VALUE


class Model(Solid2Node):
    loaded_value = VALUE

    def render(self):
        return cube(VALUE)
'''


class ScratchLoadProject(TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='solid-node-generation-')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.package = f'generation_fixture_{os.getpid()}_{id(self)}'
        self.package_dir = os.path.join(self.root, self.package)
        os.mkdir(self.package_dir)
        self.write('__init__.py', '')
        self.write('dimensions.py', 'VALUE = 1\n')
        self.write('model.py', MODEL)
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as manifest:
            manifest.write('[tool.solid-node]\n'
                           f'model = "{self.package}.model:Model"\n')
        self.reference = f'{self.package}.model:Model'
        self.dimensions = os.path.join(self.package_dir, 'dimensions.py')
        self.addCleanup(self.forget_project)

    def write(self, name, content):
        path = os.path.join(self.package_dir, name)
        with open(path, 'w') as source:
            source.write(content)
        return path

    def forget_project(self):
        for name in list(sys.modules):
            if name == self.package or name.startswith(self.package + '.'):
                del sys.modules[name]
        while self.root in sys.path:
            sys.path.remove(self.root)

    def load_generation(self):
        with chdir(self.root), project_source_generation(
                self.reference) as generation:
            node = load_node(self.reference, generation=generation)
        return node


class FreshProjectBytecodeTest(ScratchLoadProject):

    def test_same_size_restored_mtime_source_bypasses_timestamp_pyc(self):
        """A valid timestamp pyc must not decide project source freshness."""
        bytecode = py_compile.compile(self.dimensions, doraise=True)
        self.assertTrue(os.path.isfile(bytecode), 'fixture produced no bytecode')
        old_mtime = os.stat(self.dimensions).st_mtime_ns

        self.forget_project()
        self.write('dimensions.py', 'VALUE = 2\n')
        os.utime(self.dimensions, ns=(old_mtime, old_mtime))

        # The ordinary Python loader demonstrates the real counterexample:
        # timestamp-and-size validation executes the old bytecode.
        with chdir(self.root):
            stale = load_node(self.reference)
        self.assertEqual(stale.loaded_value, 1)
        self.forget_project()

        self.assertEqual(self.load_generation().loaded_value, 2)

    def test_atomic_replacement_after_read_rejects_old_live_classes(self):
        """Post-load disk identity cannot bless bytes read before replacement."""
        import solid_node.source_generation as source_generation

        original = source_generation._coherent_source_bytes
        replaced = False

        def replacing(path):
            nonlocal replaced
            data, observation = original(path)
            if os.path.realpath(path) == os.path.realpath(self.dimensions):
                replacement = os.path.join(self.package_dir, '.dimensions.py')
                with open(replacement, 'w') as source:
                    source.write('VALUE = 2\n')
                os.replace(replacement, self.dimensions)
                replaced = True
            return data, observation

        with mock.patch.object(source_generation, '_coherent_source_bytes',
                               side_effect=replacing):
            with self.assertRaises(SourceChanged):
                self.load_generation()

        self.assertTrue(replaced)

    def test_external_import_keeps_ordinary_custom_finder_behavior(self):
        module_name = f'external_generation_fixture_{id(self)}'

        class VirtualLoader(Loader):
            def create_module(self, spec):
                return None

            def exec_module(self, module):
                module.VALUE = 17

        class VirtualFinder(MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == module_name:
                    return ModuleSpec(fullname, VirtualLoader())
                return None

        finder = VirtualFinder()
        try:
            with SourceGeneration(self.root):
                # The generation finder is index zero.  Putting this finder
                # immediately behind it proves non-project imports are not
                # claimed by the project-only PathFinder seam.
                sys.meta_path.insert(1, finder)
                module = import_module(module_name)
            self.assertEqual(module.VALUE, 17)
        finally:
            sys.modules.pop(module_name, None)
            if finder in sys.meta_path:
                sys.meta_path.remove(finder)


class LateProjectImportTest(ScratchLoadProject):

    def test_late_import_joins_the_same_generation_without_forcing_retry(self):
        self.write('late.py', 'VALUE = 7\n')
        self.write('model.py', MODEL.replace(
            '    def render(self):\n        return cube(VALUE)\n',
            '    def render(self):\n'
            '        from .late import VALUE as late_value\n'
            '        return cube(VALUE + late_value)\n'))
        late = os.path.realpath(os.path.join(self.package_dir, 'late.py'))

        with chdir(self.root), project_source_generation(
                self.reference) as generation:
            node = load_node(self.reference, generation=generation)
            with generation.phase(node.files, label='assembly'):
                node.assemble()
            self.assertIn(late, generation.imported_paths)

    def test_replaced_contributor_ends_the_phase(self):
        with chdir(self.root), project_source_generation(
                self.reference) as generation:
            node = load_node(self.reference, generation=generation)
            with self.assertRaises(SourceChanged):
                with generation.phase(node.files, label='assembly'):
                    replacement = os.path.join(self.package_dir,
                                               '.dimensions.py')
                    with open(replacement, 'w') as source:
                        source.write('VALUE = 2\n')
                    os.replace(replacement, self.dimensions)

    def test_foreign_contributor_cannot_change_between_phases(self):
        foreign = self.write('profile.scad', 'cube(1);\n')
        old_mtime = os.stat(foreign).st_mtime_ns

        with SourceGeneration(self.root) as generation:
            with generation.phase([foreign], label='assembly'):
                pass

            replacement = os.path.join(self.package_dir, '.profile.scad')
            with open(replacement, 'w') as source:
                source.write('cube(2);\n')
            os.utime(replacement, ns=(old_mtime, old_mtime))
            os.replace(replacement, foreign)

            with self.assertRaises(SourceChanged):
                with generation.phase([foreign], label='artifact_pass'):
                    pass

    def test_foreign_alias_cannot_retarget_between_phases(self):
        first = self.write('first.scad', 'cube(1);\n')
        second = self.write('second.scad', 'cube(2);\n')
        alias = os.path.join(self.package_dir, 'selected.scad')
        os.symlink(first, alias)

        with SourceGeneration(self.root) as generation:
            with generation.phase([alias], label='assembly'):
                pass

            os.unlink(alias)
            os.symlink(second, alias)

            with self.assertRaises(SourceChanged):
                with generation.phase([alias], label='artifact_pass'):
                    pass


class BuilderGenerationGuardTest(ScratchLoadProject):

    def test_same_maximum_replacement_during_assembly_returns_source_changed(self):
        self.write('model.py', MODEL.replace(
            'from solid2 import cube\n',
            'import os\n\nfrom solid2 import cube\n').replace(
            '    def render(self):\n        return cube(VALUE)\n',
            '    def render(self):\n'
            "        replacement = os.environ['SOURCE_REPLACEMENT']\n"
            '        if os.path.exists(replacement):\n'
            "            os.replace(replacement, os.path.join(\n"
            "                os.path.dirname(__file__), 'dimensions.py'))\n"
            '        return cube(VALUE)\n'))
        replacement = os.path.join(self.package_dir, '.dimensions.py')
        with open(replacement, 'w') as source:
            source.write('VALUE = 2\n')
        old_mtime = os.stat(self.dimensions).st_mtime_ns
        os.utime(replacement, ns=(old_mtime, old_mtime))
        model_path = os.path.join(self.package_dir, 'model.py')
        future = time.time_ns() + 10 ** 9
        os.utime(model_path, ns=(future, future))

        with mock.patch.dict(os.environ, {
                'SOLID_BUILD_DIR': os.path.join(self.root, '_build'),
                'SOURCE_REPLACEMENT': replacement,
        }), chdir(self.root):
            builder = Builder(self.reference, watch=False, lifecycle=True)
            outcome = __import__('asyncio').run(builder._start())

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)

    def test_publication_checks_after_serialization_before_manifest_write(self):
        source = self.write('publication.py', 'VALUE = 1\n')
        artifact = os.path.join(self.root, 'part.stl')
        with open(artifact, 'w') as output:
            output.write('solid part\nendsolid part\n')
        node = SimpleNamespace(
            rigid=True, name='part', _type='SolidNode', color=None, mtime=0,
            operations=(), stl_file=artifact, files={source})
        builder = Builder('model.py', build_dir=self.root, watch=False)
        builder.node = node

        with SourceGeneration(self.root) as generation:
            with self.assertRaises(SourceChanged):
                with generation.phase(
                        [source], label='publication') as phase:
                    original = phase.checkpoint

                    def replace_before_write(paths=(), label=None):
                        if label == 'publication_pre_write':
                            replacement = os.path.join(
                                self.package_dir, '.publication.py')
                            with open(replacement, 'w') as changed:
                                changed.write('VALUE = 2\n')
                            os.replace(replacement, source)
                        return original(paths, label)

                    with mock.patch.object(
                            phase, 'checkpoint',
                            side_effect=replace_before_write):
                        builder._write_viewer_snapshot()

        self.assertFalse(os.path.exists(os.path.join(self.root, 'viewer.json')))


class AsyncRendererGenerationGuardTest(TestCase):

    def test_replacement_during_wait_discards_renderer_output(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, 'model.py')
            with open(source, 'w') as output:
                output.write('VALUE = 1\n')
            old_mtime = os.stat(source).st_mtime_ns
            temporary = os.path.join(root, '.part.stl.tmp')
            target = os.path.join(root, 'part.stl')
            lock = os.path.join(root, 'part.stl.lock')
            for path in (temporary, lock):
                with open(path, 'w') as output:
                    output.write('pending')

            proc = mock.Mock(pid=123, args=['openscad'])

            def finish_process():
                replacement = os.path.join(root, '.model.py')
                with open(replacement, 'w') as output:
                    output.write('VALUE = 2\n')
                os.utime(replacement, ns=(old_mtime, old_mtime))
                os.replace(replacement, source)
                return 0

            proc.wait.side_effect = finish_process
            job = StlRenderStart(proc, target, temporary, old_mtime, lock)

            with SourceGeneration(root) as generation:
                with self.assertRaises(SourceChanged):
                    with generation.phase(
                            [source], label='artifact_pass') as phase:
                        job.wait(checkpoint=phase.checkpoint)

            self.assertFalse(os.path.exists(temporary))
            self.assertFalse(os.path.exists(lock))
            self.assertFalse(os.path.exists(target))


class ForeignSourceCacheTest(TestCase):

    def test_step_document_cache_rejects_same_mtime_replacement(self):
        from solid_node.node.adapters import step

        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, 'part.step')
            with open(path, 'wb') as source:
                source.write(b'old step')
            old_mtime = os.stat(path).st_mtime_ns
            step._document_cache.clear()
            self.addCleanup(step._document_cache.clear)

            with mock.patch.object(step, '_read_document',
                                   side_effect=[object(), object()]) as read:
                first = step.cached_document(path)
                replacement = os.path.join(root, '.part.step')
                with open(replacement, 'wb') as source:
                    source.write(b'new step')
                os.utime(replacement, ns=(old_mtime, old_mtime))
                os.replace(replacement, path)
                second = step.cached_document(path)

            self.assertIsNot(first, second)
            self.assertEqual(read.call_count, 2)

    def test_step_read_before_phase_rejects_replacement_during_read(self):
        from solid_node.node.adapters import step

        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, 'part.step')
            with open(path, 'wb') as source:
                source.write(b'old step')
            old_mtime = os.stat(path).st_mtime_ns
            step._document_cache.clear()
            self.addCleanup(step._document_cache.clear)

            def replacing(_path):
                replacement = os.path.join(root, '.part.step')
                with open(replacement, 'wb') as source:
                    source.write(b'new step')
                os.utime(replacement, ns=(old_mtime, old_mtime))
                os.replace(replacement, path)
                return object()

            with SourceGeneration(root), mock.patch.object(
                    step, '_read_document', side_effect=replacing):
                with self.assertRaises(SourceChanged):
                    step.cached_document(path)


class JScadGenerationGuardTest(TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name
        self.source = os.path.join(self.root, 'part.js')
        self.target = os.path.join(self.root, 'part.stl')
        with open(self.source, 'w') as output:
            output.write('return cube({size: 1});\n')
        with open(self.target, 'wb') as output:
            output.write(b'old artifact')
        currency.record(self.target, 'old-digest', 'old-fingerprint')

    def node(self):
        return SimpleNamespace(
            jscad_source=self.source,
            stl_file=self.target,
            local_stl='part.stl',
            mtime_ns=os.stat(self.source).st_mtime_ns,
            source_digest='new-digest',
            source_fingerprint='new-fingerprint',
            _up_to_date=lambda path: False,
        )

    def test_source_replacement_after_renderer_preserves_old_artifact(self):
        old_mtime = os.stat(self.source).st_mtime_ns

        def launch(command):
            process = mock.Mock(returncode=0)

            def render():
                with open(command[-1], 'wb') as output:
                    output.write(b'new artifact')
                replacement = os.path.join(self.root, '.part.js')
                with open(replacement, 'w') as output:
                    output.write('return cube({size: 2});\n')
                os.utime(replacement, ns=(old_mtime, old_mtime))
                os.replace(replacement, self.source)

            process.communicate.side_effect = render
            return process

        with SourceGeneration(self.root) as generation, \
             mock.patch('solid_node.node.adapters.jscad.Popen',
                        side_effect=launch), \
             mock.patch('solid_node.node.adapters.jscad.import_stl'):
            with self.assertRaises(SourceChanged):
                with generation.phase([self.source], label='assembly'):
                    JScadNode.as_scad(self.node(), None)

        with open(self.target, 'rb') as artifact:
            self.assertEqual(artifact.read(), b'old artifact')
        self.assertEqual(currency.recorded_digest(self.target), 'old-digest')

    def test_failed_renderer_discards_partial_output_and_preserves_old(self):
        def launch(command):
            process = mock.Mock(returncode=2, args=command)

            def render():
                with open(command[-1], 'wb') as output:
                    output.write(b'partial artifact')

            process.communicate.side_effect = render
            return process

        with mock.patch('solid_node.node.adapters.jscad.Popen',
                        side_effect=launch), \
             mock.patch('solid_node.node.adapters.jscad.import_stl'):
            with self.assertRaises(CalledProcessError):
                JScadNode.as_scad(self.node(), None)

        with open(self.target, 'rb') as artifact:
            self.assertEqual(artifact.read(), b'old artifact')
        self.assertEqual(currency.recorded_digest(self.target), 'old-digest')
