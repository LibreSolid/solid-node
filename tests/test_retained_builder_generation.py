# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Red-first contracts for one fresh builder per stable source generation.

The builder remains a spawned, reconstructable child.  What changes is the
amount of stable work that child may finish: successful artifact passes
continue on its one loaded and assembled tree, while a pass that made no
progress (another producer owns the per-STL lock) still yields to the existing
supervisor retry boundary.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import tempfile
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import AsyncMock, Mock, call, patch

from solid_node.core.builder import Builder, BuildOutcome


class _StableNode:
    """Small node double for lifecycle structure rather than geometry."""

    def __init__(self):
        self.files = set()
        self.children = ()
        self.rigid = False
        self.mtime_ns = 0
        self.assemble = Mock()


class _InProcessBuilderTest(TestCase):
    """Restore the process environment changed by ``Builder._start``.

    Production builders run in disposable child processes, where exporting
    the selected build directory is intentional.  These structural tests run
    that entry point in pytest's long-lived process, so each test must put the
    ambient selection back before another test constructs a node.
    """

    def setUp(self):
        super().setUp()
        present = 'SOLID_BUILD_DIR' in os.environ
        previous = os.environ.get('SOLID_BUILD_DIR')

        def restore_build_dir():
            if present:
                os.environ['SOLID_BUILD_DIR'] = previous
            else:
                os.environ.pop('SOLID_BUILD_DIR', None)

        self.addCleanup(restore_build_dir)


class RetainedPassLoopTest(_InProcessBuilderTest):

    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory(prefix='solid-wp2-loop-')
        self.addCleanup(self.temporary.cleanup)
        self.builder = Builder(
            'model.py', build_dir=self.temporary.name, watch=False)
        self.node = _StableNode()

    def test_successful_artifact_passes_continue_on_one_assembled_root(self):
        """Intermediate renderer completions are internal to one child."""
        outcomes = iter([
            BuildOutcome.RENDERED,
            BuildOutcome.RENDERED,
            BuildOutcome.RENDERED,
            BuildOutcome.CURRENT,
        ])
        pass_roots = []

        async def generate():
            pass_roots.append(self.builder.node)
            outcome = next(outcomes)
            self.builder._artifact_pass_progressed = (
                outcome is BuildOutcome.RENDERED)
            return outcome

        self.builder.generate_stl = AsyncMock(side_effect=generate)
        self.builder._published_model_is_current = Mock(return_value=False)
        self.builder._write_viewer_snapshot = Mock(return_value=True)

        with patch('solid_node.core.builder.load_node', return_value=self.node):
            outcome = asyncio.run(self.builder._start())

        self.assertEqual(outcome, BuildOutcome.CURRENT)
        self.assertEqual(self.builder.generate_stl.await_count, 4)
        self.assertEqual(pass_roots, [self.node] * 4)
        self.assertTrue(all(root is self.node for root in pass_roots))
        self.node.assemble.assert_called_once_with()
        self.builder._write_viewer_snapshot.assert_called_once_with()

    def test_retained_passes_do_not_repeat_or_reorder_exact_fusion(self):
        """The assembled tree owns one ordered exact composition."""
        from types import SimpleNamespace

        from solid_node.node.fusion import FusionNode

        fusion = object.__new__(FusionNode)
        fusion.name = 'assembly'
        fusion.brep_file = str(Path(self.temporary.name) / 'assembly.brep')
        fusion._up_to_date = Mock(return_value=False)
        fusion.children = [
            SimpleNamespace(name=name, exact=True,
                            shape=Mock(return_value=name))
            for name in ('first', 'second', 'third')
        ]
        fusion_order = []

        def fuse(first, second, first_name, second_name):
            fusion_order.append((first_name, second_name))
            return (first, second)

        self.node.assemble.side_effect = fusion.shape
        outcomes = iter([
            BuildOutcome.RENDERED,
            BuildOutcome.RENDERED,
            BuildOutcome.CURRENT,
        ])

        async def generate():
            outcome = next(outcomes)
            self.builder._artifact_pass_progressed = (
                outcome is BuildOutcome.RENDERED)
            return outcome

        self.builder.generate_stl = AsyncMock(side_effect=generate)
        self.builder._published_model_is_current = Mock(return_value=False)
        self.builder._write_viewer_snapshot = Mock(return_value=True)

        with patch('solid_node.node.fusion._compose_solid_matrix',
                   return_value=object()), patch(
                       'solid_node.node.fusion.placed_shape',
                       side_effect=lambda shape, matrix: shape), patch(
                           'solid_node.node.fusion.fuse_shapes',
                           side_effect=fuse), patch(
                               'solid_node.core.builder.load_node',
                               return_value=self.node):
            outcome = asyncio.run(self.builder._start())

        self.assertEqual(outcome, BuildOutcome.CURRENT)
        self.node.assemble.assert_called_once_with()
        self.assertEqual(fusion_order, [
            ('assembly', 'second'),
            ('assembly', 'third'),
        ])

    def test_a_no_progress_render_pass_yields_without_busy_spinning(self):
        """A live per-STL lock is not permission for a retained tight loop."""
        async def no_progress():
            self.builder._artifact_pass_progressed = False
            return BuildOutcome.RENDERED

        self.builder.generate_stl = AsyncMock(side_effect=no_progress)
        self.builder._published_model_is_current = Mock(return_value=False)
        self.builder._write_viewer_snapshot = Mock()

        with patch('solid_node.core.builder.load_node', return_value=self.node):
            outcome = asyncio.run(self.builder._start())

        self.assertEqual(outcome, BuildOutcome.RENDERED)
        self.builder.generate_stl.assert_awaited_once_with()
        self.builder._write_viewer_snapshot.assert_not_called()


