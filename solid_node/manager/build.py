# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import sys

from solid_node.core.builder import Builder, BuildOutcome
from solid_node.core.loader import (
    AmbiguousNodeError, ProjectManifestError, resolve_node,
)
from solid_node.core.processes import Process


MODEL_NOT_FOUND = 66


def build_once(path, overrides):
    """One build pass, in its own fresh interpreter.

    Module level, and taking plain values, because the subprocess this runs
    in does not inherit this one's memory -- it is handed this function and
    its arguments to reconstruct. See `solid_node.core.processes`.
    """
    Builder(
        path,
        watch=False,
        lifecycle=True,
        overrides=overrides,
    ).start()


class Build:
    """Build a node once and publish its complete current artifacts."""

    needs_node = True

    def add_arguments(self, parser):
        pass

    def handle(self, args):
        self.path = args.path
        self.overrides = list(getattr(args, 'set', None) or [])
        try:
            resolve_node(self.path)
        except (ProjectManifestError, AmbiguousNodeError) as error:
            # The reference did not name a node. Report why -- an ambiguous
            # file, a class outside the project and a missing file are
            # different problems, and "Model not found" describes only one of
            # them. Anything else is a bug and keeps its traceback.
            sys.stderr.write(f'Model not found: {error}\n')
            sys.exit(MODEL_NOT_FOUND)

        while True:
            proc = Process(target=build_once,
                           args=(self.path, self.overrides))
            proc.start()
            proc.join()
            if proc.exitcode in (BuildOutcome.RENDERED.value,
                                 BuildOutcome.SOURCE_CHANGED.value):
                continue
            if proc.exitcode == BuildOutcome.CURRENT.value:
                return
            sys.exit(proc.exitcode or BuildOutcome.FAILED.value)
