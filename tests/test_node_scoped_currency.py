# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Currency when several node classes share one source file.

build-pipeline's content-verified fallback compares a digest of a node's
tracked sources against the one recorded beside its artifact. Digested one
file at a time, two node classes in one file share a digest and re-derive
each other on every edit -- the only reason the framework ever asked for
one node class per file. The requirement now scopes the digest to the
node: a file that defines several node classes contributes to each node's
digest only the text that node can depend on, the file with its siblings'
class bodies removed, unless the retained text refers to them.

The fixture is a project whose leaves and the fusion of them all live in
one `parts.py`. Every test edits that file, so the mtime rule fails for
every node in it and the fallback decides.
"""

import hashlib
import os

from solid_node import currency
from solid_node.core.loader import load_node

from tests.test_content_verified_currency import (
    DIMENSIONS, TRACE, ScratchProjectTest)


PARTS = '''\
import cadquery as cq

from solid_node.node import CadQueryNode, FusionNode

from . import trace
from .dimensions import SIZE

PIN_RADIUS = 1.0


def pin_height():
    return SIZE * 1.5


class Block(CadQueryNode):

    def render(self):
        trace.record('Block')
        return cq.Workplane('XY').box(SIZE, SIZE, SIZE)


class Pin(CadQueryNode):

    def render(self):
        trace.record('Pin')
        return cq.Workplane('XY').circle(PIN_RADIUS).extrude(pin_height())


class Stud(FusionNode):

    def __init__(self):
        self.block = Block()
        self.pin = Pin()
        super().__init__()

    def render(self):
        self.pin.translate([0, 0, SIZE])
        return [self.block, self.pin]
'''

MACHINE = '''\
from solid_node.node import AssemblyNode

from .parts import Pin, Stud


class Machine(AssemblyNode):

    def __init__(self):
        self.stud = Stud()
        self.spare = Pin()
        super().__init__()

    def render(self):
        self.spare.translate([10, 0, 0])
        return [self.stud, self.spare]
'''

# The edit every test makes to Block and to nothing else: a different
# body, a different shape, so a fusion built from it must change too.
TALLER_BLOCK = '''\
class Block(CadQueryNode):

    def render(self):
        trace.record('Block')
        return cq.Workplane('XY').box(SIZE, SIZE, SIZE * 2)
'''


class SharedFileTest(ScratchProjectTest):

    def project_files(self):
        return (('__init__.py', ''), ('trace.py', TRACE),
                ('dimensions.py', DIMENSIONS),
                ('parts.py', PARTS), ('machine.py', MACHINE))

    def edit_block(self, source=PARTS):
        """Rewrite parts.py with Block's body changed and nothing else."""
        taller = source.replace(
            "        return cq.Workplane('XY').box(SIZE, SIZE, SIZE)\n",
            "        return cq.Workplane('XY').box(SIZE, SIZE, SIZE * 2)\n")
        assert taller != source, 'the fixture did not edit Block'
        self.write('parts.py', taller)

    def whole_file_digest(self, node):
        """The digest the previous release recorded: every tracked file
        by its bytes, scoped to nothing."""
        entries = {
            os.path.relpath(os.path.realpath(path), self.root):
            hashlib.sha256(open(path, 'rb').read()).hexdigest()
            for path in node.files
        }
        digest = hashlib.sha256()
        for relative, content in sorted(entries.items()):
            digest.update(os.fsencode(relative))
            digest.update(b'\0')
            digest.update(content.encode('ascii'))
            digest.update(b'\n')
        return digest.hexdigest()