class ReloadFailureWaitTest(_InProcessBuilderTest):

    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory(prefix='solid-wp2-reload-')
        self.addCleanup(self.temporary.cleanup)
        model = Path(self.temporary.name) / 'model.py'
        model.write_text('# recovery-watch target\n')
        self.builder = Builder(
            str(model), build_dir=self.temporary.name,
            is_reload=True, watch=True)
        self.addCleanup(self.builder.observer.stop)
        self.node = _StableNode()
        self.node.assemble.side_effect = RuntimeError('broken reload')
        self.node.trigger_stl = Mock()

    def test_reload_failure_waits_outside_lock_without_more_geometry(self):
        """A failed generation records once, waits, then dies on repair."""
        async def scenario():
            building = asyncio.create_task(self.builder._start())
            errors = Path(self.temporary.name) / 'errors.json'
            for _ in range(500):
                await asyncio.sleep(0.01)
                if errors.exists() and self.builder.file_changed is not None:
                    break
            self.assertTrue(errors.exists(), 'reload error was not published')

            from tests.test_build_lock import lock_is_held
            self.assertFalse(
                lock_is_held(self.temporary.name),
                'recovery watch retained the project build lock')
            self.assertFalse(building.done(), 'reload failure respawned at once')
            self.node.trigger_stl.assert_not_called()

            self.builder.file_changed.set_result(True)
            return await building

        with patch('solid_node.core.builder.load_node', return_value=self.node):
            outcome = asyncio.run(scenario())

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)
        self.node.assemble.assert_called_once_with()
        self.node.trigger_stl.assert_not_called()
        error = json.loads(
            (Path(self.temporary.name) / 'errors.json').read_text())
        self.assertIn('broken reload', error['error'])


class OneShotLaterPassFailureTest(_InProcessBuilderTest):
    """A retained child remains a complete failure boundary."""

    def test_failure_after_a_completed_pass_is_fatal_without_publication(self):
        with tempfile.TemporaryDirectory(prefix='solid-wp2-failure-') as root:
            builder = Builder('model.py', build_dir=root, watch=False)
            node = _StableNode()
            calls = 0

            async def render_then_fail():
                nonlocal calls
                calls += 1
                if calls == 1:
                    builder._artifact_pass_progressed = True
                    return BuildOutcome.RENDERED
                raise RuntimeError('later retained pass failed')

            builder.generate_stl = AsyncMock(side_effect=render_then_fail)
            builder._published_model_is_current = Mock(return_value=False)
            builder._write_viewer_snapshot = Mock()
            with patch('solid_node.core.builder.load_node', return_value=node):
                outcome = asyncio.run(builder._start())

            self.assertEqual(outcome, BuildOutcome.FAILED)
            self.assertEqual(calls, 2)
            node.assemble.assert_called_once_with()
            builder._write_viewer_snapshot.assert_not_called()
            error = json.loads((Path(root) / 'errors.json').read_text())
            self.assertIn('later retained pass failed', error['error'])


