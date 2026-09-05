# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Transparent PNG rendering through the installed browser viewer.

This side knows what a node is: it brings the artifacts up to date under
the build lock, serializes the photographed node into a staging directory of
its own and links the models it names there. The photograph itself is the
viewer's -- `solid-node-viewer capture`, run on that directory as a separate
process with the image size, the animation instant and the camera this side
resolved from OpenSCAD's syntax. Nothing of the viewer is imported here.
"""

import json
import os
import shutil
import tempfile
from subprocess import run

from solid_node.core.builder import get_build_dir, project_build_lock
from solid_node.core.camera import parse_camera
from solid_node.core.pieces import PieceInventory
from solid_node.core.serializer import (
    DOCUMENT_FORMAT, document_version, serialize_node,
)
from solid_node.viewers import bundle as viewer_bundle


class BrowserSnapshotError(Exception):
    pass


class BrowserRenderer:
    def render(self, node, args, output):
        build_dir = self.build_dir(node, args)
        staging = None
        try:
            with project_build_lock(build_dir):
                node.build_stls()
                staging = self.stage(node, build_dir)
            self.capture(staging, args, output)
        finally:
            if staging is not None:
                self.remove_stage(staging)

    def build_dir(self, node, args=None):
        origin = getattr(args, "path", None) or getattr(node, "file", None)
        return os.path.abspath(get_build_dir(origin))

    def stage(self, node, build_dir):
        """Describe `node` in a private directory beside the build.

        The document is serialized here rather than republished into the
        build, because the build's own document and artifacts belong to
        whatever produced them -- usually a running `solid develop` serving
        the project's root. Writing this node's tree there would replace
        that model, sweep the artifacts it still references, and discard any
        recorded build error. A snapshot only reads.
        """
        if not viewer_bundle.has_bundle():
            raise BrowserSnapshotError(viewer_bundle.missing_bundle_remedy())

        artifacts = {}
        inventory = PieceInventory()
        root = serialize_node(
            node,
            lambda rigid_node: artifacts.setdefault(
                rigid_node.stl_file,
                self.artifact_path(rigid_node.stl_file, build_dir),
            ),
            inventory.register,
        )
        document = {
            "format": DOCUMENT_FORMAT,
            # Read off the tree, as every producer of this document does:
            # a snapshot of a project holding a flexible part still needs
            # the version that knows the shape, even though the part is
            # photographed at one numeric instant like everything else.
            "version": document_version(root),
            # Empty by construction, and not an oversight: this producer
            # photographs ONE instant, so it serializes the node exactly
            # as the caller posed it -- animation time keyframed, drivers
            # numerically bound -- and the resulting document names no
            # driver at all. Publishing a table the document never
            # references would only tell a viewer to refuse a picture it
            # can render perfectly well.
            "drivers": {},
            # Empty for the same reason, and necessarily: an instruction
            # moves a driver, and this document names none.
            "instructions": {},
            "animation": {"fps": 30, "frames": 360},
            "root": root,
            "pieces": inventory.pieces(),
        }

        staging = tempfile.mkdtemp(
            prefix=f"{os.path.basename(build_dir)}.web-snapshot.",
            dir=os.path.dirname(build_dir),
        )
        try:
            with open(os.path.join(staging, "viewer.json"), "w") as output:
                json.dump(document, output)
            for source, relative in artifacts.items():
                if not os.path.isfile(source):
                    raise BrowserSnapshotError(
                        f"Build artifact is missing: {relative}"
                    )
                target = os.path.join(staging, relative)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                os.link(source, target)
            return staging
        except Exception:
            self.remove_stage(staging)
            raise

    def artifact_path(self, stl_file, build_dir):
        """The staged, build-relative location of one artifact."""
        source = os.path.abspath(stl_file)
        if os.path.commonpath((source, build_dir)) != build_dir:
            raise BrowserSnapshotError(
                f"Node artifact lies outside the build: {stl_file}"
            )
        return os.path.relpath(source, build_dir)

    def remove_stage(self, staging):
        shutil.rmtree(staging, ignore_errors=True)

    def capture_command(self, staging, args, output):
        """The viewer's capture, told what to photograph and how to frame it."""
        command = viewer_bundle.viewer_command() + [
            "capture", staging, "-o", output,
            "--imgsize", args.imgsize, "--time", str(args.time),
        ]
        if args.camera:
            camera = parse_camera(args.camera)
            command += [
                "--view", ",".join(str(v) for v in (*camera.eye, *camera.target)),
                "--up", ",".join(str(v) for v in camera.up),
                "--fov", str(camera.fov),
            ]
        return command

    def capture(self, staging, args, output):
        """Photograph the staged document through the viewer's own process."""
        result = run(
            self.capture_command(staging, args, output),
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or (
                f"the viewer's capture exited with status {result.returncode}"
            )
            raise BrowserSnapshotError(message)
