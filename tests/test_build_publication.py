# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Publication is what a consumer of the build directory actually sees.

These tests exercise `BuildSessionPublisher` directly: no CAD, no
OpenSCAD, just the filesystem transition a reader can observe while a
build is published.
"""

import os
import shutil
import tempfile
import threading
from unittest import TestCase

from solid_node.core.builder import BuildSessionPublisher


class PublicationTestCase(TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='solid-node-publication-')
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.build_dir = os.path.join(self.root, '_build')

    def candidate(self, name, content):
        """A completed candidate directory ready to be published."""
        path = os.path.join(self.root, f'.candidate-{name}')
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, 'viewer.json'), 'w') as snapshot:
            snapshot.write(content)
        return path

    def publish(self, name, content):
        BuildSessionPublisher(self.candidate(name, content),
                              self.build_dir).publish()

    def published(self):
        with open(os.path.join(self.build_dir, 'viewer.json')) as snapshot:
            return snapshot.read()


class ReaderNeverSeesAMissingBuildTest(PublicationTestCase):
    """A consumer serving the build directory over HTTP must not 404 a
    model that is present before and after the publication."""

    def test_published_snapshot_is_readable_throughout_publication(self):
        self.publish('initial', 'v0')

        absent = []
        stop = threading.Event()

        def reader():
            while not stop.is_set():
                try:
                    self.published()
                except FileNotFoundError:
                    absent.append(1)

        watcher = threading.Thread(target=reader)
        watcher.start()
        try:
            for revision in range(50):
                self.publish(f'r{revision}', f'v{revision}')
        finally:
            stop.set()
            watcher.join()

        self.assertEqual(
            absent, [],
            f'reader saw the published snapshot absent {len(absent)} times')


class OverlappingPublicationsTest(PublicationTestCase):
    """A verification build may publish while a watch loop publishes.

    Only `test_concurrent_publishers_do_not_raise` is red against the
    two-rename publisher. The other two characterize properties that
    publisher already has and the symlink publisher must keep -- in
    particular that removing a superseded artifact set never removes a
    concurrent publisher's fresh one, which is a hazard the versioned
    layout introduces and the old one did not have.
    """

    def _publish_concurrently(self, tags):
        failures = []

        def worker(tag):
            try:
                self.publish(tag, tag)
            except Exception as error:              # noqa: BLE001
                failures.append(f'{tag}: {type(error).__name__}: {error}')

        threads = [threading.Thread(target=worker, args=(tag,))
                   for tag in tags]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return failures

    # One round of three publishers usually interleaves harmlessly, so a
    # single round proves nothing either way. Repeat until a collision is
    # overwhelmingly likely: the two-rename publisher this replaces fails
    # roughly once per round.
    ROUNDS = 25

    def test_concurrent_publishers_do_not_raise(self):
        self.publish('initial', 'v0')

        failures = []
        for round_ in range(self.ROUNDS):
            failures.extend(
                self._publish_concurrently([f'A{round_}', f'B{round_}',
                                            f'C{round_}']))

        self.assertEqual(failures, [])

    def test_concurrent_publishers_leave_one_complete_artifact_set(self):
        self.publish('initial', 'v0')

        for round_ in range(self.ROUNDS):
            tags = [f'A{round_}', f'B{round_}', f'C{round_}']
            self._publish_concurrently(tags)
            self.assertIn(self.published(), set(tags))

    def test_superseded_cleanup_spares_a_concurrent_publication(self):
        """Removing the tree this publication replaced must never remove
        a tree another publisher just published."""
        self.publish('initial', 'v0')

        for _ in range(20):
            self._publish_concurrently(['A', 'B'])
            # Whichever publisher won, its artifact set must still be
            # readable: the loser's cleanup must not have removed it.
            self.assertIn(self.published(), {'A', 'B'})


class GitInvisibilityTest(PublicationTestCase):
    """Published artifacts must not show up in `git status`, without the
    user editing anything and without the framework touching a tracked
    file."""

    def repository(self, gitignore=None):
        os.makedirs(os.path.join(self.root, '.git', 'info'), exist_ok=True)
        if gitignore is not None:
            with open(os.path.join(self.root, '.gitignore'), 'w') as handle:
                handle.write(gitignore)

    def exclude_file(self):
        return os.path.join(self.root, '.git', 'info', 'exclude')

    def exclude_contents(self):
        if not os.path.isfile(self.exclude_file()):
            return ''
        with open(self.exclude_file()) as handle:
            return handle.read()

    def test_pattern_is_recorded_when_gitignore_does_not_cover_it(self):
        self.repository(gitignore='_build/\nsnapshot.png\n')

        self.publish('initial', 'v0')

        self.assertIn('_build*', self.exclude_contents())

    def test_tracked_gitignore_is_never_modified(self):
        original = '_build/\nsnapshot.png\n'
        self.repository(gitignore=original)

        self.publish('initial', 'v0')

        with open(os.path.join(self.root, '.gitignore')) as handle:
            self.assertEqual(handle.read(), original)

    def test_nothing_is_recorded_when_gitignore_already_covers_it(self):
        self.repository(gitignore='_build*\nsnapshot.png\n')

        self.publish('initial', 'v0')

        self.assertNotIn('_build*', self.exclude_contents())

    def test_recording_is_idempotent(self):
        self.repository(gitignore='_build/\n')

        self.publish('first', 'v0')
        self.publish('second', 'v1')
        self.publish('third', 'v2')

        self.assertEqual(self.exclude_contents().count('_build*'), 1)

    def test_publication_succeeds_outside_a_git_repository(self):
        self.publish('initial', 'v0')

        self.assertEqual(self.published(), 'v0')
        self.assertFalse(os.path.exists(os.path.join(self.root, '.git')))

    def test_publication_succeeds_when_the_exclude_file_cannot_be_written(self):
        self.repository(gitignore='_build/\n')
        info = os.path.join(self.root, '.git', 'info')
        os.chmod(info, 0o500)
        self.addCleanup(os.chmod, info, 0o700)

        self.publish('initial', 'v0')

        self.assertEqual(self.published(), 'v0')