class _InjectedGeneration:
    """Controllable generation double for lifecycle boundary ordering."""

    def __init__(self, *, fail_checkpoint=None, fail_phase_entry=None,
                 fail_phase_entry_number=1, fail_phase_exit=None):
        self.fail_checkpoint = fail_checkpoint
        self.fail_phase_entry = fail_phase_entry
        self.fail_phase_entry_number = fail_phase_entry_number
        self.fail_phase_exit = fail_phase_exit
        self.phase_entries = []

    def checkpoint(self, label):
        if label == self.fail_checkpoint:
            from solid_node.source_generation import SourceChanged
            raise SourceChanged(f'changed at {label}')

    @contextmanager
    def phase(self, paths, *, label):
        self.phase_entries.append(label)
        if (label == self.fail_phase_entry
                and self.phase_entries.count(label)
                == self.fail_phase_entry_number):
            from solid_node.source_generation import SourceChanged
            raise SourceChanged(f'changed entering {label}')
        try:
            yield self
        finally:
            if label == self.fail_phase_exit:
                from solid_node.source_generation import SourceChanged
                raise SourceChanged(f'changed leaving {label}')


class RetainedGenerationRaceTest(_InProcessBuilderTest):

    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory(prefix='solid-wp2-race-')
        self.addCleanup(self.temporary.cleanup)
        self.node = _StableNode()

    def builder_with(self, generation):
        builder = Builder(
            'model.py', build_dir=self.temporary.name, watch=False)
        # Installing the explicit generation bypasses Builder's outer context
        # setup, exactly as its recursive implementation does internally.
        builder._source_generation = generation
        builder._published_model_is_current = Mock(return_value=False)
        builder._write_viewer_snapshot = Mock(return_value=True)
        return builder

    def run_builder(self, builder):
        with patch('solid_node.core.builder.load_node', return_value=self.node):
            return asyncio.run(builder._start())

    def assert_stood_down(self, builder, outcome):
        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)
        builder._write_viewer_snapshot.assert_not_called()

    def test_source_replaced_while_waiting_for_lock_stands_down(self):
        generation = _InjectedGeneration(fail_checkpoint='after_lock')
        builder = self.builder_with(generation)
        builder.generate_stl = AsyncMock()

        outcome = self.run_builder(builder)

        self.assert_stood_down(builder, outcome)
        self.assertIn('loaded_sources', generation.phase_entries)
        self.node.assemble.assert_not_called()
        builder.generate_stl.assert_not_awaited()

    def test_source_replaced_during_assembly_stands_down(self):
        generation = _InjectedGeneration(fail_phase_exit='assembly')
        builder = self.builder_with(generation)
        builder.generate_stl = AsyncMock()

        outcome = self.run_builder(builder)

        self.assert_stood_down(builder, outcome)
        self.node.assemble.assert_called_once_with()
        builder.generate_stl.assert_not_awaited()

    def test_source_replaced_between_retained_passes_stands_down(self):
        generation = _InjectedGeneration(
            fail_phase_entry='artifact_pass', fail_phase_entry_number=2)
        builder = self.builder_with(generation)
        calls = 0

        async def first_pass():
            nonlocal calls
            calls += 1
            builder._artifact_pass_progressed = True
            return BuildOutcome.RENDERED

        builder.generate_stl = AsyncMock(side_effect=first_pass)

        outcome = self.run_builder(builder)

        self.assert_stood_down(builder, outcome)
        self.assertEqual(calls, 1)
        self.assertEqual(generation.phase_entries.count('artifact_pass'), 2)

    def test_source_replaced_immediately_before_publication_is_not_published(self):
        generation = _InjectedGeneration()
        builder = self.builder_with(generation)
        builder.generate_stl = AsyncMock(return_value=BuildOutcome.CURRENT)

        def reject_publication():
            from solid_node.source_generation import SourceChanged
            raise SourceChanged('changed before publication')

        builder._write_viewer_snapshot.side_effect = reject_publication

        outcome = self.run_builder(builder)

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)
        builder._write_viewer_snapshot.assert_called_once_with()


