# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Artifact freshness on a filesystem coarser than a nanosecond.

build-pipeline's Mtime-equality caching requires an artifact to be current
when its stamp is the one the framework gave it. Deciding that from a
floating-point timestamp cannot honour it off a nanosecond-resolution
filesystem: reading a source mtime as a double and handing it back to
`os.utime` makes CPython floor to a timespec a nanosecond or two low,
which a coarser filesystem then truncates across a quantum boundary about
half the time. A whole quantum disappears and nothing ever reports
current.

Observed for real, not imagined: solid-node 0.5.1 under Emscripten MEMFS
failed freshness in 13 of 25 generations, every failure exactly one
millisecond low, against 0/25 on native ext4 (browser-engine, change
`prove-solid-node-runs-in-browser`, upstream finding 1,
`evidence/groundwork.md` task 1.4).

`coarse_fs` supplies the millisecond filesystem. The failure direction is
safe -- quantisation can only make an artifact look older -- so the whole
point of the fix is caching, and the guards below are what stop it from
being bought with staleness.
"""

import os
import shutil
import tempfile
from unittest import TestCase, mock

import cadquery as cq
from solid2 import cube

from solid_node.node import CadQueryNode, FusionNode, Solid2Node
from solid_node.node.base import StlRenderStart

from . import coarse_fs
from .base import BaseNodeTest
from .coarse_fs import (PINNED_STAMP_NS, MILLISECOND_NS, SECOND_NS,
                        float_to_ns, millisecond_filesystem, stamp,
                        truncate_to_ms)


class ExactLeaf(CadQueryNode):
    """Exact, so it carries a .brep beside its .stl (ADR-044)."""

    def render(self):
        return cq.Workplane('XY').box(2, 2, 2)


class ExactRing(CadQueryNode):

    def render(self):
        return cq.Workplane('XY').circle(2).circle(1).extrude(2)


class FacetedLeaf(Solid2Node):
    """Faceted, so its .stl comes back from an OpenSCAD subprocess and is
    stamped by StlRenderStart.finish rather than by the exact writer."""

    def render(self):
        return cube(2)


class ExactFusion(FusionNode):
    """All-exact: writes its BREP and tessellates in process (ADR-045)."""

    def __init__(self):
        self.ring = ExactRing()
        self.leaf = ExactLeaf()
        super().__init__()

    def render(self):
        return [self.ring, self.leaf]


def count_renders(NodeClass):
    """Patch NodeClass.render to count calls while still rendering."""
    calls = []
    original = NodeClass.render

    def counting(self):
        calls.append(self)
        return original(self)

    return calls, mock.patch.object(NodeClass, 'render', counting)


class EmulatorPremiseTest(TestCase):
    """The fixture before the framework.

    A test whose emulator is wrong proves nothing, and a stamp that
    happened to survive the float path would pass for the wrong reason.
    Both premises are asserted here so a platform that changed either one
    fails loudly instead of quietly certifying nothing.
    """

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, 'artifact')
        with open(self.path, 'w') as handle:
            handle.write('x')

    def test_float_to_ns_matches_what_this_platform_actually_stores(self):
        """The emulator models CPython's float->timespec floor. If it
        models it wrongly, every result below is an artifact of the
        fixture rather than of the framework."""
        for millisecond in range(500, 600):
            requested = (PINNED_STAMP_NS
                         - 540 * MILLISECOND_NS
                         + millisecond * MILLISECOND_NS) / 1e9
            os.utime(self.path, (requested, requested))
            self.assertEqual(os.stat(self.path).st_mtime_ns,
                             float_to_ns(requested),
                             f'model diverges at {requested!r}')

    def test_the_pinned_stamp_loses_a_millisecond_through_the_float_path(self):
        """Why this stamp and not another: half of all whole-millisecond
        stamps survive, so an arbitrary one would be a coin flip."""
        with millisecond_filesystem():
            as_float = PINNED_STAMP_NS / 1e9
            os.utime(self.path, (as_float, as_float))

        self.assertEqual(os.stat(self.path).st_mtime_ns,
                         PINNED_STAMP_NS - MILLISECOND_NS)

    def test_the_pinned_stamp_is_a_fixed_point_through_the_ns_path(self):
        """And why the fix is expected to work at all: the value came off
        this filesystem already quantised, so re-storing it is a no-op."""
        with millisecond_filesystem():
            os.utime(self.path, ns=(PINNED_STAMP_NS, PINNED_STAMP_NS))

        self.assertEqual(os.stat(self.path).st_mtime_ns, PINNED_STAMP_NS)

    def test_half_of_all_whole_millisecond_stamps_lose_one(self):
        """The measured rate behind the spike's 13-of-25."""
        lost = sum(
            1 for millisecond in range(1000)
            if truncate_to_ms(float_to_ns(
                (1787402869 * SECOND_NS + millisecond * MILLISECOND_NS) / 1e9
            )) != 1787402869 * SECOND_NS + millisecond * MILLISECOND_NS
        )
        self.assertGreater(lost, 300)
        self.assertLess(lost, 700)


