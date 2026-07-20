# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Setuptools hooks needed to package the bundled web viewer."""

from pathlib import Path
import subprocess

from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


VIEWER_DIR = Path(__file__).parent / "viewers" / "web" / "app"
VIEWER_BUILD_INDEX = VIEWER_DIR / "build" / "index.html"


def build_frontend():
    """Build the web viewer included in source distributions and wheels."""
    subprocess.check_call(["npm", "ci"], cwd=VIEWER_DIR)
    subprocess.check_call(["npm", "run", "build"], cwd=VIEWER_DIR)


class BuildSourceDistribution(sdist):
    """Ensure a source distribution contains a freshly built viewer."""

    def run(self):
        build_frontend()
        super().run()


class BuildPythonWithFrontend(build_py):
    """Build a missing viewer before creating a wheel from the checkout."""

    def run(self):
        if not VIEWER_BUILD_INDEX.exists():
            build_frontend()
        super().run()