class FilesystemGenerationRaceTest(_InProcessBuilderTest):
    """Real identity changes at WP2's two retained-loop boundaries."""

    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory(prefix='solid-wp2-fs-race-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'model.py'
        self.anchor = self.root / 'future.py'
        self.source.write_text('VALUE = 1\n')
        self.anchor.write_text('ANCHOR = True\n')
        future = os.stat(self.anchor).st_mtime_ns + 10 ** 9
        os.utime(self.anchor, ns=(future, future))
        (self.root / 'pyproject.toml').write_text(
            '[tool.solid-node]\nmodel = "model.py"\n')
        self.node = _StableNode()
        self.node.files = {str(self.source), str(self.anchor)}
        self.node.mtime_ns = future
        self.builder = Builder(
            str(self.source), build_dir=str(self.root / '_build'),
            watch=False)
        self.builder._published_model_is_current = Mock(return_value=False)
        self.builder._write_viewer_snapshot = Mock(return_value=True)

    def replace_source_beneath_same_maximum(self):
        old_mtime = os.stat(self.source).st_mtime_ns
        replacement = self.root / '.model.py'
        replacement.write_text('VALUE = 2\n')
        os.utime(replacement, ns=(old_mtime, old_mtime))
        os.replace(replacement, self.source)
        self.assertEqual(
            max(os.stat(path).st_mtime_ns for path in self.node.files),
            self.node.mtime_ns)

    def run_builder(self):
        with patch('solid_node.core.builder.load_node', return_value=self.node):
            return asyncio.run(self.builder._start())

    def test_same_maximum_replacement_before_lock_acquisition_stands_down(self):
        @contextmanager
        def changed_before_acquisition(build_dir=None):
            self.replace_source_beneath_same_maximum()
            yield

        self.builder.generate_stl = AsyncMock()
        with patch('solid_node.core.builder.project_build_lock',
                   changed_before_acquisition):
            outcome = self.run_builder()

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)
        self.node.assemble.assert_not_called()
        self.builder.generate_stl.assert_not_awaited()
        self.builder._write_viewer_snapshot.assert_not_called()

    def test_same_maximum_replacement_between_retained_passes_stands_down(self):
        from solid_node.source_generation import SourceGeneration

        owner = self

        class ChangeBetweenPasses(SourceGeneration):
            artifact_passes = 0

            @contextmanager
            def phase(self, paths, label):
                with super().phase(paths, label) as phase:
                    yield phase
                if label == 'artifact_pass':
                    self.artifact_passes += 1
                    if self.artifact_passes == 1:
                        owner.replace_source_beneath_same_maximum()

        async def completed_renderer():
            self.builder._artifact_pass_progressed = True
            return BuildOutcome.RENDERED

        self.builder.generate_stl = AsyncMock(side_effect=completed_renderer)
        with patch('solid_node.core.builder.project_source_generation',
                   side_effect=lambda _: ChangeBetweenPasses(self.root)):
            outcome = self.run_builder()

        self.assertEqual(outcome, BuildOutcome.SOURCE_CHANGED)
        self.builder.generate_stl.assert_awaited_once_with()
        self.builder._write_viewer_snapshot.assert_not_called()


class BuildSupervisorGenerationTest(TestCase):
    """Only source movement and no-progress contention are retry outcomes."""

    def test_source_change_retries_in_a_new_fresh_interpreter(self):
        from solid_node.manager.build import Build, build_once

        changed = Mock(exitcode=BuildOutcome.SOURCE_CHANGED.value)
        current = Mock(exitcode=BuildOutcome.CURRENT.value)
        command = Build()
        command.overrides = []
        with patch('solid_node.manager.build.resolve_node'), patch(
                'solid_node.manager.build.Process',
                side_effect=[changed, current]) as process:
            status = command.build('model.py')

        self.assertEqual(status, 0)
        self.assertEqual(process.call_args_list, [
            call(target=build_once, args=('model.py', [])),
            call(target=build_once, args=('model.py', [])),
        ])

    def test_ordinary_one_shot_failure_is_fatal_not_a_generation_retry(self):
        from solid_node.manager.build import Build, build_once

        failed = Mock(exitcode=BuildOutcome.FAILED.value)
        command = Build()
        command.overrides = []
        with patch('solid_node.manager.build.resolve_node'), patch(
                'solid_node.manager.build.Process',
                return_value=failed) as process:
            status = command.build('model.py')

        self.assertEqual(status, BuildOutcome.FAILED.value)
        self.assertEqual(process.call_args_list, [
            call(target=build_once, args=('model.py', [])),
        ])


def _single_pass_build_once(path, overrides):
    """Reference target retaining the pre-WP2 process-per-pass boundary.

    It uses the current artifact and source guards but deliberately tells the
    builder that a completed renderer is not retained.  The manager therefore
    starts a new spawned interpreter for each artifact, isolating output
    equivalence from the lifecycle optimization under test.
    """
    builder = Builder(
        path, watch=False, lifecycle=True, overrides=overrides)
    generate_stl = builder.generate_stl

    async def one_pass():
        outcome = await generate_stl()
        if outcome is BuildOutcome.RENDERED:
            builder._artifact_pass_progressed = False
        return outcome

    builder.generate_stl = one_pass
    builder.start()


