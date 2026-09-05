# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Find the browser viewer this framework does not carry.

The viewer is `solid-node-viewer`, a separately licensed package installed
through the ``viewer`` extra. It registers one entry point,
``solid_node.viewer``, whose ``bundle`` entry resolves to a function that
returns where the built bundle and the standalone export page are, and which
viewer API version the widget declares. That entry point is the whole of
what this module -- and this framework -- imports of the viewer. Everything
else the framework asks of it runs as a separate process, through
:func:`viewer_command`.

Only the standard library is imported here, so that answering costs no
browser bundle, no web framework and no CAD stack.
"""

import sys
from importlib.metadata import entry_points
from pathlib import Path

ENTRY_POINT_GROUP = 'solid_node.viewer'
ENTRY_POINT_NAME = 'bundle'
BUNDLE_NAME = 'solid-widget.js'
INSTALL_REMEDY = (
    'The browser viewer is not installed. It is the separate '
    'solid-node-viewer package; install it with: '
    'pip install "solid-node[viewer]"'
)


class ViewerUnavailable(Exception):
    """No usable viewer is installed; the message is the remedy."""


def _entry():
    for entry in entry_points(group=ENTRY_POINT_GROUP):
        if entry.name == ENTRY_POINT_NAME:
            return entry
    return None


def describe():
    """The installed viewer: ``path``, ``index``, ``apiVersion``, ``version``.

    Raises :class:`ViewerUnavailable` naming the remedy when the viewer
    package is not installed, or -- with the viewer's own words -- when it is
    installed but carries no built bundle.
    """
    entry = _entry()
    if entry is None:
        raise ViewerUnavailable(INSTALL_REMEDY)
    try:
        return entry.load()()
    except Exception as error:
        raise ViewerUnavailable(str(error)) from error


def has_bundle():
    """Whether a usable viewer is installed beside this framework."""
    try:
        describe()
    except ViewerUnavailable:
        return False
    return True


def missing_bundle_remedy():
    """What to do about the viewer that is not there."""
    try:
        describe()
    except ViewerUnavailable as error:
        return str(error)
    return None


def bundle_path():
    """Return the installed viewer bundle path."""
    return Path(describe()['path'])


def index_path():
    """Return the installed standalone export page path."""
    return Path(describe()['index'])


def api_version():
    """Return the viewer API version the installed widget declares."""
    return describe()['apiVersion']


def viewer_command():
    """The viewer's command line, run through this interpreter.

    The viewer installed beside the interpreter running ``solid`` is the one
    asked; a ``solid-node-viewer`` script earlier on the PATH from another
    environment is never picked up by accident.
    """
    return [sys.executable, '-m', 'solid_node_viewer']
