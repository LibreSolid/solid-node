# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import sys
from multiprocessing import Process

from solid_node.core.builder import Builder, BuildOutcome
from solid_node.core.loader import (
    AmbiguousNodeError, ProjectManifestError, resolve_node,
)


MODEL_NOT_FOUND = 66


class Build:
    """Build a node once and publish its complete current artifacts."""

    needs_node = True

    def add_arguments(self, parser):
        pass

    def builder(self):
        Builder(
            self.path,
            watch=False,
            lifecycle=True,
        ).start()

    def handle(self, args):
        self.path = args.path
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
            proc = Process(target=self.builder)
            proc.start()
            proc.join()
            if proc.exitcode in (BuildOutcome.RENDERED.value,
                                 BuildOutcome.SOURCE_CHANGED.value):
                continue
            if proc.exitcode == BuildOutcome.CURRENT.value:
                return
            sys.exit(proc.exitcode or BuildOutcome.FAILED.value)