class FreshProcessBatchTest(TestCase):
    """End-to-end child/process/construction and publication proof."""

    PROJECT_SOURCE = '''\
import os
from solid2 import cube
from solid_node.node import AssemblyNode, Solid2Node
from solid_node.parameters import Count, Length


def record(event):
    with open(os.environ['SOLID_WP2_TRACE'], 'a') as stream:
        stream.write(event + '\\n')


class Part(Solid2Node):
    size = Length(1.0)

    def __init__(self, **kwargs):
        record('part-init')
        super().__init__(**kwargs)

    def render(self):
        record('part-render')
        return cube([self.size, 1, 1])


class Machine(AssemblyNode):
    count = Count(24, min=1)

    def __init__(self, **kwargs):
        record('root-init')
        super().__init__(**kwargs)
        self.parts = [Part(size=1 + i / 100) for i in range(self.count)]

    def render(self):
        record('root-render')
        for i, part in enumerate(self.parts):
            part.translate([3 * i, 0, 0])
        return self.parts
'''

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='solid-wp2-batch-')
        self.addCleanup(self.temporary.cleanup)
        self.root = self.make_project('retained')
        self.reference_root = self.make_project('single-pass-reference')

    def make_project(self, name):
        root = Path(self.temporary.name) / name
        package = root / 'bench'
        package.mkdir(parents=True)
        (package / '__init__.py').write_text('')
        (package / 'solid.py').write_text(self.PROJECT_SOURCE)
        (root / 'pyproject.toml').write_text(
            '[tool.solid-node]\nmodel = "bench.solid:Machine"\n')
        return root

    @contextmanager
    def project_environment(self, root):
        previous = os.getcwd()
        os.chdir(root)
        try:
            with patch.dict(os.environ, {
                    'SOLID_BUILD_DIR': str(root / '_build'),
                    'SOLID_WP2_TRACE': str(root / 'trace.log'),
                    'PYTHONDONTWRITEBYTECODE': '1',
            }):
                yield
        finally:
            os.chdir(previous)

    def build(self, root, *, single_pass_reference=False):
        import solid_node.manager.build as build_module

        real_process = build_module.Process
        children = []

        def counted_process(*args, **kwargs):
            if single_pass_reference:
                self.assertIs(kwargs.get('target'), build_module.build_once)
                kwargs['target'] = _single_pass_build_once
            child = real_process(*args, **kwargs)
            children.append(child)
            return child

        command = build_module.Build()
        command.overrides = []
        with self.project_environment(root), patch.object(
                build_module, 'Process', side_effect=counted_process):
            status = command.build('bench.solid:Machine')
        self.assertEqual(status, 0)
        return children

    def artifact_hashes(self, root):
        build_dir = root / '_build'
        return {
            str(path.relative_to(build_dir)):
                hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(build_dir.rglob('*.stl'))
        }

    def test_cold_twenty_four_artifact_build_uses_one_spawned_builder(self):
        children = self.build(self.root)
        reference_children = self.build(
            self.reference_root, single_pass_reference=True)
        self.assertEqual(
            len(children), 1,
            'one stable generation spawned more than one builder child')
        self.assertEqual([child.exitcode for child in children], [0])
        self.assertEqual(
            len(reference_children), 25,
            'single-pass reference did not exercise all 24 artifact passes')

        events = (self.root / 'trace.log').read_text().splitlines()
        self.assertEqual(events.count('root-init'), 1)
        self.assertEqual(events.count('part-init'), 24)
        self.assertEqual(events.count('root-render'), 1)
        self.assertEqual(events.count('part-render'), 24)

        build_dir = self.root / '_build'
        document = json.loads((build_dir / 'viewer.json').read_text())
        published = {
            node['model']
            for node in document['root']['children']
            if 'model' in node
        }
        artifact_hashes = self.artifact_hashes(self.root)
        self.assertEqual(set(artifact_hashes), published)
        self.assertEqual(len(artifact_hashes), 24)
        self.assertEqual(
            artifact_hashes, self.artifact_hashes(self.reference_root),
            'retained continuation changed the complete filename/SHA-256 map')