class CoarseFilesystemTest(BaseNodeTest):
    """Nodes built on a filesystem that records only to the millisecond."""

    def setUp(self):
        super().setUp()
        self._restore = {}

    def tearDown(self):
        for path, mtime_ns in self._restore.items():
            stamp(path, mtime_ns)
        super().tearDown()

    def quantise_sources(self, node, mtime_ns=PINNED_STAMP_NS):
        """Give every file the node tracks a whole-millisecond mtime.

        This is what a project unpacked into MEMFS looks like: the
        filesystem could not have recorded anything finer. Restored after
        the test so the suite's other mtime-sensitive fixtures are left
        as they were found.
        """
        for path in node.files:
            real = os.path.realpath(path)
            self._restore.setdefault(real, os.stat(real).st_mtime_ns)
            stamp(real, mtime_ns)

    def build_stls_bounded(self, node, limit=3):
        """What `build_stls()` does, with a bound.

        `build_stls()` loops `while True` until nothing reports stale. On
        a filesystem that cannot record the stamp, nothing ever stops
        reporting stale, so it does not merely rebuild -- it never
        returns, re-running OpenSCAD forever. Bounded here so the suite
        reports that instead of hanging on it.
        """
        for attempt in range(limit):
            try:
                node.trigger_stl()
                return attempt
            except StlRenderStart as job:
                job.wait()
        self.fail(
            f'build_stls() did not converge in {limit} passes: every '
            'artifact reported stale immediately after being written, so '
            'the loop would spin forever')

    def assertArtifactsCurrent(self, node, *paths):
        for path in paths:
            self.assertTrue(
                node._up_to_date(path),
                f'{os.path.basename(path)} is not current: it carries '
                f'{os.stat(path).st_mtime_ns} ns and the node reports '
                f'{node.mtime!r} '
                f'({float_to_ns(node.mtime)} ns as a float)')

    def test_exact_leaf_caches_on_a_millisecond_filesystem(self):
        """A CadQuery leaf's .stl, .scad and .brep must all report current
        after a build whose stamps could only be recorded to the
        millisecond."""
        with millisecond_filesystem():
            node = ExactLeaf()
            self.quantise_sources(node)
            node.assemble()

            self.assertArtifactsCurrent(node, node.stl_file, node.scad_file,
                                        node.brep_file)

    def test_an_unchanged_exact_leaf_is_not_rebuilt(self):
        """The consequence that matters to a user: the second build does
        no work. Under the defect every build was a cold build."""
        with millisecond_filesystem():
            first = ExactLeaf()
            self.quantise_sources(first)
            first.assemble()

            calls, patched = count_renders(ExactLeaf)
            with patched:
                ExactLeaf().assemble()

        self.assertEqual(calls, [],
                         'render() ran for a leaf whose artifacts were '
                         'already on disk and already current')

    def test_exact_fusion_caches_both_artifacts(self):
        """An all-exact fusion writes its BREP and tessellates in process
        (ADR-045); both artifacts obey the same rule (ADR-044)."""
        with millisecond_filesystem():
            fusion = ExactFusion()
            self.quantise_sources(fusion)
            fusion.assemble()
            self.build_stls_bounded(fusion)

            self.assertArtifactsCurrent(fusion, fusion.stl_file,
                                        fusion.brep_file)

    def test_faceted_leaf_caches_on_a_millisecond_filesystem(self):
        """The OpenSCAD path stamps its STL in StlRenderStart.finish and
        its scad in _atomic_write_text -- different writers, same rule."""
        if shutil.which('openscad') is None:
            self.skipTest('openscad is not installed')

        with millisecond_filesystem():
            node = FacetedLeaf()
            self.quantise_sources(node)
            node.assemble()
            self.build_stls_bounded(node)

            self.assertArtifactsCurrent(node, node.stl_file, node.scad_file)

    def test_an_edited_source_is_never_current(self):
        """The guard. Caching may not be bought with staleness: a source
        that moved must invalidate whatever the timestamp resolution, and
        this passes before the fix as well as after it."""
        with millisecond_filesystem():
            built = ExactLeaf()
            self.quantise_sources(built)
            built.assemble()

            stamp(os.path.realpath(built.src), PINNED_STAMP_NS + SECOND_NS)

            rebuilt = ExactLeaf()
            self.assertFalse(rebuilt._up_to_date(rebuilt.stl_file))
            self.assertFalse(rebuilt._up_to_date(rebuilt.brep_file))

    def test_a_sub_millisecond_edit_is_never_current(self):
        """The same guard at the resolution the filesystem cannot see.
        An edit one millisecond later is the smallest change this
        filesystem can record, and it must still invalidate."""
        with millisecond_filesystem():
            built = ExactLeaf()
            self.quantise_sources(built)
            built.assemble()

            stamp(os.path.realpath(built.src),
                  PINNED_STAMP_NS + MILLISECOND_NS)

            rebuilt = ExactLeaf()
            self.assertFalse(rebuilt._up_to_date(rebuilt.stl_file))


class NativeFilesystemTest(BaseNodeTest):
    """No emulator. Exact equality on a nanosecond filesystem is what the
    framework has always promised, and this change may not cost it."""

    def test_public_mtime_is_bit_identical_to_the_operating_system(self):
        """`mtime` is published per node in the viewer document, so moving
        the build onto integer nanoseconds may not shift its last bit.

        `mtime_ns / 1e9` does shift it: at the current epoch the integer
        is past 2**53, so converting it to a double before dividing lands
        on a different double than the OS's own `sec + 1e-9 * nsec` for
        about a quarter of all timestamps.
        """
        node = ExactLeaf()
        newest = max(os.path.getmtime(path) for path in node.files)

        self.assertEqual(node.mtime, newest)
        self.assertEqual(node.mtime_ns,
                         max(os.stat(path).st_mtime_ns
                             for path in node.files))

    def test_exact_equality_still_holds_natively(self):
        node = ExactLeaf()
        node.assemble()

        self.assertTrue(node._up_to_date(node.stl_file))
        self.assertTrue(node._up_to_date(node.scad_file))
        self.assertTrue(node._up_to_date(node.brep_file))
        self.assertEqual(os.stat(node.stl_file).st_mtime_ns,
                         os.stat(node.brep_file).st_mtime_ns)
