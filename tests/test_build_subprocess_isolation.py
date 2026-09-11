# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A build subprocess must not inherit the parent's native runtime state.

`solid build` resolves the model in its own process, to tell a missing model
from a failed build. That import runs the model's geometry, which leaves
OCCT's OpenMP worker team live in the command process. If the build subprocess
is then forked, it inherits libgomp's record of that team but none of its
threads, and the first parallel OCCT call -- tessellation during STL export --
waits on a barrier no thread will ever reach. The build does not fail. It
stops, at no CPU, forever.

The tests here are slow by construction: proving a process does not hang means
waiting for it. They are also quiet on a warm build directory, which is why
they render geometry rather than reusing an artifact.
"""

import os
import pickle
import tempfile
from unittest import TestCase

# A generous ceiling. The isolated child does this work in well under a
# second; anything approaching this bound is a hang, not slow arithmetic.
OUTCOME_TIMEOUT = 120


def _tessellate(done_path):
    """Do the work that deadlocks in a child forked from a threaded parent.

    Module level, and takes a path rather than a queue, so that it survives
    being reconstructed in a fresh interpreter.
    """
    import cadquery as cq

    solid = cq.Workplane().box(10, 10, 10).edges().fillet(1)
    with tempfile.TemporaryDirectory() as directory:
        solid.val().exportStl(os.path.join(directory, 'part.stl'),
                              tolerance=0.05, angularTolerance=0.05)
    with open(done_path, 'w') as stream:
        stream.write('done')


def _spin_native_worker_team():
    """Leave the calling process in the state `solid build` is in after it
    has resolved a model: native worker threads up and idle."""
    import cadquery as cq

    solid = cq.Workplane().box(10, 10, 10).edges().fillet(1)
    with tempfile.TemporaryDirectory() as directory:
        solid.val().exportStl(os.path.join(directory, 'part.stl'),
                              tolerance=0.05, angularTolerance=0.05)
    # How many threads this process has now, not how many this call added:
    # under a full suite run an earlier test may already have spun the team,
    # and a team that is already up is exactly the state being guarded
    # against, not a reason to skip the check.
    return len(os.listdir('/proc/self/task'))


class BuildSubprocessReachesAnOutcomeTest(TestCase):

    def test_child_of_a_threaded_parent_finishes_its_work(self):
        from solid_node.manager.build import Process

        threads = _spin_native_worker_team()
        # If geometry in this process leaves no worker threads behind, the
        # test is not exercising what it claims to.
        self.assertGreater(
            threads, 1,
            'parent has no native worker team; the deadlock this test guards '
            'against cannot be reproduced without one')

        with tempfile.TemporaryDirectory() as directory:
            done = os.path.join(directory, 'done')
            child = Process(target=_tessellate, args=(done,))
            child.start()
            try:
                child.join(OUTCOME_TIMEOUT)
                alive = child.is_alive()
            finally:
                if child.is_alive():
                    child.kill()
                    child.join()

            self.assertFalse(
                alive,
                f'build subprocess did not reach an outcome in '
                f'{OUTCOME_TIMEOUT}s: it inherited the parent native worker '
                f'team and is waiting on threads that do not exist in it')
            self.assertEqual(child.exitcode, 0)
            self.assertTrue(os.path.exists(done))


class SubprocessTargetsSurviveAFreshInterpreterTest(TestCase):
    """A child that does not inherit the parent's memory is handed its target
    instead. A target that cannot be reconstructed fails at process start, at
    a user's first build, far from whatever made it unreconstructable -- so
    the suite checks every one of them.
    """

    def _assert_calls_picklable(self, command, calls):
        self.assertTrue(calls, f'{command} started no subprocess')
        for index, call_args in enumerate(calls):
            with self.subTest(subprocess=index):
                payload = (call_args.kwargs.get('target'),
                           call_args.kwargs.get('args', ()))
                try:
                    pickle.loads(pickle.dumps(payload))
                except Exception as error:
                    self.fail(
                        f'{command} subprocess {index} cannot be '
                        f'reconstructed in a fresh interpreter: '
                        f'{type(error).__name__}: {error}')

    def test_build_subprocess_targets(self):
        from argparse import Namespace
        from unittest.mock import MagicMock, patch

        from solid_node.core.builder import BuildOutcome
        from solid_node.manager.build import Build

        current = MagicMock(exitcode=BuildOutcome.CURRENT.value)
        with patch('solid_node.manager.build.resolve_node'), \
             patch('solid_node.manager.build.Process',
                   return_value=current) as process:
            Build().handle(Namespace(path='model.py'))

        self._assert_calls_picklable('solid build', process.call_args_list)

    def test_develop_subprocess_targets(self):
        from argparse import ArgumentParser, Namespace
        from unittest.mock import MagicMock, patch

        from solid_node.manager.develop import Develop

        command = Develop()
        # add_arguments is how the CLI reaches this command, and it is what
        # leaves an unpicklable ArgumentParser on the command object.
        command.add_arguments(ArgumentParser())
        args = Namespace(path='model.py', web=False, web_dev=False,
                         debug_builder=False, no_web=True, callback=None)

        started = []

        def record(*call_args, **call_kwargs):
            child = MagicMock()
            # Ends the otherwise-infinite watch loop the way a real
            # KeyboardInterrupt during join() does.
            child.join.side_effect = KeyboardInterrupt
            started.append(child)
            return child

        with patch('solid_node.manager.develop.Process',
                   side_effect=record) as process:
            with self.assertRaises(SystemExit):
                command.handle(args)

        self._assert_calls_picklable('solid develop', process.call_args_list)
