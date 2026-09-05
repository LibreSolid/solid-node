# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Exports a node tree as a static, embeddable artifact: a manifest.json
describing the tree (with raw, unevaluated operation expressions, so a
viewer can animate $t client-side) plus the STL meshes of every rigid
node, deduplicated. This is the data layer of the export widget; the
serialization mirrors what the published build snapshot serves to
the live web app, but frozen on disk with no server.

Those unevaluated expressions are guaranteed here rather than assumed
of the caller: export clears any keyframe on the node first. The
serializer cannot do it -- an operation records whatever value render()
already computed, so a keyframed tree has no symbolic form left to
recover -- and the serializer must not do it, because the web-snapshot
producer keyframes deliberately and bakes its one instant through
solid_node.math, the ADR-022 source of truth."""

import json
import logging
import os
import shutil

from .serializer import (
    DOCUMENT_FORMAT, DOCUMENT_VERSION, animation_block, document_version,
    drivers_table, instructions_table, serialize_node, symbolic_document,
)
from .builder import project_build_lock
from .pieces import PieceInventory
from solid_node.viewers import bundle as viewer_bundle


logger = logging.getLogger('core.export')

MANIFEST_FORMAT = DOCUMENT_FORMAT
# The version a manifest without flexible content declares. A manifest
# carrying a flexible part needs the shape only a later version knows, so
# what each export declares is read off the tree it just serialized.
MANIFEST_VERSION = DOCUMENT_VERSION

class WidgetBundleMissing(Exception):
    """No viewer is installed to copy the widget files from."""

    def __init__(self):
        super().__init__(
            f'{viewer_bundle.missing_bundle_remedy()} Or pass --no-widget '
            'to export only the manifest and models.'
        )


def export_node(node, output_dir, fps=30, frames=360, widget=True):
    """Builds all STLs for `node`, then writes into `output_dir`:

    - manifest.json: the serialized node tree plus animation parameters
    - models/: one STL per distinct rigid artifact, keyed by its path
      relative to the build dir (so same-named scripts in different
      directories never collide, and identical instances deduplicate)
    - unless widget=False: index.html plus the solid-widget.js bundle,
      making the directory a self-contained, embeddable viewer

    The manifest always carries symbolic $t operations, and symbolic
    named-driver operations beside them. Preserving both is this
    producer's guarantee, not the caller's obligation: `node` is
    returned to symbolic animation time before it is serialized, and
    every declared driver in its tree is bound to its qualified token
    for the duration of the walk, so a host that keyframed or stepped
    it -- to read a mesh, run a test, or render one instant -- still
    publishes the animated document rather than the constants that
    keyframe or snapshot computed.

    `node` is left in symbolic time afterwards; a previously set
    keyframe is NOT restored, because an assembly's children can be
    recreated objects on each render, so the only safe restore would
    flatten a non-uniform nested keyframe. A caller wanting a numeric
    pose back applies set_keyframe again. Driver bindings ARE restored,
    because there is nothing to flatten: the symbolic mode binds every
    declared driver of the tree by qualified id and puts back exactly
    the per-instance snapshot each node held. A static PRESENTATION of an
    export needs no frozen document: the widget's ?t= and ?autoplay=0
    options render any instant of an animated one.

    Returns the manifest dict."""
    node.clear_keyframe()

    with project_build_lock():
        node.build_stls()

    # Maps each rigid node's stl_file to its manifest-relative path
    models = {}
    inventory = PieceInventory()
    with symbolic_document(node) as (declarations, instructions):
        root = serialize_node(
            node,
            lambda rigid_node: models.setdefault(
                rigid_node.stl_file, _model_path(rigid_node),
            ),
            inventory.register,
        )
        drivers = drivers_table(declarations)
        events = instructions_table(instructions)

    manifest = {
        'format': MANIFEST_FORMAT,
        'version': document_version(root),
        'animation': animation_block(node, fps, frames),
        'drivers': drivers,
        'instructions': events,
        'root': root,
        'pieces': inventory.pieces(),
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
    if not viewer_bundle.has_bundle():
        raise WidgetBundleMissing()
    for source in (viewer_bundle.bundle_path(), viewer_bundle.index_path()):
        target = os.path.join(output_dir, os.path.basename(source))
        shutil.copy2(source, target)
        logger.info(f'{source} -> {target}')


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
