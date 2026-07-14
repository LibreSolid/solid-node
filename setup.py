#!/usr/bin/env python
# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The setup script."""

import os
import subprocess
from setuptools import setup, find_packages
from setuptools.command.sdist import sdist
from setuptools.command.build_py import build_py

VIEWER_DIR = 'solid_node/viewers/web/app/'
VIEWER_BUILD_INDEX = os.path.join(VIEWER_DIR, 'build', 'index.html')


def build_frontend():
    # Build the web application inside the python library
    subprocess.check_call(['npm', 'install'], cwd=VIEWER_DIR)
    subprocess.check_call(['npm', 'run', 'build'], cwd=VIEWER_DIR)


class DistWithFrontend(sdist):
    # sdist always ships a freshly built frontend
    def run(self):
        build_frontend()
        sdist.run(self)


class BuildPyWithFrontend(build_py):
    # Wheels (and `pip install .`) go through build_py rather than sdist, so
    # they need their own hook or they ship without app/build and the web
    # viewer 404s. Only (re)build when the compiled frontend is missing, so
    # this doesn't run npm on every test/import of setup.py.
    def run(self):
        if not os.path.exists(VIEWER_BUILD_INDEX):
            build_frontend()
        super().run()


setup(
    author="Luis Fagundes",
    author_email='lhfagundes@gmail.com',
    version='0.3.0',
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    description="A framework to develop and manage mechanical projects in Python",
    entry_points={
        'console_scripts': [
            'solid=solid_node.cli:manage',
        ],
    },
    install_requires=[
        "watchdog",
        "trimesh==4.4.*",
        "solidpython2==2.1.*",
        "cadquery==2.5.*",
        "httpx==0.27.*",
        "fastapi==0.111.*",
        "termcolor==2.4.*",
        "asgiref==3.8.*",
        "uvicorn==0.30.*",
        "numpy==2.2.*",
        "manifold3d",
    ],
    license="GNU Affero General Public License v3",
    include_package_data=True,
    keywords='solid_node',
    name='solid_node',
    packages=find_packages(include=['solid_node', 'solid_node.*']),
    test_suite='tests',
    tests_require=['pytest>=3'],
    url='https://github.com/lfagundes/solid_node',
    cmdclass={
        'sdist': DistWithFrontend,
        'build_py': BuildPyWithFrontend,
    },
    zip_safe=False,
)
