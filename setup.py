#!/usr/bin/env python
# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""The setup script."""

import subprocess
from setuptools import setup, find_packages
from setuptools.command.sdist import sdist

class DistWithFrontend(sdist):
    # Build the web application inside the python library
    def run(self):
        viewer_dir = 'solid_node/viewers/web/app/'
        subprocess.check_call(['npm', 'install'], cwd=viewer_dir)
        subprocess.check_call(['npm', 'run', 'build'], cwd=viewer_dir)
        sdist.run(self)

setup(
    author="Luis Fagundes",
    author_email='lhfagundes@gmail.com',
    version='0.2',
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
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
        "unicorn==2.0.*",
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
    },
    zip_safe=False,
)
