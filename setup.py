#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ ]

test_requirements = ['pytest>=3', ]

setup(
    author="Luis Fagundes",
    author_email='lhfagundes@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="A framework to develop and manage solid projects in Python",
    entry_points={
        'console_scripts': [
            'solid=solid_node.manager:manage',
        ],
    },
    install_requires=requirements,
    license='GNU Affero General Public License v3 or later',
    long_description=readme + '\n\n' + history,
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