class NodeScopedCurrencyTest(SharedFileTest):
    """Task 1.2 and its guards."""

    def test_editing_one_class_re_derives_that_node_alone(self):
        """The case this change exists for: Block, Pin and their fusion in
        one file. Editing Block must re-derive Block and the fusion, and
        must only restamp Pin."""
        self.build()
        self.assertEqual(self.renders(), ['Block', 'Pin'])
        before = self.contents()

        self.edit_block()
        rebuilt = self.build()

        self.assertEqual(self.renders(), ['Block'],
                         'a node whose class did not change was re-derived '
                         'because it shares a file with one that did')
        after = self.contents()
        pin = os.path.relpath(rebuilt.spare.stl_file, self.build_dir)
        stud = os.path.relpath(rebuilt.stud.stl_file, self.build_dir)
        self.assertEqual(after[pin], before[pin])
        self.assertNotEqual(after[stud], before[stud],
                            'a fusion of an edited leaf was not re-derived')
        self.assertEqual(set(self.stamps().values()), {rebuilt.mtime_ns},
                         'an artifact was left carrying the old stamp')

    def test_editing_shared_code_re_derives_every_node_in_the_file(self):
        """Module-level code is what every class in the file can see, so
        an edit to it is an edit to all of them."""
        self.build()
        self.renders()

        self.write('parts.py', PARTS.replace('PIN_RADIUS = 1.0',
                                             'PIN_RADIUS = 1.5'))
        self.build()
        self.assertEqual(self.renders(), ['Block', 'Pin'])

        self.write('parts.py', PARTS.replace('return SIZE * 1.5',
                                             'return SIZE * 2.0'))
        self.build()
        self.assertEqual(self.renders(), ['Block', 'Pin'])

    def test_a_subclass_follows_its_base(self):
        """A sibling reached as a base class is part of what the node is."""
        source = PARTS.replace(
            'class Pin(CadQueryNode):', 'class Pin(Block):')
        self.write('parts.py', source)
        self.build()
        self.renders()

        self.edit_block(source)
        self.build()

        self.assertEqual(self.renders(), ['Block', 'Pin'],
                         'a subclass was not re-derived when its base was')

    def test_a_node_follows_a_sibling_its_helper_names(self):
        """A reference routed through module-level code counts: the
        helper is retained, and it names the sibling."""
        source = PARTS.replace(
            'def pin_height():\n    return SIZE * 1.5\n',
            'def pin_height():\n    return SIZE * 1.5 + Block.HINT\n'
        ).replace(
            'class Block(CadQueryNode):\n',
            'class Block(CadQueryNode):\n    HINT = 0.0\n')
        self.write('parts.py', source)
        self.build()
        self.renders()

        self.write('parts.py', source.replace('HINT = 0.0', 'HINT = 0.5'))
        self.build()

        self.assertEqual(self.renders(), ['Block', 'Pin'],
                         'a node whose helper names a sibling was not '
                         're-derived when the sibling changed')

    def test_a_node_follows_a_sibling_it_names_as_a_string(self):
        """The dynamic form the scan can still see."""
        source = PARTS.replace(
            'import cadquery as cq\n', 'import sys\n\nimport cadquery as cq\n'
        ).replace(
            'def pin_height():\n    return SIZE * 1.5\n',
            "def pin_height():\n"
            "    hint = getattr(sys.modules[__name__], 'Block').HINT\n"
            "    return SIZE * 1.5 + hint\n"
        ).replace(
            'class Block(CadQueryNode):\n',
            'class Block(CadQueryNode):\n    HINT = 0.0\n')
        self.write('parts.py', source)
        self.build()
        self.renders()

        self.write('parts.py', source.replace('HINT = 0.0', 'HINT = 0.5'))
        self.build()

        self.assertEqual(self.renders(), ['Block', 'Pin'])

    def test_the_fast_path_still_reads_no_source(self):
        node = self.build()
        from unittest.mock import patch
        with patch('solid_node.currency.source_digest') as digest, \
             patch('solid_node.currency.recorded_digest') as recorded:
            self.assertTrue(node.spare._up_to_date(node.spare.stl_file))
            self.assertTrue(node.stud._up_to_date(node.stud.stl_file))
        digest.assert_not_called()
        recorded.assert_not_called()

    def test_a_multi_node_file_rebuilds_once_after_upgrading(self):
        """A build directory whose sidecars were recorded whole-file, by
        the previous release. Touched, its nodes must rebuild once -- the
        recorded digest is simply not the scoped one -- and then settle."""
        node = self.build()
        self.renders()
        for leaf in (node.spare, node.stud.block, node.stud.pin, node.stud):
            for artifact in (leaf.stl_file, leaf.brep_file):
                currency.record(artifact, self.whole_file_digest(leaf))

        self.rewrite_timestamps()
        self.build()
        self.assertEqual(self.renders(), ['Block', 'Pin'])

        self.rewrite_timestamps()
        self.build()
        self.assertEqual(self.renders(), [])


class SingleClassFileTest(ScratchProjectTest):
    """Guard 1.5: the conventional layout digests exactly as before, so
    no sidecar written by the previous release is invalidated."""

    def whole_file_digest(self, node):
        return SharedFileTest.whole_file_digest(self, node)

    def test_a_single_class_file_digests_as_it_always_has(self):
        node = self.build()
        for leaf in (node.block, node.pin):
            self.assertEqual(leaf.source_digest, self.whole_file_digest(leaf))
            self.assertEqual(currency.recorded_digest(leaf.stl_file),
                             self.whole_file_digest(leaf))

    def test_recorded_whole_file_digests_still_match(self):
        self.build()
        self.renders()
        self.rewrite_timestamps()
        self.build()
        self.assertEqual(self.renders(), [])
