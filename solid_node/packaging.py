# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Setuptools hooks needed to package the bundled web viewer."""

from dataclasses import dataclass
from pathlib import Path
import subprocess

from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist


@dataclass
class Frontend:
    directory: Path
    output: Path

    def output_exists(self):
        return self.output.exists()


DEVELOPMENT_VIEWER = Frontend(
    Path(__file__).parent / 'viewers' / 'web' / 'app',
    Path(__file__).parent / 'viewers' / 'web' / 'app' / 'build' / 'index.html',
)
WIDGET_VIEWER = Frontend(
    Path(__file__).parent / 'viewers' / 'widget',
    Path(__file__).parent / 'viewers' / 'widget' / 'dist' / 'solid-widget.js',
)


def build_frontend(frontend):
    """Build one frontend included in source distributions and wheels."""
    subprocess.check_call(['npm', 'ci'], cwd=frontend.directory)
    subprocess.check_call(['npm', 'run', 'build'], cwd=frontend.directory)


def build_distribution_frontends():
    """Build every frontend for a source distribution."""
    for frontend in (DEVELOPMENT_VIEWER, WIDGET_VIEWER):
        build_frontend(frontend)


def build_missing_frontends():
    """Build only frontend artifacts absent from a wheel checkout."""
    for frontend in (DEVELOPMENT_VIEWER, WIDGET_VIEWER):
        if not frontend.output_exists():
            build_frontend(frontend)


class BuildSourceDistribution(sdist):
    """Ensure a source distribution contains a freshly built viewer."""

    def run(self):
        build_distribution_frontends()
        super().run()


class BuildPythonWithFrontend(build_py):
    """Build a missing viewer before creating a wheel from the checkout."""

    def run(self):
        build_missing_frontends()
        super().run()
