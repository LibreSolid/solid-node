# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Exports a node tree as a static, embeddable artifact: a manifest.json
describing the tree (with raw, unevaluated operation expressions, so a
viewer can animate $t client-side) plus the STL meshes of every rigid
node, deduplicated. This is the data layer of the export widget; the
serialization mirrors what NodeAPI (viewers/web/viewer.py) streams to
the live web app, but frozen on disk with no server."""

import json
import logging
import os
import shutil


logger = logging.getLogger('core.export')

MANIFEST_FORMAT = 'solid-node-export'
MANIFEST_VERSION = 1

# The standalone viewer: a static index.html plus the JS bundle built
# by npm/CI inside viewers/widget (dist/ is not committed to git)
WIDGET_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'viewers', 'widget',
)
WIDGET_BUNDLE = os.path.join(WIDGET_DIR, 'dist', 'solid-widget.js')
WIDGET_INDEX = os.path.join(WIDGET_DIR, 'index.html')


class WidgetBundleMissing(Exception):
    """The prebuilt widget JS bundle is not present (source checkouts
    only ship its sources; releases ship the built artifact)."""

    def __init__(self):
        super().__init__(
            f'Widget bundle not found at {WIDGET_BUNDLE}. '
            f'Build it with: cd {WIDGET_DIR} && npm install && '
            'npm run build -- or pass --no-widget to export only '
            'the manifest and models.'
        )


def export_node(node, output_dir, fps=30, frames=360, widget=True):
    """Builds all STLs for `node`, then writes into `output_dir`:

    - manifest.json: the serialized node tree plus animation parameters
    - models/: one STL per distinct rigid artifact, keyed by its path
      relative to the build dir (so same-named scripts in different
      directories never collide, and identical instances deduplicate)
    - unless widget=False: index.html plus the solid-widget.js bundle,
      making the directory a self-contained, embeddable viewer

    Returns the manifest dict."""
    node.build_stls()

    # Maps each rigid node's stl_file to its manifest-relative path
    models = {}
    root = _serialize_tree(node, models)

    manifest = {
        'format': MANIFEST_FORMAT,
        'version': MANIFEST_VERSION,
        'animation': {'fps': fps, 'frames': frames},
        'root': root,
    }

    os.makedirs(output_dir, exist_ok=True)
    for stl_file, model_path in models.items():
        target = os.path.join(output_dir, model_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(stl_file, target)
        logger.info(f'{stl_file} -> {target}')

    manifest_path = os.path.join(output_dir, 'manifest.json')
    with open(manifest_path, 'w') as fh:
        json.dump(manifest, fh, indent=2)
    logger.info(f'{manifest_path} written')

    if widget:
        _copy_widget(output_dir)

    return manifest


def _copy_widget(output_dir):
    if not os.path.exists(WIDGET_BUNDLE):
        raise WidgetBundleMissing()
    for source in (WIDGET_BUNDLE, WIDGET_INDEX):
        target = os.path.join(output_dir, os.path.basename(source))
        shutil.copy2(source, target)
        logger.info(f'{source} -> {target}')


def _serialize_tree(node, models):
    """Serializes a node and, recursively, its children -- the same
    walk NodeAPI does: rigid nodes are a single mesh and stop the
    recursion; non-rigid nodes recurse into their rendered children."""
    data = {
        'name': node.name,
        'type': node._type,
        'color': node.color,
        'operations': [op.serialized for op in node.operations],
    }

    if node.rigid:
        data['model'] = models.setdefault(
            node.stl_file, _model_path(node),
        )
        return data

    children = node.render()
    if type(children) not in (list, tuple):
        # A non-rigid leaf: nothing to recurse into
        return data

    data['children'] = [
        _serialize_tree(child, models) for child in children
    ]
    return data


def _model_path(node):
    """The manifest-relative path for a rigid node's STL, preserving
    its position under the build dir for uniqueness."""
    build_root = os.path.relpath(
        os.environ.get('SOLID_BUILD_DIR', '_build')
    )
    return os.path.join(
        'models',
        os.path.relpath(node.stl_file, build_root),
    )
