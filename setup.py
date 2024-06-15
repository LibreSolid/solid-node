#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

test_requirements = ['pytest>=3', ]

setup(
    author="Luis Fagundes",
    author_email='lhfagundes@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    description="A framework to develop and manage solid projects in Python",
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
        "uvicorn==0.30.*"
    ],
    license="GNU Affero General Public License v3",
    include_package_data=True,
    keywords='solid_node',
    name='solid_node',
    packages=find_packages(include=['solid_node', 'solid_node.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/lfagundes/solid_node',
    version='0.0.1',
    zip_safe=False,
)
