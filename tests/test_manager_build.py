# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import io
from argparse import Namespace
from contextlib import redirect_stderr
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from solid_node.core.builder import BuildOutcome
from solid_node.manager.build import Build, MODEL_NOT_FOUND


class BuildCommandTest(TestCase):

    def test_missing_model_has_documented_exit_code(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as ctx:
            Build().handle(Namespace(path='missing-model.py'))

        self.assertEqual(ctx.exception.code, MODEL_NOT_FOUND)
        # The reason travels with the report: a reference can fail to name a
        # node in more ways than one, and the exit code distinguishes none of
        # them.
        self.assertIn('Model not found', stderr.getvalue())
        self.assertIn('missing-model.py', stderr.getvalue())

    def test_repeats_render_passes_until_current(self):
        command = Build()
        render = MagicMock(exitcode=BuildOutcome.RENDERED.value)
        current = MagicMock(exitcode=BuildOutcome.CURRENT.value)

        with patch('solid_node.manager.build.resolve_node'), \
             patch('solid_node.manager.build.Process', side_effect=[render, current]) as process:
            command.handle(Namespace(path='model.py'))

        self.assertEqual(process.call_args_list, [
            call(target=command.builder),
            call(target=command.builder),
        ])
        self.assertEqual(render.start.call_count, 1)
        self.assertEqual(current.start.call_count, 1)
