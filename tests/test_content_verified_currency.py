# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Currency when a timestamp moved and the content did not.

build-pipeline's Mtime-equality caching decides currency by comparing an
artifact's stamp with the maximum mtime across the node's tracked sources.
That is precise about edits and blind to content: a clone, a branch
switch, a stash pop, a copy, or a formatter rewriting a file with
identical bytes moves the stamp and changes nothing the model depends on,
and every artifact in the project is re-derived. Measured on a 22-part
CadQuery project, `touch`ing every source with zero content change turned
a 6.05 s settled rebuild into 35.66 s.

The requirement now says that when, and only when, mtime equality fails,
the build compares a digest of the node's tracked sources against the
digest recorded when the artifact was written. The tests here are the two
halves of that, and the second half is the one that matters: sparing a
rebuild is worth nothing if it can ever spare one that was needed. A
stale model reported as fresh is the failure ADR-006 says the system
cannot survive.

The fixture is a project of its own, written to a temporary directory,
because these tests must edit source files -- and moving a timestamp is
no longer an edit.
"""

import asyncio
import hashlib
import itertools
import json
import os
import shutil
import tempfile
import time
from unittest import TestCase
from unittest.mock import patch

from solid_node import currency
from solid_node.core.builder import Builder, BuildOutcome
from solid_node.core.loader import load_node


# Each test gets its own project package name. The loader keeps imported
# project modules in sys.modules, and two temporary projects sharing a
# dotted name would have to fight over that entry.
PROJECT_NAMES = itertools.count()


TRACE = '''\
import os


def record(name):
    with open(os.environ['SOLID_NODE_RENDER_LOG'], 'a') as log:
        log.write(name + '\\n')
'''

DIMENSIONS = '''\
SIZE = 4.0
'''

BLOCK = '''\
import cadquery as cq

from solid_node.node import CadQueryNode

from . import trace
from .dimensions import SIZE


class Block(CadQueryNode):

    def render(self):
        trace.record('Block')
        return cq.Workplane('XY').box(SIZE, SIZE, SIZE)
'''

PIN = '''\
import cadquery as cq

from solid_node.node import CadQueryNode

from . import trace


class Pin(CadQueryNode):
    """A second leaf that shares nothing with Block but the project."""

    def render(self):
        trace.record('Pin')
        return cq.Workplane('XY').circle(1.0).extrude(6.0)
'''

MACHINE = '''\
from solid_node.node import AssemblyNode

from .block import Block
from .pin import Pin


class Machine(AssemblyNode):

    def __init__(self):
        self.block = Block()
        self.pin = Pin()
        super().__init__()

    def render(self):
        self.pin.translate([10, 0, 0])
        return [self.block, self.pin]
'''


class ScratchProjectTest(TestCase):
    """A real CadQuery project, in a directory the test owns.

    Exact leaves on purpose: this workspace's projects are overwhelmingly
    exact, an exact leaf carries a `.brep` beside its `.stl` (ADR-044),
    and both must answer this rule the same way or the node reports
    half-current and rebuilds anyway.
    """

    def setUp(self):
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)

        self.root = tempfile.mkdtemp(prefix='solid-node-currency-')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.package = f'currency_fixture_{next(PROJECT_NAMES)}'
        package_dir = os.path.join(self.root, self.package)
        os.makedirs(package_dir)

        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as manifest:
            manifest.write('[tool.solid-node]\n'
                           f'model = "{self.package}.machine:Machine"\n')
        for name, content in (('__init__.py', ''), ('trace.py', TRACE),
                              ('dimensions.py', DIMENSIONS),
                              ('block.py', BLOCK), ('pin.py', PIN),
                              ('machine.py', MACHINE)):
            self.write(name, content)

        self.build_dir = os.path.join(self.root, '_build')
        os.environ['SOLID_BUILD_DIR'] = self.build_dir
        self.render_log = os.path.join(self.root, 'renders.log')
        os.environ['SOLID_NODE_RENDER_LOG'] = self.render_log
        self.reference = os.path.join(package_dir, 'machine.py') + ':Machine'

    ##############################################
    # The project

    def write(self, name, content):
        path = os.path.join(self.root, self.package, name)
        with open(path, 'w') as source:
            source.write(content)
        return path

    def sources(self):
        directory = os.path.join(self.root, self.package)
        return [os.path.join(directory, name)
                for name in sorted(os.listdir(directory))
                if name.endswith('.py')]

    def rewrite_timestamps(self):
        """What a clone, a branch switch or a copy does: every source
        stamped with the time it was written, not one byte changed."""
        moved = time.time_ns() + 10 ** 9
        for path in self.sources():
            os.utime(path, ns=(moved, moved))
        return moved

    ##############################################
    # Building

    def build(self):
        node = load_node(self.reference)
        node.assemble()
        node.build_stls()
        return node

    def publish(self):
        """A complete build, through the builder that publishes and sweeps."""
        builder = Builder(self.reference, build_dir=self.build_dir,
                          watch=False)
        outcome = asyncio.run(builder._start())
        self.assertEqual(outcome, BuildOutcome.CURRENT)
        return builder

    def renders(self):
        """Which leaves ran render() since the log was last read."""
        try:
            with open(self.render_log) as log:
                recorded = log.read().split()
        except FileNotFoundError:
            return []
        os.remove(self.render_log)
        return sorted(recorded)

    ##############################################
    # The build directory

    def artifacts(self):
        """Every artifact in the build directory.

        Not the digests, which are the mechanism under test rather than
        an output, and not the document, which records each node's source
        mtime and therefore MUST change when a source mtime moves.
        """
        found = {}
        for root, _, names in os.walk(self.build_dir):
            for name in names:
                if (name.endswith(currency.SIDECAR_SUFFIX)
                        or name in ('viewer.json', 'errors.json')):
                    continue
                path = os.path.join(root, name)
                found[os.path.relpath(path, self.build_dir)] = path
        return found

    def contents(self):
        return {relative: hashlib.sha256(open(path, 'rb').read()).hexdigest()
                for relative, path in self.artifacts().items()}

    def stamps(self):
        return {relative: os.stat(path).st_mtime_ns
                for relative, path in self.artifacts().items()}

    def document(self):
        """The published document with every recorded source mtime removed.

        A pure timestamp rewrite genuinely does move `node.mtime`, and the
        document publishes it per node, so the document cannot be
        byte-identical across one -- it never has been. What must not
        change is the model it describes: the tree, the names, and the
        artifacts it makes reachable.
        """
        with open(os.path.join(self.build_dir, 'viewer.json')) as published:
            snapshot = json.load(published)

        def strip(node):
            node.pop('mtime', None)
            for child in node.get('children', []):
                strip(child)

        strip(snapshot['root'])
        return snapshot


class ContentVerifiedCurrencyTest(ScratchProjectTest):
    """Task 1.2 and its guards: what the fallback must and must not do."""

    def test_a_pure_mtime_rewrite_re_derives_no_geometry(self):
        """The measured case, in one test: every source stamped anew with
        no byte changed must cost nothing."""
        node = self.build()
        self.assertEqual(self.renders(), ['Block', 'Pin'])
        before = self.contents()
        settled = node.mtime_ns

        moved = self.rewrite_timestamps()
        self.assertNotEqual(moved, settled, 'the fixture moved no timestamp')
        rebuilt = self.build()

        self.assertEqual(self.renders(), [],
                         'geometry was re-derived for sources that had not '
                         'changed a byte')
        self.assertEqual(self.contents(), before,
                         'an artifact changed while nothing was rebuilt')
        self.assertEqual(rebuilt.mtime_ns, moved)
        self.assertEqual(set(self.stamps().values()), {moved},
                         'an artifact was left carrying the old stamp')

    def test_a_pure_mtime_rewrite_leaves_the_published_model_alone(self):
        self.publish()
        self.renders()
        before = self.document()
        artifacts = self.contents()

        self.rewrite_timestamps()
        self.publish()

        self.assertEqual(self.renders(), [])
        self.assertEqual(self.document(), before)
        self.assertEqual(self.contents(), artifacts)

    def test_a_source_rewritten_with_different_content_still_rebuilds(self):
        """The safety test. The fallback may only ever spare a rebuild
        that would have reproduced the same artifact."""
        node = self.build()
        self.renders()

        self.write('dimensions.py', 'SIZE = 6.0\n')

        stale = load_node(self.reference)
        self.assertFalse(stale.block._up_to_date(stale.block.stl_file))
        self.assertFalse(stale.block._up_to_date(stale.block.brep_file))
        self.assertFalse(stale.block._up_to_date(stale.block.scad_file))

        self.build()

        self.assertIn('Block', self.renders(),
                      'a leaf whose source changed was not re-derived')

    def test_an_edit_is_not_forgiven_by_a_later_identical_rebuild(self):
        """The digest recorded must be the digest of the sources that
        produced the artifact, so an edit stays visible until the artifact
        catches up with it."""
        self.build()
        self.renders()
        block = load_node(self.reference).block
        recorded = currency.recorded_digest(block.stl_file)

        self.write('dimensions.py', 'SIZE = 6.0\n')
        self.build()

        rebuilt = load_node(self.reference).block
        self.assertNotEqual(currency.recorded_digest(rebuilt.stl_file),
                            recorded)
        self.assertEqual(currency.recorded_digest(rebuilt.stl_file),
                         rebuilt.source_digest)

    def test_the_fast_path_reads_no_source_for_a_digest(self):
        """When mtime equality succeeds it decides alone, so the common
        path costs exactly what it always did."""
        node = self.build()

        with patch('solid_node.currency.source_digest') as digest, \
             patch('solid_node.currency.recorded_digest') as recorded:
            self.assertTrue(node.block._up_to_date(node.block.stl_file))
            self.assertTrue(node.block._up_to_date(node.block.brep_file))

        digest.assert_not_called()
        recorded.assert_not_called()

    def test_an_artifact_with_no_recorded_digest_rebuilds_and_gains_one(self):
        """What every build directory produced before this rule looks
        like: artifacts, and nothing vouching for them."""
        node = self.build()
        self.renders()
        for relative, path in self.artifacts().items():
            currency.drop(path)

        self.rewrite_timestamps()
        stale = load_node(self.reference)
        self.assertFalse(stale.block._up_to_date(stale.block.stl_file))

        rebuilt = self.build()

        self.assertEqual(self.renders(), ['Block', 'Pin'])
        self.assertEqual(currency.recorded_digest(rebuilt.block.stl_file),
                         rebuilt.block.source_digest)

    def test_an_unreadable_source_is_never_current(self):
        """A build about to fail on its own terms must not certify an
        artifact on the way there.

        `mtime_ns` has always raised for a source that cannot be stat'ed,
        and still does -- a missing file is a build failure, not a cache
        question. What matters here is that the fallback added beneath it
        refuses rather than answering from a digest it could not compute.
        """
        node = self.build()
        self.rewrite_timestamps()
        os.remove(os.path.join(self.root, self.package, 'dimensions.py'))

        self.assertIsNone(node.block.source_digest)
        self.assertFalse(node.block._content_verified(node.block.stl_file))
        with self.assertRaises(FileNotFoundError):
            node.block._up_to_date(node.block.stl_file)

    def test_the_stl_and_the_brep_restamp_together(self):
        """An exact node is current only when both its artifacts are, so a
        fallback that restamped one of them would deliver nothing at all
        (ADR-044, ADR-047)."""
        self.build()
        moved = self.rewrite_timestamps()

        node = load_node(self.reference)

        self.assertTrue(node.block._up_to_date(node.block.stl_file))
        self.assertTrue(node.block._up_to_date(node.block.brep_file))
        self.assertEqual(os.stat(node.block.stl_file).st_mtime_ns, moved)
        self.assertEqual(os.stat(node.block.brep_file).st_mtime_ns, moved)

        builder = Builder(self.reference, build_dir=self.build_dir,
                          watch=False)
        builder.node = node
        self.assertTrue(builder._artifacts_are_current())

    def test_an_unrelated_leaf_keeps_its_own_answer(self):
        """The fallback is per node, over that node's own tracked set: a
        real edit to one leaf's dependency does not spare the other, and
        does not condemn it either."""
        self.build()
        self.renders()

        self.write('dimensions.py', 'SIZE = 6.0\n')
        self.build()

        self.assertEqual(self.renders(), ['Block'])


class SweptSidecarTest(ScratchProjectTest):
    """Task 4: the silent failure.

    A sweep that deletes the digest beside an artifact it keeps leaves
    every test passing and the optimisation permanently off, so this
    publishes FIRST and only then asks whether the fallback still works.
    """

    def test_the_fallback_still_fires_after_a_publication_has_swept(self):
        self.publish()
        self.renders()

        self.rewrite_timestamps()
        self.publish()

        self.assertEqual(self.renders(), [],
                         'the sweep took the digests with it: geometry was '
                         're-derived for sources that had not changed')

    def test_a_publication_keeps_the_digest_of_an_artifact_it_keeps(self):
        self.publish()

        node = load_node(self.reference)
        for artifact in (node.block.stl_file, node.block.brep_file,
                         node.pin.stl_file):
            self.assertTrue(os.path.isfile(currency.sidecar(artifact)),
                            f'{os.path.basename(artifact)} lost its digest')

    def test_a_publication_leaves_no_digest_for_an_artifact_it_removes(self):
        self.publish()
        stray = os.path.join(self.build_dir, self.package, 'superseded.stl')
        with open(stray, 'w') as artifact:
            artifact.write('solid superseded\nendsolid superseded\n')
        currency.record(stray, 'deadbeef')

        self.rewrite_timestamps()
        self.publish()

        self.assertFalse(os.path.exists(stray))
        self.assertFalse(os.path.exists(currency.sidecar(stray)),
                         'a digest outlived the artifact it described')

    def test_the_published_document_never_names_a_digest(self):
        self.publish()

        with open(os.path.join(self.build_dir, 'viewer.json')) as published:
            document = published.read()

        self.assertNotIn(currency.SIDECAR_SUFFIX, document)
