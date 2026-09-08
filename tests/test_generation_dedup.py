# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Generation-local SCAD work and compare-before-replace publication."""

import os
import tempfile
from types import SimpleNamespace
from unittest import TestCase, mock

from solid2 import cube, scad_render

from solid_node import currency
from solid_node.node import Solid2Node
from solid_node.node.assembly import AssemblyNode
from solid_node.node.base import AbstractBaseNode, _atomic_write_text
from solid_node.node.flexible import FlexibleNode
from solid_node.source_generation import (
    SourceCensus, SourceChanged, SourceGeneration,
)


class RepeatedBlock(Solid2Node):
    renders = 0

    def render(self):
        type(self).renders += 1
        return cube(4)


class BindingDependentFlexible(FlexibleNode):
    """Minimal actual flexible class for the SCAD publication seam only."""

    @property
    def scad_code(self):
        return self._test_scad_code

    @property
    def mtime_ns(self):
        return 10

    @property
    def mtime(self):
        return 10

    @property
    def source_digest(self):
        return 'digest'

    @property
    def source_fingerprint(self):
        return 'fingerprint'


class BindingDependentAssembly(AssemblyNode):
    """A non-flexible assembly whose instances share one artifact path."""

    @property
    def scad_code(self):
        return self._test_scad_code

    @property
    def mtime_ns(self):
        return 10

    @property
    def mtime(self):
        return 10

    @property
    def source_digest(self):
        return 'digest'

    @property
    def source_fingerprint(self):
        return 'fingerprint'


class ComposedBindingDependentAssembly(AssemblyNode):
    """Assembly instances whose child placement is not in artifact identity."""

    def render(self):
        return [self.part]


