# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Locate the built, distributable viewer without loading CAD runtime code."""

import json
from pathlib import Path


WIDGET_DIR = Path(__file__).parent / 'widget'
PACKAGE_JSON = WIDGET_DIR / 'package.json'
BUNDLE_NAME = 'solid-widget.js'


def bundle_path():
    """Return the installed viewer bundle path."""
    return WIDGET_DIR / 'dist' / BUNDLE_NAME


def index_path():
    """Return the installed viewer index page path."""
    return WIDGET_DIR / 'index.html'


def has_bundle():
    """Whether this installation includes the built viewer bundle."""
    return bundle_path().is_file()


def api_version():
    """Return the viewer API version declared by its package."""
    with open(PACKAGE_JSON) as stream:
        return json.load(stream)['solidNodeViewerApi']


def missing_bundle_remedy():
    """Explain how a source checkout can produce the missing bundle."""
    return (
        f'Viewer bundle not found at {bundle_path()}. Build it with: '
        f'cd {WIDGET_DIR} && npm ci && npm run build.'
    )
