#!/usr/bin/env python

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
    version='0.0.5',
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
        "pyinotify==0.9.6",
        "trimesh==4.4.*",
        "solidpython2==2.1.*",
        "cadquery==2.4.*",
        "unicorn==2.0.*",
        "httpx==0.27.*",
        "fastapi==0.111.*",
        "termcolor==2.4.*",
        "websockets==12.*",
        "GitPython==3.1.*",
        "asgiref==3.8.*",
        "uvicorn==0.30.*",
        "numpy<2",
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