class GenerationScadDedupTest(TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name

    def desired(self, path, code, *, rigid=False, flexible=False,
                digest='digest', fingerprint='fingerprint'):
        return SimpleNamespace(
            scad_file=path, scad_code=code,
            mtime_ns=1_700_000_000_123_456_789,
            mtime=1_700_000_000.1234567,
            source_digest=digest, source_fingerprint=fingerprint,
            rigid=rigid, flexible=flexible,
        )

    def publish_non_rigid_phase(self, path):
        nodes = [
            self.desired(path, 'translate([1, 0, 0]) cube(1);'),
            self.desired(path, 'translate([2, 0, 0]) cube(1);'),
        ]
        with SourceGeneration(self.root) as generation, generation.phase(
                (), label='assembly'):
            for node in nodes:
                AbstractBaseNode.generate_scad(node)

    def replace_source_preserving_size_and_mtime(self, source):
        previous = os.stat(source).st_mtime_ns
        replacement = os.path.join(
            os.path.dirname(source), f'.{os.path.basename(source)}')
        with open(replacement, 'wb') as changed:
            changed.write(b'VALUE = 2\n')
        os.utime(replacement, ns=(previous, previous))
        os.replace(replacement, source)

    def test_repeated_instances_render_user_code_but_generate_base_scad_once(self):
        with mock.patch.dict(os.environ, {'SOLID_BUILD_DIR': self.root}):
            first = RepeatedBlock().translate([1, 0, 0])
            second = RepeatedBlock().translate([2, 0, 0])
        self.assertEqual(first.scad_file, second.scad_file)
        RepeatedBlock.renders = 0

        import solid_node.node.base as base
        real_scad_render = base.scad_render
        with SourceGeneration(self.root) as generation, generation.phase(
                first.files | second.files, label='assembly'), mock.patch.object(
                    base, 'scad_render', wraps=real_scad_render) as generate:
            first_assembled = first.assemble()
            second_assembled = second.assemble()

        self.assertEqual(RepeatedBlock.renders, 2)
        self.assertEqual(generate.call_count, 1)
        self.assertNotEqual(scad_render(first_assembled),
                            scad_render(second_assembled))

    def test_audit_scale_repeated_instances_still_generate_one_base_scad(self):
        with mock.patch.dict(os.environ, {'SOLID_BUILD_DIR': self.root}):
            nodes = [RepeatedBlock().translate([index, 0, 0])
                     for index in range(59)]
        files = set().union(*(node.files for node in nodes))
        RepeatedBlock.renders = 0

        import solid_node.node.base as base
        real_scad_render = base.scad_render
        with SourceGeneration(self.root) as generation, generation.phase(
                files, label='assembly'), mock.patch.object(
                    base, 'scad_render', wraps=real_scad_render) as generate:
            assembled = [node.assemble() for node in nodes]

        self.assertEqual(RepeatedBlock.renders, 59)
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(len({scad_render(model) for model in assembled}), 59)

    def test_same_path_with_different_full_source_identity_is_not_reused(self):
        path = os.path.join(self.root, 'shared.scad')
        first = SimpleNamespace(
            scad_file=path, scad_code='cube(1);', mtime_ns=10, mtime=10,
            source_digest='digest-one', source_fingerprint='fingerprint-one',
            rigid=True)
        second = SimpleNamespace(
            scad_file=path, scad_code='cube(2);', mtime_ns=10, mtime=10,
            source_digest='digest-two', source_fingerprint='fingerprint-two',
            rigid=True)

        import solid_node.node.base as base
        with SourceGeneration(self.root), mock.patch.object(
                base, '_atomic_write_text') as write:
            AbstractBaseNode.generate_scad(first)
            AbstractBaseNode.generate_scad(second)

        self.assertEqual(write.call_count, 2)

    def test_alternating_full_identities_follow_current_artifact(self):
        path = os.path.join(self.root, 'shared.scad')
        nodes = [
            SimpleNamespace(
                scad_file=path, scad_code=code, mtime_ns=10, mtime=10,
                source_digest=digest, source_fingerprint=fingerprint,
                rigid=True, flexible=False)
            for code, digest, fingerprint in (
                ('cube(1);', 'digest-one', 'fingerprint-one'),
                ('cube(2);', 'digest-two', 'fingerprint-two'),
                ('cube(1);', 'digest-one', 'fingerprint-one'),
            )
        ]

        import solid_node.node.base as base
        with SourceGeneration(self.root), mock.patch.object(
                base, '_atomic_write_text') as write:
            for node in nodes:
                AbstractBaseNode.generate_scad(node)

        self.assertEqual(write.call_count, 3)

    def test_unknown_identity_invalidates_rigid_current_artifact(self):
        path = os.path.join(self.root, 'shared.scad')
        nodes = [
            self.desired(path, 'cube(1);', rigid=True,
                         digest='digest-a', fingerprint='fingerprint-a'),
            self.desired(path, 'cube(2);', rigid=True,
                         digest=None, fingerprint=None),
            self.desired(path, 'cube(1);', rigid=True,
                         digest='digest-a', fingerprint='fingerprint-a'),
        ]

        import solid_node.node.base as base
        with SourceGeneration(self.root), mock.patch.object(
                base, '_atomic_write_text') as write:
            for node in nodes:
                AbstractBaseNode.generate_scad(node)

        self.assertEqual(write.call_count, 3)

    def test_non_flexible_assembly_instances_share_base_scad_path(self):
        path = os.path.join(self.root, 'assembly.scad')
        nodes = []
        for code in ('translate([1, 0, 0]) cube(1);',
                     'translate([2, 0, 0]) cube(1);'):
            node = object.__new__(BindingDependentAssembly)
            node.scad_file = path
            node._test_scad_code = code
            nodes.append(node)

        self.assertFalse(nodes[0].rigid)
        self.assertFalse(nodes[0].flexible)

        import solid_node.node.base as base
        with SourceGeneration(self.root) as generation, mock.patch.object(
                base, '_atomic_write_text') as write:
            with generation.phase((), label='assembly'):
                for node in nodes:
                    AbstractBaseNode.generate_scad(node)

        self.assertEqual(write.call_count, 1)

    def test_binding_dependent_assemblies_keep_distinct_compositions(self):
        with mock.patch.dict(os.environ, {'SOLID_BUILD_DIR': self.root}):
            first = ComposedBindingDependentAssembly()
            first.part = RepeatedBlock().translate([1, 0, 0])
            second = ComposedBindingDependentAssembly()
            second.part = RepeatedBlock().translate([2, 0, 0])
        self.assertEqual(first.scad_file, second.scad_file)
        files = first.files | first.part.files | second.files | second.part.files

        import solid_node.node.base as base
        with SourceGeneration(self.root) as generation, mock.patch.object(
                base, '_atomic_write_text', wraps=_atomic_write_text) as write:
            with generation.phase(files, label='assembly'):
                compositions = [first.assemble(), second.assemble()]

        self.assertNotEqual(scad_render(compositions[0]),
                            scad_render(compositions[1]))
        parent_writes = [
            call for call in write.call_args_list
            if os.path.realpath(call.args[0]) == os.path.realpath(first.scad_file)
        ]
        self.assertEqual(len(parent_writes), 1)
        with open(first.scad_file) as published:
            self.assertEqual(published.read(), second.scad_code)

    def test_last_desired_values_are_captured_and_flushed_in_path_order(self):
        first_path = os.path.join(self.root, 'first.scad')
        second_path = os.path.join(self.root, 'second.scad')
        first_old = self.desired(first_path, 'cube(1);', digest='first-old')
        second = self.desired(second_path, 'sphere(2);', digest='second')
        first_final = self.desired(
            first_path, 'cube(3);', digest='first-final')

        import solid_node.node.base as base
        with SourceGeneration(self.root) as generation, mock.patch.object(
                base, '_atomic_write_text') as write:
            with generation.phase((), label='assembly'):
                AbstractBaseNode.generate_scad(first_old)
                AbstractBaseNode.generate_scad(second)
                AbstractBaseNode.generate_scad(first_final)
                first_final.scad_code = 'cube(999);'
                first_final.mtime_ns += 1
                first_final.source_digest = 'mutated-after-request'
                self.assertEqual(write.call_count, 0)

        self.assertEqual([call.args[0] for call in write.call_args_list],
                         [second_path, first_path])
        self.assertEqual(write.call_args_list[0].args[1:], (
            'sphere(2);', second.mtime_ns,
            second.source_digest, second.source_fingerprint,
        ))
        self.assertEqual(write.call_args_list[1].args[1:], (
            'cube(3);', first_final.mtime_ns - 1,
            'first-final', first_final.source_fingerprint,
        ))

    def test_second_and_third_stable_phase_preserve_file_identities(self):
        path = os.path.join(self.root, 'assembly.scad')
        self.publish_non_rigid_phase(path)
        targets = (path, currency.sidecar(path))
        settled = {
            target: os.stat(target) for target in targets
        }

        self.publish_non_rigid_phase(path)
        second = {target: os.stat(target) for target in targets}
        self.publish_non_rigid_phase(path)
        third = {target: os.stat(target) for target in targets}

        for target in targets:
            for current in (second[target], third[target]):
                self.assertEqual(current.st_ino, settled[target].st_ino)
                self.assertEqual(current.st_mtime_ns,
                                 settled[target].st_mtime_ns)
                self.assertEqual(current.st_ctime_ns,
                                 settled[target].st_ctime_ns)
        with open(path) as published:
            self.assertEqual(
                published.read(), 'translate([2, 0, 0]) cube(1);')

    def test_nonassembly_phase_and_direct_generation_remain_immediate(self):
        nodes = [
            self.desired(os.path.join(self.root, 'phase.scad'), 'cube(1);'),
            self.desired(os.path.join(self.root, 'direct.scad'), 'cube(2);'),
        ]

        import solid_node.node.base as base
        with SourceGeneration(self.root) as generation, mock.patch.object(
                base, '_atomic_write_text') as write:
            with generation.phase((), label='artifact_pass'):
                AbstractBaseNode.generate_scad(nodes[0])
                self.assertEqual(write.call_count, 1)
            AbstractBaseNode.generate_scad(nodes[1])
            self.assertEqual(write.call_count, 2)

    def test_flexible_generation_remains_immediate_in_assembly_phase(self):
        nodes = [
            self.desired(os.path.join(self.root, 'spring.scad'), code,
                         flexible=True)
            for code in ('import("one.stl");', 'import("two.stl");')
        ]

        import solid_node.node.base as base
        with SourceGeneration(self.root) as generation, mock.patch.object(
                base, '_atomic_write_text') as write:
            with generation.phase((), label='assembly'):
                for index, node in enumerate(nodes, 1):
                    AbstractBaseNode.generate_scad(node)
                    self.assertEqual(write.call_count, index)

    def test_body_failure_discards_pending_scad_without_generated_log(self):
        node = self.desired(
            os.path.join(self.root, 'assembly.scad'), 'cube(1);')

        import solid_node.node.base as base
        with SourceGeneration(self.root) as generation, mock.patch.object(
                base, '_atomic_write_text') as write, mock.patch.object(
                    base.logger, 'info') as logged:
            with self.assertRaisesRegex(RuntimeError, 'body failed'):
                with generation.phase((), label='assembly'):
                    AbstractBaseNode.generate_scad(node)
                    raise RuntimeError('body failed')

        write.assert_not_called()
        logged.assert_not_called()

    def test_preflush_source_failure_discards_pending_scad(self):
        source = os.path.join(self.root, 'model.py')
        with open(source, 'wb') as current:
            current.write(b'VALUE = 1\n')
        node = self.desired(
            os.path.join(self.root, 'assembly.scad'), 'cube(1);')

        import solid_node.node.base as base
        with SourceGeneration(self.root) as generation, mock.patch.object(
                base, '_atomic_write_text') as write:
            with self.assertRaisesRegex(SourceChanged, 'pre-flush'):
                with generation.phase((source,), label='assembly'):
                    AbstractBaseNode.generate_scad(node)
                    self.replace_source_preserving_size_and_mtime(source)

        write.assert_not_called()

    def test_flush_failure_clears_pending_requests_after_partial_progress(self):
        nodes = [
            self.desired(os.path.join(self.root, 'one.scad'), 'cube(1);'),
            self.desired(os.path.join(self.root, 'two.scad'), 'cube(2);'),
            self.desired(os.path.join(self.root, 'three.scad'), 'cube(3);'),
        ]

        import solid_node.node.base as base
        phase = None
        with SourceGeneration(self.root) as generation, mock.patch.object(
                base, '_atomic_write_text',
                side_effect=[None, OSError('flush failed')]) as write:
            with self.assertRaisesRegex(OSError, 'flush failed'):
                with generation.phase((), label='assembly') as phase:
                    for node in nodes:
                        AbstractBaseNode.generate_scad(node)
                    self.assertEqual(write.call_count, 0)

        self.assertEqual(write.call_count, 2)
        self.assertEqual(phase.pending_scad_count, 0)

    def test_flush_failure_leaves_only_completed_atomic_publications(self):
        first = self.desired(
            os.path.join(self.root, 'one.scad'), 'cube(2);',
            digest='new-one', fingerprint='new-one-fingerprint')
        second = self.desired(
            os.path.join(self.root, 'two.scad'), 'sphere(2);',
            digest='new-two', fingerprint='new-two-fingerprint')
        for path in (first.scad_file, second.scad_file):
            _atomic_write_text(
                path, 'cube(1);', first.mtime_ns,
                'old-digest', 'old-fingerprint')
        real_replace = os.replace

        def fail_second_artifact(source, target):
            if os.path.realpath(target) == os.path.realpath(second.scad_file):
                raise OSError('second atomic replacement failed')
            return real_replace(source, target)

        with SourceGeneration(self.root) as generation, mock.patch(
                'os.replace', side_effect=fail_second_artifact):
            with self.assertRaisesRegex(
                    OSError, 'second atomic replacement failed'):
                with generation.phase((), label='assembly'):
                    AbstractBaseNode.generate_scad(first)
                    AbstractBaseNode.generate_scad(second)

        with open(first.scad_file) as published:
            self.assertEqual(published.read(), 'cube(2);')
        self.assertEqual(currency.recorded_digest(first.scad_file), 'new-one')
        with open(second.scad_file) as published:
            self.assertEqual(published.read(), 'cube(1);')
        self.assertFalse(os.path.exists(currency.sidecar(second.scad_file)))
        self.assertFalse(any(name.endswith('.tmp')
                             for name in os.listdir(self.root)))

    def test_postflush_source_failure_propagates_after_atomic_publication(self):
        source = os.path.join(self.root, 'model.py')
        with open(source, 'wb') as current:
            current.write(b'VALUE = 1\n')
        node = self.desired(
            os.path.join(self.root, 'assembly.scad'), 'cube(1);')

        import solid_node.node.base as base
        real_publish = base._publish_scad

        def publish_then_change(*args):
            real_publish(*args)
            self.replace_source_preserving_size_and_mtime(source)

        with SourceGeneration(self.root) as generation, mock.patch.object(
                base, '_publish_scad', side_effect=publish_then_change) as write:
            with self.assertRaisesRegex(SourceChanged, 'post-flush'):
                with generation.phase((source,), label='assembly'):
                        AbstractBaseNode.generate_scad(node)

        write.assert_called_once()
        with open(node.scad_file) as published:
            self.assertEqual(published.read(), 'cube(1);')

    def test_generated_log_is_emitted_only_for_the_flushed_value(self):
        path = os.path.join(self.root, 'assembly.scad')
        nodes = [
            self.desired(path, 'cube(1);'),
            self.desired(path, 'cube(2);'),
        ]

        with SourceGeneration(self.root) as generation, self.assertLogs(
                'node.base', level='INFO') as logs:
            with generation.phase((), label='assembly'):
                for node in nodes:
                    AbstractBaseNode.generate_scad(node)
                self.assertFalse(any(
                    'generated with' in line for line in logs.output))

        generated = [line for line in logs.output if 'generated with' in line]
        self.assertEqual(len(generated), 1)

    def test_three_flexible_bindings_are_never_reused_by_base_scad_path(self):
        path = os.path.join(self.root, 'spring.scad')
        nodes = []
        for binding in ('spring-a.stl', 'spring-b.stl', 'spring-c.stl'):
            node = object.__new__(BindingDependentFlexible)
            node.scad_file = path
            node._test_scad_code = f'import("{binding}");'
            nodes.append(node)

        import solid_node.node.base as base
        with SourceGeneration(self.root), mock.patch.object(
                base, '_atomic_write_text') as write:
            for node in nodes:
                AbstractBaseNode.generate_scad(node)

        self.assertEqual(write.call_count, 3)

    def test_scad_reuse_does_not_survive_a_source_generation(self):
        node = SimpleNamespace(
            scad_file=os.path.join(self.root, 'part.scad'),
            scad_code='cube(1);', mtime_ns=10, mtime=10,
            source_digest='digest', source_fingerprint='fingerprint',
            rigid=True)

        import solid_node.node.base as base
        with mock.patch.object(base, '_atomic_write_text') as write:
            with SourceGeneration(self.root):
                AbstractBaseNode.generate_scad(node)
            with SourceGeneration(self.root):
                AbstractBaseNode.generate_scad(node)

        self.assertEqual(write.call_count, 2)

    def test_overlapping_currency_digests_hash_each_distinct_source_once(self):
        paths = []
        for name, content in (('one.py', b'ONE = 1\n'),
                              ('two.py', b'TWO = 2\n')):
            path = os.path.join(self.root, name)
            with open(path, 'wb') as source:
                source.write(content)
            paths.append(path)
        census = SourceCensus(self.root)
        census.include(paths)

        import solid_node.source_generation as source_generation
        original = source_generation._coherent_real_source_digest
        with mock.patch.object(
                source_generation, '_coherent_real_source_digest',
                wraps=original) as hashed:
            first = currency.source_digest(paths, self.root, census=census)
            second = currency.source_digest(
                [paths[1], paths[0], paths[0]], self.root, census=census)

        self.assertEqual(first, second)
        self.assertEqual(hashed.call_count, 2)

    def test_audit_scale_closures_hash_210_sources_once_in_one_census(self):
        paths = []
        for index in range(210):
            path = os.path.join(self.root, f'source_{index}.txt')
            with open(path, 'wb') as source:
                source.write(f'source {index}\n'.encode())
            paths.append(path)
        census = SourceCensus(self.root)
        census.include(paths)

        import solid_node.source_generation as source_generation
        original = source_generation._coherent_real_source_digest
        with mock.patch.object(
                source_generation, '_coherent_real_source_digest',
                wraps=original) as hashed:
            expected = currency.source_digest(
                paths, self.root, census=census)
            for _ in range(190):
                self.assertEqual(currency.source_digest(
                    reversed(paths), self.root, census=census), expected)

        self.assertEqual(hashed.call_count, 210)


class CompareBeforeReplaceTest(TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = os.path.join(self.temp.name, 'part.scad')
        self.stamp = 1_700_000_000_123_456_789

    def publish(self, content='cube(1);', stamp=None, digest='digest',
                fingerprint='fingerprint'):
        _atomic_write_text(
            self.path, content, self.stamp if stamp is None else stamp,
            digest, fingerprint)

    def replacements(self, action):
        replaced = []
        original = os.replace

        def counting(source, target):
            replaced.append(os.path.realpath(target))
            return original(source, target)

        with mock.patch('os.replace', side_effect=counting):
            action()
        return replaced

    def test_identical_text_stamp_and_record_replace_nothing(self):
        self.publish()
        before = {
            path: os.stat(path)
            for path in (self.path, currency.sidecar(self.path))
        }

        replaced = self.replacements(self.publish)

        self.assertEqual(replaced, [])
        for path, previous in before.items():
            current = os.stat(path)
            self.assertEqual(current.st_ino, previous.st_ino)
            self.assertEqual(current.st_mtime_ns, previous.st_mtime_ns)
            self.assertEqual(current.st_ctime_ns, previous.st_ctime_ns)

    def test_equal_text_with_new_metadata_restamps_without_text_replace(self):
        self.publish()
        old_inode = os.stat(self.path).st_ino
        moved = self.stamp + 1_000_000

        replaced = self.replacements(lambda: self.publish(
            stamp=moved, fingerprint='new-fingerprint'))

        self.assertEqual(replaced, [
            os.path.realpath(currency.sidecar(self.path)),
        ])
        self.assertEqual(os.stat(self.path).st_ino, old_inode)
        self.assertEqual(os.stat(self.path).st_mtime_ns, moved)
        self.assertEqual(currency.recorded_digest(self.path), 'digest')
        self.assertEqual(currency.recorded_fingerprint(self.path),
                         'new-fingerprint')

    def test_changed_text_atomically_replaces_text_and_record(self):
        self.publish()

        replaced = self.replacements(
            lambda: self.publish(content='cube(2);', digest='new-digest'))

        self.assertEqual(replaced, [
            os.path.realpath(self.path),
            os.path.realpath(currency.sidecar(self.path)),
        ])
        with open(self.path) as source:
            self.assertEqual(source.read(), 'cube(2);')
        self.assertEqual(currency.recorded_digest(self.path), 'new-digest')
